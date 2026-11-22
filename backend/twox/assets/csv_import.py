"""CSV import of the device list (E-44), in the format of ``testfactory/layout/devices.csv``.

Format (version 1):

- Exactly the 13 columns of :data:`COLUMNS`, in this order, in the first line,
  optionally followed by a 14th column ``device_class`` (E-53). Every row has
  as many fields as the first line names.
- UTF-8; a byte order mark at the start is accepted. Comma as separator,
  double quotes as in RFC 4180 (a field may hold commas, quotes and line
  breaks).
- One row per device. A row without ``device_id`` names a plant without
  devices; its ``notes`` are the notes of the plant.

Mapping: ``site`` is the name of the site, ``area`` the name of the area at
that site, ``plant_id``/``plant_name`` the key and name of the plant,
``device_id``/``device_name`` the key and name of the device; the other
columns go one to one into the device fields. An empty ``ip_address`` is no
address. ``device_class`` must be one of the values of
:class:`~twox.assets.models.DeviceClass`; without the column, or with an
empty value, a new device gets ``other`` and a stored device keeps its class.

Rules (E-44): plants and devices are matched by their keys. Existing objects
are updated, new ones created, nothing is deleted; a device may move to
another plant. Sites and areas are matched by name and never renamed.
Contradictions inside the file are errors: one ``plant_id`` with another
name, area or site, and a ``device_id`` twice. Everything happens in one
transaction; any error, or a dry run, rolls all of it back.

The import works in two steps: :func:`parse` reads and checks the file
without touching the database, :func:`apply` writes. Each object is saved on
its own with ``save()`` inside :func:`~twox.accounts.audit.acting_as`, so the
change log names the importing user (E-43); ``bulk_create`` would bypass it.

The content of the file is data, never instructions: values are stored as
text exactly as given (apart from leading and trailing spaces). A value that
starts with ``=``, ``+``, ``-`` or ``@`` is stored as it is; an export to CSV
(not built yet) must neutralise such values against formula injection.

Limits: at most :data:`MAX_ROWS` rows, at most :data:`MAX_LINE_BYTES` bytes
per line and the field limit of Python's ``csv`` module per field; at most
:data:`MAX_ERRORS` errors are listed. The API also limits the size of the
upload (``TWOX_UPLOAD_MAX_BYTES``).

Messages are marked for translation (work order 034).
"""

import csv
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from django.db import IntegrityError, transaction
from django.utils.translation import gettext
from rest_framework import serializers

from twox.accounts.audit import acting_as
from twox.accounts.models import User
from twox.assets.integrity import unique_violation
from twox.assets.models import (
    KEY_MAX_LENGTH,
    NAME_MAX_LENGTH,
    Area,
    Device,
    DeviceClass,
    Plant,
    Site,
    validate_key,
)

#: The required columns of format version 1, in this order.
COLUMNS: tuple[str, ...] = (
    "site",
    "area",
    "plant_id",
    "plant_name",
    "device_id",
    "device_name",
    "manufacturer",
    "model",
    "software_version",
    "ip_address",
    "address_source",
    "protocols",
    "notes",
)

#: The optional last column (E-53): the class of the device.
DEVICE_CLASS_COLUMN = "device_class"

#: The columns of a file with the optional last column, in this order.
COLUMNS_WITH_DEVICE_CLASS: tuple[str, ...] = (*COLUMNS, DEVICE_CLASS_COLUMN)

#: Columns that describe a device and stay empty in a row without ``device_id``.
#: (``notes`` is the exception: without a device it holds the plant's notes.)
DEVICE_ONLY_COLUMNS: tuple[str, ...] = (
    "device_name",
    "manufacturer",
    "model",
    "software_version",
    "ip_address",
    "address_source",
    "protocols",
    DEVICE_CLASS_COLUMN,
)

#: Device fields filled from the column of the same name (besides key and name).
DEVICE_VALUE_FIELDS: tuple[str, ...] = (
    "manufacturer",
    "model",
    "software_version",
    "ip_address",
    "address_source",
    "protocols",
    "notes",
)

#: Most data rows of one file. More rows are an error for the whole file.
MAX_ROWS = 10_000

#: Most errors listed; reading stops after the row that reaches the limit.
MAX_ERRORS = 1_000

#: Longest physical line in bytes, line break included. 14 fields at the
#: ``csv`` field limit (131072 characters of up to 4 bytes) fit.
MAX_LINE_BYTES = 8 * 1024 * 1024

