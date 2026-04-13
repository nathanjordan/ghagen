"""Raw[T] escape hatch for bypassing type constraints."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
from ruamel.yaml.scalarstring import PlainScalarString, ScalarString

T = TypeVar("T")


class Raw(Generic[T]):
    """Escape hatch that bypasses type constraints, emitting the inner value as-is.

    Use this to pass values that aren't covered by the library's typed enums
    or Literal constraints without losing type safety on other fields.

    Example::

        Step(shell=Raw("future-shell-type"))
        Job(runs_on=Raw("custom-runner-label"))
    """

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Raw({self.value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Raw):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)

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
    def _validate(cls, value: Any) -> Raw[Any]:
        if isinstance(value, Raw):
            return value
        return cls(value)

    @staticmethod
    def _serialize(value: Raw[Any]) -> Any:
        inner = value.value
        if isinstance(inner, str) and not isinstance(inner, ScalarString):
            return PlainScalarString(inner)
        return inner
