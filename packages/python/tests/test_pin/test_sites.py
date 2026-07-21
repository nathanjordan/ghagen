"""Tests for ghagen.pin.sites — the UsesSite traversal policy.

These exercise the iterator and ``replace`` directly on constructed
Workflow/Action models — no App, no network.
"""

from __future__ import annotations

from ghagen._commented import is_commented, with_comment
from ghagen.models.action import Action, CompositeRuns, DockerRuns, NodeRuns
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.trigger import On, PushTrigger
from ghagen.models.workflow import Workflow
from ghagen.pin.sites import UsesSite, iter_uses_sites

SHA = "a" * 40


def _uses(document) -> list[str]:
    """The ``uses`` string of every site yielded for *document*."""
    return [site.uses for site in iter_uses_sites(document)]


class TestIterUsesSites:
    def test_nested_jobs_and_steps(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[
                        Step(uses="actions/checkout@v4"),
                        Step(uses="actions/setup-python@v5"),
                    ],
                ),
                "call": Job(uses="octo/repo/.github/workflows/ci.yml@v1"),
            },
        )
        assert set(_uses(wf)) == {
            "actions/checkout@v4",
            "actions/setup-python@v5",
            "octo/repo/.github/workflows/ci.yml@v1",
        }

    def test_step_site_carries_parsed_ref(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                )
            },
        )
        sites = list(iter_uses_sites(wf))
        assert len(sites) == 1
        site = sites[0]
        assert isinstance(site, UsesSite)
        assert site.uses == "actions/checkout@v4"
        assert site.ref.owner == "actions"
        assert site.ref.repo == "checkout"
        assert site.ref.ref == "v4"
        assert site.ref.is_pinnable

    def test_commented_wrapped_uses_is_seen_through(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[
                        Step(
                            uses=with_comment("actions/checkout@v4", "pin me"),
                        )
                    ],
                )
            },
        )
        sites = list(iter_uses_sites(wf))
        assert len(sites) == 1
        assert sites[0].uses == "actions/checkout@v4"
        assert sites[0].ref.is_pinnable

    def test_local_refs_yield_no_site(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="./local-action")],
                )
            },
        )
        assert list(iter_uses_sites(wf)) == []

    def test_docker_refs_yield_no_site(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="docker://node:18")],
                )
            },
        )
        assert list(iter_uses_sites(wf)) == []

    def test_run_step_yields_no_site(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(run="echo hi")],
                )
            },
        )
        assert list(iter_uses_sites(wf)) == []

    def test_already_sha_ref_yields_site_but_not_pinnable(self):
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses=f"actions/checkout@{SHA}")],
                )
            },
        )
        sites = list(iter_uses_sites(wf))
        assert len(sites) == 1
        assert sites[0].uses == f"actions/checkout@{SHA}"
        assert not sites[0].ref.is_pinnable

    def test_composite_action_runs_steps(self):
        action = Action(
            name="greet",
            description="say hi",
            runs=CompositeRuns(
                steps=[
                    Step(uses="actions/setup-python@v5"),
                    Step(run="echo hi", shell="bash"),
                    Step(uses="./local"),
                ],
            ),
        )
        assert _uses(action) == ["actions/setup-python@v5"]

    def test_docker_action_yields_no_site(self):
        action = Action(
            name="d",
            description="d",
            runs=DockerRuns(image="docker://alpine:3"),
        )
        assert list(iter_uses_sites(action)) == []

    def test_node_action_yields_no_site(self):
        action = Action(
            name="n",
            description="n",
            runs=NodeRuns(using="node20", main="dist/index.js"),
        )
        assert list(iter_uses_sites(action)) == []


class TestReplace:
    def test_replace_wraps_with_original_ref_eol_comment(self):
        step = Step(uses="actions/checkout@v4")
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={"build": Job(runs_on="ubuntu-latest", steps=[step])},
        )
        site = next(iter_uses_sites(wf))
        site.replace(site.ref.with_sha(SHA))

        assert is_commented(step.uses)
        assert step.uses.value == f"actions/checkout@{SHA}"
        assert step.uses.eol_comment == "v4"

    def test_replace_preserves_existing_block_comment(self):
        step = Step(uses=with_comment("actions/checkout@v4", "keep me"))
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={"build": Job(runs_on="ubuntu-latest", steps=[step])},
        )
        site = next(iter_uses_sites(wf))
        site.replace(site.ref.with_sha(SHA))

        assert is_commented(step.uses)
        assert step.uses.value == f"actions/checkout@{SHA}"
        assert step.uses.comment == "keep me"
        assert step.uses.eol_comment == "v4"

    def test_replace_round_trip_in_emitted_yaml(self):
        step = Step(uses=with_comment("actions/checkout@v4", "please pin"))
        wf = Workflow(
            name="CI",
            on=On(push=PushTrigger()),
            jobs={"build": Job(runs_on="ubuntu-latest", steps=[step])},
        )
        for site in iter_uses_sites(wf):
            site.replace(site.ref.with_sha(SHA))

        yaml = wf.to_yaml(header=None)
        assert f"actions/checkout@{SHA}" in yaml
        # The original ref is emitted as an end-of-line comment.
        assert "# v4" in yaml
        # The pre-existing block comment survives the replace.
        assert "# please pin" in yaml
