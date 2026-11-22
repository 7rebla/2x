"""The management command ``embed_sections`` (work order 048).

The last tests check the field ``ingest`` of the files API (051) after an
embedding job, with the AI features on and off (work order 061).

The task ``twox.ingest.embed`` is recorded instead of sent; no test reaches a
broker or a model service (``isolated_services``).
"""

from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks, Settings
from rest_framework.test import APIClient

from tests.accounts.users import TEST_PASSWORD, make_user
from tests.files.helpers import client_for
from tests.ingest.fake_converter import (
    FAKE_MODEL,
    FakeEmbedder,
    add_sections,
    install_embedder,
    isolated_services,
    make_version,
    vector_for,
)
from twox.accounts.models import User
from twox.answers.embeddings import EmbeddingUnavailableError
from twox.files.models import DocumentVersion
from twox.files.storage import key_for_sha256
from twox.ingest import pipeline, tasks
from twox.ingest.docling import ConversionErrorItem
from twox.ingest.models import IngestErrorCode, IngestJob, IngestStatus, IngestStep, Section

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("isolated_services")]

# Imported for its side effect: pytest finds the fixture in this module.
__all__ = ["isolated_services"]


class SentEmbeds(list[int]):
    """Job IDs of the messages ``embed``, with their send options; ``error`` fails each send."""

    def __init__(self) -> None:
        super().__init__()
        self.options: list[dict[str, object]] = []
        self.error: Exception | None = None


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> SentEmbeds:
    """Messages ``embed``, recorded instead of sent to the broker."""
    record = SentEmbeds()

    def apply_async(args: tuple[int, ...], **options: object) -> None:
        if record.error is not None:
            raise record.error
        record.append(args[0])
        record.options.append(options)

    monkeypatch.setattr(tasks.embed, "apply_async", apply_async)
    return record


@pytest.fixture
def manager() -> User:
    user = make_user("manage")
    assert user is not None
    return user


@pytest.fixture
def ai_on(settings: Settings, isolated_services: Path) -> None:
    """AI features on; after ``isolated_services``, which switches them off."""
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_EMBED_MODEL = FAKE_MODEL


def run(*args: str) -> str:
    stdout = StringIO()
    call_command("embed_sections", *args, stdout=stdout)
    return stdout.getvalue()


def embed_all(version: DocumentVersion, model: str = FAKE_MODEL) -> None:
    Section.objects.filter(document_version=version).update(
        embedding=vector_for(0), embedding_model=model
    )


@pytest.fixture
def versions() -> dict[str, DocumentVersion]:
    """Four versions: complete, without embeddings, old model, partly embedded."""
    made = {
        "complete": make_version(b"complete", device="dps-plc"),
        "missing": make_version(b"missing", device="hbw-plc"),
        "old_model": make_version(b"old model", device="vgr-plc"),
        "partly": make_version(b"partly", device="mpo-plc"),
    }
    for version in made.values():
        add_sections(version, 3)
    embed_all(made["complete"])
    embed_all(made["old_model"], "old-model")
    Section.objects.filter(document_version=made["partly"], ordinal=0).update(
        embedding=vector_for(0), embedding_model=FAKE_MODEL
    )
    return made


def embed_jobs() -> list[IngestJob]:
    return list(IngestJob.objects.filter(step=IngestStep.EMBED).order_by("pk"))


@pytest.mark.usefixtures("ai_on")
def test_dry_run_counts_and_changes_nothing(
    versions: dict[str, DocumentVersion], manager: User, sent: SentEmbeds
) -> None:
    before = list(Section.objects.order_by("pk").values_list("pk", "embedding_model"))

    output = run("--user", manager.username)

    assert "versions: 3 jobs to create, 0 skipped (queued or running job)" in output
    # missing 3, old model 3, partly 2
    assert "sections: 8 to embed, 0 skipped" in output
    assert "Dry run: nothing was saved" in output
    assert embed_jobs() == []
    assert sent == []
    assert list(Section.objects.order_by("pk").values_list("pk", "embedding_model")) == before


