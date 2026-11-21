"""Who may read and write the structure through the API (E-40, E-41)."""

from typing import Any

import pytest
from rest_framework.test import APIClient

from tests.assets.conftest import ClientFactory, Structure
from twox.assets.models import Area, Device, Plant, Site

RESOURCES = ["sites", "areas", "plants", "devices"]
MODELS: dict[str, type[Site | Area | Plant | Device]] = {
    "sites": Site,
    "areas": Area,
    "plants": Plant,
    "devices": Device,
}


def existing_id(structure: Structure, resource: str) -> int:
    """The id of an object of ``resource`` in the test structure."""
    objects: dict[str, Site | Area | Plant | Device] = {
        "sites": structure.north,
        "areas": structure.north_line,
        "plants": structure.press,
        "devices": structure.press_plc,
    }
    return objects[resource].id


def new_object(structure: Structure, resource: str) -> dict[str, Any]:
    """A valid body that creates a new object of ``resource``."""
    bodies: dict[str, dict[str, Any]] = {
        "sites": {"name": "East"},
        "areas": {"site": structure.north.pk, "name": "Line 2"},
        "plants": {"area": structure.north_line.pk, "key": "robot", "name": "Robot"},
        "devices": {"plant": structure.press.pk, "key": "press-io", "name": "Press I/O"},
    }
    return bodies[resource]


def full_object(structure: Structure, resource: str) -> dict[str, Any]:
    """A valid body for PUT on the existing object of ``resource``."""
    bodies: dict[str, dict[str, Any]] = {
        "sites": {"name": "North renamed"},
        "areas": {"site": structure.north.pk, "name": "Line 1 renamed"},
        "plants": {"area": structure.north_line.pk, "key": "press", "name": "Press renamed"},
        "devices": {"plant": structure.press.pk, "key": "press-plc", "name": "PLC renamed"},
    }
    return bodies[resource]


def write(
    client: APIClient, method: str, resource: str, structure: Structure
) -> tuple[int, dict[str, Any] | list[Any]]:
    """Send a valid write of ``method`` to ``resource``; return status and body."""
    path = f"/api/v1/{resource}/{existing_id(structure, resource)}/"
    body = full_object(structure, resource)
    if method == "POST":
        response = client.post(f"/api/v1/{resource}/", new_object(structure, resource), "json")
    elif method == "PUT":
        response = client.put(path, body, "json")
    else:
        response = client.patch(path, {"name": body["name"]}, "json")
    return response.status_code, response.json()


def snapshot() -> list[tuple[object, ...]]:
    """Everything stored in the structure, to show that a refused write changed nothing."""
    return [
        tuple(model.objects.order_by("pk").values_list()) for model in (Site, Area, Plant, Device)
    ]


@pytest.mark.parametrize("kind", ["anonymous", "no_role"])
@pytest.mark.parametrize("resource", RESOURCES)
def test_reading_needs_a_role(
    structure: Structure, client_for: ClientFactory, kind: str, resource: str
) -> None:
    client = client_for(kind)

    listing = client.get(f"/api/v1/{resource}/")
    detail = client.get(f"/api/v1/{resource}/{existing_id(structure, resource)}/")

    assert listing.status_code == 403
    assert detail.status_code == 403
    assert set(listing.json()) == {"detail"}
    assert set(detail.json()) == {"detail"}


@pytest.mark.parametrize("kind", ["read", "manage", "superuser"])
@pytest.mark.parametrize("resource", RESOURCES)
def test_every_role_reads(
    structure: Structure, client_for: ClientFactory, kind: str, resource: str
) -> None:
    client = client_for(kind)
    pk = existing_id(structure, resource)

    listing = client.get(f"/api/v1/{resource}/")
    detail = client.get(f"/api/v1/{resource}/{pk}/")

    assert listing.status_code == 200
    assert len(listing.json()) == MODELS[resource].objects.count()
    assert detail.status_code == 200
    assert detail.json()["id"] == pk


@pytest.mark.parametrize("kind", ["anonymous", "no_role", "read"])
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH"])
@pytest.mark.parametrize("resource", RESOURCES)
def test_writing_needs_the_role_manage(
    structure: Structure, client_for: ClientFactory, kind: str, method: str, resource: str
) -> None:
    before = snapshot()

    status, _ = write(client_for(kind), method, resource, structure)

    assert status == 403
    assert snapshot() == before


@pytest.mark.parametrize("kind", ["manage", "superuser"])
@pytest.mark.parametrize(("method", "expected"), [("POST", 201), ("PUT", 200), ("PATCH", 200)])
@pytest.mark.parametrize("resource", RESOURCES)
def test_role_manage_writes(
    structure: Structure,
    client_for: ClientFactory,
    kind: str,
    method: str,
    expected: int,
    resource: str,
) -> None:
    status, body = write(client_for(kind), method, resource, structure)

    assert status == expected
    assert isinstance(body, dict)
    stored = MODELS[resource].objects.get(pk=body["id"])
    sent = new_object(structure, resource) if method == "POST" else full_object(structure, resource)
    assert stored.name == sent["name"]


@pytest.mark.parametrize("kind", ["read", "manage", "superuser"])
@pytest.mark.parametrize("resource", RESOURCES)
def test_nobody_deletes_through_the_api(
    structure: Structure, client_for: ClientFactory, kind: str, resource: str
) -> None:
    pk = existing_id(structure, resource)
    client = client_for(kind)

    detail = client.delete(f"/api/v1/{resource}/{pk}/")
    listing = client.delete(f"/api/v1/{resource}/")

    # read is refused before the method is looked at; the others learn that
    # the method does not exist.
    expected = 403 if kind == "read" else 405
    assert detail.status_code == expected
    assert listing.status_code == expected
    assert MODELS[resource].objects.filter(pk=pk).exists()


@pytest.mark.parametrize("resource", RESOURCES)
def test_options_lists_no_delete(
    structure: Structure, client_for: ClientFactory, resource: str
) -> None:
    response = client_for("manage").options(
        f"/api/v1/{resource}/{existing_id(structure, resource)}/"
    )

    assert response.status_code == 200
    assert "DELETE" not in response["Allow"]
