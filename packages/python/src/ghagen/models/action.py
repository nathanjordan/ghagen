"""Models for GitHub Actions action.yml files.

This module provides models for the three kinds of GitHub Actions
that use an ``action.yml`` metadata file:

- **Composite actions** — a bundle of steps (shell + ``uses``) that run
  in the runner's workspace, via :class:`CompositeRuns`.
- **Docker container actions** — a container image executed in place, via
  :class:`DockerRuns`.
- **JavaScript/Node actions** — a Node.js entrypoint script, via
  :class:`NodeRuns`.

All three share the same top-level :class:`Action` document with
``name``/``description``/``inputs``/``outputs``/``branding``/``runs`` keys.
Only the ``runs`` subsection varies.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field
from ruamel.yaml.comments import CommentedMap

from ghagen.emitter.key_order import (
    ACTION_INPUT_KEY_ORDER,
    ACTION_KEY_ORDER,
    ACTION_OUTPUT_KEY_ORDER,
    BRANDING_KEY_ORDER,
    COMPOSITE_RUNS_KEY_ORDER,
    DOCKER_RUNS_KEY_ORDER,
    NODE_RUNS_KEY_ORDER,
)
from ghagen.models._base import Document, GhagenModel
from ghagen.models.step import Step


class ActionInput(GhagenModel):
    """An input parameter for a GitHub Action.

    Distinct from :class:`ghagen.models.trigger.WorkflowCallInput`: action
    inputs do not carry a ``type`` field (all inputs are strings) but do
    support ``deprecationMessage``.
    """

    description: str | None = None
    required: bool | None = None
    default: str | None = None
    deprecation_message: str | None = Field(
        None,
        serialization_alias="deprecationMessage",
        description="Warning message shown when a deprecated input is used.",
    )

    def _get_key_order(self) -> list[str]:
        return ACTION_INPUT_KEY_ORDER


class ActionOutput(GhagenModel):
    """An output for a GitHub Action.

    For composite actions, ``value`` is required and typically
    references a step output (e.g. ``${{ steps.foo.outputs.bar }}``).
    For Docker and Node actions, ``value`` is omitted — the action
    itself writes outputs via ``$GITHUB_OUTPUT``.
    """

    description: str | None = None
    value: str | None = None

    def _get_key_order(self) -> list[str]:
        return ACTION_OUTPUT_KEY_ORDER


class Branding(GhagenModel):
    """Branding (icon + color) shown in the GitHub Marketplace."""

    icon: str | None = None
    color: str | None = None

    def _get_key_order(self) -> list[str]:
        return BRANDING_KEY_ORDER


class CompositeRuns(GhagenModel):
    """The ``runs:`` section for a composite action.

    Composite actions execute a sequence of :class:`~ghagen.models.step.Step`
    entries (``run`` commands or ``uses`` references) in the runner's
    workspace. ``run`` steps must set an explicit ``shell``.
    """

    using: Literal["composite"] = "composite"
    steps: list[Step | CommentedMap] = Field(default_factory=list)

    def model_post_init(self, _context: Any) -> None:
        # Ensure ``using`` is always emitted even when it takes the default.
        self.__pydantic_fields_set__.add("using")

    def _get_key_order(self) -> list[str]:
        return COMPOSITE_RUNS_KEY_ORDER


class DockerRuns(GhagenModel):
    """The ``runs:`` section for a Docker container action.

    ``image`` is either ``"Dockerfile"`` (to build in place) or a
    ``docker://registry/image:tag`` reference. ``pre-if`` / ``post-if``
    gate the execution of the optional pre/post entrypoints.
    """

    using: Literal["docker"] = "docker"
    image: str
    env: dict[str, str] | None = None
    args: list[str] | None = None
    pre_entrypoint: str | None = Field(None, serialization_alias="pre-entrypoint")
    pre_if: str | None = Field(None, serialization_alias="pre-if")
    entrypoint: str | None = None
    post_entrypoint: str | None = Field(None, serialization_alias="post-entrypoint")
    post_if: str | None = Field(None, serialization_alias="post-if")

    def model_post_init(self, _context: Any) -> None:
        self.__pydantic_fields_set__.add("using")

    def _get_key_order(self) -> list[str]:
        return DOCKER_RUNS_KEY_ORDER


class NodeRuns(GhagenModel):
    """The ``runs:`` section for a JavaScript/Node action.

    ``using`` is a Node runtime identifier such as ``"node20"``.
    ``main`` is the JS entrypoint; ``pre``/``post`` are optional
    setup/cleanup scripts with ``pre-if``/``post-if`` guards.
    """

    using: str
    main: str
    pre: str | None = None
    post: str | None = None
    pre_if: str | None = Field(None, serialization_alias="pre-if")
    post_if: str | None = Field(None, serialization_alias="post-if")

    def _get_key_order(self) -> list[str]:
        return NODE_RUNS_KEY_ORDER


class Action(Document):
    """A GitHub Action metadata definition (``action.yml``).

    This is the top-level model that maps to a complete ``action.yml``
    file. The ``runs`` field accepts a :class:`CompositeRuns`,
    :class:`DockerRuns`, or :class:`NodeRuns` instance (or a raw
    :class:`CommentedMap` escape hatch).

    Example::

        action = Action(
            name="My Action",
            description="Does a thing",
            branding=Branding(icon="check-circle", color="green"),
            inputs={
                "greeting": ActionInput(
                    description="Who to greet",
                    required=True,
                    default="world",
                ),
            },
            runs=CompositeRuns(
                steps=[
                    Step(
                        run="echo Hello, ${{ inputs.greeting }}",
                        shell="bash",
                    ),
                ],
            ),
        )
        print(action.to_yaml())
    """

    name: str
    description: str
    author: str | None = None
    branding: Branding | CommentedMap | None = None
    inputs: dict[str, ActionInput | CommentedMap] | None = None
    outputs: dict[str, ActionOutput | CommentedMap] | None = None
    runs: CompositeRuns | DockerRuns | NodeRuns | CommentedMap

    def _get_key_order(self) -> list[str]:
        return ACTION_KEY_ORDER


__all__ = [
    "Action",
    "ActionInput",
    "ActionOutput",
    "Branding",
    "CompositeRuns",
    "DockerRuns",
    "NodeRuns",
]
