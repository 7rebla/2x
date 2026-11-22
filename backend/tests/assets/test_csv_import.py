"""CSV import of the device list (twox.assets.csv_import): reading, checks and writing."""

import csv
import io
from typing import Any

import pytest
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from tests.accounts.users import make_user
from tests.assets.csv_files import (
    TESTFACTORY_DEVICE_CLASSES,
    TESTFACTORY_DEVICES_CSV,
    csv_file,
    csv_text,
    factory_rows,
    plant_row,
    raw_file,
    row,
)
from twox.accounts.models import User
from twox.assets import csv_import
from twox.assets.csv_import import (
    COLUMNS,
    COLUMNS_WITH_DEVICE_CLASS,
    DEVICE_CLASS_COLUMN,
    ImportReport,
    ParsedFile,
    RowError,
    apply,
    parse,
)
from twox.assets.models import Area, Device, DeviceClass, Plant, Site

pytestmark = pytest.mark.django_db


@pytest.fixture
def importer() -> User:
    user = make_user("manage")
    assert user is not None
    return user


def import_testfactory(user: User, dry_run: bool = False) -> ImportReport:
    with TESTFACTORY_DEVICES_CSV.open("rb") as stream:
        return apply(parse(stream), user, dry_run=dry_run)


def counts(report: ImportReport) -> dict[str, tuple[int, int, int]]:
    """``{level: (created, updated, unchanged)}``."""
    return {
        level: (value.created, value.updated, value.unchanged)
        for level, value in (
            ("sites", report.sites),
            ("areas", report.areas),
            ("plants", report.plants),
            ("devices", report.devices),
        )
    }


def errors_of(parsed: ParsedFile) -> list[tuple[int | None, str | None]]:
    return [(error.line, error.column) for error in parsed.errors]


def structure_entries() -> int:
    """Number of change log entries of the structure models."""
    return LogEntry.objects.filter(
        content_type__in=ContentType.objects.get_for_models(Site, Area, Plant, Device).values()
    ).count()


def structure_snapshot() -> list[tuple[Any, ...]]:
    """Every stored value of the structure, to compare before and after."""
    return [
        *Site.objects.values_list(),
        *Area.objects.values_list(),
        *Plant.objects.values_list(),
        *Device.objects.values_list(),
    ]


# --- acceptance case: the device list of the test factory -------------------


def test_testfactory_device_list_is_imported(importer: User) -> None:
    report = import_testfactory(importer)

    assert report.errors == []
    assert report.saved is True
    assert report.dry_run is False
    assert report.rows == 14
    assert counts(report) == {
        "sites": (1, 0, 0),
        "areas": (3, 0, 0),
        "plants": (10, 0, 0),
        "devices": (13, 0, 0),
    }
    assert Site.objects.count() == 1
    assert sorted(Area.objects.values_list("name", flat=True)) == [
        "Fertigungslinie",
        "Netzübergang",
        "Roboterzelle",
    ]
    assert Plant.objects.count() == 10
    assert Device.objects.count() == 13
    assert Device.objects.filter(ip_address__isnull=True).count() == 6


def test_testfactory_plant_without_device_keeps_its_notes(importer: User) -> None:
    import_testfactory(importer)

    charging = Plant.objects.get(key="aps-charging")
    source = next(values for values in factory_rows() if values["plant_id"] == "aps-charging")
    assert not charging.devices.exists()
    assert charging.notes == source["notes"]
    assert charging.notes


def test_testfactory_values_arrive_unchanged(importer: User) -> None:
    import_testfactory(importer)

    rows = factory_rows()
    for values in rows:
        plant = Plant.objects.select_related("area__site").get(key=values["plant_id"])
        assert plant.name == values["plant_name"]
        assert plant.area.name == values["area"]
        assert plant.area.site.name == values["site"]
        if not values["device_id"]:
            continue
        device = Device.objects.get(key=values["device_id"])
        assert device.plant == plant
        assert device.name == values["device_name"]
        assert device.ip_address == (values["ip_address"] or None)
        for column in ("manufacturer", "model", "software_version", "address_source"):
            assert getattr(device, column) == values[column], (values["device_id"], column)
        assert device.protocols == values["protocols"]
        assert device.notes == values["notes"]
        assert device.device_class == values["device_class"]
    # Umlauts stay as they are.
    assert Plant.objects.get(key="aps-mill").name == "Frässtation"
    assert Area.objects.filter(name="Netzübergang").exists()
    assert any("ä" in values["plant_name"] for values in rows)


