"""ghagen pin — SHA-based lockfile for GitHub Actions references."""

from ghagen.pin.collect import collect_uses_refs
from ghagen.pin.lockfile import Lockfile, PinEntry, read_lockfile, write_lockfile
from ghagen.pin.resolve import resolve_ref
from ghagen.pin.transform import PinTransform

__all__ = [
    "Lockfile",
    "PinEntry",
    "PinTransform",
    "collect_uses_refs",
    "read_lockfile",
    "resolve_ref",
    "write_lockfile",
]
