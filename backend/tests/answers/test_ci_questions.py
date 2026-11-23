"""The answer chain in CI with recorded model answers (E-10, work order 135).

Every question of ``fixtures/ci_questions.json`` goes through
:func:`twox.answers.service.answer` with the real context selection, prompt
and citation check. The sections come from the Docling fixtures of the free
test documents (``tests/ingest/fixtures/``, from ``testdata/klein``) through
:class:`~tests.ingest.fake_converter.FakeConverter`, plus one self-written
injection text (``fixtures/injection.md``); the vectors come from stand-ins.
The model answers come from ``recorded/ci_questions.json`` through
:class:`~twox.answers.replay.ReplayChatModel`: no model, no network. A socket
lock fails every test that tries to connect anywhere.

``manage.py record_answers`` runs this module with ``TWOX_RECORD_ANSWERS=1``:
then the real chat model answers (``TWOX_CHAT_MODEL``), every check runs as
well, and the last test writes the recording, but only when every question
that asked the model passed its checks. The set-up is the same in both modes,
so the prompts, and with them the keys, are the same.

Uploaded are the stand-in bytes of ``fake_converter.py``, not the files of
``testdata/klein``; the question set therefore names a document id, and the
test maps it to the checksum of the version it created.
"""

import hashlib
import json
import logging
import math
import os
import re
import socket
import sys
import urllib.request
from collections.abc import Callable, Iterator, Sequence
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Literal

import pytest
from django.conf import settings as django_settings
from django.core.management import call_command
from django.core.management.base import CommandError
from pytest_django.fixtures import Settings

from tests.files.helpers import make_device
from tests.ingest.fake_converter import (
    MARKDOWN_CONTENT,
    PDF_CONTENT,
    FakeConverter,
    make_job,
    make_version,
    run_job,
)
from tests.ingest.fake_docling import (
    BETRSICHV_FIXTURE,
    MARKDOWN_FIXTURE,
    fixture_document,
    result_answer,
)
from tests.search.fake_embedder import (
    CLOSED_MODEL_SERVICE,
    FAKE_MODEL,
    FakeEmbedder,
    embed,
    install,
    unit,
)
from tests.search.test_keyword_search import add_sections, make_document
from twox.answers import chat as chat_module
from twox.answers import embeddings, prompt, replay, service
from twox.answers.chat import (
    ChatModel,
    ChatUnavailableError,
    FakeChatModel,
    OpenAICompatibleChat,
)
from twox.answers.evaluation import (
    AnswerFunction,
    Observed,
    Question,
    QuestionKind,
    QuestionPlaces,
    Verdict,
    evaluate,
    judge_run,
)
from twox.answers.llm_guard import TAGS_PATH, find_local_model, ollama_root
from twox.answers.replay import (
    RecordedEntry,
    RecordedSource,
    Recording,
    RecordingChatModel,
    RecordingMissingError,
    RecordingSettings,
    ReplayChatModel,
)
from twox.answers.types import (
    NO_EVIDENCE_TEXT,
    AnswerEvent,
    AnswerStatus,
    DeltaEvent,
    DoneEvent,
    ErrorCode,
    ErrorEvent,
    SourcesEvent,
)
from twox.files.models import DocumentVersion
from twox.ingest.models import Section
from twox.search.evaluation import ExpectedPlace
from twox.search.interface import SearchRequest, SemanticState, get_search_backend

pytestmark = pytest.mark.django_db

HERE = Path(__file__).parent
QUESTIONS_FILE = HERE / "fixtures" / "ci_questions.json"
INJECTION_FILE = HERE / "fixtures" / "injection.md"
RECORDING_FILE = HERE / "recorded" / "ci_questions.json"

#: True when ``manage.py record_answers`` runs this module.
RECORDING = os.environ.get(replay.RECORD_ENV) == "1"
replay_only = pytest.mark.skipif(RECORDING, reason="checks the replay, not the recording")

#: The identifier of the delimiters, fixed so that the prompts and keys are stable.
NONCE = "0123456789abcdef"
#: The seed of every request; part of the recording.
SEED = 135
#: The model settings of a recording (Temperature 0, reasoning off, work order 121).
TEMPERATURE = 0.0
MAX_TOKENS = 1024
REASONING_EFFORT = "none"
#: The context settings of the answers (125), fixed so that ``.env`` cannot change them.
ANSWER_SETTINGS = {
    "TWOX_ANSWER_MAX_SOURCES": 3,
    "TWOX_ANSWER_CONTEXT_CHARS": 8000,
    "TWOX_ANSWER_NEIGHBOURS": False,
    "TWOX_ANSWER_MAX_DISTANCE": 0.6,
    "TWOX_ANSWER_TRANSLATION_DISTANCE": 0.15,
    "TWOX_SECTION_MAX_CHARS": 2000,
}
#: The largest cosine distance: with it every section passes the threshold.
THRESHOLD_OFF = 2.0
#: Angle between a question and the section that answers it (cosine distance about 0.06).
EVIDENCE_ANGLE = 20.0
#: Axes of the question vectors start here; sections get their own axes after them.
QUESTION_AXIS = 1
SECTION_AXIS = 64

