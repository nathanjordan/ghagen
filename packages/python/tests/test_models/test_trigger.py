"""Acceptance + rejection guards for the Python trigger/permission surface.

Every field exercised here is a schema-declared property that the Python port
did not model, while the TypeScript port either did or (for the last two `on:`
events) declared it unreachable too. With ``extra="forbid"`` on
:class:`~ghagen.models._base.GhagenModel` these were not silent no-ops but hard
Pydantic ``ValidationError``\\ s, so the identical program was valid TypeScript
and a construction-time error in Python.

Each field gets a *pair*: the field is accepted and reaches ``to_data`` under
the right YAML key, and a neighbouring misspelling is still rejected. The
rejection half keeps the unknown-key contract visibly intact rather than
widened away -- under the ``extras=`` escape hatch a typo is indistinguishable
from a real event, which is exactly why modelling the fields beats routing them
through extras.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ghagen.emitter import to_data
from ghagen.models.common import PermissionLevel
from ghagen.models.job import Environment
from ghagen.models.permissions import Permissions
from ghagen.models.trigger import (
    On,
    PRTrigger,
    ScheduleTrigger,
    WorkflowDispatchInput,
)

# (field name, constructor kwargs, emitted YAML key) for every `on:` event the
# schema declares that this port did not model.
ON_EVENTS = [
    ("branch_protection_rule", {}, "branch_protection_rule"),
    ("discussion", {}, "discussion"),
    ("discussion_comment", {}, "discussion_comment"),
    ("gollum", {}, "gollum"),
    ("merge_group", {"types": ["checks_requested"]}, "merge_group"),
    ("pull_request_review", {"types": ["submitted"]}, "pull_request_review"),
    (
        "pull_request_review_comment",
        {"types": ["created"]},
        "pull_request_review_comment",
    ),
    ("repository_dispatch", {"types": ["deploy"]}, "repository_dispatch"),
]


@pytest.mark.parametrize(
    ("field", "value", "yaml_key"), ON_EVENTS, ids=[f for f, _, _ in ON_EVENTS]
)
def test_on_event_is_accepted(
    field: str, value: dict[str, object], yaml_key: str
) -> None:
    """The event constructs and emits under its schema-declared key."""
    # A `**dict[str, object]` splat has no static shape, so pyright checks it
    # against every keyword of `On.__init__` at once. The table is the point of
    # this test; the splat is how it is driven.
    data = to_data(On(**{field: value}))  # type: ignore[arg-type]
    assert data[yaml_key] == value


@pytest.mark.parametrize("field", [f for f, _, _ in ON_EVENTS])
def test_on_event_misspelling_is_rejected(field: str) -> None:
    """A neighbouring typo still raises -- the unknown-key contract is intact."""
    typo = field.replace("_", "", 1) if "_" in field else field[:-1]
    with pytest.raises(ValidationError):
        On(**{typo: {}})  # type: ignore[arg-type]  # splat; see above


def test_pr_trigger_tags_are_accepted() -> None:
    """`pull_request` declares `tags`/`tags-ignore`; only `PushTrigger` had them."""
    data = to_data(PRTrigger(tags=["v*"], tags_ignore=["v0.*"]))
    assert data["tags"] == ["v*"]
    assert data["tags-ignore"] == ["v0.*"]


def test_pr_trigger_tag_misspelling_is_rejected() -> None:
    with pytest.raises(ValidationError):
        # Deliberately misspelled. pyright rejects it too, which is not the
        # contract under test: this pins the *runtime* `extra="forbid"`, which
        # is what catches the same typo written through a splat or a dict.
        PRTrigger(tag=["v*"])  # type: ignore[call-arg]


def test_schedule_trigger_timezone_is_accepted() -> None:
    data = to_data(ScheduleTrigger(cron="0 0 * * *", timezone="UTC"))
    assert data == {"cron": "0 0 * * *", "timezone": "UTC"}


def test_schedule_trigger_timezone_misspelling_is_rejected() -> None:
    with pytest.raises(ValidationError):
        # Deliberately misspelled -- runtime rejection is the contract.
        ScheduleTrigger(cron="0 0 * * *", time_zone="UTC")  # type: ignore[call-arg]


def test_workflow_dispatch_input_deprecation_message_is_accepted() -> None:
    """The schema key is camelCase `deprecationMessage`, unlike its siblings."""
    data = to_data(WorkflowDispatchInput(description="d", deprecation_message="use x"))
    assert data["deprecationMessage"] == "use x"


def test_workflow_dispatch_input_deprecation_misspelling_is_rejected() -> None:
    with pytest.raises(ValidationError):
        # Deliberately misspelled -- runtime rejection is the contract.
        WorkflowDispatchInput(deprecationMessage="use x")  # type: ignore[call-arg]


def test_new_permission_scopes_are_accepted() -> None:
    """Three scopes GitHub ships that neither port exposed."""
    data = to_data(
        Permissions(
            artifact_metadata=PermissionLevel.READ,
            attestations=PermissionLevel.WRITE,
            models=PermissionLevel.READ,
        )
    )
    assert data == {
        "artifact-metadata": "read",
        "attestations": "write",
        "models": "read",
    }


def test_permission_scope_misspelling_is_rejected() -> None:
    with pytest.raises(ValidationError):
        # Deliberately misspelled -- runtime rejection is the contract.
        Permissions(artifact_metadta="read")  # type: ignore[call-arg]


def test_environment_deployment_is_accepted() -> None:
    """`deployment: false` uses environment secrets without a deployment record."""
    data = to_data(Environment(name="prod", deployment=False))
    assert data == {"name": "prod", "deployment": False}


def test_environment_deployment_misspelling_is_rejected() -> None:
    with pytest.raises(ValidationError):
        # Deliberately misspelled -- runtime rejection is the contract.
        Environment(name="prod", deployments=False)  # type: ignore[call-arg]
