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
    result = runner.invoke(app, ["check-synced"])
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

    result = runner.invoke(app, ["check-synced"])
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
    result = runner.invoke(app, ["check-synced"])
    assert result.exit_code == 1
    assert "out of date" in result.output


def test_synth_no_config(tmp_path: Path, monkeypatch: object):
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    result = runner.invoke(app, ["synth"])
    assert result.exit_code == 1
    assert "no config file found" in result.output


_MINIMAL_WORKFLOW_SRC = """\
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


def test_entrypoint_in_ghagen_yml(tmp_path: Path, monkeypatch: object):
    """An `entrypoint` key in .ghagen.yml is used to locate the App."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "wf.py").write_text(_MINIMAL_WORKFLOW_SRC)

    (tmp_path / ".ghagen.yml").write_text("entrypoint: scripts/wf.py\n")

    result = runner.invoke(app, ["synth"])
    assert result.exit_code == 0, result.output
    assert "Synthesized 1" in result.output
    assert (tmp_path / ".github" / "workflows" / "ci.yml").exists()


def test_entrypoint_relative_to_yml_dir(tmp_path: Path, monkeypatch: object):
    """Relative entrypoint values resolve against .ghagen.yml's directory."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    # File lives in .github/ — path is relative to repo root (where .ghagen.yml is).
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "my_wf.py").write_text(_MINIMAL_WORKFLOW_SRC)
    (tmp_path / ".ghagen.yml").write_text("entrypoint: .github/my_wf.py\n")

    result = runner.invoke(app, ["synth"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".github" / "workflows" / "ci.yml").exists()


def test_entrypoint_file_missing(tmp_path: Path, monkeypatch: object):
    """A bogus entrypoint value exits 1 and names both the yml and target."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    (tmp_path / ".ghagen.yml").write_text("entrypoint: does_not_exist.py\n")

    result = runner.invoke(app, ["synth"])
    assert result.exit_code == 1
    assert ".ghagen.yml" in result.output
    assert "does_not_exist.py" in result.output


def test_entrypoint_wrong_type(tmp_path: Path, monkeypatch: object):
    """A non-string entrypoint value is rejected with a clear error."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    (tmp_path / ".ghagen.yml").write_text("entrypoint: 42\n")

    result = runner.invoke(app, ["synth"])
    assert result.exit_code == 1
    assert "must be a string" in result.output


def test_entrypoint_malformed_yaml(tmp_path: Path, monkeypatch: object):
    """Unparseable .ghagen.yml surfaces a parse error, not a crash."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    (tmp_path / ".ghagen.yml").write_text(":\n  - :\n  bad: [")

    result = runner.invoke(app, ["synth"])
    assert result.exit_code == 1
    assert "failed to parse YAML" in result.output


def test_cli_config_overrides_ghagen_yml(tmp_path: Path, monkeypatch: object):
    """An explicit --config flag wins over the .ghagen.yml entrypoint key."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    # A valid "flag" file the user will pass via --config.
    (tmp_path / "flag_wf.py").write_text(_MINIMAL_WORKFLOW_SRC)
    # A broken .ghagen.yml that would error out if it were consulted.
    (tmp_path / ".ghagen.yml").write_text("entrypoint: does_not_exist.py\n")

    result = runner.invoke(app, ["synth", "--config", "flag_wf.py"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".github" / "workflows" / "ci.yml").exists()


def test_ghagen_yml_without_entrypoint_falls_back(tmp_path: Path, monkeypatch: object):
    """A lint-only .ghagen.yml (no entrypoint key) still falls back to search."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    (tmp_path / ".ghagen.yml").write_text("lint:\n  disable: []\n")
    (tmp_path / "ghagen_config.py").write_text(_MINIMAL_WORKFLOW_SRC)

    result = runner.invoke(app, ["synth"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".github" / "workflows" / "ci.yml").exists()