_UTF8_BOM = b"\xef\xbb\xbf"

#: Column of the file that a unique constraint of the structure belongs to.
_CONSTRAINT_COLUMNS: dict[str, str] = {
    "assets_site_name_unique": "site",
    "assets_area_site_name_unique": "area",
    "assets_plant_key_unique": "plant_id",
    "assets_device_key_unique": "device_id",
}

#: Longest header name repeated in an error message.
_ECHO_MAX_CHARS = 40


class ByteLines(Protocol):
    """A binary stream read line by line: an open file or an uploaded file."""

    def readline(self, size: int = -1, /) -> bytes: ...


@dataclass(frozen=True)
class RowError:
    """An error in the file.

    ``line`` is the line where the row starts (the header is line 1);
    ``None`` for the file as a whole. ``column`` is one of
    :data:`COLUMNS_WITH_DEVICE_CLASS`, or ``None`` for the whole row.
    """

    line: int | None
    column: str | None
    message: str


@dataclass
class PlantRow:
    """A plant as the file describes it, from the first row that names it."""

    line: int
    site: str
    area: str
    key: str
    name: str
    #: From the row without ``device_id``; ``None`` if the file has no such
    #: row for this plant (then stored notes stay as they are).
    notes: str | None = None
    notes_line: int | None = None


@dataclass(frozen=True)
class DeviceRow:
    """A device as one row describes it."""

    line: int
    plant_key: str
    key: str
    name: str
    #: The fields of :data:`DEVICE_VALUE_FIELDS`; ``ip_address`` may be ``None``.
    #: ``device_class`` only if the row gives one; otherwise a new device gets
    #: the default and a stored device keeps its class.
    values: Mapping[str, str | None]


@dataclass
class ParsedFile:
    """Result of :func:`parse`: the plants and devices in file order, and the errors."""

    rows: int = 0
    plants: list[PlantRow] = field(default_factory=list)
    devices: list[DeviceRow] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)


@dataclass
class Counts:
    """What the import did (or would do) at one level of the structure."""

    created: int = 0
    updated: int = 0
    unchanged: int = 0


@dataclass
class ImportReport:
    """Result of :func:`apply`.

    ``saved`` is true only if the changes were committed: no dry run and no
    error. With errors the counts are zero and nothing was saved.
    """

    dry_run: bool
    saved: bool = False
    rows: int = 0
    sites: Counts = field(default_factory=Counts)
    areas: Counts = field(default_factory=Counts)
    plants: Counts = field(default_factory=Counts)
    devices: Counts = field(default_factory=Counts)
    errors: list[RowError] = field(default_factory=list)


# --- reading -----------------------------------------------------------------


class _StopParsingError(Exception):
    """The rest of the file cannot be read; ``error`` says why."""

    def __init__(self, error: RowError) -> None:
        super().__init__(error.message)
        self.error = error


class _Lines:
    """Decoded lines of a binary stream, counting the physical lines read."""

    def __init__(self, stream: ByteLines) -> None:
        self.stream = stream
        self.count = 0

    def __iter__(self) -> Iterator[str]:
        while True:
            raw = self.stream.readline(MAX_LINE_BYTES + 1)
            if not raw:
                return
            self.count += 1
            if len(raw) > MAX_LINE_BYTES:
                raise _StopParsingError(
                    RowError(
                        self.count,
                        None,
                        gettext("The line is longer than %(limit)d bytes.")
                        % {"limit": MAX_LINE_BYTES},
                    )
                )
            if self.count == 1 and raw.startswith(_UTF8_BOM):
                raw = raw[len(_UTF8_BOM) :]
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as error:
                raise _StopParsingError(
                    RowError(
                        self.count,
                        None,
                        gettext(
                            "The file is not UTF-8 (byte %(position)d of this line)."
                            " Save it as UTF-8 and try again."
                        )
                        % {"position": error.start + 1},
                    )
                ) from error
            yield text


def _echo(name: str) -> str:
    """A header name from the file, shortened for an error message."""
    if len(name) <= _ECHO_MAX_CHARS:
        return name
    return name[:_ECHO_MAX_CHARS] + "…"


