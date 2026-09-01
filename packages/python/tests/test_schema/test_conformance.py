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
Every entry is itself asserted three ways, so the file is a regression guard,
not a comment that happens to be YAML: a listed name must still be upstream
(``stale``), must still be uncovered by the model (``closed`` -- catching a gap
that was fixed without the row being deleted), and the file's own top-level
snapshot/scope keys must match the sweep exactly (``test_gap_set_matches_sweep``
-- catching a garbled key, which an empty allow-list under it would otherwise
hide).

A second sweep, one level down, covers *values* rather than properties: the
shared ``schema/conformance-values.yml`` binds each declared value grammar (a
``ModelSpec.patterns`` entry) back to the pattern string in the canonical
Snapshot, and carries accept/reject vectors that catch what a pattern *string*
comparison cannot -- regex-dialect divergence.

It needs no code generation -- it reads each model's ``ModelSpec`` directly.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from ghagen import Raw, with_comment
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
from ghagen.models.container import Container, Service
from ghagen.models.image_snapshot import IMAGE_SNAPSHOT_SPEC, ImageSnapshot
from ghagen.models.job import (
    JOB_SPEC,
    Concurrency,
    Defaults,
    DefaultsRun,
    Environment,
    Job,
    Matrix,
    Strategy,
)
from ghagen.models.permissions import Permissions, PermissionsValue
from ghagen.models.spec import ModelSpec
from ghagen.models.step import STEP_SPEC, Step
from ghagen.models.trigger import (
    WORKFLOW_CALL_INPUT_SPEC,
    WORKFLOW_DISPATCH_INPUT_SPEC,
    On,
    PRTrigger,
    PushTrigger,
    ScheduleTrigger,
    WorkflowCallInput,
    WorkflowCallOutput,
    WorkflowCallSecret,
    WorkflowCallTrigger,
    WorkflowDispatchInput,
    WorkflowDispatchTrigger,
)
from ghagen.models.workflow import WORKFLOW_SPEC, Workflow
from ghagen_schema.paths import SCHEMA_DIR

GAPS_PATH = SCHEMA_DIR / "conformance-gaps.yml"
SCOPES_PATH = SCHEMA_DIR / "conformance-scopes.yml"
VALUES_PATH = SCHEMA_DIR / "conformance-values.yml"
INPUTS_PATH = SCHEMA_DIR / "conformance-inputs.yml"
KEY_ORDER_PATH = SCHEMA_DIR / "key-order.yml"

# A JSON path into a loaded schema: the keys to walk before reading properties.
# Integer segments index into a list -- ten of the workflow scopes name a
# ``oneOf`` alternative positionally (``properties.on.oneOf[2]``,
# ``definitions.snapshot.oneOf[1]``), and there is no other way to reach either.
SchemaPath = tuple[str | int, ...]

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
        # --- the on: sub-tree ---
        "on": On,
        "pushTrigger": PushTrigger,
        # One model covers both `pull_request` and `pull_request_target`.
        "prTrigger": PRTrigger,
        "scheduleTrigger": ScheduleTrigger,
        "workflowDispatch": WorkflowDispatchTrigger,
        "workflowDispatchInput": WorkflowDispatchInput,
        "workflowCall": WorkflowCallTrigger,
        "workflowCallInput": WorkflowCallInput,
        "workflowCallOutput": WorkflowCallOutput,
        "workflowCallSecret": WorkflowCallSecret,
        # --- job sub-shapes ---
        "permissions": Permissions,
        "container": Container,
        "serviceContainer": Service,
        "strategy": Strategy,
        "concurrency": Concurrency,
        "defaults": Defaults,
        "defaultsRun": DefaultsRun,
        "environment": Environment,
        "imageSnapshot": ImageSnapshot,
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


#: Reserved top-level key in conformance-gaps.yml holding cross-field
#: constraint gaps rather than per-scope property gaps. It is not a snapshot,
#: so the property-gap sweep and its key-set guard must both skip it.
CONSTRAINTS_KEY = "constraints"

#: Reserved top-level key in conformance-gaps.yml holding the gaps in the OTHER
#: direction -- emitted keys the Snapshot does not declare for their scope (see
#: ``test_scope_emits_only_declared_keys``). Not a snapshot either, so the
#: property-gap sweep and its key-set guard skip it too.
UNDECLARED_KEY = "undeclared"

#: Every reserved (non-snapshot) top-level key in conformance-gaps.yml.
_RESERVED_KEYS = frozenset({CONSTRAINTS_KEY, UNDECLARED_KEY})


def _load_gaps_file() -> dict[str, Any]:
    """The whole gaps document, reserved sections included."""
    return YAML(typ="safe").load(GAPS_PATH.read_text())


