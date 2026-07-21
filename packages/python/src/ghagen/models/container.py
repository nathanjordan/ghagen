"""Container and Service models for GitHub Actions jobs."""

from __future__ import annotations

from typing import ClassVar

from ghagen.models._base import GhagenModel
from ghagen.models.spec import ModelSpec

CONTAINER_SPEC = ModelSpec(
    yaml_keys={
        "image": "image",
        "credentials": "credentials",
        "env": "env",
        "ports": "ports",
        "volumes": "volumes",
        "options": "options",
    },
    order=("image", "credentials", "env", "ports", "volumes", "options"),
)


class Container(GhagenModel):
    """Container configuration for a job or service."""

    SPEC: ClassVar[ModelSpec] = CONTAINER_SPEC

    image: str
    credentials: dict[str, str] | None = None
    env: dict[str, str] | None = None
    ports: list[str | int] | None = None
    volumes: list[str] | None = None
    options: str | None = None


class Service(Container):
    """Service container configuration (identical shape to Container)."""
