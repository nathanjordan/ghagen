"""Container and Service models for GitHub Actions jobs."""

from __future__ import annotations

from ghagen.emitter.key_order import CONTAINER_KEY_ORDER
from ghagen.models._base import GhagenModel


class Container(GhagenModel):
    """Container configuration for a job or service."""

    image: str
    credentials: dict[str, str] | None = None
    env: dict[str, str] | None = None
    ports: list[str | int] | None = None
    volumes: list[str] | None = None
    options: str | None = None

    def _get_key_order(self) -> list[str]:
        return CONTAINER_KEY_ORDER


class Service(Container):
    """Service container configuration (identical shape to Container)."""
