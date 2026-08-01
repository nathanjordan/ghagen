"""Tests for the generic model traversal primitives ``walk()`` / ``children()``."""

from ghagen import Action, Job, On, PushTrigger, Step, Workflow
from ghagen.models.action import CompositeRuns


def test_children_yields_direct_nested_models():
    job = Job(
        runs_on="ubuntu-latest",
        steps=[Step(uses="actions/checkout@v4"), Step(run="pytest")],
    )
    models = list(job.children())
    assert all(isinstance(m, Step) for m in models)
    assert len(models) == 2


def test_children_skips_scalars_and_none():
    step = Step(name="only scalars", run="echo hi")
    assert list(step.children()) == []


def test_walk_yields_self_first():
    wf = Workflow(name="CI", on=On(push=PushTrigger(branches=["main"])))
    assert next(iter(wf.walk())) is wf


def test_walk_reaches_steps_inside_workflow_jobs():
    wf = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "test": Job(
                runs_on="ubuntu-latest",
                steps=[Step(uses="actions/checkout@v4"), Step(run="pytest")],
            ),
        },
    )
    steps = [m for m in wf.walk() if isinstance(m, Step)]
    jobs = [m for m in wf.walk() if isinstance(m, Job)]
    assert len(jobs) == 1
    assert {s.uses or s.run for s in steps} == {"actions/checkout@v4", "pytest"}


def test_walk_reaches_steps_inside_composite_action_runs():
    action = Action(
        name="My Action",
        description="composite",
        runs=CompositeRuns(
            steps=[
                Step(uses="actions/setup-node@v4"),
                Step(run="npm ci", shell="bash"),
            ],
        ),
    )
    steps = [m for m in action.walk() if isinstance(m, Step)]
    assert len(steps) == 2


# --- extras participate in traversal, last (H14; see the TypeScript twin in
# packages/typescript/src/models/walk.test.ts) ---


def _extras_job() -> Job:
    return Job(
        runs_on="ubuntu-latest",
        steps=[Step(uses="actions/checkout@v4")],
        extras={"hidden": Step(uses="actions/setup-node@v4")},
    )


def test_children_reaches_models_nested_in_extras():
    """``extras`` is a traversed field, not an opaque blob."""
    uses = [m.uses for m in _extras_job().children()]
    assert "actions/setup-node@v4" in uses


def test_children_yields_extras_last():
    """``extras`` is declared on the base class but must be scanned last.

    ``model_fields`` puts base-class fields before subclass fields, so the
    plain declaration order would yield extras *first*; TypeScript keeps
    extras off ``data`` and appends them. The skip-and-rescan in
    ``children()`` is what makes the two ports agree on visit order.
    """
    assert [m.uses for m in _extras_job().children()] == [
        "actions/checkout@v4",
        "actions/setup-node@v4",
    ]


def test_walk_visits_extras_nested_models_last():
    wf = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={"build": _extras_job()},
    )
    assert [m.uses for m in wf.walk() if isinstance(m, Step)] == [
        "actions/checkout@v4",
        "actions/setup-node@v4",
    ]
