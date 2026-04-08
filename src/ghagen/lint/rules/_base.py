"""Base types for lint rules: @rule decorator, RuleMeta, RuleContext."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from ghagen.lint.violation import Severity, SourceLocation, Violation

if TYPE_CHECKING:
    from ghagen.lint.config import LintConfig
    from ghagen.models.workflow import Workflow


@dataclass(frozen=True)
class RuleMeta:
    """Metadata describing a lint rule."""

    id: str
    description: str
    default_severity: Severity


@dataclass
class RuleContext:
    """Context passed to rule functions during a lint run."""

    workflow_key: str
    config: LintConfig

    def loc(self, model: Any, symbolic: str) -> SourceLocation:
        """Build a SourceLocation from a model's captured _source_location
        and a symbolic path string. Degrades gracefully if the model has
        no captured location."""
        source = getattr(model, "_source_location", None)
        if source is None:
            return SourceLocation(file=None, line=None, symbolic=symbolic)
        file_str, line = source
        return SourceLocation(file=Path(file_str), line=line, symbolic=symbolic)


class Rule(Protocol):
    """A lint rule: a callable that yields Violations for a workflow.

    Rules are plain functions decorated with ``@rule(...)`` which attaches
    a ``.meta: RuleMeta`` attribute.
    """

    meta: RuleMeta

    def __call__(
        self, wf: Workflow, ctx: RuleContext
    ) -> Iterable[Violation]: ...


def rule(
    *,
    id: str,  # noqa: A002 — "id" is the natural parameter name here
    severity: Severity,
    description: str,
) -> Callable[[Callable[..., Iterable[Violation]]], Rule]:
    """Decorator that attaches RuleMeta to a rule function."""

    def decorator(fn: Callable[..., Iterable[Violation]]) -> Rule:
        fn.meta = RuleMeta(  # type: ignore[attr-defined]
            id=id,
            description=description,
            default_severity=severity,
        )
        return fn  # type: ignore[return-value]

    return decorator
