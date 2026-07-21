"""Coarse schema-conformance sweep for the hand-written Python models.

This is the test-based replacement for the deleted diff-only generated models
(see ADR-0003). It walks **both** canonical Snapshots -- the workflow schema
(``.github/workflows/*.yml``) and the action schema (``action.yml``) -- and for
each scope asserts that ghagen's hand-written Pydantic models expose every
upstream property, either as a field name or via a serialization alias (e.g.
``if_`` -> ``if``, ``run_name`` -> ``run-name``, ``pre_if`` -> ``pre-if``).

Properties ghagen intentionally does not model live in the shared allow-list at
``schema/conformance-gaps.yml``, read here *and* by the TypeScript sweep
(``packages/typescript/src/models/conformance.test.ts``). Both ports held to the
same allow-list means both modelling the same property set -- cross-port surface
agreement, structurally. Anything upstream but missing from the models (and not
allow-listed) fails the sweep, surfacing schema drift as a conformance gap.

It needs no code generation -- it reflects over ``model_fields`` directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from ruamel.yaml import YAML

from ghagen.models.action import (
    Action,
    ActionInput,
    ActionOutput,
    Branding,
    CompositeRuns,
    DockerRuns,
    NodeRuns,
)
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.workflow import Workflow

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_DIR = REPO_ROOT / "schema"
GAPS_PATH = SCHEMA_DIR / "conformance-gaps.yml"

# A JSON path into a loaded schema: the keys to walk before reading properties.
SchemaPath = tuple[str, ...]

# ---------------------------------------------------------------------------
# Sweep table. Each scope names, per Snapshot, the schema location(s) whose
# property set the mapped Pydantic model must cover. Paths and scope names are
# mirrored exactly by the TypeScript sweep so both read one shared allow-list.
# ---------------------------------------------------------------------------

_ROOT: SchemaPath = ()


class Scope:
    """One conformance scope: schema location(s) mapped to a covering model."""

    def __init__(self, model: type[BaseModel], *paths: SchemaPath) -> None:
        self.model = model
        # Default to the schema root when no explicit path is given.
        self.paths: tuple[SchemaPath, ...] = paths or (_ROOT,)


# snapshot filename -> {scope name -> Scope}
SWEEP: dict[str, dict[str, Scope]] = {
    "workflow_schema.json": {
        "workflow": Scope(Workflow, _ROOT),
        # ghagen's single Job model covers both the regular-job and the
        # reusable-workflow-call-job shapes.
        "job": Scope(
            Job,
            ("definitions", "normalJob"),
            ("definitions", "reusableWorkflowCallJob"),
        ),
        "step": Scope(Step, ("definitions", "step")),
    },
    "action_schema.json": {
        "action": Scope(Action, _ROOT),
        "compositeRuns": Scope(CompositeRuns, ("definitions", "runs-composite")),
        "dockerRuns": Scope(DockerRuns, ("definitions", "runs-docker")),
        "nodeRuns": Scope(NodeRuns, ("definitions", "runs-javascript")),
        "actionInput": Scope(ActionInput, ("properties", "inputs")),
        "actionOutput": Scope(ActionOutput, ("definitions", "outputs-composite")),
        "branding": Scope(Branding, ("properties", "branding")),
    },
}


def _load_schema(filename: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / filename).read_text())


def _load_gaps() -> dict[str, dict[str, list[str]]]:
    return YAML(typ="safe").load(GAPS_PATH.read_text())


def _resolve(schema: dict[str, Any], path: SchemaPath) -> dict[str, Any]:
    node: Any = schema
    for key in path:
        node = node[key]
    return node


def _node_properties(node: dict[str, Any]) -> set[str]:
    """Property names a schema node declares, direct or via patternProperties."""
    names = set(node.get("properties", {}).keys())
    for sub in node.get("patternProperties", {}).values():
        if isinstance(sub, dict):
            names |= set(sub.get("properties", {}).keys())
    return names


def _schema_properties(schema: dict[str, Any], scope: Scope) -> set[str]:
    props: set[str] = set()
    for path in scope.paths:
        props |= _node_properties(_resolve(schema, path))
    return props


def _model_property_names(model: type[BaseModel]) -> set[str]:
    """Serialization names a model exposes (alias when set, else field name)."""
    names: set[str] = set()
    for field_name, info in model.model_fields.items():
        names.add(info.serialization_alias or info.alias or field_name)
    return names


def _iter_scopes() -> list[tuple[str, str]]:
    return [(snap, scope) for snap, scopes in SWEEP.items() for scope in scopes]


@pytest.mark.parametrize(
    ("snapshot", "scope_name"),
    _iter_scopes(),
    ids=[f"{snap}:{scope}" for snap, scope in _iter_scopes()],
)
def test_scope_properties_covered(snapshot: str, scope_name: str) -> None:
    scope = SWEEP[snapshot][scope_name]
    schema = _load_schema(snapshot)
    props = _schema_properties(schema, scope)
    assert props, f"{snapshot}:{scope_name} exposes no schema properties"

    snapshot_gaps = _load_gaps().get(snapshot.removesuffix(".json"), {})
    allow = set(snapshot_gaps.get(scope_name, []))
    covered = _model_property_names(scope.model)

    missing = props - covered - allow
    assert not missing, (
        f"{snapshot}:{scope_name} model {scope.model.__name__} is missing schema "
        f"properties {sorted(missing)}. Add fields, or list them in "
        f"{GAPS_PATH.name} if intentionally unsupported."
    )
    # Keep the allow-list honest: every allowed name must still exist upstream.
    stale = allow - props
    assert not stale, (
        f"{snapshot}:{scope_name} allow-list has stale entries no longer in the "
        f"schema: {sorted(stale)}. Remove them from {GAPS_PATH.name}."
    )
