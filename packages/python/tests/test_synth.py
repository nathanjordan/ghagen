"""Tests for ghagen.synth — the filesystem-free synthesis pipeline.

These exercise the ``render`` seam directly with pure-string assertions: no
temp dir, no disk. They cover the invariants that previously were only
observable after a round-trip through the filesystem via ``App.synth`` —
transform ordering, clone isolation, and header / auto_dedent threading.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ghagen.emitter.header import DEFAULT
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.trigger import On, PushTrigger
from ghagen.models.workflow import Workflow
from ghagen.pin.lockfile import Lockfile, PinEntry
from ghagen.pin.transform import PinTransform
from ghagen.synth import Rendered, apply_transforms, render

SHA_CHECKOUT = "a" * 40
SAMPLE_TIME = datetime(2026, 4, 9, tzinfo=UTC)


def _lockfile(**pins: str) -> Lockfile:
    return Lockfile(
        pins={
            uses: PinEntry(sha=sha, resolved_at=SAMPLE_TIME)
            for uses, sha in pins.items()
        }
    )


def _workflow(uses: str = "actions/checkout@v4", name: str = "CI") -> Workflow:
    return Workflow(
        name=name,
        on=On(push=PushTrigger()),
        jobs={"build": Job(runs_on="ubuntu-latest", steps=[Step(uses=uses)])},
    )


def _workflow_with_run(run: str) -> Workflow:
    return Workflow(
        name="CI",
        on=On(push=PushTrigger()),
        jobs={"build": Job(runs_on="ubuntu-latest", steps=[Step(run=run)])},
    )


def _rename_uses(new_ref: str):
    """A user transform that rewrites the first step's ``uses`` ref."""

    def transform(item):
        item.jobs["build"].steps[0].uses = new_ref
        return item

    return transform


class TestRender:
    def test_returns_one_rendered_per_item(self):
        items = [(_workflow(), Path("ci.yml")), (_workflow(), Path("cd.yml"))]
        results = render(items, [], header=None, auto_dedent=True)
        assert len(results) == 2
        assert [r.path for r in results] == [Path("ci.yml"), Path("cd.yml")]
        assert all(isinstance(r, Rendered) for r in results)

    def test_path_is_carried_through_opaque(self):
        # An arbitrary registered path is returned untouched — no root join.
        weird = Path("nested/dir/thing.yaml")
        [r] = render([(_workflow(), weird)], [], header=None, auto_dedent=True)
        assert r.path == weird

    def test_pin_runs_after_user_transforms(self):
        # The whole ordering contract: transforms fold in list order. A user
        # transform rewrites the ref to one present in the lockfile; pin then
        # locks the *surviving* ref.
        lf = _lockfile(**{"actions/checkout@v4": SHA_CHECKOUT})
        # Authored ref is v3 (absent from the lockfile); user transform rewrites
        # it to v4, which pin (running last) then resolves to a SHA.
        wf = _workflow(uses="actions/checkout@v3")
        text = render(
            [(wf, Path("ci.yml"))],
            [_rename_uses("actions/checkout@v4"), PinTransform(lf)],
            header=None,
            auto_dedent=True,
        )[0].text
        assert f"actions/checkout@{SHA_CHECKOUT}" in text  # pinned
        assert "v4" in text  # user edit survived (as the pin's EOL comment)
        assert "v3" not in text

    def test_render_does_not_mutate_input(self):
        original = _workflow(uses="actions/checkout@v4")
        render(
            [(original, Path("ci.yml"))],
            [_rename_uses("actions/setup-node@v4")],
            header=None,
            auto_dedent=True,
        )
        # The clone was edited; the caller's model is untouched.
        assert original.jobs["build"].steps[0].uses == "actions/checkout@v4"

    def test_header_none_emits_no_header(self):
        text = render(
            [(_workflow(), Path("ci.yml"))], [], header=None, auto_dedent=True
        )[0].text
        assert not text.startswith("#")

    def test_default_header_is_threaded(self):
        text = render(
            [(_workflow(), Path("ci.yml"))], [], header=DEFAULT, auto_dedent=True
        )[0].text
        assert text.startswith("#")

    def test_string_header_is_threaded(self):
        text = render(
            [(_workflow(), Path("ci.yml"))],
            [],
            header="hand written",
            auto_dedent=True,
        )[0].text
        assert text.startswith("# hand written")

    def test_auto_dedent_false_passes_run_through(self):
        text = render(
            [
                (
                    _workflow_with_run("\n        echo hi\n        echo bye\n    "),
                    Path("ci.yml"),
                )
            ],
            [],
            header=None,
            auto_dedent=False,
        )[0].text
        assert "        echo hi" in text

    def test_auto_dedent_true_differs_from_false(self):
        run = "\n        echo hi\n        echo bye\n    "
        dedented = render(
            [(_workflow_with_run(run), Path("ci.yml"))],
            [],
            header=None,
            auto_dedent=True,
        )[0].text
        raw = render(
            [(_workflow_with_run(run), Path("ci.yml"))],
            [],
            header=None,
            auto_dedent=False,
        )[0].text
        assert "echo hi" in dedented
        # auto_dedent=True strips the script's own indentation, so the emitted
        # text differs from the verbatim (auto_dedent=False) emission.
        assert dedented != raw


class TestApplyTransforms:
    def test_no_transforms_returns_same_object(self):
        wf = _workflow()
        assert apply_transforms(wf, []) is wf

    def test_transforms_apply_in_order(self):
        wf = _workflow(uses="actions/checkout@v1")
        result = apply_transforms(
            wf,
            [_rename_uses("actions/checkout@v2"), _rename_uses("actions/checkout@v3")],
        )
        assert result.jobs["build"].steps[0].uses == "actions/checkout@v3"

    def test_deep_copies_before_mutating(self):
        wf = _workflow(uses="actions/checkout@v4")
        result = apply_transforms(wf, [_rename_uses("actions/setup-node@v4")])
        assert result is not wf
        assert wf.jobs["build"].steps[0].uses == "actions/checkout@v4"
        assert result.jobs["build"].steps[0].uses == "actions/setup-node@v4"
