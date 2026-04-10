"""Version comparison utilities for GitHub Action tags.

Parses tag strings into :class:`packaging.version.Version` objects,
classifies the severity of version bumps, and finds the latest
available tag from a list of candidates.
"""

from __future__ import annotations

import re
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


def parse_tag(tag: str) -> Version | None:
    """Parse a GitHub Action tag into a :class:`~packaging.version.Version`.

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
        return Version(".".join(segments))
    except InvalidVersion:
        return None


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


def find_latest_tag(
    current_ref: str, available_tags: list[str]
) -> str | None:
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
    current_version = parse_tag(current_ref)
    if current_version is None:
        return None

    current_prefix = _extract_prefix(current_ref)

    best_tag: str | None = None
    best_version: Version | None = None

    for tag in available_tags:
        # Only consider tags that share the same prefix.
        if _extract_prefix(tag) != current_prefix:
            continue

        version = parse_tag(tag)
        if version is None:
            continue

        if version <= current_version:
            continue

        if best_version is None or version > best_version:
            best_version = version
            best_tag = tag

    return best_tag


def _extract_prefix(tag: str) -> str | None:
    """Return the prefix portion of a tag, or ``None`` if there is no prefix.

    Examples::

        _extract_prefix("v4.1.2")           → None
        _extract_prefix("prefix-v1.0.0")    → "prefix"
        _extract_prefix("prefix/v1.0.0")    → "prefix"
    """
    m = _TAG_RE.match(tag)
    if m is None:
        return None
    return m.group(1)
