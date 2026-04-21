"""Tests for ghagen.pin.transform — model-level SHA pinning."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ghagen._commented import is_commented
from ghagen.models.action import Action, CompositeRuns, DockerRuns
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.trigger import On, PushTrigger
from ghagen.models.workflow import Workflow
from ghagen.pin.lockfile import Lockfile, PinEntry
from ghagen.pin.transform import PinError, PinTransform
from ghagen.transforms import SynthContext

SHA_CHECKOUT = "a" * 40
SHA_SETUP_PY = "b" * 40
SHA_REUSABLE = "c" * 40
SAMPLE_TIME = datetime(2026, 4, 9, tzinfo=UTC)


def _ctx() -> SynthContext:
    return SynthContext(workflow_key="ci", item_type="workflow", root=Path("."))


def _action_ctx() -> SynthContext:
    return SynthContext(workflow_key="action", item_type="action", root=Path("."))


def _lockfile(**pins: str) -> Lockfile:
    """Build a lockfile from {uses: sha} pairs."""
    return Lockfile(
        pins={
            uses: PinEntry(sha=sha, resolved_at=SAMPLE_TIME)
            for uses, sha in pins.items()
        }
    )


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
        result = transform(wf, _ctx())
        step = result.jobs["build"].steps[0]
        assert is_commented(step.uses)
        assert step.uses.value == f"actions/checkout@{SHA_CHECKOUT}"
        assert step.uses.eol_comment == "v4"

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
        result = transform(wf, _ctx())
        steps = result.jobs["build"].steps
        assert is_commented(steps[0].uses)
        assert steps[0].uses.value == f"actions/checkout@{SHA_CHECKOUT}"
        assert is_commented(steps[1].uses)
        assert steps[1].uses.value == f"actions/setup-python@{SHA_SETUP_PY}"

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
        result = transform(wf, _ctx())
        job = result.jobs["call"]
        assert is_commented(job.uses)
        assert (
            job.uses.value
            == f"octo-org/repo/.github/workflows/ci.yml@{SHA_REUSABLE}"
        )
        assert job.uses.eol_comment == "v1"

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
        result = transform(wf, _ctx())
        assert result.jobs["build"].steps[0].uses == "./local-action"

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
        result = transform(wf, _ctx())
        assert result.jobs["build"].steps[0].uses == "docker://node:18"

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
            transform(wf, _ctx())

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
        result = transform(wf, _ctx())
        assert result.jobs["build"].steps[0].run == "echo hello"


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
                    Step(run="echo hi", shell="bash"),
                ],
            ),
        )
        transform = PinTransform(lf)
        result = transform(action, _action_ctx())
        assert isinstance(result, Action)
        assert isinstance(result.runs, CompositeRuns)
        step = result.runs.steps[0]
        assert isinstance(step, Step)
        assert is_commented(step.uses)
        assert step.uses.value == f"actions/setup-python@{SHA_SETUP_PY}"
        assert step.uses.eol_comment == "v5"
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
            transform(action, _action_ctx())

    def test_docker_action_is_passthrough(self):
        """DockerRuns has no pinnable refs; transform must leave it alone."""
        lf = _lockfile()
        action = Action(
            name="docker-action",
            description="runs in a container",
            runs=DockerRuns(image="docker://alpine:3"),
        )
        transform = PinTransform(lf)
        result = transform(action, _action_ctx())
        assert isinstance(result, Action)
        assert isinstance(result.runs, DockerRuns)
        assert result.runs.image == "docker://alpine:3"
