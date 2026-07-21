"""Emit-time dedent folded into the node recursion (ADR-0002 + round-2 unit 3).

Dedent no longer runs as a separate ``model_copy(deep=True)`` + tree walk; it
applies at node-build time inside the emitter, gated by ``auto_dedent`` and
threaded explicitly. These tests cover the previously-untested paths: dedent of
composite-action steps, dedent combined with a Transform, and the guarantee
that the emit path does not deep-copy the Document.
"""

from __future__ import annotations

import ghagen.models._base as base_module
from ghagen import (
    Action,
    App,
    CompositeRuns,
    Job,
    On,
    PushTrigger,
    Step,
    Workflow,
)

_TRIPLE_RUN = """
    echo building
    make all
"""


def _composite_action() -> Action:
    return Action(
        name="Build",
        description="Build the project",
        runs=CompositeRuns(
            steps=[
                Step(run=_TRIPLE_RUN, shell="bash"),
            ],
        ),
    )


def _run_line_indent(yaml: str, marker: str) -> int:
    """Leading-space count of the emitted block-scalar line containing *marker*."""
    line = next(ln for ln in yaml.splitlines() if marker in ln)
    return len(line) - len(line.lstrip(" "))


def test_composite_action_run_is_dedented_by_default() -> None:
    """A composite-action ``runs.steps`` ``run`` is dedented at emit.

    The source-indent (4 spaces from the triple-quote) is stripped, so the
    dedented block-scalar line sits shallower than the raw one.
    """
    dedented = _composite_action().to_yaml(header=None)
    raw = _composite_action().to_yaml(header=None, auto_dedent=False)
    assert dedented != raw
    assert _run_line_indent(dedented, "echo building") == _run_line_indent(
        raw, "echo building"
    ) - len("    ")


def test_composite_action_run_verbatim_without_auto_dedent() -> None:
    """``auto_dedent=False`` leaves the composite ``run`` source-indent intact."""
    dedented = _composite_action().to_yaml(header=None)
    raw = _composite_action().to_yaml(header=None, auto_dedent=False)
    # The raw block keeps the extra 4-space source indent the dedented one lacks.
    assert _run_line_indent(raw, "echo building") > _run_line_indent(
        dedented, "echo building"
    )


def test_composite_action_dedent_does_not_mutate_caller() -> None:
    """Dedent reads-and-copies the value; the caller's model stays raw."""
    action = _composite_action()
    action.to_yaml(header=None)
    step = action.runs.steps[0]
    assert step.run == _TRIPLE_RUN


# --- transform + dedent interaction ---


def _rename_transform(item: Workflow | Action) -> Workflow | Action:
    """A trivial Transform that also appends a step with an indented run."""
    if isinstance(item, Workflow):
        for _path, node in item.walk():
            if isinstance(node, Job):
                node.steps.append(Step(run=_TRIPLE_RUN))
    return item


def test_transform_then_dedent(tmp_path) -> None:
    """A Transform-added Step's ``run`` is still dedented at emit."""
    wf = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={"test": Job(runs_on="ubuntu-latest", steps=[Step(uses="a/b@v1")])},
    )
    app = App(root=tmp_path, lockfile=None, transforms=[_rename_transform])
    app.add_workflow(wf, "ci.yml")
    app.synth()

    out = (tmp_path / ".github/workflows/ci.yml").read_text()
    assert "echo building" in out
    # The transform-added step's run is dedented: its block-scalar line sits at
    # the same shallow indent as a normally-authored step (source indent gone).
    dedented_indent = _run_line_indent(out, "echo building")
    undedented = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={"test": Job(runs_on="ubuntu-latest", steps=[Step(run=_TRIPLE_RUN)])},
    ).to_yaml(header=None, auto_dedent=False)
    assert dedented_indent < _run_line_indent(undedented, "echo building")
    # The caller's original model was deep-copied by the transform pass, so it
    # never gained the appended step.
    assert len(wf.jobs["test"].steps) == 1


# --- single deep-copy on the synth path ---


def test_emit_does_not_deep_copy_the_document(monkeypatch) -> None:
    """``to_yaml(auto_dedent=True)`` performs zero ``model_copy`` calls.

    The old ``_dedent_steps`` deep-copied the whole tree on top of App's own
    copy. Dedent now applies in-place at node build with no mutation, so the
    emit path copies nothing.
    """
    calls = {"n": 0}
    original = base_module.GhagenModel.model_copy

    def _counting_copy(self, *args, **kwargs):
        calls["n"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(base_module.GhagenModel, "model_copy", _counting_copy)

    wf = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "test": Job(
                runs_on="ubuntu-latest",
                steps=[Step(run=_TRIPLE_RUN)],
            )
        },
    )
    wf.to_yaml(header=None, auto_dedent=True)
    assert calls["n"] == 0


def test_synth_deep_copies_once_per_document(monkeypatch, tmp_path) -> None:
    """With a Transform, App copies the Document exactly once; emit adds none."""
    calls = {"n": 0}
    original = base_module.GhagenModel.model_copy

    def _counting_copy(self, *args, **kwargs):
        # Count only top-level Document copies (App._apply_transforms).
        if isinstance(self, base_module.Document):
            calls["n"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(base_module.GhagenModel, "model_copy", _counting_copy)

    wf = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={"test": Job(runs_on="ubuntu-latest", steps=[Step(run=_TRIPLE_RUN)])},
    )
    app = App(root=tmp_path, lockfile=None, transforms=[lambda item: item])
    app.add_workflow(wf, "ci.yml")
    app.synth()

    assert calls["n"] == 1
