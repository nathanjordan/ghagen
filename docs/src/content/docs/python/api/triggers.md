---
title: Triggers
description: Models for configuring the `on` section of GitHub Actions workflows, including push, pull request, schedule, and dispatch triggers.
---

The trigger models define the `on:` section of a workflow, controlling when the workflow runs. The top-level `On` class contains fields for each event type.

## On

The top-level trigger configuration. Common event types have typed fields; less common events can use the `extras` parameter.

```python
from ghagen.models.trigger import On, PushTrigger, PRTrigger

on = On(
    push=PushTrigger(branches=["main"]),
    pull_request=PRTrigger(branches=["main"]),
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `push` | `PushTrigger \| None` | `None` | Push event configuration. |
| `pull_request` | `PRTrigger \| None` | `None` | Pull request event configuration. |
| `pull_request_target` | `PRTrigger \| None` | `None` | Pull request target event configuration. |
| `workflow_dispatch` | `WorkflowDispatchTrigger \| bool \| None` | `None` | Manual dispatch trigger. Set to `True` or `WorkflowDispatchTrigger()` for no inputs. |
| `workflow_call` | `WorkflowCallTrigger \| None` | `None` | Reusable workflow call trigger. |
| `workflow_run` | `dict[str, Any] \| None` | `None` | Workflow run event configuration. |
| `schedule` | `list[ScheduleTrigger] \| None` | `None` | Cron schedule triggers. |
| `release` | `dict[str, Any] \| None` | `None` | Release event configuration. |
| `issues` | `dict[str, Any] \| None` | `None` | Issues event configuration. |
| `issue_comment` | `dict[str, Any] \| None` | `None` | Issue comment event configuration. |
| `create` | `dict[str, Any] \| None` | `None` | Branch/tag creation event. |
| `delete` | `dict[str, Any] \| None` | `None` | Branch/tag deletion event. |
| `fork` | `dict[str, Any] \| None` | `None` | Fork event configuration. |
| `page_build` | `dict[str, Any] \| None` | `None` | GitHub Pages build event. |
| `deployment` | `dict[str, Any] \| None` | `None` | Deployment event configuration. |
| `deployment_status` | `dict[str, Any] \| None` | `None` | Deployment status event. |
| `check_run` | `dict[str, Any] \| None` | `None` | Check run event configuration. |
| `check_suite` | `dict[str, Any] \| None` | `None` | Check suite event configuration. |
| `label` | `dict[str, Any] \| None` | `None` | Label event configuration. |
| `milestone` | `dict[str, Any] \| None` | `None` | Milestone event configuration. |
| `project` | `dict[str, Any] \| None` | `None` | Project event configuration. |
| `project_card` | `dict[str, Any] \| None` | `None` | Project card event configuration. |
| `project_column` | `dict[str, Any] \| None` | `None` | Project column event configuration. |
| `public` | `dict[str, Any] \| None` | `None` | Repository visibility change event. |
| `registry_package` | `dict[str, Any] \| None` | `None` | Registry package event. |
| `status` | `dict[str, Any] \| None` | `None` | Commit status event. |
| `watch` | `dict[str, Any] \| None` | `None` | Watch/star event configuration. |

Events without a dedicated model accept a `dict[str, Any]` for full flexibility.

## PushTrigger

Configuration for `push` event triggers. Filters which pushes trigger the workflow.

```python
from ghagen.models.trigger import PushTrigger

