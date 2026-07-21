"""Job model for GitHub Actions workflows."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from ghagen._raw import Raw
from ghagen.models._base import GhagenModel, OrRaw
from ghagen.models.container import Container, Service
from ghagen.models.image_snapshot import ImageSnapshot
from ghagen.models.permissions import Permissions
from ghagen.models.spec import ModelSpec
from ghagen.models.step import Step

MATRIX_SPEC = ModelSpec(
    yaml_keys={"include": "include", "exclude": "exclude"},
    order=("include", "exclude"),
)

STRATEGY_SPEC = ModelSpec(
    yaml_keys={
        "matrix": "matrix",
        "fail_fast": "fail-fast",
        "max_parallel": "max-parallel",
    },
    order=("matrix", "fail-fast", "max-parallel"),
)

ENVIRONMENT_SPEC = ModelSpec(
    yaml_keys={"name": "name", "url": "url"},
    order=("name", "url"),
)

CONCURRENCY_SPEC = ModelSpec(
    yaml_keys={"group": "group", "cancel_in_progress": "cancel-in-progress"},
    order=("group", "cancel-in-progress"),
)

DEFAULTS_SPEC = ModelSpec(yaml_keys={"run": "run"}, order=("run",))

DEFAULTS_RUN_SPEC = ModelSpec(
    yaml_keys={"shell": "shell", "working_directory": "working-directory"},
    order=("shell", "working-directory"),
)

JOB_OUTPUT_SPEC = ModelSpec(
    yaml_keys={"description": "description", "value": "value"},
    order=("description", "value"),
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
    order=(
        "name",
        "runs-on",
        "needs",
        "if",
        "permissions",
        "environment",
        "strategy",
        "env",
        "defaults",
        "steps",
        "outputs",
        "timeout-minutes",
        "continue-on-error",
        "concurrency",
        "services",
        "container",
        "snapshot",
        "uses",
        "with",
        "secrets",
    ),
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
    fail_fast: bool | None = Field(None, serialization_alias="fail-fast")
    max_parallel: int | None = Field(None, serialization_alias="max-parallel")


class Environment(GhagenModel):
    """Job environment configuration."""

    SPEC: ClassVar[ModelSpec] = ENVIRONMENT_SPEC

    name: str
    url: str | None = None


class Concurrency(GhagenModel):
    """Concurrency configuration for workflows or jobs."""

    SPEC: ClassVar[ModelSpec] = CONCURRENCY_SPEC

    group: str
    cancel_in_progress: bool | None = Field(
        None, serialization_alias="cancel-in-progress"
    )


class Defaults(GhagenModel):
    """Default settings for all run steps in a job or workflow."""

    SPEC: ClassVar[ModelSpec] = DEFAULTS_SPEC

    run: OrRaw[DefaultsRun] | None = None


class DefaultsRun(GhagenModel):
    """Default run step settings."""

    SPEC: ClassVar[ModelSpec] = DEFAULTS_RUN_SPEC

    shell: str | Raw[str] | None = None
    working_directory: str | None = Field(None, serialization_alias="working-directory")


class JobOutput(GhagenModel):
    """A job output definition."""

    SPEC: ClassVar[ModelSpec] = JOB_OUTPUT_SPEC

    description: str | None = None
    value: str


class Job(GhagenModel):
    """A job within a GitHub Actions workflow.

    Supports both regular jobs (with steps) and reusable workflow jobs
    (with uses).
    """

    SPEC: ClassVar[ModelSpec] = JOB_SPEC

    name: str | None = None
    runs_on: str | list[str] | Raw[str] | Raw[list[str]] | None = Field(
        None,
        serialization_alias="runs-on",
        description="Runner label(s) for this job.",
    )
    needs: str | list[str] | None = None
    if_: str | None = Field(
        None,
        serialization_alias="if",
        description="Conditional expression that must evaluate "
        "to true for this job to run.",
    )
    permissions: OrRaw[Permissions] | None = None
    environment: OrRaw[str | Environment] | None = None
    strategy: OrRaw[Strategy] | None = None
    env: dict[str, str] | None = None
    defaults: OrRaw[Defaults] | None = None
    steps: list[OrRaw[Step]] | None = None
    outputs: dict[str, OrRaw[str | JobOutput]] | None = None
    timeout_minutes: int | None = Field(
        None,
        serialization_alias="timeout-minutes",
        description="Maximum minutes the job can run before being cancelled.",
    )
    continue_on_error: bool | str | None = Field(
        None,
        serialization_alias="continue-on-error",
        description="Allow the workflow to continue when this job fails.",
    )
    concurrency: OrRaw[str | Concurrency] | None = None
    services: dict[str, OrRaw[Service | str]] | None = None
    container: OrRaw[Container | str] | None = None
    snapshot: OrRaw[str | ImageSnapshot] | None = Field(
        None,
        description="Custom runner-image generation request. A string is the "
        "image name (string syntax); an ImageSnapshot adds an optional version "
        "(mapping syntax).",
    )

    # Reusable workflow job fields
    uses: str | None = None
    with_: OrRaw[dict[str, Any]] | None = Field(None, serialization_alias="with")
    secrets: OrRaw[dict[str, str] | str] | None = None