def test_testfactory_devices_get_their_classes(importer: User) -> None:
    import_testfactory(importer)

    assert dict(Device.objects.values_list("key", "device_class")) == TESTFACTORY_DEVICE_CLASSES
    # Every class but "other" occurs at least once.
    assert set(TESTFACTORY_DEVICE_CLASSES.values()) == set(DeviceClass.values) - {"other"}


def test_second_import_of_the_same_file_changes_nothing(importer: User) -> None:
    import_testfactory(importer)
    entries = LogEntry.objects.count()
    before = structure_snapshot()

    report = import_testfactory(importer)

    assert report.errors == []
    assert counts(report) == {
        "sites": (0, 0, 1),
        "areas": (0, 0, 3),
        "plants": (0, 0, 10),
        "devices": (0, 0, 13),
    }
    assert structure_snapshot() == before
    assert LogEntry.objects.count() == entries


def test_changed_value_updates_one_device_with_a_log_entry(importer: User) -> None:
    import_testfactory(importer)
    rows = factory_rows()
    changed = next(values for values in rows if values["device_id"] == "hbw-plc")
    old = changed["software_version"]
    changed["software_version"] = "SPS-Projekt HBWv1_4_0 (test value)"

    report = apply(parse(csv_file(rows)), importer, dry_run=False)

    assert report.errors == []
    assert counts(report)["devices"] == (0, 1, 12)
    assert counts(report)["plants"] == (0, 0, 10)
    device = Device.objects.get(key="hbw-plc")
    assert device.software_version == "SPS-Projekt HBWv1_4_0 (test value)"
    entries = LogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(Device),
        object_id=device.pk,
        action=LogEntry.Action.UPDATE,
    )
    assert entries.count() == 1
    entry = entries.get()
    assert entry.actor == importer
    assert entry.changes == {"software_version": [old, "SPS-Projekt HBWv1_4_0 (test value)"]}


def test_import_logs_every_new_object_with_the_importer(importer: User) -> None:
    import_testfactory(importer)

    created = LogEntry.objects.filter(
        action=LogEntry.Action.CREATE,
        content_type__in=ContentType.objects.get_for_models(Site, Area, Plant, Device).values(),
    )
    assert created.count() == 1 + 3 + 10 + 13
    assert structure_entries() == created.count()
    assert set(created.values_list("actor", flat=True)) == {importer.pk}


def test_dry_run_changes_nothing(importer: User) -> None:
    report = import_testfactory(importer, dry_run=True)

    assert report.errors == []
    assert report.dry_run is True
    assert report.saved is False
    # The counts say what a real import would do.
    assert counts(report)["devices"] == (13, 0, 0)
    assert structure_snapshot() == []
    assert structure_entries() == 0


def test_dry_run_of_a_change_changes_nothing(importer: User) -> None:
    import_testfactory(importer)
    before = structure_snapshot()
    entries = LogEntry.objects.count()
    rows = factory_rows()
    rows[0]["device_name"] = "Renamed in a dry run"

    report = apply(parse(csv_file(rows)), importer, dry_run=True)

    assert counts(report)["devices"] == (0, 1, 12)
    assert structure_snapshot() == before
    assert LogEntry.objects.count() == entries


# --- format ------------------------------------------------------------------


def test_columns_are_the_header_of_the_testfactory_file() -> None:
    with TESTFACTORY_DEVICES_CSV.open(encoding="utf-8", newline="") as stream:
        header = next(csv.reader(stream))

    assert tuple(header) == COLUMNS_WITH_DEVICE_CLASS
    assert (*COLUMNS, "device_class") == COLUMNS_WITH_DEVICE_CLASS
    assert len(COLUMNS) == 13


def test_byte_order_mark_is_accepted() -> None:
    parsed = parse(io.BytesIO(b"\xef\xbb\xbf" + csv_text([row()]).encode()))

    assert parsed.errors == []
    assert [device.key for device in parsed.devices] == ["press-plc"]


