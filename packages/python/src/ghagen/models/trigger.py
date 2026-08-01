"""Trigger models for the `on:` section of GitHub Actions workflows."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from ghagen._raw import Raw
from ghagen.models._base import GhagenModel, OrRaw
from ghagen.models.spec import ModelSpec

PUSH_TRIGGER_SPEC = ModelSpec(
    yaml_keys={
        "branches": "branches",
        "branches_ignore": "branches-ignore",
        "tags": "tags",
        "tags_ignore": "tags-ignore",
        "paths": "paths",
        "paths_ignore": "paths-ignore",
    },
    order=(
        "branches",
        "branches-ignore",
        "tags",
        "tags-ignore",
        "paths",
        "paths-ignore",
    ),
)

PR_TRIGGER_SPEC = ModelSpec(
    yaml_keys={
        "branches": "branches",
        "branches_ignore": "branches-ignore",
        "paths": "paths",
        "paths_ignore": "paths-ignore",
        "types": "types",
    },
    order=("branches", "branches-ignore", "paths", "paths-ignore", "types"),
)

SCHEDULE_TRIGGER_SPEC = ModelSpec(yaml_keys={"cron": "cron"}, order=("cron",))

WORKFLOW_DISPATCH_INPUT_SPEC = ModelSpec(
    yaml_keys={
        "description": "description",
        "required": "required",
        "default": "default",
        "type": "type",
        "options": "options",
    },
    order=("description", "required", "default", "type", "options"),
)

WORKFLOW_DISPATCH_SPEC = ModelSpec(
    yaml_keys={"inputs": "inputs"},
    order=("inputs",),
)

WORKFLOW_CALL_INPUT_SPEC = ModelSpec(
    yaml_keys={
        "description": "description",
        "required": "required",
        "default": "default",
        "type": "type",
    },
    order=("description", "required", "default", "type"),
)

WORKFLOW_CALL_OUTPUT_SPEC = ModelSpec(
    yaml_keys={"description": "description", "value": "value"},
    order=("description", "value"),
)

WORKFLOW_CALL_SECRET_SPEC = ModelSpec(
    yaml_keys={"description": "description", "required": "required"},
    order=("description", "required"),
)

WORKFLOW_CALL_SPEC = ModelSpec(
    yaml_keys={"inputs": "inputs", "outputs": "outputs", "secrets": "secrets"},
    order=("inputs", "outputs", "secrets"),
)

# ``On`` has no canonical trigger order: ``order=None`` selects alphabetical
# emission (extras interleave). An empty ``workflow_dispatch`` emits as a bare
# ``workflow_dispatch:`` key via ``present_null_when_empty`` — the declared rule
# that replaces the old model-layer ``Raw(None)`` smuggle.
ON_SPEC = ModelSpec(
    yaml_keys={
        "push": "push",
        "pull_request": "pull_request",
        "pull_request_target": "pull_request_target",
        "workflow_dispatch": "workflow_dispatch",
        "workflow_call": "workflow_call",
        "workflow_run": "workflow_run",
        "schedule": "schedule",
        "release": "release",
        "issues": "issues",
        "issue_comment": "issue_comment",
        "create": "create",
        "delete": "delete",
        "fork": "fork",
        "page_build": "page_build",
        "deployment": "deployment",
        "deployment_status": "deployment_status",
        "check_run": "check_run",
        "check_suite": "check_suite",
        "label": "label",
        "milestone": "milestone",
        "project": "project",
        "project_card": "project_card",
        "project_column": "project_column",
        "public": "public",
        "registry_package": "registry_package",
        "status": "status",
        "watch": "watch",
    },
    order=None,
    present_null_when_empty=frozenset({"workflow_dispatch"}),
)


class PushTrigger(GhagenModel):
    """Configuration for push event triggers."""

    SPEC: ClassVar[ModelSpec] = PUSH_TRIGGER_SPEC

    branches: list[str] | None = None
    branches_ignore: list[str] | None = None
    tags: list[str] | None = None
    tags_ignore: list[str] | None = None
    paths: list[str] | None = None
    paths_ignore: list[str] | None = None


class PRTrigger(GhagenModel):
    """Configuration for pull_request event triggers."""

    SPEC: ClassVar[ModelSpec] = PR_TRIGGER_SPEC

    branches: list[str] | None = None
    branches_ignore: list[str] | None = None
    paths: list[str] | None = None
    paths_ignore: list[str] | None = None
    types: list[str] | None = None


class ScheduleTrigger(GhagenModel):
    """Configuration for schedule (cron) triggers."""

    SPEC: ClassVar[ModelSpec] = SCHEDULE_TRIGGER_SPEC

    cron: str


class WorkflowDispatchInput(GhagenModel):
    """An input parameter for workflow_dispatch triggers."""

    SPEC: ClassVar[ModelSpec] = WORKFLOW_DISPATCH_INPUT_SPEC

    description: str | None = None
    required: bool | None = None
    default: str | None = None
    # The canonical Snapshot's five-member enum for this event, matching the
    # TypeScript port's union. `workflow_call` has a *narrower* set (below);
    # widening either to the other would manufacture a divergence from the
    # schema.
    type: (
        Literal["boolean", "number", "string", "choice", "environment"]
        | Raw[str]
        | None
    ) = None
    options: list[str] | None = None


class WorkflowDispatchTrigger(GhagenModel):
    """Configuration for workflow_dispatch (manual) triggers."""

    SPEC: ClassVar[ModelSpec] = WORKFLOW_DISPATCH_SPEC

    inputs: dict[str, OrRaw[WorkflowDispatchInput]] | None = None


class WorkflowCallInput(GhagenModel):
    """An input parameter for workflow_call (reusable workflow) triggers."""

    SPEC: ClassVar[ModelSpec] = WORKFLOW_CALL_INPUT_SPEC

    description: str | None = None
    required: bool | None = None
    default: str | None = None
    # Three members, not five: the Snapshot gives `workflow_call` a narrower
    # enum than `workflow_dispatch`, and marks it `"required"` — both of which
    # the TypeScript port already declared.
    type: Literal["boolean", "number", "string"] | Raw[str]


class WorkflowCallOutput(GhagenModel):
    """An output for workflow_call triggers."""

    SPEC: ClassVar[ModelSpec] = WORKFLOW_CALL_OUTPUT_SPEC

    description: str | None = None
    value: str


class WorkflowCallSecret(GhagenModel):
    """A secret for workflow_call triggers."""

    SPEC: ClassVar[ModelSpec] = WORKFLOW_CALL_SECRET_SPEC

    description: str | None = None
    required: bool | None = None


class WorkflowCallTrigger(GhagenModel):
    """Configuration for workflow_call (reusable workflow) triggers."""

    SPEC: ClassVar[ModelSpec] = WORKFLOW_CALL_SPEC

    inputs: dict[str, OrRaw[WorkflowCallInput]] | None = None
    outputs: dict[str, OrRaw[WorkflowCallOutput]] | None = None
    secrets: dict[str, OrRaw[WorkflowCallSecret]] | None = None


class On(GhagenModel):
    """The `on:` trigger configuration for a workflow.

    Supports all GitHub Actions event types. Common ones have typed fields;
    use extras for less common events.
    """

    SPEC: ClassVar[ModelSpec] = ON_SPEC

    push: OrRaw[PushTrigger] | None = None
    pull_request: OrRaw[PRTrigger] | None = None
    pull_request_target: OrRaw[PRTrigger] | None = None
    workflow_dispatch: OrRaw[WorkflowDispatchTrigger | bool] | None = None
    workflow_call: OrRaw[WorkflowCallTrigger] | None = None
    workflow_run: OrRaw[dict[str, Any]] | None = None
    schedule: list[OrRaw[ScheduleTrigger]] | None = None
    release: OrRaw[dict[str, Any]] | None = None
    issues: OrRaw[dict[str, Any]] | None = None
    issue_comment: OrRaw[dict[str, Any]] | None = None
    create: OrRaw[dict[str, Any]] | None = None
    delete: OrRaw[dict[str, Any]] | None = None
    fork: OrRaw[dict[str, Any]] | None = None
    page_build: OrRaw[dict[str, Any]] | None = None
    deployment: OrRaw[dict[str, Any]] | None = None
    deployment_status: OrRaw[dict[str, Any]] | None = None
    check_run: OrRaw[dict[str, Any]] | None = None
    check_suite: OrRaw[dict[str, Any]] | None = None
    label: OrRaw[dict[str, Any]] | None = None
    milestone: OrRaw[dict[str, Any]] | None = None
    project: OrRaw[dict[str, Any]] | None = None
    project_card: OrRaw[dict[str, Any]] | None = None
    project_column: OrRaw[dict[str, Any]] | None = None
    public: OrRaw[dict[str, Any]] | None = None
    registry_package: OrRaw[dict[str, Any]] | None = None
    status: OrRaw[dict[str, Any]] | None = None
    watch: OrRaw[dict[str, Any]] | None = None
