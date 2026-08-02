"""The version-tag grammar for GitHub Action refs — ghagen's own.

This module alone answers: *is this ref a version tag, which of two tags is
newer, and how big is the jump?*  It holds the tag regex, the prefix rule, the
canonical-release rule, the segment cap, the total order, the same-prefix
filter, and the severity classification.

The grammar is declared once, in ``schema/tag-grammar.yml``, and pinned by
both ports' suites.  No third-party version library sits on this path — see
``docs/adr/0008-ghagen-owns-its-tag-grammar.md``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

# Matches an optional prefix (delimited by - or /) followed by an
# optional ``v`` and a numeric version.
#   group 1 = prefix (including delimiter), or None
#   group 2 = the version digits (e.g. "4", "4.1", "4.1.2", "4.1.2.3")
#
# ADR-0008 writes this grammar as ``^(?:(.+)[/-])?v?(\d+(?:\.\d+)*)$`` and
# means one accept-set for both ports.  Written with those metacharacters it is
# not one accept-set, because ``\d``, ``.`` and ``$`` each denote something
# wider in Python than in JavaScript, and every difference lets Python accept a
# ref TypeScript rejects — which is the damaging direction, since an accepted
# ref is a bump and a bump rewrites the user's workflow files.  So the classes
# below are spelled out to the narrower, JavaScript reading:
#
#   ``\d``  JavaScript: exactly [0-9].  Python: every Unicode decimal digit, so
#           the Arabic-indic ``v١.٢.٤`` parsed as 1.2.4 here and nowhere else.
#   ``.``   JavaScript excludes all four line terminators (\n, \r and the
#           two Unicode line/paragraph separators); Python excludes only
#           \n, so a carriage return could sit inside a prefix here.
#   ``$``   JavaScript anchors at the end of the string; Python's ``$`` also
#           matches just before a trailing \n.  ``fullmatch`` is the anchoring
#           that has no such exemption (equivalent to \A...\Z).
_NOT_LINE_TERMINATOR = r"[^\n\r\u2028\u2029]"
_TAG_RE = re.compile(
    rf"(?:({_NOT_LINE_TERMINATOR}+)[/-])?"  # optional prefix + delimiter
    r"v?([0-9]+(?:\.[0-9]+)*)"  # version digits
)

#: Largest value a release segment may hold (10**15 - 1).
#:
#: The rule is on the integer **value**, not on the literal's length: a
#: zero-padded ``v0000000000000001.0.0`` is 16 characters but the value 1, and
#: is accepted, while ``v9999999999999999.0.0`` is rejected.  The cap exists so
#: both ports can hold a release in a plain integer array — JS numbers are
#: exact below 2**53, and 999_999_999_999_999 < 9_007_199_254_740_991.
_MAX_SEGMENT = 999_999_999_999_999

#: Digits in :data:`_MAX_SEGMENT` — the length test that stands in for the
#: value test when the literal is too long to convert at all.
_MAX_SEGMENT_DIGITS = len(str(_MAX_SEGMENT))

BumpSeverity = Literal["major", "minor", "patch"]
"""Severity of a version bump."""


@dataclass(frozen=True, order=True)
class ParsedTag:
    """A parsed version tag: its prefix and its canonical release.

    Mirrors the TypeScript ``ParsedTag`` shape down to the member that carries
    the behaviour: ``release`` is the same integer sequence in both ports, and
    the ordering on it is the same rule.  Two tags compare — and hash — by
    ``release`` alone, so ``v1.2.3`` and ``v1.2.3.0`` are the same version.
    """

    tag: str = field(compare=False)
    """The original tag string, preserved for rewriting the uses-site."""

    prefix: str | None = field(compare=False)
    """Prefix (without delimiter), or ``None`` when there is no prefix."""

    release: tuple[int, ...]
    """Canonical release: length >= 3, no trailing zeros past index 2."""


@dataclass(frozen=True)
class Bump:
    """A newer tag for a ref, with everything the caller needs about it."""

    current: ParsedTag
    latest: ParsedTag
    severity: BumpSeverity


def _segment_value(literal: str) -> int | None:
    """The value of one release segment, or ``None`` when it exceeds the cap.

    The cap is on the value, so leading zeros are stripped before the test —
    ``0000000000000001`` is 16 characters but the value 1, and is accepted.

    The length test comes *before* ``int()`` on purpose.  CPython refuses to
    build an integer from a decimal string longer than
    ``sys.get_int_max_str_digits()`` (4300 by default) and raises
    ``ValueError``; a 5000-digit segment therefore used to escape this module
    as an exception rather than as "not a version tag".  Anything longer than
    :data:`_MAX_SEGMENT_DIGITS` is over the cap by construction, so the test
    that avoids the conversion is the same test the cap already demands.
    """
    digits = literal.lstrip("0")
    if len(digits) > _MAX_SEGMENT_DIGITS:
        return None
    value = int(digits) if digits else 0
    return value if value <= _MAX_SEGMENT else None


def parse_tag(tag: str) -> ParsedTag | None:
    """Parse a GitHub Action tag into a :class:`ParsedTag`, or ``None``.

    A ref is a version tag iff it matches the tag regex — an optional
    ``prefix-`` / ``prefix/``, an optional ``v``, then dot-separated integers
    — **and** every segment's value is at most :data:`_MAX_SEGMENT`.  When a
    prefix is present the numeric part needs at least two segments, which
    keeps branch-like refs such as ``release/v1`` out.

    The canonical release parses each segment as an integer, pads with zeros
    to length three, then drops trailing zeros beyond index 2: ``v4`` becomes
    ``(4, 0, 0)``, ``v01.02.03`` becomes ``(1, 2, 3)``, and ``v1.2.3.0``
    becomes ``(1, 2, 3)`` — the same version as ``v1.2.3``.

    Returns ``None`` for refs that are not version tags (e.g. ``main``,
    ``release/v1``, ``v1.2.3-rc1``).
    """
    # ``fullmatch``, not ``match``: ``$`` would also match just before a
    # trailing newline, and a git ref name cannot contain a newline at all.
    m = _TAG_RE.fullmatch(tag)
    if m is None:
        return None

    prefix = m.group(1)
    segments = m.group(2).split(".")

    # When a prefix is present (foo/v1, release/v1), require at least two
    # version segments so that branch-like refs such as ``release/v1`` are
    # rejected while ``prefix/v1.0.0`` is accepted.
    if prefix is not None and len(segments) < 2:
        return None

    release: list[int] = []
    for literal in segments:
        value = _segment_value(literal)
        if value is None:
            return None
        release.append(value)

    # Pad to three so ``v4`` -> (4, 0, 0), then strip trailing zeros beyond
    # the third so ``v1.2.3.0`` compares equal to ``v1.2.3``.
    while len(release) < 3:
        release.append(0)
    while len(release) > 3 and release[-1] == 0:
        release.pop()

    return ParsedTag(tag=tag, prefix=prefix, release=tuple(release))


def _classify(current: ParsedTag, latest: ParsedTag) -> BumpSeverity:
    """Severity of the jump from *current* to *latest* (both length >= 3)."""
    if latest.release[0] != current.release[0]:
        return "major"
    if latest.release[1] != current.release[1]:
        return "minor"
    return "patch"


def latest_bump(current_ref: str, available_tags: Iterable[str]) -> Bump | None:
    """The newest same-prefix tag strictly newer than *current_ref*, classified.

    ``None`` when *current_ref* is not a version tag, or when nothing in
    *available_tags* is newer.  Equal versions are not newer, so they produce
    no :class:`Bump` at all.  Every returned ``Bump`` holds parsed values; no
    caller re-parses (ADR-0006).
    """
    current = parse_tag(current_ref)
    if current is None:
        return None

    best: ParsedTag | None = None
    for tag in available_tags:
        parsed = parse_tag(tag)
        if parsed is None:
            continue

        # Only consider tags that share the same prefix.
        if parsed.prefix != current.prefix:
            continue

        if parsed.release <= current.release:
            continue

        if best is None or parsed.release > best.release:
            best = parsed

    if best is None:
        return None

    return Bump(current=current, latest=best, severity=_classify(current, best))
