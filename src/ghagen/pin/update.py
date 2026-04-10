"""Apply version updates to user Python source files.

Replaces ``uses=`` string literals in-place, scoped to files identified
by the source-tracking module.
"""

from __future__ import annotations

from pathlib import Path


def apply_updates(
    updates: dict[str, str],
    ref_locations: dict[str, list[Path]],
) -> list[Path]:
    """Replace ``uses`` strings in user source files.

    Args:
        updates: Mapping of ``old_uses → new_uses``
            (e.g. ``{"actions/checkout@v4": "actions/checkout@v5"}``).
        ref_locations: Mapping of ``uses → [files]`` from
            :func:`ghagen.pin.sources.locate_uses_refs`.  Only files
            listed here are modified.

    Returns:
        Sorted list of files that were actually changed.
    """
    changed: set[Path] = set()

    for old_uses, new_uses in updates.items():
        if old_uses == new_uses:
            continue
        files = ref_locations.get(old_uses)
        if not files:
            continue
        for path in files:
            content = path.read_text()
            if old_uses in content:
                path.write_text(content.replace(old_uses, new_uses))
                changed.add(path)

    return sorted(changed)
