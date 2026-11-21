"""The structure API: answers, filters, checks, query count and schema."""

from collections.abc import Iterator
from io import StringIO
from typing import Any

import pytest
import yaml
from django.core.management import call_command
from django.db.models import Model
from django.db.models.signals import post_save
from pytest_django import DjangoAssertNumQueries
from rest_framework.test import APIClient

from tests.assets.conftest import ClientFactory, Structure
from twox.assets.models import Area, Device, Plant, Site


@pytest.fixture
def manager(client_for: ClientFactory) -> APIClient:
    return client_for("manage")


@pytest.fixture
def reader(client_for: ClientFactory) -> APIClient:
    return client_for("read")


def ids(response_body: list[dict[str, Any]]) -> list[int]:
    return [item["id"] for item in response_body]


# --- Answers -----------------------------------------------------------------


def test_device_answer_shows_the_chain(structure: Structure, reader: APIClient) -> None:
    response = reader.get(f"/api/v1/devices/{structure.press_plc.pk}/")

    assert response.status_code == 200
    body = response.json()
    assert body["plant"] == {"id": structure.press.pk, "key": "press", "name": "Press"}
    assert body["area"] == {"id": structure.north_line.pk, "name": "Line 1"}
    assert body["site"] == {"id": structure.north.pk, "name": "North"}
    assert body["key"] == "press-plc"
    assert body["ip_address"] == "192.0.2.10"
    assert set(body) == {
        "id",
        "plant",
        "area",
        "site",
        "key",
        "name",
        "manufacturer",
        "model",
        "software_version",
        "ip_address",
        "address_source",
        "protocols",
        "notes",
        "created_at",
        "updated_at",
    }


def test_device_without_address_shows_null(structure: Structure, reader: APIClient) -> None:
    response = reader.get(f"/api/v1/devices/{structure.press_hmi.pk}/")

    assert response.json()["ip_address"] is None


def test_lists_are_sorted_like_the_models(structure: Structure, reader: APIClient) -> None:
    sites = reader.get("/api/v1/sites/").json()
    devices = reader.get("/api/v1/devices/").json()

    assert [site["name"] for site in sites] == ["North", "South"]
    assert [device["key"] for device in devices] == sorted(device["key"] for device in devices)


def test_area_and_plant_name_their_parent_by_id(structure: Structure, reader: APIClient) -> None:
    area = reader.get(f"/api/v1/areas/{structure.south_line.pk}/").json()
    plant = reader.get(f"/api/v1/plants/{structure.paint.pk}/").json()

    assert area["site"] == structure.south.pk
    assert plant["area"] == structure.south_line.pk
    assert plant["key"] == "paint"


def test_unknown_id_is_404(structure: Structure, reader: APIClient) -> None:
    for resource in ("sites", "areas", "plants", "devices"):
        assert reader.get(f"/api/v1/{resource}/999999/").status_code == 404


# --- Writing -----------------------------------------------------------------