def _header_error(header: Sequence[str]) -> RowError:
    message = gettext(
        "The first line must name exactly these %(count)d columns in this order: %(columns)s."
    ) % {"count": len(COLUMNS), "columns": ", ".join(COLUMNS)}
    message += " " + gettext("The column %(column)s may follow as the last one.") % {
        "column": DEVICE_CLASS_COLUMN
    }
    missing = [column for column in COLUMNS if column not in header]
    unexpected = [_echo(name) for name in header if name not in COLUMNS_WITH_DEVICE_CLASS][
        : len(COLUMNS_WITH_DEVICE_CLASS)
    ]
    if missing:
        message += " " + gettext("Missing: %(columns)s.") % {"columns": ", ".join(missing)}
    if unexpected:
        message += " " + gettext("Not expected: %(columns)s.") % {"columns": ", ".join(unexpected)}
    if len(header) == 1 and ";" in header[0]:
        message += " " + gettext("The separator must be a comma, not a semicolon.")
    return RowError(1, None, message)


def _csv_error(line: int, error: csv.Error) -> RowError:
    if "field larger than field limit" in str(error):
        message = gettext("A field in this row is longer than %(limit)d characters.") % {
            "limit": csv.field_size_limit()
        }
    else:
        message = gettext("The row is not valid CSV: %(reason)s.") % {"reason": error}
    return RowError(line, None, message + " " + gettext("The rest of the file was not checked."))


class DeviceListRowSerializer(serializers.Serializer[Any]):
    """Checks one row: lengths, key format, IP address and which columns go together.

    Leading and trailing spaces are removed; an empty ``ip_address`` becomes
    ``None``.
    """

    site = serializers.CharField(max_length=NAME_MAX_LENGTH)
    area = serializers.CharField(max_length=NAME_MAX_LENGTH)
    plant_id = serializers.CharField(max_length=KEY_MAX_LENGTH, validators=[validate_key])
    plant_name = serializers.CharField(max_length=NAME_MAX_LENGTH)
    device_id = serializers.CharField(
        max_length=KEY_MAX_LENGTH, validators=[validate_key], allow_blank=True
    )
    device_name = serializers.CharField(max_length=NAME_MAX_LENGTH, allow_blank=True)
    manufacturer = serializers.CharField(allow_blank=True)
    model = serializers.CharField(allow_blank=True)
    software_version = serializers.CharField(allow_blank=True)
    ip_address = serializers.IPAddressField(allow_blank=True)
    address_source = serializers.CharField(allow_blank=True)
    protocols = serializers.CharField(allow_blank=True)
    notes = serializers.CharField(allow_blank=True)
    # Only in a file with the optional last column.
    device_class = serializers.CharField(allow_blank=True, required=False)

    def validate_device_class(self, value: str) -> str:
        if value and value not in DeviceClass.values:
            raise serializers.ValidationError(
                gettext('"%(value)s" is not a device class. Use one of: %(values)s.')
                % {"value": _echo(value), "values": ", ".join(DeviceClass.values)}
            )
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        errors: dict[str, list[str]] = {}
        if attrs["device_id"]:
            if not attrs["device_name"]:
                errors["device_name"] = [gettext("A row with a device_id needs a device_name.")]
        else:
            for column in DEVICE_ONLY_COLUMNS:
                if attrs.get(column):
                    errors[column] = [
                        gettext(
                            "This column describes a device; leave it empty in a row"
                            " without device_id."
                        )
                    ]
        if errors:
            raise serializers.ValidationError(errors)
        attrs["ip_address"] = attrs["ip_address"] or None
        return attrs


