"""Tests for the dev-only schema staleness gate (``ghagen_schema.check``).

``check.run()`` snapshots the generated directory, regenerates, diffs against
git, and restores the tree -- see the module docstring on
``ghagen_schema.check`` for why. These tests exercise that diff against an
isolated throwaway git repository rather than this repo's own working tree,
so a generated-but-uncommitted file can be constructed without touching real
repo state.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ghagen_schema import check as schema_check


def _init_repo(root: Path) -> None:
    """Initialize an empty git repo at *root* with a throwaway identity.

    The identity and ``commit.gpgsign=false`` are set in *this repo's own*
    local config (created under pytest's tmp dir and discarded at test end)
    -- they never touch the invoking user's real, global git config.
    """
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=root,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=root, check=True)


def _commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway git repo with a committed ``schema`` generated-output dir.

    Rebinds ``check.REPO_ROOT`` and ``check.GENERATED_TYPES_DIR`` so
    ``check.run()`` operates entirely inside this repo, never the real one.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _init_repo(root)

    generated = root / "packages" / "typescript" / "src" / "schema"
    generated.mkdir(parents=True)
    (generated / "committed.ts").write_text("export type A = string;\n")
    _commit_all(root, "initial")

    monkeypatch.setattr(schema_check, "REPO_ROOT", root)
    monkeypatch.setattr(schema_check, "GENERATED_TYPES_DIR", generated)
    return root


def test_check_passes_when_regeneration_changes_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Control case: an unchanged, fully-committed tree is clean."""
    monkeypatch.setattr(schema_check.generate, "run", lambda: 0)
    assert schema_check.run() == 0


def test_check_fails_on_a_generated_file_that_was_never_committed(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A regenerated-but-never-committed path must fail the gate.

    ``git diff --exit-code`` alone is blind to untracked paths: regenerating
    into an untracked file changes nothing *tracked*, so the old check printed
    "Schema types are up to date" here. This is exactly the input that check
    could not see -- reproduced with a real git repo and a real untracked
    file, not a mock.
    """
    generated = schema_check.GENERATED_TYPES_DIR

    def fake_generate() -> int:
        # Simulate `generate` producing a new generated file the author
        # never `git add`ed and committed.
        (generated / "never-committed.ts").write_text("export type B = number;\n")
        return 0

    monkeypatch.setattr(schema_check.generate, "run", fake_generate)
    assert schema_check.run() == 1

    # And the tree is restored to its pre-check state either way.
    assert not (generated / "never-committed.ts").exists()
    assert (generated / "committed.ts").exists()
