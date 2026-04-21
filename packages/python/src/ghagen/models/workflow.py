"""Top-level Workflow model."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import Field
from ruamel.yaml.comments import CommentedMap

from ghagen._raw import Raw
from ghagen.emitter.header import (
    DEFAULT_HEADER,
    build_header_variables,
    format_header,
)
from ghagen.emitter.key_order import WORKFLOW_KEY_ORDER
from ghagen.emitter.yaml_writer import attach_comment, dump_yaml
from ghagen.models._base import GhagenModel
from ghagen.models.job import Concurrency, Defaults, Job
from ghagen.models.permissions import Permissions
from ghagen.models.trigger import On


class Workflow(GhagenModel):
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
    on: On | CommentedMap | dict[str, Any] | None = None
    permissions: (
        Permissions | Literal["read-all", "write-all"] | Raw[str] | CommentedMap | None
    ) = None
    env: dict[str, str] | None = None
    defaults: Defaults | CommentedMap | None = None
    concurrency: str | Concurrency | CommentedMap | None = None
    jobs: dict[str, Job | CommentedMap] = Field(default_factory=dict)

    def _get_key_order(self) -> list[str]:
        return WORKFLOW_KEY_ORDER

    def to_commented_map(self) -> CommentedMap:
        """Override to handle special on: serialization."""
        cm = super().to_commented_map()

        # Handle permissions string shorthand
        if "permissions" in cm and isinstance(cm["permissions"], str):
            pass  # Leave as string

        return cm

    def to_yaml(
        self,
        header: str | None = None,
        include_header: bool = True,
    ) -> str:
        """Generate the complete YAML string for this workflow.

        Args:
            header: Custom header comment template. May contain
                ``{variable}`` placeholders — see
                :data:`ghagen.emitter.header.HEADER_VARIABLES` for the
                full list. If ``None``, uses
                :data:`~ghagen.emitter.header.DEFAULT_HEADER`.
            include_header: Whether to include the header comment.

        Returns:
            The complete YAML string.
        """
        cm = self.to_commented_map()

        # Attach top-level comment if set
        if self.comment:
            attach_comment(cm, list(cm.keys())[0], comment=self.comment)

        if include_header:
            template = header if header is not None else DEFAULT_HEADER
            variables = build_header_variables(self._source_location)
            header_str = format_header(template, variables)
        else:
            header_str = None

        return dump_yaml(cm, header=header_str)

    def to_yaml_file(
        self,
        path: str | Path,
        header: str | None = None,
        include_header: bool = True,
    ) -> None:
        """Write the workflow YAML to a file.

        Args:
            path: File path to write to.
            header: Custom header comment template. See
                :meth:`to_yaml` for details.
            include_header: Whether to include the header comment.
        """
        content = self.to_yaml(header=header, include_header=include_header)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
