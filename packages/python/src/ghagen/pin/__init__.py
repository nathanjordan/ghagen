"""ghagen pin — SHA-based lockfile for GitHub Actions references."""

from ghagen.pin.collect import collect_uses_refs
from ghagen.pin.engine import (
    LockfileStaleEntry,
    PinReport,
    ResolvedPin,
    SyncReport,
    UpgradeReport,
    VersionBump,
    check_sync,
    pin,
    upgrade,
)
from ghagen.pin.github import (
    GitHubClient,
    HttpClient,
    ResolveError,
    Response,
    UrllibTransport,
)
from ghagen.pin.lockfile import (
    Lockfile,
    LockfileError,
    PinEntry,
    read_lockfile,
    write_lockfile,
)
from ghagen.pin.sites import UsesSite, iter_uses_sites
from ghagen.pin.transform import PinTransform
from ghagen.pin.uses import UsesRef

__all__ = [
    "GitHubClient",
    "HttpClient",
    "Lockfile",
    "LockfileError",
    "LockfileStaleEntry",
    "PinEntry",
    "PinReport",
    "PinTransform",
    "ResolveError",
    "ResolvedPin",
    "Response",
    "SyncReport",
    "UpgradeReport",
    "UrllibTransport",
    "UsesRef",
    "UsesSite",
    "VersionBump",
    "check_sync",
    "collect_uses_refs",
    "iter_uses_sites",
    "pin",
    "read_lockfile",
    "upgrade",
    "write_lockfile",
]
