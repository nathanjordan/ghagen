"""End-to-end tests for the `ghagen lint` CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ghagen.cli.main import app

runner = CliRunner()


_CLEAN_CONFIG = '''\
"""Clean workflow — passes all lint rules."""

from ghagen import App, Job, Permissions, PushTrigger, Step, Workflow
from ghagen.models.trigger import On

app = App()

ci = Workflow(
    name="ci",
    permissions=Permissions(contents="read"),
    on=On(push=PushTrigger(branches=["main"])),
    jobs={
        "build": Job(
            runs_on="ubuntu-latest",
            timeout_minutes=10,
            steps=[Step(uses="actions/checkout@v4")],
        ),
    },
)

app.add_workflow(ci, "ci.yml")
'''


_BAD_CONFIG = '''\
"""Violating workflow — triggers all three rules."""

from ghagen import App, Job, PushTrigger, Step, Workflow
from ghagen.models.trigger import On

app = App()

ci = Workflow(
    name="ci",
    on=On(push=PushTrigger(branches=["main"])),
    jobs={
        "build": Job(
            runs_on="ubuntu-latest",
            steps=[Step(uses="actions/checkout@main")],
        ),
    },
)

app.add_workflow(ci, "ci.yml")
'''


def _setup(tmp_path: Path, config_contents: str) -> None:
    config_dir = tmp_path / ".github"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "ghagen_workflows.py").write_text(config_contents)


def test_lint_on_clean_workflow_exits_zero(
    tmp_path: Path, monkeypatch: object
) -> None:
    _setup(tmp_path, _CLEAN_CONFIG)
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["lint"])
    assert result.exit_code == 0
    assert "no violations" in result.output.lower()


def test_lint_on_violating_workflow_reports_all_rules(
    tmp_path: Path, monkeypatch: object
) -> None:
    _setup(tmp_path, _BAD_CONFIG)
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["lint"])
    # All are warnings by default → exit 0
    assert result.exit_code == 0
    assert "missing-permissions" in result.output
    assert "unpinned-actions" in result.output
    assert "missing-timeout" in result.output


def test_lint_warnings_only_exits_zero(
    tmp_path: Path, monkeypatch: object
) -> None:
    _setup(tmp_path, _BAD_CONFIG)
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["lint"])
    assert result.exit_code == 0


def test_lint_errors_exit_one(tmp_path: Path, monkeypatch: object) -> None:
    """With severity overridden to error, exit code should be 1."""
    _setup(tmp_path, _BAD_CONFIG)
    (tmp_path / ".github" / "ghagen.toml").write_text(
        """
[lint.severity]
missing-permissions = "error"
"""
    )
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["lint"])
    assert result.exit_code == 1


def test_lint_json_format(tmp_path: Path, monkeypatch: object) -> None:
    _setup(tmp_path, _BAD_CONFIG)
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["lint", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "violations" in data
    assert "summary" in data
    assert data["summary"]["warnings"] == 3
    assert data["summary"]["errors"] == 0


def test_lint_github_format(tmp_path: Path, monkeypatch: object) -> None:
    _setup(tmp_path, _BAD_CONFIG)
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["lint", "--format", "github"])
    assert result.exit_code == 0
    assert "::warning" in result.output
    assert "title=missing-permissions" in result.output


def test_lint_list_rules(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    result = runner.invoke(app, ["lint", "--list-rules"])
    assert result.exit_code == 0
    assert "missing-permissions" in result.output
    assert "unpinned-actions" in result.output
    assert "missing-timeout" in result.output


def test_lint_disable_flag(tmp_path: Path, monkeypatch: object) -> None:
    _setup(tmp_path, _BAD_CONFIG)
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["lint", "--disable", "missing-permissions"])
    assert result.exit_code == 0
    assert "missing-permissions" not in result.output
    # The other two rules should still fire
    assert "unpinned-actions" in result.output
    assert "missing-timeout" in result.output


def test_lint_disable_multiple_flags(
    tmp_path: Path, monkeypatch: object
) -> None:
    _setup(tmp_path, _BAD_CONFIG)
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    result = runner.invoke(
        app,
        [
            "lint",
            "--disable",
            "missing-permissions",
            "--disable",
            "unpinned-actions",
        ],
    )
    assert result.exit_code == 0
    assert "missing-permissions" not in result.output
    assert "unpinned-actions" not in result.output
    assert "missing-timeout" in result.output


def test_lint_multi_source_warning(
    tmp_path: Path, monkeypatch: object
) -> None:
    _setup(tmp_path, _CLEAN_CONFIG)
    (tmp_path / ".github" / "ghagen.toml").write_text("[lint]\ndisable = []\n")
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.ghagen.lint]
disable = []
"""
    )
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["lint"])
    assert result.exit_code == 0
    # Warning goes to stderr but CliRunner combines streams by default
    assert "multiple locations" in result.output
    assert "ghagen.toml" in result.output
    assert "pyproject.toml" in result.output


def test_lint_bad_config_exits_two(
    tmp_path: Path, monkeypatch: object
) -> None:
    _setup(tmp_path, _CLEAN_CONFIG)
    (tmp_path / ".github" / "ghagen.toml").write_text(
        """
[lint.severity]
missing-timeout = "definitely-not-a-severity"
"""
    )
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["lint"])
    assert result.exit_code == 2
