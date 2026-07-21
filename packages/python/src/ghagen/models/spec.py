"""Per-model serialization spec.

A :class:`ModelSpec` is the single place a model type's serialization surface
lives: the field-name → emitted-YAML-key mapping and the canonical emission
order. It is declared next to the model class and read by the Emitter (via
:meth:`~ghagen.models._base.GhagenModel.to_commented_map`) instead of the old
scattered ``emitter/key_order.py`` tables and ``_get_key_order()`` overrides.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelSpec:
    """Serialization spec for one model type.

    Attributes:
        yaml_keys: Maps each content field name to its emitted YAML key. Values
            agree with the field's Pydantic ``serialization_alias`` (a plain
            field with no alias maps to itself), so emitted YAML is unchanged.
        order: Emitted YAML key names in canonical emission order. Keys absent
            from ``order`` are appended alphabetically. An empty ``order`` emits
            every key alphabetically (used by :class:`~ghagen.models.trigger.On`,
            whose trigger keys have no canonical order).
    """

    yaml_keys: Mapping[str, str]
    order: tuple[str, ...] = field(default_factory=tuple)
