"""ModelSpec self-consistency checks across every model.

These assertions were impossible before Unit 2: key ordering lived in
``emitter/key_order.py`` while the field → YAML-key mapping lived in Pydantic
aliases, in separate files with no compile-time link. Both then moved into one
:class:`~ghagen.models.spec.ModelSpec` per model, but as *two* declarations — a
``yaml_keys`` mapping and an ``order`` tuple restating its values — checked
against each other only as sets. Now ``yaml_keys`` is the sole declaration and
its declaration order is the emission order, so the assertions here are about
the emitted sequence itself rather than about two copies agreeing.
"""

from __future__ import annotations

import enum
import importlib
import pkgutil
import re
import types
from collections.abc import Iterator
from typing import Any, ClassVar, Literal, Union, get_args, get_origin

import pytest
from pydantic import ValidationError
from ruamel.yaml.comments import CommentedMap

import ghagen.models
from ghagen import Commented, Matrix, Raw, Step, with_comment, with_eol_comment
from ghagen.emitter.data import to_data
from ghagen.models._base import _META_FIELDS, Document, GhagenModel
from ghagen.models.spec import ModelSpec
from ghagen.models.trigger import On


def _import_every_model_module() -> None:
    """Import every module in ``ghagen.models``, so reflection sees them all.

    ``__subclasses__()`` only reports classes whose defining module has been
    imported, so seeding it with a hand-written import list makes coverage
    depend on import luck: this file used to import four modules and reach
    ``ImageSnapshot`` only because ``job.py`` happens to import it at runtime.
    Moving that under ``TYPE_CHECKING`` would have shrunk the sweep with no
    test failure -- the same defect as a hand-maintained list, one refactor
    away. Walking the package is the Python-idiom peer of the TypeScript port's
    ``satisfies Record<ModelKind, ModelSpec>``: coverage derived from the
    language's own model of "all the model types".
    """
    for mod in pkgutil.iter_modules(ghagen.models.__path__):
        importlib.import_module(f"ghagen.models.{mod.name}")


def _all_model_classes() -> list[type[GhagenModel]]:
    """Every concrete GhagenModel subclass (excludes the abstract bases)."""
    _import_every_model_module()
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


# --- constructive model building, for the emitted-sequence guard ---
#
# A spec's emitted key sequence is only observable on a model that actually sets
# every field, and eight specs have no golden-fixture coverage at all, so the
# values have to be synthesized. Each field gets an ordered candidate list read
# off its annotation; if Pydantic rejects the first choice, the field named in
# the error advances to its next candidate and construction is retried. That
# keeps the helper from needing a hand-maintained value table that would go
# stale the next time a field's type changes.

_UNSUPPORTED = object()
# Probe strings for a field carrying a ``ModelSpec.patterns`` grammar; the first
# one the grammar accepts is used.
_PATTERN_PROBES = ("1", "1.0", "1.*", "x", "abc", "0")


def _union_members(annotation: Any) -> Iterator[Any]:
    if get_origin(annotation) in (Union, types.UnionType):
        for arg in get_args(annotation):
            yield from _union_members(arg)
    else:
        yield annotation


def _value_for(annotation: Any, depth: int) -> Any:
    """One sample value for a single (non-union) annotation, or ``_UNSUPPORTED``."""
    if annotation is type(None):
        return _UNSUPPORTED
    origin = get_origin(annotation)
    if origin is Literal:
        return get_args(annotation)[0]
    if origin in (list, set, tuple):
        return []
    if origin is dict:
        return {}
    if annotation in (str, Any):
        return "x"
    if annotation is bool:
        return True
    if annotation is int:
        return 1
    if annotation is float:
        return 1.0
    if isinstance(annotation, type):
        if issubclass(annotation, CommentedMap):
            return CommentedMap()
        if issubclass(annotation, enum.Enum):
            return next(iter(annotation))
        if issubclass(annotation, GhagenModel):
            if depth <= 0:
                return _UNSUPPORTED
            return _populated(annotation, depth - 1, required_only=True)
        if issubclass(annotation, dict):
            return {}
        if issubclass(annotation, list):
            return []
    return _UNSUPPORTED


