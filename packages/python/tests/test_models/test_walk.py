"""Tests for the generic model traversal primitives ``walk()`` / ``children()``."""

from ghagen import Action, Job, On, PushTrigger, Raw, Step, Workflow, with_comment
from ghagen.models.action import CompositeRuns


def _visit_labels(root) -> list[str]:
    """Every model ``walk()`` visits, in order, labelled by kind + a stable field.

    The peer of the TypeScript twin's ``visitLabels`` helper in
    ``packages/typescript/src/models/walk.test.ts``.
    """
    labels = []
    for model in root.walk():
        tag = model.uses if getattr(model, "uses", None) else None
        tag = tag or (model.name if getattr(model, "name", None) else None)
        tag = tag or (model.run if getattr(model, "run", None) else None)
        kind = type(model).__name__.lower()
        labels.append(f"{kind}:{tag}" if tag else kind)
    return labels


def test_children_yields_direct_nested_models():
    job = Job(
        runs_on="ubuntu-latest",
        steps=[Step(uses="actions/checkout@v4"), Step(run="pytest")],
    )
    models = list(job.children())
    assert all(isinstance(m, Step) for m in models)
    # Ordered, not just present -- a reordering regression in the list branch
    # of ``_scan_for_models`` must fail this, matching the TypeScript twin's
    # ``toEqual`` in "yields bare Models, not key/model records".
    assert [m.uses or m.run for m in models] == ["actions/checkout@v4", "pytest"]


def test_children_skips_scalars_and_none():
    step = Step(name="only scalars", run="echo hi")
    assert list(step.children()) == []


def test_walk_yields_self_first():
    wf = Workflow(name="CI", on=On(push=PushTrigger(branches=["main"])))
    assert next(iter(wf.walk())) is wf


def test_walk_visits_depth_first_pre_order_over_a_nested_document():
    """``walk()`` yields in a defined, meaningful order -- not just a defined set.

    The peer of the TypeScript twin's "visits depth-first, pre-order, over a
    nested document" in ``walk.test.ts``. This asserts the full ordered
    sequence (workflow, then each job interleaved with its own steps) rather
    than set-membership, so a traversal-order regression in either the dict
    branch (``jobs``) or the list branch (``steps``) of ``_scan_for_models``
    fails this test. Traversal order determines emission order for anything
    downstream of the walk (proposal 24), which is exactly what a set
    assertion cannot observe.
    """
    wf = Workflow(
        name="CI",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[Step(uses="actions/checkout@v4"), Step(run="pytest")],
            ),
            "lint": Job(runs_on="ubuntu-latest", steps=[Step(run="ruff")]),
        },
    )
    assert _visit_labels(wf) == [
        "workflow:CI",
        "job",
        "step:actions/checkout@v4",
        "step:pytest",
        "job",
        "step:ruff",
    ]


def test_walk_traverses_commented_wrappers_but_not_into_raw():
    """``Commented`` is transparent, ``Raw`` is an opaque escape hatch.

    The peer of the TypeScript twin's "traverses through Commented wrappers
    but not into Raw" in ``walk.test.ts``. Guards the two branches of
    ``_scan_for_models`` (``packages/python/src/ghagen/models/_base.py``,
    the ``Commented`` and ``Raw`` ``elif`` arms) that had no Python peer.

    A whole field's value -- not one list item -- is what carries a
    ``Commented`` wrapper in this port: ``_preserve_commented`` re-attaches
    the wrapper to the *field* after validation (``GhagenModel`` docstring
    examples: ``Step(uses=with_comment(...))``), so ``steps`` below is
    ``Commented([Step(...)])`` at runtime, not a list containing a
    ``Commented`` item as the TypeScript twin builds it.
    """
    wf = Workflow(
        name="CI",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=with_comment([Step(uses="actions/checkout@v4")], "pin me"),
                extras={"escape": Raw({"nested": Step(uses="actions/never-seen@v1")})},
            ),
        },
    )
    steps = [m for m in wf.walk() if isinstance(m, Step)]
    assert [s.uses for s in steps] == ["actions/checkout@v4"]


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
