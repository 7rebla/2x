"""Device lists for the tests of the CSV import.

Rows are written with Python's ``csv`` module (comma, RFC 4180 quoting,
CRLF), so the tests read what a spreadsheet would save. Addresses come from
the documentation ranges 192.0.2.0/24 and 2001:db8::/32.
"""

import csv
import io
from collections.abc import Iterable, Mapping
from pathlib import Path

from twox.assets.csv_import import COLUMNS

#: The device list of the test factory, mounted read-only into backend-dev
#: (deploy/compose/compose.yaml). It is the acceptance case of M1.
TESTFACTORY_DEVICES_CSV = Path("/testfactory/layout/devices.csv")

HEADER = ",".join(COLUMNS)


def row(**values: str) -> dict[str, str]:
    """A row of the press PLC; keyword arguments replace columns."""
    unknown = set(values) - set(COLUMNS)
    if unknown:
        raise ValueError(f"unknown columns: {sorted(unknown)}")
    base = dict.fromkeys(COLUMNS, "")
    base.update(
        site="North",
        area="Line 1",
        plant_id="press",
        plant_name="Press",
        device_id="press-plc",
        device_name="Press PLC",
        manufacturer="Vendor",
        model="PLC 1",
        software_version="1.0",
        ip_address="192.0.2.10",
        address_source="Manual page 3",
        protocols="OPC UA",
        notes="",
    )
    base.update(values)
    return base


def plant_row(**values: str) -> dict[str, str]:
    """A row of a plant without devices; keyword arguments replace columns."""
    empty_device = dict.fromkeys(COLUMNS[COLUMNS.index("device_id") :], "")
    return row(**{**empty_device, "plant_id": "charging", "plant_name": "Charging", **values})


def csv_text(rows: Iterable[Mapping[str, str]], header: Iterable[str] = COLUMNS) -> str:
    """The rows as CSV text with the header ``header``."""
    out = io.StringIO()
    writer = csv.writer(out)
    columns = list(header)
    writer.writerow(columns)
    for values in rows:
        writer.writerow([values.get(column, "") for column in COLUMNS])
    return out.getvalue()


def csv_file(
    rows: Iterable[Mapping[str, str]],
    header: Iterable[str] = COLUMNS,
    encoding: str = "utf-8",
) -> io.BytesIO:
    """The rows as an encoded CSV file."""
    return io.BytesIO(csv_text(rows, header).encode(encoding))


def raw_file(text: str, encoding: str = "utf-8") -> io.BytesIO:
    """A file with exactly ``text``."""
    return io.BytesIO(text.encode(encoding))


def factory_rows() -> list[dict[str, str]]:
    """The rows of the test factory's device list, read with the ``csv`` module."""
    with TESTFACTORY_DEVICES_CSV.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))
