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
)

PR_TRIGGER_SPEC = ModelSpec(
    yaml_keys={
        "branches": "branches",
        "branches_ignore": "branches-ignore",
        "tags": "tags",
        "tags_ignore": "tags-ignore",
        "paths": "paths",
        "paths_ignore": "paths-ignore",
        "types": "types",
    },
)

SCHEDULE_TRIGGER_SPEC = ModelSpec(
    yaml_keys={"cron": "cron", "timezone": "timezone"},
)

WORKFLOW_DISPATCH_INPUT_SPEC = ModelSpec(
    yaml_keys={
        "description": "description",
        "required": "required",
        "default": "default",
        "type": "type",
        "options": "options",
        # The schema spells this one in camelCase, unlike its five siblings.
        "deprecation_message": "deprecationMessage",
    },
)

WORKFLOW_DISPATCH_SPEC = ModelSpec(
    yaml_keys={"inputs": "inputs"},
)

WORKFLOW_CALL_INPUT_SPEC = ModelSpec(
    yaml_keys={
        "description": "description",
        "required": "required",
        "default": "default",
        "type": "type",
    },
)

WORKFLOW_CALL_OUTPUT_SPEC = ModelSpec(
    yaml_keys={"description": "description", "value": "value"},
)

WORKFLOW_CALL_SECRET_SPEC = ModelSpec(
    yaml_keys={"description": "description", "required": "required"},
)

WORKFLOW_CALL_SPEC = ModelSpec(
    yaml_keys={"inputs": "inputs", "outputs": "outputs", "secrets": "secrets"},
)

# ``On`` has no canonical trigger order: ``order="alphabetical"`` sorts every
# key at emit time (extras interleave).
_ON_YAML_KEYS = {
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
    "branch_protection_rule": "branch_protection_rule",
    "discussion": "discussion",
    "discussion_comment": "discussion_comment",
    "gollum": "gollum",
    "merge_group": "merge_group",
    "pull_request_review": "pull_request_review",
    "pull_request_review_comment": "pull_request_review_comment",
    "repository_dispatch": "repository_dispatch",
    "label": "label",
    "milestone": "milestone",
    "project": "project",
    "project_card": "project_card",
    "project_column": "project_column",
    "public": "public",
    "registry_package": "registry_package",
    "status": "status",
    "watch": "watch",
}

# Every event key, DERIVED from ``_ON_YAML_KEYS`` rather than listed: an empty
# map is never the right emission for an ``on:`` event. GitHub's documented
# spelling for "this event, no filters" is the bare key — ``create:`` for an
# event that takes no filters at all, and equally ``push:`` or
# ``workflow_call:`` for one whose filters were simply left empty. The
# allowlist used to name ``workflow_dispatch`` alone, which was not a decision
# about ``workflow_dispatch`` — it was the one key somebody needed.
#
# It is derived, not listed, so it cannot fall out of date: adding an event to
# ``_ON_YAML_KEYS`` adds it here in the same edit, and there is no second list
# for a guard test to compare against the first. (``schema/key-order.yml``
# already binds this key set across the two ports, so the derivation inherits
# that cross-port binding for free.) The peer of TypeScript's
# ``presentNullWhenEmpty: Object.values(ON_FIELD_MAP)``.
ON_SPEC = ModelSpec(
    yaml_keys=_ON_YAML_KEYS,
    order="alphabetical",
    present_null_when_empty=frozenset(_ON_YAML_KEYS.values()),
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
    tags: list[str] | None = None
    tags_ignore: list[str] | None = None
    paths: list[str] | None = None
    paths_ignore: list[str] | None = None
    types: list[str] | None = None


class ScheduleTrigger(GhagenModel):
    """Configuration for schedule (cron) triggers."""

    SPEC: ClassVar[ModelSpec] = SCHEDULE_TRIGGER_SPEC

    cron: str
    timezone: str | None = None


class WorkflowDispatchInput(GhagenModel):
    """An input parameter for workflow_dispatch triggers."""

    SPEC: ClassVar[ModelSpec] = WORKFLOW_DISPATCH_INPUT_SPEC

    description: str | None = None
    required: bool | None = None
    # `str | bool | int | float`, not `str`: the Snapshot leaves this property
    # untyped and constrains it from the `allOf`/`if`/`then` block instead —
    # `type: string`/`environment` -> a string default, `type: boolean` -> a
    # boolean one, `type: number` -> a number. The *unconditional* union is
    # therefore the union of those branches. `int` is spelled out alongside
    # `float` so an integer default emits as `3`, not `3.0`. The conditional
    # itself is not enforced (see the `constraints` section of
    # schema/conformance-gaps.yml); the union is bound to the Snapshot by
    # schema/conformance-inputs.yml.
    default: str | bool | int | float | None = None
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
    # Emitted as `deprecationMessage` — the Snapshot spells this key in
    # camelCase while its five siblings are lowercase.
    deprecation_message: str | None = None


class WorkflowDispatchTrigger(GhagenModel):
    """Configuration for workflow_dispatch (manual) triggers."""

    SPEC: ClassVar[ModelSpec] = WORKFLOW_DISPATCH_SPEC

    inputs: dict[str, OrRaw[WorkflowDispatchInput]] | None = None


class WorkflowCallInput(GhagenModel):
    """An input parameter for workflow_call (reusable workflow) triggers."""

    SPEC: ClassVar[ModelSpec] = WORKFLOW_CALL_INPUT_SPEC

    description: str | None = None
    required: bool | None = None
    # The Snapshot types this one directly — `type: [boolean, number, string]`
    # — rather than through the `workflow_dispatch` conditional. Same union
    # either way; `int` is spelled out alongside `float` so an integer default
    # emits as `3`, not `3.0`. Bound by schema/conformance-inputs.yml.
    default: str | bool | int | float | None = None
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
    branch_protection_rule: OrRaw[dict[str, Any]] | None = None
    discussion: OrRaw[dict[str, Any]] | None = None
    discussion_comment: OrRaw[dict[str, Any]] | None = None
    gollum: OrRaw[dict[str, Any]] | None = None
    merge_group: OrRaw[dict[str, Any]] | None = None
    pull_request_review: OrRaw[dict[str, Any]] | None = None
    pull_request_review_comment: OrRaw[dict[str, Any]] | None = None
    repository_dispatch: OrRaw[dict[str, Any]] | None = None
    label: OrRaw[dict[str, Any]] | None = None
    milestone: OrRaw[dict[str, Any]] | None = None
    project: OrRaw[dict[str, Any]] | None = None
    project_card: OrRaw[dict[str, Any]] | None = None
    project_column: OrRaw[dict[str, Any]] | None = None
    public: OrRaw[dict[str, Any]] | None = None
    registry_package: OrRaw[dict[str, Any]] | None = None
    status: OrRaw[dict[str, Any]] | None = None
    watch: OrRaw[dict[str, Any]] | None = None