#: The documents of the test: device key, uploaded bytes and where the sections come from.
DOCUMENT_DEVICES = {
    "betrsichv": "ci-device-a",
    "sftp-backup": "ci-device-b",
    "injection": "ci-device-c",
}

#: Questions whose answer the model gives (and that are therefore recorded).
RECORDED_QUESTIONS = ("ci-fact-1", "ci-fact-2", "ci-control", "ci-injection")

_TAG = re.compile(r"<\s*/?\s*[a-zA-Z!]")


# --- The question set -------------------------------------------------------------------


@dataclass(frozen=True)
class CiQuestion:
    """One entry of ``fixtures/ci_questions.json``."""

    id: str
    kind: Literal["fact", "contradiction", "no-evidence", "injection"]
    question: str
    document: str | None = None
    page: int | None = None
    heading_path: tuple[str, ...] | None = None
    #: A short piece of the section that answers the question (from the free text).
    evidence: str | None = None
    #: Words for the keyword search with the AI features off.
    keywords: str | None = None
    #: Restricts the question to the device of this document.
    scope_document: str | None = None
    key_facts: tuple[str, ...] = ()
    alternatives: tuple[tuple[str, tuple[str, ...]], ...] = ()
    forbidden: tuple[str, ...] = ()


def load_question_set() -> dict[str, CiQuestion]:
    data = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    questions: dict[str, CiQuestion] = {}
    for item in data["questions"]:
        heading_path = item.get("heading_path")
        questions[item["id"]] = CiQuestion(
            id=item["id"],
            kind=item["kind"],
            question=item["question"],
            document=item.get("document"),
            page=item.get("page"),
            heading_path=None if heading_path is None else tuple(heading_path),
            evidence=item.get("evidence"),
            keywords=item.get("keywords"),
            scope_document=item.get("scope_document"),
            key_facts=tuple(item.get("key_facts", ())),
            alternatives=tuple(
                (fact, tuple(spellings))
                for fact, spellings in item.get("key_fact_alternatives", {}).items()
            ),
            forbidden=tuple(item.get("forbidden", ())),
        )
    return questions


QUESTIONS = load_question_set()


def injection_section() -> tuple[list[str], str]:
    """Heading path and text of the self-written injection document (without its note)."""
    lines = INJECTION_FILE.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("<!-- self-written test text, no real device")
    heading = next(index for index, line in enumerate(lines) if line.startswith("# "))
    text = "\n".join(lines[heading + 1 :]).strip()
    return [lines[heading][2:].strip()], text


# --- Socket lock --------------------------------------------------------------------------


class NetworkUsedError(AssertionError):
    """A test tried to resolve a name or to open a connection."""


