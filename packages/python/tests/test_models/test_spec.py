"""ModelSpec self-consistency checks across every model.

These assertions were impossible before Unit 2: key ordering lived in
``emitter/key_order.py`` while the field → YAML-key mapping lived in Pydantic
aliases, in separate files with no compile-time link. Now that both live in one
:class:`~ghagen.models.spec.ModelSpec` per model, a single test can verify they
agree — and that the spec's YAML keys match the emitted keys byte-for-byte.
"""

from __future__ import annotations

import ghagen.models.action  # noqa: F401  (ensure all model modules import)
import ghagen.models.job  # noqa: F401
import ghagen.models.trigger  # noqa: F401
import ghagen.models.workflow  # noqa: F401
from ghagen.emitter.nodes import _META_FIELDS
from ghagen.models._base import Document, GhagenModel
from ghagen.models.trigger import On


def _all_model_classes() -> list[type[GhagenModel]]:
    """Every concrete GhagenModel subclass (excludes the abstract bases)."""
    seen: dict[str, type[GhagenModel]] = {}

    def _walk(cls: type[GhagenModel]) -> None:
        for sub in cls.__subclasses__():
            if sub not in (GhagenModel, Document):
                seen[sub.__qualname__] = sub
            _walk(sub)

    _walk(GhagenModel)
    return list(seen.values())


def _content_fields(model: type[GhagenModel]) -> set[str]:
    return set(model.model_fields) - _META_FIELDS


def test_every_model_has_a_spec() -> None:
    for model in _all_model_classes():
        assert hasattr(model, "SPEC"), f"{model.__name__} has no ModelSpec"


def test_spec_covers_exactly_the_content_fields() -> None:
    for model in _all_model_classes():
        assert set(model.SPEC.yaml_keys) == _content_fields(model), (
            f"{model.__name__}: spec.yaml_keys keys must be exactly the content fields"
        )


def test_explicit_order_has_no_duplicates() -> None:
    for model in _all_model_classes():
        order = model.SPEC.order
        if order is None:  # alphabetical
            continue
        assert len(order) == len(set(order)), f"{model.__name__}: duplicate order keys"


def test_explicit_order_is_complete() -> None:
    """An explicit ``order`` (a tuple) lists exactly the model's emitted keys.

    No phantom keys, none missing. ``order=None`` opts into alphabetical
    emission and is exempt.
    """
    for model in _all_model_classes():
        if model.SPEC.order is None:  # alphabetical
            continue
        order = set(model.SPEC.order)
        keys = set(model.SPEC.yaml_keys.values())
        assert order == keys, (
            f"{model.__name__}: order {order} must equal emitted keys {keys}"
        )


def test_only_on_uses_alphabetical_order() -> None:
    """``On`` is the sole model that emits alphabetically (``order=None``)."""
    alpha = {m.__name__ for m in _all_model_classes() if m.SPEC.order is None}
    assert alpha == {On.__name__}, f"unexpected alphabetical-order models: {alpha}"
