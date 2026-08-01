"""Base model with escape hatches and comment support."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator
from ruamel.yaml.comments import CommentedMap

from ghagen._commented import Commented
from ghagen._package_paths import is_internal_frame
from ghagen._raw import Raw
from ghagen.emitter.header import DEFAULT, HeaderInput
from ghagen.models.spec import ModelSpec

_T = TypeVar("_T")

# Escape hatch for every field: accept the modeled type, or a raw
# CommentedMap passed straight through to YAML unmodeled. ``requires-python``
# is >=3.11, so this is a TypeVar-based generic alias rather than a PEP 695
# ``type`` statement (3.12+).
OrRaw = _T | CommentedMap


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
        if not is_internal_frame(frame.f_code.co_filename):
            return (frame.f_code.co_filename, frame.f_lineno)
        frame = frame.f_back

    return None


def _scan_for_models(value: Any) -> Iterator[GhagenModel]:
    """Yield every GhagenModel reachable from *value*.

    Recurses through Commented wrappers, dicts, and lists. Raw-wrapped
    values are opaque escape hatches and are not traversed.
    """
    if isinstance(value, GhagenModel):
        yield value
    elif isinstance(value, Commented):
        yield from _scan_for_models(value.value)
    elif isinstance(value, Raw):
        return
    elif isinstance(value, dict):
        for v in value.values():
            yield from _scan_for_models(v)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _scan_for_models(item)


# Fields carrying serialization policy rather than YAML content; structurally
# excluded from output. Declared immediately below, each with ``exclude=True``.
#
# This lives here, at the declaration site, rather than in the emitter: nothing
# in the emitter reads it any more (``collect_fields`` iterates
# ``spec.yaml_keys``, in which a meta field cannot appear), and a
# serialization-policy constant with no emitter consumer had no business sitting
# in ``emitter/nodes.py``. The import direction is unchanged — ``emitter``
# imports ``models``, never the reverse (ADR-0001 amendment).
_META_FIELDS = frozenset({"extras", "post_process", "comment", "eol_comment"})


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
        # Reject unknown keyword arguments. Pydantic's default is "ignore",
        # which silently swallowed misspelled field names (``Step(nmae=...)``
        # constructed an empty Step). ``extras=`` is the sanctioned channel for
        # unmodeled YAML keys.
        extra="forbid",
    )

    # Per-model serialization spec (field → YAML key mapping + emission order).
    # Every concrete model sets this next to its class definition.
    SPEC: ClassVar[ModelSpec]

    # The four ``_META_FIELDS`` below. They carry serialization *policy* rather
    # than YAML content, which is why each declares ``exclude=True``.
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

    @model_validator(mode="after")
    def _enforce_spec_patterns(self) -> GhagenModel:
        """Enforce the value grammars this model's spec declares.

        The peer of TypeScript's ``buildYamlData`` grammar check: one reader
        per port, in the one place that already consumes the spec at
        construction. Runs after :meth:`_preserve_commented`'s
        ``handler(clean)``, so it sees unwrapped values; skips non-``str``
        values, so ``Raw`` stays the explicit escape hatch.

        ``fullmatch`` rather than ``match``: ``re.match`` anchors only the
        start and Python's ``$`` matches before a trailing newline, so
        ``match`` accepted a superset of the schema language. The ``^``/``$``
        anchors in each pattern are therefore redundant and are kept solely so
        ``.pattern`` stays byte-identical to the Snapshot's pattern string,
        which ``schema/conformance-values.yml`` compares.
        """
        spec = getattr(type(self), "SPEC", None)
        if spec is None:
            return self
        for field_name, pattern in spec.patterns.items():
            value = getattr(self, field_name, None)
            if isinstance(value, str) and not pattern.fullmatch(value):
                raise ValueError(
                    f"{field_name} {value!r} must match {pattern.pattern}; "
                    "wrap the value in Raw(...) to bypass the grammar"
                )
        return self

    def model_post_init(self, __context: Any) -> None:
        """Capture the construction site's file/line from the call stack."""
        self._source_location = _find_user_frame()

    def children(self) -> Iterator[GhagenModel]:
        """Yield every nested GhagenModel in this model, in traversal order.

        Generic field scan: walks each field value, recursing through
        Commented wrappers, dicts, and lists (Raw values are opaque). This
        is the traversal primitive; subclasses need not override it.

        Schema fields come first, in declaration order, then ``extras``.
        This is *traversal* order, not emission order -- emission order is
        the spec's, resolved by :func:`~ghagen.emitter.nodes.order_entries`.
        ``extras`` is declared on this base class, so the plain
        ``model_fields`` order would yield it *before* every subclass field;
        TypeScript keeps extras outside ``data`` and appends them, so the
        skip-and-rescan below is what makes the two ports agree on visit
        order as well as visit set.
        """
        for field_name in type(self).model_fields:
            if field_name == "extras":
                continue
            yield from _scan_for_models(getattr(self, field_name, None))
        yield from _scan_for_models(self.extras)

    def walk(self) -> Iterator[GhagenModel]:
        """Depth-first pre-order iterator over self and every descendant.

        The root is yielded first. Read the yielded models to inspect the
        tree, or mutate their fields in place (e.g. the pin transform
        rewrites ``uses``).
        """

        def _visit(model: GhagenModel) -> Iterator[GhagenModel]:
            yield model
            for child in model.children():
                yield from _visit(child)

        yield from _visit(self)


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
