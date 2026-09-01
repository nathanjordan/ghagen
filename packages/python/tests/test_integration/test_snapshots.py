"""Snapshot tests: compare generated YAML against stored expected output."""

from __future__ import annotations

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
    ImageSnapshot,
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
    with_comment,
    with_eol_comment,
)
from ghagen.models.common import PermissionLevel
from ghagen.models.job import Concurrency
from ghagen.models.trigger import WorkflowDispatchInput
from ghagen_schema.paths import EXPECTED_DIR

SNAPSHOT_DIR = EXPECTED_DIR


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

    snapshot.assert_match(wf.to_yaml(header=None), "ci_basic.yml")


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
                    Step(
                        name="Checkout",
                        uses="actions/checkout@v6",
                        with_={"fetch-depth": 1},
                    ),
                    Step(
                        name="Set up Python",
                        uses="actions/setup-python@v6",
                        with_={"python-version": "${{ matrix.python-version }}"},
                    ),
                    Step(name="Install deps", run="pip install -e '.[test]'"),
                    Step(name="Test", run="python -m pytest"),
                ],
            ),
        },
    )

    snapshot.assert_match(wf.to_yaml(header=None), "matrix_complex.yml")


def test_comments(snapshot: Snapshot):
    """Workflow with block, EOL, and field-level comments snapshot."""
    snapshot.snapshot_dir = SNAPSHOT_DIR

    wf = Workflow(
        name=with_comment("Commented Workflow", "The name shown in the GitHub UI"),
        on=with_eol_comment(
            On(
                push=PushTrigger(branches=["main"]),
                # An otherwise-empty sub-model carrying only its own comment.
                # `present_null_when_empty` discards the map; the comment folds
                # onto the bare key rather than vanishing with it. Bound here so
                # the two ports cannot resolve it differently.
                workflow_dispatch=WorkflowDispatchTrigger(comment="Run it by hand too"),
            ),
            "trigger configuration",
        ),
        jobs={
            "lint": Job(
                # A model comment and a field comment on the SAME key: the
                # model's own comment comes first (see attach_model_comment).
                name=with_comment("Lint", "Shown in the checks list"),
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
                needs=with_comment("lint", "Wait for lint to pass"),
                steps=[
                    Step(uses="actions/checkout@v4"),
                    Step(name="Pytest", run="python -m pytest"),
                ],
            ),
        },
    )

    snapshot.assert_match(wf.to_yaml(header=None), "comments.yml")


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

    snapshot.assert_match(wf.to_yaml(header=None), "multiline_run.yml")


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

    snapshot.assert_match(wf.to_yaml(header=None), "escape_hatches.yml")


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
                    Step(
                        name="Checkout",
                        uses="actions/checkout@v6",
                        with_={"fetch-depth": 1},
                    ),
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
                    Step(
                        name="Checkout",
                        uses="actions/checkout@v6",
                        with_={"fetch-depth": 1},
                    ),
                    Step(
                        name="Set up Python",
                        uses="actions/setup-python@v6",
                        with_={"python-version": "${{ matrix.python-version }}"},
                    ),
                    Step(name="Test", run="python -m pytest"),
                ],
            ),
            "container-test": Job(
                name="Container Test",
                runs_on="ubuntu-latest",
                needs="lint",
                container=Container(image="python:3.13"),
                snapshot=ImageSnapshot(image_name="custom-ubuntu", version="1.0"),
                services={
                    "db": Service(
                        image="postgres:16",
                        env={"POSTGRES_PASSWORD": "test"},
                        ports=[5432],
                    ),
                },
                steps=[
                    Step(
                        name="Checkout",
                        uses="actions/checkout@v6",
                        with_={"fetch-depth": 1},
                    ),
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

    snapshot.assert_match(wf.to_yaml(header=None), "full_featured.yml")


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

    snapshot.assert_match(action.to_yaml(header=None), "composite_action.yml")


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

    snapshot.assert_match(action.to_yaml(header=None), "docker_action.yml")


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

    snapshot.assert_match(action.to_yaml(header=None), "node_action.yml")


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
    snapshot.assert_match(wf.to_yaml(header=None), "triple_quoted_run.yml")


# --- Header goldens --------------------------------------------------------
#
# The cross-port byte oracle for ``format_header``. These six are read by hand
# rather than through pytest-snapshot because they are an *oracle* — the
# artefact that proves the two ports' headers agree byte-for-byte — not a
# regenerable snapshot of current behaviour. Peer:
# ``packages/typescript/src/integration/snapshots.test.ts``.


def _header_workflow(**kwargs: object) -> Workflow:
    """The one body every header golden shares: 10 lines, no comments."""
    return Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[Step(uses="actions/checkout@v4")],
            ),
        },
        **kwargs,  # type: ignore[arg-type]
    )


def _golden(name: str) -> str:
    return (SNAPSHOT_DIR / name).read_text()


def test_header_string_golden() -> None:
    """A string header sits immediately above the body — no blank line."""
    assert _header_workflow().to_yaml(header="Hand written") == _golden(
        "header_string.yml"
    )


def test_header_multiline_golden() -> None:
    """Blank source line renders a bare ``#``; one trailing break is dropped."""
    assert _header_workflow().to_yaml(header="line1\n\nline3\n") == _golden(
        "header_multiline.yml"
    )


def test_header_crlf_golden() -> None:
    """CRLF and a bare CR are both line breaks; no CR reaches the output."""
    out = _header_workflow().to_yaml(header="a\r\nb\rc")
    assert out == _golden("header_crlf.yml")
    assert "\r" not in out


def test_header_empty_golden() -> None:
    """``header=""`` is a header — a lone ``#`` — not a skip."""
    assert _header_workflow().to_yaml(header="") == _golden("header_empty.yml")


def test_header_closure_golden() -> None:
    """The closure branch wraps like the string branch; ``#`` survives verbatim."""
    assert _header_workflow().to_yaml(
        header=lambda v: f"built by {v['tool']} # verbatim"
    ) == _golden("header_closure.yml")


def test_header_doc_comment_golden() -> None:
    """The root Document comment sits directly under the header."""
    assert _header_workflow(comment="root doc comment").to_yaml(
        header="Hand written"
    ) == _golden("header_doc_comment.yml")
