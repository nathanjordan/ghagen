---
title: Step
description: Model for defining individual steps within a GitHub Actions job.
---

The `Step` class represents a single step within a GitHub Actions job. A step either runs a shell command (`run`) or uses an action (`uses`).

## Step

```python
from ghagen import Step

# Action step
checkout = Step(uses="actions/checkout@v4")

# Run step
test = Step(
    name="Run tests",
    run="pytest --verbose",
    env={"CI": "true"},
)

# Conditional step
deploy = Step(
    name="Deploy",
    if_="github.ref == 'refs/heads/main'",
    run="./deploy.sh",
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `id` | `str \| None` | `None` | Unique identifier for the step. Used to reference step outputs in expressions (e.g., `steps.<id>.outputs`). |
| `name` | `str \| None` | `None` | Display name for the step. |
| `if_` | `str \| None` | `None` | Conditional expression that must evaluate to true for this step to run. Serialized as `if`. |
| `uses` | `str \| None` | `None` | Action to use (e.g., `"actions/checkout@v4"`). Mutually exclusive with `run`. |
| `run` | `str \| None` | `None` | Shell command(s) to run. Multi-line strings are automatically dedented. Mutually exclusive with `uses`. |
| `with_` | `dict[str, Any] \| None` | `None` | Input parameters for the action specified by `uses`. Serialized as `with`. |
| `env` | `dict[str, str] \| None` | `None` | Environment variables for this step. |
| `shell` | `ShellType \| Raw[str] \| None` | `None` | Shell to use for `run` commands. See [ShellType](#shelltype). |
| `working_directory` | `str \| None` | `None` | Working directory for `run` commands. Serialized as `working-directory`. |
| `continue_on_error` | `bool \| str \| None` | `None` | Allow the job to continue when this step fails. Serialized as `continue-on-error`. |
| `timeout_minutes` | `int \| None` | `None` | Maximum minutes the step can run before being cancelled. Serialized as `timeout-minutes`. |

### Inherited parameters

All step instances also accept the base model parameters (`extras`, `comment`, `eol_comment`, `field_comments`, `field_eol_comments`, `post_process`). See [Workflow](/python/api/workflow/) for details.

## ShellType

An enum of supported shell types for `run` steps. Use `Raw[str]` for shell types not covered by this enum.

```python
from ghagen.models.common import ShellType

step = Step(run="echo hello", shell=ShellType.BASH)
```

| Value | String |
|-------|--------|
| `ShellType.BASH` | `"bash"` |
| `ShellType.PWSH` | `"pwsh"` |
| `ShellType.PYTHON` | `"python"` |
| `ShellType.SH` | `"sh"` |
| `ShellType.CMD` | `"cmd"` |

## StepList

A type alias for step lists that accept both typed and raw entries:

```python
StepList = list[Step | CommentedMap]
```

This is the type used by `Job.steps`, allowing you to mix typed `Step` objects with raw `CommentedMap` entries for full flexibility.
