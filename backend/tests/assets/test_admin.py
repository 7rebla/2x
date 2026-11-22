"""The structure in the admin: lists, search and filters, for superusers only (E-39, E-41)."""

import pytest
from auditlog.models import LogEntry
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from tests.accounts.users import make_user
from tests.assets.conftest import Structure
from twox.assets.admin import DeviceAdmin
from twox.assets.models import Area, Device, DeviceClass, Plant, Site

PAGES = ["site", "area", "plant", "device"]


@pytest.fixture
def superuser_client(db: None) -> Client:
    client = Client()
    superuser = make_user("superuser")
    assert superuser is not None
    client.force_login(superuser)
    return client


@pytest.mark.parametrize("model", [Site, Area, Plant, Device])
def test_models_are_registered(model: type[Site | Area | Plant | Device]) -> None:
    assert admin.site.is_registered(model)


@pytest.mark.parametrize("page", PAGES)
def test_superuser_reaches_list_add_and_change_pages(
    structure: Structure, superuser_client: Client, page: str
) -> None:
    objects = {
        "site": structure.north,
        "area": structure.north_line,
        "plant": structure.press,
        "device": structure.press_plc,
    }

    listing = superuser_client.get(f"/admin/assets/{page}/")
    adding = superuser_client.get(f"/admin/assets/{page}/add/")
    change = superuser_client.get(f"/admin/assets/{page}/{objects[page].pk}/change/")

    assert listing.status_code == 200
    assert adding.status_code == 200
    assert change.status_code == 200


@pytest.mark.parametrize("kind", ["anonymous", "no_role", "read", "manage"])
@pytest.mark.parametrize("page", PAGES)
def test_roles_do_not_open_the_admin(structure: Structure, kind: str, page: str) -> None:
    client = Client()
    user = make_user(kind)
    if user is not None:
        client.force_login(user)

    response = client.get(f"/admin/assets/{page}/")

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


def listed(client: Client, page: str, query: dict[str, str | int]) -> list[str]:
    """``str()`` of every object the admin list ``page`` shows for ``query``."""
    response = client.get(f"/admin/assets/{page}/", query)
    assert response.status_code == 200
    assert response.context is not None
    return sorted(str(obj) for obj in response.context["cl"].result_list)


@pytest.mark.parametrize(
    ("query", "found"),
    [
        ("press-plc", ["Press PLC (press-plc)"]),
        ("Welder", ["Welder PLC (welder-plc)"]),
        ("192.0.2.20", ["Welder PLC (welder-plc)"]),
        ("192.0.2", ["Press PLC (press-plc)", "Welder PLC (welder-plc)"]),
        ("2001:db8", ["Paint PLC (paint-plc)"]),
    ],
)
def test_device_search_finds_name_key_and_address(
    structure: Structure, superuser_client: Client, query: str, found: list[str]
) -> None:
    assert listed(superuser_client, "device", {"q": query}) == found


@pytest.mark.parametrize(
    ("page", "query", "found"),
    [
        ("site", "Nor", ["North"]),
        ("area", "South", ["Line 1"]),
        ("plant", "weld", ["Welder (welder)"]),
        ("plant", "Paint", ["Paint shop (paint)"]),
    ],
)
def test_search_on_the_other_lists(
    structure: Structure, superuser_client: Client, page: str, query: str, found: list[str]
) -> None:
    assert listed(superuser_client, page, {"q": query}) == found


def test_lists_filter_by_parent(structure: Structure, superuser_client: Client) -> None:
    south = structure.south.pk

    assert listed(superuser_client, "device", {"plant__area__site__id__exact": south}) == [
        "Paint PLC (paint-plc)"
    ]
    assert listed(superuser_client, "plant", {"area__site__id__exact": south}) == [
        "Paint shop (paint)"
    ]
    assert listed(superuser_client, "area", {"site__id__exact": south}) == ["Line 1"]


def test_device_list_filters_and_shows_the_device_class(
    structure: Structure, superuser_client: Client
) -> None:
    Device.objects.filter(pk=structure.welder_plc.pk).update(device_class=DeviceClass.PLC)
    Device.objects.filter(pk=structure.paint_plc.pk).update(device_class=DeviceClass.PLC)
    Device.objects.filter(pk=structure.press_hmi.pk).update(device_class=DeviceClass.COMPUTER)

    assert "device_class" in DeviceAdmin.list_display
    assert listed(superuser_client, "device", {"device_class__exact": "plc"}) == [
        "Paint PLC (paint-plc)",
        "Welder PLC (welder-plc)",
    ]
    assert listed(superuser_client, "device", {"device_class__exact": "computer"}) == [
        "Press HMI (press-hmi)"
    ]
    assert listed(superuser_client, "device", {"device_class__exact": "other"}) == [
        "Press PLC (press-plc)"
    ]
    page = superuser_client.get("/admin/assets/device/")
    assert "?device_class__exact=robot" in page.content.decode()


def test_superuser_changes_the_device_class_with_a_log_entry(
    structure: Structure, superuser_client: Client
) -> None:
    device = structure.press_plc
    form = {
        "plant": device.plant_id,
        "key": device.key,
        "name": device.name,
        "device_class": "robot",
        "manufacturer": device.manufacturer,
        "model": device.model,
        "software_version": device.software_version,
        "ip_address": device.ip_address or "",
        "address_source": device.address_source,
        "protocols": device.protocols,
        "notes": device.notes,
    }

    response = superuser_client.post(f"/admin/assets/device/{device.pk}/change/", form)

    assert response.status_code == 302
    assert Device.objects.get(pk=device.pk).device_class == DeviceClass.ROBOT
    entry = LogEntry.objects.get(
        content_type=ContentType.objects.get_for_model(Device),
        object_id=device.pk,
        action=LogEntry.Action.UPDATE,
    )
    assert entry.changes == {"device_class": ["other", "robot"]}


def test_admin_rejects_an_unknown_device_class(
    structure: Structure, superuser_client: Client
) -> None:
    device = structure.press_plc

    response = superuser_client.post(
        f"/admin/assets/device/{device.pk}/change/",
        {"plant": device.plant_id, "key": device.key, "name": device.name, "device_class": "sps"},
    )

    assert response.status_code == 200
    assert response.context is not None
    assert "device_class" in response.context["adminform"].form.errors
    assert Device.objects.get(pk=device.pk).device_class == DeviceClass.OTHER


def test_superuser_cannot_delete_a_site_with_areas(
    structure: Structure, superuser_client: Client
) -> None:
    response = superuser_client.post(
        f"/admin/assets/site/{structure.north.pk}/delete/", {"post": "yes"}
    )

    # The admin explains which children protect the site and deletes nothing.
    assert response.status_code == 200
    assert Site.objects.filter(pk=structure.north.pk).exists()


def test_superuser_deletes_a_device(structure: Structure, superuser_client: Client) -> None:
    response = superuser_client.post(
        f"/admin/assets/device/{structure.press_hmi.pk}/delete/", {"post": "yes"}
    )

    assert response.status_code == 302
    assert not Device.objects.filter(pk=structure.press_hmi.pk).exists()
