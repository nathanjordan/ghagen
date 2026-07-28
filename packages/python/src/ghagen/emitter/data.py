"""The Emitter's public observation surface: emit any model to plain data.

:func:`to_data` renders any :class:`~ghagen.models._base.GhagenModel` to a
nested structure of plain ``dict`` / ``list`` / scalars — the supported way to
inspect a single model's emitted shape (key names, values, ordering, aliasing,
extras merge, dynamic keys, and optionally comment placement) without reaching
into ruamel nodes, the ``Commented`` / ``Raw`` wrappers, or ModelSpec identity.

This is the observation peer of :mod:`ghagen.emitter.nodes` (which builds ruamel
nodes for file emission): both read the same :class:`~ghagen.models.spec.ModelSpec`
for field → YAML key mapping and canonical order, so ``to_data`` and ``emit``
cannot disagree on structure. Unlike ``emit``, ``to_data`` does not run the
ruamel-backend passes (block-scalar promotion, comment-column alignment) or the
``post_process`` hook — those operate on the backend node; assert them via the
emitted YAML string.

Recursion lives entirely inside the emitter (ADR-0001 amendment): this module
imports ``models``, never the reverse.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ghagen._commented import is_commented
from ghagen._dedent import dedent_script
from ghagen._raw import Raw
from ghagen.emitter.nodes import _META_FIELDS, is_empty_map, order_entries
from ghagen.models._base import GhagenModel
from ghagen.models.step import Step


@dataclass(frozen=True)
class CommentNode:
    """A value plus the comments the Emitter would attach to it.

    The public, backend-independent representation of a commented node — the
    observation-surface peer of the internal ``Commented`` wrapper and ruamel's
    ``CommentToken``. Only produced by :func:`to_data` with ``comments=True``,
    and only for nodes that actually carry a comment.
    """

    value: Any
    comment: str | None = None
    eol_comment: str | None = None


def to_data(
    model: GhagenModel,
    *,
    auto_dedent: bool = False,
    comments: bool = False,
) -> Any:
    """Emit any model to plain Python data — the supported observation surface.

    Returns a nested structure of plain ``dict`` / ``list`` / scalars in
    canonical emission order, with field names mapped to their YAML keys (from
    the model's :class:`~ghagen.models.spec.ModelSpec`), extras merged after the
    ordered keys, and ``Raw`` escape-hatch values unwrapped to their inner
    value.

    - ``comments=False`` (default): ``Commented`` wrappers are unwrapped to
      their values. The returned tree contains no framework wrapper types
      (``Commented``, ``Raw``, ``CommentNode``, ``GhagenModel``, ruamel nodes),
      so it is safe for ``==``. Use this for key/value/order/aliasing
      assertions.
    - ``comments=True``: a node that carries a comment is returned as a
      :class:`CommentNode` so comment placement is observable as data (no ruamel
      ``.ca`` reads).

    Any model may be passed (Step, Job, On, …) — this observes a node, not file
    serialization, so it is deliberately not gated on
    :class:`~ghagen.models._base.Document`.

    Unlike :func:`~ghagen.emitter.emit`, this does not run the ruamel-backend
    passes (block-scalar promotion, comment-column alignment) or the
    ``post_process`` hook, which operate on the backend node. Assert those via
    the emitted YAML string.

    Raises:
        TypeError: if *model* is not a :class:`~ghagen.models._base.GhagenModel`.
    """
    if not isinstance(model, GhagenModel):
        raise TypeError(f"to_data expects a GhagenModel, got {type(model).__name__!r}")
    return _model_to_data(model, auto_dedent=auto_dedent, comments=comments)


def _model_to_data(
    model: GhagenModel, *, auto_dedent: bool, comments: bool
) -> dict[str, Any]:
    """Walk a model's fields to a plain dict — the peer of ``_model_to_map``.

    Applies the same ``exclude_none`` / ``exclude_unset`` semantics, canonical
    key ordering, YAML-key mapping, extras merge, and (when *auto_dedent*)
    Step ``run`` dedent as the ruamel walk — but produces plain data and does
    NOT run ``post_process``. A model's OWN comment is not represented here; it
    is a container-placement concern, surfaced by :func:`_value_to_data` when a
    model appears as a value.
    """
    spec = type(model).SPEC
    is_step = isinstance(model, Step)

    raw: dict[str, Any] = {}
    for field_name in type(model).model_fields:
        if field_name in _META_FIELDS:
            continue
        if field_name not in model.model_fields_set:  # exclude_unset
            continue
        value = getattr(model, field_name, None)
        if value is None:  # exclude_none
            continue
        if auto_dedent and is_step and field_name == "run" and isinstance(value, str):
            value = dedent_script(value)
        raw[spec.yaml_keys.get(field_name, field_name)] = value

    present_null = spec.present_null_when_empty

    result: dict[str, Any] = {}
    for key, value in order_entries(raw, model.extras, spec):
        if is_commented(value):
            inner = _value_to_data(
                value.value, auto_dedent=auto_dedent, comments=comments
            )
            if key in present_null and is_empty_map(inner):
                inner = None
            if comments and (
                value.comment is not None or value.eol_comment is not None
            ):
                result[key] = CommentNode(
                    inner, comment=value.comment, eol_comment=value.eol_comment
                )
            else:
                result[key] = inner
        else:
            data_value = _value_to_data(
                value, auto_dedent=auto_dedent, comments=comments
            )
            if key in present_null and is_empty_map(data_value):
                data_value = None
            result[key] = data_value
    return result


def _value_to_data(value: Any, *, auto_dedent: bool, comments: bool) -> Any:
    """Convert any model value to plain data — the peer of ``_to_node``.

    ``Commented`` wrappers encountered here (i.e. not at a model-field position)
    are unwrapped with their comment dropped, matching ``_to_node``. A model's
    OWN comment IS surfaced (as a :class:`CommentNode` when *comments*), matching
    the ruamel walk's ``attach_model_comment`` / seq-index attach.
    """
    if is_commented(value):
        return _value_to_data(value.value, auto_dedent=auto_dedent, comments=comments)
    if isinstance(value, Raw):
        return _value_to_data(value.value, auto_dedent=auto_dedent, comments=comments)
    if isinstance(value, GhagenModel):
        data = _model_to_data(value, auto_dedent=auto_dedent, comments=comments)
        if comments and (value.comment is not None or value.eol_comment is not None):
            return CommentNode(
                data, comment=value.comment, eol_comment=value.eol_comment
            )
        return data
    if isinstance(value, dict):
        return {
            k: _value_to_data(v, auto_dedent=auto_dedent, comments=comments)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [
            _value_to_data(item, auto_dedent=auto_dedent, comments=comments)
            for item in value
        ]
    return value
