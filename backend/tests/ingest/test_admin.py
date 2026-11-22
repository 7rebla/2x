"""Ingest jobs and sections in the admin: superusers only, read only (042)."""

from dataclasses import dataclass

import pytest
from django.contrib import admin
from django.test import Client
from django.utils import translation

from tests.accounts.users import make_user
from tests.files.helpers import make_device
from twox.files.models import Document, DocumentVersion
from twox.files.storage import key_for_sha256
from twox.ingest.models import EMBEDDING_DIMENSIONS, IngestJob, IngestStatus, Section

pytestmark = pytest.mark.django_db

PAGES = ["ingestjob", "section"]


@dataclass(frozen=True)
class Rows:
    job: IngestJob
    plain: Section
    embedded: Section


@pytest.fixture
def rows() -> Rows:
    sha256 = "ab" * 32
    document = Document.objects.create(device=make_device(), title="Pump manual")
    version = DocumentVersion.objects.create(
        document=document,
        number=1,
        blob_key=key_for_sha256(sha256),
        sha256=sha256,
        size=7,
        content_type="application/pdf",
        original_filename="manual.pdf",
    )
    job = IngestJob.objects.create(
        document_version=version, status=IngestStatus.DONE, section_count=2
    )
    plain = Section.objects.create(
        document_version=version,
        ingest_job=job,
        ordinal=1,
        heading_path=["Plain heading"],
        text="Text without embedding.",
    )
    embedded = Section.objects.create(
        document_version=version,
        ingest_job=job,
        ordinal=2,
        heading_path=["Embedded heading"],
        text="Text with embedding.",
        embedding=[0.25] * EMBEDDING_DIMENSIONS,
        embedding_model="bge-m3",
    )
    return Rows(job=job, plain=plain, embedded=embedded)


@pytest.fixture
def superuser_client() -> Client:
    client = Client()
    superuser = make_user("superuser")
    assert superuser is not None
    client.force_login(superuser)
    return client


def pk_of(rows: Rows, page: str) -> int:
    return rows.job.pk if page == "ingestjob" else rows.plain.pk


@pytest.mark.parametrize("model", [IngestJob, Section])
def test_models_are_registered(model: type[IngestJob | Section]) -> None:
    assert admin.site.is_registered(model)


@pytest.mark.parametrize("page", PAGES)
def test_superuser_can_list_and_view(rows: Rows, superuser_client: Client, page: str) -> None:
    listing = superuser_client.get(f"/admin/ingest/{page}/")
    detail = superuser_client.get(f"/admin/ingest/{page}/{pk_of(rows, page)}/change/")

    assert listing.status_code == 200
    assert detail.status_code == 200
    assert "Pump manual" in listing.content.decode()
    # View only: no save button.
    assert 'name="_save"' not in detail.content.decode()


@pytest.mark.parametrize("page", PAGES)
def test_nobody_adds_changes_or_deletes(rows: Rows, superuser_client: Client, page: str) -> None:
    pk = pk_of(rows, page)

    assert superuser_client.get(f"/admin/ingest/{page}/add/").status_code == 403
    assert (
        superuser_client.post(
            f"/admin/ingest/{page}/{pk}/change/", {"status": "failed"}
        ).status_code
        == 403
    )
    assert superuser_client.get(f"/admin/ingest/{page}/{pk}/delete/").status_code == 403
    assert (
        superuser_client.post(f"/admin/ingest/{page}/{pk}/delete/", {"post": "yes"}).status_code
        == 403
    )
    assert IngestJob.objects.get().status == IngestStatus.DONE
    assert Section.objects.count() == 2


@pytest.mark.parametrize("page", PAGES)
def test_list_has_no_bulk_delete(rows: Rows, superuser_client: Client, page: str) -> None:
    response = superuser_client.post(
        f"/admin/ingest/{page}/",
        {"action": "delete_selected", "_selected_action": [str(pk_of(rows, page))], "post": "yes"},
    )

    assert response.status_code in {200, 302}
    assert IngestJob.objects.count() == 1
    assert Section.objects.count() == 2


@pytest.mark.parametrize("kind", ["anonymous", "no_role", "read", "manage"])
@pytest.mark.parametrize("page", PAGES)
def test_roles_do_not_open_the_admin(rows: Rows, kind: str, page: str) -> None:
    client = Client()
    user = make_user(kind)
    if user is not None:
        client.force_login(user)

    response = client.get(f"/admin/ingest/{page}/")

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


def test_staff_without_superuser_flag_gets_no_access(rows: Rows) -> None:
    client = Client()
    staff = make_user("no_role")
    assert staff is not None
    staff.is_staff = True
    staff.save()
    client.force_login(staff)

    response = client.get("/admin/ingest/section/")

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


@pytest.mark.parametrize(
    ("query", "shown", "hidden"),
    [
        ("?embedding=no", "Plain heading", "Embedded heading"),
        ("?embedding=yes", "Embedded heading", "Plain heading"),
    ],
)
def test_sections_filter_by_embedding(
    rows: Rows, superuser_client: Client, query: str, shown: str, hidden: str
) -> None:
    content = superuser_client.get(f"/admin/ingest/section/{query}").content.decode()

    assert shown in content
    assert hidden not in content


def test_section_list_shows_both_without_filter(rows: Rows, superuser_client: Client) -> None:
    content = superuser_client.get("/admin/ingest/section/").content.decode()

    assert "Plain heading" in content
    assert "Embedded heading" in content
    # The boolean column: one section with, one without an embedding.
    assert "icon-yes.svg" in content
    assert "icon-no.svg" in content


def test_section_list_does_not_load_the_vectors(rows: Rows, superuser_client: Client) -> None:
    admin_class = admin.site.get_model_admin(Section)
    request = superuser_client.get("/admin/ingest/section/").wsgi_request

    queryset = admin_class.get_queryset(request)

    assert {"embedding", "search_vector"} <= queryset.query.deferred_loading[0]
    assert [s.embedding_present for s in queryset.order_by("ordinal")] == [False, True]  # type: ignore[attr-defined]


def test_labels_in_german() -> None:
    with translation.override("de"):
        assert str(IngestJob._meta.verbose_name_plural) == "Einlese-Aufträge"
        assert str(Section._meta.verbose_name_plural) == "Abschnitte"
        assert str(IngestStatus.QUEUED.label) == "wartet"
        assert str(Section._meta.get_field("embedding").verbose_name) == "Einbettung"
