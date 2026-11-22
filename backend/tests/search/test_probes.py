"""The probe list of M2 refers only to what the test factory documents (056).

Every ``manifest_id`` and ``sha256`` of ``twox/search/probes/m2.json`` must be
an entry of ``testfactory/manifest.yaml`` (JSON notation, read with ``json``),
and every page must be named for that entry in ``testfactory/questions.yaml``
(probe basis ``question``) or in ``testfactory/layout/devices.csv`` (basis
``device``). Compose mounts the three files read-only into ``backend-dev``.

A place in the other language edition of the same manual counts as correct
(E-61, work order 067). The test factory names only one edition, so such a
place is marked in the basis (``other_language_edition``: its manifest id
mapped to the one of the documented place) and checked against that place
and the manifest: same pages, same document version, another language.
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


#: Bases that name where the pages of a probe are documented.
SOURCE_BASES = ("question", "device")
#: Basis key of places in the other language edition of a documented manual.
OTHER_EDITION = "other_language_edition"
#: Probes on the documentation of the production line also expect the English edition.
APS_EDITIONS = {"aps-documentation-en": "aps-documentation-de"}


def is_address(query: str) -> bool:
    return IPV4.fullmatch(query) is not None


def source_basis(probe: dict[str, Any]) -> str:
    """The one basis key that names where the pages of ``probe`` are documented."""
    (key,) = [key for key in SOURCE_BASES if key in probe["basis"]]
    return key


def other_editions(probe: dict[str, Any]) -> dict[str, str]:
    """Manifest id of a place in another language edition -> id of the documented place."""
    editions = probe["basis"].get(OTHER_EDITION, {})
    assert isinstance(editions, dict), probe["id"]
    return editions


def documented_places(probe: dict[str, Any]) -> list[dict[str, Any]]:
    """The expected places named by the test factory itself (not another edition)."""
    editions = other_editions(probe)
    return [place for place in probe["expected"] if place["manifest_id"] not in editions]


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
        if source_basis(probe) == "question":
            documented = pages_of_question(questions[basis["question"]])
        else:
            documented = pages_of_device(devices[basis["device"]])
        assert documented, probe["id"]
        for place in documented_places(probe):
            for page in place["pages"]:
                assert (place["manifest_id"], page) in documented, (probe["id"], page)


def test_documented_pdf_pages_are_all_expected(
    probe_list: dict[str, Any], questions: dict[object, dict[str, Any]]
) -> None:
    """A probe based on a test question expects every PDF page of its sources."""
    for probe in probe_list["probes"]:
        if source_basis(probe) != "question":
            continue
        expected = {
            (place["manifest_id"], page)
            for place in documented_places(probe)
            for page in place["pages"]
        }
        assert expected == pages_of_question(questions[probe["basis"]["question"]]), probe["id"]


def test_places_in_the_other_language_edition_match_the_documented_place(
    probe_list: dict[str, Any], manifest: dict[str, dict[str, Any]]
) -> None:
    """E-61: the same pages of the same manual in another language, checksum from the manifest."""
    for probe in probe_list["probes"]:
        editions = other_editions(probe)
        places = {place["manifest_id"]: place for place in probe["expected"]}
        assert set(editions) <= set(places), probe["id"]
        for edition, documented in editions.items():
            assert documented in places, (probe["id"], documented)
            assert documented not in editions, (probe["id"], documented)
            assert sorted(places[edition]["pages"]) == sorted(places[documented]["pages"]), (
                probe["id"],
                edition,
            )
            this, that = manifest[edition], manifest[documented]
            assert this["sha256"] == places[edition]["sha256"], (probe["id"], edition)
            assert this["document_version"] == that["document_version"], (probe["id"], edition)
            assert this["language"] != that["language"], (probe["id"], edition)


def test_every_probe_on_the_aps_documentation_accepts_both_editions(
    probe_list: dict[str, Any],
) -> None:
    """E-61: wherever the German documentation of the line is expected, the English one is too."""
    covered = []
    for probe in probe_list["probes"]:
        ids = {place["manifest_id"] for place in probe["expected"]}
        for edition, documented in APS_EDITIONS.items():
            if documented in ids:
                assert edition in ids, probe["id"]
                assert other_editions(probe).get(edition) == documented, probe["id"]
                covered.append(probe["id"])
    assert covered == ["ip-ccu", "ip-drill-plc", "question-1", "question-3", "question-7"]


def test_the_required_questions_are_covered_in_own_words(
    probe_list: dict[str, Any], questions: dict[object, dict[str, Any]]
) -> None:
    worded = {
        probe["basis"]["question"]: probe["query"]
        for probe in probe_list["probes"]
        if source_basis(probe) == "question" and not is_address(probe["query"])
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
    bases = {source_basis(probe) for probe in addresses}

    # The address of test question 1 and the address of a PLC.
    assert bases == {"question", "device"}
    for probe in addresses:
        basis = probe["basis"]
        if source_basis(probe) == "question":
            assert probe["query"] in questions[basis["question"]]["key_facts"]
        else:
            row = devices[basis["device"]]
            assert row["device_class"] == "plc"
            assert probe["query"] == row["ip_address"]
