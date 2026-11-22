"""The management command ``embed_sections`` (work order 048).

The task ``twox.ingest.embed`` is recorded instead of sent; no test reaches a
broker or a model service (``isolated_services``).
"""

from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks, Settings

from tests.accounts.users import make_user
from tests.ingest.fake_converter import (
    FAKE_MODEL,
    add_sections,
    install_embedder,
    isolated_services,
    make_version,
    vector_for,
)
from twox.accounts.models import User
from twox.files.models import DocumentVersion
from twox.ingest import pipeline, tasks
from twox.ingest.models import IngestJob, IngestStatus, IngestStep, Section

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("isolated_services")]

# Imported for its side effect: pytest finds the fixture in this module.
__all__ = ["isolated_services"]


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Job IDs given to ``embed.delay``, recorded instead of sent."""
    record: list[int] = []
    monkeypatch.setattr(tasks.embed, "delay", record.append)
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
    versions: dict[str, DocumentVersion], manager: User, sent: list[int]
) -> None:
    before = list(Section.objects.order_by("pk").values_list("pk", "embedding_model"))

    output = run("--user", manager.username)

    assert "versions: 3 to create, 0 skipped (queued or running job)" in output
    # missing 3, old model 3, partly 2
    assert "sections: 8 to create, 0 skipped" in output
    assert "Dry run: nothing was saved" in output
    assert embed_jobs() == []
    assert sent == []
    assert list(Section.objects.order_by("pk").values_list("pk", "embedding_model")) == before


@pytest.mark.usefixtures("ai_on")
def test_missing_creates_one_job_per_version_and_sends_embed_after_the_commit(
    versions: dict[str, DocumentVersion],
    manager: User,
    sent: list[int],
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
    assert len(callbacks) == 3
    assert sent == [job.pk for job in jobs]
    assert "versions: 3 created, 0 skipped (queued or running job)" in output
    assert "sections: 8 created, 0 skipped" in output
    # --missing keeps the embeddings that exist.
    assert Section.objects.filter(embedding_model=FAKE_MODEL).count() == 4


@pytest.mark.usefixtures("ai_on")
def test_versions_with_a_running_job_are_skipped_and_counted(
    versions: dict[str, DocumentVersion],
    manager: User,
    sent: list[int],
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    IngestJob.objects.create(document_version=versions["missing"], status=IngestStatus.RUNNING)
    IngestJob.objects.create(document_version=versions["partly"], status=IngestStatus.QUEUED)

    with django_capture_on_commit_callbacks(execute=True):
        output = run("--user", manager.username, "--commit")

    assert "versions: 1 created, 2 skipped (queued or running job)" in output
    assert "sections: 3 created, 5 skipped" in output
    assert [job.document_version for job in embed_jobs()] == [versions["old_model"]]
    assert len(sent) == 1


@pytest.mark.usefixtures("ai_on")
def test_all_takes_every_version_and_clears_its_embeddings(
    versions: dict[str, DocumentVersion],
    manager: User,
    sent: list[int],
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        output = run("--user", manager.username, "--all", "--commit")

    assert "versions: 4 created, 0 skipped" in output
    assert "sections: 12 created, 0 skipped" in output
    assert len(embed_jobs()) == len(sent) == 4
    assert not Section.objects.filter(embedding__isnull=False).exists()


@pytest.mark.usefixtures("ai_on")
def test_all_as_dry_run_keeps_the_embeddings(
    versions: dict[str, DocumentVersion], manager: User, sent: list[int]
) -> None:
    output = run("--user", manager.username, "--all")

    assert "versions: 4 to create" in output
    assert Section.objects.filter(embedding__isnull=False).count() == 7
    assert embed_jobs() == []


def test_created_jobs_are_embedded_by_the_task(
    versions: dict[str, DocumentVersion],
    manager: User,
    sent: list[int],
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
    assert "versions: 0 to create" in run("--user", manager.username)


@pytest.mark.usefixtures("ai_on")
@pytest.mark.parametrize("kind", ["read", "no_role"])
def test_account_without_manage_is_refused(
    versions: dict[str, DocumentVersion], sent: list[int], kind: str
) -> None:
    user = make_user(kind)
    assert user is not None

    with pytest.raises(CommandError, match="does not have the role 'manage'"):
        run("--user", user.username, "--commit")

    assert embed_jobs() == []
    assert sent == []


@pytest.mark.usefixtures("ai_on")
def test_unknown_or_inactive_account_is_refused(manager: User, sent: list[int]) -> None:
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
    versions: dict[str, DocumentVersion], manager: User, sent: list[int], settings: Settings
) -> None:
    # E-59: no embedding task without AI; a neutral message, exit code 0.
    settings.TWOX_AI_ENABLED = False

    output = run("--user", manager.username, "--commit")

    assert output.strip() == (
        "DISABLED: AI features are not enabled (TWOX_AI_ENABLED is false); nothing was embedded"
    )
    assert embed_jobs() == []
    assert sent == []