def test_lf_line_ends_are_accepted() -> None:
    text = csv_text([row(), row(device_id="press-hmi", device_name="HMI")]).replace("\r\n", "\n")

    parsed = parse(raw_file(text))

    assert parsed.errors == []
    assert len(parsed.devices) == 2


def test_quoted_fields_keep_commas_quotes_and_line_breaks() -> None:
    notes = 'First line, with comma\nsecond line with "quotes"'

    parsed = parse(csv_file([row(notes=notes)]))

    assert parsed.errors == []
    assert parsed.devices[0].values["notes"] == notes


def test_spaces_around_values_are_removed() -> None:
    parsed = parse(csv_file([row(device_name="  Press PLC  ", ip_address=" 192.0.2.10 ")]))

    assert parsed.devices[0].name == "Press PLC"
    assert parsed.devices[0].values["ip_address"] == "192.0.2.10"


def test_empty_lines_are_skipped() -> None:
    text = csv_text([row()]) + "\r\n,,,,,,,,,,,,\r\n"

    parsed = parse(raw_file(text))

    assert parsed.errors == []
    assert parsed.rows == 1


def test_header_only_imports_nothing(importer: User) -> None:
    report = apply(parse(csv_file([])), importer, dry_run=False)

    assert report.errors == []
    assert report.rows == 0
    assert report.saved is True


def test_empty_file_is_an_error() -> None:
    parsed = parse(io.BytesIO(b""))

    assert parsed.errors == [RowError(None, None, "The file is empty.")]


# --- errors with line and column ---------------------------------------------


@pytest.mark.parametrize(
    "header",
    [
        ["site", "area", "plant", "plant_name"],
        list(reversed(COLUMNS)),
        [*COLUMNS, "extra"],
        [*COLUMNS_WITH_DEVICE_CLASS, "extra"],
        [DEVICE_CLASS_COLUMN, *COLUMNS],
        [*COLUMNS[:-1], DEVICE_CLASS_COLUMN, "notes"],
        [*COLUMNS, "DEVICE_CLASS"],
        [column.upper() for column in COLUMNS],
        ["Standort", *COLUMNS[1:]],
    ],
)
def test_wrong_header_is_an_error_for_the_whole_file(header: list[str]) -> None:
    parsed = parse(csv_file([row()], header=header))

    assert errors_of(parsed) == [(1, None)]
    assert "site, area, plant_id" in parsed.errors[0].message
    assert "The column device_class may follow as the last one." in parsed.errors[0].message
    assert parsed.devices == []
    assert parsed.plants == []


def test_header_error_does_not_call_device_class_unexpected() -> None:
    header = ["site", "Bereich", *COLUMNS[2:], DEVICE_CLASS_COLUMN, "extra"]

    message = parse(csv_file([row()], header=header)).errors[0].message

    assert "Not expected: Bereich, extra." in message


def test_header_error_names_missing_and_unexpected_columns() -> None:
    header = ["site", "Bereich", *COLUMNS[2:]]

    message = parse(csv_file([row()], header=header)).errors[0].message

    assert "Missing: area." in message
    assert "Not expected: Bereich." in message


def test_long_unexpected_header_name_is_shortened() -> None:
    header = ["x" * 5000, *COLUMNS[1:]]

    message = parse(csv_file([row()], header=header)).errors[0].message

    assert "x" * 40 + "…" in message
    assert "x" * 41 not in message


def test_error_list_is_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(csv_import, "MAX_ERRORS", 3)
    rows = [row(device_id=f"d{number}", ip_address="bad") for number in range(5)]

    parsed = parse(csv_file(rows))

    assert errors_of(parsed) == [
        (2, "ip_address"),
        (3, "ip_address"),
        (4, "ip_address"),
        (None, None),
    ]
    assert "More than 3 errors; reading stopped at line 4." in parsed.errors[-1].message


def test_semicolon_file_gets_a_hint() -> None:
    text = csv_text([row()]).replace(",", ";")

    parsed = parse(raw_file(text))

    assert errors_of(parsed) == [(1, None)]
    assert "comma, not a semicolon" in parsed.errors[0].message


def test_comma_header_gets_no_semicolon_hint() -> None:
    message = parse(csv_file([row()], header=["site"])).errors[0].message

    assert "semicolon" not in message


