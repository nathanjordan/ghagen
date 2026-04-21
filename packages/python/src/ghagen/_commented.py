"""Commented[T] wrapper for attaching YAML comments to field values."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

T = TypeVar("T")


class Commented(Generic[T]):
    """Wrapper that attaches YAML block or end-of-line comments to a value.

    Use :func:`with_comment` and :func:`with_eol_comment` to create instances.
    Wrappers persist in model fields at runtime; the serialization pipeline
    unwraps them and emits the comments onto the YAML nodes.

    Example::

        Step(uses=with_eol_comment("actions/checkout@v4", "pinned"))
        Workflow(name=with_comment("CI", "The workflow display name"))
    """

    def __init__(
        self,
        value: T,
        comment: str | None = None,
        eol_comment: str | None = None,
    ) -> None:
        self.value = value
        self.comment = comment
        self.eol_comment = eol_comment

    def __repr__(self) -> str:
        parts = [repr(self.value)]
        if self.comment is not None:
            parts.append(f"comment={self.comment!r}")
        if self.eol_comment is not None:
            parts.append(f"eol_comment={self.eol_comment!r}")
        return f"Commented({', '.join(parts)})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Commented):
            return (
                self.value == other.value
                and self.comment == other.comment
                and self.eol_comment == other.eol_comment
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.value, self.comment, self.eol_comment))

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls._serialize,
                info_arg=False,
                return_schema=core_schema.any_schema(),
            ),
        )

    @classmethod
    def _validate(cls, value: Any) -> Any:
        if isinstance(value, Commented):
            return value
        return value

    @staticmethod
    def _serialize(value: Any) -> Any:
        if isinstance(value, Commented):
            return value.value
        return value


def with_comment(value: T, comment: str) -> T:
    """Attach a block comment (emitted above the field) to a value.

    The return type is ``T`` for type-checker ergonomics, but at runtime
    the returned object is a :class:`Commented` wrapper.

    Chainable: if *value* is already :class:`Commented`, the comment field
    is merged.
    """
    if isinstance(value, Commented):
        return Commented(value.value, comment=comment, eol_comment=value.eol_comment)  # type: ignore[return-value]
    return Commented(value, comment=comment)  # type: ignore[return-value]


def with_eol_comment(value: T, eol_comment: str) -> T:
    """Attach an end-of-line comment to a value.

    The return type is ``T`` for type-checker ergonomics, but at runtime
    the returned object is a :class:`Commented` wrapper.

    Chainable: if *value* is already :class:`Commented`, the eol_comment
    field is merged.
    """
    if isinstance(value, Commented):
        return Commented(value.value, comment=value.comment, eol_comment=eol_comment)  # type: ignore[return-value]
    return Commented(value, eol_comment=eol_comment)  # type: ignore[return-value]


def unwrap_commented(value: Any) -> Any:
    """Return the inner value if *value* is :class:`Commented`, else passthrough."""
    if isinstance(value, Commented):
        return value.value
    return value


def is_commented(value: Any) -> bool:
    """Type guard: return ``True`` if *value* is a :class:`Commented` wrapper."""
    return isinstance(value, Commented)
