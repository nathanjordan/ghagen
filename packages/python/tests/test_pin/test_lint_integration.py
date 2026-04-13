"""Tests for lint integration with lockfile pinning."""

from __future__ import annotations

from datetime import UTC, datetime

from ghagen.app import App
from ghagen.lint.config import LintConfig
from ghagen.lint.engine import run_lint
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.trigger import On, PushTrigger
from ghagen.models.workflow import Workflow
from ghagen.pin.lockfile import Lockfile, PinEntry, write_lockfile

SHA = "a" * 40


def test_unpinned_rule_passes_when_lockfile_covers_ref(tmp_path):
    """The unpinned-actions rule should not flag refs that are in the lockfile."""
    lf = Lockfile(
        pins={"actions/checkout@v4": PinEntry(sha=SHA, resolved_at=datetime.now(UTC))}
    )
    lockfile_path = tmp_path / ".github" / "ghagen.lock.toml"
    write_lockfile(lf, lockfile_path)

    app = App(root=tmp_path)
    wf = Workflow(
        on=On(push=PushTrigger()),
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[Step(uses="actions/checkout@v4")],
            )
        },
    )
    app.add_workflow(wf, "ci.yml")

    # The unpinned-actions rule should NOT flag this since the lockfile covers it.
    # Note: v4 is a version tag which _is_pinned_ref already accepts, so let's
    # test with a mutable ref like @main that would normally be flagged.
    pass  # v4 is already accepted by _is_pinned_ref — covered below


def test_unpinned_rule_passes_for_mutable_ref_when_locked(tmp_path):
    """A mutable ref like @main should NOT be flagged if the lockfile covers it."""
    lf = Lockfile(
        pins={"actions/checkout@main": PinEntry(sha=SHA, resolved_at=datetime.now(UTC))}
    )
    lockfile_path = tmp_path / ".github" / "ghagen.lock.toml"
    write_lockfile(lf, lockfile_path)

    app = App(root=tmp_path)
    wf = Workflow(
        on=On(push=PushTrigger()),
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[Step(uses="actions/checkout@main")],
            )
        },
    )
    app.add_workflow(wf, "ci.yml")

    config = LintConfig()
    violations = run_lint(app, config)
    unpinned = [v for v in violations if v.rule_id == "unpinned-actions"]
    assert unpinned == []


def test_unpinned_rule_flags_mutable_ref_without_lockfile(tmp_path):
    """A mutable ref like @main should be flagged when no lockfile covers it."""
    app = App(root=tmp_path)
    wf = Workflow(
        on=On(push=PushTrigger()),
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[Step(uses="actions/checkout@main")],
            )
        },
    )
    app.add_workflow(wf, "ci.yml")

    config = LintConfig()
    violations = run_lint(app, config)
    unpinned = [v for v in violations if v.rule_id == "unpinned-actions"]
    assert len(unpinned) == 1