def _candidates(model: type[GhagenModel], name: str, depth: int) -> list[Any]:
    pattern = model.SPEC.patterns.get(name)
    out: list[Any] = [v for v in _PATTERN_PROBES if pattern and pattern.match(v)]
    for member in _union_members(model.model_fields[name].annotation):
        value = _value_for(member, depth)
        if value is not _UNSUPPORTED:
            out.append(value)
    out.extend(("x", {}))
    return out


def _populated(
    model: type[GhagenModel], depth: int = 3, *, required_only: bool = False
) -> GhagenModel:
    """Build *model* with every field set, supplied in reverse declaration order."""
    names = [
        name
        for name in reversed(list(model.SPEC.yaml_keys))
        if not required_only or model.model_fields[name].is_required()
    ]
    candidates = {name: _candidates(model, name, depth) for name in names}
    choice = dict.fromkeys(names, 0)
    error: ValidationError | None = None
    for _ in range(60):
        try:
            return model(**{n: candidates[n][choice[n]] for n in names})
        except ValidationError as exc:
            error = exc
            advanced = False
            for entry in exc.errors():
                loc = entry["loc"]
                name = loc[0] if loc else None
                if isinstance(name, str) and choice.get(name, 0) + 1 < len(
                    candidates.get(name, ())
                ):
                    choice[name] += 1
                    advanced = True
            if not advanced:
                break
    raise AssertionError(f"could not build a populated {model.__name__}: {error}")


def test_every_model_has_a_spec() -> None:
    for model in _all_model_classes():
        assert hasattr(model, "SPEC"), f"{model.__name__} has no ModelSpec"


def test_spec_covers_exactly_the_content_fields() -> None:
    for model in _all_model_classes():
        assert set(model.SPEC.yaml_keys) == _content_fields(model), (
            f"{model.__name__}: spec.yaml_keys keys must be exactly the content fields"
        )


def test_yaml_keys_values_are_unique() -> None:
    """Two fields may not map to one YAML key — the later one would be dropped.

    ``collect_fields`` writes into a ``dict`` keyed by YAML key, so a duplicate
    value silently loses a field. Nothing caught this before: the deleted
    ``order``/``yaml_keys`` comparison was between *sets*, and a duplicate
    satisfies a set comparison. This is the guard that replaced it, over the one
    structure that survives.
    """
    for model in _all_model_classes():
        keys = list(model.SPEC.yaml_keys.values())
        assert len(keys) == len(set(keys)), (
            f"{model.__name__}: duplicate YAML keys in yaml_keys — "
            f"{[k for k in keys if keys.count(k) > 1]}"
        )


def test_emitted_key_sequence_equals_yaml_keys_declaration_order() -> None:
    """Every spec emits exactly ``yaml_keys``' declaration order, as a *sequence*.

    Built constructively, one fully populated model per spec, with the fields
    supplied in **reverse** declaration order — so a pass means the Emitter
    normalised them, not that the input happened to arrive sorted.

    This is the guard the port never had. ``order`` restated
    ``tuple(yaml_keys.values())`` in all 28 explicit specs and only *set*
    equality was checked, so permuting one against the other changed the emitted
    YAML with the whole suite green (the golden fixtures do not back-stop it:
    most specs never emit enough keys at once for any ordering to be
    observable). There is no second list to permute now; what remains to guard
    is the Emitter re-sorting, which this catches.
    """
    for model in _all_model_classes():
        expected = list(model.SPEC.yaml_keys.values())
        if model.SPEC.order == "alphabetical":
            expected = sorted(expected)
        emitted = list(to_data(_populated(model)))
        assert emitted == expected, (
            f"{model.__name__}: emitted {emitted}, expected {expected}"
        )


