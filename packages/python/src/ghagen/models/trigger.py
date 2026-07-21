"""Trigger models for the `on:` section of GitHub Actions workflows."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field, model_validator

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

# ``On`` has no canonical trigger order: keys emit alphabetically (empty order).
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
)


class PushTrigger(GhagenModel):
    """Configuration for push event triggers."""

    SPEC: ClassVar[ModelSpec] = PUSH_TRIGGER_SPEC

    branches: list[str] | None = None
    branches_ignore: list[str] | None = Field(
        None, serialization_alias="branches-ignore"
    )
    tags: list[str] | None = None
    tags_ignore: list[str] | None = Field(None, serialization_alias="tags-ignore")
    paths: list[str] | None = None
    paths_ignore: list[str] | None = Field(None, serialization_alias="paths-ignore")


class PRTrigger(GhagenModel):
    """Configuration for pull_request event triggers."""

    SPEC: ClassVar[ModelSpec] = PR_TRIGGER_SPEC

    branches: list[str] | None = None
    branches_ignore: list[str] | None = Field(
        None, serialization_alias="branches-ignore"
    )
    paths: list[str] | None = None
    paths_ignore: list[str] | None = Field(None, serialization_alias="paths-ignore")
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
    type: str | Raw[str] | None = None
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
    type: str | Raw[str] | None = None


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
    pull_request: OrRaw[PRTrigger] | None = Field(
        None, serialization_alias="pull_request"
    )
    pull_request_target: OrRaw[PRTrigger] | None = Field(
        None, serialization_alias="pull_request_target"
    )
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

    @model_validator(mode="after")
    def _normalize_workflow_dispatch(self) -> On:
        """Render an empty ``workflow_dispatch`` as a present null key.

        ``workflow_dispatch:`` with no inputs must emit as a bare key (null),
        not ``workflow_dispatch: {}``. Pydantic's ``exclude_none`` would drop
        a plain ``None`` field, so an empty trigger is normalized to
        ``Raw(None)`` at construction — which the emitter renders as a present
        null value. A boolean ``workflow_dispatch`` is left untouched.
        """
        wd = self.workflow_dispatch
        is_empty_model = isinstance(wd, WorkflowDispatchTrigger) and wd.inputs is None
        is_empty_map = isinstance(wd, dict) and len(wd) == 0
        if is_empty_model or is_empty_map:
            object.__setattr__(self, "workflow_dispatch", Raw(None))
        return self
