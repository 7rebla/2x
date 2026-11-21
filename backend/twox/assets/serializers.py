"""Serializers of the structure API: site > area > plant > device.

Writes go through ``ModelSerializer.create`` and ``update``, that is through
``Model.save()``, so that the change log of work order 028 sees them.

Error messages of this module are marked for translation (work order 034).
"""

from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from twox.assets.models import Area, Device, Plant, Site, validate_key


class SiteSerializer(serializers.ModelSerializer[Site]):
    """A site of the operation."""

    class Meta:
        model = Site
        fields = ("id", "name", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")
        extra_kwargs = {  # noqa: RUF012 - DRF reads this mapping as is.
            "name": {
                "validators": [
                    UniqueValidator(
                        queryset=Site.objects.all(),
                        message=_("A site with this name exists already."),
                    )
                ]
            },
        }


class AreaSerializer(serializers.ModelSerializer[Area]):
    """An area of a site. ``site`` is the id of the site."""

    class Meta:
        model = Area
        fields = ("id", "site", "name", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")
        # The pair (site, name) is unique. validate() reports a clash at the
        # field name instead of DRF's general unique-together message.
        validators = ()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        site = attrs.get("site", self.instance.site if self.instance else None)
        name = attrs.get("name", self.instance.name if self.instance else None)
        clashes = Area.objects.filter(site=site, name=name)
        if self.instance is not None:
            clashes = clashes.exclude(pk=self.instance.pk)
        if clashes.exists():
            raise serializers.ValidationError(
                {"name": [_("This site has an area with this name already.")]}
            )
        return attrs


class PlantSerializer(serializers.ModelSerializer[Plant]):
    """A plant of an area. ``area`` is the id of the area."""

    class Meta:
        model = Plant
        fields = ("id", "area", "key", "name", "notes", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")
        extra_kwargs = {  # noqa: RUF012 - DRF reads this mapping as is.
            "key": {
                "validators": [
                    validate_key,
                    UniqueValidator(
                        queryset=Plant.objects.all(),
                        message=_("A plant with this key exists already."),
                    ),
                ]
            },
        }


# Fields of a device besides its id, its plant and the time stamps.
DEVICE_FIELDS = (
    "key",
    "name",
    "manufacturer",
    "model",
    "software_version",
    "ip_address",
    "address_source",
    "protocols",
    "notes",
)


class DeviceWriteSerializer(serializers.ModelSerializer[Device]):
    """Input for creating and changing a device. ``plant`` is the id of the plant.

    An empty IP address is stored as no address (``null``).
    """

    class Meta:
        model = Device
        fields = ("plant", *DEVICE_FIELDS)
        extra_kwargs = {  # noqa: RUF012 - DRF reads this mapping as is.
            "key": {
                "validators": [
                    validate_key,
                    UniqueValidator(
                        queryset=Device.objects.all(),
                        message=_("A device with this key exists already."),
                    ),
                ]
            },
            # A form sends an empty field as "": accepted, stored as null.
            "ip_address": {"allow_blank": True},
        }

    def validate_ip_address(self, value: str | None) -> str | None:
        return value or None


class PlantRefSerializer(serializers.ModelSerializer[Plant]):
    """The plant of a device, for reading."""

    class Meta:
        model = Plant
        fields = ("id", "key", "name")
        read_only_fields = fields


class AreaRefSerializer(serializers.ModelSerializer[Area]):
    """The area of a device, for reading."""

    class Meta:
        model = Area
        fields = ("id", "name")
        read_only_fields = fields


class SiteRefSerializer(serializers.ModelSerializer[Site]):
    """The site of a device, for reading."""

    class Meta:
        model = Site
        fields = ("id", "name")
        read_only_fields = fields


class DeviceSerializer(serializers.ModelSerializer[Device]):
    """A device with its chain plant > area > site, for reading."""

    plant = PlantRefSerializer(read_only=True)
    area = AreaRefSerializer(source="plant.area", read_only=True)
    site = SiteRefSerializer(source="plant.area.site", read_only=True)

    class Meta:
        model = Device
        fields = ("id", "plant", "area", "site", *DEVICE_FIELDS, "created_at", "updated_at")
        read_only_fields = fields
