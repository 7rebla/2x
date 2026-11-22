"""The probe list of M2 refers only to what the test factory documents (056).

Every ``manifest_id`` and ``sha256`` of ``twox/search/probes/m2.json`` must be
an entry of ``testfactory/manifest.yaml`` (JSON notation, read with ``json``),
and every page must be named for that entry in ``testfactory/questions.yaml``
(probe basis ``question``) or in ``testfactory/layout/devices.csv`` (basis
``device``). Compose mounts the three files read-only into ``backend-dev``.
"""

import csv
import json
import re
from pathlib import Path
from typing import Any

import pytest

import twox.search
from twox.search.evaluation import load_probes

PROBES = Path(twox.search.__file__).parent / "probes" / "m2.json"
MANIFEST = Path("/testfactory/manifest.yaml")
QUESTIONS = Path("/testfactory/questions.yaml")
DEVICES_CSV = Path("/testfactory/layout/devices.csv")

#: Test questions the probe list must cover in own words.
REQUIRED_QUESTIONS = {1, 3, 7, 9, 10}
#: In devices.csv, "Handbuch" is the manual of the production line.
DEVICES_MANUAL = "aps-documentation-de"
#: A page index of a PDF file in a locator ("PDF-S. 31").
PDF_PAGE = re.compile(r"PDF-S\. (\d+)")
#: A query that is an IPv4 address only.
IPV4 = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")


def is_address(query: str) -> bool:
    return IPV4.fullmatch(query) is not None


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.fixture(scope="module")
def probe_list() -> dict[str, Any]:
    return read_json(PROBES)


@pytest.fixture(scope="module")
def manifest() -> dict[str, dict[str, Any]]:
    return {entry["id"]: entry for entry in read_json(MANIFEST)["entries"]}


@pytest.fixture(scope="module")
def questions() -> dict[object, dict[str, Any]]:
    return {question["id"]: question for question in read_json(QUESTIONS)["questions"]}


@pytest.fixture(scope="module")
def devices() -> dict[str, dict[str, str]]:
    with DEVICES_CSV.open(encoding="utf-8", newline="") as file:
        return {row["device_id"]: row for row in csv.DictReader(file) if row["device_id"]}


def pages_of_question(question: dict[str, Any]) -> set[tuple[str, int]]:
    """``(manifest_id, page)`` of every source of ``question`` located by PDF page."""
    return {
        (source["manifest_id"], int(page))
        for source in question["sources"]
        for page in PDF_PAGE.findall(source["locator"])
    }


def pages_of_device(row: dict[str, str]) -> set[tuple[str, int]]:
    """``(manifest_id, page)`` of the manual pages in the address source of a device."""
    return {(DEVICES_MANUAL, int(page)) for page in PDF_PAGE.findall(row["address_source"])}


def test_probe_list_is_valid() -> None:
    probes = load_probes(PROBES.read_text(encoding="utf-8"))

    assert len(probes) >= 7


def test_every_file_is_in_the_manifest(
    probe_list: dict[str, Any], manifest: dict[str, dict[str, Any]]
) -> None:
    for probe in probe_list["probes"]:
        for place in probe["expected"]:
            entry = manifest.get(place["manifest_id"])
            assert entry is not None, place["manifest_id"]
            assert entry["kind"] == "file", place["manifest_id"]
            assert entry["sha256"] == place["sha256"], place["manifest_id"]


def test_every_page_is_documented(
    probe_list: dict[str, Any],
    questions: dict[object, dict[str, Any]],
    devices: dict[str, dict[str, str]],
) -> None:
    for probe in probe_list["probes"]:
        basis = probe["basis"]
        if "question" in basis:
            documented = pages_of_question(questions[basis["question"]])
        else:
            documented = pages_of_device(devices[basis["device"]])
        assert documented, probe["id"]
        for place in probe["expected"]:
            for page in place["pages"]:
                assert (place["manifest_id"], page) in documented, (probe["id"], page)


def test_documented_pdf_pages_are_all_expected(
    probe_list: dict[str, Any], questions: dict[object, dict[str, Any]]
) -> None:
    """A probe based on a test question expects every PDF page of its sources."""
    for probe in probe_list["probes"]:
        if "question" not in probe["basis"]:
            continue
        expected = {
            (place["manifest_id"], page) for place in probe["expected"] for page in place["pages"]
        }
        assert expected == pages_of_question(questions[probe["basis"]["question"]]), probe["id"]


def test_the_required_questions_are_covered_in_own_words(
    probe_list: dict[str, Any], questions: dict[object, dict[str, Any]]
) -> None:
    worded = {
        probe["basis"]["question"]: probe["query"]
        for probe in probe_list["probes"]
        if "question" in probe["basis"] and not is_address(probe["query"])
    }

    assert set(worded) >= REQUIRED_QUESTIONS
    for number, query in worded.items():
        assert query != questions[number]["question"], number


def test_addresses_come_from_the_test_factory(
    probe_list: dict[str, Any],
    questions: dict[object, dict[str, Any]],
    devices: dict[str, dict[str, str]],
) -> None:
    """Probes that search an address use one of questions.yaml or devices.csv."""
    addresses = [probe for probe in probe_list["probes"] if is_address(probe["query"])]
    bases = {next(iter(probe["basis"])) for probe in addresses}

    # The address of test question 1 and the address of a PLC.
    assert bases == {"question", "device"}
    for probe in addresses:
        basis = probe["basis"]
        if "question" in basis:
            assert probe["query"] in questions[basis["question"]]["key_facts"]
        else:
            row = devices[basis["device"]]
            assert row["device_class"] == "plc"
            assert probe["query"] == row["ip_address"]
