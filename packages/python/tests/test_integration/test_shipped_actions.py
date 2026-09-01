"""Assertions about the composite actions this repository *ships*.

Not a library test.  These parse the real generated YAML at the repo root --
the artifacts a tag-pinned consumer downloads -- and pin properties of their
shell that no unit test can see, because the shell is a string inside a YAML
block scalar and nothing type-checks or executes it locally.

Python-only on purpose.  The subject is an artifact produced by the Python
generator (``.github/ghagen_workflows.py``); the TypeScript port neither
produces nor consumes it, so a mirror would assert against a file that port has
no relationship to.  The parity-bearing half of the same work is
``pin/plan.py`` / ``pin/plan.ts`` and their shared decision table.

Repo paths come from ``ghagen_schema.paths`` (``pyproject.toml`` puts
``scripts`` on ``pythonpath``), never from hand-rolled ``parents[N]``.
"""

from __future__ import annotations

from typing import Any

import pytest
from ruamel.yaml import YAML

from ghagen_schema.paths import REPO_ROOT

#: Every composite action this repository ships, by directory name.
SHIPPED_ACTIONS = ["check-deps", "check-synth"]


def _load_action(name: str) -> dict[str, Any]:
    yaml = YAML()
    return yaml.load((REPO_ROOT / name / "action.yml").read_text())


def _run_blocks(action: dict[str, Any]) -> list[str]:
    """Every ``run:`` script in a composite action's steps."""
    return [
        str(step["run"])
        for step in action["runs"]["steps"]
        if step.get("run") is not None
    ]


@pytest.fixture(scope="module")
def check_deps() -> dict[str, Any]:
    return _load_action("check-deps")


@pytest.mark.parametrize("name", SHIPPED_ACTIONS)
def test_no_run_block_downgrades_an_exit_code_with_or_true(name: str):
    """``|| true`` before a read of the command's output is a downgrade, not tolerance.

    Measured on a replay of the old detect step: with ``|| true`` the step exits
    **1** with a ``json.decoder.JSONDecodeError`` traceback from the *reader*;
    without it the step exits with the code the CLI chose and prints the CLI's
    own one-line message.  So the construct destroys both the exit code and the
    diagnostic, for every failure mode the CLI has.
    """
    for block in _run_blocks(_load_action(name)):
        assert "|| true" not in block, f"{name}/action.yml: `|| true` in a run block"


@pytest.mark.parametrize("name", SHIPPED_ACTIONS)
def test_no_run_block_parses_ghagen_output_with_the_ambient_python(name: str):
    """A shipped action must not re-implement a reader for ghagen's own output.

    Reaching for the runner's ambient ``python3`` to parse the output of the
    ghagen that was just ``pip install``ed is a fourth, untypechecked, untested
    encoding of the report shape.  The CLI answers; the action asks.
    """
    for block in _run_blocks(_load_action(name)):
        assert "python3 " not in block, (
            f"{name}/action.yml: ambient python3 in a run block"
        )


def test_check_deps_decides_nothing_about_the_lockfile(check_deps: dict[str, Any]):
    """H7: the lockfile-refresh decision must not be reconstructed in shell.

    ``lockfile=None`` is supported configuration; under it ``deps pin`` exits 1.
    A guard written as ``lockfile_stale != 0 || version_bumps != 0`` fires
    anyway, because the serialized report deliberately does not carry
    ``app.lockfile_path``.  The decision belongs to ``pin/plan``, which holds the
    ``App``, and the only thing that may appear in the action is the answer.
    """
    for block in _run_blocks(check_deps):
        assert "deps pin" not in block, (
            "check-deps/action.yml: decides its own lockfile refresh"
        )
        assert "steps.detect." not in block, (
            "check-deps/action.yml: reads a re-derived detect output"
        )


def test_check_deps_exposes_the_plan_as_composite_outputs(check_deps: dict[str, Any]):
    """The outputs a consumer of the tag-pinned action can actually read.

    Per-step ``steps.<id>.outputs.*`` are invisible outside the action, so
    without an ``outputs:`` block no caller -- including a CI job -- can assert
    anything about what the action decided.  That is what made
    ``docs/issues/05`` unactionable rather than merely unaddressed.
    """
    outputs = check_deps.get("outputs")
    assert outputs is not None, "check-deps/action.yml declares no outputs:"
    assert set(outputs) == {
        "action",
        "total_updates",
        "refresh_lockfile",
        "branch",
        "title",
        "changed",
    }
    for key, spec in outputs.items():
        # `value` is optional on ActionOutput (Docker/Node actions omit it) and
        # nothing validates it, so a composite action's outputs are asserted
        # here instead.
        assert spec.get("value"), f"composite output {key} has no value:"


def test_check_deps_can_install_the_working_tree(check_deps: dict[str, Any]):
    """``source`` is what makes a CI exercise test *this* commit.

    Without it, a job writing ``uses: ./check-deps`` gets the action definition
    from the working tree but ``pip install ghagen`` from PyPI -- so it would
    exercise the last published release, and a regression introduced in the same
    PR would pass.  ``check-synth`` has had the input since spec 0005 Part B.
    """
    assert "source" in check_deps["inputs"]
    assert "dry-run" in check_deps["inputs"]
    assert check_deps["inputs"]["dry-run"]["default"] == "false"