push = PushTrigger(
    branches=["main", "release/*"],
    paths=["src/**"],
    paths_ignore=["docs/**"],
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `branches` | `list[str] \| None` | `None` | Branch filter patterns (supports glob). |
| `branches_ignore` | `list[str] \| None` | `None` | Branch exclusion patterns. Serialized as `branches-ignore`. |
| `tags` | `list[str] \| None` | `None` | Tag filter patterns. |
| `tags_ignore` | `list[str] \| None` | `None` | Tag exclusion patterns. Serialized as `tags-ignore`. |
| `paths` | `list[str] \| None` | `None` | Path filter patterns. Only pushes affecting these paths trigger the workflow. |
| `paths_ignore` | `list[str] \| None` | `None` | Path exclusion patterns. Serialized as `paths-ignore`. |

## PRTrigger

Configuration for `pull_request` and `pull_request_target` event triggers.

```python
from ghagen.models.trigger import PRTrigger

pr = PRTrigger(
    branches=["main"],
    types=["opened", "synchronize"],
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `branches` | `list[str] \| None` | `None` | Branch filter patterns (matches the PR's base branch). |
| `branches_ignore` | `list[str] \| None` | `None` | Branch exclusion patterns. Serialized as `branches-ignore`. |
| `paths` | `list[str] \| None` | `None` | Path filter patterns. |
| `paths_ignore` | `list[str] \| None` | `None` | Path exclusion patterns. Serialized as `paths-ignore`. |
| `types` | `list[str] \| None` | `None` | Activity types to filter on (e.g., `["opened", "synchronize", "reopened"]`). |

## ScheduleTrigger

Configuration for cron-based schedule triggers.

```python
from ghagen.models.trigger import ScheduleTrigger

schedule = ScheduleTrigger(cron="0 0 * * 1")  # Every Monday at midnight
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cron` | `str` | required | POSIX cron expression (e.g., `"0 0 * * *"` for daily at midnight). |

## WorkflowDispatchTrigger

Configuration for `workflow_dispatch` (manual) triggers. Allows defining input parameters that users provide when triggering the workflow manually.

```python
from ghagen.models.trigger import WorkflowDispatchTrigger, WorkflowDispatchInput

dispatch = WorkflowDispatchTrigger(
    inputs={
        "environment": WorkflowDispatchInput(
            description="Deployment target",
            required=True,
            type="choice",
            options=["staging", "production"],
        ),
    },
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `inputs` | `dict[str, WorkflowDispatchInput] \| None` | `None` | Input parameter definitions, keyed by input name. |

## WorkflowDispatchInput

An input parameter for `workflow_dispatch` triggers.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `description` | `str \| None` | `None` | Human-readable description of the input. |
| `required` | `bool \| None` | `None` | Whether the input is required. |
| `default` | `str \| None` | `None` | Default value for the input. |
| `type` | `str \| Raw[str] \| None` | `None` | Input type (e.g., `"string"`, `"boolean"`, `"choice"`, `"environment"`). |
| `options` | `list[str] \| None` | `None` | Available options when `type` is `"choice"`. |

## WorkflowCallTrigger

Configuration for `workflow_call` (reusable workflow) triggers. Defines the interface for a workflow that can be called by other workflows.

```python
from ghagen.models.trigger import (
    WorkflowCallTrigger,
    WorkflowCallInput,
    WorkflowCallOutput,
    WorkflowCallSecret,
)

call = WorkflowCallTrigger(
    inputs={
        "environment": WorkflowCallInput(
            description="Target environment",
            required=True,
            type="string",
        ),
    },
    outputs={
        "deploy-url": WorkflowCallOutput(
            description="Deployment URL",
            value="${{ jobs.deploy.outputs.url }}",
        ),
    },
    secrets={
        "DEPLOY_TOKEN": WorkflowCallSecret(
            description="Deployment token",
            required=True,
        ),
    },
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `inputs` | `dict[str, WorkflowCallInput] \| None` | `None` | Input parameter definitions. |
| `outputs` | `dict[str, WorkflowCallOutput] \| None` | `None` | Output definitions. |
| `secrets` | `dict[str, WorkflowCallSecret] \| None` | `None` | Secret definitions. |

## WorkflowCallInput

An input parameter for `workflow_call` triggers.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `description` | `str \| None` | `None` | Human-readable description of the input. |
| `required` | `bool \| None` | `None` | Whether the input is required. |
| `default` | `str \| None` | `None` | Default value. |
| `type` | `str \| Raw[str] \| None` | `None` | Input type (`"string"`, `"boolean"`, `"number"`). |

## WorkflowCallOutput

An output for `workflow_call` triggers.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `description` | `str \| None` | `None` | Human-readable description. |
| `value` | `str` | required | The output value, typically referencing a job output expression. |

## WorkflowCallSecret

A secret definition for `workflow_call` triggers.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `description` | `str \| None` | `None` | Human-readable description. |
| `required` | `bool \| None` | `None` | Whether the secret is required. |
