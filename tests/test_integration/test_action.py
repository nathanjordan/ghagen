"""Integration tests for action.yml generation with schema validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ghagen import (
    Action,
    ActionInput,
    ActionOutput,
    App,
    Branding,
    CompositeRuns,
    DockerRuns,
    Job,
    NodeRuns,
    On,
    PushTrigger,
    Step,
    Workflow,
)

from .conftest import validate_and_roundtrip


def test_composite_action_full(action_schema: dict[str, Any]) -> None:
    """Full composite action generates schema-valid YAML."""
    action = Action(
        name="Greet",
        description="Say hello",
        author="ghagen",
        branding=Branding(icon="heart", color="purple"),
        inputs={
            "greeting": ActionInput(
                description="Who to greet",
                required=True,
                default="world",
            ),
        },
        outputs={
            "message": ActionOutput(
                description="The greeting message",
                value="${{ steps.greet.outputs.text }}",
            ),
        },
        runs=CompositeRuns(
            steps=[
                Step(
                    id="greet",
                    name="Greet",
                    run="echo Hello, ${{ inputs.greeting }}",
                    shell="bash",
                ),
            ],
        ),
    )

    yaml_str = action.to_yaml(include_header=False)
    data = validate_and_roundtrip(yaml_str, action_schema)

    assert data["name"] == "Greet"
    assert data["description"] == "Say hello"
    assert data["author"] == "ghagen"
    assert data["branding"]["icon"] == "heart"
    assert data["inputs"]["greeting"]["required"] is True
    assert data["outputs"]["message"]["value"] == "${{ steps.greet.outputs.text }}"
    assert data["runs"]["using"] == "composite"
    assert data["runs"]["steps"][0]["run"] == "echo Hello, ${{ inputs.greeting }}"


def test_docker_action_full(action_schema: dict[str, Any]) -> None:
    """Docker action generates schema-valid YAML."""
    action = Action(
        name="Docker Action",
        description="Runs a Docker container",
        inputs={
            "who": ActionInput(description="Who to greet", default="world"),
        },
        outputs={
            "time": ActionOutput(description="Time the greeting happened"),
        },
        runs=DockerRuns(
            image="Dockerfile",
            env={"GREETING": "Hello"},
            args=["${{ inputs.who }}"],
            pre_entrypoint="pre.sh",
            pre_if="runner.os == 'Linux'",
            entrypoint="entrypoint.sh",
            post_entrypoint="post.sh",
            post_if="always()",
        ),
    )

    yaml_str = action.to_yaml(include_header=False)
    data = validate_and_roundtrip(yaml_str, action_schema)

    runs = data["runs"]
    assert runs["using"] == "docker"
    assert runs["image"] == "Dockerfile"
    assert runs["env"] == {"GREETING": "Hello"}
    assert runs["args"] == ["${{ inputs.who }}"]
    assert runs["pre-entrypoint"] == "pre.sh"
    assert runs["pre-if"] == "runner.os == 'Linux'"
    assert runs["entrypoint"] == "entrypoint.sh"
    assert runs["post-entrypoint"] == "post.sh"
    assert runs["post-if"] == "always()"


def test_node_action_full(action_schema: dict[str, Any]) -> None:
    """Node.js action generates schema-valid YAML."""
    action = Action(
        name="Node Action",
        description="Runs a Node.js script",
        runs=NodeRuns(
            using="node20",
            main="dist/index.js",
            pre="dist/setup.js",
            post="dist/cleanup.js",
            pre_if="runner.os == 'Linux'",
            post_if="always()",
        ),
    )

    yaml_str = action.to_yaml(include_header=False)
    data = validate_and_roundtrip(yaml_str, action_schema)

    runs = data["runs"]
    assert runs["using"] == "node20"
    assert runs["main"] == "dist/index.js"
    assert runs["pre"] == "dist/setup.js"
    assert runs["post"] == "dist/cleanup.js"


def test_app_adds_workflow_and_action_to_right_paths(tmp_path: Path) -> None:
    """``App.add_workflow`` and ``add_action`` place files by convention."""
    app = App(root=tmp_path)

    ci = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "test": Job(
                runs_on="ubuntu-latest",
                steps=[Step(uses="actions/checkout@v4")],
            ),
        },
    )
    app.add_workflow(ci, "ci.yml")

    action = Action(
        name="Test Action",
        description="desc",
        runs=CompositeRuns(steps=[Step(run="echo", shell="bash")]),
    )
    app.add_action(action)

    written = app.synth()
    assert len(written) == 2

    workflow_file = tmp_path / ".github" / "workflows" / "ci.yml"
    action_file = tmp_path / "action.yml"
    assert workflow_file.exists()
    assert action_file.exists()
    assert "name: CI" in workflow_file.read_text()
    assert "name: Test Action" in action_file.read_text()
    assert "using: composite" in action_file.read_text()


def test_app_add_action_with_custom_dir(tmp_path: Path) -> None:
    """``add_action(..., dir=...)`` places action.yml inside the directory."""
    app = App(root=tmp_path)
    action = Action(
        name="Sub",
        description="Subdir action",
        runs=CompositeRuns(steps=[Step(run="echo", shell="bash")]),
    )
    app.add_action(action, dir="actions/sub")
    app.synth()

    target = tmp_path / "actions" / "sub" / "action.yml"
    assert target.exists()
    assert "name: Sub" in target.read_text()


def test_app_add_escape_hatch_explicit_path(tmp_path: Path) -> None:
    """``add(item, path=...)`` writes to the explicit path under ``root``."""
    app = App(root=tmp_path)
    action = Action(
        name="Custom",
        description="Custom-path action",
        runs=CompositeRuns(steps=[Step(run="echo", shell="bash")]),
    )
    app.add(action, "custom/location/action.yml")
    app.synth()

    target = tmp_path / "custom" / "location" / "action.yml"
    assert target.exists()


def test_app_check_detects_stale_action(tmp_path: Path) -> None:
    """``App.check`` flags an action whose on-disk content is out of date."""
    app = App(root=tmp_path)
    action = Action(
        name="Stale",
        description="desc",
        runs=CompositeRuns(steps=[Step(run="echo", shell="bash")]),
    )
    app.add_action(action)

    # Write a stale action.yml.
    (tmp_path / "action.yml").write_text("# stale content\n")

    stale = app.check()
    assert len(stale) == 1
    path, diff = stale[0]
    assert path == tmp_path / "action.yml"
    assert "stale content" in diff


def test_app_check_reports_missing_file(tmp_path: Path) -> None:
    """``App.check`` reports an item whose file doesn't exist yet."""
    app = App(root=tmp_path)
    action = Action(
        name="Missing",
        description="desc",
        runs=CompositeRuns(steps=[Step(run="echo", shell="bash")]),
    )
    app.add_action(action)

    stale = app.check()
    assert len(stale) == 1
    _, diff = stale[0]
    assert "does not exist" in diff
