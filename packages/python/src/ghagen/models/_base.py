"""Base model with escape hatches and comment support."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator
from ruamel.yaml.comments import CommentedMap

from ghagen._commented import Commented
from ghagen._raw import Raw
from ghagen.emitter.header import DEFAULT, HeaderInput
from ghagen.models.spec import ModelSpec

_T = TypeVar("_T")

# Escape hatch for every field: accept the modeled type, or a raw
# CommentedMap passed straight through to YAML unmodeled. ``requires-python``
# is >=3.11, so this is a TypeVar-based generic alias rather than a PEP 695
# ``type`` statement (3.12+).
OrRaw = _T | CommentedMap

# Root of the installed ``ghagen`` package (…/ghagen). Any frame inside it is
# ghagen-internal — regardless of the submodule (models/, emitter/, helpers/,
# pin/, …). Deriving the prefix from the package location instead of a
# hand-listed set of subdir substrings means a model constructed via a new
# subpackage still attributes the correct user frame (round-2 fix: the old
# ``/ghagen/models/`` + ``/ghagen/emitter/`` list mis-attributed helpers/pin
# construction sites).
_GHAGEN_ROOT = Path(__file__).resolve().parent.parent


def _is_internal_frame(filename: str) -> bool:
    """Return True if ``filename`` is inside pydantic or the ghagen package."""
    if "pydantic" in Path(filename).parts:
        return True
    try:
        resolved = Path(filename).resolve()
    except (OSError, ValueError):  # pragma: no cover — defensive
        return False
    return resolved == _GHAGEN_ROOT or _GHAGEN_ROOT in resolved.parents


def _find_user_frame() -> tuple[str, int] | None:
    """Walk up the call stack to find the first user-code frame.

    Returns ``(filename, lineno)`` of the first frame that is NOT inside
    pydantic or ghagen internals, or ``None`` if no such frame exists.
    """
    try:
        frame = sys._getframe(1)  # skip this helper
    except ValueError:  # pragma: no cover — defensive
        return None

    while frame is not None:
        if not _is_internal_frame(frame.f_code.co_filename):
            return (frame.f_code.co_filename, frame.f_lineno)
        frame = frame.f_back

    return None


def _scan_for_models(key: str, value: Any) -> Iterator[tuple[str, GhagenModel]]:
    """Yield ``(key, model)`` for every GhagenModel reachable from *value*.

    Recurses through Commented wrappers, dicts, and lists. Raw-wrapped
    values are opaque escape hatches and are not traversed.
    """
    if isinstance(value, GhagenModel):
        yield (key, value)
    elif isinstance(value, Commented):
        yield from _scan_for_models(key, value.value)
    elif isinstance(value, Raw):
        return
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _scan_for_models(k, v)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _scan_for_models(key, item)


class GhagenModel(BaseModel):
    """Base model for all ghagen types.

    Provides:
    - extras: dict of arbitrary key/values merged into YAML output
    - post_process: callback to modify the CommentedMap before emission
    - comment: block comment emitted above this node
    - eol_comment: end-of-line comment

    Per-field comments are attached via :func:`~ghagen.with_comment` and
    :func:`~ghagen.with_eol_comment` wrappers on individual field values.

    A model carries only data plus its :class:`~ghagen.models.spec.ModelSpec`;
    serialization to YAML nodes lives entirely in the emitter
    (:mod:`ghagen.emitter.nodes`), which reads the spec. Models never call back
    into the emitter (ADR-0001 amendment).
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )

    # Per-model serialization spec (field → YAML key mapping + emission order).
    # Every concrete model sets this next to its class definition.
    SPEC: ClassVar[ModelSpec]

    extras: dict[str, Any] = Field(default_factory=dict, exclude=True)
    post_process: Callable[[CommentedMap], None] | None = Field(None, exclude=True)
    comment: str | None = Field(None, exclude=True)
    eol_comment: str | None = Field(None, exclude=True)

    # Captured source location (file, line) of the user code that
    # constructed this model. Populated by model_post_init via frame
    # walking. None if no user frame was found (e.g., constructed entirely
    # from inside ghagen internals).
    _source_location: tuple[str, int] | None = PrivateAttr(default=None)

    @model_validator(mode="wrap")
    @classmethod
    def _preserve_commented(cls, values: Any, handler: Callable[..., Any]) -> Any:
        """Allow Commented wrappers on any field without altering type annotations.

        Unwraps Commented values before Pydantic field validation runs, then
        re-sets them on the validated instance so the wrappers survive.
        """
        if not isinstance(values, dict):
            return handler(values)

        commented: dict[str, Commented[Any]] = {}
        clean: dict[str, Any] = {}
        for k, v in values.items():
            if isinstance(v, Commented):
                commented[k] = v
                clean[k] = v.value
            else:
                clean[k] = v

        instance = handler(clean)

        for k, v in commented.items():
            object.__setattr__(instance, k, v)

        return instance

    def model_post_init(self, __context: Any) -> None:
        """Capture the construction site's file/line from the call stack."""
        self._source_location = _find_user_frame()

    def children(self) -> Iterator[tuple[str, GhagenModel]]:
        """Yield ``(key, child)`` for every nested GhagenModel in this model.

        Generic field scan: walks each field value, recursing through
        Commented wrappers, dicts, and lists (Raw values are opaque). This
        is the traversal primitive; subclasses need not override it.
        """
        for field_name in type(self).model_fields:
            yield from _scan_for_models(field_name, getattr(self, field_name, None))

    def walk(self) -> Iterator[tuple[list[str], GhagenModel]]:
        """Depth-first walk yielding ``(path, model)`` for self and all descendants.

        The root is yielded first with an empty path; each descendant's
        path is its parent's path plus the field key it was found under.
        Read the yielded models to inspect the tree, or mutate their fields
        in place (e.g. the pin transform rewrites ``uses``).
        """

        def _visit(
            path: list[str], model: GhagenModel
        ) -> Iterator[tuple[list[str], GhagenModel]]:
            yield (path, model)
            for key, child in model.children():
                yield from _visit([*path, key], child)

        yield from _visit([], self)


