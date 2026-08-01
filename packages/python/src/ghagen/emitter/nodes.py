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

from ghagen._commented import Commented, is_commented, unwrap_commented
from ghagen._dedent import dedent_script
from ghagen._raw import Raw, raw_scalar
from ghagen.emitter.comments import attach, attach_model_comment
from ghagen.models._base import GhagenModel
from ghagen.models.spec import ModelSpec
from ghagen.models.step import Step


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


def order_entries(
    raw: dict[str, Any],
    extras: dict[str, Any],
    spec: ModelSpec,
) -> list[tuple[str, Any]]:
    """Resolve a model's emitted ``(key, value)`` entries in canonical order.

    The single home for emission ordering, shared by the ruamel walk
    (:func:`_model_to_map`) and the plain-data walk
    (:func:`ghagen.emitter.data._model_to_data`), so the two cannot disagree.

    - ``"alphabetical"``: every key — ``raw`` and ``extras`` alike — is sorted,
      so a dynamic extra event interleaves with the typed fields rather than
      being force-appended.
    - ``"explicit"`` (the default): ``raw`` is emitted as it stands, then
      ``extras``. :func:`collect_fields` builds ``raw`` by iterating
      ``spec.yaml_keys``, so "as it stands" *is* the spec's declaration order —
      there is no second key list to re-derive it from, and therefore none to
      disagree with it.
    """
    if spec.order == "alphabetical":
        merged = {**raw, **extras}
        return [(key, merged[key]) for key in sorted(merged)]

    return [*raw.items(), *extras.items()]


def collect_fields(model: GhagenModel, *, auto_dedent: bool) -> dict[str, Any]:
    """Collect a model's emitted fields under their YAML keys.

    The single home for emission *membership*, shared by the ruamel walk
    (:func:`_model_to_map`) and the plain-data walk
    (:func:`ghagen.emitter.data._model_to_data`), so the two cannot disagree
    about which fields exist — the peer of :func:`order_entries`, which is the
    single home for the order they come out in.

    The loop iterates ``spec.yaml_keys``, not ``model_fields``, so the spec is
    the single declaration of *which* fields are emitted and *in what order*.
    That drops two rules the ``model_fields`` loop needed and neither of which
    could fire any more:

    - a ``_META_FIELDS`` skip. A meta field can never appear in ``yaml_keys`` —
      ``test_spec_covers_exactly_the_content_fields`` asserts
      ``set(SPEC.yaml_keys) == set(model_fields) - _META_FIELDS`` for every
      model — so the guard was unreachable, not merely unused.
    - a ``.get(field_name, field_name)`` fallback for a field missing from
      ``yaml_keys``. Unreachable by the same guarantee; the lookup is now total.

    A field is collected iff all of these hold (the contract stated in
    ``docs/specs/0001-python-single-pass-serialization.md`` §4):

    1. it is named in ``spec.yaml_keys`` — the spec, not the Pydantic class, is
       the emission surface;
    2. it is set (``model_fields_set`` — ``exclude_unset``);
    3. its value, wrapper and all, is not ``None`` — ``exclude_none`` is checked
       on the *raw* attribute, before any ``Commented`` / ``Raw`` see-through, so
       a ``Raw(None)`` survives;
    4. the key it lands under is ``spec.yaml_keys[field]``.

    When *auto_dedent* is true a :class:`~ghagen.models.step.Step`'s ``run``
    string is dedented here, at collection — no model mutation, no copy
    (ADR-0002). This is the sole home of the dedent-at-emit rule for both job
    steps and composite-action ``runs.steps``.

    Returns the ``{yaml_key: value}`` mapping in ``spec.yaml_keys`` declaration
    order, which under the default ``"explicit"`` :data:`~ghagen.models.spec.OrderMode`
    is the emitted order; :func:`order_entries` folds in ``extras`` from there.
    """
    spec = type(model).SPEC
    is_step = isinstance(model, Step)

    raw: dict[str, Any] = {}
    for field_name, yaml_key in spec.yaml_keys.items():
        if field_name not in model.model_fields_set:  # exclude_unset
            continue
        value = getattr(model, field_name, None)
        if value is None:  # exclude_none (checked on the raw wrapper)
            continue
        if auto_dedent and is_step and field_name == "run" and isinstance(value, str):
            value = dedent_script(value)
        raw[yaml_key] = value
    return raw


def is_empty_map(node: Any) -> bool:
    """True when *node* is an empty map — the trigger for ``present_null_when_empty``.

    Booleans, non-empty maps, and non-map scalars are not empty maps. Both a
    ruamel ``CommentedMap`` and a plain ``dict`` (used by the data walk) are
    ``dict`` subclasses, so one check serves both Emitter passes.
    """
    return isinstance(node, dict) and len(node) == 0


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
        return _to_node(unwrap_commented(value), auto_dedent=auto_dedent)
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

    Walks the model's own fields directly (no ``model_dump``): membership and
    the ``run`` dedent come from :func:`collect_fields`, emission order from
    :func:`order_entries` — both shared with the plain-data walk. This function
    owns only what is ruamel-specific from there on: it harvests per-field
    comments from ``Commented`` wrappers, merges extras, attaches comments, and
    runs the ``post_process`` hook. Field → YAML key mapping and emission order
    both come from the model's :class:`~ghagen.models.spec.ModelSpec`.

    Does NOT attach the model's OWN comment — that is the container's job
    (:func:`_to_node` for a map value, :func:`_to_seq` for a seq item, and the
    document emitter for the root).
    """
    spec = type(model).SPEC
    raw = collect_fields(model, auto_dedent=auto_dedent)
    present_null = spec.present_null_when_empty
    cm = CommentedMap()

    # Emit each field, attaching any Commented-wrapper comment inline at the
    # point of emission (no collect-then-reattach two-pass). The comment
    # module owns the actual placement. A ``present_null_when_empty`` field whose
    # value resolves to an empty map emits as a bare ``key:`` (null).
    for key, value in order_entries(raw, model.extras, spec):
        if is_commented(value):
            node = _to_node(unwrap_commented(value), auto_dedent=auto_dedent)
            if key in present_null and is_empty_map(node):
                node = None
            cm[key] = node
            attach(cm, key, comment=value.comment, eol_comment=value.eol_comment)
        else:
            node = _to_node(value, auto_dedent=auto_dedent)
            if key in present_null and is_empty_map(node):
                node = None
            cm[key] = node

    if model.post_process is not None:
        model.post_process(cm)

    return cm
