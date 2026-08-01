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
    TransportError,
    UrllibTransport,
)
from ghagen.pin.lockfile import (
    Lockfile,
    LockfileError,
    PinEntry,
    read_lockfile,
    write_lockfile,
)
from ghagen.pin.plan import (
    PlanFormat,
    UpdateAction,
    UpdateOutput,
    UpdatePlan,
    parse_labels,
    plan_update,
    render_update_plan,
)
from ghagen.pin.render import UpgradeFormat, render_upgrade_report
from ghagen.pin.sites import UsesSite, iter_uses_sites
from ghagen.pin.transform import PinTransform
from ghagen.pin.uses import UsesRef
from ghagen.pin.versions import BumpSeverity

__all__ = [
    "BumpSeverity",
    "GitHubClient",
    "HttpClient",
    "Lockfile",
    "LockfileError",
    "LockfileStaleEntry",
    "PinEntry",
    "PinReport",
    "PinTransform",
    "PlanFormat",
    "ResolveError",
    "ResolvedPin",
    "Response",
    "SyncReport",
    "TransportError",
    "UpdateAction",
    "UpdateOutput",
    "UpdatePlan",
    "UpgradeFormat",
    "UpgradeReport",
    "UrllibTransport",
    "UsesRef",
    "UsesSite",
    "VersionBump",
    "check_sync",
    "collect_uses_refs",
    "iter_uses_sites",
    "parse_labels",
    "pin",
    "plan_update",
    "read_lockfile",
    "render_update_plan",
    "render_upgrade_report",
    "upgrade",
    "write_lockfile",
]
