"""Permissions model for GitHub Actions workflows and jobs."""

from __future__ import annotations

from typing import ClassVar, Literal

from ghagen._raw import Raw
from ghagen.models._base import GhagenModel, OrRaw
from ghagen.models.common import PermissionLevel
from ghagen.models.spec import ModelSpec

PERMISSIONS_SPEC = ModelSpec(
    yaml_keys={
        "actions": "actions",
        "artifact_metadata": "artifact-metadata",
        "attestations": "attestations",
        "checks": "checks",
        "code_quality": "code-quality",
        "contents": "contents",
        "copilot_requests": "copilot-requests",
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
        "vulnerability_alerts": "vulnerability-alerts",
    },
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
    code_quality: PermissionLevel | Raw[str] | None = None
    contents: PermissionLevel | Raw[str] | None = None
    # The Snapshot narrows this scope to `write` alone -- there is no read
    # or none level for it. Typed like its siblings, for the same reason
    # `models` is: the shared value table binds `pattern` strings, and this
    # grammar is an `enum`.
    copilot_requests: PermissionLevel | Raw[str] | None = None
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
    # Narrowed upstream to `read | none`, like `models`; see the note there.
    vulnerability_alerts: PermissionLevel | Raw[str] | None = None


#: Everything a ``permissions:`` key accepts, at either level.
#:
#: The canonical Snapshot defines ``permissions`` once
#: (``definitions.permissions``) as a two-way ``oneOf`` — the blanket enum
#: ``read-all`` / ``write-all``, or the per-scope ``permissions-event``
#: object — and both ``Workflow.permissions`` and ``Job.permissions`` are a
#: bare ``$ref`` to it. One schema node, one alias: writing the union out at
#: each use site is how the two drifted apart in the first place (issue 27 —
#: ``Job`` was missing the string shorthand while ``Workflow`` had it, and the
#: API reference published this alias under this name while neither port
#: defined it).
#:
#: ``OrRaw[...]`` adds the every-field ``CommentedMap`` passthrough; ``Raw[str]``
#: is the hatch for a blanket keyword GitHub ships before ghagen models it.
#: Bound to the Snapshot, with executed accept/reject vectors, by
#: ``schema/conformance-inputs.yml`` under ``job.permissions`` and
#: ``workflow.permissions``. The TypeScript peer is ``PermissionsValue`` in
#: ``models/permissions.ts``.
PermissionsValue = OrRaw[Permissions | Literal["read-all", "write-all"] | Raw[str]]
