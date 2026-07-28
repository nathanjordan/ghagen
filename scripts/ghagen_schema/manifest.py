"""The validated manifest interface -- sole owner of the filename convention.

``schema/manifest.json`` maps a short name to ``{url, filename}``. This module
is the one loader and the single authority for the
``<name>_schema.json -> <name>-types.generated.ts`` derivation. It validates
*loudly*: a ``filename`` that does not end in ``_schema.json`` raises (naming the
offending entry) instead of silently no-op'ing, the way the old regex in
``generate-types.ts`` did.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .paths import SCHEMA_DIR

#: Path to the shared schema registry.
MANIFEST_PATH = SCHEMA_DIR / "manifest.json"

_SCHEMA_SUFFIX = "_schema.json"
_GENERATED_SUFFIX = "-types.generated.ts"


def derive_generated_filename(snapshot_filename: str) -> str:
    """Derive the generated-types filename from a Snapshot filename.

    ``workflow_schema.json`` -> ``workflow-types.generated.ts``.

    Raises:
        ValueError: if *snapshot_filename* does not end in ``_schema.json``.
    """
    if not snapshot_filename.endswith(_SCHEMA_SUFFIX):
        raise ValueError(
            f"manifest filename {snapshot_filename!r} must end in "
            f"{_SCHEMA_SUFFIX!r} so the generated-types name can be derived; "
            "rename it or fix the manifest entry."
        )
    stem = snapshot_filename[: -len(_SCHEMA_SUFFIX)]
    return stem + _GENERATED_SUFFIX


@dataclass(frozen=True)
class ManifestEntry:
    """One validated manifest entry."""

    name: str
    url: str
    filename: str

    @property
    def generated_filename(self) -> str:
        """The generated-types filename derived from :attr:`filename`."""
        return derive_generated_filename(self.filename)


def load_manifest(path: Path | None = None) -> list[ManifestEntry]:
    """Load the manifest as validated, typed entries in registry order.

    Every entry's ``filename`` is validated to end in ``_schema.json`` (via
    :func:`derive_generated_filename`), so a convention violation fails loudly
    at load time.

    Raises:
        ValueError: on a malformed entry or a filename-convention violation.
    """
    manifest_path = path if path is not None else MANIFEST_PATH
    raw = json.loads(manifest_path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"{manifest_path} must be a JSON object of name -> entry.")

    entries: list[ManifestEntry] = []
    for name, info in raw.items():
        if not isinstance(info, dict) or "url" not in info or "filename" not in info:
            raise ValueError(
                f"manifest entry {name!r} must be an object with 'url' and "
                f"'filename'; got {info!r}."
            )
        entry = ManifestEntry(name=name, url=info["url"], filename=info["filename"])
        # Validate the filename convention eagerly (raises on violation).
        _ = entry.generated_filename
        entries.append(entry)
    return entries