@pytest.mark.parametrize("address", ["999.1.1.1", "192.0.2", "host.example", "192.0.2.1/24"])
def test_invalid_ip_address_is_an_error_at_its_line_and_column(address: str) -> None:
    parsed = parse(csv_file([plant_row(), row(ip_address=address)]))

    assert errors_of(parsed) == [(3, "ip_address")]


def test_ipv6_address_is_normalised() -> None:
    parsed = parse(csv_file([row(ip_address="2001:DB8::0:1")]))

    assert parsed.devices[0].values["ip_address"] == "2001:db8::1"


def test_duplicate_device_id_is_an_error_at_the_second_line() -> None:
    parsed = parse(csv_file([row(), plant_row(), row(device_name="Other name")]))

    assert errors_of(parsed) == [(4, "device_id")]
    assert "line 2" in parsed.errors[0].message


@pytest.mark.parametrize(
    ("change", "column"),
    [
        ({"plant_name": "Another press"}, "plant_name"),
        ({"area": "Line 2"}, "area"),
        ({"site": "South"}, "site"),
    ],
)
def test_contradicting_plant_is_an_error(change: dict[str, str], column: str) -> None:
    second = row(device_id="press-hmi", device_name="Press HMI", **change)

    parsed = parse(csv_file([row(), second]))

    assert errors_of(parsed) == [(3, column)]
    assert "Line 2" in parsed.errors[0].message
    assert "press" in parsed.errors[0].message


def test_plant_without_device_with_other_notes_twice_is_an_error() -> None:
    parsed = parse(csv_file([plant_row(notes="One"), plant_row(notes="Two")]))

    assert errors_of(parsed) == [(3, "notes")]


def test_plant_without_device_repeated_with_the_same_notes_is_fine() -> None:
    parsed = parse(csv_file([plant_row(notes="Same"), plant_row(notes="Same")]))

    assert parsed.errors == []
    assert [(plant.key, plant.notes) for plant in parsed.plants] == [("charging", "Same")]


def test_latin_1_file_is_an_error_with_line() -> None:
    rows = [row(), row(device_id="mill-plc", plant_id="mill", plant_name="Frässtation")]

    parsed = parse(csv_file(rows, encoding="latin-1"))

    assert errors_of(parsed) == [(3, None)]
    assert "UTF-8" in parsed.errors[0].message
    assert parsed.devices[0].key == "press-plc"


def test_field_over_the_csv_limit_is_an_error_of_its_row() -> None:
    limit = csv.field_size_limit()
    rows = [row(), row(device_id="long", notes="x" * (limit + 1))]

    parsed = parse(csv_file(rows))

    assert errors_of(parsed) == [(3, None)]
    assert str(limit) in parsed.errors[0].message


def test_field_at_the_csv_limit_is_accepted() -> None:
    notes = "x" * csv.field_size_limit()

    parsed = parse(csv_file([row(notes=notes)]))

    assert parsed.errors == []
    assert parsed.devices[0].values["notes"] == notes


def test_line_numbers_count_line_breaks_inside_quotes() -> None:
    rows = [row(notes="one\ntwo\nthree"), row(device_id="bad", ip_address="nope")]

    parsed = parse(csv_file(rows))

    # Header line 1, the first row lines 2 to 4, the second row line 5.
    assert errors_of(parsed) == [(5, "ip_address")]


def test_broken_quoting_is_an_error_and_stops_reading() -> None:
    text = csv_text([row()]) + 'North,"Line 1"x,press,Press\r\n' + csv_text([row()])

    parsed = parse(raw_file(text))

    assert errors_of(parsed) == [(3, None)]
    assert "not checked" in parsed.errors[0].message


@pytest.mark.parametrize(
    ("header", "count"),
    [
        (COLUMNS, 12),
        (COLUMNS, 14),
        (COLUMNS_WITH_DEVICE_CLASS, 13),
        (COLUMNS_WITH_DEVICE_CLASS, 15),
    ],
)
def test_wrong_number_of_fields_is_an_error_of_the_row(header: tuple[str, ...], count: int) -> None:
    text = ",".join(header) + "\r\n" + ",".join(["x"] * count) + "\r\n"

    parsed = parse(raw_file(text))

    assert errors_of(parsed) == [(2, None)]
    assert f"has {count} fields instead of {len(header)}" in parsed.errors[0].message


