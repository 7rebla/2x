"""Tests for the evidence table of the three conditions (work order 113).

``testfactory/layout/evidence.md`` holds one row per ID of
``testfactory/layout/devices.csv`` and condition (1, 2, 3). The tests check
that the table can be read, that every plant and every device has exactly
three rows, that the status values are allowed, that every fulfilled row
names evidence that exists, that every open row explains itself, that plants
follow their devices and that the summary counts match the table. Rows of
``devices.csv`` without ``device_id`` (plants without a device, for example
``aps-charging``) are skipped by every per-device check. No network needed.
"""

from __future__ import annotations

import csv
import re
import unittest
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from testfactory import manifest_tools

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LAYOUT = REPOSITORY_ROOT / "testfactory" / "layout"
EVIDENCE_PATH = LAYOUT / "evidence.md"
DEVICES_PATH = LAYOUT / "devices.csv"
MANIFEST_PATH = REPOSITORY_ROOT / "testfactory" / "manifest.yaml"

TABLE_HEADER = ["id", "bedingung", "status", "beleg", "anmerkung"]
SUMMARY_HEADER = ["Bereich", "Zeilen", "erfüllt", "offen", "folgt in T2"]

FULFILLED = "erfüllt"
OPEN = "offen"
LATER = "folgt in T2"
STATUSES = (FULFILLED, OPEN, LATER)
CONDITIONS = ("1", "2", "3")

# Only the robot cell and the firewall may defer to T2 (E-23, question 2 of
# work order 113, answer A).
IDS_ALLOWED_IN_T2 = {"ur5e", "ur5e-cell", "opnsense-fw", "it-ot-firewall"}

# A code span that looks like an ID (lower case words, joined by hyphens).
# Paths and file names contain "/" or "." and do not match.
CODE_SPAN = re.compile(r"`([^`]+)`")
ID_LIKE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class EvidenceRow:
    line: int
    id: str
    condition: str
    status: str
    evidence: str
    remark: str


@dataclass(frozen=True)
class Layout:
    plant_of_device: dict[str, str]
    devices_of_plant: dict[str, list[str]]
    area_of_id: dict[str, str]


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _table_after(lines: list[str], header: list[str]) -> list[tuple[int, list[str]]]:
    """Return (line number, cells) of the table that starts with ``header``."""
    for index, line in enumerate(lines):
        if line.startswith("|") and _cells(line) == header:
            rows: list[tuple[int, list[str]]] = []
            for number, row in enumerate(lines[index + 2 :], start=index + 3):
                if not row.startswith("|"):
                    break
                rows.append((number, _cells(row)))
            return rows
    raise AssertionError(f"table with header {header} not found in {EVIDENCE_PATH.name}")


def _lines() -> list[str]:
    return EVIDENCE_PATH.read_text(encoding="utf-8").splitlines()


def read_evidence() -> list[EvidenceRow]:
    rows = []
    for number, cells in _table_after(_lines(), TABLE_HEADER):
        if len(cells) != len(TABLE_HEADER):
            raise AssertionError(f"line {number}: expected {len(TABLE_HEADER)} cells, got {len(cells)}")
        rows.append(EvidenceRow(number, *cells))
    return rows


def read_layout() -> Layout:
    with DEVICES_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    plant_of_device: dict[str, str] = {}
    devices_of_plant: dict[str, list[str]] = {}
    area_of_id: dict[str, str] = {}
    for row in rows:
        plant_id = row["plant_id"]
        devices_of_plant.setdefault(plant_id, [])
        area_of_id[plant_id] = row["area"]
        device_id = row["device_id"]
        if not device_id:
            # Plant without a device (Nachtrag der Leitstelle): no device check.
            continue
        plant_of_device[device_id] = plant_id
        devices_of_plant[plant_id].append(device_id)
        area_of_id[device_id] = row["area"]
    return Layout(plant_of_device, devices_of_plant, area_of_id)


def manifest_assignments() -> dict[str, set[str]]:
    """Map every manifest ID to the IDs in its ``assigned_to``."""
    manifest = manifest_tools.load_manifest(MANIFEST_PATH)
    return {entry.id: set(entry.assigned_to) for entry in manifest.entries}


def id_spans(text: str) -> list[str]:
    return [span for span in CODE_SPAN.findall(text) if ID_LIKE.match(span)]


def plant_status(device_statuses: list[str]) -> str:
    if all(status == FULFILLED for status in device_statuses):
        return FULFILLED
    if any(status == OPEN for status in device_statuses):
        return OPEN
    return LATER


