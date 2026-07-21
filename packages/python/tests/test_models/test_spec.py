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
from ghagen.emitter.yaml_writer import _yaml_key
from ghagen.models._base import _META_FIELDS, Document, GhagenModel
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


def test_yaml_keys_agree_with_pydantic_aliases() -> None:
    """The spec's emitted key for a field must match Pydantic's alias.

    This is the guarantee that byte output is unchanged: serialization now
    reads ``spec.yaml_keys`` instead of the alias resolver, so they must agree.
    """
    for model in _all_model_classes():
        for name in _content_fields(model):
            expected = _yaml_key(name, model.model_fields[name])
            assert model.SPEC.yaml_keys[name] == expected, (
                f"{model.__name__}.{name}: spec key "
                f"{model.SPEC.yaml_keys[name]!r} != alias key {expected!r}"
            )


def test_order_has_no_duplicates() -> None:
    for model in _all_model_classes():
        order = model.SPEC.order
        assert len(order) == len(set(order)), f"{model.__name__}: duplicate order keys"


def test_order_is_complete_or_empty() -> None:
    """Either the spec fully orders its keys, or opts into alphabetical (empty).

    A non-empty ``order`` must list exactly the model's emitted YAML keys — no
    phantom keys, none missing. An empty ``order`` means alphabetical emission.
    """
    for model in _all_model_classes():
        order = set(model.SPEC.order)
        keys = set(model.SPEC.yaml_keys.values())
        if model.SPEC.order:
            assert order == keys, (
                f"{model.__name__}: order {order} must equal emitted keys {keys}"
            )


def test_only_on_uses_empty_order() -> None:
    """``On`` is the sole model that emits alphabetically (empty order)."""
    empty = {m.__name__ for m in _all_model_classes() if not m.SPEC.order}
    assert empty == {On.__name__}, f"unexpected empty-order models: {empty}"
