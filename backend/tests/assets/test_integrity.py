"""Unique constraints hit at the same time as another request give 400, not 500.

The serializers check uniqueness first; a request running at the same time
can save the same name or key between that check and the write. These tests
reproduce it twice: by switching the serializer checks off (the check found
nothing, the row is there anyway) and with two real requests in two threads.
"""

import threading
from collections.abc import Iterator
from typing import Any

import pytest
from django.contrib.auth.models import Group
from django.db import IntegrityError, connection
from django.db.models import Model
from django.db.models.signals import pre_save
from rest_framework import serializers
from rest_framework.test import APIClient
from rest_framework.validators import UniqueValidator

from tests.accounts.users import TEST_PASSWORD
from tests.assets.conftest import ClientFactory, Structure
from twox.accounts.models import User
from twox.assets.integrity import UNIQUE_CONSTRAINTS, constraint_name, unique_violation
from twox.assets.models import Area, Device, Plant, Site
from twox.assets.serializers import AreaSerializer
from twox.assets.views import save_checked


@pytest.fixture
def unchecked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Switch off the uniqueness checks of the serializers, as if they ran too early."""

    def no_check(self: UniqueValidator, value: object, serializer_field: object) -> None:
        return None

    def no_area_check(self: AreaSerializer, attrs: dict[str, Any]) -> dict[str, Any]:
        return attrs

    monkeypatch.setattr(UniqueValidator, "__call__", no_check)
    monkeypatch.setattr(AreaSerializer, "validate", no_area_check)


@pytest.fixture
def manager(client_for: ClientFactory) -> APIClient:
    return client_for("manage")


@pytest.mark.parametrize(
    ("resource", "body", "field", "message"),
    [
        ("sites", {"name": "North"}, "name", "A site with this name exists already."),
        ("areas", {"name": "Line 1"}, "name", "This site has an area with this name already."),
        ("plants", {"key": "press", "name": "P"}, "key", "A plant with this key exists already."),
        (
            "devices",
            {"key": "press-plc", "name": "D"},
            "key",
            "A device with this key exists already.",
        ),
    ],
)
def test_create_hitting_a_unique_constraint_is_400_at_the_field(
    structure: Structure,
    manager: APIClient,
    unchecked: None,
    resource: str,
    body: dict[str, str],
    field: str,
    message: str,
) -> None:
    parents = {
        "sites": {},
        "areas": {"site": structure.north.pk},
        "plants": {"area": structure.north_line.pk},
        "devices": {"plant": structure.welder.pk},
    }
    counts_before = [model.objects.count() for model in (Site, Area, Plant, Device)]

    response = manager.post(f"/api/v1/{resource}/", {**parents[resource], **body}, format="json")

    assert response.status_code == 400
    assert response.json() == {field: [message]}
    assert [model.objects.count() for model in (Site, Area, Plant, Device)] == counts_before
    # The savepoint kept the connection usable for the next request.
    assert manager.get(f"/api/v1/{resource}/").status_code == 200


@pytest.mark.parametrize(
    ("path", "body", "field"),
    [
        ("sites/{north}", {"name": "South"}, "name"),
        ("areas/{south_line}", {"site": "{north}"}, "name"),
        ("plants/{welder}", {"key": "press"}, "key"),
        ("devices/{press_hmi}", {"key": "press-plc"}, "key"),
    ],
)
def test_update_hitting_a_unique_constraint_is_400_at_the_field(
    structure: Structure,
    manager: APIClient,
    unchecked: None,
    path: str,
    body: dict[str, str],
    field: str,
) -> None:
    ids = {
        "north": structure.north.pk,
        "south_line": structure.south_line.pk,
        "welder": structure.welder.pk,
        "press_hmi": structure.press_hmi.pk,
    }
    filled = {name: value.format(**ids) for name, value in body.items()}

    response = manager.patch(f"/api/v1/{path.format(**ids)}/", filled, format="json")

    assert response.status_code == 400
    assert list(response.json()) == [field]
    assert Site.objects.get(pk=structure.north.pk).name == "North"
    assert Area.objects.get(pk=structure.south_line.pk).site == structure.south
    assert Plant.objects.get(pk=structure.welder.pk).key == "welder"
    assert Device.objects.get(pk=structure.press_hmi.pk).key == "press-hmi"


# --- the mapping itself ------------------------------------------------------


def test_every_unique_constraint_of_the_models_is_mapped() -> None:
    names = {
        constraint.name
        for model in (Site, Area, Plant, Device)
        for constraint in model._meta.constraints
    }

    assert set(UNIQUE_CONSTRAINTS) == names


def test_constraint_name_comes_from_the_database(structure: Structure) -> None:
    with pytest.raises(IntegrityError) as caught:
        Plant.objects.create(area=structure.north_line, key="press", name="Second")

    assert constraint_name(caught.value) == "assets_plant_key_unique"
    violation = unique_violation(caught.value)
    assert violation is not None
    assert violation.field == "key"


class _Diagnostics:
    def __init__(self, name: str | None) -> None:
        self.constraint_name = name


class _DatabaseError(Exception):
    def __init__(self, name: str | None) -> None:
        super().__init__("from the database")
        self.diag = _Diagnostics(name)


def integrity_error(name: str | None) -> IntegrityError:
    error = IntegrityError("duplicate")
    error.__cause__ = _DatabaseError(name)
    return error


@pytest.mark.parametrize("name", [None, "assets_area_site_id_fk", "other_unique"])
def test_other_integrity_errors_are_not_mapped(name: str | None) -> None:
    assert unique_violation(integrity_error(name)) is None
    assert unique_violation(IntegrityError("no cause")) is None


class _FailingSerializer(serializers.ModelSerializer[Site]):
    """Saving raises the given integrity error."""

    class Meta:
        model = Site
        fields = ("name",)

    def __init__(self, error: IntegrityError) -> None:
        super().__init__(data={"name": "x"})
        self.error = error

    def save(self, **kwargs: object) -> Site:
        raise self.error


def test_save_checked_keeps_other_integrity_errors(db: None) -> None:
    error = integrity_error("assets_area_site_id_fk")

    with pytest.raises(IntegrityError) as caught:
        save_checked(_FailingSerializer(error))

    assert caught.value is error


def test_save_checked_turns_a_unique_violation_into_a_field_error(db: None) -> None:
    with pytest.raises(serializers.ValidationError) as caught:
        save_checked(_FailingSerializer(integrity_error("assets_site_name_unique")))

    assert caught.value.detail == {"name": ["A site with this name exists already."]}


# --- two requests at the same time -------------------------------------------


@pytest.fixture
def both_waiting_before_the_write() -> Iterator[threading.Barrier]:
    """Hold each save of a site until two requests have passed their checks."""
    barrier = threading.Barrier(2, timeout=20)

    def wait(sender: type[Model], instance: Model, **kwargs: object) -> None:
        barrier.wait()

    pre_save.connect(wait, sender=Site, dispatch_uid="test-integrity-race")
    yield barrier
    pre_save.disconnect(sender=Site, dispatch_uid="test-integrity-race")


@pytest.mark.django_db(transaction=True)
def test_two_requests_creating_the_same_site_give_201_and_400(
    both_waiting_before_the_write: threading.Barrier,
) -> None:
    # A transactional test empties the tables afterwards, also the role
    # groups of the data migration; create them if an earlier test removed them.
    Group.objects.get_or_create(name="manage")
    user = User.objects.create_user(username="racer", password=TEST_PASSWORD)
    user.groups.add(Group.objects.get(name="manage"))
    clients = []
    for _ in range(2):
        client = APIClient()
        client.force_login(user)
        clients.append(client)
    results: list[tuple[int, Any]] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def create(client: APIClient) -> None:
        try:
            response = client.post("/api/v1/sites/", {"name": "Race"}, format="json")
            with lock:
                results.append((response.status_code, response.json()))
        except BaseException as error:  # reported below
            errors.append(error)
        finally:
            connection.close()

    threads = [threading.Thread(target=create, args=(client,)) for client in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert errors == []
    assert sorted(status for status, _ in results) == [201, 400]
    refused = next(body for status, body in results if status == 400)
    assert refused == {"name": ["A site with this name exists already."]}
    assert Site.objects.filter(name="Race").count() == 1
