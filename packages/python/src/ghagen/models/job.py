"""Job model for GitHub Actions workflows."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import Field

from ghagen._raw import Raw
from ghagen.models._base import GhagenModel, OrRaw
from ghagen.models.container import Container, Service
from ghagen.models.image_snapshot import ImageSnapshot
from ghagen.models.permissions import PermissionsValue
from ghagen.models.spec import ModelSpec
from ghagen.models.step import Step

MATRIX_SPEC = ModelSpec(
    yaml_keys={"include": "include", "exclude": "exclude"},
)

STRATEGY_SPEC = ModelSpec(
    yaml_keys={
        "matrix": "matrix",
        "fail_fast": "fail-fast",
        "max_parallel": "max-parallel",
    },
)

ENVIRONMENT_SPEC = ModelSpec(
    yaml_keys={"name": "name", "url": "url", "deployment": "deployment"},
)

CONCURRENCY_SPEC = ModelSpec(
    yaml_keys={
        "group": "group",
        "cancel_in_progress": "cancel-in-progress",
        "queue": "queue",
    },
)

DEFAULTS_SPEC = ModelSpec(yaml_keys={"run": "run"})

DEFAULTS_RUN_SPEC = ModelSpec(
    yaml_keys={"shell": "shell", "working_directory": "working-directory"},
)

JOB_SPEC = ModelSpec(
    yaml_keys={
        "name": "name",
        "runs_on": "runs-on",
        "needs": "needs",
        "if_": "if",
        "permissions": "permissions",
        "environment": "environment",
        "strategy": "strategy",
        "env": "env",
        "defaults": "defaults",
        "steps": "steps",
        "outputs": "outputs",
        "timeout_minutes": "timeout-minutes",
        "continue_on_error": "continue-on-error",
        "concurrency": "concurrency",
        "services": "services",
        "container": "container",
        "snapshot": "snapshot",
        "uses": "uses",
        "with_": "with",
        "secrets": "secrets",
    },
)


class Matrix(GhagenModel):
    """Strategy matrix configuration.

    Dynamic dimensions are set via extras since they are user-defined keys.

    Example::

        Matrix(
            extras={
                "python-version": ["3.11", "3.12", "3.13"],
                "os": ["ubuntu-latest", "macos-latest"],
            },
            include=[{"os": "ubuntu-latest", "experimental": True}],
            exclude=[{"os": "macos-latest", "python-version": "3.11"}],
        )
    """

    SPEC: ClassVar[ModelSpec] = MATRIX_SPEC

    include: list[dict[str, Any]] | None = None
    exclude: list[dict[str, Any]] | None = None


class Strategy(GhagenModel):
    """Job strategy configuration (matrix, fail-fast, max-parallel)."""

    SPEC: ClassVar[ModelSpec] = STRATEGY_SPEC

    matrix: OrRaw[Matrix] | None = None
    fail_fast: bool | None = None
    max_parallel: int | None = None


class Environment(GhagenModel):
    """Job environment configuration."""

    SPEC: ClassVar[ModelSpec] = ENVIRONMENT_SPEC

    name: str
    url: str | None = None
    # `False` lets the job use the environment's secrets and variables without
    # creating a deployment record; wait timers and reviewers still apply.
    deployment: bool | Raw[str] | None = None


class Concurrency(GhagenModel):
    """Concurrency configuration for workflows or jobs."""

    SPEC: ClassVar[ModelSpec] = CONCURRENCY_SPEC

    group: str
    cancel_in_progress: bool | None = None
    #: How pending runs queue within the group. Upstream enumerates
    #: ``single`` (default) and ``max``; ``Raw[str]`` is the hatch for a
    #: mode GitHub ships before ghagen models it. GitHub also forbids
    #: ``queue: max`` together with ``cancel-in-progress: true``, but the
    #: Snapshot states that only in prose -- it is not a schema rule, so it
    #: is not a ``constraints`` row either (those record rules the Snapshot
    #: enforces and the ports do not).
    queue: Literal["single", "max"] | Raw[str] | None = None


class Defaults(GhagenModel):
    """Default settings for all run steps in a job or workflow."""

    SPEC: ClassVar[ModelSpec] = DEFAULTS_SPEC

    run: OrRaw[DefaultsRun] | None = None


class DefaultsRun(GhagenModel):
    """Default run step settings."""

    SPEC: ClassVar[ModelSpec] = DEFAULTS_RUN_SPEC

    shell: str | Raw[str] | None = None
    working_directory: str | None = None


class Job(GhagenModel):
    """A job within a GitHub Actions workflow.

    Supports both regular jobs (with steps) and reusable workflow jobs
    (with uses).
    """

    SPEC: ClassVar[ModelSpec] = JOB_SPEC

    name: str | None = None
    runs_on: str | list[str] | Raw[str] | Raw[list[str]] | None = Field(
        default=None,
        description="Runner label(s) for this job.",
    )
    needs: str | list[str] | None = None
    if_: str | None = Field(
        default=None,
        description="Conditional expression that must evaluate "
        "to true for this job to run.",
    )
    permissions: PermissionsValue | None = None
    environment: OrRaw[str | Environment] | None = None
    strategy: OrRaw[Strategy] | None = None
    env: dict[str, str] | None = None
    defaults: OrRaw[Defaults] | None = None
    steps: list[OrRaw[Step]] | None = None
    outputs: dict[str, OrRaw[str]] | None = None
    timeout_minutes: int | None = Field(
        default=None,
        description="Maximum minutes the job can run before being cancelled.",
    )
    continue_on_error: bool | str | None = Field(
        default=None,
        description="Allow the workflow to continue when this job fails.",
    )
    concurrency: OrRaw[str | Concurrency] | None = None
    services: dict[str, OrRaw[Service | str]] | None = None
    container: OrRaw[Container | str] | None = None
    snapshot: OrRaw[str | ImageSnapshot] | None = Field(
        default=None,
        description="Custom runner-image generation request. A string is the "
        "image name (string syntax); an ImageSnapshot adds an optional version "
        "(mapping syntax).",
    )

    # Reusable workflow job fields
    uses: str | None = None
    with_: OrRaw[dict[str, Any]] | None = None
    secrets: OrRaw[dict[str, str] | str] | None = None