def _load_gaps() -> dict[str, dict[str, list[str]]]:
    """Only the per-snapshot property-gap sections."""
    return {
        snapshot: scopes
        for snapshot, scopes in _load_gaps_file().items()
        if snapshot not in _RESERVED_KEYS
    }


def _load_undeclared() -> dict[str, dict[str, list[str]]]:
    """The ``undeclared`` section: snapshot -> scope -> emitted-but-unbacked."""
    return _load_gaps_file()[UNDECLARED_KEY]


def _resolve(schema: dict[str, Any], path: SchemaPath) -> Any:
    """Walk *path* into *schema*; integer segments index into a list."""
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
    # A gap entry is a claim that the model does NOT cover this name. If the
    # model now covers it, the gap has been closed and the row is stale in the
    # other direction -- catching that is the whole point of recording gaps as
    # data instead of a comment: closing one forces this table to be updated.
    closed = allow & covered
    assert not closed, (
        f"{snapshot}:{scope_name} allow-list names {sorted(closed)} that "
        f"{scope.model.__name__} now covers -- the gap has been closed. Remove "
        f"them from {GAPS_PATH.name}."
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


def test_gap_set_matches_sweep() -> None:
    """The gaps file's key structure must match the sweep exactly.

    ``test_scope_properties_covered`` above reads ``conformance-gaps.yml`` via
    ``.get(..., {})``, which silently treats a garbled or missing snapshot/scope
    key as "no gaps recorded" -- so if the file happened to record no gaps for
    that key anyway, corrupting the key is invisible to that test. This guard
    makes the file's shape itself load-bearing: every snapshot and scope key the
    sweep binds must appear here, and vice versa, so renaming or dropping a
    top-level key (e.g. ``workflow_schema`` -> ``workflow_schemas``) fails here
    even when every allow-list under it is empty. Mirrored in the TypeScript
    sweep.
    """
    gaps = _load_gaps()
    sweep_keys = {snapshot.removesuffix(".json") for snapshot in SWEEP}
    assert sweep_keys == set(gaps), (
        f"{GAPS_PATH.name} top-level keys diverge from the sweep: "
        f"sweep has {sorted(sweep_keys)}, {GAPS_PATH.name} has {sorted(gaps)}."
    )
    for snapshot, scopes in SWEEP.items():
        key = snapshot.removesuffix(".json")
        assert set(scopes) == set(gaps[key]), (
            f"{key} scope keys in {GAPS_PATH.name} diverge from the sweep: "
            f"sweep has {sorted(scopes)}, {GAPS_PATH.name} has {sorted(gaps[key])}."
        )


# ---------------------------------------------------------------------------
# The sweep in the other direction: model keys must be DECLARED upstream.
#
# ``test_scope_properties_covered`` above asserts upstream <= model -- every
# property the Snapshot declares is emitted by some model, or allow-listed.
# That catches the drift everyone expects (upstream grows a field and neither
# port models it). It says nothing at all about the reverse: a ``yaml_keys``
# value is a free string, so ``"shell": "shel"`` -- or a key GitHub retired two
# years ago -- passes every check in this file, and ghagen emits a workflow
# GitHub refuses.
#
# TypeScript has a compile-time answer to that for SOME of its specs:
# ``satisfies Record<keyof StepInput, keyof SchemaStep>`` asserts each emitted
# key is a property name the generated type declares, so a typo is TS2322 (and
# an upstream rename is TS2724 -- which is exactly how the 2026-09-01 refresh's
# ``definitions.container`` -> ``jobContainer``/``serviceContainer`` split
# surfaced). But there are seven such clauses, covering eight of this sweep's
# twenty-nine scopes, and Python had no peer for any of them. This test is the
# peer, for every scope, in both ports.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("snapshot", "scope_name"),
    _iter_scopes(),
    ids=[f"{snap}:{scope}" for snap, scope in _iter_scopes()],
)
def test_scope_emits_only_declared_keys(snapshot: str, scope_name: str) -> None:
    """Every emitted YAML key must be a property the Snapshot declares.

    The inverse of ``test_scope_properties_covered``: model <= upstream rather
    than upstream <= model. Legitimate exceptions live under the reserved
    ``undeclared`` key in the same shared allow-list, and are held to the same
    three-way claim the property gaps are -- the name must still be emitted
    (else the row is closed), must still be absent upstream (else it is stale),
    and the section's key set must equal the sweep's
    (``test_undeclared_set_matches_sweep``).
    """
    scope = SWEEP[snapshot][scope_name]
    schema = _load_schema(snapshot)
    props = _schema_properties(schema, scope)
    emitted = _model_property_names(scope.model)

    snapshot_undeclared = _load_undeclared().get(snapshot.removesuffix(".json"), {})
    allow = set(snapshot_undeclared.get(scope_name, []))

    invented = emitted - props - allow
    assert not invented, (
        f"{snapshot}:{scope_name} model {scope.model.__name__} emits keys the "
        f"Snapshot does not declare for this scope: {sorted(invented)}. Fix the "
        f"ModelSpec, or record them under `undeclared` in {GAPS_PATH.name} with "
        f"the reason they are emitted anyway."
    )
    # Claim 1: the row is still needed -- the model still emits this key.
    closed = allow - emitted
    assert not closed, (
        f"{snapshot}:{scope_name} `undeclared` names {sorted(closed)} that "
        f"{scope.model.__name__} no longer emits. Remove them from "
        f"{GAPS_PATH.name}."
    )
    # Claim 2: the key is still un-upstream. The day the Snapshot declares it,
    # the exception has become ordinary coverage and the row must go.
    backed = allow & props
    assert not backed, (
        f"{snapshot}:{scope_name} `undeclared` names {sorted(backed)} that the "
        f"Snapshot now declares -- the exception is no longer one. Remove them "
        f"from {GAPS_PATH.name}."
    )


