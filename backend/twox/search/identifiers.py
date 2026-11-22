"""Identifiers in a search query: addresses, part numbers, error codes.

The full-text parser of PostgreSQL splits or reads identifiers in its own way
(``PLC-01`` becomes ``plc`` and ``-01``, ``fe80::1`` becomes ``fe80`` and
``1``). So every identifier of the query is searched a second time as an
exact string, with boundaries that keep ``192.168.0.5`` from matching
``192.168.0.50``. This module finds the identifiers and builds the regular
expressions for PostgreSQL (``~*``) and for Python (highlights); both escape
the user's input.

Recognised kinds (see :class:`IdentifierKind`):

* IPv4 addresses with an optional prefix length (``10.0.0.1/24``);
* IPv6 addresses with an optional prefix length (``fe80::1``);
* MAC addresses with ``:`` or ``-`` (``00:1b:1b:aa:bb:cc``);
* other tokens of ASCII letters and digits, optionally joined by ``-``,
  ``_``, ``.`` or ``/``, that contain a digit and at least one letter or
  joining character (``PLC-01``, ``E1234``, ``S7-1200``, ``3.5``). Plain
  numbers such as ``1200`` are left to the full-text search, which keeps
  them as words anyway.

Boundaries: an identifier must not be preceded or followed by a letter,
digit or underscore, nor by ``.`` or ``-`` that joins it to a further letter
or digit. ``192.168.0.5`` therefore matches ``IP:192.168.0.5``,
``192.168.0.5/24``, ``192.168.0.5:502`` and ``192.168.0.5.`` at the end of
a sentence, but not ``192.168.0.50``, ``10.192.168.0.5`` or
``192.168.0.5.1``. IPv6 and MAC addresses treat ``:`` as joining as well, so
``fe80::1`` does not match ``fe80::1:5``. Letters match without regard to
case. Different spellings of the same address (``fe80::1`` and
``fe80:0::1``, ``-`` and ``:`` in MAC addresses) are not normalised.
"""

import ipaddress
import re
from dataclasses import dataclass
from enum import StrEnum

#: At most this many identifiers of one query are searched exactly; each one
#: adds a condition to the query.
MAX_IDENTIFIERS = 10

#: Characters stripped from the ends of a query token before it is checked:
#: quotes, brackets and sentence punctuation around an identifier.
_STRIP_CHARS = "\"'()[]{}<>,;!?"
#: Stripped from the end only: a full stop or colon after an identifier.
_STRIP_END_CHARS = ".:"

_IPV4 = re.compile(r"([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})(?:/([0-9]{1,2}))?")
_MAC = re.compile(r"[0-9A-Fa-f]{2}([:-])[0-9A-Fa-f]{2}(?:\1[0-9A-Fa-f]{2}){4}")
_IPV6_CHARS = re.compile(r"[0-9A-Fa-f:.]+(?:/[0-9]{1,3})?")
_GENERIC = re.compile(r"[A-Za-z0-9]+(?:[-_./][A-Za-z0-9]+)*")


class IdentifierKind(StrEnum):
    """What kind of identifier a query token is."""

    IPV4 = "ipv4"
    IPV6 = "ipv6"
    MAC = "mac"
    GENERIC = "generic"


@dataclass(frozen=True, slots=True)
class Identifier:
    """An identifier found in a query, as typed (without surrounding punctuation)."""

    value: str
    kind: IdentifierKind

    @property
    def joiners(self) -> str:
        """Characters that join this identifier to a neighbouring one."""
        if self.kind in {IdentifierKind.IPV6, IdentifierKind.MAC}:
            return ".:-"
        return ".-"


def _identify_token(raw: str) -> Identifier | None:
    """The identifier in a query token, without the punctuation around it.

    A full stop or colon at the end is part of the identifier only where it
    makes one (``fe80::``); otherwise it ends the sentence.
    """
    token = raw.strip(_STRIP_CHARS)
    candidates = [token]
    if token[-1:] in tuple(_STRIP_END_CHARS):
        candidates.append(token[:-1].strip(_STRIP_CHARS))
    for candidate in candidates:
        kind = classify(candidate) if candidate else None
        if kind is not None:
            return Identifier(value=candidate, kind=kind)
    return None


def _is_ipv4(token: str) -> bool:
    match = _IPV4.fullmatch(token)
    if match is None:
        return False
    octets = [int(part) for part in match.group(1, 2, 3, 4)]
    prefix = match.group(5)
    return all(octet <= 255 for octet in octets) and (prefix is None or int(prefix) <= 32)


def _is_ipv6(token: str) -> bool:
    if token.count(":") < 2 or _IPV6_CHARS.fullmatch(token) is None:
        return False
    if not any(char.isalnum() for char in token.partition("/")[0]):
        return False  # "::" alone is valid, but matches every double colon
    address, _, prefix = token.partition("/")
    try:
        ipaddress.IPv6Address(address)
    except ValueError:
        return False
    return prefix == "" or int(prefix) <= 128


def _is_generic(token: str) -> bool:
    if _GENERIC.fullmatch(token) is None:
        return False
    has_digit = any(char.isdigit() for char in token)
    has_other = any(not char.isdigit() for char in token)
    return has_digit and has_other


def classify(token: str) -> IdentifierKind | None:
    """The kind of identifier ``token`` is, or ``None`` for an ordinary word."""
    if _is_ipv4(token):
        return IdentifierKind.IPV4
    if _MAC.fullmatch(token) is not None:
        return IdentifierKind.MAC
    if _is_ipv6(token):
        return IdentifierKind.IPV6
    if _is_generic(token):
        return IdentifierKind.GENERIC
    return None


def find_identifiers(query: str) -> list[Identifier]:
    """The identifiers in ``query``, in order, without duplicates.

    Tokens are separated by white space. A token that starts with ``-`` is an
    exclusion in the web search syntax and is skipped. Duplicates are
    compared without regard to case. At most :data:`MAX_IDENTIFIERS`.
    """
    found: list[Identifier] = []
    seen: set[str] = set()
    for raw in query.split():
        if raw.lstrip(_STRIP_CHARS).startswith("-"):
            continue
        identifier = _identify_token(raw)
        if identifier is None or identifier.value.casefold() in seen:
            continue
        seen.add(identifier.value.casefold())
        found.append(identifier)
        if len(found) == MAX_IDENTIFIERS:
            break
    return found


def _escape(value: str) -> str:
    """``value`` with a backslash before every character that is not a letter or digit.

    In PostgreSQL's advanced regular expressions and in Python's ``re``, a
    backslash before such a character stands for the character itself.
    """
    return "".join(char if char.isascii() and char.isalnum() else "\\" + char for char in value)


def postgres_pattern(identifier: Identifier) -> str:
    """Regular expression for PostgreSQL's ``~*`` that finds ``identifier`` exactly."""
    word = "[[:alnum:]_]"
    joiners = _escape(identifier.joiners)
    return (
        f"(?<!{word})(?<!{word}[{joiners}])"
        f"{_escape(identifier.value)}"
        f"(?!{word})(?![{joiners}]{word})"
    )


def python_pattern(identifier: Identifier) -> re.Pattern[str]:
    """The same expression as :func:`postgres_pattern` for Python's ``re``."""
    joiners = _escape(identifier.joiners)
    return re.compile(
        f"(?<!\\w)(?<!\\w[{joiners}]){_escape(identifier.value)}(?!\\w)(?![{joiners}]\\w)",
        re.IGNORECASE,
    )
