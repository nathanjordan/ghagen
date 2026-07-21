"""Permissions model for GitHub Actions workflows and jobs."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ghagen._raw import Raw
from ghagen.models._base import GhagenModel
from ghagen.models.common import PermissionLevel
from ghagen.models.spec import ModelSpec

PERMISSIONS_SPEC = ModelSpec(
    yaml_keys={
        "actions": "actions",
        "checks": "checks",
        "contents": "contents",
        "deployments": "deployments",
        "discussions": "discussions",
        "id_token": "id-token",
        "issues": "issues",
        "packages": "packages",
        "pages": "pages",
        "pull_requests": "pull-requests",
        "repository_projects": "repository-projects",
        "security_events": "security-events",
        "statuses": "statuses",
    },
    order=(
        "actions",
        "checks",
        "contents",
        "deployments",
        "discussions",
        "id-token",
        "issues",
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
    checks: PermissionLevel | Raw[str] | None = None
    contents: PermissionLevel | Raw[str] | None = None
    deployments: PermissionLevel | Raw[str] | None = None
    discussions: PermissionLevel | Raw[str] | None = None
    id_token: PermissionLevel | Raw[str] | None = Field(
        None, serialization_alias="id-token"
    )
    issues: PermissionLevel | Raw[str] | None = None
    packages: PermissionLevel | Raw[str] | None = None
    pages: PermissionLevel | Raw[str] | None = None
    pull_requests: PermissionLevel | Raw[str] | None = Field(
        None, serialization_alias="pull-requests"
    )
    repository_projects: PermissionLevel | Raw[str] | None = Field(
        None, serialization_alias="repository-projects"
    )
    security_events: PermissionLevel | Raw[str] | None = Field(
        None, serialization_alias="security-events"
    )
    statuses: PermissionLevel | Raw[str] | None = None
