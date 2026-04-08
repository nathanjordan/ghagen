"""Tests for the ghagen CLI."""

from pathlib import Path

from typer.testing import CliRunner

from ghagen.cli.main import app

runner = CliRunner()


def test_init(tmp_path: Path, monkeypatch: object):

    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Created" in result.output

    config = tmp_path / ".github" / "ghagen_workflows.py"
    assert config.exists()
    assert "from ghagen" in config.read_text()


def test_init_already_exists(tmp_path: Path, monkeypatch: object):

    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    # Create the file first
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "ghagen_workflows.py").write_text("# existing")

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_synth_and_check(tmp_path: Path, monkeypatch: object):
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    # Create a config file
    config_file = tmp_path / "ghagen_config.py"
    config_file.write_text(
        """\
from ghagen import App, Job, On, PushTrigger, Step, Workflow

app = App()
ci = Workflow(
    name="CI",
    on=On(push=PushTrigger(branches=["main"])),
    jobs={"test": Job(
        runs_on="ubuntu-latest",
        steps=[Step(uses="actions/checkout@v4")],
    )},
)
app.add_workflow(ci, "ci.yml")
"""
    )

    # Synth
    result = runner.invoke(app, ["synth"])
    assert result.exit_code == 0
    assert "Synthesized 1" in result.output

    # Verify file exists
    generated = tmp_path / ".github" / "workflows" / "ci.yml"
    assert generated.exists()
    content = generated.read_text()
    assert "name: CI" in content
    assert "runs-on: ubuntu-latest" in content

    # Check should pass (files are in sync)
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "up-to-date" in result.output


def test_synth_workflow_and_action(tmp_path: Path, monkeypatch: object):
    """Synth a workflow and an action together via the new App API."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    config_file = tmp_path / "ghagen_config.py"
    config_file.write_text(
        """\
from ghagen import (
    Action,
    ActionInput,
    App,
    CompositeRuns,
    Job,
    On,
    PushTrigger,
    Step,
    Workflow,
)

app = App()

ci = Workflow(
    name="CI",
    on=On(push=PushTrigger(branches=["main"])),
    jobs={"test": Job(
        runs_on="ubuntu-latest",
        steps=[Step(uses="actions/checkout@v4")],
    )},
)
app.add_workflow(ci, "ci.yml")

greet = Action(
    name="Greet",
    description="Say hello",
    inputs={"who": ActionInput(description="Name", default="world")},
    runs=CompositeRuns(steps=[
        Step(run="echo hello ${{ inputs.who }}", shell="bash"),
    ]),
)
app.add_action(greet)
"""
    )

    result = runner.invoke(app, ["synth"])
    assert result.exit_code == 0, result.output
    assert "Synthesized 2 file(s)" in result.output

    assert (tmp_path / ".github" / "workflows" / "ci.yml").exists()
    action_file = tmp_path / "action.yml"
    assert action_file.exists()
    content = action_file.read_text()
    assert "name: Greet" in content
    assert "using: composite" in content

    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "up-to-date" in result.output


def test_check_detects_stale(tmp_path: Path, monkeypatch: object):
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    config_file = tmp_path / "ghagen_config.py"
    config_file.write_text(
        """\
from ghagen import App, Job, On, PushTrigger, Step, Workflow

app = App()
ci = Workflow(
    name="CI",
    on=On(push=PushTrigger(branches=["main"])),
    jobs={"test": Job(
        runs_on="ubuntu-latest",
        steps=[Step(uses="actions/checkout@v4")],
    )},
)
app.add_workflow(ci, "ci.yml")
"""
    )

    # Create a stale file
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("# stale content\n")

    # Check should fail
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 1
    assert "out of date" in result.output


def test_synth_no_config(tmp_path: Path, monkeypatch: object):
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    result = runner.invoke(app, ["synth"])
    assert result.exit_code == 1
    assert "no config file found" in result.output
