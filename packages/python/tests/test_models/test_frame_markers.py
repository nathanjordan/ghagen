"""Tests for the user-frame stack walk that captures a model's source location.

The ``{source_file}`` header variable and diagnostics rely on
:func:`~ghagen.models._base._find_user_frame` skipping ghagen/pydantic internals
and stopping at the first user-code frame. The frame *classification* it walks
over lives in :mod:`ghagen._package_paths` and is tested in
``test_package_paths.py``; this file covers only the stack walk itself.
"""

from __future__ import annotations

from ghagen.models._base import _find_user_frame


def test_find_user_frame_returns_this_test_file() -> None:
    """Called from user (test) code, the first non-internal frame is here."""
    frame = _find_user_frame()
    assert frame is not None
    filename, _lineno = frame
    assert filename == __file__
