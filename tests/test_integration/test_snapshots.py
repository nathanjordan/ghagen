"""Snapshot tests: compare generated YAML against stored expected output."""

from __future__ import annotations

from pathlib import Path

from pytest_snapshot.plugin import Snapshot
from ruamel.yaml.comments import CommentedMap

from ghagen import (
    Action,
    ActionInput,
    ActionOutput,
    Branding,
    CompositeRuns,
    Container,
    DockerRuns,
    Job,
    Matrix,
    NodeRuns,
    On,
    Permissions,
    PRTrigger,
    PushTrigger,
    Raw,
    ScheduleTrigger,
    Service,
    Step,
    Strategy,
    Workflow,
    WorkflowDispatchTrigger,
    checkout,
    setup_python,
)
from ghagen.models.common import PermissionLevel
from ghagen.models.job import Concurrency
from ghagen.models.trigger import WorkflowDispatchInput

SNAPSHOT_DIR = Path(__file__).parent.parent / "snapshots"


def test_ci_basic(snapshot: Snapshot):
    """Minimal CI workflow snapshot."""
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
                    Step(
                        name="Run tests",
                        run="python -m pytest",
                    ),
                ],
            ),
        },
    )

    snapshot.assert_match(wf.to_yaml(include_header=False), "ci_basic.yml")


def test_matrix_complex(snapshot: Snapshot):
    """Multi-axis matrix with exclude snapshot."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name="Matrix CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "test": Job(
                name="Test (${{ matrix.python-version }}, ${{ matrix.os }})",
                runs_on=Raw("${{ matrix.os }}"),
                strategy=Strategy(
                    matrix=Matrix(
                        extras={
                            "python-version": ["3.11", "3.12", "3.13"],
                            "os": ["ubuntu-latest", "macos-latest", "windows-latest"],
                        },
                        exclude=[
                            {"os": "windows-latest", "python-version": "3.11"},
                        ],
                    ),
                    fail_fast=False,
                ),
                steps=[
                    checkout(),
                    setup_python(
                        version="${{ matrix.python-version }}",
                    ),
                    Step(name="Install deps", run="pip install -e '.[test]'"),
                    Step(name="Test", run="python -m pytest"),
                ],
            ),
        },
    )

    snapshot.assert_match(wf.to_yaml(include_header=False), "matrix_complex.yml")


def test_comments(snapshot: Snapshot):
    """Workflow with block, EOL, and field-level comments snapshot."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name="Commented Workflow",
        on=On(
            push=PushTrigger(branches=["main"]),
        ),
        field_comments={
            "name": "The name shown in the GitHub UI",
        },
        field_eol_comments={
            "on": "trigger configuration",
        },
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
            "test": Job(
                name="Test",
                runs_on="ubuntu-latest",
                needs="lint",
                field_comments={"needs": "Wait for lint to pass"},
                steps=[
                    Step(uses="actions/checkout@v4"),
                    Step(name="Pytest", run="python -m pytest"),
                ],
            ),
        },
    )

    snapshot.assert_match(wf.to_yaml(include_header=False), "comments.yml")


def test_multiline_run(snapshot: Snapshot):
    """Multi-line run commands render as YAML literal block scalars."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name="Multiline",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "test": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(uses="actions/checkout@v4"),
                    Step(
                        name="Tests",
                        run="python -m pytest\ncoverage report\n",
                    ),
                    Step(
                        name="Inline",
                        run="echo single-line",
                    ),
                    Step(
                        name="Strip",
                        run="echo one\necho two",
                    ),
                ],
            ),
        },
    )

    snapshot.assert_match(wf.to_yaml(include_header=False), "multiline_run.yml")


def test_escape_hatches(snapshot: Snapshot):
    """All four escape hatches in one workflow snapshot."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    def add_annotation(cm: CommentedMap) -> None:
        cm["x-generated-by"] = "ghagen"

    cm_job = CommentedMap()
    cm_job["runs-on"] = "ubuntu-latest"
    cm_job["steps"] = [{"run": "echo 'raw job'"}]

    wf = Workflow(
        name="Escape Hatches",
        on=On(push=PushTrigger(branches=["main"])),
        post_process=add_annotation,
        jobs={
            "typed": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(
                        name="Custom shell",
                        run="echo hello",
                        shell=Raw("custom-shell"),
                    ),
                ],
                extras={"custom-timeout": 30},
            ),
            "raw": cm_job,
        },
    )

    snapshot.assert_match(wf.to_yaml(include_header=False), "escape_hatches.yml")


