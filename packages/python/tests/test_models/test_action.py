"""Tests for the Action model and its sub-models."""

from __future__ import annotations

from ruamel.yaml.comments import CommentedMap

from ghagen import (
    Action,
    ActionInput,
    ActionOutput,
    Branding,
    CompositeRuns,
    DockerRuns,
    NodeRuns,
    Step,
)


def test_minimal_composite_action() -> None:
    """The smallest valid composite action."""
    action = Action(
        name="Minimal",
        description="A minimal composite action",
        runs=CompositeRuns(steps=[Step(run="echo hi", shell="bash")]),
    )
    cm = action.to_commented_map()
    assert cm["name"] == "Minimal"
    assert cm["description"] == "A minimal composite action"
    assert cm["runs"]["using"] == "composite"
    assert cm["runs"]["steps"][0]["run"] == "echo hi"
    assert cm["runs"]["steps"][0]["shell"] == "bash"


def test_composite_action_full() -> None:
    """Composite action with inputs, outputs, branding, author."""
    action = Action(
        name="Full Composite",
        description="A fully specified composite action",
        author="ghagen",
        branding=Branding(icon="check-circle", color="green"),
        inputs={
            "greeting": ActionInput(
                description="Who to greet",
                required=True,
                default="world",
            ),
            "shout": ActionInput(
                description="Shout the greeting",
                required=False,
                default="false",
            ),
        },
        outputs={
            "result": ActionOutput(
                description="The greeting text",
                value="${{ steps.greet.outputs.text }}",
            ),
        },
        runs=CompositeRuns(
            steps=[
                Step(
                    id="greet",
                    run="echo hello ${{ inputs.greeting }}",
                    shell="bash",
                ),
            ],
        ),
    )
    cm = action.to_commented_map()
    assert cm["author"] == "ghagen"
    assert cm["branding"]["icon"] == "check-circle"
    assert cm["branding"]["color"] == "green"
    assert cm["inputs"]["greeting"]["required"] is True
    assert cm["inputs"]["greeting"]["default"] == "world"
    assert cm["inputs"]["shout"]["required"] is False
    assert cm["outputs"]["result"]["value"] == "${{ steps.greet.outputs.text }}"
    assert cm["runs"]["using"] == "composite"
    assert cm["runs"]["steps"][0]["id"] == "greet"


def test_docker_action() -> None:
    """Docker container action with env, args, entrypoints, pre-if."""
    action = Action(
        name="Docker",
        description="A Docker action",
        runs=DockerRuns(
            image="Dockerfile",
            env={"DEBUG": "true"},
            args=["--flag", "value"],
            pre_entrypoint="pre.sh",
            pre_if="runner.os == 'Linux'",
            entrypoint="main.sh",
            post_entrypoint="post.sh",
            post_if="always()",
        ),
    )
    cm = action.to_commented_map()
    runs = cm["runs"]
    assert runs["using"] == "docker"
    assert runs["image"] == "Dockerfile"
    assert runs["env"]["DEBUG"] == "true"
    assert runs["args"] == ["--flag", "value"]
    assert runs["pre-entrypoint"] == "pre.sh"
    assert runs["pre-if"] == "runner.os == 'Linux'"
    assert runs["entrypoint"] == "main.sh"
    assert runs["post-entrypoint"] == "post.sh"
    assert runs["post-if"] == "always()"


def test_node_action() -> None:
    """Node.js action with main, pre, post, pre-if, post-if."""
    action = Action(
        name="Node",
        description="A JavaScript action",
        runs=NodeRuns(
            using="node20",
            main="dist/index.js",
            pre="dist/pre.js",
            post="dist/post.js",
            pre_if="runner.os == 'Linux'",
            post_if="always()",
        ),
    )
    cm = action.to_commented_map()
    runs = cm["runs"]
    assert runs["using"] == "node20"
    assert runs["main"] == "dist/index.js"
    assert runs["pre"] == "dist/pre.js"
    assert runs["post"] == "dist/post.js"
    assert runs["pre-if"] == "runner.os == 'Linux'"
    assert runs["post-if"] == "always()"


def test_action_key_ordering() -> None:
    """Top-level action keys follow canonical order."""
    action = Action(
        name="Ordered",
        description="desc",
        author="me",
        branding=Branding(icon="check-circle", color="green"),
        inputs={"foo": ActionInput(description="foo")},
        outputs={"bar": ActionOutput(description="bar", value="baz")},
        runs=CompositeRuns(steps=[Step(run="echo", shell="bash")]),
    )
    cm = action.to_commented_map()
    keys = list(cm.keys())
    assert keys == [
        "name",
        "description",
        "author",
        "branding",
        "inputs",
        "outputs",
        "runs",
    ]


