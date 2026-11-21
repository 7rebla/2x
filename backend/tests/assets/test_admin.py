"""The structure in the admin: lists, search and filters, for superusers only (E-39, E-41)."""

import pytest
from django.contrib import admin
from django.test import Client

from tests.accounts.users import make_user
from tests.assets.conftest import Structure
from twox.assets.models import Area, Device, Plant, Site

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
