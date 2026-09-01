"""Per-model serialization spec.

A :class:`ModelSpec` is the single place a model type's serialization surface
lives: the field-name → emitted-YAML-key mapping, the canonical emission order,
and the value grammars enforced at construction. It is declared next to the
model class and read by the Emitter (:mod:`ghagen.emitter.nodes`) instead of the
old scattered ``emitter/key_order.py`` tables and ``_get_key_order()``
overrides, and by :class:`~ghagen.models._base.GhagenModel` for ``patterns``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

OrderMode = Literal["explicit", "alphabetical"]
"""How a model's emitted keys are ordered. Two cases, no third (ADR-0011).

- ``"explicit"`` (the default): the ``yaml_keys`` mapping's **declaration
  order** is the emission order — a ``dict`` literal inserts in source order and
  ``dict`` has preserved insertion order since Python 3.7 (the project floor is
  3.11). Extras follow, in insertion order.
- ``"alphabetical"``: every key, extras included, is sorted at emit time.

``"explicit"`` used to carry a ``tuple`` naming the sequence a second time;
every spec restated ``tuple(yaml_keys.values())`` verbatim and only *set*
equality was tested, so a key could be declared in one position and emitted in
another with the whole suite green. Deleting the payload removed the second list
rather than tightening the test over it.
"""


@dataclass(frozen=True)
class ModelSpec:
    """Serialization spec for one model type.

    Attributes:
        yaml_keys: Maps each content field name to its emitted YAML key. This is
            the single authority for the field -> emitted-key fact *and* for the
            emission sequence: its declaration order is the order keys come out
            in, so reordering it reorders the emitted YAML. Models carry no
            Pydantic ``serialization_alias`` (a field whose key equals its name
            maps to itself).
        order: The emission ordering mode — see :data:`OrderMode`. ``"explicit"``
            (the default) emits ``yaml_keys`` in its own declaration order, then
            extras in insertion order. ``"alphabetical"`` sorts every key, extras
            included, at emit time — used by :class:`~ghagen.models.trigger.On`,
            whose trigger keys have no canonical order. The peer of TypeScript's
            ``OrderMode``; the sort lives in the Emitter, identically for both
            ports.
        present_null_when_empty: YAML keys whose value, when it resolves to an
            empty map (an empty sub-model or ``{}``), is emitted as a bare null
            key (``key:``) instead of ``key: {}``. The declarative replacement
            for the old model-layer present-null smuggle. This is about an
            *empty map*, never about ``None``: a ``None`` field is dropped by
            ``exclude_none`` in :func:`~ghagen.emitter.nodes.collect_fields` and
            never reaches this rule. An empty map is how a caller spells
            "present, no configuration"; ``None`` is how they spell "absent".
        patterns: Value grammars for individual fields, keyed by the same field
            names as ``yaml_keys``. Enforced at construction by
            :class:`~ghagen.models._base.GhagenModel`; non-``str`` values
            (including ``Raw``) are skipped, so the escape hatch stays opt-in.
            Compile each pattern with ``re.ASCII`` so ``\\d`` means what it
            means in ECMA-262 (the JSON Schema regex dialect) — the flag leaves
            ``.pattern`` byte-identical to the Snapshot's string. The peer of
            TypeScript's ``ModelSpec.patterns``; each grammar's single home is
            the canonical Snapshot, and ``schema/conformance-values.yml`` binds
            the two together by test.
    """

    yaml_keys: Mapping[str, str]
    order: OrderMode = "explicit"
    present_null_when_empty: frozenset[str] = frozenset()
    patterns: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
