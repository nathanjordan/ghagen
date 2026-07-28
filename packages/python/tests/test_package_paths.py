"""Tests for the shared ghagen-internal vs. user-authored path predicates.

:mod:`ghagen._package_paths` is the single home for both classifications —
:func:`is_internal_frame` (stack attribution, used by ``models/_base.py``) and
:func:`is_user_file` (import tracking, used by ``pin/sources.py``) — over one
shared ``GHAGEN_ROOT``. This suite merges the matrices that previously lived in
``test_frame_markers.py`` (the frame predicate) and ``test_pin/test_sources.py``
(the user-file predicate) onto that one module.
"""

from __future__ import annotations

import sysconfig
from pathlib import Path

from ghagen._package_paths import GHAGEN_ROOT, is_internal_frame, is_user_file


class TestGhagenRoot:
    def test_root_is_the_package_dir(self) -> None:
        assert GHAGEN_ROOT.name == "ghagen"
        assert (GHAGEN_ROOT / "models" / "_base.py").is_file()
        assert (GHAGEN_ROOT / "_package_paths.py").is_file()


class TestIsInternalFrame:
    def test_models_frame_is_internal(self) -> None:
        assert is_internal_frame(str(GHAGEN_ROOT / "models" / "step.py"))

    def test_emitter_frame_is_internal(self) -> None:
        assert is_internal_frame(str(GHAGEN_ROOT / "emitter" / "nodes.py"))

    def test_helpers_frame_is_internal(self) -> None:
        """A model built in helpers/ must attribute past the helper module."""
        assert is_internal_frame(str(GHAGEN_ROOT / "helpers" / "expressions.py"))

    def test_pin_frame_is_internal(self) -> None:
        assert is_internal_frame(str(GHAGEN_ROOT / "pin" / "transform.py"))

    def test_pydantic_frame_is_internal(self) -> None:
        assert is_internal_frame("/some/venv/site-packages/pydantic/main.py")

    def test_user_frame_is_not_internal(self) -> None:
        assert not is_internal_frame("/home/user/project/build.py")
        # A user directory that merely contains the word "ghagen" as a substring
        # of some other path component must not be treated as internal.
        assert not is_internal_frame("/home/user/my-ghagen-configs/build.py")


class TestIsUserFile:
    def test_plain_user_file_is_user_file(self) -> None:
        assert is_user_file(Path("/home/user/project/build.py"))

    def test_ghagen_internal_is_not_user_file(self) -> None:
        assert not is_user_file(GHAGEN_ROOT / "models" / "step.py")
        assert not is_user_file(GHAGEN_ROOT / "pin" / "sources.py")

    def test_site_packages_is_not_user_file(self) -> None:
        assert not is_user_file(Path("/env/lib/python3.13/site-packages/vendored.py"))

    def test_stdlib_is_not_user_file(self) -> None:
        stdlib_dir = sysconfig.get_paths()["stdlib"]
        assert not is_user_file(Path(stdlib_dir) / "json" / "__init__.py")
