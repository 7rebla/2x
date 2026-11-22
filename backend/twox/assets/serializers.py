"""Serializers of the structure API: site > area > plant > device.

Writes go through ``ModelSerializer.create`` and ``update``, that is through
``Model.save()``, so that the change log of work order 028 sees them.

Error messages of this module are marked for translation (work order 034).
"""

from typing import Any

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from twox.assets.csv_import import Counts, ImportReport, RowError
from twox.assets.integrity import (
    AREA_NAME_TAKEN,
    DEVICE_KEY_TAKEN,
    PLANT_KEY_TAKEN,
    SITE_NAME_TAKEN,
)
from twox.assets.models import Area, Device, Plant, Site, validate_key
from twox.files.serializers import UploadFileField


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
                        message=SITE_NAME_TAKEN,
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
            raise serializers.ValidationError({"name": [AREA_NAME_TAKEN]})
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
                        message=PLANT_KEY_TAKEN,
                    ),
                ]
            },
        }


# Fields of a device besides its id, its plant and the time stamps.
DEVICE_FIELDS = (
    "key",
    "name",
    "device_class",
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
                        message=DEVICE_KEY_TAKEN,
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


# --- CSV import of the device list (twox.assets.csv_import) ------------------


class FormBooleanField(serializers.BooleanField):
    """A boolean form field whose default applies when the form leaves it out.

    DRF reads a missing boolean of an HTML form as ``False`` (an unticked
    checkbox), whatever the default. For ``dry_run`` that would turn a form
    without the field into a real import.
    """

    default_empty_html = serializers.empty


class DeviceImportFormSerializer(serializers.Serializer[Any]):
    """Form of a device list import (``multipart/form-data``)."""

    file = UploadFileField(
        help_text=(
            "The device list as CSV: UTF-8, comma, the 13 columns of format version 1,"
            " optionally followed by device_class; at most TWOX_UPLOAD_MAX_BYTES bytes."
        )
    )
    dry_run = FormBooleanField(
        default=True,
        help_text="Check and count only, save nothing (default). Send false to save.",
    )


class ImportCountsSerializer(serializers.Serializer[Counts]):
    """What an import did, or would do in a dry run, at one level of the structure."""

    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    unchanged = serializers.IntegerField()


class ImportRowErrorSerializer(serializers.Serializer[RowError]):
    """An error in the imported file."""

    line = serializers.IntegerField(
        allow_null=True,
        help_text="Line where the row starts (the header is line 1); null for the whole file.",
    )
    column = serializers.CharField(
        allow_null=True, help_text="Column of the file; null for the whole row or file."
    )
    message = serializers.CharField()


class ImportReportSerializer(serializers.Serializer[ImportReport]):
    """Result of a device list import.

    ``saved`` is true only if the changes were saved. With errors nothing is
    saved and all counts are zero.
    """

    dry_run = serializers.BooleanField()
    saved = serializers.BooleanField()
    rows = serializers.IntegerField(help_text="Number of data rows read.")
    sites = ImportCountsSerializer()
    areas = ImportCountsSerializer()
    plants = ImportCountsSerializer()
    devices = ImportCountsSerializer()

    def get_fields(self) -> dict[str, serializers.Field[Any, Any, Any, Any]]:
        # "errors" names a property of every serializer, so the field cannot
        # be declared in the class body.
        fields = super().get_fields()
        fields["errors"] = ImportRowErrorSerializer(many=True)
        return fields