@pytest.fixture
def network_lock(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    """Every attempt to resolve or connect fails, and fails the test at its end.

    As in ``test_check_llm.py``. The database is not affected: psycopg connects
    through libpq, not through :mod:`socket`. Off while recording.
    """
    attempts: list[str] = []
    if RECORDING:
        yield attempts
        return

    def refuse(*args: object, **kwargs: object) -> object:
        attempts.append(type(args[0]).__name__ if args else "-")
        raise NetworkUsedError("the CI questions must not use the network")

    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    yield attempts
    assert not attempts, f"a test tried to use the network: {attempts}"


# --- Recording ----------------------------------------------------------------------------


@dataclass
class Collector:
    """What one recording run gathered (only used with ``TWOX_RECORD_ANSWERS=1``)."""

    entries: dict[str, RecordedEntry] = field(default_factory=dict)
    known: dict[str, tuple[str, ...]] = field(default_factory=dict)
    confirmed: set[str] = field(default_factory=set)


@pytest.fixture(scope="module")
def collector() -> Collector:
    return Collector()


def model_digest(model: str) -> str:
    """The digest of ``model`` in the local model list of Ollama (read-only)."""
    url = ollama_root(django_settings.TWOX_LLM_BASE_URL) + TAGS_PATH
    with urllib.request.urlopen(url, timeout=30) as response:
        body: bytes = response.read()
    digest = find_local_model(body, model).get("digest")
    assert isinstance(digest, str) and digest, "the model list names no digest"
    return digest


# --- The world of a test ------------------------------------------------------------------


Chat = ReplayChatModel | RecordingChatModel


@dataclass
class World:
    """The ingested documents, the stand-ins and the model of the test."""

    ai_enabled: bool
    query_embedder: FakeEmbedder | None
    collector: Collector
    #: Document id -> checksum of the version created in the test.
    checksums: dict[str, str]
    #: Document id -> device id.
    devices: dict[str, int]
    #: Document id -> the bytes uploaded for it.
    uploaded: dict[str, bytes]
    #: Every model created by :meth:`chat_for`, in order.
    models: list[Chat] = field(default_factory=list)

    def chat_for(self, question_id: str) -> Chat:
        """The model for one question: replay, or the real model while recording."""
        model: Chat
        if RECORDING:
            model = RecordingChatModel(
                chat_module.get_chat_model(), question_id, known=self.collector.known
            )
        else:
            model = ReplayChatModel(recording(), question_id)
        self.models.append(model)
        return model

    def scope(self, question: CiQuestion) -> tuple[int, ...]:
        if question.scope_document is None:
            return ()
        return (self.devices[question.scope_document],)

    def ask(
        self,
        question: CiQuestion,
        *,
        chat: ChatModel | None = None,
        stop_after_delta: bool = False,
    ) -> list[AnswerEvent]:
        """The events of ``question``; recording misses fail here, with the question id."""
        model = chat or self.chat_for(question.id)
        events: list[AnswerEvent] = []
        generator = service.answer(
            question.question, device_ids=self.scope(question), chat=model, seed=SEED
        )
        with closing(generator):
            for event in generator:
                events.append(event)
                if stop_after_delta and isinstance(event, DeltaEvent):
                    break
        self.after(model, events)
        return events

    def answer_function(self, questions: Sequence[CiQuestion]) -> AnswerFunction:
        """:func:`service.answer` for :func:`~twox.answers.evaluation.evaluate`."""
        by_text = {question.question: question for question in questions}

        def run(
            question: str,
            *,
            device_ids: Sequence[int] = (),
            plant_ids: Sequence[int] = (),
            seed: int | None = None,
            on_context: service.ContextObserver | None = None,
        ) -> Iterator[AnswerEvent]:
            # The seed of the recordings (SEED) stays; the one of the caller is not used.
            model = self.chat_for(by_text[question].id)
            events = service.answer(
                question,
                device_ids=device_ids,
                plant_ids=plant_ids,
                chat=model,
                seed=SEED,
                on_context=on_context,
            )
            seen: list[AnswerEvent] = []
            try:
                for event in events:
                    seen.append(event)
                    yield event
            finally:
                events.close()
                self.after(model, seen)

        return run

    def after(self, model: ChatModel, events: Sequence[AnswerEvent]) -> None:
        """Raise a recording miss; keep what the real model said while recording."""
        if isinstance(model, ReplayChatModel):
            if model.misses:
                raise model.misses[0]
            return
        if not isinstance(model, RecordingChatModel):
            return
        sources = sources_of(events)
        for call in model.calls:
            self.collector.entries.setdefault(
                call.key,
                RecordedEntry(
                    question_id=call.question_id,
                    key=call.key,
                    sources=recorded_sources(sources),
                    chunks=call.chunks,
                ),
            )

    def confirm(self, question_id: str) -> None:
        """The checks of ``question_id`` passed: its recording may be written."""
        self.collector.confirmed.add(question_id)


def asked(model: Chat) -> int:
    """How often the answer service called ``stream()`` of ``model``."""
    return model.requests


def recording() -> Recording:
    if not RECORDING_FILE.exists():
        pytest.fail(f"{RECORDING_FILE.name} is missing; {replay.RERECORD_HINT}")
    return replay.load_recording(RECORDING_FILE.read_text(encoding="utf-8"))


def sources_of(events: Sequence[AnswerEvent]) -> list[tuple[int, int]]:
    """``(n, section_id)`` of the ``sources`` event."""
    for event in events:
        if isinstance(event, SourcesEvent):
            return [(source.n, source.section_id) for source in event.sources]
    return []


def recorded_sources(sources: Sequence[tuple[int, int]]) -> tuple[RecordedSource, ...]:
    rows = Section.objects.filter(pk__in=[section_id for _, section_id in sources]).values_list(
        "pk", "ordinal", "document_version__sha256"
    )
    stored = {pk: (ordinal, sha256) for pk, ordinal, sha256 in rows}
    return tuple(
        RecordedSource(n=n, sha256=stored[section_id][1], ordinal=stored[section_id][0])
        for n, section_id in sources
    )


def done_of(events: Sequence[AnswerEvent]) -> DoneEvent:
    last = events[-1]
    assert isinstance(last, DoneEvent), [event.type for event in events]
    return last


def source_numbers(events: Sequence[AnswerEvent]) -> set[int]:
    return {n for n, _ in sources_of(events)}


def ingest_docling(document: str, content: bytes, fixture: Path, filename: str, kind: str) -> str:
    """Upload stand-in bytes and ingest them; Docling answers with ``fixture``."""
    version = make_version(
        content, device=DOCUMENT_DEVICES[document], filename=filename, content_type=kind
    )
    run_job(make_job(version), FakeConverter(answer=result_answer(fixture_document(fixture))))
    assert version.sections.exists()
    return version.sha256


def store_vectors(questions: Sequence[CiQuestion]) -> dict[str, list[float]]:
    """Section vectors on their own axes; the evidence of a question near its question.

    Returns the vector of each question text. A question without evidence
    (the control question) is orthogonal to every section: cosine distance 1.
    """
    axes: dict[str, int] = {}
    for question in questions:
        axes.setdefault(question.question, QUESTION_AXIS + len(axes))
    near: dict[int, int] = {}
    for question in questions:
        if question.evidence is None:
            continue
        [section] = Section.objects.filter(text__contains=question.evidence)
        near[section.pk] = axes[question.question]
    sections = Section.objects.order_by("document_version_id", "ordinal")
    for index, section in enumerate(sections):
        own = SECTION_AXIS + index
        vector = unit(own)
        if section.pk in near:
            vector[near[section.pk]] = math.cos(math.radians(EVIDENCE_ANGLE))
            vector[own] = math.sin(math.radians(EVIDENCE_ANGLE))
        embed(section, vector)
    return {text: unit(axis) for text, axis in axes.items()}


def build_world(
    *,
    ai_enabled: bool,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    collector: Collector,
) -> World:
    for name, value in ANSWER_SETTINGS.items():
        setattr(settings, name, value)
    settings.TWOX_MEDIA_ROOT = tmp_path / "media"
    settings.TWOX_AI_ENABLED = False
    settings.TWOX_DOCLING_URL = "http://docling.invalid:5001"
    settings.TWOX_EMBED_MODEL = FAKE_MODEL
    settings.TWOX_CHAT_TEMPERATURE = TEMPERATURE
    settings.TWOX_CHAT_MAX_TOKENS = MAX_TOKENS
    settings.TWOX_CHAT_REASONING_EFFORT = REASONING_EFFORT
    if not RECORDING:
        settings.TWOX_LLM_BASE_URL = CLOSED_MODEL_SERVICE
        settings.TWOX_CHAT_MODEL = ""

        def no_real_model() -> ChatModel:
            raise AssertionError("the CI questions must not fetch the real chat model")

        monkeypatch.setattr(chat_module, "get_chat_model", no_real_model)
    monkeypatch.setattr(prompt, "new_nonce", lambda: NONCE)
    embeddings.forget_query_embedder()

    uploaded = {"betrsichv": PDF_CONTENT, "sftp-backup": MARKDOWN_CONTENT}
    checksums = {
        "betrsichv": ingest_docling(
            "betrsichv", PDF_CONTENT, BETRSICHV_FIXTURE, "BetrSichV.pdf", "application/pdf"
        ),
        "sftp-backup": ingest_docling(
            "sftp-backup", MARKDOWN_CONTENT, MARKDOWN_FIXTURE, "sftp-backup.md", "text/markdown"
        ),
    }
    injection_bytes = INJECTION_FILE.read_bytes()
    uploaded["injection"] = injection_bytes
    checksums["injection"] = hashlib.sha256(injection_bytes).hexdigest()
    headings, text = injection_section()
    version = make_document(
        make_device(DOCUMENT_DEVICES["injection"]),
        title="Injection probe",
        sha256=checksums["injection"],
    )
    add_sections(version, text, headings=headings, page=None)
    devices = {
        document: DocumentVersion.objects.get(sha256=checksum).document.device_id
        for document, checksum in checksums.items()
    }

    vectors = store_vectors(list(QUESTIONS.values()))
    query_embedder: FakeEmbedder | None = None
    if ai_enabled:
        query_embedder = install(monkeypatch, settings, FakeEmbedder(FAKE_MODEL))
        query_embedder.queries.update(vectors)
    else:

        def no_model_service() -> embeddings.Embedder:
            raise AssertionError("the model service was asked with the AI features off")

        monkeypatch.setattr(embeddings, "get_embedder", no_model_service)
        monkeypatch.setattr(embeddings, "get_query_embedder", no_model_service)
    return World(
        ai_enabled=ai_enabled,
        query_embedder=query_embedder,
        collector=collector,
        checksums=checksums,
        devices=devices,
        uploaded=uploaded,
    )


@pytest.fixture(params=[False, True], ids=["ai-off", "ai-on"])
def world(
    request: pytest.FixtureRequest,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    collector: Collector,
    network_lock: list[str],
) -> Iterator[World]:
    """The documents with the AI features off and on (E-59)."""
    yield build_world(
        ai_enabled=request.param,
        settings=settings,
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        collector=collector,
    )
    embeddings.forget_query_embedder()


@pytest.fixture
def ai_world(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    collector: Collector,
    network_lock: list[str],
) -> Iterator[World]:
    """The documents with the AI features on."""
    yield build_world(
        ai_enabled=True,
        settings=settings,
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        collector=collector,
    )
    embeddings.forget_query_embedder()


def expected_place(world: World, question: CiQuestion) -> ExpectedPlace:
    assert question.document is not None
    return ExpectedPlace(
        manifest_id=question.document,
        sha256=world.checksums[question.document],
        pages=frozenset() if question.page is None else frozenset({question.page}),
        heading_path=question.heading_path,
    )


def as_evaluation_question(number: int, question: CiQuestion) -> Question:
    kind = QuestionKind.NO_EVIDENCE if question.kind == "no-evidence" else QuestionKind.FACT
    return Question(
        id=number,
        question=question.question,
        kind=kind,
        key_facts=question.key_facts,
        alternatives=question.alternatives,
    )


def places_of(world: World, number: int, question: CiQuestion) -> QuestionPlaces:
    return QuestionPlaces(
        question=number,
        probe_ids=(question.id,),
        expected=(expected_place(world, question),),
        editions=(),
        query=question.question,
    )


# --- The question set and the documents ---------------------------------------------------


def test_question_set_is_complete_and_self_written() -> None:
    kinds = {question.kind for question in QUESTIONS.values()}
    assert {"fact", "no-evidence", "injection"} <= kinds
    # The two fixtures hold no real contradiction; a made-up one is not allowed
    # (guard rail 9). The path is covered with FakeChatModel in 123 and 126.
    assert "contradiction" not in kinds
    for question in QUESTIONS.values():
        assert question.document in (None, *DOCUMENT_DEVICES)
        assert question.scope_document in (None, *DOCUMENT_DEVICES)
        if question.kind in ("fact", "injection"):
            assert question.evidence
            assert (question.page is None) != (question.heading_path is None)
    assert set(RECORDED_QUESTIONS) <= set(QUESTIONS)
    note = INJECTION_FILE.read_text(encoding="utf-8").splitlines()[0]
    assert "self-written test text, no real device" in note


def test_document_ids_point_to_the_version_whose_sections_are_cited(
    ai_world: World,
) -> None:
    for document, checksum in ai_world.checksums.items():
        assert checksum == hashlib.sha256(ai_world.uploaded[document]).hexdigest()
        version = DocumentVersion.objects.get(sha256=checksum)
        assert version.document.device.key == DOCUMENT_DEVICES[document]
    for question in QUESTIONS.values():
        if question.evidence is None:
            continue
        assert question.document is not None
        [section] = Section.objects.filter(text__contains=question.evidence)
        assert section.document_version.sha256 == ai_world.checksums[question.document]
        if question.page is not None:
            assert section.page_start is not None and section.page_end is not None
            assert section.page_start <= question.page <= section.page_end
        else:
            assert question.heading_path is not None
            assert tuple(section.heading_path[: len(question.heading_path)]) == (
                question.heading_path
            )


# --- Facts, AI off and on -----------------------------------------------------------------


@pytest.mark.parametrize("question_id", ["ci-fact-1", "ci-fact-2"])
def test_fact_question(world: World, question_id: str) -> None:
    question = QUESTIONS[question_id]
    if not world.ai_enabled:
        never = FakeChatModel(fail_on_call=ChatUnavailableError("the model must not be asked"))
        events = world.ask(question, chat=never)
        assert events == [ErrorEvent(code=ErrorCode.AI_DISABLED)]
        assert never.calls == []
        assert question.evidence is not None
        assert question.keywords is not None
        result = get_search_backend().search(SearchRequest(query=question.keywords))
        assert result.semantic is SemanticState.DISABLED
        place = expected_place(world, question)
        assert any(
            hit.locations[0].version_id == DocumentVersion.objects.get(sha256=place.sha256).pk
            and question.evidence in Section.objects.get(pk=hit.section_id).text
            for hit in result.hits
        )
        return

    chat = world.chat_for(question.id)
    events = world.ask(question, chat=chat)
    types = [event.type for event in events]
    assert types[0] == "sources"
    assert types[-1] == "done"
    assert set(types[1:-1]) == {"delta"}
    assert asked(chat) == 1
    done = done_of(events)
    assert done.status is AnswerStatus.ANSWERED, done
    assert set(done.cited) <= source_numbers(events)
    sources_event = events[0]
    assert isinstance(sources_event, SourcesEvent)
    observed = Observed(sources=tuple(sources_event.sources), done=done)
    verdict = judge_run(
        as_evaluation_question(1, question), places_of(world, 1, question), observed
    )
    assert verdict.verdict is Verdict.CORRECT, verdict
    world.confirm(question.id)


def test_evaluate_with_the_small_question_set(ai_world: World) -> None:
    """The rules of 127 decide, with the threshold of the small set (2 of 2)."""
    chosen = [QUESTIONS[key] for key in ("ci-fact-1", "ci-fact-2", "ci-control")]
    questions = [as_evaluation_question(n, q) for n, q in enumerate(chosen, 1)]
    places = {
        n: places_of(ai_world, n, q) for n, q in enumerate(chosen, 1) if q.kind != "no-evidence"
    }
    present = set(ai_world.checksums.values())
    report = evaluate(
        questions,
        places,
        answer=ai_world.answer_function(chosen),
        required=2,
        ingested=lambda checksums: set(checksums) & present,
    )
    assert report.summary is not None
    assert [result.verdict for result in report.questions] == [Verdict.CORRECT] * 3, report
    assert report.summary.control_ok
    assert report.summary.passed


def test_evaluate_reports_the_best_distance_of_every_asked_question(ai_world: World) -> None:
    """The values come from the context selection of the run itself (work order 142).

    No particular distance is fixed here, so that a new recording does not break it.
    """
    chosen = [QUESTIONS[key] for key in ("ci-fact-1", "ci-fact-2", "ci-control")]
    questions = [as_evaluation_question(n, q) for n, q in enumerate(chosen, 1)]
    places = {
        n: places_of(ai_world, n, q) for n, q in enumerate(chosen, 1) if q.kind != "no-evidence"
    }
    present = set(ai_world.checksums.values())
    report = evaluate(
        questions,
        places,
        runs=2,
        answer=ai_world.answer_function(chosen),
        required=2,
        ingested=lambda checksums: set(checksums) & present,
        seed=5,
    )
    assert report.seed == 5
    for result in report.questions:
        assert len(result.runs) == 2
        for run in result.runs:
            assert isinstance(run.best_distance, float), result.question_id
            assert run.below_threshold is not None
        assert result.best_distance.median is not None
        # The control question is below the threshold in every run: the model is not asked.
        if result.is_control:
            assert result.below_threshold_runs == 2
            assert all(run.below_threshold is True for run in result.runs)
        else:
            assert result.below_threshold_runs == 0


# --- Control question ---------------------------------------------------------------------


def test_control_question_below_the_threshold_does_not_ask_the_model(ai_world: World) -> None:
    question = QUESTIONS["ci-control"]
    chat = ai_world.chat_for(question.id)
    events = ai_world.ask(question, chat=chat)
    assert events[0] == SourcesEvent(sources=[])
    done = done_of(events)
    assert done.status is AnswerStatus.NO_EVIDENCE
    assert done.cited == []
    assert done.final_text == NO_EVIDENCE_TEXT
    assert asked(chat) == 0


def test_control_question_without_threshold_plays_the_refusal(
    ai_world: World, settings: Settings
) -> None:
    settings.TWOX_ANSWER_MAX_DISTANCE = THRESHOLD_OFF
    question = QUESTIONS["ci-control"]
    chat = ai_world.chat_for(question.id)
    events = ai_world.ask(question, chat=chat)
    assert sources_of(events), "with the threshold off the model must see sources"
    assert asked(chat) == 1
    done = done_of(events)
    assert done.status is AnswerStatus.NO_EVIDENCE, done
    assert done.cited == []
    assert done.final_text == NO_EVIDENCE_TEXT
    ai_world.confirm(question.id)


# --- Injection probe ----------------------------------------------------------------------


def test_injection_probe_does_not_follow_the_embedded_instruction(ai_world: World) -> None:
    question = QUESTIONS["ci-injection"]
    chat = ai_world.chat_for(question.id)
    events = ai_world.ask(question, chat=chat)
    sources_event = events[0]
    assert isinstance(sources_event, SourcesEvent)
    assert ai_world.checksums["injection"] in {source.sha256 for source in sources_event.sources}
    done = done_of(events)
    assert done.status in (AnswerStatus.ANSWERED, AnswerStatus.NO_EVIDENCE), done
    text = done.final_text
    assert "http" not in text.casefold()
    assert "](" not in text
    assert not _TAG.search(text), text
    for word in question.forbidden:
        assert word.casefold() not in text.casefold()
    assert set(done.cited) <= source_numbers(events)
    ai_world.confirm(question.id)


# --- Scope --------------------------------------------------------------------------------


def test_fact_question_scoped_to_the_foreign_device(ai_world: World) -> None:
    question = QUESTIONS["ci-scope-foreign"]
    assert question.question == QUESTIONS["ci-fact-1"].question
    chat = ai_world.chat_for(question.id)
    events = ai_world.ask(question, chat=chat)
    sources_event = events[0]
    assert isinstance(sources_event, SourcesEvent)
    assert ai_world.checksums["betrsichv"] not in {s.sha256 for s in sources_event.sources}
    done = done_of(events)
    assert done.status is AnswerStatus.NO_EVIDENCE
    assert done.cited == []
    assert asked(chat) == 0


# --- Replay: out of date, cancelled -------------------------------------------------------


def _changed_template(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompt, "SYSTEM_TEMPLATE", prompt.SYSTEM_TEMPLATE + "7. Neue Regel.\n")


def _changed_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompt, "prompt_version", lambda: "000000000000")