def test_undeclared_set_matches_sweep() -> None:
    """The ``undeclared`` section's key structure must match the sweep exactly.

    Claim 3, and the peer of ``test_gap_set_matches_sweep``: the test above
    reads the section via ``.get(..., {})``, so a garbled snapshot or scope key
    would silently read as "no exceptions recorded" -- which is this section's
    entire current content, and therefore invisible. Mirrored in the TypeScript
    sweep.
    """
    undeclared = _load_undeclared()
    sweep_keys = {snapshot.removesuffix(".json") for snapshot in SWEEP}
    assert sweep_keys == set(undeclared), (
        f"{GAPS_PATH.name} `undeclared` top-level keys diverge from the sweep: "
        f"sweep has {sorted(sweep_keys)}, file has {sorted(undeclared)}."
    )
    for snapshot, scopes in SWEEP.items():
        key = snapshot.removesuffix(".json")
        assert set(scopes) == set(undeclared[key]), (
            f"{key} scope keys under `undeclared` in {GAPS_PATH.name} diverge "
            f"from the sweep: sweep has {sorted(scopes)}, file has "
            f"{sorted(undeclared[key])}."
        )


# ---------------------------------------------------------------------------
# Key-order sweep. The scope table above covers *which properties* a model
# exposes, as a SET -- ``_model_property_names`` returns a ``set``, so it never
# sees the sequence. Every order guard in either port is intra-port and compares
# a spec's emitted sequence to its own key map, which passes by construction.
# Permuting ``DEFAULTS_RUN_SPEC.fieldMap`` against ``DefaultsRun.yaml_keys``
# therefore changed the TypeScript port's emitted YAML with both suites green.
#
# The shared table is schema/key-order.yml, read identically by the TypeScript
# sweep; only the kind -> model binding stays here. Together with
# ``test_spec.py``'s "emitted key sequence equals yaml_keys declaration order",
# the chain is closed in both ports: shared table == yaml_keys == emitted.
# ---------------------------------------------------------------------------

# Shared model-kind name -> this port's model class. The kind names are the
# TypeScript port's ``ModelKind`` discriminants, which the conformance scope
# table already uses; this port has no ``kind`` field, and the class names are
# not a mechanical transform of them (``WorkflowDispatchTrigger`` is
# ``workflowDispatch``), so the binding is written out.
_KINDS: dict[str, type[GhagenModel]] = {
    "step": Step,
    "job": Job,
    "workflow": Workflow,
    "action": Action,
    "on": On,
    "pushTrigger": PushTrigger,
    "prTrigger": PRTrigger,
    "scheduleTrigger": ScheduleTrigger,
    "workflowDispatch": WorkflowDispatchTrigger,
    "workflowDispatchInput": WorkflowDispatchInput,
    "workflowCall": WorkflowCallTrigger,
    "workflowCallInput": WorkflowCallInput,
    "workflowCallOutput": WorkflowCallOutput,
    "workflowCallSecret": WorkflowCallSecret,
    "permissions": Permissions,
    "strategy": Strategy,
    "matrix": Matrix,
    "concurrency": Concurrency,
    "defaults": Defaults,
    "defaultsRun": DefaultsRun,
    "environment": Environment,
    "container": Container,
    "service": Service,
    "imageSnapshot": ImageSnapshot,
    "actionInput": ActionInput,
    "actionOutput": ActionOutput,
    "branding": Branding,
    "compositeRuns": CompositeRuns,
    "dockerRuns": DockerRuns,
    "nodeRuns": NodeRuns,
}


def _load_key_order() -> dict[str, dict[str, Any]]:
    """Load the shared key-order table: model kind -> {order, keys}."""
    return YAML(typ="safe").load(KEY_ORDER_PATH.read_text())


