"""Structure models: site > area > plant > device."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from twox.assets.models import Area, Device, Plant, Site

pytestmark = pytest.mark.django_db


def make_chain() -> Device:
    site = Site.objects.create(name="Test site")
    area = Area.objects.create(site=site, name="Production line")
    plant = Plant.objects.create(area=area, key="aps-dps", name="Goods in and out")
    return Device.objects.create(
        plant=plant,
        key="dps-plc",
        name="PLC goods in and out",
        manufacturer="Vendor",
        model="Model 1",
        software_version="1.0",
        ip_address="192.168.0.90",
        address_source="Manual page 1",
        protocols="OPC UA",
        notes="",
    )


def test_chain_can_be_created() -> None:
    device = make_chain()

    loaded = Device.objects.select_related("plant__area__site").get(pk=device.pk)
    assert loaded.plant.area.site.name == "Test site"
    assert loaded.plant.area.name == "Production line"
    assert loaded.plant.key == "aps-dps"
    assert loaded.ip_address == "192.168.0.90"
    assert loaded.created_at is not None
    assert loaded.updated_at is not None
    assert str(loaded) == "PLC goods in and out (dps-plc)"
    assert str(loaded.plant) == "Goods in and out (aps-dps)"
    assert str(loaded.plant.area) == "Production line"
    assert str(loaded.plant.area.site) == "Test site"
    assert list(loaded.plant.area.site.areas.all()) == [loaded.plant.area]


def test_plant_without_device_keeps_notes() -> None:
    site = Site.objects.create(name="Test site")
    area = Area.objects.create(site=site, name="Production line")
    plant = Plant.objects.create(area=area, key="aps-charging", name="Charging", notes="No device")

    plant.full_clean()
    assert not plant.devices.exists()
    assert Plant.objects.get(pk=plant.pk).notes == "No device"


def test_area_name_is_unique_per_site() -> None:
    first = Site.objects.create(name="Site A")
    second = Site.objects.create(name="Site B")
    Area.objects.create(site=first, name="Line")

    with pytest.raises(IntegrityError), transaction.atomic():
        Area.objects.create(site=first, name="Line")

    other = Area.objects.create(site=second, name="Line")
    assert other.pk is not None
    assert Area.objects.filter(name="Line").count() == 2


def test_duplicate_area_name_fails_full_clean() -> None:
    site = Site.objects.create(name="Site A")
    Area.objects.create(site=site, name="Line")

    with pytest.raises(ValidationError):
        Area(site=site, name="Line").full_clean()


def test_site_name_is_unique() -> None:
    Site.objects.create(name="Site A")

    with pytest.raises(IntegrityError), transaction.atomic():
        Site.objects.create(name="Site A")


def test_plant_and_device_keys_are_unique_in_the_whole_system() -> None:
    device = make_chain()
    other_site = Site.objects.create(name="Other site")
    other_area = Area.objects.create(site=other_site, name="Other line")

    with pytest.raises(IntegrityError), transaction.atomic():
        Plant.objects.create(area=other_area, key=device.plant.key, name="Copy")

    other_plant = Plant.objects.create(area=other_area, key="other-plant", name="Other")
    with pytest.raises(IntegrityError), transaction.atomic():
        Device.objects.create(plant=other_plant, key=device.key, name="Copy")


def test_protect_prevents_deleting_site_with_areas() -> None:
    device = make_chain()
    site = device.plant.area.site

    with pytest.raises(ProtectedError):
        site.delete()

    assert Site.objects.filter(pk=site.pk).exists()


def test_protect_prevents_deleting_area_and_plant_with_children() -> None:
    device = make_chain()

    with pytest.raises(ProtectedError):
        device.plant.area.delete()
    with pytest.raises(ProtectedError):
        device.plant.delete()


def test_invalid_ip_address_is_rejected() -> None:
    device = make_chain()
    device.ip_address = "192.168.0.300"

    with pytest.raises(ValidationError) as error:
        device.full_clean()

    assert "ip_address" in error.value.message_dict


def test_empty_ip_address_is_allowed() -> None:
    device = make_chain()
    device.ip_address = None

    device.full_clean()
    device.save()
    assert Device.objects.get(pk=device.pk).ip_address is None


@pytest.mark.parametrize("key", ["APS-DPS", "aps_dps", "aps dps", "aps.dps", "äps", ""])
def test_invalid_key_is_rejected(key: str) -> None:
    device = make_chain()
    device.key = key
    device.plant.key = key

    with pytest.raises(ValidationError) as device_error:
        device.full_clean()
    with pytest.raises(ValidationError) as plant_error:
        device.plant.full_clean()

    assert "key" in device_error.value.message_dict
    assert "key" in plant_error.value.message_dict


@pytest.mark.parametrize("key", ["aps-dps", "ur5e-cell", "it-ot-firewall", "ccu-rpi"])
def test_valid_key_is_accepted(key: str) -> None:
    device = make_chain()
    device.key = key

    device.full_clean()


def test_long_notes_are_stored_unchanged() -> None:
    device = make_chain()
    text = "Notes; with semicolons, commas and umlauts äöü.\n" * 40
    assert len(text) > 1000
    device.notes = text
    device.address_source = text
    device.save()
    device.plant.notes = text
    device.plant.save()

    loaded = Device.objects.select_related("plant").get(pk=device.pk)
    assert loaded.notes == text
    assert loaded.address_source == text
    assert loaded.plant.notes == text


def test_free_text_fields_may_be_empty() -> None:
    site = Site.objects.create(name="Test site")
    area = Area.objects.create(site=site, name="Cell")
    plant = Plant.objects.create(area=area, key="ur5e-cell", name="Robot cell")
    device = Device(plant=plant, key="ur5e", name="Robot arm")

    device.full_clean()
    device.save()
    loaded = Device.objects.get(pk=device.pk)
    assert loaded.manufacturer == ""
    assert loaded.protocols == ""
    assert loaded.ip_address is None


def test_models_have_ordering_and_verbose_names() -> None:
    for model in (Site, Area, Plant, Device):
        assert model._meta.ordering
        assert str(model._meta.verbose_name) == model.__name__.lower()
        assert all(constraint.name for constraint in model._meta.constraints)