@pytest.mark.parametrize("column", ["site", "area", "plant_id", "plant_name"])
def test_required_column_left_empty_is_an_error(column: str) -> None:
    parsed = parse(csv_file([row(**{column: ""})]))

    assert errors_of(parsed) == [(2, column)]


def test_device_id_without_device_name_is_an_error() -> None:
    parsed = parse(csv_file([row(device_name="")]))

    assert errors_of(parsed) == [(2, "device_name")]


@pytest.mark.parametrize("column", csv_import.DEVICE_ONLY_COLUMNS)
def test_device_columns_without_device_id_are_errors(column: str) -> None:
    value = {"ip_address": "192.0.2.1", "device_class": "plc"}.get(column, "something")

    parsed = parse(csv_file([plant_row(**{column: value})], header=COLUMNS_WITH_DEVICE_CLASS))

    assert errors_of(parsed) == [(2, column)]


def test_device_class_is_a_device_only_column() -> None:
    assert DEVICE_CLASS_COLUMN in csv_import.DEVICE_ONLY_COLUMNS


@pytest.mark.parametrize("key", ["Press", "press_1", "press 1", "presse-ä", "a" * 65])
@pytest.mark.parametrize("column", ["plant_id", "device_id"])
def test_invalid_keys_are_errors(column: str, key: str) -> None:
    parsed = parse(csv_file([row(**{column: key})]))

    assert errors_of(parsed) == [(2, column)]


def test_too_long_name_is_an_error() -> None:
    parsed = parse(csv_file([row(plant_name="n" * 201)]))

    assert errors_of(parsed) == [(2, "plant_name")]


def test_nul_character_is_an_error() -> None:
    parsed = parse(csv_file([row(notes="before\x00after")]))

    assert errors_of(parsed) == [(2, "notes")]


def test_errors_of_several_rows_are_all_reported() -> None:
    rows = [
        row(device_id="a"),
        row(device_id="b", ip_address="bad"),
        row(device_id="c", plant_name="Other"),
        row(device_id="d"),
    ]

    parsed = parse(csv_file(rows))

    assert errors_of(parsed) == [(3, "ip_address"), (4, "plant_name")]


def test_too_many_rows_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(csv_import, "MAX_ROWS", 2)
    rows = [row(device_id=f"device-{number}") for number in range(3)]

    parsed = parse(csv_file(rows))

    assert errors_of(parsed) == [(4, None)]
    assert "more than 2 rows" in parsed.errors[0].message


def test_too_long_line_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(csv_import, "MAX_LINE_BYTES", 300)
    rows = [row(), row(device_id="long", notes="x" * 300)]

    parsed = parse(csv_file(rows))

    assert errors_of(parsed) == [(3, None)]
    assert "300 bytes" in parsed.errors[0].message


def test_file_with_errors_writes_nothing(importer: User) -> None:
    rows = [row(), row(device_id="second", ip_address="bad")]

    report = apply(parse(csv_file(rows)), importer, dry_run=False)

    assert report.saved is False
    assert [(error.line, error.column) for error in report.errors] == [(3, "ip_address")]
    assert counts(report)["devices"] == (0, 0, 0)
    assert structure_snapshot() == []
    assert structure_entries() == 0


# --- matching rules ----------------------------------------------------------


def stored_press(notes: str = "") -> Plant:
    site = Site.objects.create(name="North")
    area = Area.objects.create(site=site, name="Line 1")
    return Plant.objects.create(area=area, key="press", name="Press", notes=notes)


def test_device_moves_to_the_plant_of_the_file(importer: User) -> None:
    press = stored_press()
    other = Plant.objects.create(area=press.area, key="welder", name="Welder")
    Device.objects.create(plant=other, key="press-plc", name="Press PLC")

    report = apply(parse(csv_file([row()])), importer, dry_run=False)

    assert counts(report)["devices"] == (0, 1, 0)
    assert Device.objects.get(key="press-plc").plant == press