def test_model_kind_set_matches_shared_key_order_table() -> None:
    """Mirrored by the TypeScript guard of the same name.

    The table covers all 30 kinds -- two more than the conformance scope table,
    which has no scope for ``matrix`` or ``service``.
    """
    table = _load_key_order()
    assert set(_KINDS) == set(table), (
        f"model kinds diverge from {KEY_ORDER_PATH.name}: port has "
        f"{sorted(_KINDS)}, shared table has {sorted(table)}."
    )


@pytest.mark.parametrize(
    "kind", sorted(_load_key_order()), ids=sorted(_load_key_order())
)
def test_key_sequence_matches_shared_table(kind: str) -> None:
    table = _load_key_order()[kind]
    model = _KINDS[kind]
    assert model.SPEC.order == table["order"], (
        f"{kind}: port declares order={model.SPEC.order!r}, shared table says "
        f"{table['order']!r}."
    )
    # ``alphabetical`` leaves declaration order unread -- the Emitter sorts at
    # emit time -- so the table states the SORTED sequence for ``on`` and the
    # declared list is sorted to meet it. Asserting the raw declaration for
    # ``on`` would bind a sequence nothing observes.
    declared = list(model.SPEC.yaml_keys.values())
    emitted = sorted(declared) if table["order"] == "alphabetical" else declared
    assert emitted == list(table["keys"]), (
        f"{kind}: emitted key sequence {emitted} != shared table {table['keys']}."
    )


# ---------------------------------------------------------------------------
# Value-grammar sweep. The scope table above covers *which properties* a model
# exposes; this covers *which values* a field accepts. The shared table is
# schema/conformance-values.yml, read identically by the TypeScript sweep
# (packages/typescript/src/models/conformance.test.ts); only the spec +
# constructor binding stays here.
# ---------------------------------------------------------------------------


class ValueBinding:
    """One declared value grammar: this port's spec plus two constructors.

    ``construct`` passes the vector bare -- or, for the raw-hatch check
    (``test_value_raw_hatch_bypasses_the_grammar``), wrapped in ``Raw(...)``.
    ``construct_commented`` passes it wrapped in :func:`~ghagen.with_comment`.
    Two constructors rather than three because a comment wrapper reaches the
    grammar check by a different route in each port, and the shared table's
    ``reject_commented`` vectors are what bind both routes to the same answer
    -- ``construct`` alone is enough for the raw hatch since ``Raw`` and
    ``Commented`` compose (``Raw`` inside or outside a comment wrapper is
    unwrapped the same way).
    """

    def __init__(
        self,
        spec: ModelSpec,
        construct: Callable[[str | Raw[str]], GhagenModel],
        construct_commented: Callable[[str], GhagenModel],
    ) -> None:
        self.spec = spec
        self.construct = construct
        self.construct_commented = construct_commented


# snapshot filename -> "<kind>.<field>" -> binding. The key format is exactly a
# TypeScript ``spec.kind`` plus a ``patterns`` key; Python's ModelSpec carries
# no ``kind`` field (a pre-existing asymmetry between the two spec shapes), so
# this port supplies the ``kind`` half from the table below.
_VALUE_BINDINGS: dict[str, dict[str, ValueBinding]] = {
    "workflow_schema.json": {
        "imageSnapshot.version": ValueBinding(
            IMAGE_SNAPSHOT_SPEC,
            lambda version: ImageSnapshot(image_name="img", version=version),
            lambda version: ImageSnapshot(
                image_name="img", version=with_comment(version, "note")
            ),
        ),
    },
}


def _load_values() -> dict[str, dict[str, dict[str, Any]]]:
    """Load the shared value table: snapshot -> "<kind>.<field>" -> entry."""
    return YAML(typ="safe").load(VALUES_PATH.read_text())


_VALUES = _load_values()


def _iter_values() -> list[tuple[str, str]]:
    return [
        (snapshot, key)
        for snapshot, entries in _VALUES.items()
        for key in entries
        if key in _VALUE_BINDINGS.get(snapshot, {})
    ]


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_values(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_values()],
)
def test_value_pattern_matches_snapshot(snapshot: str, key: str) -> None:
    """The port's pattern source equals the canonical Snapshot's string.

    ``re.ASCII`` changes matching, not the source string, so the flag that
    fixes the Unicode-digit dialect bug leaves this comparison intact.
    """
    entry = _VALUES[snapshot][key]
    binding = _VALUE_BINDINGS[snapshot][key]
    field_name = key.split(".", 1)[1]
    pattern = binding.spec.patterns.get(field_name)
    assert pattern is not None, f"{key} declares no pattern in its ModelSpec"
    assert pattern.pattern == _resolve(_load_schema(snapshot), tuple(entry["path"]))


