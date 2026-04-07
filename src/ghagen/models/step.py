"""Step model for GitHub Actions workflow jobs."""

from __future__ import annotations

from typing import Any

from pydantic import Field
from ruamel.yaml.comments import CommentedMap

from ghagen._raw import Raw
from ghagen.emitter.key_order import STEP_KEY_ORDER
from ghagen.models._base import GhagenModel
from ghagen.models.common import ShellType


class Step(GhagenModel):
    """A single step within a GitHub Actions job.

    A step either runs a shell command (`run`) or uses an action (`uses`).
    """

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
    with_: dict[str, Any] | CommentedMap | None = Field(
        None,
        serialization_alias="with",
        description="Input parameters for the action "
        "specified by ``uses``.",
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
        description="Allow the job to continue when this step "
        "fails.",
    )
    timeout_minutes: int | None = Field(
        None,
        serialization_alias="timeout-minutes",
        description="Maximum minutes the step can run before "
        "being cancelled.",
    )

    def _get_key_order(self) -> list[str]:
        return STEP_KEY_ORDER


# Type alias for step lists that accept both typed and raw entries
StepList = list[Step | CommentedMap]