def test_plant_moves_to_the_area_of_the_file(importer: User) -> None:
    press = stored_press()

    report = apply(parse(csv_file([row(area="Line 2")])), importer, dry_run=False)

    assert counts(report)["areas"] == (1, 0, 0)
    assert counts(report)["plants"] == (0, 1, 0)
    press.refresh_from_db()
    assert press.area.name == "Line 2"


def test_nothing_is_deleted(importer: User) -> None:
    press = stored_press()
    Device.objects.create(plant=press, key="not-in-file", name="Kept")
    Plant.objects.create(area=press.area, key="also-kept", name="Kept")

    apply(parse(csv_file([row()])), importer, dry_run=False)

    assert Device.objects.filter(key="not-in-file").exists()
    assert Plant.objects.filter(key="also-kept").exists()


def test_notes_of_a_plant_change_only_with_a_row_without_device(importer: User) -> None:
    stored_press(notes="Stored note")

    apply(parse(csv_file([row()])), importer, dry_run=False)
    kept = Plant.objects.get(key="press").notes
    apply(
        parse(csv_file([row(), plant_row(plant_id="press", plant_name="Press", notes="New")])),
        importer,
        dry_run=False,
    )

    assert kept == "Stored note"
    assert Plant.objects.get(key="press").notes == "New"


def test_device_notes_go_to_the_device(importer: User) -> None:
    apply(parse(csv_file([row(notes="Device note")])), importer, dry_run=False)

    assert Device.objects.get(key="press-plc").notes == "Device note"
    assert Plant.objects.get(key="press").notes == ""


def test_empty_ip_address_clears_a_stored_one(importer: User) -> None:
    Device.objects.create(
        plant=stored_press(), key="press-plc", name="Press PLC", ip_address="192.0.2.99"
    )

    apply(parse(csv_file([row(ip_address="")])), importer, dry_run=False)

    assert Device.objects.get(key="press-plc").ip_address is None


def test_ipv6_address_is_unchanged_on_a_second_import(importer: User) -> None:
    rows = [row(ip_address="2001:DB8::0:1")]
    apply(parse(csv_file(rows)), importer, dry_run=False)

    report = apply(parse(csv_file(rows)), importer, dry_run=False)

    assert counts(report)["devices"] == (0, 0, 1)


def test_existing_site_and_area_are_reused(importer: User) -> None:
    stored_press()

    report = apply(
        parse(csv_file([row(plant_id="welder", plant_name="Welder", device_id="welder-plc")])),
        importer,
        dry_run=False,
    )

    assert counts(report)["sites"] == (0, 0, 1)
    assert counts(report)["areas"] == (0, 0, 1)
    assert Site.objects.count() == 1


def test_area_name_is_matched_within_its_site(importer: User) -> None:
    stored_press()

    report = apply(
        parse(csv_file([row(site="South", plant_id="paint", plant_name="Paint", device_id="p1")])),
        importer,
        dry_run=False,
    )

    assert counts(report)["areas"] == (1, 0, 0)
    assert Area.objects.filter(name="Line 1").count() == 2


