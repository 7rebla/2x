"""Identifiers in search queries and their exact patterns (047)."""

import pytest
from django.db import connection

from twox.search.identifiers import (
    MAX_IDENTIFIERS,
    Identifier,
    IdentifierKind,
    classify,
    find_identifiers,
    postgres_pattern,
    python_pattern,
)


@pytest.mark.parametrize(
    ("token", "kind"),
    [
        ("192.168.0.5", IdentifierKind.IPV4),
        ("10.0.0.1/24", IdentifierKind.IPV4),
        ("255.255.255.0", IdentifierKind.IPV4),
        ("fe80::1", IdentifierKind.IPV6),
        ("2001:db8::17/64", IdentifierKind.IPV6),
        ("::ffff:192.0.2.1", IdentifierKind.IPV6),
        ("00:1b:1b:aa:bb:cc", IdentifierKind.MAC),
        ("00-1B-1B-AA-BB-CC", IdentifierKind.MAC),
        ("PLC-01", IdentifierKind.GENERIC),
        ("E1234", IdentifierKind.GENERIC),
        ("S7-1200", IdentifierKind.GENERIC),
        ("x86_64", IdentifierKind.GENERIC),
        ("A1/B2", IdentifierKind.GENERIC),
        ("3.5", IdentifierKind.GENERIC),
        # Not a valid IPv4 address, but still a dotted token with digits.
        ("300.1.1.1", IdentifierKind.GENERIC),
    ],
)
def test_classify_recognises_identifiers(token: str, kind: IdentifierKind) -> None:
    assert classify(token) == kind


@pytest.mark.parametrize(
    "token",
    ["pump", "Steuerung", "1200", "42", "::", "12:30", "PLC-", "-01", "a--1", "C++", "", "über1"],
)
def test_classify_leaves_ordinary_words(token: str) -> None:
    assert classify(token) is None


@pytest.mark.parametrize(
    "token",
    [
        # Arabic-Indic digits: 192.168.0.5
        "\u0661\u0669\u0662.\u0661\u0666\u0668.\u0660.\u0665",
        "192.168.0.\u0665",
        # Fullwidth digits in the prefix length: fe80::1/64
        "fe80::1/\uff16\uff14",
    ],
)
def test_non_ascii_digits_make_no_address(token: str) -> None:
    assert classify(token) not in {IdentifierKind.IPV4, IdentifierKind.IPV6}


def test_ipv4_prefix_above_32_is_no_ipv4() -> None:
    assert classify("10.0.0.1/33") == IdentifierKind.GENERIC


def test_find_identifiers_strips_punctuation_and_skips_words() -> None:
    query = 'Pumpe (192.168.0.5), "PLC-01" und E1234. Adresse fe80::1: ok'

    assert find_identifiers(query) == [
        Identifier("192.168.0.5", IdentifierKind.IPV4),
        Identifier("PLC-01", IdentifierKind.GENERIC),
        Identifier("E1234", IdentifierKind.GENERIC),
        Identifier("fe80::1", IdentifierKind.IPV6),
    ]


def test_trailing_colon_stays_where_it_makes_the_identifier() -> None:
    assert find_identifiers("prefix fe80:: and fe80::1:") == [
        Identifier("fe80::", IdentifierKind.IPV6),
        Identifier("fe80::1", IdentifierKind.IPV6),
    ]


def test_find_identifiers_skips_exclusions_and_duplicates() -> None:
    assert find_identifiers("PLC-01 plc-01 -PLC-02 -E5") == [
        Identifier("PLC-01", IdentifierKind.GENERIC)
    ]


def test_find_identifiers_stops_at_the_maximum() -> None:
    query = " ".join(f"E{number}" for number in range(MAX_IDENTIFIERS + 5))

    assert len(find_identifiers(query)) == MAX_IDENTIFIERS


@pytest.mark.parametrize("query", ["", "   ", "'", "\\", "(", "\"'()\\", "-", "--"])
def test_find_identifiers_with_special_characters(query: str) -> None:
    assert find_identifiers(query) == []


#: Identifier, text, whether the identifier is in the text as an exact token.
BOUNDARY_CASES = [
    ("192.168.0.5", "address 192.168.0.5 here", True),
    ("192.168.0.5", "address 192.168.0.50 here", False),
    ("192.168.0.5", "address 10.192.168.0.5 here", False),
    ("192.168.0.5", "address 192.168.0.5.1 here", False),
    ("192.168.0.5", "the address is 192.168.0.5.", True),
    ("192.168.0.5", "IP:192.168.0.5", True),
    ("192.168.0.5", "net 192.168.0.5/24", True),
    ("192.168.0.5", "Modbus 192.168.0.5:502", True),
    ("192.168.0.5", "| PLC-01 | 192.168.0.5 | 255.255.255.0 |", True),
    ("192.168.0.5", "x192.168.0.5", False),
    ("10.0.0.1/24", "net 10.0.0.1/24 and more", True),
    ("10.0.0.1/24", "net 10.0.0.1/240", False),
    ("fe80::1", "link fe80::1 up", True),
    ("fe80::1", "link FE80::1 up", True),
    ("fe80::1", "link fe80::10 up", False),
    ("fe80::1", "link fe80::1:5 up", False),
    ("00:1b:1b:aa:bb:cc", "MAC 00:1B:1B:AA:BB:CC", True),
    ("00:1b:1b:aa:bb:cc", "MAC 00:1b:1b:aa:bb:cc:dd", False),
    ("PLC-01", "the plc-01 starts", True),
    ("PLC-01", "the PLC-010 starts", False),
    ("PLC-01", "the PLC-01-A starts", False),
    ("PLC-01", "the XPLC-01 starts", False),
    ("PLC-01", "the A-PLC-01 starts", False),
    ("PLC-01", "(PLC-01)", True),
    ("E1234", "error E1234: stop", True),
    ("E1234", "error E12345", False),
    ("E1234", "error E1234_X", False),
]


@pytest.mark.parametrize(("value", "text", "expected"), BOUNDARY_CASES)
def test_python_pattern_boundaries(value: str, text: str, expected: bool) -> None:
    identifier = Identifier(value, classify(value) or IdentifierKind.GENERIC)

    assert (python_pattern(identifier).search(text) is not None) is expected


@pytest.mark.django_db
@pytest.mark.parametrize(("value", "text", "expected"), BOUNDARY_CASES)
def test_postgres_pattern_matches_like_python(value: str, text: str, expected: bool) -> None:
    identifier = Identifier(value, classify(value) or IdentifierKind.GENERIC)

    with connection.cursor() as cursor:
        cursor.execute("SELECT %s ~* %s", [text, postgres_pattern(identifier)])
        row = cursor.fetchone()

    assert row == (expected,)


def test_patterns_escape_every_character_but_letters_and_digits() -> None:
    identifier = Identifier("a.b-c/d_e:f", IdentifierKind.GENERIC)

    assert "a\\.b\\-c\\/d\\_e\\:f" in postgres_pattern(identifier)
    assert python_pattern(identifier).search("x a.b-c/d_e:f y") is not None
    assert python_pattern(identifier).search("x aXb-c/d_e:f y") is None
