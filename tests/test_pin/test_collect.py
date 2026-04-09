"""Tests for ghagen.pin.collect — extracting pinnable uses: refs."""

from __future__ import annotations

from ruamel.yaml.comments import CommentedMap

from ghagen.app import App
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
        assert refs == {"actions/checkout@v4"}

    def test_multiple_actions(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[
                        Step(uses="actions/checkout@v4"),
                        Step(uses="actions/setup-python@v5"),
                    ],
                )
            },
        )
        refs = collect_uses_refs(_make_app(wf))
        assert refs == {"actions/checkout@v4", "actions/setup-python@v5"}

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
        assert refs == set()

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
        assert refs == set()

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
        assert refs == set()

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
        assert refs == {"octo-org/repo/.github/workflows/ci.yml@v1"}

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
        assert refs == set()

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
        assert refs == set()
