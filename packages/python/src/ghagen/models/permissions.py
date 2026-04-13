"""Permissions model for GitHub Actions workflows and jobs."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ghagen._raw import Raw
from ghagen.emitter.key_order import PERMISSIONS_KEY_ORDER
from ghagen.models._base import GhagenModel
from ghagen.models.common import PermissionLevel


class Permissions(GhagenModel):
    """GitHub Actions permissions for GITHUB_TOKEN scopes.

    Can be used at workflow or job level. Each scope can be set to
    read, write, or none.
    """

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

    def _get_key_order(self) -> list[str]:
        return PERMISSIONS_KEY_ORDER


# Convenience: workflow-level permission shorthand
PermissionsValue = (
    Permissions | Literal["read-all", "write-all"] | Raw[str] | dict[str, str]
)
