"""Tests for the test factory layout (device list). They need no network."""

from __future__ import annotations

import csv
import ipaddress
import unittest
from collections import Counter
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LAYOUT = REPOSITORY_ROOT / "testfactory" / "layout"
DEVICES_CSV = LAYOUT / "devices.csv"

HEADER = [
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
]

SITE = "Testfabrik"
AREAS = {"Fertigungslinie", "Roboterzelle", "Netzübergang"}
PRODUCTION_LINE = "Fertigungslinie"
PRODUCTION_LINE_NETWORK = ipaddress.ip_network("192.168.0.0/24")

PLANT_IDS = {
    "aps-dps",
    "aps-hbw",
    "aps-drill",
    "aps-mill",
    "aps-aiqs",
    "aps-agv",
    "aps-charging",
    "aps-core",
    "ur5e-cell",
    "it-ot-firewall",
}

DEVICE_IDS = {
    "dps-plc",
    "dps-txt",
    "hbw-plc",
    "drill-plc",
    "mill-plc",
    "aiqs-plc",
    "aiqs-txt",
    "agv-txt",
    "cgw-txt",
    "ccu-rpi",
    "aps-router",
    "ur5e",
    "opnsense-fw",
}

# Devices whose address is not a fixed value from the vendor documents.
DEVICES_WITHOUT_ADDRESS = {
    "dps-txt",
    "aiqs-txt",
    "agv-txt",
    "cgw-txt",
    "ur5e",
    "opnsense-fw",
}


def read_rows() -> tuple[list[str], list[dict[str, str]]]:
    """Return the header and the data rows of the device list."""
    with DEVICES_CSV.open(encoding="utf-8", newline="") as handle:
        raw = list(csv.reader(handle))
    header = raw[0]
    rows = [dict(zip(header, line, strict=True)) for line in raw[1:]]
    return header, rows


class DeviceListFormatTest(unittest.TestCase):
    def test_file_is_utf8_without_byte_order_mark(self) -> None:
        data = DEVICES_CSV.read_bytes()
        self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
        data.decode("utf-8")

    def test_header_is_exactly_the_agreed_one(self) -> None:
        header, _ = read_rows()
        self.assertEqual(header, HEADER)

    def test_every_row_has_one_value_per_column(self) -> None:
        with DEVICES_CSV.open(encoding="utf-8", newline="") as handle:
            for number, line in enumerate(csv.reader(handle), start=1):
                self.assertEqual(len(line), len(HEADER), f"line {number}")

    def test_no_value_has_surrounding_whitespace(self) -> None:
        _, rows = read_rows()
        for row in rows:
            for column, value in row.items():
                self.assertEqual(value, value.strip(), f"{row['plant_id']}: {column}")


class DeviceListContentTest(unittest.TestCase):
    def setUp(self) -> None:
        _, self.rows = read_rows()
        self.devices = [row for row in self.rows if row["device_id"]]

    def test_site_and_areas(self) -> None:
        self.assertEqual({row["site"] for row in self.rows}, {SITE})
        self.assertEqual({row["area"] for row in self.rows}, AREAS)

    def test_device_ids_are_unique(self) -> None:
        counts = Counter(row["device_id"] for row in self.devices)
        duplicates = sorted(key for key, count in counts.items() if count > 1)
        self.assertEqual(duplicates, [])

    def test_expected_identifiers_are_present(self) -> None:
        self.assertEqual({row["plant_id"] for row in self.rows}, PLANT_IDS)
        self.assertEqual({row["device_id"] for row in self.devices}, DEVICE_IDS)

    def test_plant_has_one_name_and_one_area(self) -> None:
        for plant_id in PLANT_IDS:
            rows = [row for row in self.rows if row["plant_id"] == plant_id]
            self.assertEqual(len({row["plant_name"] for row in rows}), 1, plant_id)
            self.assertEqual(len({row["area"] for row in rows}), 1, plant_id)

    def test_every_plant_has_a_device_or_a_note(self) -> None:
        for plant_id in PLANT_IDS:
            rows = [row for row in self.rows if row["plant_id"] == plant_id]
            has_device = any(row["device_id"] for row in rows)
            has_note = any(row["notes"] for row in rows if not row["device_id"])
            self.assertTrue(has_device or has_note, plant_id)

    def test_row_without_device_has_a_note_and_no_device_fields(self) -> None:
        device_columns = [
            "device_name",
            "manufacturer",
            "model",
            "software_version",
            "ip_address",
            "protocols",
        ]
        for row in self.rows:
            if row["device_id"]:
                continue
            self.assertTrue(row["notes"], row["plant_id"])
            for column in device_columns:
                self.assertEqual(row[column], "", f"{row['plant_id']}: {column}")

    def test_every_device_has_name_manufacturer_and_model(self) -> None:
        for row in self.devices:
            for column in ("device_name", "manufacturer", "model"):
                self.assertTrue(row[column], f"{row['device_id']}: {column}")

    def test_addresses_are_valid_and_have_a_source(self) -> None:
        for row in self.rows:
            if not row["ip_address"]:
                continue
            ipaddress.ip_address(row["ip_address"])
            self.assertTrue(row["address_source"], row["device_id"])

    def test_addresses_are_unique(self) -> None:
        counts = Counter(row["ip_address"] for row in self.rows if row["ip_address"])
        duplicates = sorted(key for key, count in counts.items() if count > 1)
        self.assertEqual(duplicates, [])

    def test_production_line_addresses_are_in_its_network(self) -> None:
        for row in self.rows:
            if row["area"] != PRODUCTION_LINE or not row["ip_address"]:
                continue
            address = ipaddress.ip_address(row["ip_address"])
            self.assertIn(address, PRODUCTION_LINE_NETWORK, row["device_id"])

    def test_devices_without_fixed_address_say_why(self) -> None:
        for row in self.devices:
            if row["device_id"] not in DEVICES_WITHOUT_ADDRESS:
                self.assertTrue(row["ip_address"], row["device_id"])
                continue
            self.assertEqual(row["ip_address"], "", row["device_id"])
            self.assertTrue(row["address_source"], row["device_id"])

    def test_central_control_and_router_addresses(self) -> None:
        by_id = {row["device_id"]: row for row in self.devices}
        self.assertEqual(by_id["ccu-rpi"]["ip_address"], "192.168.0.100")
        self.assertEqual(by_id["aps-router"]["ip_address"], "192.168.0.1")
        text = DEVICES_CSV.read_text(encoding="utf-8")
        lines = [line for line in text.splitlines() if "192.168.0.100" in line]
        self.assertEqual(len(lines), 1)

    def test_add_on_oven_is_not_part_of_the_factory(self) -> None:
        for row in self.rows:
            self.assertNotIn("oven", row["plant_id"])
            self.assertNotIn("oven", row["device_id"])


class LayoutDocumentsTest(unittest.TestCase):
    def test_network_plan_and_description_exist(self) -> None:
        for name in ("network-plan.md", "description.md"):
            path = LAYOUT / name
            self.assertTrue(path.is_file(), name)
            self.assertTrue(path.read_text(encoding="utf-8").strip(), name)

    def test_network_plan_has_the_contradictions_section(self) -> None:
        text = (LAYOUT / "network-plan.md").read_text(encoding="utf-8")
        self.assertIn("## Widersprüche in den Quellen", text)


if __name__ == "__main__":
    unittest.main()
