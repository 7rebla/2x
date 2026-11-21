"""Documents and versions in the admin: superusers only, read only."""

from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from tests.files.helpers import make_device
from twox.accounts.models import User
from twox.files.models import Document, DocumentKind, DocumentVersion
from twox.files.services import create_document

pytestmark = pytest.mark.django_db

TEST_PASSWORD = "files-admin-test-only-password"


@pytest.fixture
def version(media_root: Path) -> DocumentVersion:
    upload = SimpleUploadedFile("manual.pdf", b"content", content_type="application/pdf")
    return create_document(make_device(), upload, "Manual", DocumentKind.DOCUMENT, None).version


def superuser_client() -> Client:
    client = Client()
    client.force_login(User.objects.create_superuser(username="root", password=TEST_PASSWORD))
    return client


@pytest.mark.parametrize("model", ["document", "documentversion"])
def test_superuser_can_list_and_view(version: DocumentVersion, model: str) -> None:
    client = superuser_client()
    pk = version.document.pk if model == "document" else version.pk

    listing = client.get(f"/admin/files/{model}/")
    detail = client.get(f"/admin/files/{model}/{pk}/change/")

    assert listing.status_code == 200
    assert detail.status_code == 200
    assert "Manual" in listing.content.decode()
    # View only: no save button.
    assert 'name="_save"' not in detail.content.decode()


@pytest.mark.parametrize("model", ["document", "documentversion"])
def test_nobody_adds_changes_or_deletes(version: DocumentVersion, model: str) -> None:
    client = superuser_client()
    pk = version.document.pk if model == "document" else version.pk

    assert client.get(f"/admin/files/{model}/add/").status_code == 403
    assert client.post(f"/admin/files/{model}/{pk}/change/", {"title": "x"}).status_code == 403
    assert client.get(f"/admin/files/{model}/{pk}/delete/").status_code == 403
    assert Document.objects.get().title == "Manual"
    assert DocumentVersion.objects.count() == 1


def test_staff_without_superuser_flag_gets_no_access(version: DocumentVersion) -> None:
    client = Client()
    client.force_login(
        User.objects.create_user(username="staff", password=TEST_PASSWORD, is_staff=True)
    )

    response = client.get("/admin/files/document/")

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")
