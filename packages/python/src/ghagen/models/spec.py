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


@dataclass(frozen=True)
class ModelSpec:
    """Serialization spec for one model type.

    Attributes:
        yaml_keys: Maps each content field name to its emitted YAML key. This is
            the single authority for the field -> emitted-key fact; models carry
            no Pydantic ``serialization_alias`` (a field whose key equals its
            name maps to itself).
        order: The emission ordering mode. A ``tuple`` is *explicit*: the listed
            YAML keys come first in that order, then any remaining keys (and
            extras) in insertion order. ``None`` is *alphabetical*: every key,
            extras included, is sorted at emit time — used by
            :class:`~ghagen.models.trigger.On`, whose trigger keys have no
            canonical order. This is the declarative peer of TypeScript's
            ``OrderMode`` (explicit key list vs alphabetical); the sort lives in
            the Emitter, identically for both ports.
        present_null_when_empty: YAML keys whose value, when it resolves to an
            empty map (an empty sub-model or ``{}``), is emitted as a bare null
            key (``key:``) instead of ``key: {}``. The declarative replacement
            for the old model-layer present-null smuggle.
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
    order: tuple[str, ...] | None = field(default_factory=tuple)
    present_null_when_empty: frozenset[str] = frozenset()
    patterns: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
