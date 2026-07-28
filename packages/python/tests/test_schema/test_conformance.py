"""Coarse schema-conformance sweep for the hand-written Python models.

This is the test-based replacement for the deleted diff-only generated models
(see ADR-0003). It walks **both** canonical Snapshots -- the workflow schema
(``.github/workflows/*.yml``) and the action schema (``action.yml``) -- and for
each scope asserts that ghagen's hand-written Pydantic models expose every
upstream property. The emitted YAML key for each field is sourced from the
model's :class:`~ghagen.models.spec.ModelSpec` -- the single authority for the
field -> YAML-key mapping (e.g. ``if_`` -> ``if``, ``run_name`` -> ``run-name``,
``pre_if`` -> ``pre-if``).

Properties ghagen intentionally does not model live in the shared allow-list at
``schema/conformance-gaps.yml``, read here *and* by the TypeScript sweep
(``packages/typescript/src/models/conformance.test.ts``). Both ports held to the
same allow-list means both modelling the same property set -- cross-port surface
agreement, structurally. Anything upstream but missing from the models (and not
allow-listed) fails the sweep, surfacing schema drift as a conformance gap.

It needs no code generation -- it reads each model's ``ModelSpec`` directly.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from ghagen_schema.paths import SCHEMA_DIR
from ruamel.yaml import YAML

from ghagen.models._base import GhagenModel
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

GAPS_PATH = SCHEMA_DIR / "conformance-gaps.yml"
SCOPES_PATH = SCHEMA_DIR / "conformance-scopes.yml"

# A JSON path into a loaded schema: the keys to walk before reading properties.
SchemaPath = tuple[str, ...]

# ---------------------------------------------------------------------------
# Sweep table. The scope set and each scope's schema path(s) are shared data at
# schema/conformance-scopes.yml (read identically by the TypeScript sweep); this
# port binds each shared scope to its covering Pydantic model below. A parity
# guard asserts the two key sets match, so a scope added to one port and not the
# other fails a test instead of drifting silently.
# ---------------------------------------------------------------------------


class Scope:
    """One conformance scope: schema location(s) mapped to a covering model."""

    def __init__(self, model: type[GhagenModel], paths: tuple[SchemaPath, ...]) -> None:
        self.model = model
        self.paths = paths


# snapshot filename -> {scope name -> covering model}. The schema path(s) for
# each scope live in the shared conformance-scopes.yml; only the model binding
# stays here (a Python type cannot be serialized into the shared file).
_MODELS: dict[str, dict[str, type[GhagenModel]]] = {
    "workflow_schema.json": {
        "workflow": Workflow,
        # ghagen's single Job model covers both the regular-job and the
        # reusable-workflow-call-job shapes.
        "job": Job,
        "step": Step,
    },
    "action_schema.json": {
        "action": Action,
        "compositeRuns": CompositeRuns,
        "dockerRuns": DockerRuns,
        "nodeRuns": NodeRuns,
        "actionInput": ActionInput,
        "actionOutput": ActionOutput,
        "branding": Branding,
    },
}


def _load_scopes() -> dict[str, dict[str, tuple[SchemaPath, ...]]]:
    """Load the shared scope table: snapshot -> scope name -> schema path(s)."""
    raw = YAML(typ="safe").load(SCOPES_PATH.read_text())
    return {
        snapshot: {
            name: tuple(tuple(path) for path in paths) for name, paths in scopes.items()
        }
        for snapshot, scopes in raw.items()
    }


_SCOPE_PATHS = _load_scopes()

# snapshot filename -> {scope name -> Scope}, binding each shared scope's
# path(s) to this port's covering model. Built over the intersection so a
# divergence never crashes import; the parity guard below is the failure surface.
SWEEP: dict[str, dict[str, Scope]] = {
    snapshot: {
        name: Scope(_MODELS[snapshot][name], paths)
        for name, paths in scopes.items()
        if name in _MODELS.get(snapshot, {})
    }
    for snapshot, scopes in _SCOPE_PATHS.items()
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


def _model_property_names(model: type[GhagenModel]) -> set[str]:
    """Emitted YAML key names for a model — sourced from its ModelSpec."""
    return set(model.SPEC.yaml_keys.values())


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


def test_scope_set_matches_shared_table() -> None:
    """This port's scope bindings must match the shared scope table exactly.

    The mirror of this guard in the TypeScript sweep asserts the same equality,
    so a scope added to one port and not the other -- or a snapshot/scope typo --
    fails a test instead of degrading conformance coverage silently.
    """
    shared = _load_scopes()
    assert set(_MODELS) == set(shared), (
        f"conformance snapshots diverge from {SCOPES_PATH.name}: "
        f"port has {sorted(_MODELS)}, shared table has {sorted(shared)}."
    )
    for snapshot in shared:
        assert set(_MODELS[snapshot]) == set(shared[snapshot]), (
            f"{snapshot} conformance scopes diverge from {SCOPES_PATH.name}: "
            f"port has {sorted(_MODELS[snapshot])}, shared table has "
            f"{sorted(shared[snapshot])}."
        )
