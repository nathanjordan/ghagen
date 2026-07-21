"""Trigger models for the `on:` section of GitHub Actions workflows."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from ghagen._raw import Raw
from ghagen.emitter.key_order import (
    TRIGGER_KEY_ORDER,
    WORKFLOW_CALL_KEY_ORDER,
    WORKFLOW_DISPATCH_INPUT_KEY_ORDER,
    WORKFLOW_DISPATCH_KEY_ORDER,
)
from ghagen.models._base import GhagenModel, OrRaw


class PushTrigger(GhagenModel):
    """Configuration for push event triggers."""

    branches: list[str] | None = None
    branches_ignore: list[str] | None = Field(
        None, serialization_alias="branches-ignore"
    )
    tags: list[str] | None = None
    tags_ignore: list[str] | None = Field(None, serialization_alias="tags-ignore")
    paths: list[str] | None = None
    paths_ignore: list[str] | None = Field(None, serialization_alias="paths-ignore")

    def _get_key_order(self) -> list[str]:
        return TRIGGER_KEY_ORDER


class PRTrigger(GhagenModel):
    """Configuration for pull_request event triggers."""

    branches: list[str] | None = None
    branches_ignore: list[str] | None = Field(
        None, serialization_alias="branches-ignore"
    )
    paths: list[str] | None = None
    paths_ignore: list[str] | None = Field(None, serialization_alias="paths-ignore")
    types: list[str] | None = None

    def _get_key_order(self) -> list[str]:
        return TRIGGER_KEY_ORDER


class ScheduleTrigger(GhagenModel):
    """Configuration for schedule (cron) triggers."""

    cron: str

    def _get_key_order(self) -> list[str]:
        return ["cron"]


class WorkflowDispatchInput(GhagenModel):
    """An input parameter for workflow_dispatch triggers."""

    description: str | None = None
    required: bool | None = None
    default: str | None = None
    type: str | Raw[str] | None = None
    options: list[str] | None = None

    def _get_key_order(self) -> list[str]:
        return WORKFLOW_DISPATCH_INPUT_KEY_ORDER


class WorkflowDispatchTrigger(GhagenModel):
    """Configuration for workflow_dispatch (manual) triggers."""

    inputs: dict[str, OrRaw[WorkflowDispatchInput]] | None = None

    def _get_key_order(self) -> list[str]:
        return WORKFLOW_DISPATCH_KEY_ORDER


class WorkflowCallInput(GhagenModel):
    """An input parameter for workflow_call (reusable workflow) triggers."""

    description: str | None = None
    required: bool | None = None
    default: str | None = None
    type: str | Raw[str] | None = None

    def _get_key_order(self) -> list[str]:
        return ["description", "required", "default", "type"]


class WorkflowCallOutput(GhagenModel):
    """An output for workflow_call triggers."""

    description: str | None = None
    value: str

    def _get_key_order(self) -> list[str]:
        return ["description", "value"]


class WorkflowCallSecret(GhagenModel):
    """A secret for workflow_call triggers."""

    description: str | None = None
    required: bool | None = None

    def _get_key_order(self) -> list[str]:
        return ["description", "required"]


class WorkflowCallTrigger(GhagenModel):
    """Configuration for workflow_call (reusable workflow) triggers."""

    inputs: dict[str, OrRaw[WorkflowCallInput]] | None = None
    outputs: dict[str, OrRaw[WorkflowCallOutput]] | None = None
    secrets: dict[str, OrRaw[WorkflowCallSecret]] | None = None

    def _get_key_order(self) -> list[str]:
        return WORKFLOW_CALL_KEY_ORDER


class On(GhagenModel):
    """The `on:` trigger configuration for a workflow.

    Supports all GitHub Actions event types. Common ones have typed fields;
    use extras for less common events.
    """

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

    def _get_key_order(self) -> list[str]:
        # No strong canonical order for trigger types; emit in declaration order
        return []

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
