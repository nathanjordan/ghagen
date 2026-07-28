"""Tests for ghagen.App — the filesystem tail of the synthesis pipeline.

The render seam itself is covered in ``test_synth``; these focus on what ``App``
adds on top: resolving ``root / rel_path``, writing / reading / diffing, and the
one ordering responsibility it owns — composing user transforms first and the
pin transform last.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ghagen.app import WORKFLOWS_DIR, App
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.trigger import On, PushTrigger
from ghagen.models.workflow import Workflow
from ghagen.pin.lockfile import Lockfile, PinEntry, write_lockfile

SHA_CHECKOUT = "a" * 40
SAMPLE_TIME = datetime(2026, 4, 9, tzinfo=UTC)


def _workflow(uses: str = "actions/checkout@v4") -> Workflow:
    return Workflow(
        name="CI",
        on=On(push=PushTrigger()),
        jobs={"build": Job(runs_on="ubuntu-latest", steps=[Step(uses=uses)])},
    )


class TestSynth:
    def test_writes_registered_workflow_to_resolved_path(self, tmp_path: Path):
        app = App(root=tmp_path, lockfile=None)
        app.add_workflow(_workflow(), "ci.yml")
        written = app.synth()
        assert written == [tmp_path / WORKFLOWS_DIR / "ci.yml"]
        assert written[0].is_file()
        content = written[0].read_text()
        assert "name: CI" in content
        assert "actions/checkout@v4" in content

    def test_creates_parent_directories(self, tmp_path: Path):
        app = App(root=tmp_path, lockfile=None)
        app.add(_workflow(), "deeply/nested/out.yml")
        [written] = app.synth()
        assert written == tmp_path / "deeply/nested/out.yml"
        assert written.is_file()


class TestCheck:
    def test_empty_when_in_sync(self, tmp_path: Path):
        app = App(root=tmp_path, lockfile=None)
        app.add_workflow(_workflow(), "ci.yml")
        app.synth()
        assert app.check() == []

    def test_flags_missing_file(self, tmp_path: Path):
        app = App(root=tmp_path, lockfile=None)
        app.add_workflow(_workflow(), "ci.yml")
        stale = app.check()
        assert len(stale) == 1
        assert "File does not exist" in stale[0][1]

    def test_flags_tampered_file_with_diff(self, tmp_path: Path):
        app = App(root=tmp_path, lockfile=None)
        app.add_workflow(_workflow(), "ci.yml")
        app.synth()
        (tmp_path / WORKFLOWS_DIR / "ci.yml").write_text("name: tampered\n")
        stale = app.check()
        assert len(stale) == 1
        assert "---" in stale[0][1]
        assert "+++" in stale[0][1]


class TestTransformComposition:
    def test_user_transform_runs_on_a_deep_clone(self, tmp_path: Path):
        original = _workflow()

        def rename(item):
            item.name = "RENAMED"
            return item

        app = App(root=tmp_path, lockfile=None, transforms=[rename])
        app.add(original, "out.yml")
        [written] = app.synth()
        assert "name: RENAMED" in written.read_text()
        # The caller's model is untouched.
        assert original.name == "CI"

    def test_pin_runs_after_user_transforms(self, tmp_path: Path):
        # A user transform rewrites the authored ref (v3, absent from the
        # lockfile) to v4, which is locked. Because pin runs LAST, the injected
        # ref is pinned in the emitted output.
        write_lockfile(
            Lockfile(
                pins={
                    "actions/checkout@v4": PinEntry(
                        sha=SHA_CHECKOUT, resolved_at=SAMPLE_TIME
                    )
                }
            ),
            tmp_path / ".ghagen.lock.yml",
        )

        def rewrite(item):
            item.jobs["build"].steps[0].uses = "actions/checkout@v4"
            return item

        app = App(root=tmp_path, transforms=[rewrite])
        app.add_workflow(_workflow(uses="actions/checkout@v3"), "ci.yml")
        [written] = app.synth()
        content = written.read_text()
        assert f"actions/checkout@{SHA_CHECKOUT}" in content  # pinned
        assert "v3" not in content  # authored ref was rewritten before pinning
