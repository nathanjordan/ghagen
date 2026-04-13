"""Job model for GitHub Actions workflows."""

from __future__ import annotations

from typing import Any

from pydantic import Field
from ruamel.yaml.comments import CommentedMap

from ghagen._raw import Raw
from ghagen.emitter.key_order import (
    CONCURRENCY_KEY_ORDER,
    DEFAULTS_KEY_ORDER,
    ENVIRONMENT_KEY_ORDER,
    JOB_KEY_ORDER,
    MATRIX_KEY_ORDER,
    STRATEGY_KEY_ORDER,
)
from ghagen.models._base import GhagenModel
from ghagen.models.container import Container, Service
from ghagen.models.permissions import Permissions
from ghagen.models.step import Step


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

    include: list[dict[str, Any]] | None = None
    exclude: list[dict[str, Any]] | None = None

    def _get_key_order(self) -> list[str]:
        # Dynamic dimension keys come before include/exclude
        return MATRIX_KEY_ORDER


class Strategy(GhagenModel):
    """Job strategy configuration (matrix, fail-fast, max-parallel)."""

    matrix: Matrix | CommentedMap | None = None
    fail_fast: bool | None = Field(None, serialization_alias="fail-fast")
    max_parallel: int | None = Field(None, serialization_alias="max-parallel")

    def _get_key_order(self) -> list[str]:
        return STRATEGY_KEY_ORDER


class Environment(GhagenModel):
    """Job environment configuration."""

    name: str
    url: str | None = None

    def _get_key_order(self) -> list[str]:
        return ENVIRONMENT_KEY_ORDER


class Concurrency(GhagenModel):
    """Concurrency configuration for workflows or jobs."""

    group: str
    cancel_in_progress: bool | None = Field(
        None, serialization_alias="cancel-in-progress"
    )

    def _get_key_order(self) -> list[str]:
        return CONCURRENCY_KEY_ORDER


class Defaults(GhagenModel):
    """Default settings for all run steps in a job or workflow."""

    run: DefaultsRun | CommentedMap | None = None

    def _get_key_order(self) -> list[str]:
        return DEFAULTS_KEY_ORDER


class DefaultsRun(GhagenModel):
    """Default run step settings."""

    shell: str | Raw[str] | None = None
    working_directory: str | None = Field(None, serialization_alias="working-directory")

    def _get_key_order(self) -> list[str]:
        return ["shell", "working-directory"]


class JobOutput(GhagenModel):
    """A job output definition."""

    description: str | None = None
    value: str

    def _get_key_order(self) -> list[str]:
        return ["description", "value"]


class Job(GhagenModel):
    """A job within a GitHub Actions workflow.

    Supports both regular jobs (with steps) and reusable workflow jobs
    (with uses).
    """

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
    permissions: Permissions | CommentedMap | None = None
    environment: str | Environment | CommentedMap | None = None
    strategy: Strategy | CommentedMap | None = None
    env: dict[str, str] | None = None
    defaults: Defaults | CommentedMap | None = None
    steps: list[Step | CommentedMap] | None = None
    outputs: dict[str, str | JobOutput | CommentedMap] | None = None
    timeout_minutes: int | None = Field(
        None,
        serialization_alias="timeout-minutes",
        description="Maximum minutes the job can run before "
        "being cancelled.",
    )
    continue_on_error: bool | str | None = Field(
        None,
        serialization_alias="continue-on-error",
        description="Allow the workflow to continue when this "
        "job fails.",
    )
    concurrency: str | Concurrency | CommentedMap | None = None
    services: dict[str, Service | str | CommentedMap] | None = None
    container: Container | str | CommentedMap | None = None

    # Reusable workflow job fields
    uses: str | None = None
    with_: dict[str, Any] | CommentedMap | None = Field(
        None, serialization_alias="with"
    )
    secrets: dict[str, str] | str | CommentedMap | None = None

    def _get_key_order(self) -> list[str]:
        return JOB_KEY_ORDER

    def to_commented_map(self) -> CommentedMap:
        """Override to handle environment string shorthand."""
        cm = super().to_commented_map()

        # Environment can be just a string (name only)
        if "environment" in cm and isinstance(cm["environment"], str):
            pass  # Leave as string

        return cm