def test_only_on_uses_alphabetical_order() -> None:
    """``On`` is the sole model that emits alphabetically."""
    alpha = {m.__name__ for m in _all_model_classes() if m.SPEC.order == "alphabetical"}
    assert alpha == {On.__name__}, f"unexpected alphabetical-order models: {alpha}"


# --- the value-grammar escape hatch, on a synthetic patterned model ---
#
# No shipped model declares both a ``patterns`` entry and an ``OrRaw`` annotation
# on the same field, so the "non-``str`` values skip the grammar" half of the
# contract has no natural home among them. A synthetic model states it directly.


class _Patterned(GhagenModel):
    """A model whose one patterned field also accepts the ``Raw`` escape hatch."""

    SPEC: ClassVar[ModelSpec] = ModelSpec(
        yaml_keys={"value": "value"},
        patterns={"value": re.compile(r"^\d+$", re.ASCII)},
    )

    value: str | Raw[str] | None = None


def test_grammar_rejects_a_non_matching_string() -> None:
    with pytest.raises(ValidationError):
        _Patterned(value="nope")


def test_grammar_rejects_a_non_matching_string_under_a_comment_wrapper() -> None:
    """``with_comment`` must not defeat the grammar (the TypeScript peel rule)."""
    with pytest.raises(ValidationError):
        _Patterned(value=with_comment("nope", "note"))
    with pytest.raises(ValidationError):
        _Patterned(value=with_eol_comment("nope", "note"))


def test_raw_bypasses_the_grammar() -> None:
    """``Raw`` is not a ``str``, so the grammar skips it — bare or wrapped.

    ``_Patterned.value`` is declared ``str | Raw[str] | None`` and
    ``with_comment`` is annotated ``T -> T`` while returning a ``Commented[T]``
    (see ``ghagen._commented``), so neither the ``Raw`` nor the wrapper is
    visible in the declared type. The ``isinstance`` narrowings below are what
    this test is *for* -- that the value arrived as a ``Raw``, and that the
    comment wrapper is still around it -- so they are stated rather than
    asserted through a suppression (docs/issues/09).
    """
    bare = _Patterned(value=Raw("nope")).value
    assert isinstance(bare, Raw)
    assert bare.value == "nope"

    wrapped = _Patterned(value=with_comment(Raw("nope"), "note")).value
    assert isinstance(wrapped, Commented)
    assert isinstance(wrapped.value, Raw)
    assert wrapped.value.value == "nope"
    assert wrapped.comment == "note"


# --- integer-like YAML keys: rejected wherever a user key can reach the map ---
#
# JavaScript's ``OrdinaryOwnPropertyKeys`` enumerates decimal-integer string
# keys FIRST, ahead of insertion order. The TypeScript port therefore cannot
# hold a key like ``"2"`` in its declared position, while Python's ``dict``
# can — so the two ports emit different YAML for the same input. The guard on
# ``yaml_keys`` values covers only the keys ghagen itself declares; ``extras``
# is the channel through which a *user* key reaches the same map, so it needs
# the same rule. Python must reject them too, or the ports disagree about what
# is legal.


@pytest.mark.parametrize("key", ["0", "1", "2", "42", "-1", "-42"])
def test_extras_rejects_an_integer_like_key(key: str) -> None:
    with pytest.raises(ValidationError):
        Step(run="x", extras={key: 1})


@pytest.mark.parametrize("key", ["01", "-0", "1.0", "+1", "1a", "a1", "", "١"])
def test_extras_accepts_a_key_that_is_not_a_decimal_integer(key: str) -> None:
    assert to_data(Step(run="x", extras={key: 1}))[key] == 1


def test_extras_rejects_an_integer_like_key_on_a_dynamic_key_model() -> None:
    """``Matrix`` reaches its dynamic axes through ``extras`` in this port."""
    with pytest.raises(ValidationError):
        Matrix(extras={"2": ["a"]})