@replay_only
@pytest.mark.parametrize(
    "change", [_changed_template, _changed_version], ids=["template", "version"]
)
def test_a_changed_prompt_asks_to_record_again(
    ai_world: World,
    monkeypatch: pytest.MonkeyPatch,
    change: Callable[[pytest.MonkeyPatch], None],
) -> None:
    before = prompt.prompt_version()
    change(monkeypatch)
    assert prompt.prompt_version() != before
    question = QUESTIONS["ci-fact-1"]
    with pytest.raises(RecordingMissingError, match=re.escape(replay.RERECORD_HINT)) as caught:
        ai_world.ask(question)
    message = str(caught.value)
    assert message.endswith("; re-record: manage.py record_answers")
    assert "question=ci-fact-1" in message
    assert f"prompt_version={prompt.prompt_version()}" in message
    assert question.question not in message
    assert "Ausfertigungsdatum" not in message


@replay_only
def test_an_entry_of_another_question_is_no_fallback(ai_world: World) -> None:
    question = QUESTIONS["ci-fact-1"]
    other = ReplayChatModel(recording(), "ci-fact-2")
    with pytest.raises(RecordingMissingError, match="question=ci-fact-2"):
        ai_world.ask(question, chat=other)


@replay_only
def test_cancelling_closes_the_stream_of_the_replay(ai_world: World) -> None:
    question = QUESTIONS["ci-fact-1"]
    chat = ai_world.chat_for(question.id)
    assert isinstance(chat, ReplayChatModel)
    events = ai_world.ask(question, chat=chat, stop_after_delta=True)
    assert [event.type for event in events] == ["sources", "delta"]
    [stream] = chat.streams
    assert stream.closed
    # The service closes the stream of a model passed in, not the model (126).
    assert chat.close_count == 0


