"""ImageSnapshot model for custom runner-image generation on a Job."""

from __future__ import annotations

import re
from typing import ClassVar

from pydantic import Field, field_validator

from ghagen.models._base import GhagenModel
from ghagen.models.spec import ModelSpec

IMAGE_SNAPSHOT_SPEC = ModelSpec(
    yaml_keys={"image_name": "image-name", "version": "version"},
    order=("image-name", "version"),
)

# Mapping-syntax ``version`` grammar from the workflow schema
# (``definitions.snapshot``): a major version, optionally a minor version or a
# ``*`` wildcard. Patch versions are not supported.
_VERSION_PATTERN = re.compile(r"^\d+(\.\d+|\*)?$")


class ImageSnapshot(GhagenModel):
    """A custom runner-image generation request on a Job (mapping syntax).

    Maps to ``jobs.<job_id>.snapshot`` using the mapping syntax: an image name
    plus an optional version. The string syntax (image name only) is expressed
    by passing a plain ``str`` to :attr:`~ghagen.models.job.Job.snapshot`
    instead of this model.
    """

    SPEC: ClassVar[ModelSpec] = IMAGE_SNAPSHOT_SPEC

    image_name: str = Field(serialization_alias="image-name")
    version: str | None = None

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str | None) -> str | None:
        if value is not None and not _VERSION_PATTERN.match(value):
            raise ValueError(
                f"version {value!r} must match {_VERSION_PATTERN.pattern} "
                "(e.g. '1', '1.2', '1*'); patch versions are not supported"
            )
        return value