class _Collector:
    """Turns checked rows into plants and devices and finds contradictions."""

    def __init__(self, parsed: ParsedFile, columns: tuple[str, ...]) -> None:
        self.parsed = parsed
        #: The columns of the file: :data:`COLUMNS` or :data:`COLUMNS_WITH_DEVICE_CLASS`.
        self.columns = columns
        self.plants: dict[str, PlantRow] = {}
        self.device_lines: dict[str, int] = {}

    def error(self, line: int, column: str | None, message: str) -> None:
        self.parsed.errors.append(RowError(line, column, message))

    def add(self, line: int, record: list[str]) -> None:
        if len(record) != len(self.columns):
            self.error(
                line,
                None,
                gettext("The row has %(found)d fields instead of %(expected)d.")
                % {"found": len(record), "expected": len(self.columns)},
            )
            return
        row = DeviceListRowSerializer(data=dict(zip(self.columns, record, strict=True)))
        if not row.is_valid():
            for column, messages in row.errors.items():
                for message in messages:
                    self.error(line, column if column in self.columns else None, str(message))
            return
        values: dict[str, Any] = row.validated_data
        plant = self.plant(line, values)
        if values["device_id"]:
            self.device(line, values)
        elif plant is not None:
            self.plant_notes(line, plant, values["notes"])

    def plant(self, line: int, values: Mapping[str, Any]) -> PlantRow | None:
        """The plant of the row; ``None`` if the row contradicts an earlier one."""
        key: str = values["plant_id"]
        known = self.plants.get(key)
        if known is None:
            known = PlantRow(
                line=line,
                site=values["site"],
                area=values["area"],
                key=key,
                name=values["plant_name"],
            )
            self.plants[key] = known
            self.parsed.plants.append(known)
            return known
        consistent = True
        for column, value, earlier in (
            ("site", values["site"], known.site),
            ("area", values["area"], known.area),
            ("plant_name", values["plant_name"], known.name),
        ):
            if value != earlier:
                consistent = False
                self.error(
                    line,
                    column,
                    gettext("Line %(line)d gives the plant %(key)s another value in this column.")
                    % {"line": known.line, "key": key},
                )
        return known if consistent else None

    def device(self, line: int, values: Mapping[str, Any]) -> None:
        key: str = values["device_id"]
        earlier = self.device_lines.get(key)
        if earlier is not None:
            self.error(
                line,
                "device_id",
                gettext("The device %(key)s appears in line %(line)d already.")
                % {"key": key, "line": earlier},
            )
            return
        self.device_lines[key] = line
        device_values: dict[str, str | None] = {name: values[name] for name in DEVICE_VALUE_FIELDS}
        if values.get(DEVICE_CLASS_COLUMN):
            device_values[DEVICE_CLASS_COLUMN] = values[DEVICE_CLASS_COLUMN]
        self.parsed.devices.append(
            DeviceRow(
                line=line,
                plant_key=values["plant_id"],
                key=key,
                name=values["device_name"],
                values=device_values,
            )
        )

    def plant_notes(self, line: int, plant: PlantRow, notes: str) -> None:
        if plant.notes_line is None:
            plant.notes = notes
            plant.notes_line = line
        elif plant.notes != notes:
            self.error(
                line,
                "notes",
                gettext("Line %(line)d gives the plant %(key)s other notes.")
                % {"line": plant.notes_line, "key": plant.key},
            )


def parse(stream: ByteLines) -> ParsedFile:
    """Read and check a device list; nothing is written.

    Errors carry the line where the row starts and the column. A wrong
    header, bytes that are not UTF-8, a line or field over the limits, CSV
    that cannot be read and more than :data:`MAX_ROWS` rows stop the
    reading; other errors are collected for every row, up to
    :data:`MAX_ERRORS`.
    """
    parsed = ParsedFile()
    lines = _Lines(stream)
    reader = csv.reader(iter(lines), dialect="excel", strict=True)
    start = 1
    try:
        header = next(reader, None)
        if header is None:
            parsed.errors.append(RowError(None, None, gettext("The file is empty.")))
            return parsed
        columns = tuple(header)
        if columns not in (COLUMNS, COLUMNS_WITH_DEVICE_CLASS):
            parsed.errors.append(_header_error(header))
            return parsed
        collector = _Collector(parsed, columns)
        while True:
            start = lines.count + 1
            record = next(reader, None)
            if record is None:
                break
            if not any(value.strip() for value in record):
                continue  # empty line
            parsed.rows += 1
            if parsed.rows > MAX_ROWS:
                parsed.errors.append(
                    RowError(
                        start,
                        None,
                        gettext("The file has more than %(limit)d rows.") % {"limit": MAX_ROWS},
                    )
                )
                break
            collector.add(start, record)
            if len(parsed.errors) >= MAX_ERRORS:
                parsed.errors.append(
                    RowError(
                        None,
                        None,
                        gettext("More than %(limit)d errors; reading stopped at line %(line)d.")
                        % {"limit": MAX_ERRORS, "line": start},
                    )
                )
                break
    except _StopParsingError as stop:
        parsed.errors.append(stop.error)
    except csv.Error as error:
        parsed.errors.append(_csv_error(start, error))
    return parsed


# --- writing -----------------------------------------------------------------