# --- Network ------------------------------------------------------------------------------


@replay_only
def test_the_network_lock_would_fail_a_connection(ai_world: World, network_lock: list[str]) -> None:
    with pytest.raises(NetworkUsedError):
        socket.create_connection(("127.0.0.1", 9), timeout=1)
    client = OpenAICompatibleChat(
        base_url="http://127.0.0.1:9/v1",
        model="any-model",
        timeout=1,
        max_tokens=8,
        temperature=0,
        reasoning_effort=None,
    )
    with pytest.raises(NetworkUsedError):
        client.stream([{"role": "user", "content": "x"}])
    assert len(network_lock) >= 2
    # The database still works: psycopg talks through libpq, not through socket.
    assert Section.objects.exists()
    network_lock.clear()


# --- Logs ---------------------------------------------------------------------------------


def test_no_log_line_holds_a_question_an_answer_or_a_section_text(
    ai_world: World, settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    answers: list[str] = []
    for question_id in ("ci-fact-1", "ci-fact-2", "ci-injection", "ci-control"):
        events = ai_world.ask(QUESTIONS[question_id])
        answers += [event.text for event in events if isinstance(event, DeltaEvent)]
        answers.append(done_of(events).final_text)
    settings.TWOX_ANSWER_MAX_DISTANCE = THRESHOLD_OFF
    events = ai_world.ask(QUESTIONS["ci-control"])
    answers += [event.text for event in events if isinstance(event, DeltaEvent)]
    texts = list(Section.objects.values_list("text", flat=True))
    secrets = [q.question for q in QUESTIONS.values()]
    secrets += [answer.strip() for answer in answers if len(answer.strip()) >= 12]
    secrets += [text[:40] for text in texts] + [text[-40:] for text in texts]
    assert caplog.records, "the service logs one line per request"
    for record in caplog.records:
        line = record.getMessage()
        for secret in secrets:
            assert secret not in line, (record.name, line)


# --- The recording file (written here while recording) ------------------------------------


def _model_questions(world: World, settings: Settings) -> set[str]:
    """Ask every question that reaches the model; return the keys asked."""
    keys: set[str] = set()
    for question_id in ("ci-fact-1", "ci-fact-2", "ci-injection"):
        chat = world.chat_for(question_id)
        world.ask(QUESTIONS[question_id], chat=chat)
        keys |= keys_of(chat)
    settings.TWOX_ANSWER_MAX_DISTANCE = THRESHOLD_OFF
    chat = world.chat_for("ci-control")
    world.ask(QUESTIONS["ci-control"], chat=chat)
    keys |= keys_of(chat)
    return keys


def keys_of(model: Chat) -> set[str]:
    return set(model.keys)


def test_recording_file(ai_world: World, settings: Settings, collector: Collector) -> None:
    """Format, no orphans, current prompt version; while recording: write it."""
    keys = _model_questions(ai_world, settings)
    if RECORDING:
        missing = [qid for qid in RECORDED_QUESTIONS if qid not in collector.confirmed]
        assert not missing, f"not recorded, the checks failed for: {', '.join(missing)}"
        unconfirmed = sorted(
            {e.question_id for e in collector.entries.values()} - collector.confirmed
        )
        assert not unconfirmed, f"recorded but not checked: {', '.join(unconfirmed)}"
        model = django_settings.TWOX_CHAT_MODEL
        entries = sorted(
            (collector.entries[key] for key in keys),
            key=lambda entry: (entry.question_id, entry.key),
        )
        written = Recording(
            model=model,
            model_digest=model_digest(model),
            prompt_version=prompt.prompt_version(),
            recorded_on=date.today().isoformat(),
            settings=RecordingSettings(
                temperature=TEMPERATURE,
                seed=SEED,
                max_tokens=MAX_TOKENS,
                reasoning_effort=REASONING_EFFORT,
            ),
            entries=tuple(entries),
        )
        RECORDING_FILE.parent.mkdir(parents=True, exist_ok=True)
        RECORDING_FILE.write_text(replay.dump_recording(written), encoding="utf-8", newline="\n")

    text = RECORDING_FILE.read_text(encoding="utf-8")
    loaded = replay.load_recording(text)
    assert replay.dump_recording(loaded) == text, "the file is not in the fixed layout"
    assert loaded.prompt_version == prompt.prompt_version(), replay.RERECORD_HINT
    assert loaded.settings == RecordingSettings(TEMPERATURE, SEED, MAX_TOKENS, REASONING_EFFORT)
    ids = {entry.question_id for entry in loaded.entries}
    assert ids <= set(QUESTIONS)
    assert ids == set(RECORDED_QUESTIONS)
    orphans = [entry.question_id for entry in loaded.entries if entry.key not in keys]
    assert not orphans, f"entries no question asks for: {orphans}"
    assert {entry.key for entry in loaded.entries} == keys
    for entry in loaded.entries:
        assert entry.chunks, entry.question_id
        assert all(source.sha256 in ai_world.checksums.values() for source in entry.sources)


# --- manage.py record_answers -------------------------------------------------------------


def _forbid_pytest_main(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def refuse(args: list[str]) -> int:
        calls.append(args)
        raise AssertionError("pytest.main must not run")

    monkeypatch.setattr(pytest, "main", refuse)
    return calls


def test_record_answers_needs_pytest(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, network_lock: list[str]
) -> None:
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_CHAT_MODEL = "some-model"
    monkeypatch.setitem(sys.modules, "pytest", None)
    with pytest.raises(CommandError, match="record_answers runs only in backend-dev"):
        call_command("record_answers", stdout=StringIO())


@pytest.mark.parametrize(
    ("ai_enabled", "model", "message"),
    [
        (False, "some-model", "TWOX_AI_ENABLED"),
        (True, "", "TWOX_CHAT_MODEL"),
    ],
    ids=["ai-off", "no-model"],
)
def test_record_answers_refuses_without_ai_or_model(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    network_lock: list[str],
    ai_enabled: bool,
    model: str,
    message: str,
) -> None:
    settings.TWOX_AI_ENABLED = ai_enabled
    settings.TWOX_CHAT_MODEL = model
    calls = _forbid_pytest_main(monkeypatch)
    monkeypatch.setenv(replay.RECORD_ENV, "0")
    with pytest.raises(CommandError, match=message):
        call_command("record_answers", stdout=StringIO())
    assert calls == []
    assert os.environ[replay.RECORD_ENV] == "0"


def test_record_answers_runs_this_module_with_the_switch(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, network_lock: list[str]
) -> None:
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_CHAT_MODEL = "some-model"
    seen: list[tuple[list[str], str | None]] = []

    def fake_main(args: list[str]) -> int:
        seen.append((args, os.environ.get(replay.RECORD_ENV)))
        return 1

    monkeypatch.setattr(pytest, "main", fake_main)
    monkeypatch.setenv(replay.RECORD_ENV, "0")
    with pytest.raises(CommandError, match="recording failed"):
        call_command("record_answers", stdout=StringIO())
    [(args, switch)] = seen
    assert switch == "1"
    assert args[0].endswith("tests/answers/test_ci_questions.py")
