"""The Python half of the docs' emitted-output oracle.

Every YAML block the guides show is produced by running the emitter at
docs-build time -- see ``docs/src/snippets/emitted.ts`` and ``docs/issues/18``.
That build has Node and no Python, so it can only run the TypeScript port; it
pins each result to ``fixtures/expected/docs_*.yml``.

This module is the other half of that pin. It builds the mirrored Python model
for each documented example and byte-compares against the same file, so a
cross-port divergence in anything the guides show fails one side or the other
instead of shipping. The snippets in the guides' Python tabs are the models
below -- keep the two in step.
"""

from __future__ import annotations

from pytest_snapshot.plugin import Snapshot

from ghagen import (
    Job,
    On,
    PRTrigger,
    PushTrigger,
    Step,
    Workflow,
    with_comment,
    with_eol_comment,
)
from ghagen_schema.paths import EXPECTED_DIR

SNAPSHOT_DIR = EXPECTED_DIR


def _build_job() -> Job:
    """The filler job the field-level comment examples hang a workflow off.

    Shared so that the annotated field is the only thing that varies between
    them, and so the guides' snippets can stay short enough to read.
    """
    return Job(runs_on="ubuntu-latest", steps=[Step(run="make")])


def test_docs_quickstart(snapshot: Snapshot):
    """`index.mdx` -- "ghagen generates clean, readable YAML"."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name="CI",
        on=On(
            push=PushTrigger(branches=["main"]),
            pull_request=PRTrigger(branches=["main"]),
        ),
        jobs={
            "test": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(uses="actions/checkout@v4"),
                    Step(name="Run tests", run="python -m pytest"),
                ],
            ),
        },
    )
    snapshot.assert_match(wf.to_yaml(header=None), "docs_quickstart.yml")


def test_docs_comment_block(snapshot: Snapshot):
    """`guides/comments.mdx` -- "Block comments"."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "test": Job(
                name="Test",
                runs_on="ubuntu-latest",
                comment="Run the full test suite against all supported Python versions",
                steps=[Step(run="pytest")],
            ),
        },
    )
    snapshot.assert_match(wf.to_yaml(header=None), "docs_comment_block.yml")


def test_docs_comment_eol(snapshot: Snapshot):
    """`guides/comments.mdx` -- "End-of-line comments"."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "lint": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(
                        name="Ruff",
                        run="ruff check .",
                        eol_comment="fast Python linter",
                    ),
                ],
            ),
        },
    )
    snapshot.assert_match(wf.to_yaml(header=None), "docs_comment_eol.yml")


def test_docs_comment_field_block(snapshot: Snapshot):
    """`guides/comments.mdx` -- "Field-level block comments"."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name=with_comment("CI", "The name shown in the GitHub UI"),
        on=On(push=PushTrigger(branches=["main"])),
        jobs={"build": _build_job()},
    )
    snapshot.assert_match(wf.to_yaml(header=None), "docs_comment_field_block.yml")


def test_docs_comment_field_eol(snapshot: Snapshot):
    """`guides/comments.mdx` -- "Field-level EOL comments"."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name="CI",
        on=with_eol_comment(
            On(push=PushTrigger(branches=["main"])), "trigger configuration"
        ),
        jobs={"build": _build_job()},
    )
    snapshot.assert_match(wf.to_yaml(header=None), "docs_comment_field_eol.yml")


def test_docs_comment_full(snapshot: Snapshot):
    """`guides/comments.mdx` -- "Full example", all four comment kinds."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name=with_comment("Commented Workflow", "The name shown in the GitHub UI"),
        on=with_eol_comment(
            On(push=PushTrigger(branches=["main"])), "trigger configuration"
        ),
        jobs={
            "lint": Job(
                name="Lint",
                runs_on="ubuntu-latest",
                comment="Run linters before tests",
                steps=[
                    Step(uses="actions/checkout@v4"),
                    Step(
                        name="Ruff",
                        run="ruff check .",
                        eol_comment="fast Python linter",
                    ),
                ],
            ),
        },
    )
    snapshot.assert_match(wf.to_yaml(header=None), "docs_comment_full.yml")


def test_docs_header_verbatim(snapshot: Snapshot):
    """`guides/comments.mdx` -- a string header sitting straight on the body."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={"build": _build_job()},
    )
    snapshot.assert_match(wf.to_yaml("Hand written"), "docs_header_verbatim.yml")


def test_docs_extras(snapshot: Snapshot):
    """`guides/escape-hatches.mdx` -- "extras"."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name="Extras",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                extras={"timeout-minutes": 30, "continue-on-error": True},
            ),
        },
    )
    snapshot.assert_match(wf.to_yaml(header=None), "docs_extras.yml")