def test_unique_key_saved_at_the_same_time_is_an_error(
    importer: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Another change saved the plant "press" after the import looked it up.
    stored_press()
    monkeypatch.setattr(Plant.objects, "in_bulk", lambda *args, **kwargs: {})
    before = structure_snapshot()

    report = apply(parse(csv_file([plant_row(notes="x"), row()])), importer, dry_run=False)

    assert report.saved is False
    assert [(error.line, error.column) for error in report.errors] == [(3, "plant_id")]
    assert "A plant with this key exists already." in report.errors[0].message
    assert counts(report)["sites"] == (0, 0, 0)
    assert structure_snapshot() == before


# --- optional column device_class (E-53) -------------------------------------


def class_file(*rows: dict[str, str]) -> io.BytesIO:
    """A file with the optional 14th column."""
    return csv_file(rows, header=COLUMNS_WITH_DEVICE_CLASS)


@pytest.mark.parametrize("device_class", DeviceClass.values)
def test_every_device_class_is_accepted(importer: User, device_class: str) -> None:
    report = apply(parse(class_file(row(device_class=device_class))), importer, dry_run=False)

    assert report.errors == []
    assert Device.objects.get(key="press-plc").device_class == device_class


def test_file_with_13_columns_creates_devices_of_class_other(importer: User) -> None:
    report = apply(parse(csv_file([row()])), importer, dry_run=False)

    assert report.errors == []
    assert Device.objects.get(key="press-plc").device_class == DeviceClass.OTHER


def test_empty_device_class_creates_a_device_of_class_other(importer: User) -> None:
    report = apply(parse(class_file(row(device_class=""))), importer, dry_run=False)

    assert report.errors == []
    assert Device.objects.get(key="press-plc").device_class == DeviceClass.OTHER


@pytest.mark.parametrize("with_class_column", [False, True])
def test_device_class_left_out_keeps_the_stored_one(
    importer: User, with_class_column: bool
) -> None:
    Device.objects.create(
        plant=stored_press(), key="press-plc", name="Press PLC", device_class=DeviceClass.PLC
    )
    rows = [row(manufacturer="Changed")]

    parsed = parse(class_file(*rows) if with_class_column else csv_file(rows))
    report = apply(parsed, importer, dry_run=False)

    assert report.errors == []
    assert counts(report)["devices"] == (0, 1, 0)
    device = Device.objects.get(key="press-plc")
    assert device.manufacturer == "Changed"
    assert device.device_class == DeviceClass.PLC


def test_same_device_class_again_is_unchanged(importer: User) -> None:
    apply(parse(class_file(row(device_class="plc"))), importer, dry_run=False)

    report = apply(parse(class_file(row(device_class="plc"))), importer, dry_run=False)

    assert counts(report)["devices"] == (0, 0, 1)


def test_changed_device_class_updates_the_device_with_a_log_entry(importer: User) -> None:
    apply(parse(class_file(row(device_class="plc"))), importer, dry_run=False)

    report = apply(parse(class_file(row(device_class="controller"))), importer, dry_run=False)

    assert counts(report)["devices"] == (0, 1, 0)
    device = Device.objects.get(key="press-plc")
    assert device.device_class == DeviceClass.CONTROLLER
    entry = LogEntry.objects.get(
        content_type=ContentType.objects.get_for_model(Device),
        object_id=device.pk,
        action=LogEntry.Action.UPDATE,
    )
    assert entry.actor == importer
    assert entry.changes == {"device_class": ["plc", "controller"]}


def test_dry_run_of_a_device_class_change_changes_nothing(importer: User) -> None:
    apply(parse(class_file(row(device_class="plc"))), importer, dry_run=False)
    before = structure_snapshot()

    report = apply(parse(class_file(row(device_class="robot"))), importer, dry_run=True)

    assert counts(report)["devices"] == (0, 1, 0)
    assert structure_snapshot() == before


def test_spaces_around_the_device_class_are_removed() -> None:
    parsed = parse(class_file(row(device_class="  router ")))

    assert parsed.errors == []
    assert parsed.devices[0].values["device_class"] == "router"


@pytest.mark.parametrize("value", ["PLC", "Plc", "sps", "switch", "plc,router", "x" * 300])
def test_unknown_device_class_is_an_error_at_its_line_and_column(
    importer: User, value: str
) -> None:
    rows = [plant_row(), row(), row(device_id="press-hmi", device_class=value)]

    report = apply(parse(class_file(*rows)), importer, dry_run=False)

    assert [(error.line, error.column) for error in report.errors] == [(4, "device_class")]
    message = report.errors[0].message
    assert "is not a device class" in message
    assert "plc, controller, computer, router, firewall, robot, other" in message
    assert "x" * 41 not in message
    assert report.saved is False
    assert structure_snapshot() == []


def test_unknown_device_classes_in_several_rows_are_all_reported() -> None:
    rows = [
        row(device_id="a", device_class="plc"),
        row(device_id="b", device_class="nope"),
        row(device_id="c", device_class="robot"),
        row(device_id="d", device_class="other-thing"),
    ]

    parsed = parse(class_file(*rows))

    assert errors_of(parsed) == [(3, "device_class"), (5, "device_class")]


def test_testfactory_classes_survive_a_13_column_reimport(importer: User) -> None:
    import_testfactory(importer)

    report = apply(parse(csv_file(factory_rows())), importer, dry_run=False)

    assert counts(report)["devices"] == (0, 0, 13)
    assert dict(Device.objects.values_list("key", "device_class")) == TESTFACTORY_DEVICE_CLASSES
