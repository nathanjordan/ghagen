"""Tests for the Document serialization seam (ADR-0001)."""

from ghagen import Action, Job, On, PushTrigger, Step, Workflow
from ghagen.models._base import Document
from ghagen.models.action import CompositeRuns
from ghagen.models.trigger import WorkflowDispatchTrigger


def test_workflow_and_action_are_documents():
    assert issubclass(Workflow, Document)
    assert issubclass(Action, Document)


def test_nested_models_are_not_documents():
    # Step and Job serialize for nesting but cannot be emitted to a file.
    assert not isinstance(Step(run="echo hi"), Document)
    assert not isinstance(Job(runs_on="ubuntu-latest"), Document)
    assert not hasattr(Step(run="echo hi"), "to_yaml")
    assert not hasattr(Job(runs_on="ubuntu-latest"), "to_yaml")


def test_document_to_yaml_still_works_via_method():
    wf = Workflow(name="CI", on=On(push=PushTrigger(branches=["main"])))
    out = wf.to_yaml(header=None)
    assert out.startswith("name: CI")


def test_action_to_yaml_still_works():
    action = Action(
        name="A",
        description="d",
        runs=CompositeRuns(steps=[Step(run="echo hi", shell="bash")]),
    )
    out = action.to_yaml(header=None)
    assert "name: A" in out
    assert "runs:" in out


def test_empty_workflow_dispatch_emits_present_null():
    # ADR-0002: normalized at construction, not via a serialize-time override.
    wf = Workflow(
        name="CI",
        on=On(workflow_dispatch=WorkflowDispatchTrigger()),
    )
    out = wf.to_yaml(header=None)
    assert "workflow_dispatch:\n" in out
    assert "workflow_dispatch: {}" not in out


def test_boolean_workflow_dispatch_unchanged():
    wf = Workflow(name="CI", on=On(workflow_dispatch=True))
    out = wf.to_yaml(header=None)
    assert "workflow_dispatch: true" in out
