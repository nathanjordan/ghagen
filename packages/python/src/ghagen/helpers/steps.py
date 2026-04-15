"""Pre-built factory functions for common GitHub Actions steps."""

from __future__ import annotations

from typing import Any

from ghagen.models.step import Step

# Action version constants
_CHECKOUT = "actions/checkout@v6"
_SETUP_PYTHON = "actions/setup-python@v6"
_SETUP_NODE = "actions/setup-node@v6"
_SETUP_UV = "astral-sh/setup-uv@v7"
_CACHE = "actions/cache@v4"
_UPLOAD_ARTIFACT = "actions/upload-artifact@v4"
_DOWNLOAD_ARTIFACT = "actions/download-artifact@v4"


def _build_with(
    params: dict[str, Any],
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build a ``with_`` dict, filtering None values and merging overrides."""
    result = {k: v for k, v in params.items() if v is not None}
    if overrides:
        result.update(overrides)
    return result or None


def checkout(
    *,
    ref: str | None = None,
    fetch_depth: int | None = 1,
    **kwargs: Any,
) -> Step:
    """Create a checkout step using ``actions/checkout@v6``.

    Args:
        ref: Git reference to check out (branch, tag, or SHA).
            Defaults to the triggering ref.
        fetch_depth: Number of commits to fetch. Set to ``0`` for a full
            clone. Defaults to ``1`` (shallow clone).
        **kwargs: Additional keyword arguments passed to
            :class:`~ghagen.models.step.Step` (e.g., ``name``, ``if_``,
            ``env``). A ``with_`` dict is merged with the built-in
            parameters.

    Returns:
        A configured :class:`~ghagen.models.step.Step`.
    """
    with_overrides = kwargs.pop("with_", None)
    with_ = _build_with(
        {"ref": ref, "fetch-depth": fetch_depth},
        overrides=with_overrides,
    )
    return Step(
        name=kwargs.pop("name", "Checkout"),
        uses=_CHECKOUT,
        with_=with_,
        **kwargs,
    )


def setup_python(
    version: str,
    *,
    cache: str | None = None,
    **kwargs: Any,
) -> Step:
    """Create a Python setup step using ``actions/setup-python@v6``.

    Args:
        version: Python version string (e.g., ``"3.12"`` or
            ``"${{ matrix.python-version }}"``).
        cache: Package manager to cache (e.g., ``"pip"``, ``"uv"``).
        **kwargs: Additional keyword arguments passed to
            :class:`~ghagen.models.step.Step`. A ``with_`` dict is merged
            with the built-in parameters.

    Returns:
        A configured :class:`~ghagen.models.step.Step`.
    """
    with_overrides = kwargs.pop("with_", None)
    with_ = _build_with(
        {"python-version": version, "cache": cache},
        overrides=with_overrides,
    )
    return Step(
        name=kwargs.pop("name", "Set up Python"),
        uses=_SETUP_PYTHON,
        with_=with_,
        **kwargs,
    )


def setup_node(
    version: str,
    *,
    cache: str | None = None,
    **kwargs: Any,
) -> Step:
    """Create a Node.js setup step using ``actions/setup-node@v6``.

    Args:
        version: Node.js version string (e.g., ``"20"``).
        cache: Package manager to cache (e.g., ``"npm"``, ``"yarn"``).
        **kwargs: Additional keyword arguments passed to
            :class:`~ghagen.models.step.Step`. A ``with_`` dict is merged
            with the built-in parameters.

    Returns:
        A configured :class:`~ghagen.models.step.Step`.
    """
    with_overrides = kwargs.pop("with_", None)
    with_ = _build_with(
        {"node-version": version, "cache": cache},
        overrides=with_overrides,
    )
    return Step(
        name=kwargs.pop("name", "Set up Node.js"),
        uses=_SETUP_NODE,
        with_=with_,
        **kwargs,
    )


def setup_uv(
    *,
    version: str | None = None,
    **kwargs: Any,
) -> Step:
    """Create a uv setup step using ``astral-sh/setup-uv@v7``.

    Args:
        version: Specific uv version to install. If ``None``, uses the
            latest release.
        **kwargs: Additional keyword arguments passed to
            :class:`~ghagen.models.step.Step`. A ``with_`` dict is merged
            with the built-in parameters.

    Returns:
        A configured :class:`~ghagen.models.step.Step`.
    """
    with_overrides = kwargs.pop("with_", None)
    with_ = _build_with(
        {"version": version},
        overrides=with_overrides,
    )
    return Step(
        name=kwargs.pop("name", "Set up uv"),
        uses=_SETUP_UV,
        with_=with_,
        **kwargs,
    )


def cache(
    key: str,
    path: str,
    *,
    restore_keys: str | list[str] | None = None,
    **kwargs: Any,
) -> Step:
    """Create a cache step using ``actions/cache@v4``.

    Args:
        key: Cache key (e.g.,
            ``"${{ runner.os }}-pip-${{ hashFiles('...') }}"``).
        path: Path(s) to cache.
        restore_keys: Fallback key(s) for partial cache matches. A list
            is joined with newlines.
        **kwargs: Additional keyword arguments passed to
            :class:`~ghagen.models.step.Step`. A ``with_`` dict is merged
            with the built-in parameters.

    Returns:
        A configured :class:`~ghagen.models.step.Step`.
    """
    rk = restore_keys
    if isinstance(rk, list):
        rk = "\n".join(rk)
    with_overrides = kwargs.pop("with_", None)
    with_ = _build_with(
        {"key": key, "path": path, "restore-keys": rk},
        overrides=with_overrides,
    )
    return Step(
        name=kwargs.pop("name", "Cache"),
        uses=_CACHE,
        with_=with_,
        **kwargs,
    )


def upload_artifact(
    name: str,
    path: str,
    **kwargs: Any,
) -> Step:
    """Create an upload-artifact step using ``actions/upload-artifact@v4``.

    Args:
        name: Name for the artifact.
        path: File or directory path to upload.
        **kwargs: Additional keyword arguments passed to
            :class:`~ghagen.models.step.Step`. A ``with_`` dict is merged
            with the built-in parameters.

    Returns:
        A configured :class:`~ghagen.models.step.Step`.
    """
    with_overrides = kwargs.pop("with_", None)
    with_ = _build_with(
        {"name": name, "path": path},
        overrides=with_overrides,
    )
    return Step(
        name=kwargs.pop("name", "Upload artifact"),
        uses=_UPLOAD_ARTIFACT,
        with_=with_,
        **kwargs,
    )


def download_artifact(
    name: str,
    *,
    path: str | None = None,
    **kwargs: Any,
) -> Step:
    """Create a download-artifact step using ``actions/download-artifact@v4``.

    Args:
        name: Name of the artifact to download.
        path: Destination path. Defaults to the workspace directory.
        **kwargs: Additional keyword arguments passed to
            :class:`~ghagen.models.step.Step`. A ``with_`` dict is merged
            with the built-in parameters.

    Returns:
        A configured :class:`~ghagen.models.step.Step`.
    """
    with_overrides = kwargs.pop("with_", None)
    with_ = _build_with(
        {"name": name, "path": path},
        overrides=with_overrides,
    )
    return Step(
        name=kwargs.pop("name", "Download artifact"),
        uses=_DOWNLOAD_ARTIFACT,
        with_=with_,
        **kwargs,
    )