class Document(GhagenModel):
    """A top-level model that maps 1:1 to a generated YAML file.

    Only :class:`~ghagen.Workflow` and :class:`~ghagen.Action` are Documents:
    they are the sole models that may be serialized to a file, via
    :meth:`to_yaml` / :meth:`to_yaml_file`. Both methods are thin delegates to
    the emitter's :func:`~ghagen.emitter.emit` (imported call-time so the
    emitter stays a one-way ``emitter`` → ``models`` dependency). Nested models
    (Step, Job, …) are serialized by the emitter for embedding but are not
    Documents and cannot be emitted to a file.
    """

    def to_yaml(
        self, header: HeaderInput = DEFAULT, *, auto_dedent: bool = True
    ) -> str:
        """Generate the complete YAML string for this document.

        Args:
            header: Header comment for the generated file. Four shapes
                are accepted:

                - omit (``DEFAULT`` sentinel) — emit ghagen's default
                  header.
                - ``None`` — emit no header.
                - ``str`` — emit the string verbatim. No
                  ``{variable}`` substitution; literal braces are
                  preserved.
                - ``Callable[[HeaderVariables], str]`` — invoke with a
                  fully-populated
                  :class:`~ghagen.emitter.header.HeaderVariables` and
                  emit the returned string.
            auto_dedent: When true (the default), each Step's ``run``
                script is dedented at emit time. Set false to emit the
                raw strings verbatim.

        Returns:
            The complete YAML string.
        """
        from ghagen.emitter import emit

        return emit(self, header=header, auto_dedent=auto_dedent)

    def to_yaml_file(
        self,
        path: str | Path,
        header: HeaderInput = DEFAULT,
        *,
        auto_dedent: bool = True,
    ) -> None:
        """Write the document YAML to a file.

        Args:
            path: File path to write to.
            header: Header comment. See :meth:`to_yaml` for the four
                accepted shapes.
            auto_dedent: When true (the default), each Step's ``run``
                script is dedented at emit time.
        """
        from ghagen.emitter import emit_file

        emit_file(self, path, header=header, auto_dedent=auto_dedent)
