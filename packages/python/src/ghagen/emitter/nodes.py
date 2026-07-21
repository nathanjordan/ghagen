"""The emitter's recursion core: value → ruamel node dispatch.

This module is the *single* home for turning any model value into a
:mod:`ruamel.yaml` node. Every ``Commented`` / ``Raw`` wrapper see-through,
``GhagenModel`` / ``dict`` / ``list`` / scalar dispatch, canonical key
ordering, comment attachment, extras merge, ``post_process`` hook, and the
serialization-time ``run`` dedent live here and nowhere else.

Recursion never leaves the emitter: models carry only data plus their
:class:`~ghagen.models.spec.ModelSpec`, and the imports point one way —
``emitter`` imports ``models``, never the reverse (ADR-0001 amendment).
"""

from __future__ import annotations

from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ghagen._commented import Commented, is_commented
from ghagen._dedent import dedent_script
from ghagen._raw import Raw, raw_scalar
from ghagen.emitter.comments import attach, attach_model_comment
from ghagen.models._base import GhagenModel
from ghagen.models.step import Step

# Fields carrying serialization policy rather than YAML content; structurally
# excluded from output (they declare ``exclude=True`` on ``GhagenModel``).
_META_FIELDS = frozenset({"extras", "post_process", "comment", "eol_comment"})


def unwrap_raw(value: Any) -> Any:
    """Recursively unwrap ``Raw`` instances to their inner values.

    A ``Raw[str]`` becomes a ``PlainScalarString`` (via :func:`~ghagen._raw.raw_scalar`)
    so the block-scalar auto-conversion in
    :func:`~ghagen.emitter.yaml_writer.dump_yaml` leaves it alone — the ``Raw``
    escape-hatch contract is to emit the inner value as-is. A ``Raw``'s inner
    value is returned as-is (not itself re-unwrapped); plain dicts/lists are
    walked so nested ``Raw`` entries are unwrapped.
    """
    if isinstance(value, Raw):
        return raw_scalar(value.value)
    if isinstance(value, dict):
        return {k: unwrap_raw(v) for k, v in value.items()}
    if isinstance(value, list):
        return [unwrap_raw(v) for v in value]
    return value


def to_ordered_commented_map(
    data: dict[str, Any],
    key_order: list[str],
) -> CommentedMap:
    """Convert a dict to a CommentedMap with keys in canonical order.

    Keys present in ``key_order`` come first in that order; remaining keys
    follow in alphabetical order.
    """
    cm = CommentedMap()
    seen: set[str] = set()

    for key in key_order:
        if key in data:
            cm[key] = data[key]
            seen.add(key)

    for key in sorted(data.keys()):
        if key not in seen:
            cm[key] = data[key]

    return cm


def _to_seq(items: list[Any], *, auto_dedent: bool) -> CommentedSeq:
    """Serialize a list to a CommentedSeq.

    A ``GhagenModel`` item is serialized via :func:`_model_to_map` directly
    (not routed through :func:`_to_node`) so its OWN comment lands once, on the
    seq index — the container decision for a list entry. Routing it through
    :func:`_to_node` would additionally stamp the comment on the child map's
    first key, double-attaching it.
    """
    seq = CommentedSeq()
    for idx, item in enumerate(items):
        if isinstance(item, GhagenModel):
            seq.append(_model_to_map(item, auto_dedent=auto_dedent))
            attach(seq, idx, comment=item.comment, eol_comment=item.eol_comment)
        else:
            seq.append(_to_node(item, auto_dedent=auto_dedent))
    return seq


def _to_node(value: Any, *, auto_dedent: bool) -> Any:
    """Convert any model value to a YAML node in one recursive pass.

    The single place a ``Commented`` / ``Raw`` / ``GhagenModel`` / ``dict`` /
    ``list`` / scalar becomes a ruamel node. Python peer of TypeScript's
    ``toYamlValue``.
    """
    if isinstance(value, Commented):
        return _to_node(value.value, auto_dedent=auto_dedent)
    if isinstance(value, Raw):
        # Route through unwrap_raw to keep PlainScalarString wrapping of
        # Raw[str] (bypasses the block-scalar auto-cast).
        return unwrap_raw(value)
    if isinstance(value, GhagenModel):
        child = _model_to_map(value, auto_dedent=auto_dedent)
        # A model as a map value renders its own comment on the map as a whole
        # (block before first key, EOL after last value). Seq items never reach
        # here — _to_seq serializes them directly and attaches on the index.
        attach_model_comment(
            child, comment=value.comment, eol_comment=value.eol_comment
        )
        return child
    if isinstance(value, CommentedMap):
        return value
    if isinstance(value, dict):
        cm = CommentedMap()
        for k, v in value.items():
            cm[k] = _to_node(v, auto_dedent=auto_dedent)
        return cm
    if isinstance(value, list):
        return _to_seq(value, auto_dedent=auto_dedent)
    return unwrap_raw(value)


def _model_to_map(model: GhagenModel, *, auto_dedent: bool = False) -> CommentedMap:
    """Serialize *model* to a CommentedMap in a single field walk.

    Walks the model's own fields directly (no ``model_dump``): applies
    ``exclude_none`` / ``exclude_unset`` semantics, canonical key ordering,
    harvests per-field comments from ``Commented`` wrappers, merges extras,
    attaches comments, and runs the ``post_process`` hook. Field → YAML key
    mapping and emission order both come from the model's
    :class:`~ghagen.models.spec.ModelSpec`.

    When *auto_dedent* is true, each :class:`~ghagen.models.step.Step`'s ``run``
    script is dedented at this node-build point — no model mutation, no copy
    (ADR-0002). This is the sole home of the dedent-at-emit rule for both job
    steps and composite-action ``runs.steps``.

    Does NOT attach the model's OWN comment — that is the container's job
    (:func:`_to_node` for a map value, :func:`_to_seq` for a seq item, and the
    document emitter for the root).
    """
    spec = type(model).SPEC
    is_step = isinstance(model, Step)

    # Single walk: collect set, non-None fields under their YAML keys.
    raw: dict[str, Any] = {}
    for field_name in type(model).model_fields:
        if field_name in _META_FIELDS:
            continue
        if field_name not in model.model_fields_set:  # exclude_unset
            continue
        value = getattr(model, field_name, None)
        if value is None:  # exclude_none (checked on the raw wrapper)
            continue
        if auto_dedent and is_step and field_name == "run" and isinstance(value, str):
            value = dedent_script(value)
        raw[spec.yaml_keys.get(field_name, field_name)] = value

    ordered = to_ordered_commented_map(raw, list(spec.order))

    cm = CommentedMap()

    # Emit each field, attaching any Commented-wrapper comment inline at the
    # point of emission (no collect-then-reattach two-pass). The comment
    # module owns the actual placement.
    for key, value in list(ordered.items()) + list(model.extras.items()):
        if is_commented(value):
            cm[key] = _to_node(value.value, auto_dedent=auto_dedent)
            attach(cm, key, comment=value.comment, eol_comment=value.eol_comment)
        else:
            cm[key] = _to_node(value, auto_dedent=auto_dedent)

    if model.post_process is not None:
        model.post_process(cm)

    return cm