def test_created_device_is_answered_with_its_chain(
    structure: Structure, manager: APIClient
) -> None:
    response = manager.post(
        "/api/v1/devices/",
        {
            "plant": structure.paint.pk,
            "key": "paint-robot",
            "name": "Paint robot",
            "manufacturer": "Vendor",
            "ip_address": "192.0.2.40",
            "notes": "Line one\nLine two",
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["site"] == {"id": structure.south.pk, "name": "South"}
    assert body["area"] == {"id": structure.south_line.pk, "name": "Line 1"}
    assert body["plant"] == {"id": structure.paint.pk, "key": "paint", "name": "Paint shop"}
    stored = Device.objects.get(pk=body["id"])
    assert stored.notes == "Line one\nLine two"
    assert stored.manufacturer == "Vendor"
    assert stored.model == ""


def test_patch_changes_only_the_given_field(structure: Structure, manager: APIClient) -> None:
    response = manager.patch(
        f"/api/v1/devices/{structure.press_plc.pk}/", {"software_version": "2.0"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["software_version"] == "2.0"
    stored = Device.objects.get(pk=structure.press_plc.pk)
    assert stored.software_version == "2.0"
    assert stored.key == "press-plc"
    assert stored.ip_address == "192.0.2.10"


def test_device_moves_to_another_plant(structure: Structure, manager: APIClient) -> None:
    response = manager.patch(
        f"/api/v1/devices/{structure.press_plc.pk}/", {"plant": structure.paint.pk}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["site"]["name"] == "South"
    assert Device.objects.get(pk=structure.press_plc.pk).plant == structure.paint


def test_put_keeps_its_own_key_and_name(structure: Structure, manager: APIClient) -> None:
    device = manager.put(
        f"/api/v1/devices/{structure.press_plc.pk}/",
        {"plant": structure.press.pk, "key": "press-plc", "name": "Press PLC"},
        format="json",
    )
    area = manager.put(
        f"/api/v1/areas/{structure.north_line.pk}/",
        {"site": structure.north.pk, "name": "Line 1"},
        format="json",
    )
    site = manager.put(f"/api/v1/sites/{structure.north.pk}/", {"name": "North"}, format="json")

    assert device.status_code == 200
    assert area.status_code == 200
    assert site.status_code == 200


def test_put_empties_optional_device_fields(structure: Structure, manager: APIClient) -> None:
    Device.objects.filter(pk=structure.press_plc.pk).update(notes="old note")

    response = manager.put(
        f"/api/v1/devices/{structure.press_plc.pk}/",
        {"plant": structure.press.pk, "key": "press-plc", "name": "Press PLC", "notes": ""},
        format="json",
    )

    assert response.status_code == 200
    assert Device.objects.get(pk=structure.press_plc.pk).notes == ""


@pytest.fixture
def saved_objects() -> Iterator[list[Model]]:
    """Every instance saved with ``Model.save()`` while the test runs."""
    saved: list[Model] = []

    def remember(sender: type[Model], instance: Model, **kwargs: object) -> None:
        saved.append(instance)

    for model in (Site, Area, Plant, Device):
        post_save.connect(remember, sender=model, dispatch_uid=f"test-{model.__name__}")
    yield saved
    for model in (Site, Area, Plant, Device):
        post_save.disconnect(sender=model, dispatch_uid=f"test-{model.__name__}")


def test_writes_go_through_model_save(
    structure: Structure, manager: APIClient, saved_objects: list[Model]
) -> None:
    # The change log (work order 028) hooks into save(); bulk updates would bypass it.
    created = manager.post("/api/v1/sites/", {"name": "East"}, format="json")
    manager.patch(f"/api/v1/plants/{structure.press.pk}/", {"name": "Big press"}, format="json")
    manager.put(
        f"/api/v1/devices/{structure.paint_plc.pk}/",
        {"plant": structure.paint.pk, "key": "paint-plc", "name": "Paint PLC 2"},
        format="json",
    )

    assert [(type(obj).__name__, obj.pk) for obj in saved_objects] == [
        ("Site", created.json()["id"]),
        ("Plant", structure.press.pk),
        ("Device", structure.paint_plc.pk),
    ]


# --- Filters -----------------------------------------------------------------


def test_areas_filter_by_site(structure: Structure, reader: APIClient) -> None:
    response = reader.get("/api/v1/areas/", {"site": structure.south.pk})

    assert response.status_code == 200
    assert ids(response.json()) == [structure.south_line.pk]


def test_plants_filter_by_area(structure: Structure, reader: APIClient) -> None:
    response = reader.get("/api/v1/plants/", {"area": structure.north_line.pk})

    assert ids(response.json()) == [structure.press.pk, structure.welder.pk]


def test_devices_filter_by_plant(structure: Structure, reader: APIClient) -> None:
    response = reader.get("/api/v1/devices/", {"plant": structure.press.pk})

    assert ids(response.json()) == [structure.press_hmi.pk, structure.press_plc.pk]


def test_devices_filter_by_site_through_the_chain(structure: Structure, reader: APIClient) -> None:
    north = reader.get("/api/v1/devices/", {"site": structure.north.pk})
    south = reader.get("/api/v1/devices/", {"site": structure.south.pk})

    assert sorted(ids(north.json())) == sorted(
        [structure.press_plc.pk, structure.press_hmi.pk, structure.welder_plc.pk]
    )
    assert ids(south.json()) == [structure.paint_plc.pk]


def test_device_filters_combine(structure: Structure, reader: APIClient) -> None:
    matching = reader.get(
        "/api/v1/devices/", {"site": structure.north.pk, "plant": structure.welder.pk}
    )
    contradicting = reader.get(
        "/api/v1/devices/", {"site": structure.south.pk, "plant": structure.welder.pk}
    )

    assert ids(matching.json()) == [structure.welder_plc.pk]
    assert contradicting.json() == []


def test_filter_without_value_lists_everything(structure: Structure, reader: APIClient) -> None:
    assert len(reader.get("/api/v1/devices/").json()) == 4
    assert len(reader.get("/api/v1/areas/").json()) == 2


def test_filter_with_unknown_id_gives_an_empty_list(
    structure: Structure, reader: APIClient
) -> None:
    response = reader.get("/api/v1/plants/", {"area": 999999})

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    ("path", "parameter"),
    [
        ("/api/v1/areas/", "site"),
        ("/api/v1/plants/", "area"),
        ("/api/v1/devices/", "plant"),
        ("/api/v1/devices/", "site"),
    ],
)
@pytest.mark.parametrize("value", ["abc", "", "0", "-1", "1.5", str(2**63)])
def test_filter_with_invalid_id_is_400_at_the_parameter(
    structure: Structure, reader: APIClient, path: str, parameter: str, value: str
) -> None:
    response = reader.get(path, {parameter: value})

    assert response.status_code == 400
    assert list(response.json()) == [parameter]


def test_filters_do_not_apply_to_detail_paths(structure: Structure, reader: APIClient) -> None:
    response = reader.get(f"/api/v1/devices/{structure.press_plc.pk}/", {"site": "abc"})

    assert response.status_code == 200


# --- Checks ------------------------------------------------------------------


def test_duplicate_site_name_is_400_at_the_field(structure: Structure, manager: APIClient) -> None:
    response = manager.post("/api/v1/sites/", {"name": "North"}, format="json")

    assert response.status_code == 400
    assert response.json() == {"name": ["A site with this name exists already."]}


def test_area_name_is_unique_per_site(structure: Structure, manager: APIClient) -> None:
    same_site = manager.post(
        "/api/v1/areas/", {"site": structure.north.pk, "name": "Line 1"}, format="json"
    )
    new_site = manager.post("/api/v1/sites/", {"name": "East"}, format="json").json()
    other_site = manager.post(
        "/api/v1/areas/", {"site": new_site["id"], "name": "Line 1"}, format="json"
    )

    assert same_site.status_code == 400
    assert same_site.json() == {"name": ["This site has an area with this name already."]}
    assert other_site.status_code == 201


def test_area_cannot_be_renamed_or_moved_onto_a_clash(
    structure: Structure, manager: APIClient
) -> None:
    Area.objects.create(site=structure.north, name="Line 2")

    renamed = manager.patch(
        f"/api/v1/areas/{structure.north_line.pk}/", {"name": "Line 2"}, format="json"
    )
    # South has "Line 1" as well.
    moved = manager.patch(
        f"/api/v1/areas/{structure.north_line.pk}/", {"site": structure.south.pk}, format="json"
    )

    assert renamed.status_code == 400
    assert list(renamed.json()) == ["name"]
    assert moved.status_code == 400
    assert list(moved.json()) == ["name"]
    assert Area.objects.get(pk=structure.north_line.pk).name == "Line 1"


@pytest.mark.parametrize(
    ("resource", "body"),
    [
        ("plants", {"key": "press", "name": "Second press"}),
        ("devices", {"key": "press-plc", "name": "Second PLC"}),
    ],
)
def test_duplicate_key_is_400_at_the_field(
    structure: Structure, manager: APIClient, resource: str, body: dict[str, str]
) -> None:
    parent = (
        {"area": structure.south_line.pk} if resource == "plants" else {"plant": structure.paint.pk}
    )

    response = manager.post(f"/api/v1/{resource}/", {**parent, **body}, format="json")

    assert response.status_code == 400
    noun = "plant" if resource == "plants" else "device"
    assert response.json() == {"key": [f"A {noun} with this key exists already."]}


def test_key_of_a_device_cannot_be_changed_to_a_taken_one(
    structure: Structure, manager: APIClient
) -> None:
    response = manager.patch(
        f"/api/v1/devices/{structure.press_hmi.pk}/", {"key": "press-plc"}, format="json"
    )

    assert response.status_code == 400
    assert list(response.json()) == ["key"]


def test_plant_and_device_may_share_a_key(structure: Structure, manager: APIClient) -> None:
    # Keys are unique per kind (019): a device may be called like a plant.
    response = manager.post(
        "/api/v1/devices/",
        {"plant": structure.press.pk, "key": "press", "name": "Press controller"},
        format="json",
    )

    assert response.status_code == 201


@pytest.mark.parametrize("key", ["Press", "press_1", "press 1", "press.1", "presse-ä", ""])
@pytest.mark.parametrize("resource", ["plants", "devices"])
def test_key_format_is_checked(
    structure: Structure, manager: APIClient, resource: str, key: str
) -> None:
    parent = (
        {"area": structure.north_line.pk} if resource == "plants" else {"plant": structure.press.pk}
    )

    response = manager.post(
        f"/api/v1/{resource}/", {**parent, "key": key, "name": "New"}, format="json"
    )

    assert response.status_code == 400
    assert list(response.json()) == ["key"]
    if key:
        assert response.json()["key"] == ["Use only lowercase letters, digits and hyphens."]


def test_too_long_key_is_400(structure: Structure, manager: APIClient) -> None:
    response = manager.post(
        "/api/v1/plants/",
        {"area": structure.north_line.pk, "key": "a" * 65, "name": "Long"},
        format="json",
    )

    assert response.status_code == 400
    assert list(response.json()) == ["key"]


@pytest.mark.parametrize("address", ["999.1.1.1", "192.0.2", "host.example", "192.0.2.1/24"])
def test_invalid_ip_address_is_400_at_the_field(
    structure: Structure, manager: APIClient, address: str
) -> None:
    response = manager.patch(
        f"/api/v1/devices/{structure.press_hmi.pk}/", {"ip_address": address}, format="json"
    )

    assert response.status_code == 400
    assert list(response.json()) == ["ip_address"]
    assert Device.objects.get(pk=structure.press_hmi.pk).ip_address is None


@pytest.mark.parametrize(
    ("address", "stored"),
    [("192.0.2.99", "192.0.2.99"), ("2001:DB8::99", "2001:db8::99"), ("", None), (None, None)],
)
def test_valid_or_empty_ip_address_is_stored(
    structure: Structure, manager: APIClient, address: str | None, stored: str | None
) -> None:
    response = manager.patch(
        f"/api/v1/devices/{structure.press_plc.pk}/", {"ip_address": address}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["ip_address"] == stored
    assert Device.objects.get(pk=structure.press_plc.pk).ip_address == stored


@pytest.mark.parametrize(
    ("resource", "body", "field"),
    [
        ("areas", {"site": 999999, "name": "Line 9"}, "site"),
        ("plants", {"area": 999999, "key": "nowhere", "name": "Nowhere"}, "area"),
        ("devices", {"plant": 999999, "key": "nowhere", "name": "Nowhere"}, "plant"),
    ],
)
def test_unknown_parent_is_400_at_the_field(
    structure: Structure, manager: APIClient, resource: str, body: dict[str, Any], field: str
) -> None:
    response = manager.post(f"/api/v1/{resource}/", body, format="json")

    assert response.status_code == 400
    assert list(response.json()) == [field]


@pytest.mark.parametrize(
    ("resource", "required"),
    [
        ("sites", ["name"]),
        ("areas", ["name", "site"]),
        ("plants", ["area", "key", "name"]),
        ("devices", ["key", "name", "plant"]),
    ],
)
def test_required_fields_are_named(
    structure: Structure, manager: APIClient, resource: str, required: list[str]
) -> None:
    response = manager.post(f"/api/v1/{resource}/", {}, format="json")

    assert response.status_code == 400
    assert sorted(response.json()) == required


def test_read_only_fields_are_ignored(structure: Structure, manager: APIClient) -> None:
    response = manager.patch(
        f"/api/v1/sites/{structure.north.pk}/",
        {"id": 12345, "created_at": "2000-01-01T00:00:00Z"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["id"] == structure.north.pk
    assert not response.json()["created_at"].startswith("2000")


# --- Query count -------------------------------------------------------------


def add_devices(structure: Structure, count: int) -> None:
    """Add ``count`` devices, each in its own plant, area and site."""
    for number in range(count):
        site = Site.objects.create(name=f"Site {number}")
        area = Area.objects.create(site=site, name=f"Area {number}")
        plant = Plant.objects.create(area=area, key=f"plant-{number}", name=f"Plant {number}")
        Device.objects.create(plant=plant, key=f"device-{number}", name=f"Device {number}")


def test_device_list_needs_no_query_per_device(
    structure: Structure,
    reader: APIClient,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    add_devices(structure, 30)

    # Session, user, role groups and one query for all devices with their chain.
    with django_assert_max_num_queries(4):
        response = reader.get("/api/v1/devices/")

    assert response.status_code == 200
    assert len(response.json()) == 34
    assert all(device["site"]["name"] for device in response.json())


def test_device_answer_after_a_write_loads_the_chain_at_once(
    structure: Structure,
    manager: APIClient,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    # Session, user, role groups, the device, the plant, the uniqueness of
    # the key, the update and one query for the answer with its chain; the
    # savepoint around the write (031) adds SAVEPOINT and RELEASE SAVEPOINT.
    with django_assert_max_num_queries(10):
        response = manager.patch(
            f"/api/v1/devices/{structure.press_plc.pk}/", {"name": "Renamed"}, format="json"
        )

    assert response.status_code == 200


# --- Schema ------------------------------------------------------------------


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    stdout = StringIO()
    stderr = StringIO()
    call_command("spectacular", "--validate", stdout=stdout, stderr=stderr)
    assert stderr.getvalue() == ""
    loaded: dict[str, Any] = yaml.safe_load(stdout.getvalue())
    return loaded


def operations(schema: dict[str, Any], prefix: str) -> dict[str, str]:
    """``{"METHOD path": operationId}`` of every path that starts with ``prefix``."""
    return {
        f"{method.upper()} {path}": operation["operationId"]
        for path, item in schema["paths"].items()
        if path.startswith(prefix)
        for method, operation in item.items()
    }


@pytest.mark.parametrize("resource", ["sites", "areas", "plants", "devices"])
def test_schema_names_the_operations(schema: dict[str, Any], resource: str) -> None:
    # Nested paths of other apps (the documents of a device, 029) are not
    # operations of the structure API.
    own = {
        key: operation_id
        for key, operation_id in operations(schema, f"/api/v1/{resource}/").items()
        if key.split(" ", 1)[1] in {f"/api/v1/{resource}/", f"/api/v1/{resource}/{{id}}/"}
    }
    assert own == {
        f"GET /api/v1/{resource}/": f"{resource}_list",
        f"POST /api/v1/{resource}/": f"{resource}_create",
        f"GET /api/v1/{resource}/{{id}}/": f"{resource}_retrieve",
        f"PUT /api/v1/{resource}/{{id}}/": f"{resource}_update",
        f"PATCH /api/v1/{resource}/{{id}}/": f"{resource}_partial_update",
    }


def test_schema_operation_ids_are_unique(schema: dict[str, Any]) -> None:
    every = list(operations(schema, "/").values())

    assert len(every) == len(set(every))


def test_schema_types_every_field(schema: dict[str, Any]) -> None:
    components = schema["components"]["schemas"]
    for name in ("Site", "Area", "Plant", "Device", "DeviceWrite", "PlantRef", "AreaRef"):
        for field, definition in components[name]["properties"].items():
            assert "type" in definition or "allOf" in definition, f"{name}.{field}"


def test_schema_device_reads_the_chain_and_writes_the_plant_id(schema: dict[str, Any]) -> None:
    components = schema["components"]["schemas"]
    device = components["Device"]["properties"]
    write = components["DeviceWrite"]["properties"]
    path = schema["paths"]["/api/v1/devices/"]

    assert device["plant"]["allOf"] == [{"$ref": "#/components/schemas/PlantRef"}]
    assert device["site"]["allOf"] == [{"$ref": "#/components/schemas/SiteRef"}]
    assert write["plant"] == {"type": "integer"}
    assert write["ip_address"]["nullable"] is True
    request = path["post"]["requestBody"]["content"]["application/json"]["schema"]
    answer = path["post"]["responses"]["201"]["content"]["application/json"]["schema"]
    assert request == {"$ref": "#/components/schemas/DeviceWrite"}
    assert answer == {"$ref": "#/components/schemas/Device"}
    assert [parameter["name"] for parameter in path["get"]["parameters"]] == ["plant", "site"]


@pytest.mark.parametrize(
    ("path", "parameter"),
    [("/api/v1/areas/", "site"), ("/api/v1/plants/", "area")],
)
def test_schema_lists_the_filters(schema: dict[str, Any], path: str, parameter: str) -> None:
    parameters = schema["paths"][path]["get"]["parameters"]

    assert parameters == [
        {
            "in": "query",
            "name": parameter,
            "schema": {"type": "integer"},
            "description": parameters[0]["description"],
        }
    ]


def test_schema_has_no_delete(schema: dict[str, Any]) -> None:
    for path, item in schema["paths"].items():
        assert "delete" not in item, path
