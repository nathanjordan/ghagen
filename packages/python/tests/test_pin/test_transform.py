"""Tests for ghagen.pin.transform — model-level SHA pinning."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ghagen.emitter import CommentNode, to_data
from ghagen.models._base import OrRaw
from ghagen.models.action import Action, CompositeRuns, DockerRuns
from ghagen.models.common import ShellType
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.trigger import On, PushTrigger
from ghagen.models.workflow import Workflow
from ghagen.pin.lockfile import Lockfile, PinEntry
from ghagen.pin.transform import PinError, PinTransform

SHA_CHECKOUT = "a" * 40
SHA_SETUP_PY = "b" * 40
SHA_REUSABLE = "c" * 40
SAMPLE_TIME = datetime(2026, 4, 9, tzinfo=UTC)


def _lockfile(**pins: str) -> Lockfile:
    """Build a lockfile from {uses: sha} pairs."""
    return Lockfile(
        pins={
            uses: PinEntry(sha=sha, resolved_at=SAMPLE_TIME)
            for uses, sha in pins.items()
        }
    )


def _jobs(result: Workflow | Action) -> dict[str, Job]:
    """The ``jobs`` map of a pinned *workflow*.

    ``PinTransform.__call__`` is annotated ``Workflow | Action -> Workflow |
    Action`` and ``Workflow.jobs`` is optional, so every ``result.jobs[...]``
    below needs two narrowings that say nothing about pinning. The composite
    action cases spell theirs out inline with ``isinstance``; these hold the
    same shape once, here.
    """
    assert isinstance(result, Workflow)
    assert result.jobs is not None
    return result.jobs


def _steps(result: Workflow | Action, job: str = "build") -> list[OrRaw[Step]]:
    """The steps of one job of a pinned workflow. ``Job.steps`` is optional."""
    steps = _jobs(result)[job].steps
    assert steps is not None
    return steps


class TestPinTransform:
    def test_pins_step_uses(self):
        lf = _lockfile(**{"actions/checkout@v4": SHA_CHECKOUT})
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                )
            },
        )
        transform = PinTransform(lf)
        result = transform(wf)
        step = _steps(result)[0]
        assert to_data(step, comments=True)["uses"] == CommentNode(
            f"actions/checkout@{SHA_CHECKOUT}", eol_comment="v4"
        )

    def test_pins_multiple_steps(self):
        lf = _lockfile(
            **{
                "actions/checkout@v4": SHA_CHECKOUT,
                "actions/setup-python@v5": SHA_SETUP_PY,
            }
        )
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[
                        Step(uses="actions/checkout@v4"),
                        Step(uses="actions/setup-python@v5"),
                    ],
                )
            },
        )
        transform = PinTransform(lf)
        result = transform(wf)
        steps = _steps(result)
        assert to_data(steps[0], comments=True)["uses"] == CommentNode(
            f"actions/checkout@{SHA_CHECKOUT}", eol_comment="v4"
        )
        assert to_data(steps[1], comments=True)["uses"] == CommentNode(
            f"actions/setup-python@{SHA_SETUP_PY}", eol_comment="v5"
        )

    def test_pins_job_uses(self):
        lf = _lockfile(**{"octo-org/repo/.github/workflows/ci.yml@v1": SHA_REUSABLE})
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "call": Job(
                    uses="octo-org/repo/.github/workflows/ci.yml@v1",
                )
            },
        )
        transform = PinTransform(lf)
        result = transform(wf)
        job = _jobs(result)["call"]
        assert to_data(job, comments=True)["uses"] == CommentNode(
            f"octo-org/repo/.github/workflows/ci.yml@{SHA_REUSABLE}", eol_comment="v1"
        )

    def test_skips_local_actions(self):
        lf = _lockfile()
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="./local-action")],
                )
            },
        )
        transform = PinTransform(lf)
        result = transform(wf)
        assert _steps(result)[0].uses == "./local-action"

    def test_skips_docker(self):
        lf = _lockfile()
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="docker://node:18")],
                )
            },
        )
        transform = PinTransform(lf)
        result = transform(wf)
        assert _steps(result)[0].uses == "docker://node:18"

    def test_missing_entry_raises(self):
        lf = _lockfile()
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                )
            },
        )
        transform = PinTransform(lf)
        with pytest.raises(PinError, match="No lockfile entry"):
            transform(wf)

    def test_missing_entry_names_the_real_command(self):
        """The remedy must name a command that exists.

        `ghagen pin` is not a command -- pinning is `ghagen deps pin`. The
        TypeScript peer already says so; this pins both ports to the same
        remedy text.
        """
        lf = _lockfile()
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                )
            },
        )
        transform = PinTransform(lf)
        with pytest.raises(PinError) as excinfo:
            transform(wf)
        assert "Run `ghagen deps pin` to resolve it." in str(excinfo.value)

    def test_skips_run_steps(self):
        lf = _lockfile()
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(run="echo hello")],
                )
            },
        )
        transform = PinTransform(lf)
        result = transform(wf)
        assert _steps(result)[0].run == "echo hello"

    def test_hand_pinned_sha_is_left_untouched(self):
        """A ref already written as a SHA is not pinnable — never raises PinError."""
        sha = "d" * 40
        lf = _lockfile()  # empty lockfile — a lookup would raise
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses=f"actions/checkout@{sha}")],
                )
            },
        )
        transform = PinTransform(lf)
        result = transform(wf)
        assert _steps(result)[0].uses == f"actions/checkout@{sha}"


class TestPinTransformAction:
    """PinTransform should pin Step.uses inside composite actions too."""

    def test_pins_composite_action_step_uses(self):
        lf = _lockfile(**{"actions/setup-python@v5": SHA_SETUP_PY})
        action = Action(
            name="greet",
            description="say hi",
            runs=CompositeRuns(
                steps=[
                    Step(
                        uses="actions/setup-python@v5",
                        with_={"python-version": "3.13"},
                    ),
                    Step(run="echo hi", shell=ShellType.BASH),
                ],
            ),
        )
        transform = PinTransform(lf)
        result = transform(action)
        assert isinstance(result, Action)
        assert isinstance(result.runs, CompositeRuns)
        step = result.runs.steps[0]
        assert isinstance(step, Step)
        assert to_data(step, comments=True)["uses"] == CommentNode(
            f"actions/setup-python@{SHA_SETUP_PY}", eol_comment="v5"
        )
        # Run step is untouched.
        run_step = result.runs.steps[1]
        assert isinstance(run_step, Step)
        assert run_step.run == "echo hi"

    def test_composite_action_missing_entry_raises(self):
        lf = _lockfile()
        action = Action(
            name="greet",
            description="say hi",
            runs=CompositeRuns(
                steps=[Step(uses="actions/setup-python@v5")],
            ),
        )
        transform = PinTransform(lf)
        with pytest.raises(PinError, match="No lockfile entry"):
            transform(action)

    def test_docker_action_is_passthrough(self):
        """DockerRuns has no pinnable refs; transform must leave it alone."""
        lf = _lockfile()
        action = Action(
            name="docker-action",
            description="runs in a container",
            runs=DockerRuns(image="docker://alpine:3"),
        )
        transform = PinTransform(lf)
        result = transform(action)
        assert isinstance(result, Action)
        assert isinstance(result.runs, DockerRuns)
        assert result.runs.image == "docker://alpine:3"