def test_action_input_deprecation_message_alias() -> None:
    """``deprecation_message`` serializes as ``deprecationMessage``."""
    input_ = ActionInput(
        description="legacy",
        deprecation_message="Use new_input instead.",
    )
    cm = input_.to_commented_map()
    assert "deprecationMessage" in cm
    assert cm["deprecationMessage"] == "Use new_input instead."
    assert "deprecation_message" not in cm


def test_action_input_key_ordering() -> None:
    """Action input keys follow canonical order."""
    input_ = ActionInput(
        description="d",
        required=True,
        default="x",
        deprecation_message="old",
    )
    cm = input_.to_commented_map()
    keys = list(cm.keys())
    assert keys == ["description", "required", "default", "deprecationMessage"]


def test_branding_key_ordering() -> None:
    """Branding keys: icon before color."""
    branding = Branding(icon="heart", color="red")
    cm = branding.to_commented_map()
    assert list(cm.keys()) == ["icon", "color"]


def test_action_to_yaml_with_header() -> None:
    """``to_yaml`` prepends the default ghagen header."""
    action = Action(
        name="Test",
        description="Test",
        runs=CompositeRuns(steps=[Step(run="echo", shell="bash")]),
    )
    yaml_str = action.to_yaml()
    assert "# This file is generated by ghagen" in yaml_str
    assert "name: Test" in yaml_str


def test_action_to_yaml_no_header() -> None:
    """``to_yaml(include_header=False)`` omits the header."""
    action = Action(
        name="Test",
        description="Test",
        runs=CompositeRuns(steps=[Step(run="echo", shell="bash")]),
    )
    yaml_str = action.to_yaml(include_header=False)
    assert "# This file is generated by ghagen" not in yaml_str
    assert yaml_str.startswith("name: Test")


def test_action_extras_merge() -> None:
    """Extras dict is merged into the serialized map."""
    action = Action(
        name="Test",
        description="desc",
        runs=CompositeRuns(steps=[Step(run="echo", shell="bash")]),
        extras={"x-custom": "value"},
    )
    cm = action.to_commented_map()
    assert cm["x-custom"] == "value"


def test_action_field_comments() -> None:
    """Field-level comments flow through to the emitted YAML."""
    from ghagen import with_comment

    action = Action(
        name="Commented",
        description="A commented action",
        runs=with_comment(
            CompositeRuns(steps=[Step(run="echo", shell="bash")]),
            "How the action executes",
        ),
    )
    yaml_str = action.to_yaml(include_header=False)
    assert "How the action executes" in yaml_str


def test_action_runs_commented_map_passthrough() -> None:
    """A raw ``CommentedMap`` in the ``runs`` slot is passed through."""
    raw_runs = CommentedMap()
    raw_runs["using"] = "composite"
    raw_runs["steps"] = [{"run": "echo raw", "shell": "bash"}]

    action = Action(
        name="Raw Runs",
        description="Uses a raw CommentedMap",
        runs=raw_runs,
    )
    cm = action.to_commented_map()
    assert cm["runs"]["using"] == "composite"
    assert cm["runs"]["steps"][0]["run"] == "echo raw"


def test_action_output_without_value() -> None:
    """Docker/JS action outputs omit ``value``."""
    action = Action(
        name="Docker",
        description="desc",
        outputs={
            "result": ActionOutput(description="The result"),
        },
        runs=DockerRuns(image="Dockerfile"),
    )
    cm = action.to_commented_map()
    output = cm["outputs"]["result"]
    assert output["description"] == "The result"
    assert "value" not in output


def test_composite_runs_defaults_to_composite_using() -> None:
    """``CompositeRuns()`` always emits ``using: composite``."""
    runs = CompositeRuns(steps=[Step(run="echo", shell="bash")])
    cm = runs.to_commented_map()
    assert cm["using"] == "composite"


def test_docker_runs_defaults_to_docker_using() -> None:
    """``DockerRuns(image=...)`` always emits ``using: docker``."""
    runs = DockerRuns(image="Dockerfile")
    cm = runs.to_commented_map()
    assert cm["using"] == "docker"
