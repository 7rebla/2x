"""The change log (E-43): who changed what and when, read-only in admin and API."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
import yaml
from auditlog.models import LogEntry
from auditlog.registry import auditlog
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db.models import Model, QuerySet
from django.test import Client, RequestFactory
from pytest_django import DjangoAssertNumQueries
from pytest_django.fixtures import Settings
from rest_framework.test import APIClient

from tests.accounts.users import KINDS, TEST_PASSWORD, make_user
from twox.accounts.admin import AuditLogEntryAdmin
from twox.accounts.audit import AUDITED_MODELS, acting_as
from twox.accounts.management.commands.create_account import PASSWORD_VARIABLE
from twox.accounts.models import User
from twox.assets.models import Area, Device, Plant, Site
from twox.files.models import Document, DocumentKind, DocumentVersion, VersionImmutableError
from twox.files.services import add_version, create_document

pytestmark = pytest.mark.django_db

URL = "/api/v1/audit-log/"
PAGE_SIZE = 50
SHA256 = "ab" * 32
CREATE = LogEntry.Action.CREATE
UPDATE = LogEntry.Action.UPDATE
DELETE = LogEntry.Action.DELETE

# Recognisable test values for create_account (at least 12 characters).
FIRST_PASSWORD = "audit-test-only-first"
SECOND_PASSWORD = "audit-test-only-second"


# --- helpers ---------------------------------------------------------------


def make_site(name: str = "North") -> Site:
    return Site.objects.create(name=name)


def make_area() -> Area:
    return Area.objects.create(site=make_site(), name="Line 1")


def make_plant() -> Plant:
    return Plant.objects.create(area=make_area(), key="press", name="Press")


def make_device() -> Device:
    return Device.objects.create(plant=make_plant(), key="press-plc", name="Press PLC")


def make_document() -> Document:
    return Document.objects.create(device=make_device(), title="Manual")


def make_version() -> DocumentVersion:
    return DocumentVersion.objects.create(
        document=make_document(),
        number=1,
        blob_key=f"sha256/ab/ab/{SHA256}",
        sha256=SHA256,
        size=3,
        content_type="application/pdf",
        original_filename="manual.pdf",
    )


def make_account() -> User:
    return User.objects.create_user(username="operator", password=TEST_PASSWORD)


def make_actor(username: str = "actor") -> User:
    return User.objects.create_user(username=username, password=TEST_PASSWORD)


def entries_for(obj: Model) -> QuerySet[LogEntry]:
    """The entries of ``obj``, oldest first."""
    return LogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk
    ).order_by("pk")


def changes_of(entry: LogEntry) -> dict[str, Any]:
    changes: dict[str, Any] | None = entry.changes
    assert changes is not None
    return changes


def entry_text(entries: QuerySet[LogEntry]) -> str:
    """Every column of the entries as one text, to search for values that must not be there."""
    return json.dumps(list(entries.values()), default=str)


def upload(content: bytes) -> SimpleUploadedFile:
    return SimpleUploadedFile("manual.pdf", content, content_type="application/pdf")


def run_create_account(monkeypatch: pytest.MonkeyPatch, password: str, *args: str) -> None:
    monkeypatch.setenv(PASSWORD_VARIABLE, password)
    call_command("create_account", *args, stdout=StringIO(), stderr=StringIO())


def signed_in(user: User | None, **defaults: str) -> APIClient:
    client = APIClient()
    # Values for the WSGI environment of every request, for example REMOTE_ADDR.
    client.defaults.update(defaults)
    if user is not None:
        client.force_login(user)
    return client


def manager_client() -> APIClient:
    return signed_in(make_user("manage"))


# --- registration ----------------------------------------------------------


def test_exactly_structure_files_and_users_are_logged() -> None:
    assert set(auditlog.get_models()) == {
        Site,
        Area,
        Plant,
        Device,
        Document,
        DocumentVersion,
        User,
    }
    assert set(AUDITED_MODELS) == set(auditlog.get_models())


def test_users_are_logged_without_password_and_last_login_with_groups() -> None:
    fields = auditlog.get_model_fields(User)

    assert {"password", "last_login"} <= set(fields["exclude_fields"])
    assert "username" in fields["include_fields"]
    assert "groups" in auditlog._registry[User]["m2m_fields"]


# --- every registered model ------------------------------------------------


@dataclass(frozen=True)
class Case:
    """How to make an object of a model and which field to change."""

    model: type[Model]
    make: Callable[[], Model]
    field: str
    old: Any
    new: Any


CASES = [
    Case(Site, make_site, "name", "North", "North site"),
    Case(Area, make_area, "name", "Line 1", "Line 2"),
    Case(Plant, make_plant, "name", "Press", "Press 2"),
    Case(Device, make_device, "name", "Press PLC", "Press controller"),
    Case(Document, make_document, "title", "Manual", "Operating manual"),
    Case(User, make_account, "is_active", True, False),
]
CREATE_CASES = [
    *CASES,
    Case(DocumentVersion, make_version, "number", None, 1),
]


def case_id(case: Case) -> str:
    return case.model.__name__


def test_cases_cover_every_logged_model() -> None:
    assert {case.model for case in CREATE_CASES} == set(AUDITED_MODELS)


@pytest.mark.parametrize("case", CREATE_CASES, ids=case_id)
def test_create_gives_one_entry_with_actor_and_fields(case: Case) -> None:
    actor = make_actor()

    with acting_as(actor):
        obj = case.make()

    (entry,) = entries_for(obj)
    assert entry.action == CREATE
    assert entry.actor == actor
    assert entry.object_id == obj.pk
    assert entry.object_repr == str(obj)
    assert changes_of(entry)["id"] == [None, obj.pk]
    assert case.field in changes_of(entry)
    # Only own columns: no reverse relations such as the devices of a plant.
    own_fields = {field.name for field in case.model._meta.concrete_fields}
    assert set(changes_of(entry)) <= own_fields


@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_update_gives_one_entry_with_actor_and_old_and_new_value(case: Case) -> None:
    obj = case.make()
    actor = make_actor()
    assert getattr(obj, case.field) == case.old

    setattr(obj, case.field, case.new)
    with acting_as(actor):
        obj.save()

    (entry,) = entries_for(obj).filter(action=UPDATE)
    assert entry.actor == actor
    assert changes_of(entry) == {case.field: [case.old, case.new]}


def test_empty_value_is_null_not_the_text_none() -> None:
    device = make_device()
    device.ip_address = "192.0.2.10"
    device.save()
    device.ip_address = None
    device.save()

    updates = entries_for(device).filter(action=UPDATE)
    assert [changes_of(entry) for entry in updates] == [
        {"ip_address": [None, "192.0.2.10"]},
        {"ip_address": ["192.0.2.10", None]},
    ]


def test_saving_without_a_change_gives_no_entry() -> None:
    site = make_site()

    site.save()

    assert entries_for(site).filter(action=UPDATE).count() == 0


def test_version_cannot_change_and_so_gives_no_update_entry() -> None:
    version = make_version()
    version.original_filename = "other.pdf"

    with pytest.raises(VersionImmutableError):
        version.save()

    assert [entry.action for entry in entries_for(version)] == [CREATE]


def test_delete_gives_an_entry_with_the_old_values() -> None:
    site = make_site()
    site_id = site.pk
    actor = make_actor()

    with acting_as(actor):
        site.delete()

    entry = LogEntry.objects.get(
        content_type=ContentType.objects.get_for_model(Site), object_id=site_id, action=DELETE
    )
    assert entry.actor == actor
    assert changes_of(entry)["name"] == ["North", None]


def test_change_outside_a_request_without_acting_as_has_no_actor() -> None:
    site = make_site()

    (entry,) = entries_for(site)
    assert entry.actor is None


def test_acting_as_restores_the_actor_around_it() -> None:
    outer = make_actor("outer")
    inner = make_actor("inner")

    with acting_as(outer):
        before = make_site("Before")
        with acting_as(inner):
            during = make_site("During")
        after = make_site("After")
    outside = make_site("Outside")

    assert [entries_for(site).get().actor for site in (before, during, after)] == [
        outer,
        inner,
        outer,
    ]
    assert entries_for(outside).get().actor is None


# --- through the API, the file service and create_account ------------------


def test_device_create_and_change_through_the_api_name_the_signed_in_user() -> None:
    plant = make_plant()
    manager = make_user("manage")
    assert manager is not None
    client = signed_in(manager)

    created = client.post(
        "/api/v1/devices/",
        {"plant": plant.pk, "key": "press-hmi", "name": "Press HMI"},
        format="json",
    )
    assert created.status_code == 201
    device_id = created.json()["id"]
    changed = client.patch(f"/api/v1/devices/{device_id}/", {"name": "Press panel"}, format="json")
    assert changed.status_code == 200

    entries = entries_for(Device.objects.get(pk=device_id))
    assert [(entry.action, entry.actor) for entry in entries] == [
        (CREATE, manager),
        (UPDATE, manager),
    ]
    assert changes_of(entries[0])["key"] == [None, "press-hmi"]
    assert changes_of(entries[1]) == {"name": ["Press HMI", "Press panel"]}


def test_second_version_through_the_service_in_acting_as_names_the_actor(
    tmp_path: Path, settings: Settings
) -> None:
    settings.TWOX_MEDIA_ROOT = tmp_path
    uploader = make_actor("uploader")
    device = make_device()

    with acting_as(uploader):
        first = create_document(device, upload(b"first"), "Manual", DocumentKind.DOCUMENT, uploader)
        second = add_version(first.document, upload(b"second"), uploader)

    (entry,) = entries_for(second.version)
    assert entry.action == CREATE
    assert entry.actor == uploader
    assert changes_of(entry)["number"] == [None, 2]
    assert changes_of(entry)["uploaded_by"] == [None, uploader.pk]
    assert entries_for(first.document).get().actor == uploader


def test_role_change_through_create_account_is_logged(monkeypatch: pytest.MonkeyPatch) -> None:
    run_create_account(monkeypatch, FIRST_PASSWORD, "operator", "--role", "read")
    user = User.objects.get(username="operator")
    before = set(entries_for(user).values_list("pk", flat=True))

    run_create_account(monkeypatch, SECOND_PASSWORD, "operator", "--role", "manage", "--update")

    new_entries = entries_for(user).exclude(pk__in=before)
    assert [(entry.action, changes_of(entry)) for entry in new_entries] == [
        (UPDATE, {"groups": {"type": "m2m", "operation": "delete", "objects": ["read"]}}),
        (UPDATE, {"groups": {"type": "m2m", "operation": "add", "objects": ["manage"]}}),
    ]


def test_update_with_the_same_role_gives_no_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    run_create_account(monkeypatch, FIRST_PASSWORD, "operator", "--role", "read")
    user = User.objects.get(username="operator")
    before = entries_for(user).count()

    # Only the password changes; it is not logged.
    run_create_account(monkeypatch, SECOND_PASSWORD, "operator", "--role", "read", "--update")

    assert entries_for(user).count() == before


def test_no_entry_contains_a_password_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    run_create_account(monkeypatch, FIRST_PASSWORD, "operator", "--role", "read")
    first_hash = User.objects.get(username="operator").password
    run_create_account(monkeypatch, SECOND_PASSWORD, "operator", "--role", "manage", "--update")
    user = User.objects.get(username="operator")
    user.set_password(TEST_PASSWORD)
    user.is_staff = True
    user.save()
    superuser = make_user("superuser")
    assert superuser is not None
    signed_in(superuser).get("/api/v1/me/")  # a sign-in sets last_login

    entries = LogEntry.objects.all()
    text = entry_text(entries)
    for secret in (first_hash, user.password, superuser.password):
        assert secret not in text
    for password in (FIRST_PASSWORD, SECOND_PASSWORD, TEST_PASSWORD):
        assert password not in text
    for entry in entries:
        assert "password" not in changes_of(entry)
        assert "last_login" not in changes_of(entry)
        assert entry.serialized_data is None
        assert entry.additional_data is None
    assert entries_for(user).filter(action=UPDATE, changes__has_key="is_staff").count() == 1


def test_no_ip_address_and_no_session_is_stored() -> None:
    manager = make_user("manage")
    assert manager is not None
    client = signed_in(
        manager,
        REMOTE_ADDR="198.51.100.23",
        HTTP_X_FORWARDED_FOR="203.0.113.5, 198.51.100.23",
    )

    response = client.post("/api/v1/sites/", {"name": "West"}, format="json")

    assert response.status_code == 201
    (entry,) = entries_for(Site.objects.get(pk=response.json()["id"]))
    assert entry.actor == manager
    assert entry.remote_addr is None
    assert not LogEntry.objects.exclude(remote_addr=None).exists()
    text = entry_text(LogEntry.objects.all())
    assert "198.51.100.23" not in text
    assert "203.0.113.5" not in text
    session_key = client.cookies["sessionid"].value
    assert session_key
    assert session_key not in text


# --- admin -----------------------------------------------------------------


def superuser_client() -> tuple[Client, User]:
    superuser = make_user("superuser")
    assert superuser is not None
    client = Client()
    client.force_login(superuser)
    return client, superuser


def test_admin_shows_the_own_read_only_view() -> None:
    assert isinstance(admin.site.get_model_admin(LogEntry), AuditLogEntryAdmin)


def test_admin_permissions_are_all_false_except_viewing() -> None:
    _, superuser = superuser_client()
    request = RequestFactory().get("/admin/auditlog/logentry/")
    request.user = superuser
    model_admin = admin.site.get_model_admin(LogEntry)
    entry = entries_for(make_site()).get()

    assert model_admin.has_view_permission(request, entry) is True
    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_change_permission(request, entry) is False
    assert model_admin.has_delete_permission(request, entry) is False
    assert "delete_selected" not in model_admin.get_actions(request)


def test_superuser_reads_the_log_in_the_admin() -> None:
    client, _ = superuser_client()
    entry = entries_for(make_site("Readable site")).get()

    listing = client.get("/admin/auditlog/logentry/")
    detail = client.get(f"/admin/auditlog/logentry/{entry.pk}/change/")

    assert listing.status_code == 200
    assert b"Readable site" in listing.content
    assert detail.status_code == 200
    assert detail.context["has_change_permission"] is False


def test_superuser_cannot_add_change_or_delete_in_the_admin() -> None:
    client, _ = superuser_client()
    entry = entries_for(make_site()).get()
    count = LogEntry.objects.count()

    assert client.get("/admin/auditlog/logentry/add/").status_code == 403
    assert client.post("/admin/auditlog/logentry/add/", {}).status_code == 403
    changed = client.post(
        f"/admin/auditlog/logentry/{entry.pk}/change/", {"object_repr": "Changed"}
    )
    assert changed.status_code == 403
    assert client.get(f"/admin/auditlog/logentry/{entry.pk}/delete/").status_code == 403
    deleted = client.post(f"/admin/auditlog/logentry/{entry.pk}/delete/", {"post": "yes"})
    assert deleted.status_code == 403
    client.post(
        "/admin/auditlog/logentry/",
        {"action": "delete_selected", "_selected_action": [entry.pk], "post": "yes"},
    )

    entry.refresh_from_db()
    assert entry.object_repr == "North"
    assert LogEntry.objects.count() == count


@pytest.mark.parametrize("kind", ["no_role", "read", "manage"])
def test_roles_do_not_open_the_log_in_the_admin(kind: str) -> None:
    user = make_user(kind)
    assert user is not None
    client = Client()
    client.force_login(user)

    response = client.get("/admin/auditlog/logentry/")

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


# --- endpoint: permissions ---------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "status"),
    [("anonymous", 403), ("no_role", 403), ("read", 403), ("manage", 200), ("superuser", 200)],
)
def test_only_the_role_manage_reads_the_log(kind: str, status: int) -> None:
    assert kind in KINDS
    make_site()

    response = signed_in(make_user(kind)).get(URL)

    assert response.status_code == status
    if status == 403:
        assert "results" not in response.json()


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_log_cannot_be_written_through_the_api(method: str) -> None:
    entry = entries_for(make_site()).get()
    client = manager_client()
    count = LogEntry.objects.count()

    collection = getattr(client, method)(URL, {"object_repr": "Changed"}, format="json")
    single = getattr(client, method)(f"{URL}{entry.pk}/", {}, format="json")

    assert collection.status_code == 405
    assert single.status_code == 404
    assert LogEntry.objects.count() == count
    entry.refresh_from_db()
    assert entry.object_repr == "North"


# --- endpoint: content ------------------------------------------------------


def test_entry_has_the_documented_fields() -> None:
    actor = make_actor("editor")
    with acting_as(actor):
        site = make_site()

    response = manager_client().get(URL, {"object_type": "assets.site"})

    assert response.status_code == 200
    (entry,) = response.json()["results"]
    timestamp = entries_for(site).get().timestamp
    assert entry == {
        "id": entries_for(site).get().pk,
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "actor": "editor",
        "action": "create",
        "object_type": "assets.site",
        "object_id": site.pk,
        "object_repr": "North",
        "changes": entry["changes"],
    }
    assert entry["changes"]["name"] == [None, "North"]


def test_actions_and_missing_actor_are_shown() -> None:
    site = make_site()
    site.name = "North site"
    site.save()
    site.delete()

    response = manager_client().get(URL, {"object_type": "assets.site"})

    results = response.json()["results"]
    assert [entry["action"] for entry in results] == ["delete", "update", "create"]
    assert {entry["actor"] for entry in results} == {None}
    assert results[1]["changes"] == {"name": ["North", "North site"]}
    assert results[0]["changes"]["name"] == ["North site", None]


def test_role_change_is_shown_with_the_group_names(monkeypatch: pytest.MonkeyPatch) -> None:
    run_create_account(monkeypatch, FIRST_PASSWORD, "operator", "--role", "read")
    run_create_account(monkeypatch, SECOND_PASSWORD, "operator", "--role", "manage", "--update")
    operator = User.objects.get(username="operator")

    response = manager_client().get(
        URL, {"object_type": "accounts.user", "object_id": str(operator.pk)}
    )

    changes = [entry["changes"] for entry in response.json()["results"]]
    assert changes[:2] == [
        {"groups": {"type": "m2m", "operation": "add", "objects": ["manage"]}},
        {"groups": {"type": "m2m", "operation": "delete", "objects": ["read"]}},
    ]


def test_newest_entry_comes_first() -> None:
    for name in ("First", "Second", "Third"):
        make_site(name)

    response = manager_client().get(URL, {"object_type": "assets.site"})

    assert [entry["object_repr"] for entry in response.json()["results"]] == [
        "Third",
        "Second",
        "First",
    ]


# --- endpoint: filters ------------------------------------------------------


def test_filter_by_object_type_and_object_id() -> None:
    device = make_device()
    other = Device.objects.create(plant=device.plant, key="press-hmi", name="Press HMI")
    client = manager_client()

    devices = client.get(URL, {"object_type": "assets.device"}).json()["results"]
    one = client.get(URL, {"object_type": "assets.device", "object_id": str(other.pk)}).json()

    assert {entry["object_id"] for entry in devices} == {device.pk, other.pk}
    assert {entry["object_type"] for entry in devices} == {"assets.device"}
    assert [entry["object_repr"] for entry in one["results"]] == [str(other)]


def test_filter_by_actor() -> None:
    editor = make_actor("editor")
    with acting_as(editor):
        make_site("By editor")
    make_site("By nobody")

    response = manager_client().get(URL, {"actor": "editor"})

    assert [entry["object_repr"] for entry in response.json()["results"]] == ["By editor"]


@pytest.mark.parametrize(
    "query",
    [
        {"object_type": "assets.nothing"},
        {"object_type": "nothing.device"},
        {"object_id": "999999"},
        {"actor": "nobody"},
    ],
)
def test_unknown_filter_values_give_an_empty_list(query: dict[str, str]) -> None:
    make_device()

    response = manager_client().get(URL, query)

    assert response.status_code == 200
    assert response.json()["results"] == []
    assert response.json()["count"] == 0


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("object_type", ""),
        ("object_type", "assets"),
        ("object_type", "Assets.Device"),
        ("object_type", "assets.device.x"),
        ("object_id", ""),
        ("object_id", "abc"),
        ("object_id", "0"),
        ("object_id", "-1"),
        ("object_id", str(2**63)),
        ("actor", ""),
        ("actor", "x" * 151),
    ],
)
def test_invalid_filter_values_give_400(name: str, value: str) -> None:
    response = manager_client().get(URL, {name: value})

    assert response.status_code == 400
    assert name in response.json()


# --- endpoint: pages --------------------------------------------------------


def test_entries_come_in_pages_of_fixed_size() -> None:
    client = manager_client()
    total_before = LogEntry.objects.count()
    for number in range(PAGE_SIZE + 5):
        make_site(f"Site {number:03}")
    total = total_before + PAGE_SIZE + 5

    first = client.get(URL, {"page_size": "500"}).json()
    second = client.get(URL, {"page": "2"}).json()

    assert first["count"] == total
    assert len(first["results"]) == PAGE_SIZE
    assert first["previous"] is None
    assert first["next"].endswith(f"{URL}?page=2&page_size=500")
    assert len(second["results"]) == total - PAGE_SIZE
    assert second["next"] is None
    assert first["results"][0]["object_repr"] == f"Site {PAGE_SIZE + 4:03}"
    ids = [entry["id"] for entry in first["results"] + second["results"]]
    assert len(set(ids)) == total
    assert client.get(URL, {"page": "3"}).status_code == 404


def test_page_needs_few_queries(django_assert_max_num_queries: DjangoAssertNumQueries) -> None:
    client = manager_client()
    editor = make_actor("editor")
    with acting_as(editor):
        for number in range(PAGE_SIZE + 5):
            make_site(f"Site {number:03}")

    with django_assert_max_num_queries(6):
        response = client.get(URL)

    assert response.status_code == 200
    assert len(response.json()["results"]) == PAGE_SIZE


# --- schema ----------------------------------------------------------------


def test_log_is_described_in_the_schema(capsys: pytest.CaptureFixture[str]) -> None:
    stdout = StringIO()
    stderr = StringIO()
    call_command("spectacular", "--validate", stdout=stdout, stderr=stderr)
    schema: dict[str, Any] = yaml.safe_load(stdout.getvalue())

    assert stderr.getvalue() == ""
    # drf-spectacular prints its warnings and errors straight to sys.stderr.
    assert capsys.readouterr().err == ""
    assert set(schema["paths"][URL]) == {"get"}
    operation = schema["paths"][URL]["get"]
    assert operation["operationId"] == "audit_log_list"
    assert {parameter["name"] for parameter in operation["parameters"]} == {
        "page",
        "object_type",
        "object_id",
        "actor",
    }
    entry = schema["components"]["schemas"]["AuditLogEntry"]
    assert sorted(entry["properties"]) == sorted(
        [
            "id",
            "timestamp",
            "actor",
            "action",
            "object_type",
            "object_id",
            "object_repr",
            "changes",
        ]
    )
    assert entry["properties"]["actor"]["nullable"] is True
    assert entry["properties"]["action"]["allOf"] == [
        {"$ref": "#/components/schemas/AuditActionEnum"}
    ]
    assert schema["components"]["schemas"]["AuditActionEnum"]["enum"] == [
        "create",
        "update",
        "delete",
    ]
    assert "ActionEnum" not in schema["components"]["schemas"]
