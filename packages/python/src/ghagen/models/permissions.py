"""Permissions model for GitHub Actions workflows and jobs."""

from __future__ import annotations

from typing import ClassVar

from ghagen._raw import Raw
from ghagen.models._base import GhagenModel
from ghagen.models.common import PermissionLevel
from ghagen.models.spec import ModelSpec

PERMISSIONS_SPEC = ModelSpec(
    yaml_keys={
        "actions": "actions",
        "artifact_metadata": "artifact-metadata",
        "attestations": "attestations",
        "checks": "checks",
        "contents": "contents",
        "deployments": "deployments",
        "discussions": "discussions",
        "id_token": "id-token",
        "issues": "issues",
        "models": "models",
        "packages": "packages",
        "pages": "pages",
        "pull_requests": "pull-requests",
        "repository_projects": "repository-projects",
        "security_events": "security-events",
        "statuses": "statuses",
    },
    order=(
        "actions",
        "artifact-metadata",
        "attestations",
        "checks",
        "contents",
        "deployments",
        "discussions",
        "id-token",
        "issues",
        "models",
        "packages",
        "pages",
        "pull-requests",
        "repository-projects",
        "security-events",
        "statuses",
    ),
)


class Permissions(GhagenModel):
    """GitHub Actions permissions for GITHUB_TOKEN scopes.

    Can be used at workflow or job level. Each scope can be set to
    read, write, or none.
    """

    SPEC: ClassVar[ModelSpec] = PERMISSIONS_SPEC

    actions: PermissionLevel | Raw[str] | None = None
    artifact_metadata: PermissionLevel | Raw[str] | None = None
    attestations: PermissionLevel | Raw[str] | None = None
    checks: PermissionLevel | Raw[str] | None = None
    contents: PermissionLevel | Raw[str] | None = None
    deployments: PermissionLevel | Raw[str] | None = None
    discussions: PermissionLevel | Raw[str] | None = None
    id_token: PermissionLevel | Raw[str] | None = None
    issues: PermissionLevel | Raw[str] | None = None
    # The Snapshot narrows this one scope to `read | none`; ghagen types it like
    # its fifteen siblings and does not enforce the narrower enum. The shared
    # value table (schema/conformance-values.yml) binds *pattern* strings, and
    # this grammar is an `enum`, not a `pattern` — see the ADR-0003 amendment.
    models: PermissionLevel | Raw[str] | None = None
    packages: PermissionLevel | Raw[str] | None = None
    pages: PermissionLevel | Raw[str] | None = None
    pull_requests: PermissionLevel | Raw[str] | None = None
    repository_projects: PermissionLevel | Raw[str] | None = None
    security_events: PermissionLevel | Raw[str] | None = None
    statuses: PermissionLevel | Raw[str] | None = None