def _assert_pattern_anchored(pattern: re.Pattern[str], key: str) -> None:
    """A bound pattern's source must start with ``^`` and end with ``$``.

    Python enforces value grammars with ``re.fullmatch`` (see
    ``GhagenModel._enforce_spec_patterns``), which makes the anchors
    redundant here -- but TypeScript's peer check uses ``pattern.test``
    (``models/_base.ts``), which depends on the anchors entirely. The two
    ports therefore agree today only by coincidence of every current pattern
    happening to be anchored. The next grammar copied from a JSON Schema
    ``pattern`` -- where *unanchored* is the norm -- would make Python
    reject a value TypeScript accepts, with nothing catching the divergence
    (issue 28 #3). This assertion is what closes that gap: it fails loudly,
    at the moment a new unanchored pattern is bound, rather than waiting for
    a conformance-values.yml reject vector to happen to expose it.
    """
    src = pattern.pattern
    assert src.startswith("^") and src.endswith("$"), (
        f"{key} pattern {src!r} is not anchored with ^ and $. Python's "
        "fullmatch() does not need the anchors, but TypeScript's "
        "pattern.test() (models/_base.ts) depends on them entirely -- "
        "without them the two ports would validate this field differently. "
        "Add ^ and $ to the pattern, or wrap the TypeScript RegExp as "
        "^(?:...)$ so the anchors stop being load-bearing in either port."
    )


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_values(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_values()],
)
def test_value_pattern_is_anchored(snapshot: str, key: str) -> None:
    """Every bound pattern source must be anchored with ``^`` and ``$``.

    See :func:`_assert_pattern_anchored`. Mirrored by the TypeScript sweep's
    identically named check.
    """
    binding = _VALUE_BINDINGS[snapshot][key]
    field_name = key.split(".", 1)[1]
    pattern = binding.spec.patterns.get(field_name)
    assert pattern is not None, f"{key} declares no pattern in its ModelSpec"
    _assert_pattern_anchored(pattern, key)


def test_assert_pattern_anchored_rejects_an_unanchored_pattern() -> None:
    """Direct proof :func:`_assert_pattern_anchored` catches what it must.

    ``test_value_pattern_is_anchored`` above only ever sees today's real
    bindings, which are already anchored -- so on its own it can never turn
    red. This test constructs the exact input the sweep cannot currently
    produce (an unanchored pattern bound to a field) and confirms the
    assertion actually fails it, rather than passing by construction.
    """
    with pytest.raises(AssertionError, match="not anchored"):
        _assert_pattern_anchored(re.compile(r"\d+"), "synthetic.field")


def test_assert_pattern_anchored_accepts_an_anchored_pattern() -> None:
    """Control case: a correctly anchored pattern must not raise."""
    _assert_pattern_anchored(re.compile(r"^\d+$"), "synthetic.field")


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_values(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_values()],
)
def test_value_vectors(snapshot: str, key: str) -> None:
    """Every ``accept`` constructs; every ``reject`` raises.

    This is the assertion pattern identity cannot make: both dialect bugs this
    table was written for leave ``.pattern`` byte-identical and are visible
    only to executed vectors.
    """
    entry = _VALUES[snapshot][key]
    construct = _VALUE_BINDINGS[snapshot][key].construct
    for value in entry["accept"]:
        construct(value)  # must not raise
    for value in entry["reject"]:
        with pytest.raises(ValidationError):
            construct(value)


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_values(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_values()],
)
def test_value_vectors_under_a_comment_wrapper(snapshot: str, key: str) -> None:
    """A comment wrapper changes presentation, never what the grammar accepts.

    ``accept`` vectors still construct and ``reject_commented`` vectors still
    raise when the value arrives wrapped in :func:`~ghagen.with_comment`. This
    port peels the wrapper in ``GhagenModel._enforce_spec_patterns``; the
    TypeScript port peels it in ``buildYamlData``. Before the peel was added
    here, every ``reject_commented`` vector constructed successfully.
    """
    entry = _VALUES[snapshot][key]
    binding = _VALUE_BINDINGS[snapshot][key]
    for value in entry["accept"]:
        binding.construct_commented(value)  # must not raise
    for value in entry["reject_commented"]:
        with pytest.raises(ValidationError):
            binding.construct_commented(value)


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_values(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_values()],
)
def test_value_raw_hatch_bypasses_the_grammar(snapshot: str, key: str) -> None:
    """A field carrying a spec pattern MUST admit ``Raw`` -- see issue 22.

    ``_enforce_spec_patterns`` skips non-``str`` values specifically so
    ``Raw`` stays the escape hatch, and the grammar-violation message
    (``models/_base.py``) tells the caller exactly that. That advice is only
    true if the field's annotation actually accepts a ``Raw``. Rather than
    inspect ``type(self).model_fields[field].annotation`` -- a check
    TypeScript has no runtime form of, so it would let the two ports assert
    different things -- this executes the same path a caller acting on the
    message would: every ``reject`` vector, wrapped in ``Raw(...)`` instead of
    passed bare, must still construct. A field typed to exclude ``Raw``
    (``str | None``, as ``ImageSnapshot.version`` used to be) fails this with
    a ``ValidationError`` instead of silently shipping a false promise.
    """
    entry = _VALUES[snapshot][key]
    construct = _VALUE_BINDINGS[snapshot][key].construct
    for value in entry["reject"]:
        construct(Raw(value))  # must not raise -- Raw is the declared hatch


