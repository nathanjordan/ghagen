"""The one binding from each emitted fixture in ``fixtures/expected/`` to the
model that produces it.

Three consumers read this list, and they must read the *same* one:

- :mod:`tests.test_integration.test_snapshots` — the byte oracle. Emits each
  document and compares it to its fixture file, byte for byte, against the
  TypeScript port doing the same.
- :mod:`tests.test_integration.test_docs_snippets` — the other half of the
  docs' emitted-output oracle; the guides' YAML is produced by the TypeScript
  port at docs-build time and pinned to the same ``docs_*.yml`` files.
- :mod:`tests.test_integration.test_to_data_sweep` — the walk oracle. Asserts
  ``parse(to_yaml(doc)) == to_data(doc)`` for every document here, so a
  divergence between the Emitter's two renderings fails on real documents
  rather than on one curated one (``docs/issues/01``).

Keeping the models here rather than inline in any of the three is what makes
the sweep a sweep over the *oracle's* documents instead of a second hand-built
registry that could quietly cover less.

Peer: ``packages/typescript/src/integration/fixture-models.ts``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

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
from ghagen.emitter.header import HeaderInput
from ghagen.models._base import Document
from ghagen.models.common import PermissionLevel, ShellType
from ghagen.models.job import Concurrency, Defaults, DefaultsRun
from ghagen.models.trigger import (
    WorkflowCallInput,
    WorkflowCallOutput,
    WorkflowCallSecret,
    WorkflowCallTrigger,
    WorkflowDispatchInput,
)


@dataclass(frozen=True)
class FixtureDoc:
    """One fixture document: the file it pins, why it exists, how to build it.

    Attributes:
        fixture: File name under ``fixtures/expected/``.
        why: What this document is the oracle for.
        build: Builds a fresh model. A factory, not a value, so no two readers
            share one.
        header: The ``header`` argument its oracle was taken with. Explicit
            rather than defaulted to the ``DEFAULT`` sentinel: no fixture wants
            ghagen's default header, and stating ``None`` here says so at the
            binding rather than at each call site.
        post_process_root_keys: Root keys this document's ``post_process`` hook
            adds to the emitted YAML. ``post_process`` operates on the backend
            node, so it runs in ``to_yaml`` and, by contract, never in
            ``to_data``. That is a declared difference between the two
            renderings, not a divergence in the walk they share, so the walk
            sweep subtracts these keys from the parsed YAML before comparing —
            and asserts each one was actually there, so the subtraction cannot
            silently paper over a real difference.
    """

    fixture: str
    why: str
    build: Callable[[], Document]
    header: HeaderInput = None
    post_process_root_keys: tuple[str, ...] = ()

    def render(self) -> str:
        """Emit this document exactly as its oracle was taken."""
        return self.build().to_yaml(self.header)


def _build_job() -> Job:
    """The filler job the field-level comment examples hang a workflow off.

    Shared so that the annotated field is the only thing that varies between
    them, and so the guides' snippets can stay short enough to read.
    """
    return Job(runs_on="ubuntu-latest", steps=[Step(run="make")])


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


def _ci_basic() -> Workflow:
    return Workflow(
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


def _matrix_complex() -> Workflow:
    return Workflow(
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


def _comments() -> Workflow:
    return Workflow(
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


def _multiline_run() -> Workflow:
    return Workflow(
        name="Multiline",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "test": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(uses="actions/checkout@v4"),
                    Step(name="Tests", run="python -m pytest\ncoverage report\n"),
                    Step(name="Inline", run="echo single-line"),
                    Step(name="Strip", run="echo one\necho two"),
                ],
            ),
        },
    )


def _escape_hatches() -> Workflow:
    def add_annotation(cm: CommentedMap) -> None:
        cm["x-generated-by"] = "ghagen"

    cm_job = CommentedMap()
    cm_job["runs-on"] = "ubuntu-latest"
    cm_job["steps"] = [{"run": "echo 'raw job'"}]

    return Workflow(
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
                snapshot=ImageSnapshot(
                    image_name="custom-image", version=Raw("latest")
                ),
                extras={"custom-timeout": 30},
            ),
            "raw": cm_job,
        },
    )


def _full_featured() -> Workflow:
    return Workflow(
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


def _composite_action() -> Action:
    return Action(
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
                    shell=ShellType.BASH,
                ),
            ],
        ),
    )


def _docker_action() -> Action:
    return Action(
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


def _node_action() -> Action:
    return Action(
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


def _triple_quoted_run() -> Workflow:
    return Workflow(
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


def _body_shapes() -> Workflow:
    return Workflow(
        name="Body Shapes",
        on=On(
            # Present-null on a key the old one-element allowlist did not cover.
            create={},
            push=PushTrigger(branches=["main"]),
            workflow_call=WorkflowCallTrigger(
                inputs={
                    "environment": WorkflowCallInput(
                        description="Target environment",
                        required=True,
                        type="string",
                    ),
                },
                outputs={
                    "digest": WorkflowCallOutput(
                        description="Digest of the image this run built",
                        value="${{ jobs.build.outputs.digest }}",
                    ),
                },
                secrets={
                    "deploy-token": WorkflowCallSecret(
                        description="Token the deploy step authenticates with",
                        required=True,
                    ),
                },
            ),
            # Present-null on the key the rule started with.
            workflow_dispatch=WorkflowDispatchTrigger(),
            # An event GitHub ships ahead of the Snapshot: untyped, so it can
            # only arrive through extras, and it sorts between `create` and
            # `push`.
            extras={"pull_request_review_thread": {"types": ["resolved"]}},
        ),
        defaults=Defaults(run=DefaultsRun(shell="bash", working_directory="src")),
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                defaults=Defaults(run=DefaultsRun(working_directory="build")),
                outputs={"digest": "${{ steps.build.outputs.digest }}"},
                steps=[
                    Step(
                        name="Checkout",
                        uses=with_eol_comment(
                            "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
                            "v4.2.2",
                        ),
                    ),
                    Step(
                        name="Set up Python",
                        uses="actions/setup-python@0b93645e9fea7318ecaed2b359559ac225c90a2b",
                    ),
                    Step(
                        id="build",
                        name="Build",
                        run='echo "digest=sha256:deadbeef" >> "$GITHUB_OUTPUT"',
                    ),
                ],
            ),
        },
    )


#: The workflow and action shapes somebody wrote for their own sake.
SNAPSHOT_DOCS: tuple[FixtureDoc, ...] = (
    FixtureDoc("ci_basic.yml", "Minimal CI workflow.", _ci_basic),
    FixtureDoc(
        "matrix_complex.yml", "Multi-axis matrix with exclude.", _matrix_complex
    ),
    FixtureDoc(
        "comments.yml",
        "Workflow with block, EOL, and field-level comments.",
        _comments,
    ),
    FixtureDoc(
        "multiline_run.yml",
        "Multi-line run commands render as YAML literal block scalars.",
        _multiline_run,
    ),
    FixtureDoc(
        "escape_hatches.yml",
        "All four escape hatches in one workflow. Also the byte oracle for a "
        "``Raw`` ``ImageSnapshot.version`` (issue 22): ``'latest'`` fails the "
        "field's own grammar (``^\\d+(\\.\\d+|\\*)?$``), so accepting it here "
        "proves ``Raw`` bypasses the check rather than merely happening to "
        "match it, and pins what a ``Raw`` value emits -- a plain scalar, "
        "exactly like an ordinary string -- since ``Raw`` values reach the "
        "emitter by a different path (``ghagen._raw.raw_scalar`` / "
        "``emitter.nodes.unwrap_raw``) than plain strings do.",
        _escape_hatches,
        post_process_root_keys=("x-generated-by",),
    ),
    FixtureDoc(
        "full_featured.yml",
        "Comprehensive workflow exercising all model types.",
        _full_featured,
    ),
    FixtureDoc("composite_action.yml", "Composite action.", _composite_action),
    FixtureDoc("docker_action.yml", "Docker action.", _docker_action),
    FixtureDoc("node_action.yml", "Node.js action.", _node_action),
    FixtureDoc(
        "triple_quoted_run.yml",
        "Triple-quoted run strings produce identical YAML to \\n-concatenated "
        "style. Similar to multiline_run.yml but uses |- (strip) instead of | "
        "(clip) because dedent_script strips the artifact trailing newline "
        "triple quotes leave behind.",
        _triple_quoted_run,
    ),
    FixtureDoc(
        "body_shapes.yml",
        "The five body shapes the byte oracle had no bytes for "
        "(docs/issues/02). Every other fixture in this directory is a workflow "
        "shape somebody wrote for its own sake; this one exists because the "
        "*oracle* had holes, and each hole is a path the ports could have "
        "diverged on with both suites green: (1) ``defaults:`` at the workflow "
        "level and again inside a job, so the one Defaults/DefaultsRun pair is "
        "byte-bound at both of the two places the schema allows it; "
        "(2) present-null -- ``workflow_dispatch:`` (the rule's original single "
        "member) and ``create:`` (one of the 34 keys docs/issues/04 widened it "
        "to), both of which must be bare keys and neither of which may be "
        "``{}``; (3) a dynamic extras interleave on an alphabetical spec -- "
        "``pull_request_review_thread`` is a real GitHub event the canonical "
        "Snapshot's ``on:`` map does not declare, so it cannot be a typed field "
        "(the conformance sweep asserts ``On`` covers exactly what the Snapshot "
        "declares) and must travel through ``extras``; it sorts strictly "
        "between two typed keys, ``create`` and ``push``, so a port that "
        "appended extras instead of interleaving them produces different bytes "
        "here; (4) SHA-pinned ``uses:`` -- a bare 40-hex ref, and the "
        "``# vX.Y.Z`` end-of-line spelling that pinning tools actually emit; "
        "(5) ``workflow_call:`` with inputs, outputs and secrets -- no file "
        "under ``fixtures/expected/`` contained ``workflow_call`` at all before "
        "this one, so the canonical key order of the three sub-map defs (bound "
        "per-port by unit tests) had no shared oracle.",
        _body_shapes,
    ),
)

#: The cross-port byte oracle for ``format_header``.
#:
#: These six are read by hand rather than through pytest-snapshot because they
#: are an *oracle* -- the artefact that proves the two ports' headers agree
#: byte-for-byte -- not a regenerable snapshot of current behaviour. They all
#: share one 10-line body, so the walk sweep learns little new from five of
#: them; they are fixture documents all the same, and leaving them out would be
#: shrinking the set rather than sweeping it.
HEADER_GOLDENS: tuple[FixtureDoc, ...] = (
    FixtureDoc(
        "header_string.yml",
        "A string header sits immediately above the body -- no blank line.",
        _header_workflow,
        header="Hand written",
    ),
    FixtureDoc(
        "header_multiline.yml",
        "Blank source line renders a bare ``#``; one trailing break is dropped.",
        _header_workflow,
        header="line1\n\nline3\n",
    ),
    FixtureDoc(
        "header_crlf.yml",
        "CRLF and a bare CR are both line breaks; no CR reaches the output.",
        _header_workflow,
        header="a\r\nb\rc",
    ),
    FixtureDoc(
        "header_empty.yml",
        '``header=""`` is a header -- a lone ``#`` -- not a skip.',
        _header_workflow,
        header="",
    ),
    FixtureDoc(
        "header_closure.yml",
        "The closure branch wraps like the string branch; ``#`` survives verbatim.",
        _header_workflow,
        header=lambda v: f"built by {v['tool']} # verbatim",
    ),
    FixtureDoc(
        "header_doc_comment.yml",
        "The root Document comment sits directly under the header.",
        lambda: _header_workflow(comment="root doc comment"),
        header="Hand written",
    ),
)

#: The documents the guides show, pinned to ``fixtures/expected/docs_*.yml``.
#:
#: The guides' YAML is produced by running the TypeScript emitter at docs-build
#: time (``docs/src/snippets/emitted.ts``); these are the mirrored Python models
#: that byte-compare against the same files, so a cross-port divergence in
#: anything the guides show fails one side or the other. The snippets in the
#: guides' Python tabs are these models -- keep the two in step.
DOCS_SNIPPET_DOCS: tuple[FixtureDoc, ...] = (
    FixtureDoc(
        "docs_quickstart.yml",
        '``index.mdx`` -- "ghagen generates clean, readable YAML".',
        _ci_basic,
    ),
    FixtureDoc(
        "docs_comment_block.yml",
        '``guides/comments.mdx`` -- "Block comments".',
        lambda: Workflow(
            name="CI",
            on=On(push=PushTrigger(branches=["main"])),
            jobs={
                "test": Job(
                    name="Test",
                    runs_on="ubuntu-latest",
                    comment=(
                        "Run the full test suite against all supported Python versions"
                    ),
                    steps=[Step(run="pytest")],
                ),
            },
        ),
    ),
    FixtureDoc(
        "docs_comment_eol.yml",
        '``guides/comments.mdx`` -- "End-of-line comments".',
        lambda: Workflow(
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
        ),
    ),
    FixtureDoc(
        "docs_comment_field_block.yml",
        '``guides/comments.mdx`` -- "Field-level block comments".',
        lambda: Workflow(
            name=with_comment("CI", "The name shown in the GitHub UI"),
            on=On(push=PushTrigger(branches=["main"])),
            jobs={"build": _build_job()},
        ),
    ),
    FixtureDoc(
        "docs_comment_field_eol.yml",
        '``guides/comments.mdx`` -- "Field-level EOL comments".',
        lambda: Workflow(
            name="CI",
            on=with_eol_comment(
                On(push=PushTrigger(branches=["main"])), "trigger configuration"
            ),
            jobs={"build": _build_job()},
        ),
    ),
    FixtureDoc(
        "docs_comment_full.yml",
        '``guides/comments.mdx`` -- "Full example", all four comment kinds.',
        lambda: Workflow(
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
        ),
    ),
    FixtureDoc(
        "docs_header_verbatim.yml",
        "``guides/comments.mdx`` -- a string header sitting straight on the body.",
        lambda: Workflow(
            name="CI",
            on=On(push=PushTrigger(branches=["main"])),
            jobs={"build": _build_job()},
        ),
        header="Hand written",
    ),
    FixtureDoc(
        "docs_extras.yml",
        '``guides/escape-hatches.mdx`` -- "extras".',
        lambda: Workflow(
            name="Extras",
            on=On(push=PushTrigger(branches=["main"])),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    extras={"timeout-minutes": 30, "continue-on-error": True},
                ),
            },
        ),
    ),
)

#: Fixture files under ``fixtures/expected/`` that are not emitter documents at
#: all, so no model produces them and the sweep is not shrinking by leaving them
#: out. The lockfile goldens come from the pin lockfile serializer, not the
#: model emitter.
NON_DOCUMENT_FIXTURES: frozenset[str] = frozenset(
    {
        "lockfile_golden.yml",
        "lockfile_key_quoting.yml",
        "lockfile_space_separator_rejected.yml",
    }
)

#: Fixture documents with no static source model to bind.
#:
#: ``init_scaffold.yml`` is what ``ghagen init``'s template emits, so its source
#: is the scaffold the CLI writes at test time. It is swept where it is built,
#: in ``tests/test_cli/test_init_scaffold.py``.
UNBOUND_DOC_FIXTURES: frozenset[str] = frozenset({"init_scaffold.yml"})

#: Every fixture document this suite can build a model for.
ALL_FIXTURE_DOCS: tuple[FixtureDoc, ...] = (
    *SNAPSHOT_DOCS,
    *HEADER_GOLDENS,
    *DOCS_SNIPPET_DOCS,
)
