---
title: Job
description: Models for defining jobs within a GitHub Actions workflow, including strategy, matrix, environment, and output configuration.
---

The `Job` class represents a single job within a GitHub Actions workflow. Jobs can either run steps directly or call reusable workflows.

## Job

```python
from ghagen import Job, Step

job = Job(
    name="Test",
    runs_on="ubuntu-latest",
    steps=[
        Step(uses="actions/checkout@v4"),
        Step(name="Run tests", run="pytest"),
    ],
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str \| None` | `None` | Display name for the job. |
| `runs_on` | `str \| list[str] \| Raw[str] \| None` | `None` | Runner label(s) for this job (e.g., `"ubuntu-latest"`). Serialized as `runs-on`. |
| `needs` | `str \| list[str] \| None` | `None` | Job ID(s) that must complete before this job runs. |
| `if_` | `str \| None` | `None` | Conditional expression that must evaluate to true for this job to run. Serialized as `if`. |
| `permissions` | `Permissions \| None` | `None` | Token permissions for this job. See [Permissions](/python/api/permissions/). |
| `environment` | `str \| Environment \| None` | `None` | Deployment environment. Can be a string (name only) or an `Environment` object. |
| `strategy` | `Strategy \| None` | `None` | Matrix strategy configuration. See [Strategy](#strategy). |
| `env` | `dict[str, str] \| None` | `None` | Environment variables for all steps in this job. |
| `defaults` | `Defaults \| None` | `None` | Default settings for `run` steps. See [Workflow - Defaults](/python/api/workflow/#defaults). |
| `steps` | `list[Step] \| None` | `None` | Steps to run. See [Step](/python/api/step/). |
| `outputs` | `dict[str, str \| JobOutput] \| None` | `None` | Job outputs, accessible by downstream jobs. Values can be strings or `JobOutput` objects. |
| `timeout_minutes` | `int \| None` | `None` | Maximum minutes the job can run before being cancelled. Serialized as `timeout-minutes`. |
| `continue_on_error` | `bool \| str \| None` | `None` | Allow the workflow to continue when this job fails. Serialized as `continue-on-error`. |
| `concurrency` | `str \| Concurrency \| None` | `None` | Concurrency group for this job. See [Workflow - Concurrency](/python/api/workflow/#concurrency). |
| `services` | `dict[str, Service \| str] \| None` | `None` | Service containers for the job. Values can be `Service` objects or image strings. |
| `container` | `Container \| str \| None` | `None` | Container to run the job in. Can be a `Container` object or an image string. |

#### Reusable workflow fields

These fields are used when calling a reusable workflow instead of running steps directly.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `uses` | `str \| None` | `None` | Reusable workflow reference (e.g., `"org/repo/.github/workflows/ci.yml@main"`). |
| `with_` | `dict[str, Any] \| None` | `None` | Input parameters for the reusable workflow. Serialized as `with`. |
| `secrets` | `dict[str, str] \| str \| None` | `None` | Secrets to pass. Can be a dict or `"inherit"`. |

## Strategy

Job strategy configuration including matrix builds, fail-fast behavior, and parallelism limits.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `matrix` | `Matrix \| None` | `None` | Matrix configuration. See [Matrix](#matrix). |
| `fail_fast` | `bool \| None` | `None` | Whether to cancel all in-progress jobs if any matrix job fails. Serialized as `fail-fast`. |
| `max_parallel` | `int \| None` | `None` | Maximum number of matrix jobs to run in parallel. Serialized as `max-parallel`. |

## Matrix

Strategy matrix configuration. Dynamic dimensions are set via the `extras` parameter since they are user-defined keys.

```python
from ghagen.models.job import Matrix, Strategy

strategy = Strategy(
    matrix=Matrix(
        extras={
            "python-version": ["3.11", "3.12", "3.13"],
            "os": ["ubuntu-latest", "macos-latest"],
        },
        include=[{"os": "ubuntu-latest", "experimental": True}],
        exclude=[{"os": "macos-latest", "python-version": "3.11"}],
    ),
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include` | `list[dict[str, Any]] \| None` | `None` | Additional matrix combinations to include. |
| `exclude` | `list[dict[str, Any]] \| None` | `None` | Matrix combinations to exclude. |
| `extras` | `dict[str, Any]` | `{}` | Dynamic matrix dimensions (e.g., `{"python-version": ["3.11", "3.12"]}`). These are user-defined keys emitted at the top level of the matrix. Inherited from base model. |

## Environment

Job environment configuration for deployment environments.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | The environment name. |
| `url` | `str \| None` | `None` | The environment URL. |

## JobOutput

A job output definition, used when a downstream job needs to consume this job's outputs.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `description` | `str \| None` | `None` | Description of the output. |
| `value` | `str` | required | The output value, typically a step output expression. |

## Container

Container configuration for running a job inside a Docker container.

```python
from ghagen.models.container import Container

container = Container(
    image="node:20",
    env={"CI": "true"},
    ports=["8080:80"],
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image` | `str` | required | Docker image to use. |
| `credentials` | `dict[str, str] \| None` | `None` | Registry credentials (`username` and `password`). |
| `env` | `dict[str, str] \| None` | `None` | Environment variables for the container. |
| `ports` | `list[str \| int] \| None` | `None` | Ports to expose on the container. |
| `volumes` | `list[str] \| None` | `None` | Volumes to mount. |
| `options` | `str \| None` | `None` | Additional `docker create` options. |

## Service

Service container configuration. Has the same shape as `Container` and is used for sidecar services (databases, caches, etc.) that run alongside a job.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image` | `str` | required | Docker image to use. |
| `credentials` | `dict[str, str] \| None` | `None` | Registry credentials. |
| `env` | `dict[str, str] \| None` | `None` | Environment variables for the service. |
| `ports` | `list[str \| int] \| None` | `None` | Ports to expose. |
| `volumes` | `list[str] \| None` | `None` | Volumes to mount. |
| `options` | `str \| None` | `None` | Additional `docker create` options. |
