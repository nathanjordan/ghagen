"""Base model with escape hatches and comment support."""

from __future__ import annotations

import sys
import warnings
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ghagen._commented import Commented, is_commented, unwrap_commented
from ghagen._raw import Raw
from ghagen.emitter.yaml_writer import (
    attach_comment,
    attach_field_comments,
    to_ordered_commented_map,
    unwrap_raw,
)

# Frame path fragments that mark a frame as "internal" to ghagen/pydantic.
# When walking the stack to find the user-code construction site, frames
# matching any of these substrings are skipped.
_INTERNAL_FRAME_MARKERS: tuple[str, ...] = (
    "/pydantic/",
    "/ghagen/models/",
    "/ghagen/emitter/",
)


def _is_internal_frame(filename: str) -> bool:
    """Return True if ``filename`` is inside pydantic or ghagen internals."""
    return any(marker in filename for marker in _INTERNAL_FRAME_MARKERS)


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


def _unwrap_commented_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Unwrap Commented values in a model_dump result dict."""
    result: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, Commented):
            result[k] = v.value
        elif isinstance(v, dict):
            result[k] = _unwrap_commented_dict(v)
        elif isinstance(v, list):
            result[k] = [
                item.value if isinstance(item, Commented) else item for item in v
            ]
        else:
            result[k] = v
    return result


class GhagenModel(BaseModel):
    """Base model for all ghagen types.

    Provides:
    - extras: dict of arbitrary key/values merged into YAML output
    - post_process: callback to modify the CommentedMap before emission
    - comment: block comment emitted above this node
    - eol_comment: end-of-line comment

    Per-field comments are attached via :func:`~ghagen.with_comment` and
    :func:`~ghagen.with_eol_comment` wrappers on individual field values.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )

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

    def _get_key_order(self) -> list[str]:
        """Return the canonical key ordering for this model type.

        Subclasses should override this to provide their specific ordering.
        """
        return []

    def _collect_commented_fields(
        self,
    ) -> tuple[dict[str, str], dict[str, str]]:
        """Walk model fields and collect comments from Commented wrappers.

        Returns ``(field_comments, field_eol_comments)`` dicts keyed by
        the YAML alias name.
        """
        field_comments: dict[str, str] = {}
        field_eol_comments: dict[str, str] = {}
        for field_name, field_info in type(self).model_fields.items():
            value = getattr(self, field_name, None)
            if not is_commented(value):
                continue

            # Determine the YAML key name (alias or field name)
            alias = field_info.alias or field_name
            if field_info.validation_alias and isinstance(
                field_info.validation_alias, str
            ):
                alias = field_info.validation_alias
            ser_alias = (
                field_info.serialization_alias
                if field_info.serialization_alias
                else alias
            )

            if value.comment:
                field_comments[ser_alias] = value.comment
            if value.eol_comment:
                field_eol_comments[ser_alias] = value.eol_comment

        return field_comments, field_eol_comments

    def _serialize_value(self, value: Any) -> Any:
        """Recursively serialize a value for YAML output."""
        if isinstance(value, Commented):
            return self._serialize_value(value.value)
        if isinstance(value, Raw):
            # Route through unwrap_raw to preserve PlainScalarString wrapping
            # of Raw[str] values (which bypasses the block-scalar auto-cast).
            return unwrap_raw(value)
        if isinstance(value, GhagenModel):
            return value.to_commented_map()
        if isinstance(value, CommentedMap):
            return value
        if isinstance(value, dict):
            result = CommentedMap()
            for k, v in value.items():
                result[k] = self._serialize_value(v)
            return result
        if isinstance(value, list):
            return self._serialize_list(value)
        return unwrap_raw(value)

    def _serialize_list(self, items: list[Any]) -> CommentedSeq:
        """Serialize a list, attaching comments from GhagenModel items."""
        seq = CommentedSeq()
        for item in items:
            seq.append(self._serialize_value(item))

        # Attach comments from GhagenModel items to the sequence
        for idx, item in enumerate(items):
            if isinstance(item, GhagenModel):
                if item.comment:
                    attach_comment(seq, idx, comment=item.comment)
                if item.eol_comment:
                    attach_comment(seq, idx, eol_comment=item.eol_comment)

        return seq

    def to_commented_map(self) -> CommentedMap:
        """Serialize this model to a CommentedMap with comments and ordering.

        Applies canonical key ordering, merges extras, attaches comments,
        and runs the ``post_process`` callback if set.

        Returns:
            A :class:`ruamel.yaml.comments.CommentedMap` ready for YAML emission.
        """
        # Dump model fields (by alias, excluding None/unset).
        # Suppress Pydantic serialization warnings for Commented wrappers
        # (they survive in fields via the wrap validator and Pydantic doesn't
        # know how to serialize them — we unwrap them immediately after).
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Pydantic serializer warnings",
                category=UserWarning,
            )
            data = self.model_dump(
                by_alias=True,
                exclude_none=True,
                exclude_unset=True,
                exclude={
                    "extras",
                    "post_process",
                    "comment",
                    "eol_comment",
                },
            )

        # Unwrap Commented values that survived model_dump (the serializer
        # doesn't know about them since they're not in field type annotations).
        data = _unwrap_commented_dict(data)

        # Unwrap Raw values
        data = unwrap_raw(data)

        # Recursively serialize nested models
        # We need to walk the original model fields to find nested GhagenModel
        # instances that model_dump() converted to dicts
        self._restore_nested_models(data)

        # Apply canonical key ordering
        cm = to_ordered_commented_map(data, self._get_key_order())

        # Collect per-field comments from Commented wrappers
        field_comments, field_eol_comments = self._collect_commented_fields()

        # Merge extras (handle Commented wrappers in extras values)
        for key, value in self.extras.items():
            if is_commented(value):
                if value.comment:
                    field_comments[key] = value.comment
                if value.eol_comment:
                    field_eol_comments[key] = value.eol_comment
                cm[key] = self._serialize_value(value.value)
            else:
                cm[key] = self._serialize_value(value)

        # Attach field-level comments
        attach_field_comments(
            cm,
            field_comments=field_comments or None,
            field_eol_comments=field_eol_comments or None,
        )

        # Call post_process hook
        if self.post_process is not None:
            self.post_process(cm)

        return cm

    def _restore_nested_models(self, data: dict[str, Any]) -> None:
        """Replace dicts from model_dump with CommentedMaps from nested models."""
        for field_name, field_info in type(self).model_fields.items():
            if field_name in {
                "extras",
                "post_process",
                "comment",
                "eol_comment",
            }:
                continue

            value = getattr(self, field_name, None)
            if value is None:
                continue

            # Unwrap Commented before checking type
            value = unwrap_commented(value)

            # Determine the YAML key name (alias or field name)
            alias = field_info.alias or field_name
            if field_info.validation_alias and isinstance(
                field_info.validation_alias, str
            ):
                alias = field_info.validation_alias
            # serialization_alias takes precedence for output
            ser_alias = (
                field_info.serialization_alias
                if field_info.serialization_alias
                else alias
            )

            if ser_alias not in data:
                continue

            if isinstance(value, GhagenModel):
                data[ser_alias] = value.to_commented_map()
            elif isinstance(value, CommentedMap):
                data[ser_alias] = value
            elif isinstance(value, dict):
                new_dict = CommentedMap()
                for k, v in value.items():
                    new_dict[k] = self._serialize_value(v)
                data[ser_alias] = new_dict
            elif isinstance(value, list):
                data[ser_alias] = self._serialize_list(value)