class EvidenceTableTest(unittest.TestCase):
    rows: list[EvidenceRow]
    layout: Layout
    manifest: dict[str, set[str]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = read_evidence()
        cls.layout = read_layout()
        cls.manifest = manifest_assignments()

    def _status(self, item_id: str, condition: str) -> str:
        matches = [row.status for row in self.rows if row.id == item_id and row.condition == condition]
        self.assertEqual(len(matches), 1, f"{item_id} condition {condition}")
        return matches[0]

    def test_table_is_readable_and_not_empty(self) -> None:
        self.assertTrue(self.rows)

    def test_every_plant_and_device_has_exactly_three_rows(self) -> None:
        expected = set(self.layout.area_of_id)
        counts = Counter((row.id, row.condition) for row in self.rows)
        for item_id in sorted(expected):
            for condition in CONDITIONS:
                with self.subTest(id=item_id, condition=condition):
                    self.assertEqual(counts[(item_id, condition)], 1)
        self.assertEqual({row.id for row in self.rows} - expected, set(), "unknown IDs in the table")
        self.assertEqual(len(self.rows), 3 * len(expected))

    def test_condition_and_status_values_are_allowed(self) -> None:
        for row in self.rows:
            with self.subTest(line=row.line):
                self.assertIn(row.condition, CONDITIONS)
                self.assertIn(row.status, STATUSES)

    def test_fulfilled_rows_name_existing_evidence(self) -> None:
        devices = set(self.layout.plant_of_device)
        for row in self.rows:
            if row.status != FULFILLED:
                continue
            with self.subTest(line=row.line, id=row.id):
                spans = set(id_spans(row.evidence))
                manifest_ids = spans & set(self.manifest)
                device_ids = spans & devices
                if row.id in devices or not self.layout.devices_of_plant.get(row.id):
                    self.assertTrue(manifest_ids, "fulfilled row without an existing manifest_id")
                else:
                    self.assertTrue(
                        manifest_ids or device_ids,
                        "fulfilled plant row without manifest_id or device_id",
                    )

    def test_fulfilled_rows_of_devices_cite_an_entry_assigned_to_them(self) -> None:
        for row in self.rows:
            if row.status != FULFILLED:
                continue
            owners = {row.id, self.layout.plant_of_device.get(row.id, row.id)}
            if row.id in self.layout.devices_of_plant and self.layout.devices_of_plant[row.id]:
                continue  # plants with devices are checked through their devices
            with self.subTest(line=row.line, id=row.id):
                cited = set(id_spans(row.evidence)) & set(self.manifest)
                self.assertTrue(
                    any(self.manifest[entry] & owners for entry in cited),
                    "no cited manifest entry is assigned to the device or its plant",
                )

    def test_every_id_in_the_evidence_column_exists(self) -> None:
        known = set(self.manifest) | set(self.layout.area_of_id)
        for row in self.rows:
            for span in id_spans(row.evidence):
                with self.subTest(line=row.line, span=span):
                    self.assertIn(span, known)

    def test_open_and_later_rows_have_a_remark(self) -> None:
        for row in self.rows:
            if row.status in (OPEN, LATER):
                with self.subTest(line=row.line, id=row.id):
                    self.assertTrue(row.remark)

    def test_only_robot_cell_and_firewall_defer_to_t2(self) -> None:
        for row in self.rows:
            if row.status == LATER:
                with self.subTest(line=row.line, id=row.id):
                    self.assertIn(row.id, IDS_ALLOWED_IN_T2)

    def test_plants_follow_their_devices(self) -> None:
        for plant_id, devices in sorted(self.layout.devices_of_plant.items()):
            if not devices:
                continue
            for condition in CONDITIONS:
                with self.subTest(plant=plant_id, condition=condition):
                    expected = plant_status([self._status(device, condition) for device in devices])
                    self.assertEqual(self._status(plant_id, condition), expected)
                    row = next(r for r in self.rows if r.id == plant_id and r.condition == condition)
                    self.assertEqual(set(devices) - set(id_spans(row.evidence)), set(), "plant row must name its devices")

    def test_summary_counts_match_the_table(self) -> None:
        summary = {cells[0]: cells[1:] for _, cells in _table_after(_lines(), SUMMARY_HEADER)}
        per_area: dict[str, Counter[str]] = {}
        for row in self.rows:
            area = self.layout.area_of_id[row.id]
            per_area.setdefault(area, Counter())[row.status] += 1
        per_area["Gesamt"] = Counter(row.status for row in self.rows)
        self.assertEqual(set(summary), set(per_area))
        for area, counts in per_area.items():
            with self.subTest(area=area):
                expected = [str(sum(counts.values()))] + [str(counts[status]) for status in STATUSES]
                self.assertEqual(summary[area], expected)


if __name__ == "__main__":
    unittest.main()