def test_value_key_set_matches_shared_table() -> None:
    """This port's value-grammar bindings must match the shared table exactly.

    The mirror of this guard in the TypeScript sweep asserts the same equality,
    so a grammar enforced in one port and not the other fails a test.
    """
    shared = _load_values()
    assert set(_VALUE_BINDINGS) == set(shared), (
        f"value-grammar snapshots diverge from {VALUES_PATH.name}: "
        f"port has {sorted(_VALUE_BINDINGS)}, shared table has {sorted(shared)}."
    )
    for snapshot in shared:
        assert set(_VALUE_BINDINGS[snapshot]) == set(shared[snapshot]), (
            f"{snapshot} value grammars diverge from {VALUES_PATH.name}: "
            f"port has {sorted(_VALUE_BINDINGS[snapshot])}, shared table has "
            f"{sorted(shared[snapshot])}."
        )


# ---------------------------------------------------------------------------
# Input-TYPE sweep. The scope table binds which properties a model exposes; the
# value table binds the grammar of the string fields that declare one. Neither
# binds a field's accepted TYPE UNION, which is the axis the two ports actually
# drifted on (issue 27). The shared table is schema/conformance-inputs.yml,
# read identically by the TypeScript sweep; only the spec + constructor binding
# stays here.
#
# This port's half is the strong one: Pydantic validates the declared
# annotation on every construction, so both the ``accept`` and the ``reject``
# vectors are genuinely EXECUTED here. TypeScript has no runtime type system --
# its ``reject`` vectors are checked by the compiler instead, in
# ``models/conformance-inputs.ts``. See that file and the shared table's header;
# the asymmetry is real and neither side pretends otherwise.
# ---------------------------------------------------------------------------


class InputBinding:
    """One ``<kind>.<field>`` row: this port's spec, field name, constructor."""

    def __init__(
        self,
        spec: ModelSpec,
        field: str,
        construct: Callable[[Any], GhagenModel],
    ) -> None:
        self.spec = spec
        #: This port's name for the field. The shared table keys on the
        #: TypeScript spelling (``continueOnError``); Python's is
        #: ``continue_on_error``. Rather than transliterate -- which would bake
        #: a naming convention into the sweep -- each port names its own field
        #: and both assert their spec maps it to the shared ``yaml_key``.
        self.field = field
        self.construct = construct


_INPUT_BINDINGS: dict[str, dict[str, InputBinding]] = {
    "workflow_schema.json": {
        "job.permissions": InputBinding(
            JOB_SPEC,
            "permissions",
            lambda v: Job(runs_on="ubuntu-latest", permissions=v),
        ),
        "workflow.permissions": InputBinding(
            WORKFLOW_SPEC,
            "permissions",
            lambda v: Workflow(name="CI", permissions=v),
        ),
        "workflowDispatchInput.default": InputBinding(
            WORKFLOW_DISPATCH_INPUT_SPEC,
            "default",
            # Constructed WITHOUT ``type``: every ``if`` in the Snapshot's
            # conditional block is guarded by ``required: [type]``, so with no
            # ``type`` present the unconditional union is exactly what applies.
            lambda v: WorkflowDispatchInput(default=v),
        ),
        "workflowCallInput.default": InputBinding(
            WORKFLOW_CALL_INPUT_SPEC,
            "default",
            # ``type`` is required here, and unlike workflow_dispatch it does
            # not constrain ``default`` -- the Snapshot types that field
            # directly.
            lambda v: WorkflowCallInput(type="string", default=v),
        ),
        "job.continueOnError": InputBinding(
            JOB_SPEC,
            "continue_on_error",
            lambda v: Job(runs_on="ubuntu-latest", continue_on_error=v),
        ),
        "step.continueOnError": InputBinding(
            STEP_SPEC,
            "continue_on_error",
            lambda v: Step(run="echo hi", continue_on_error=v),
        ),
    },
}


def _load_inputs() -> dict[str, dict[str, dict[str, Any]]]:
    """Load the shared input-type table: snapshot -> "<kind>.<field>" -> entry."""
    return YAML(typ="safe").load(INPUTS_PATH.read_text())


_INPUTS = _load_inputs()


def _iter_inputs() -> list[tuple[str, str]]:
    return [
        (snapshot, key)
        for snapshot, entries in _INPUTS.items()
        for key in entries
        if key in _INPUT_BINDINGS.get(snapshot, {})
    ]


