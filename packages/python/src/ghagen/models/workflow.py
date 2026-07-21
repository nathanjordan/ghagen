"""Top-level Workflow model."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from ghagen._raw import Raw
from ghagen.emitter.key_order import WORKFLOW_KEY_ORDER
from ghagen.models._base import Document, OrRaw
from ghagen.models.job import Concurrency, Defaults, Job
from ghagen.models.permissions import Permissions
from ghagen.models.trigger import On


class Workflow(Document):
    """A GitHub Actions workflow definition.

    This is the top-level model that maps to a complete workflow YAML file.

    Example::

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
    """

    name: str | None = None
    run_name: str | None = Field(
        None,
        serialization_alias="run-name",
        description="Custom name for workflow runs, supports expressions.",
    )
    on: OrRaw[On | dict[str, Any]] | None = None
    permissions: (
        OrRaw[Permissions | Literal["read-all", "write-all"] | Raw[str]] | None
    ) = None
    env: dict[str, str] | None = None
    defaults: OrRaw[Defaults] | None = None
    concurrency: OrRaw[str | Concurrency] | None = None
    jobs: dict[str, OrRaw[Job]] = Field(default_factory=dict)

    def _get_key_order(self) -> list[str]:
        return WORKFLOW_KEY_ORDER
