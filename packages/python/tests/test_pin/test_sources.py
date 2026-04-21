"""Tests for ghagen.pin.sources — source file tracking and ref location."""

from __future__ import annotations

import sys
from pathlib import Path

from ghagen.pin.sources import locate_uses_refs, track_user_files


class TestTrackUserFiles:
    def test_excludes_ghagen_internals(self, tmp_path: Path):
        """Modules from the ghagen package itself should not appear."""
        config = tmp_path / "my_config.py"
        config.write_text(
            "from ghagen.app import App\ndef load():\n    return App(lockfile=None)\n"
        )

        sys.path.insert(0, str(tmp_path))
        try:
            # Ensure our temp module is not already loaded
            mod_name = "my_config"
            sys.modules.pop(mod_name, None)

            def app_loader():
                import importlib

                mod = importlib.import_module(mod_name)
                return mod.load()

            user_files = track_user_files(app_loader)

            # The config file should be in the set
            assert config.resolve() in user_files

            # No ghagen internal files should be present
            import ghagen

            ghagen_root = Path(ghagen.__file__).resolve().parent
            for f in user_files:
                assert not str(f).startswith(str(ghagen_root)), (
                    f"ghagen internal file leaked: {f}"
                )
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop(mod_name, None)

    def test_includes_user_config(self, tmp_path: Path):
        """A user module that creates an App should be included."""
        config = tmp_path / "user_wf.py"
        config.write_text(
            "from ghagen.app import App\ndef load():\n    return App(lockfile=None)\n"
        )

        sys.path.insert(0, str(tmp_path))
        try:
            mod_name = "user_wf"
            sys.modules.pop(mod_name, None)

            def app_loader():
                import importlib

                mod = importlib.import_module(mod_name)
                return mod.load()

            user_files = track_user_files(app_loader)
            assert config.resolve() in user_files
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop(mod_name, None)

    def test_excludes_site_packages(self, tmp_path: Path):
        """Modules under a site-packages directory should be excluded."""
        # Simulate a site-packages path
        site_pkg = tmp_path / "lib" / "site-packages" / "vendored.py"
        site_pkg.parent.mkdir(parents=True)
        site_pkg.write_text("X = 1\n")

        config = tmp_path / "user_cfg.py"
        config.write_text(
            "import sys, os\n"
            f"sys.path.insert(0, {str(site_pkg.parent)!r})\n"
            "import vendored\n"
            "from ghagen.app import App\n"
            "def load():\n"
            "    return App(lockfile=None)\n"
        )

        sys.path.insert(0, str(tmp_path))
        sys.path.insert(0, str(site_pkg.parent))
        try:
            for mod_name in ("user_cfg", "vendored"):
                sys.modules.pop(mod_name, None)

            def app_loader():
                import importlib

                mod = importlib.import_module("user_cfg")
                return mod.load()

            user_files = track_user_files(app_loader)

            # The user config IS included
            assert config.resolve() in user_files

            # The site-packages module is NOT included
            assert site_pkg.resolve() not in user_files
        finally:
            sys.path.remove(str(tmp_path))
            if str(site_pkg.parent) in sys.path:
                sys.path.remove(str(site_pkg.parent))
            sys.modules.pop("user_cfg", None)
            sys.modules.pop("vendored", None)


class TestLocateUsesRefs:
    def test_ref_in_single_file(self, tmp_path: Path):
        f1 = tmp_path / "wf.py"
        f1.write_text('Step(uses="actions/checkout@v4")\n')

        result = locate_uses_refs({"actions/checkout@v4"}, {f1})
        assert result == {"actions/checkout@v4": [f1]}

    def test_ref_in_multiple_files(self, tmp_path: Path):
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text('uses="actions/checkout@v4"\n')
        f2.write_text('Step(uses="actions/checkout@v4")\n')

        result = locate_uses_refs({"actions/checkout@v4"}, {f1, f2})
        assert "actions/checkout@v4" in result
        assert sorted(result["actions/checkout@v4"]) == sorted([f1, f2])

    def test_ref_not_found(self, tmp_path: Path):
        f1 = tmp_path / "wf.py"
        f1.write_text('Step(uses="actions/checkout@v4")\n')

        result = locate_uses_refs({"other/action@v1"}, {f1})
        assert result == {}

    def test_multiple_refs_partial_match(self, tmp_path: Path):
        f1 = tmp_path / "wf.py"
        f1.write_text(
            'Step(uses="actions/checkout@v4")\nStep(uses="actions/setup-python@v5")\n'
        )

        result = locate_uses_refs(
            {"actions/checkout@v4", "actions/setup-python@v5", "missing/ref@v1"},
            {f1},
        )
        assert "actions/checkout@v4" in result
        assert "actions/setup-python@v5" in result
        assert "missing/ref@v1" not in result

    def test_empty_refs(self, tmp_path: Path):
        f1 = tmp_path / "wf.py"
        f1.write_text("some content\n")

        result = locate_uses_refs(set(), {f1})
        assert result == {}

    def test_empty_files(self):
        result = locate_uses_refs({"actions/checkout@v4"}, set())
        assert result == {}
