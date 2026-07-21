"""Step model for GitHub Actions workflow jobs."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from ghagen._raw import Raw
from ghagen.models._base import GhagenModel, OrRaw
from ghagen.models.common import ShellType
from ghagen.models.spec import ModelSpec

STEP_SPEC = ModelSpec(
    yaml_keys={
        "id": "id",
        "name": "name",
        "if_": "if",
        "uses": "uses",
        "run": "run",
        "with_": "with",
        "env": "env",
        "shell": "shell",
        "working_directory": "working-directory",
        "continue_on_error": "continue-on-error",
        "timeout_minutes": "timeout-minutes",
    },
    order=(
        "id",
        "name",
        "if",
        "uses",
        "run",
        "with",
        "env",
        "shell",
        "working-directory",
        "continue-on-error",
        "timeout-minutes",
    ),
)


class Step(GhagenModel):
    """A single step within a GitHub Actions job.

    A step either runs a shell command (`run`) or uses an action (`uses`).
    """

    SPEC: ClassVar[ModelSpec] = STEP_SPEC

    id: str | None = None
    name: str | None = None
    if_: str | None = Field(
        None,
        serialization_alias="if",
        description="Conditional expression that must evaluate "
        "to true for this step to run.",
    )
    uses: str | None = None
    run: str | None = None
    with_: OrRaw[dict[str, Any]] | None = Field(
        None,
        serialization_alias="with",
        description="Input parameters for the action specified by ``uses``.",
    )
    env: dict[str, str] | None = None
    shell: ShellType | Raw[str] | None = None
    working_directory: str | None = Field(
        None,
        serialization_alias="working-directory",
        description="Working directory for ``run`` commands.",
    )
    continue_on_error: bool | str | None = Field(
        None,
        serialization_alias="continue-on-error",
        description="Allow the job to continue when this step fails.",
    )
    timeout_minutes: int | None = Field(
        None,
        serialization_alias="timeout-minutes",
        description="Maximum minutes the step can run before being cancelled.",
    )
