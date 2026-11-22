"""Recorded model answers for the CI: replay and recording (M3, work order 135).

E-10 asks that the test questions run with every change. The CI has neither a
model nor a network, so the answers of the real chat model are recorded once,
locally, and replayed in the CI by :class:`ReplayChatModel`. Everything else
of the answer chain (context selection, prompt, citation check, refusal,
scope) runs for real in both cases.

Key
    :func:`recording_key` is the SHA-256 over :func:`~twox.answers.prompt.prompt_version`,
    the model name of the recording and the messages to the model, serialised
    canonically (``json.dumps(..., sort_keys=True, ensure_ascii=False)``).
    The messages hold the question, the source numbers and the section texts,
    so a changed prompt template, a changed context or another model gives
    another key. The identifier of the delimiters
    (:func:`~twox.answers.prompt.new_nonce`) is random per request; tests and
    recordings fix it with ``monkeypatch``, the product code has no switch
    for it.

Replay
    :meth:`ReplayChatModel.stream` looks the key up. Without an entry it
    raises :class:`RecordingMissingError`, whose message names the prompt
    version, the model and the question id (never a prompt or section text)
    and how to record again; there is no fallback to another entry. The
    answer service turns every exception of the model into
    ``error(internal)``, so the model also keeps the error in
    :attr:`ReplayChatModel.misses` for the test to raise.

Format
    :func:`dump_recording` writes a fixed layout (two spaces of indentation,
    keys in a fixed order, one line break at the end), so that a second
    recording with the same answers is byte-identical and the diff stays
    readable. Only the output of the model is stored (``chunks``), never a
    prompt or a section text; :func:`parse_recording` reads the file with the
    standard library only.

The module opens no connection and does not look at ``TWOX_AI_ENABLED``:
whether the model is asked is decided by the answer service.
"""

import hashlib
import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from twox.answers import prompt
from twox.answers.chat import ChatMessage, ChatModel, ChatStream

#: Version of the format of a recording file.
SCHEMA_VERSION: Final = 1
#: Environment variable that switches the CI question test to recording; set
#: only by ``manage.py record_answers`` and read only by that test.
RECORD_ENV: Final = "TWOX_RECORD_ANSWERS"
#: What to run to record again; part of every :class:`RecordingMissingError`.
RERECORD_HINT: Final = "re-record: manage.py record_answers"


class RecordingFormatError(ValueError):
    """A recording file is not valid; the message names the place."""


class RecordingMissingError(AssertionError):
    """There is no recorded answer for this prompt; the recording is out of date."""


@dataclass(frozen=True, slots=True)
class RecordedSource:
    """A source of the recorded prompt: its number and where its section comes from."""

    n: int
    sha256: str
    ordinal: int


@dataclass(frozen=True, slots=True)
class RecordingSettings:
    """The model parameters of a recording."""

    temperature: float
    seed: int
    max_tokens: int
    reasoning_effort: str | None


@dataclass(frozen=True, slots=True)
class RecordedEntry:
    """The answer of the model to one prompt."""

    question_id: str
    key: str
    sources: tuple[RecordedSource, ...]
    chunks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Recording:
    """A recording file: the model, its parameters and the answers."""

    model: str
    model_digest: str
    prompt_version: str
    recorded_on: str
    settings: RecordingSettings
    entries: tuple[RecordedEntry, ...]
    schema_version: int = SCHEMA_VERSION

    def entry_for(self, key: str) -> RecordedEntry | None:
        """The entry recorded under ``key``, or ``None``."""
        return next((entry for entry in self.entries if entry.key == key), None)


def canonical_messages(messages: Sequence[ChatMessage]) -> str:
    """``messages`` as canonical JSON: role and text only, keys sorted."""
    plain = [{"role": message["role"], "content": message["content"]} for message in messages]
    return json.dumps(plain, sort_keys=True, ensure_ascii=False)