def _iter_input_refs() -> list[tuple[str, str]]:
    return [(s, k) for s, k in _iter_inputs() if "ref" in _INPUTS[s][k]]


def _snapshot_type_union(schema: dict[str, Any], entry: dict[str, Any]) -> list[str]:
    """The sorted union of the JSON-Schema type tokens at ``type_paths``."""
    types: set[str] = set()
    for path in entry["type_paths"]:
        node = _resolve(schema, tuple(path))
        if isinstance(node, str):
            types.add(node)
        else:
            types |= set(node)
    return sorted(types)


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_inputs(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_inputs()],
)
def test_input_types_match_the_snapshot(snapshot: str, key: str) -> None:
    """The declared union equals the one the Snapshot spells at ``type_paths``.

    The type-union analogue of ``test_value_pattern_matches_snapshot``, and
    what stops the shared table from being a wish. An upstream narrowing -- or
    a typo in ``types`` -- fails here, in both ports.
    """
    entry = _INPUTS[snapshot][key]
    schema = _load_schema(snapshot)
    union = _snapshot_type_union(schema, entry)
    assert union == list(entry["types"]), (
        f"{key}: {INPUTS_PATH.name} declares types={list(entry['types'])}, but "
        f"the Snapshot's type_paths resolve to {union}."
    )


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_inputs(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_inputs()],
)
def test_input_field_emits_the_shared_yaml_key(snapshot: str, key: str) -> None:
    """This port's spec maps its bound field to the shared table's ``yaml_key``.

    The shared key (``job.continueOnError``) uses one spelling for a field the
    two ports name differently. This is what makes that safe: each port names
    its own field in its own binding, and both assert the field lands on the
    same emitted key. A binding pointed at the wrong field fails here.
    """
    entry = _INPUTS[snapshot][key]
    binding = _INPUT_BINDINGS[snapshot][key]
    mapped = binding.spec.yaml_keys.get(binding.field)
    assert mapped == entry["yaml_key"], (
        f"{key}: this port's spec maps {binding.field!r} to {mapped!r}, shared "
        f"table says {entry['yaml_key']!r}."
    )


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_input_refs(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_input_refs()],
)
def test_input_ref_still_points_at_the_shared_node(snapshot: str, key: str) -> None:
    """A row with a ``ref`` is a bare ``$ref`` to one shared Snapshot node.

    Only the two ``permissions`` rows carry one, and there it is the entire
    justification for a single ``PermissionsValue`` alias serving both the
    workflow-level and the job-level field. If upstream ever inlines or splits
    ``definitions.permissions``, one alias stops being the right shape and this
    fails, rather than the divergence being rediscovered by a reader.
    """
    ref = _INPUTS[snapshot][key]["ref"]
    schema = _load_schema(snapshot)
    assert _resolve(schema, tuple(ref["path"])) == ref["value"]


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_inputs(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_inputs()],
)
def test_input_accept_vectors(snapshot: str, key: str) -> None:
    """Every ``accept`` vector constructs."""
    entry = _INPUTS[snapshot][key]
    construct = _INPUT_BINDINGS[snapshot][key].construct
    for value in entry["accept"]:
        construct(value)  # must not raise


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_inputs(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_inputs()],
)
def test_input_reject_vectors(snapshot: str, key: str) -> None:
    """Every ``reject`` vector raises.

    This half of the sweep has no runtime peer in TypeScript -- see the shared
    table's header. Here it is a real execution: Pydantic validates the
    declared annotation, so a field widened past the Snapshot's union fails
    here (a field narrowed below it fails the accept half instead).
    """
    entry = _INPUTS[snapshot][key]
    construct = _INPUT_BINDINGS[snapshot][key].construct
    for value in entry["reject"]:
        with pytest.raises(ValidationError):
            construct(value)


def test_permissions_value_alias_is_both_permissions_fields() -> None:
    """``PermissionsValue`` is the declared type of BOTH ``permissions`` fields.

    The alias exists because the Snapshot defines ``permissions`` exactly once
    and both fields are a bare ``$ref`` to it (asserted above). This is the
    other half: the alias is not merely exported, it is what the two fields are
    annotated with -- so re-inlining the union at one site, which is how they
    drifted apart in the first place, fails here.
    """
    assert Job.model_fields["permissions"].annotation == PermissionsValue | None
    assert Workflow.model_fields["permissions"].annotation == PermissionsValue | None


