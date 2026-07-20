"""Tests for the generic model traversal primitives ``walk()`` / ``children()``."""

from ghagen import Action, Job, On, PushTrigger, Step, Workflow
from ghagen.models.action import CompositeRuns


def test_children_yields_direct_nested_models():
    job = Job(
        runs_on="ubuntu-latest",
        steps=[Step(uses="actions/checkout@v4"), Step(run="pytest")],
    )
    children = list(job.children())
    models = [m for _key, m in children]
    assert all(isinstance(m, Step) for m in models)
    assert len(models) == 2


def test_children_skips_scalars_and_none():
    step = Step(name="only scalars", run="echo hi")
    assert list(step.children()) == []


def test_walk_yields_self_first_with_empty_path():
    wf = Workflow(name="CI", on=On(push=PushTrigger(branches=["main"])))
    first_path, first_model = next(iter(wf.walk()))
    assert first_path == []
    assert first_model is wf


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
    steps = [m for _p, m in wf.walk() if isinstance(m, Step)]
    jobs = [m for _p, m in wf.walk() if isinstance(m, Job)]
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
    steps = [m for _p, m in action.walk() if isinstance(m, Step)]
    assert len(steps) == 2


def test_walk_paths_track_field_keys():
    wf = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={"test": Job(runs_on="ubuntu-latest", steps=[Step(run="pytest")])},
    )
    # A dict field contributes its *key* to the path (matching the TS walk):
    # a job under jobs["test"] with steps yields step paths like ["test", "steps"].
    step_paths = [p for p, m in wf.walk() if isinstance(m, Step)]
    assert step_paths
    assert all(p == ["test", "steps"] for p in step_paths)