class _Writer:
    """Creates and updates the objects of a parsed file and counts what it did."""

    def __init__(self, parsed: ParsedFile, report: ImportReport) -> None:
        self.parsed = parsed
        self.report = report
        #: Line of the row being written, for an error from the database.
        self.line: int | None = None
        self.sites: dict[str, Site] = {}
        self.areas: dict[tuple[str, str], Area] = {}
        self.plants: dict[str, Plant] = {}

    def write(self) -> None:
        stored_sites = Site.objects.in_bulk(
            {plant.site for plant in self.parsed.plants}, field_name="name"
        )
        stored_areas = {
            (area.site.name, area.name): area
            for area in Area.objects.select_related("site").filter(
                site__name__in={plant.site for plant in self.parsed.plants},
                name__in={plant.area for plant in self.parsed.plants},
            )
        }
        stored_plants = Plant.objects.in_bulk(
            [plant.key for plant in self.parsed.plants], field_name="key"
        )
        stored_devices = Device.objects.in_bulk(
            [device.key for device in self.parsed.devices], field_name="key"
        )
        for plant_row in self.parsed.plants:
            self.line = plant_row.line
            site = self.site(plant_row.site, stored_sites.get(plant_row.site))
            area_key = (plant_row.site, plant_row.area)
            area = self.area(site, plant_row.area, stored_areas.get(area_key))
            self.plants[plant_row.key] = self.plant(plant_row, area, stored_plants)
        for device_row in self.parsed.devices:
            self.line = device_row.line
            self.device(device_row, self.plants[device_row.plant_key], stored_devices)

    def site(self, name: str, stored: Site | None) -> Site:
        site = self.sites.get(name)
        if site is not None:
            return site
        if stored is None:
            site = Site(name=name)
            site.save()
            self.report.sites.created += 1
        else:
            site = stored
            self.report.sites.unchanged += 1
        self.sites[name] = site
        return site

    def area(self, site: Site, name: str, stored: Area | None) -> Area:
        area = self.areas.get((site.name, name))
        if area is not None:
            return area
        if stored is None:
            area = Area(site=site, name=name)
            area.save()
            self.report.areas.created += 1
        else:
            area = stored
            self.report.areas.unchanged += 1
        self.areas[(site.name, name)] = area
        return area

    def plant(self, row: PlantRow, area: Area, stored: Mapping[str, Plant]) -> Plant:
        plant = stored.get(row.key)
        if plant is None:
            plant = Plant(area=area, key=row.key, name=row.name, notes=row.notes or "")
            plant.save()
            self.report.plants.created += 1
            return plant
        wanted: dict[str, Any] = {"area_id": area.pk, "name": row.name}
        if row.notes is not None:
            wanted["notes"] = row.notes
        self.update(plant, wanted, self.report.plants)
        return plant

    def device(self, row: DeviceRow, plant: Plant, stored: Mapping[str, Device]) -> None:
        device = stored.get(row.key)
        if device is None:
            Device(plant=plant, key=row.key, name=row.name, **row.values).save()
            self.report.devices.created += 1
            return
        wanted: dict[str, Any] = {"plant_id": plant.pk, "name": row.name, **row.values}
        self.update(device, wanted, self.report.devices)

    @staticmethod
    def update(instance: Plant | Device, wanted: Mapping[str, Any], counts: Counts) -> None:
        """Set the fields that differ and save once; count as updated or unchanged."""
        changed = False
        for name, value in wanted.items():
            if getattr(instance, name) != value:
                setattr(instance, name, value)
                changed = True
        if changed:
            instance.save()
            counts.updated += 1
        else:
            counts.unchanged += 1


def _integrity_error(line: int | None, error: IntegrityError) -> RowError:
    retry = gettext("Another change was saved at the same time; run the import again.")
    violation = unique_violation(error)
    if violation is None:
        return RowError(line, None, gettext("The database refused this row.") + " " + retry)
    column = _CONSTRAINT_COLUMNS.get(violation.constraint)
    return RowError(line, column, f"{violation.message} {retry}")


def apply(parsed: ParsedFile, user: User, dry_run: bool) -> ImportReport:
    """Write a parsed file in one transaction, with ``user`` as the actor in the change log.

    Nothing is written if ``parsed`` has errors. A dry run does all the work
    and rolls it back, so its counts say what a real run would do. An error
    from the database (another change saved at the same time) rolls back
    everything and is reported at the row being written.
    """
    report = ImportReport(dry_run=dry_run, rows=parsed.rows, errors=list(parsed.errors))
    if report.errors:
        return report
    writer = _Writer(parsed, report)
    try:
        with acting_as(user), transaction.atomic():
            writer.write()
            if dry_run:
                transaction.set_rollback(True)
    except IntegrityError as error:
        failed = ImportReport(dry_run=dry_run, rows=parsed.rows)
        failed.errors.append(_integrity_error(writer.line, error))
        return failed
    report.saved = not dry_run
    return report