def test_input_key_set_matches_shared_table() -> None:
    """This port's input-type bindings must match the shared table exactly.

    Mirrored by the TypeScript sweep, so a type union bound in one port and not
    the other fails a test.
    """
    shared = _load_inputs()
    assert set(_INPUT_BINDINGS) == set(shared), (
        f"input-type snapshots diverge from {INPUTS_PATH.name}: "
        f"port has {sorted(_INPUT_BINDINGS)}, shared table has {sorted(shared)}."
    )
    for snapshot in shared:
        assert set(_INPUT_BINDINGS[snapshot]) == set(shared[snapshot]), (
            f"{snapshot} input types diverge from {INPUTS_PATH.name}: "
            f"port has {sorted(_INPUT_BINDINGS[snapshot])}, shared table has "
            f"{sorted(shared[snapshot])}."
        )


# ---------------------------------------------------------------------------
# Cross-field constraint gaps -- the ``constraints`` section of
# conformance-gaps.yml. A property gap proves itself by the property's absence
# from the spec, a set-membership test. A cross-field constraint has no such
# footprint (both fields are present and both are typed), so the only proof the
# limit still exists is to construct the schema-invalid combination and watch
# it succeed.
# ---------------------------------------------------------------------------

# snapshot -> "<kind>.<field>" -> constructor over the row's ``counterexample``.
_CONSTRAINT_BINDINGS: dict[str, dict[str, Callable[[dict[str, Any]], GhagenModel]]] = {
    "workflow_schema": {
        "workflowDispatchInput.default": lambda kw: WorkflowDispatchInput(**kw),
    },
}


def _load_constraints() -> dict[str, dict[str, dict[str, Any]]]:
    return _load_gaps_file()[CONSTRAINTS_KEY]


def _iter_constraints() -> list[tuple[str, str]]:
    return [
        (snapshot, key)
        for snapshot, rows in _load_constraints().items()
        for key in rows
        if key in _CONSTRAINT_BINDINGS.get(snapshot, {})
    ]


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_constraints(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_constraints()],
)
def test_constraint_gap_rule_still_exists_upstream(snapshot: str, key: str) -> None:
    """Every ``requires`` path must still hold its stated value.

    Claim 1 of a constraint row, the peer of the property rows' ``stale``
    check: the row cannot outlive the upstream rule it describes.
    """
    row = _load_constraints()[snapshot][key]
    schema = _load_schema(f"{snapshot}.json")
    for req in row["requires"]:
        found = _resolve(schema, tuple(req["path"]))
        assert found == req["value"], (
            f"{key}: {GAPS_PATH.name} says the Snapshot holds {req['value']!r} "
            f"at {req['path']}, but it holds {found!r}. The upstream rule this "
            "gap records has changed -- update or remove the row."
        )


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_constraints(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_constraints()],
)
def test_constraint_gap_is_still_unenforced(snapshot: str, key: str) -> None:
    """The ``counterexample`` must still CONSTRUCT -- the gap is still open.

    Claim 2, the peer of the property rows' ``closed`` check. Implementing the
    conditional turns this red, which forces the row to be deleted rather than
    left standing as a stale "known limit".
    """
    row = _load_constraints()[snapshot][key]
    construct = _CONSTRAINT_BINDINGS[snapshot][key]
    construct(dict(row["counterexample"]))  # must not raise -- the gap is real


def test_constraint_gap_key_set_matches_the_sweep() -> None:
    """Claim 3: this port's constraint bindings match the shared section.

    Mirrored in the TypeScript sweep, so a constraint recorded against one port
    only -- or a garbled key -- fails a test.
    """
    shared = _load_constraints()
    assert set(_CONSTRAINT_BINDINGS) == set(shared), (
        f"{GAPS_PATH.name} constraint snapshots diverge from the sweep: port "
        f"has {sorted(_CONSTRAINT_BINDINGS)}, file has {sorted(shared)}."
    )
    for snapshot in shared:
        assert set(_CONSTRAINT_BINDINGS[snapshot]) == set(shared[snapshot]), (
            f"{snapshot} constraint rows diverge from the sweep: port has "
            f"{sorted(_CONSTRAINT_BINDINGS[snapshot])}, {GAPS_PATH.name} has "
            f"{sorted(shared[snapshot])}."
        )


@pytest.mark.parametrize(
    ("snapshot", "key"),
    _iter_constraints(),
    ids=[f"{snapshot}:{key}" for snapshot, key in _iter_constraints()],
)
def test_constraint_gap_row_states_its_claim(snapshot: str, key: str) -> None:
    """A gap row is a claim, so it must actually say what is unenforced.

    ``requires_prose`` and ``unenforced`` are the row's reasoning, and an empty
    or placeholder one turns the row back into the shrug it exists to replace.
    """
    row = _load_constraints()[snapshot][key]
    for field in ("requires_prose", "unenforced"):
        text = row.get(field, "")
        assert len(text) > 120, (
            f"{key}: {GAPS_PATH.name} row has no substantive {field!r}. State "
            "what the Snapshot requires and what the ports do not enforce."
        )