def test_full_featured(snapshot: Snapshot):
    """Comprehensive workflow exercising all model types snapshot."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name="Full Featured",
        on=On(
            push=PushTrigger(branches=["main"], tags=["v*"]),
            pull_request=PRTrigger(branches=["main"]),
            schedule=[ScheduleTrigger(cron="0 0 * * 0")],
            workflow_dispatch=WorkflowDispatchTrigger(
                inputs={
                    "target": WorkflowDispatchInput(
                        description="Deploy target",
                        required=True,
                        type="string",
                    ),
                },
            ),
        ),
        permissions=Permissions(
            contents=PermissionLevel.READ,
            pull_requests=PermissionLevel.WRITE,
        ),
        env={"CI": "true"},
        concurrency=Concurrency(
            group="${{ github.workflow }}-${{ github.ref }}",
            cancel_in_progress=True,
        ),
        jobs={
            "lint": Job(
                name="Lint",
                runs_on="ubuntu-latest",
                steps=[
                    checkout(),
                    Step(name="Ruff", run="ruff check ."),
                ],
            ),
            "test": Job(
                name="Test",
                runs_on="ubuntu-latest",
                needs="lint",
                strategy=Strategy(
                    matrix=Matrix(
                        extras={"python-version": ["3.11", "3.12", "3.13"]},
                    ),
                ),
                steps=[
                    checkout(),
                    setup_python(version="${{ matrix.python-version }}"),
                    Step(name="Test", run="python -m pytest"),
                ],
            ),
            "container-test": Job(
                name="Container Test",
                runs_on="ubuntu-latest",
                needs="lint",
                container=Container(image="python:3.13"),
                services={
                    "db": Service(
                        image="postgres:16",
                        env={"POSTGRES_PASSWORD": "test"},
                        ports=[5432],
                    ),
                },
                steps=[
                    checkout(),
                    Step(name="Test with DB", run="python -m pytest --db"),
                ],
            ),
            "deploy": Job(
                uses="octo-org/deploy/.github/workflows/deploy.yml@main",
                needs=["test", "container-test"],
                with_={"environment": "production"},
                secrets="inherit",
            ),
        },
    )

    snapshot.assert_match(wf.to_yaml(include_header=False), "full_featured.yml")


def test_composite_action_snapshot(snapshot: Snapshot):
    """Composite action YAML snapshot."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    action = Action(
        name="Greet",
        description="Say hello to someone",
        author="ghagen",
        branding=Branding(icon="heart", color="purple"),
        inputs={
            "who": ActionInput(
                description="Who to greet",
                required=True,
                default="world",
            ),
            "shout": ActionInput(
                description="Uppercase the greeting",
                required=False,
                default="false",
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
                    run="echo Hello, ${{ inputs.who }}",
                    shell="bash",
                ),
            ],
        ),
    )

    snapshot.assert_match(action.to_yaml(include_header=False), "composite_action.yml")


def test_docker_action_snapshot(snapshot: Snapshot):
    """Docker action YAML snapshot."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    action = Action(
        name="Docker Greet",
        description="Greet inside a container",
        branding=Branding(icon="box", color="blue"),
        inputs={
            "who": ActionInput(description="Who to greet", default="world"),
        },
        outputs={
            "time": ActionOutput(description="Time the action ran"),
        },
        runs=DockerRuns(
            image="Dockerfile",
            env={"GREETING": "Hello"},
            args=["${{ inputs.who }}"],
            entrypoint="entrypoint.sh",
            post_entrypoint="cleanup.sh",
            post_if="always()",
        ),
    )

    snapshot.assert_match(action.to_yaml(include_header=False), "docker_action.yml")


def test_node_action_snapshot(snapshot: Snapshot):
    """Node.js action YAML snapshot."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    action = Action(
        name="Node Greet",
        description="Greet from a Node script",
        branding=Branding(icon="code", color="yellow"),
        inputs={
            "who": ActionInput(description="Who to greet", default="world"),
        },
        outputs={
            "message": ActionOutput(description="The greeting"),
        },
        runs=NodeRuns(
            using="node20",
            main="dist/index.js",
            pre="dist/setup.js",
            post="dist/cleanup.js",
            post_if="always()",
        ),
    )

    snapshot.assert_match(action.to_yaml(include_header=False), "node_action.yml")


def test_triple_quoted_run(snapshot: Snapshot):
    """Triple-quoted run strings produce identical YAML to \\n-concatenated style."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name="Multiline",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "test": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(uses="actions/checkout@v4"),
                    Step(
                        name="Tests",
                        run="""
                            python -m pytest
                            coverage report
                        """,
                    ),
                    Step(
                        name="Inline",
                        run="echo single-line",
                    ),
                    Step(
                        name="Strip",
                        run="""
                            echo one
                            echo two
                        """,
                    ),
                ],
            ),
        },
    )

    # Similar to multiline_run.yml but uses |- (strip) instead of | (clip)
    # because dedent_script strips the artifact trailing \n from triple quotes.
    snapshot.assert_match(
        wf.to_yaml(include_header=False), "triple_quoted_run.yml"
    )
