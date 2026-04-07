"""Base model with escape hatches and comment support."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ghagen._raw import Raw
from ghagen.emitter.yaml_writer import (
    attach_comment,
    attach_field_comments,
    to_ordered_commented_map,
    unwrap_raw,
)


class GhagenModel(BaseModel):
    """Base model for all ghagen types.

    Provides:
    - extras: dict of arbitrary key/values merged into YAML output
    - post_process: callback to modify the CommentedMap before emission
    - comment: block comment emitted above this node
    - eol_comment: end-of-line comment
    - field_comments: per-field block comments (keyed by YAML alias)
    - field_eol_comments: per-field end-of-line comments (keyed by YAML alias)
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
    field_comments: dict[str, str] = Field(default_factory=dict, exclude=True)
    field_eol_comments: dict[str, str] = Field(default_factory=dict, exclude=True)

    def _get_key_order(self) -> list[str]:
        """Return the canonical key ordering for this model type.

        Subclasses should override this to provide their specific ordering.
        """
        return []

    def _serialize_value(self, value: Any) -> Any:
        """Recursively serialize a value for YAML output."""
        if isinstance(value, Raw):
            return value.value
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
        # Dump model fields (by alias, excluding None/unset)
        data = self.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude_unset=True,
            exclude={
                "extras",
                "post_process",
                "comment",
                "eol_comment",
                "field_comments",
                "field_eol_comments",
            },
        )

        # Unwrap Raw values
        data = unwrap_raw(data)

        # Recursively serialize nested models
        # We need to walk the original model fields to find nested GhagenModel
        # instances that model_dump() converted to dicts
        self._restore_nested_models(data)

        # Apply canonical key ordering
        cm = to_ordered_commented_map(data, self._get_key_order())

        # Merge extras
        for key, value in self.extras.items():
            cm[key] = self._serialize_value(value)

        # Attach field-level comments
        attach_field_comments(
            cm,
            field_comments=self.field_comments or None,
            field_eol_comments=self.field_eol_comments or None,
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
                "field_comments",
                "field_eol_comments",
            }:
                continue

            value = getattr(self, field_name, None)
            if value is None:
                continue

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
