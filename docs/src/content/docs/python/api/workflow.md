---
title: Workflow
description: Top-level model representing a complete GitHub Actions workflow YAML file.
---

The `Workflow` class is the top-level model that maps to a complete GitHub Actions workflow YAML file. It contains the workflow name, triggers, permissions, environment variables, defaults, concurrency settings, and jobs.

## Workflow

```python
from ghagen import Workflow, On, Job, Step
from ghagen.models.trigger import PushTrigger

workflow = Workflow(
    name="CI",
    on=On(push=PushTrigger(branches=["main"])),
    jobs={
        "test": Job(
            runs_on="ubuntu-latest",
            steps=[Step(uses="actions/checkout@v4")],
        ),
    },
)
print(workflow.to_yaml())
```

### Parameters

| Parameter     | Type                                                                  | Default | Description                                                                                                          |
| ------------- | --------------------------------------------------------------------- | ------- | -------------------------------------------------------------------------------------------------------------------- |
| `name`        | `str \| None`                                                         | `None`  | The display name of the workflow.                                                                                    |
| `run_name`    | `str \| None`                                                         | `None`  | Custom name for workflow runs. Supports GitHub Actions expressions. Serialized as `run-name`.                        |
| `on`          | `On \| dict \| None`                                                  | `None`  | Trigger configuration for the workflow. See [Triggers](/python/api/triggers/).                                       |
| `permissions` | `Permissions \| Literal["read-all", "write-all"] \| Raw[str] \| None` | `None`  | Token permissions. Can be a `Permissions` object or a string shorthand. See [Permissions](/python/api/permissions/). |
| `env`         | `dict[str, str] \| None`                                              | `None`  | Environment variables available to all jobs in the workflow.                                                         |
| `defaults`    | `Defaults \| None`                                                    | `None`  | Default settings for all `run` steps. See [Defaults](#defaults).                                                     |
| `concurrency` | `str \| Concurrency \| None`                                          | `None`  | Concurrency group configuration. Can be a string (group name) or a `Concurrency` object.                             |
| `jobs`        | `dict[str, Job]`                                                      | `{}`    | Map of job IDs to job definitions. See [Job](/python/api/job/).                                                      |

All models also accept these inherited parameters from the base class:

| Parameter            | Type               | Default | Description                                                                                |
| -------------------- | ------------------ | ------- | ------------------------------------------------------------------------------------------ |
| `extras`             | `dict[str, Any]`   | `{}`    | Arbitrary key/value pairs merged into YAML output for fields not covered by the typed API. |
| `post_process`       | `Callable \| None` | `None`  | Callback to modify the `CommentedMap` before emission.                                     |
| `comment`            | `str \| None`      | `None`  | Block comment emitted above this node in the YAML output.                                  |
| `eol_comment`        | `str \| None`      | `None`  | End-of-line comment for this node.                                                         |
| `field_comments`     | `dict[str, str]`   | `{}`    | Per-field block comments, keyed by YAML alias.                                             |
| `field_eol_comments` | `dict[str, str]`   | `{}`    | Per-field end-of-line comments, keyed by YAML alias.                                       |

### Methods

#### `to_yaml(header=None, include_header=True) -> str`

Generate the complete YAML string for this workflow.

| Argument         | Type          | Default | Description                                                                                                       |
| ---------------- | ------------- | ------- | ----------------------------------------------------------------------------------------------------------------- |
| `header`         | `str \| None` | `None`  | Custom header comment template. May contain `{variable}` placeholders. If `None`, uses the default ghagen header. |
| `include_header` | `bool`        | `True`  | Whether to include the header comment at the top of the file.                                                     |

Returns the complete YAML string.

#### `to_yaml_file(path, header=None, include_header=True) -> None`

Write the workflow YAML to a file. Creates parent directories if they don't exist.

| Argument         | Type          | Default  | Description                                                  |
| ---------------- | ------------- | -------- | ------------------------------------------------------------ |
| `path`           | `str \| Path` | required | File path to write to.                                       |
| `header`         | `str \| None` | `None`   | Custom header comment template. See `to_yaml()` for details. |
| `include_header` | `bool`        | `True`   | Whether to include the header comment.                       |

#### `to_commented_map() -> CommentedMap`

Serialize this model to a `ruamel.yaml.comments.CommentedMap` with canonical key ordering, merged extras, and attached comments. This is the lower-level method used by `to_yaml()`.

## Defaults

Default settings for all `run` steps in a job or workflow.

### Parameters

| Parameter | Type                  | Default | Description                |
| --------- | --------------------- | ------- | -------------------------- |
| `run`     | `DefaultsRun \| None` | `None`  | Default run step settings. |

## DefaultsRun

Default shell and working directory for `run` steps.

### Parameters

| Parameter           | Type                      | Default | Description                                                   |
| ------------------- | ------------------------- | ------- | ------------------------------------------------------------- |
| `shell`             | `str \| Raw[str] \| None` | `None`  | Default shell for run steps (e.g., `"bash"`, `"pwsh"`).       |
| `working_directory` | `str \| None`             | `None`  | Default working directory. Serialized as `working-directory`. |

## Concurrency

Concurrency configuration for workflows or jobs. Prevents concurrent runs in the same group.

### Parameters

| Parameter            | Type           | Default  | Description                                                                                      |
| -------------------- | -------------- | -------- | ------------------------------------------------------------------------------------------------ |
| `group`              | `str`          | required | Concurrency group name. Supports expressions.                                                    |
| `cancel_in_progress` | `bool \| None` | `None`   | Whether to cancel in-progress runs when a new run is queued. Serialized as `cancel-in-progress`. |
