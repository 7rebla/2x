"""Cross references between the manifest and the device list (work order 109).

Every ID in ``assigned_to`` of ``testfactory/manifest.yaml`` must exist in
``testfactory/layout/devices.csv`` as ``plant_id`` or ``device_id``, and every
device of the device list must have at least one manifest entry, unless it is
named in ``DEVICES_WITHOUT_ENTRY`` with a reason. The tests need no network.
"""

from __future__ import annotations

import csv
import unittest
from pathlib import Path

from testfactory import manifest_tools

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "testfactory" / "manifest.yaml"
DEVICES_PATH = REPOSITORY_ROOT / "testfactory" / "layout" / "devices.csv"

# Devices that may lack a manifest entry, each with the reason. Empty on
# 2026-11-21: every device has at least one entry.
DEVICES_WITHOUT_ENTRY: dict[str, str] = {}


def _device_rows() -> list[dict[str, str]]:
    with DEVICES_PATH.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _plant_ids() -> set[str]:
    return {row["plant_id"] for row in _device_rows() if row["plant_id"]}


def _device_ids() -> set[str]:
    return {row["device_id"] for row in _device_rows() if row["device_id"]}


def _assignments() -> dict[str, list[str]]:
    """Map every assigned ID to the manifest entries that name it."""
    manifest = manifest_tools.load_manifest(MANIFEST_PATH)
    result: dict[str, list[str]] = {}
    for entry in manifest.entries:
        for assigned in entry.assigned_to:
            result.setdefault(assigned, []).append(entry.id)
    return result


class CrossReferenceTest(unittest.TestCase):
    def test_device_list_is_not_empty(self) -> None:
        self.assertTrue(_plant_ids())
        self.assertTrue(_device_ids())

    def test_every_assigned_id_exists_in_the_device_list(self) -> None:
        known = _plant_ids() | _device_ids()
        for assigned, entry_ids in sorted(_assignments().items()):
            with self.subTest(assigned=assigned):
                self.assertIn(
                    assigned,
                    known,
                    f"assigned_to of {entry_ids} names an ID that is neither "
                    "plant_id nor device_id in layout/devices.csv",
                )

    def test_every_device_has_a_manifest_entry(self) -> None:
        assignments = _assignments()
        for device_id in sorted(_device_ids()):
            if device_id in DEVICES_WITHOUT_ENTRY:
                continue
            with self.subTest(device=device_id):
                self.assertIn(
                    device_id,
                    assignments,
                    "device has no manifest entry and is not listed in DEVICES_WITHOUT_ENTRY",
                )

    def test_exceptions_are_real_devices_with_a_reason(self) -> None:
        devices = _device_ids()
        assignments = _assignments()
        for device_id, reason in DEVICES_WITHOUT_ENTRY.items():
            with self.subTest(device=device_id):
                self.assertIn(device_id, devices)
                self.assertNotIn(
                    device_id,
                    assignments,
                    "the device has an entry; remove it from the exceptions",
                )
                self.assertTrue(reason.strip())

    def test_ids_are_not_both_plant_and_device(self) -> None:
        self.assertEqual(_plant_ids() & _device_ids(), set())


if __name__ == "__main__":
    unittest.main()
