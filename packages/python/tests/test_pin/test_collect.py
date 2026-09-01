"""Tests for ghagen.pin.collect — extracting pinnable uses: refs.

``collect_uses_refs`` returns parsed, deduplicated :class:`UsesRef`s sorted by
their full ref string (``UsesRef.uses``), not bare strings. Assertions compare
on ``[r.uses for r in refs]`` (the lockfile key) and, where the richer type
matters, on the parsed components the engine relies on.
"""

from __future__ import annotations

from ruamel.yaml.comments import CommentedMap

from ghagen.app import App
from ghagen.models.action import Action, CompositeRuns, DockerRuns, NodeRuns
from ghagen.models.common import ShellType
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.trigger import On, PushTrigger
from ghagen.models.workflow import Workflow
from ghagen.pin.collect import collect_uses_refs


def _make_app(*workflows: Workflow) -> App:
    app = App(lockfile=None)
    for i, wf in enumerate(workflows):
        app.add_workflow(wf, f"wf{i}.yml")
    return app


class TestCollectUsesRefs:
    def test_basic_action(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                )
            },
        )
        refs = collect_uses_refs(_make_app(wf))
        assert [r.uses for r in refs] == ["actions/checkout@v4"]
        # The parsed components the engine relies on travel with the ref.
        assert refs[0].owner == "actions"
        assert refs[0].repo == "checkout"
        assert refs[0].ref == "v4"

    def test_multiple_actions(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[
                        Step(uses="actions/setup-python@v5"),
                        Step(uses="actions/checkout@v4"),
                    ],
                )
            },
        )
        refs = collect_uses_refs(_make_app(wf))
        # Sorted by full ref string, regardless of authored order.
        assert [r.uses for r in refs] == [
            "actions/checkout@v4",
            "actions/setup-python@v5",
        ]

    def test_deduplicates(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "a": Job(
                    runs_on="ubuntu-latest", steps=[Step(uses="actions/checkout@v4")]
                ),
                "b": Job(
                    runs_on="ubuntu-latest", steps=[Step(uses="actions/checkout@v4")]
                ),
            },
        )
        refs = collect_uses_refs(_make_app(wf))
        assert len(refs) == 1
        assert refs[0].uses == "actions/checkout@v4"

    def test_distinct_refs_stay_separate(self):
        """Same repo, different ref components do not collapse."""
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "a": Job(
                    runs_on="ubuntu-latest", steps=[Step(uses="actions/checkout@v4")]
                ),
                "b": Job(
                    runs_on="ubuntu-latest", steps=[Step(uses="actions/checkout@v5")]
                ),
            },
        )
        refs = collect_uses_refs(_make_app(wf))
        assert [r.uses for r in refs] == [
            "actions/checkout@v4",
            "actions/checkout@v5",
        ]

    def test_skips_local(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="./local-action")],
                )
            },
        )
        refs = collect_uses_refs(_make_app(wf))
        assert refs == []

    def test_skips_docker(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="docker://node:18")],
                )
            },
        )
        refs = collect_uses_refs(_make_app(wf))
        assert refs == []

    def test_skips_already_sha_pinned(self):
        sha = "a" * 40
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses=f"actions/checkout@{sha}")],
                )
            },
        )
        refs = collect_uses_refs(_make_app(wf))
        assert refs == []

    def test_job_uses_reusable_workflow(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "call": Job(
                    uses="octo-org/repo/.github/workflows/ci.yml@v1",
                )
            },
        )
        refs = collect_uses_refs(_make_app(wf))
        assert [r.uses for r in refs] == ["octo-org/repo/.github/workflows/ci.yml@v1"]
        # A pathful reusable-workflow ref keeps its path component.
        assert refs[0].path == ".github/workflows/ci.yml"
        assert refs[0].ref == "v1"

    def test_skips_run_steps(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(run="echo hello")],
                )
            },
        )
        refs = collect_uses_refs(_make_app(wf))
        assert refs == []

    def test_skips_commented_map_steps(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[CommentedMap({"uses": "actions/checkout@v4", "with": {}})],
                )
            },
        )
        refs = collect_uses_refs(_make_app(wf))
        assert refs == []


class TestCollectFromActions:
    """Composite action steps should be collected just like workflow steps."""

    def test_composite_action_steps_collected(self):
        action = Action(
            name="greet",
            description="say hi",
            runs=CompositeRuns(
                steps=[
                    Step(uses="actions/setup-python@v5"),
                    Step(uses="actions/checkout@v4"),
                    Step(run="echo hi", shell=ShellType.BASH),
                ],
            ),
        )
        app = App(lockfile=None)
        app.add_action(action)
        refs = collect_uses_refs(app)
        assert [r.uses for r in refs] == [
            "actions/checkout@v4",
            "actions/setup-python@v5",
        ]

    def test_composite_action_skips_local_and_docker(self):
        action = Action(
            name="greet",
            description="say hi",
            runs=CompositeRuns(
                steps=[
                    Step(uses="./local-step"),
                    Step(uses="docker://alpine:3"),
                ],
            ),
        )
        app = App(lockfile=None)
        app.add_action(action)
        refs = collect_uses_refs(app)
        assert refs == []

    def test_docker_action_runs_not_scanned(self):
        """DockerRuns has no pinnable refs — ``image`` is a docker:// URL."""
        action = Action(
            name="docker-action",
            description="runs in a container",
            runs=DockerRuns(image="docker://alpine:3"),
        )
        app = App(lockfile=None)
        app.add_action(action)
        refs = collect_uses_refs(app)
        assert refs == []

    def test_node_action_runs_not_scanned(self):
        """NodeRuns has no pinnable refs — ``main`` is a JS entrypoint path."""
        action = Action(
            name="node-action",
            description="runs node",
            runs=NodeRuns(using="node20", main="dist/index.js"),
        )
        app = App(lockfile=None)
        app.add_action(action)
        refs = collect_uses_refs(app)
        assert refs == []

    def test_workflow_and_action_refs_merge(self):
        """Refs from workflows and actions deduplicate into one sorted list."""
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                )
            },
        )
        action = Action(
            name="a",
            description="d",
            runs=CompositeRuns(
                steps=[
                    Step(uses="actions/checkout@v4"),  # duplicate
                    Step(uses="actions/setup-python@v5"),
                ],
            ),
        )
        app = App(lockfile=None)
        app.add_workflow(wf, "ci.yml")
        app.add_action(action)
        refs = collect_uses_refs(app)
        assert [r.uses for r in refs] == [
            "actions/checkout@v4",
            "actions/setup-python@v5",
        ]
