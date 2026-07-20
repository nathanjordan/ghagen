"""Version comparison utilities for GitHub Action tags.

Parses tag strings into :class:`packaging.version.Version` objects,
classifies the severity of version bumps, and finds the latest
available tag from a list of candidates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from packaging.version import InvalidVersion, Version

# Matches an optional prefix (delimited by - or /) followed by an
# optional ``v`` and a numeric version.
#   group 1 = prefix (including delimiter), or None
#   group 2 = the version digits (e.g. "4", "4.1", "4.1.2")
_TAG_RE = re.compile(
    r"^(?:(.+)[/-])?"  # optional prefix + delimiter
    r"v?(\d+(?:\.\d+)*)"  # version digits
    r"$"
)


@dataclass(frozen=True)
class ParsedTag:
    """A parsed tag — wraps a comparable version plus its optional prefix.

    Mirrors the TypeScript ``ParsedTag`` shape so the tag regex runs once
    (no separate prefix re-extraction).
    """

    tag: str
    """The original tag string (e.g. ``"v4"``, ``"prefix-v1.0.0"``)."""

    prefix: str | None
    """Prefix (without delimiter), or ``None`` when there is no prefix."""

    version: Version
    """Comparable semantic version."""


def parse_tag(tag: str) -> ParsedTag | None:
    """Parse a GitHub Action tag into a :class:`ParsedTag`, or ``None``.

    Strips a leading ``v``, pads single-segment versions (``v4`` becomes
    ``4.0.0``), and supports prefixed tags like ``prefix-v1.0.0`` or
    ``prefix/v1.0.0``.

    Returns ``None`` for refs that do not look like version tags (e.g.
    ``main``, ``release/v1``).
    """
    m = _TAG_RE.match(tag)
    if m is None:
        return None

    prefix = m.group(1)
    version_str = m.group(2)
    segments = version_str.split(".")

    # When a prefix is present (foo/v1, release/v1), require at least two
    # version segments so that branch-like refs such as ``release/v1`` are
    # rejected while ``prefix/v1.0.0`` is accepted.
    if prefix is not None and len(segments) < 2:
        return None

    # Pad to three segments so ``v4`` → ``4.0.0``, ``v4.1`` → ``4.1.0``.
    while len(segments) < 3:
        segments.append("0")

    try:
        version = Version(".".join(segments))
    except InvalidVersion:
        return None

    return ParsedTag(tag=tag, prefix=prefix, version=version)


def classify_bump(
    current: Version, latest: Version
) -> Literal["major", "minor", "patch"]:
    """Classify the severity of a version bump.

    Args:
        current: The currently-used version.
        latest: The newer version to compare against.

    Returns:
        ``"major"``, ``"minor"``, or ``"patch"``.
    """
    if latest.major != current.major:
        return "major"
    if latest.minor != current.minor:
        return "minor"
    return "patch"


def find_latest_tag(current_ref: str, available_tags: list[str]) -> str | None:
    """Find the latest tag that is newer than *current_ref*.

    Filters *available_tags* to those that share the same prefix (if any)
    as *current_ref*, parses them as versions, and returns the original
    tag string for the highest version — or ``None`` if *current_ref* is
    already up to date (or unparseable).

    Args:
        current_ref: The tag currently in use (e.g. ``"v4"``).
        available_tags: All known tags for the repository.

    Returns:
        The original tag string (preserving ``v`` prefix) of the latest
        version, or ``None`` if the current ref is already the latest or
        cannot be parsed.
    """
    current = parse_tag(current_ref)
    if current is None:
        return None

    best_tag: str | None = None
    best_version: Version | None = None

    for tag in available_tags:
        parsed = parse_tag(tag)
        if parsed is None:
            continue

        # Only consider tags that share the same prefix.
        if parsed.prefix != current.prefix:
            continue

        if parsed.version <= current.version:
            continue

        if best_version is None or parsed.version > best_version:
            best_version = parsed.version
            best_tag = tag

    return best_tag
