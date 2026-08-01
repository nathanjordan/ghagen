"""ImageSnapshot model for custom runner-image generation on a Job."""

from __future__ import annotations

import re
from typing import ClassVar

from ghagen.models._base import GhagenModel
from ghagen.models.spec import ModelSpec

IMAGE_SNAPSHOT_SPEC = ModelSpec(
    yaml_keys={"image_name": "image-name", "version": "version"},
    order=("image-name", "version"),
    # Mapping-syntax ``version`` grammar, copied verbatim from the canonical
    # Snapshot (``definitions.snapshot.oneOf[1].properties.version.pattern``)
    # and bound back to it by ``schema/conformance-values.yml``: a major
    # version, optionally a minor version or a ``*`` wildcard. Patch versions
    # are not supported. ``re.ASCII`` matches ECMA-262's ``\d`` (the JSON
    # Schema regex dialect); the flag leaves ``.pattern`` byte-identical to
    # the Snapshot's string.
    patterns={"version": re.compile(r"^\d+(\.\d+|\*)?$", re.ASCII)},
)


class ImageSnapshot(GhagenModel):
    """A custom runner-image generation request on a Job (mapping syntax).

    Maps to ``jobs.<job_id>.snapshot`` using the mapping syntax: an image name
    plus an optional version. The string syntax (image name only) is expressed
    by passing a plain ``str`` to :attr:`~ghagen.models.job.Job.snapshot`
    instead of this model.
    """

    SPEC: ClassVar[ModelSpec] = IMAGE_SNAPSHOT_SPEC

    image_name: str
    version: str | None = None
