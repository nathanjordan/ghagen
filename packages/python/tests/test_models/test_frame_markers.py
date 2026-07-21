"""Tests for the user-frame detection that captures a model's source location.

The ``{source_file}`` header variable and diagnostics rely on
:func:`~ghagen.models._base._find_user_frame` skipping ghagen/pydantic internals
and stopping at the first user-code frame. Round 2 replaced the hand-listed
``/ghagen/models/`` + ``/ghagen/emitter/`` substrings — which mis-attributed
models built via ``helpers/`` or ``pin/`` — with a package-root derivation.
"""

from __future__ import annotations

from ghagen.models._base import (
    _GHAGEN_ROOT,
    _find_user_frame,
    _is_internal_frame,
)


def test_ghagen_root_is_the_package_dir() -> None:
    assert _GHAGEN_ROOT.name == "ghagen"
    assert (_GHAGEN_ROOT / "models" / "_base.py").is_file()


def test_models_frame_is_internal() -> None:
    assert _is_internal_frame(str(_GHAGEN_ROOT / "models" / "step.py"))


def test_emitter_frame_is_internal() -> None:
    assert _is_internal_frame(str(_GHAGEN_ROOT / "emitter" / "nodes.py"))


def test_helpers_frame_is_internal() -> None:
    """The old substring list missed helpers/ — a model built there would have
    mis-attributed its user frame to the helper module."""
    assert _is_internal_frame(str(_GHAGEN_ROOT / "helpers" / "expressions.py"))


def test_pin_frame_is_internal() -> None:
    assert _is_internal_frame(str(_GHAGEN_ROOT / "pin" / "transform.py"))


def test_pydantic_frame_is_internal() -> None:
    assert _is_internal_frame("/some/venv/site-packages/pydantic/main.py")


def test_user_frame_is_not_internal() -> None:
    assert not _is_internal_frame("/home/user/project/build.py")
    # A user directory that merely contains the word "ghagen" as a substring of
    # some other path component must not be treated as internal.
    assert not _is_internal_frame("/home/user/my-ghagen-configs/build.py")


def test_find_user_frame_returns_this_test_file() -> None:
    """Called from user (test) code, the first non-internal frame is here."""
    frame = _find_user_frame()
    assert frame is not None
    filename, _lineno = frame
    assert filename == __file__