def recording_key(messages: Sequence[ChatMessage], model_name: str) -> str:
    """The key of the answer to ``messages`` by ``model_name`` (see the module docstring)."""
    parts = (prompt.prompt_version(), model_name, canonical_messages(messages))
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()


def missing_message(model_name: str, question_id: str) -> str:
    """The message of :class:`RecordingMissingError`: identifiers only, no text."""
    return (
        f"no recording for this prompt (prompt_version={prompt.prompt_version()},"
        f" model={model_name}, question={question_id}); {RERECORD_HINT}"
    )


# --- Reading and writing ------------------------------------------------------------


def _object(value: object, where: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise RecordingFormatError(f"{where}: expected an object")
    return value


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise RecordingFormatError(f"{where}: expected non-empty text")
    return value


def _whole(value: object, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RecordingFormatError(f"{where}: expected a whole number")
    return value


def _number(value: object, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise RecordingFormatError(f"{where}: expected a number")
    return float(value)


def _list(value: object, where: str) -> list[object]:
    if not isinstance(value, list):
        raise RecordingFormatError(f"{where}: expected a list")
    return value


def _settings(value: object, where: str) -> RecordingSettings:
    data = _object(value, where)
    effort = data.get("reasoning_effort")
    if effort is not None and not isinstance(effort, str):
        raise RecordingFormatError(f"{where}.reasoning_effort: expected text or null")
    return RecordingSettings(
        temperature=_number(data.get("temperature"), f"{where}.temperature"),
        seed=_whole(data.get("seed"), f"{where}.seed"),
        max_tokens=_whole(data.get("max_tokens"), f"{where}.max_tokens"),
        reasoning_effort=effort,
    )


def _source(value: object, where: str) -> RecordedSource:
    data = _object(value, where)
    return RecordedSource(
        n=_whole(data.get("n"), f"{where}.n"),
        sha256=_text(data.get("sha256"), f"{where}.sha256"),
        ordinal=_whole(data.get("ordinal"), f"{where}.ordinal"),
    )


def _entry(value: object, where: str) -> RecordedEntry:
    data = _object(value, where)
    sources = _list(data.get("sources"), f"{where}.sources")
    chunks = _list(data.get("chunks"), f"{where}.chunks")
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, str):
            raise RecordingFormatError(f"{where}.chunks[{index}]: expected text")
    return RecordedEntry(
        question_id=_text(data.get("question_id"), f"{where}.question_id"),
        key=_text(data.get("key"), f"{where}.key"),
        sources=tuple(
            _source(item, f"{where}.sources[{index}]") for index, item in enumerate(sources)
        ),
        chunks=tuple(str(chunk) for chunk in chunks),
    )


def parse_recording(data: object) -> Recording:
    """The recording in ``data`` (parsed JSON); :class:`RecordingFormatError` if invalid."""
    top = _object(data, "recording")
    if top.get("schema_version") != SCHEMA_VERSION:
        raise RecordingFormatError(f"schema_version: expected {SCHEMA_VERSION}")
    entries = tuple(
        _entry(item, f"entries[{index}]")
        for index, item in enumerate(_list(top.get("entries"), "entries"))
    )
    keys = [entry.key for entry in entries]
    if len(set(keys)) != len(keys):
        raise RecordingFormatError("entries: a key occurs twice")
    return Recording(
        model=_text(top.get("model"), "model"),
        model_digest=_text(top.get("model_digest"), "model_digest"),
        prompt_version=_text(top.get("prompt_version"), "prompt_version"),
        recorded_on=_text(top.get("recorded_on"), "recorded_on"),
        settings=_settings(top.get("settings"), "settings"),
        entries=entries,
    )


def load_recording(text: str) -> Recording:
    """The recording in JSON ``text``; :class:`RecordingFormatError` if invalid."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise RecordingFormatError(
            f"not valid JSON (line {error.lineno}, column {error.colno}: {error.msg})"
        ) from None
    return parse_recording(data)


def dump_recording(recording: Recording) -> str:
    """``recording`` as JSON text in the fixed layout (see the module docstring)."""
    data = {
        "schema_version": recording.schema_version,
        "model": recording.model,
        "model_digest": recording.model_digest,
        "prompt_version": recording.prompt_version,
        "recorded_on": recording.recorded_on,
        "settings": {
            "temperature": recording.settings.temperature,
            "seed": recording.settings.seed,
            "max_tokens": recording.settings.max_tokens,
            "reasoning_effort": recording.settings.reasoning_effort,
        },
        "entries": [
            {
                "question_id": entry.question_id,
                "key": entry.key,
                "sources": [
                    {"n": source.n, "sha256": source.sha256, "ordinal": source.ordinal}
                    for source in entry.sources
                ],
                "chunks": list(entry.chunks),
            }
            for entry in recording.entries
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


# --- Chat models ----------------------------------------------------------------------


class ReplayChatModel:
    """A :class:`~twox.answers.chat.ChatModel` that plays recorded answers; no network.

    ``question_id`` names the question in the error message only; the entry
    is found by its key, and an entry recorded for another question counts
    as missing. Every returned stream is kept in :attr:`streams`, every
    :meth:`close` counted in :attr:`close_count`.
    """

    def __init__(self, recording: Recording, question_id: str) -> None:
        self.recording = recording
        self.question_id = question_id
        self.streams: list[ChatStream] = []
        self.misses: list[RecordingMissingError] = []
        self.close_count = 0
        #: The key of every call of :meth:`stream`, in order.
        self.keys: list[str] = []

    @property
    def requests(self) -> int:
        """How often :meth:`stream` was called."""
        return len(self.keys)

    @property
    def model_name(self) -> str:
        return self.recording.model

    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> ChatStream:
        """The recorded pieces of the answer to ``messages``, in the recorded order.

        Raises :class:`RecordingMissingError` when nothing is recorded for them.
        """
        key = recording_key(messages, self.model_name)
        self.keys.append(key)
        entry = self.recording.entry_for(key)
        if entry is None or entry.question_id != self.question_id:
            error = RecordingMissingError(missing_message(self.model_name, self.question_id))
            self.misses.append(error)
            raise error
        stream = ChatStream(iter(entry.chunks))
        self.streams.append(stream)
        return stream

    def close(self) -> None:
        self.close_count += 1
        for stream in self.streams:
            stream.close()


@dataclass(frozen=True, slots=True)
class RecordedCall:
    """One complete answer the recorder saw."""

    question_id: str
    key: str
    chunks: tuple[str, ...]


@dataclass
class RecordingChatModel:
    """Wraps a real :class:`~twox.answers.chat.ChatModel` and records its answers.

    Only an answer read to its end is recorded (in :attr:`calls`). A prompt
    asked again with the same key is answered from the first recording, so
    one recording run gives exactly one answer per prompt.
    """

    inner: ChatModel
    question_id: str
    calls: list[RecordedCall] = field(default_factory=list)
    #: Key -> pieces of every answer recorded so far; may be shared between instances.
    known: dict[str, tuple[str, ...]] = field(default_factory=dict)
    #: The key of every call of :meth:`stream`, in order.
    keys: list[str] = field(default_factory=list)

    @property
    def model_name(self) -> str:
        return self.inner.model_name

    @property
    def requests(self) -> int:
        """How often :meth:`stream` was called."""
        return len(self.keys)

    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> ChatStream:
        key = recording_key(messages, self.model_name)
        self.keys.append(key)
        if key in self.known:
            return ChatStream(iter(self.known[key]))
        inner = self.inner.stream(
            messages, max_tokens=max_tokens, temperature=temperature, seed=seed
        )
        return ChatStream(self._collect(key, inner), inner.close)

    def _collect(self, key: str, inner: ChatStream) -> Iterator[str]:
        pieces: list[str] = []
        for piece in inner:
            pieces.append(piece)
            yield piece
        self.known[key] = tuple(pieces)
        self.calls.append(RecordedCall(self.question_id, key, tuple(pieces)))

    def close(self) -> None:
        self.inner.close()
