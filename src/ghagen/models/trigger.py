"""Trigger models for the `on:` section of GitHub Actions workflows."""

from __future__ import annotations

from typing import Any

from pydantic import Field
from ruamel.yaml.comments import CommentedMap

from ghagen._raw import Raw
from ghagen.emitter.key_order import (
    TRIGGER_KEY_ORDER,
    WORKFLOW_CALL_KEY_ORDER,
    WORKFLOW_DISPATCH_INPUT_KEY_ORDER,
    WORKFLOW_DISPATCH_KEY_ORDER,
)
from ghagen.models._base import GhagenModel


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

    inputs: dict[str, WorkflowDispatchInput | CommentedMap] | None = None

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

    inputs: dict[str, WorkflowCallInput | CommentedMap] | None = None
    outputs: dict[str, WorkflowCallOutput | CommentedMap] | None = None
    secrets: dict[str, WorkflowCallSecret | CommentedMap] | None = None

    def _get_key_order(self) -> list[str]:
        return WORKFLOW_CALL_KEY_ORDER


class On(GhagenModel):
    """The `on:` trigger configuration for a workflow.

    Supports all GitHub Actions event types. Common ones have typed fields;
    use extras for less common events.
    """

    push: PushTrigger | CommentedMap | None = None
    pull_request: PRTrigger | CommentedMap | None = Field(
        None, serialization_alias="pull_request"
    )
    pull_request_target: PRTrigger | CommentedMap | None = Field(
        None, serialization_alias="pull_request_target"
    )
    workflow_dispatch: WorkflowDispatchTrigger | CommentedMap | bool | None = None
    workflow_call: WorkflowCallTrigger | CommentedMap | None = None
    workflow_run: dict[str, Any] | CommentedMap | None = None
    schedule: list[ScheduleTrigger | CommentedMap] | None = None
    release: dict[str, Any] | CommentedMap | None = None
    issues: dict[str, Any] | CommentedMap | None = None
    issue_comment: dict[str, Any] | CommentedMap | None = None
    create: dict[str, Any] | CommentedMap | None = None
    delete: dict[str, Any] | CommentedMap | None = None
    fork: dict[str, Any] | CommentedMap | None = None
    page_build: dict[str, Any] | CommentedMap | None = None
    deployment: dict[str, Any] | CommentedMap | None = None
    deployment_status: dict[str, Any] | CommentedMap | None = None
    check_run: dict[str, Any] | CommentedMap | None = None
    check_suite: dict[str, Any] | CommentedMap | None = None
    label: dict[str, Any] | CommentedMap | None = None
    milestone: dict[str, Any] | CommentedMap | None = None
    project: dict[str, Any] | CommentedMap | None = None
    project_card: dict[str, Any] | CommentedMap | None = None
    project_column: dict[str, Any] | CommentedMap | None = None
    public: dict[str, Any] | CommentedMap | None = None
    registry_package: dict[str, Any] | CommentedMap | None = None
    status: dict[str, Any] | CommentedMap | None = None
    watch: dict[str, Any] | CommentedMap | None = None

    def _get_key_order(self) -> list[str]:
        # No strong canonical order for trigger types; emit in declaration order
        return []

    def to_commented_map(self) -> CommentedMap:
        """Override to handle schedule as a list of cron entries."""
        cm = super().to_commented_map()

        # Schedule needs special handling: list of {cron: "..."} dicts
        if "schedule" in cm and isinstance(cm["schedule"], list):
            from ruamel.yaml.comments import CommentedSeq

            seq = CommentedSeq()
            for item in cm["schedule"]:
                if isinstance(item, CommentedMap):
                    seq.append(item)
                elif isinstance(item, dict):
                    entry = CommentedMap()
                    for k, v in item.items():
                        entry[k] = v
                    seq.append(entry)
                else:
                    seq.append(item)
            cm["schedule"] = seq

        # workflow_dispatch with no inputs should be null (renders as just the key)
        if "workflow_dispatch" in cm:
            val = cm["workflow_dispatch"]
            if val is True:
                pass  # Leave as boolean
            elif isinstance(val, (dict, CommentedMap)) and len(val) == 0:
                cm["workflow_dispatch"] = None

        return cm
