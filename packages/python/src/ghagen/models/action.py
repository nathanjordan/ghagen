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

from typing import Any, ClassVar, Literal

from pydantic import Field

from ghagen.models._base import Document, GhagenModel, OrRaw
from ghagen.models.spec import ModelSpec
from ghagen.models.step import Step

ACTION_INPUT_SPEC = ModelSpec(
    yaml_keys={
        "description": "description",
        "required": "required",
        "default": "default",
        "deprecation_message": "deprecationMessage",
    },
    order=("description", "required", "default", "deprecationMessage"),
)

ACTION_OUTPUT_SPEC = ModelSpec(
    yaml_keys={"description": "description", "value": "value"},
    order=("description", "value"),
)

BRANDING_SPEC = ModelSpec(
    yaml_keys={"icon": "icon", "color": "color"},
    order=("icon", "color"),
)

COMPOSITE_RUNS_SPEC = ModelSpec(
    yaml_keys={"using": "using", "steps": "steps"},
    order=("using", "steps"),
)

DOCKER_RUNS_SPEC = ModelSpec(
    yaml_keys={
        "using": "using",
        "image": "image",
        "env": "env",
        "args": "args",
        "pre_entrypoint": "pre-entrypoint",
        "pre_if": "pre-if",
        "entrypoint": "entrypoint",
        "post_entrypoint": "post-entrypoint",
        "post_if": "post-if",
    },
    order=(
        "using",
        "image",
        "env",
        "args",
        "pre-entrypoint",
        "pre-if",
        "entrypoint",
        "post-entrypoint",
        "post-if",
    ),
)

NODE_RUNS_SPEC = ModelSpec(
    yaml_keys={
        "using": "using",
        "main": "main",
        "pre": "pre",
        "post": "post",
        "pre_if": "pre-if",
        "post_if": "post-if",
    },
    order=("using", "main", "pre", "post", "pre-if", "post-if"),
)

ACTION_SPEC = ModelSpec(
    yaml_keys={
        "name": "name",
        "description": "description",
        "author": "author",
        "branding": "branding",
        "inputs": "inputs",
        "outputs": "outputs",
        "runs": "runs",
    },
    order=("name", "description", "author", "branding", "inputs", "outputs", "runs"),
)


class ActionInput(GhagenModel):
    """An input parameter for a GitHub Action.

    Distinct from :class:`ghagen.models.trigger.WorkflowCallInput`: action
    inputs do not carry a ``type`` field (all inputs are strings) but do
    support ``deprecationMessage``.
    """

    SPEC: ClassVar[ModelSpec] = ACTION_INPUT_SPEC

    description: str | None = None
    required: bool | None = None
    default: str | None = None
    deprecation_message: str | None = Field(
        None,
        serialization_alias="deprecationMessage",
        description="Warning message shown when a deprecated input is used.",
    )


class ActionOutput(GhagenModel):
    """An output for a GitHub Action.

    For composite actions, ``value`` is required and typically
    references a step output (e.g. ``${{ steps.foo.outputs.bar }}``).
    For Docker and Node actions, ``value`` is omitted — the action
    itself writes outputs via ``$GITHUB_OUTPUT``.
    """

    SPEC: ClassVar[ModelSpec] = ACTION_OUTPUT_SPEC

    description: str | None = None
    value: str | None = None


class Branding(GhagenModel):
    """Branding (icon + color) shown in the GitHub Marketplace."""

    SPEC: ClassVar[ModelSpec] = BRANDING_SPEC

    icon: str | None = None
    color: str | None = None


class CompositeRuns(GhagenModel):
    """The ``runs:`` section for a composite action.

    Composite actions execute a sequence of :class:`~ghagen.models.step.Step`
    entries (``run`` commands or ``uses`` references) in the runner's
    workspace. ``run`` steps must set an explicit ``shell``.
    """

    SPEC: ClassVar[ModelSpec] = COMPOSITE_RUNS_SPEC

    using: Literal["composite"] = "composite"
    steps: list[OrRaw[Step]] = Field(default_factory=list)

    def model_post_init(self, _context: Any) -> None:
        # Ensure ``using`` is always emitted even when it takes the default.
        self.__pydantic_fields_set__.add("using")


class DockerRuns(GhagenModel):
    """The ``runs:`` section for a Docker container action.

    ``image`` is either ``"Dockerfile"`` (to build in place) or a
    ``docker://registry/image:tag`` reference. ``pre-if`` / ``post-if``
    gate the execution of the optional pre/post entrypoints.
    """

    SPEC: ClassVar[ModelSpec] = DOCKER_RUNS_SPEC

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


class NodeRuns(GhagenModel):
    """The ``runs:`` section for a JavaScript/Node action.

    ``using`` is a Node runtime identifier such as ``"node20"``.
    ``main`` is the JS entrypoint; ``pre``/``post`` are optional
    setup/cleanup scripts with ``pre-if``/``post-if`` guards.
    """

    SPEC: ClassVar[ModelSpec] = NODE_RUNS_SPEC

    using: str
    main: str
    pre: str | None = None
    post: str | None = None
    pre_if: str | None = Field(None, serialization_alias="pre-if")
    post_if: str | None = Field(None, serialization_alias="post-if")


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

    SPEC: ClassVar[ModelSpec] = ACTION_SPEC

    name: str
    description: str
    author: str | None = None
    branding: OrRaw[Branding] | None = None
    inputs: dict[str, OrRaw[ActionInput]] | None = None
    outputs: dict[str, OrRaw[ActionOutput]] | None = None
    runs: OrRaw[CompositeRuns | DockerRuns | NodeRuns]


__all__ = [
    "Action",
    "ActionInput",
    "ActionOutput",
    "Branding",
    "CompositeRuns",
    "DockerRuns",
    "NodeRuns",
]