@pytest.mark.usefixtures("ai_on")
def test_missing_creates_one_job_per_version_and_sends_embed_after_the_commit(
    versions: dict[str, DocumentVersion],
    manager: User,
    sent: SentEmbeds,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        output = run("--user", manager.username, "--missing", "--commit")

    jobs = embed_jobs()
    assert [job.document_version for job in jobs] == [
        versions["missing"],
        versions["old_model"],
        versions["partly"],
    ]
    assert all(
        (job.status, job.step, job.requested_by, job.section_count)
        == (IngestStatus.QUEUED, IngestStep.EMBED, manager, 3)
        for job in jobs
    )
    # One transaction, one callback after its commit that sends all messages.
    assert len(callbacks) == 1
    assert sent == [job.pk for job in jobs]
    # As send_convert of 049: no task result is kept.
    assert all(options["ignore_result"] is True for options in sent.options)
    assert "versions: 3 jobs created, 0 skipped (queued or running job)" in output
    assert "sections: 8 to embed, 0 skipped" in output
    # --missing keeps the embeddings that exist.
    assert Section.objects.filter(embedding_model=FAKE_MODEL).count() == 4


@pytest.mark.usefixtures("ai_on")
def test_versions_with_a_running_job_are_skipped_and_counted(
    versions: dict[str, DocumentVersion],
    manager: User,
    sent: SentEmbeds,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    IngestJob.objects.create(document_version=versions["missing"], status=IngestStatus.RUNNING)
    IngestJob.objects.create(document_version=versions["partly"], status=IngestStatus.QUEUED)

    with django_capture_on_commit_callbacks(execute=True):
        output = run("--user", manager.username, "--commit")

    assert "versions: 1 jobs created, 2 skipped (queued or running job)" in output
    assert "sections: 3 to embed, 5 skipped" in output
    assert [job.document_version for job in embed_jobs()] == [versions["old_model"]]
    assert len(sent) == 1


@pytest.mark.usefixtures("ai_on")
def test_all_takes_every_version_and_clears_its_embeddings(
    versions: dict[str, DocumentVersion],
    manager: User,
    sent: SentEmbeds,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        output = run("--user", manager.username, "--all", "--commit")

    assert "versions: 4 jobs created, 0 skipped" in output
    assert "sections: 12 to embed, 0 skipped" in output
    assert len(embed_jobs()) == len(sent) == 4
    assert not Section.objects.filter(embedding__isnull=False).exists()


@pytest.mark.usefixtures("ai_on")
def test_all_as_dry_run_keeps_the_embeddings(
    versions: dict[str, DocumentVersion], manager: User, sent: SentEmbeds
) -> None:
    output = run("--user", manager.username, "--all")

    assert "versions: 4 jobs to create" in output
    assert Section.objects.filter(embedding__isnull=False).count() == 7
    assert embed_jobs() == []


def test_created_jobs_are_embedded_by_the_task(
    versions: dict[str, DocumentVersion],
    manager: User,
    sent: SentEmbeds,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    embedder = install_embedder(monkeypatch, settings)

    with django_capture_on_commit_callbacks(execute=True):
        run("--user", manager.username, "--commit")
    for job_id in sent:
        assert pipeline.embed(job_id).outcome == pipeline.Outcome.DONE

    assert len(embedder.texts) == 8
    assert not Section.objects.exclude(embedding_model=FAKE_MODEL).exists()
    assert {job.status for job in embed_jobs()} == {IngestStatus.DONE}
    # Nothing left: a second run creates nothing.
    assert "versions: 0 jobs to create" in run("--user", manager.username)


@pytest.mark.usefixtures("ai_on")
@pytest.mark.parametrize("kind", ["read", "no_role"])
def test_account_without_manage_is_refused(
    versions: dict[str, DocumentVersion], sent: SentEmbeds, kind: str
) -> None:
    user = make_user(kind)
    assert user is not None

    with pytest.raises(CommandError, match="does not have the role 'manage'"):
        run("--user", user.username, "--commit")

    assert embed_jobs() == []
    assert sent == []


@pytest.mark.usefixtures("ai_on")
def test_unknown_or_inactive_account_is_refused(manager: User, sent: SentEmbeds) -> None:
    with pytest.raises(CommandError, match="no active account 'nobody'"):
        run("--user", "nobody", "--commit")
    manager.is_active = False
    manager.save()
    with pytest.raises(CommandError, match="no active account"):
        run("--user", manager.username, "--commit")


@pytest.mark.usefixtures("ai_on")
def test_user_is_required_and_missing_and_all_exclude_each_other(manager: User) -> None:
    with pytest.raises(CommandError, match="--user"):
        run("--commit")
    with pytest.raises(CommandError, match="not allowed with argument"):
        run("--user", manager.username, "--missing", "--all")


def test_ai_off_creates_nothing_and_says_so(
    versions: dict[str, DocumentVersion], manager: User, sent: SentEmbeds, settings: Settings
) -> None:
    # E-59: no embedding task without AI; a neutral message, exit code 0.
    settings.TWOX_AI_ENABLED = False

    output = run("--user", manager.username, "--commit")

    assert output.strip() == (
        "DISABLED: AI features are not enabled (TWOX_AI_ENABLED is false); nothing was embedded"
    )
    assert embed_jobs() == []
    assert sent == []


@pytest.mark.usefixtures("ai_on")
def test_a_message_that_cannot_be_sent_leaves_its_job_queued_with_a_warning(
    versions: dict[str, DocumentVersion],
    manager: User,
    sent: SentEmbeds,
    caplog: pytest.LogCaptureFixture,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    sent.error = ConnectionError("broker down")

    with (
        caplog.at_level("WARNING", logger="twox.ingest.management.commands.embed_sections"),
        django_capture_on_commit_callbacks(execute=True),
    ):
        run("--user", manager.username, "--commit")

    assert sent == []
    assert {job.status for job in embed_jobs()} == {IngestStatus.QUEUED}
    assert len(embed_jobs()) == 3
    assert caplog.text.count("could not be sent to the task queue and stays queued") == 3
    assert "ingest_versions --stuck" in caplog.text


@pytest.mark.django_db(transaction=True)
def test_all_computes_again_for_two_versions_of_the_same_content(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Review of 048: with the embeddings cleared version by version and each
    # message sent at once, the first job took over the old vectors of the
    # other version (same content, same model) and nothing was computed.
    first = make_version(b"same manual", device="dps-plc")
    second = make_version(b"same manual", device="hbw-plc", filename="copy.pdf")
    for version in (first, second):
        add_sections(version, 3)
        embed_all(version, FAKE_MODEL)
    Section.objects.update(embedding=vector_for(999))
    # A superuser has the role manage without the groups of the data
    # migration, which an earlier test with transaction=True may have flushed.
    admin = User.objects.create_superuser(username="admin-048", password=TEST_PASSWORD)
    embedder = install_embedder(monkeypatch, settings)
    # A fast worker: every message is worked off as soon as it is sent.
    monkeypatch.setattr(tasks.embed, "apply_async", lambda args, **options: pipeline.embed(args[0]))

    output = run("--user", admin.username, "--all", "--commit")

    assert "versions: 2 jobs created" in output
    # The model was asked for the first version; the second took that over.
    assert len(embedder.texts) == 3
    vectors = [list(map(float, section.embedding)) for section in Section.objects.all()]
    assert len(vectors) == 6
    assert vector_for(999) not in vectors
    assert {job.status for job in embed_jobs()} == {IngestStatus.DONE}


# --- the field ingest of the files API after an embedding job (work order 061) ---

#: A partial-conversion note exactly as the ingest flow writes it (046).
PARTIAL_NOTE = pipeline._partial_detail(
    (ConversionErrorItem(component_type="model", module_name="ocr", error_message="x", page_no=3),)
)

#: Fields of ``ingest`` in which an embedding job shows its conversion as before.
CONVERSION_FIELDS = ("partly_converted", "page_count", "section_count", "error_detail")


@pytest.fixture(params=[True, False], ids=["ai_on", "ai_off"])
def embedder(
    request: pytest.FixtureRequest,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    isolated_services: Path,
) -> FakeEmbedder | None:
    """The embedding stand-in with the AI features on; ``None`` with them off (E-59)."""
    if request.param:
        return install_embedder(monkeypatch, settings)
    return None


def converted(
    version: DocumentVersion, *, pages: int | None, detail: str = "", sections: int = 3
) -> IngestJob:
    """A finished conversion of ``version`` with a stored answer, as the ingest flow leaves it.

    With ``sections=0`` the version keeps the sections it has.
    """
    if sections:
        job = add_sections(version, sections)
    else:
        job = IngestJob.objects.create(
            document_version=version, status=IngestStatus.DONE, step=IngestStep.SECTIONS
        )
    IngestJob.objects.filter(pk=job.pk).update(
        page_count=pages,
        error_detail=detail,
        section_count=Section.objects.filter(document_version=version).count(),
        result_blob_key=key_for_sha256(version.sha256),
    )
    return job


def ingest_state(client: APIClient, version: DocumentVersion) -> dict[str, Any]:
    """The field ``ingest`` of the newest version in the document detail (051)."""
    response = client.get(f"/api/v1/documents/{version.document_id}/")
    assert response.status_code == 200
    state: dict[str, Any] = response.json()["latest_version"]["ingest"]
    return state


def embed_with_command(
    client: APIClient,
    version: DocumentVersion,
    manager: User,
    sent: SentEmbeds,
    capture: DjangoCaptureOnCommitCallbacks,
    *,
    ai: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run ``embed_sections --commit``, then the task as the worker would.

    Returns the field ``ingest`` after the command and after the worker.
    """
    with capture(execute=True):
        output = run("--user", manager.username, "--commit")
    queued = ingest_state(client, version)
    if not ai:
        assert output.startswith("DISABLED:")
        assert sent == []
        return queued, ingest_state(client, version)
    [job_id] = sent
    for _ in range(20):
        if pipeline.embed(job_id).embed_after is None:
            break
    else:
        pytest.fail("the embedding job never ended")
    return queued, ingest_state(client, version)


def same_conversion(state: dict[str, Any], before: dict[str, Any]) -> bool:
    return all(state[name] == before[name] for name in CONVERSION_FIELDS)


def test_embedding_after_a_partial_conversion_keeps_the_note_and_the_pages(
    embedder: FakeEmbedder | None,
    manager: User,
    sent: SentEmbeds,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    version = make_version(b"partly converted")
    conversion = converted(version, pages=60, detail=PARTIAL_NOTE)
    client = client_for("read")
    before = ingest_state(client, version)
    assert (before["id"], before["status"]) == (conversion.pk, "done")
    assert (before["partly_converted"], before["page_count"]) == (True, 60)

    queued, done = embed_with_command(
        client, version, manager, sent, django_capture_on_commit_callbacks, ai=embedder is not None
    )

    if embedder is None:
        # E-59: no embedding job; nothing changes.
        assert queued == done == before
        return
    [job] = embed_jobs()
    assert (job.page_count, job.error_detail) == (60, PARTIAL_NOTE)
    assert (queued["id"], queued["status"], queued["step"]) == (job.pk, "queued", "embed")
    assert (queued["page_count"], queued["error_detail"]) == (60, PARTIAL_NOTE)
    assert (done["id"], done["status"], done["step"]) == (job.pk, "done", "embed")
    assert same_conversion(done, before)
    assert done["partly_converted"] is True
    assert len(embedder.texts) == 3


def test_embedding_after_a_complete_conversion_shows_no_note(
    embedder: FakeEmbedder | None,
    manager: User,
    sent: SentEmbeds,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    version = make_version(b"converted twice")
    # An older partial conversion, a newer complete one: the newer one counts.
    converted(version, pages=59, detail=PARTIAL_NOTE)
    converted(version, pages=60, sections=0)
    # Neither a failed conversion nor a skipped job is a finished conversion.
    IngestJob.objects.create(
        document_version=version,
        status=IngestStatus.FAILED,
        step=IngestStep.CONVERT,
        error_code=IngestErrorCode.DOCLING_UNAVAILABLE,
        error_detail="docling-serve refused the connection",
        page_count=7,
    )
    client = client_for("read")
    before = ingest_state(client, version)

    queued, done = embed_with_command(
        client, version, manager, sent, django_capture_on_commit_callbacks, ai=embedder is not None
    )

    if embedder is None:
        assert queued == done == before
        assert before["status"] == "failed"
        return
    [job] = embed_jobs()
    assert (job.page_count, job.error_detail) == (60, "")
    assert (done["id"], done["status"], done["error_code"]) == (job.pk, "done", "")
    assert (done["page_count"], done["section_count"]) == (60, 3)
    assert (done["error_detail"], done["partly_converted"]) == ("", False)


def test_failed_embedding_shows_as_failed_embedding_with_its_sections(
    embedder: FakeEmbedder | None,
    manager: User,
    sent: SentEmbeds,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    version = make_version(b"model service down")
    converted(version, pages=60, detail=PARTIAL_NOTE)
    if embedder is not None:
        # Unreachable every time: the job fails once the retries are used up.
        embedder.errors = [EmbeddingUnavailableError("no answer from the model service")] * 20
    client = client_for("read")
    before = ingest_state(client, version)

    queued, done = embed_with_command(
        client, version, manager, sent, django_capture_on_commit_callbacks, ai=embedder is not None
    )

    if embedder is None:
        assert queued == done == before
        assert Section.objects.filter(document_version=version).count() == 3
        return
    [job] = embed_jobs()
    assert done["id"] == job.pk
    # Not a failed ingest: the step and the code name the embedding.
    assert (done["status"], done["step"]) == ("failed", "embed")
    assert done["error_code"] == "embedding_unavailable"
    assert "gave up after" in done["error_detail"]
    assert done["partly_converted"] is False
    # The sections are there; the keyword search keeps working (E-59).
    assert (done["section_count"], done["page_count"]) == (3, 60)
    assert Section.objects.filter(document_version=version).count() == 3
    assert not Section.objects.filter(embedding__isnull=False).exists()
    assert embedder.texts == []
