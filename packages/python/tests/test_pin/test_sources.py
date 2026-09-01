"""Tests for ghagen.pin.sources — source file tracking and ref location."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from ghagen.config import resolve_app
from ghagen.pin.sources import locate_uses_refs, track_user_files


class TestResolveApp:
    """Direct tests for the shared module -> App policy (mirrors TS resolveApp)."""

    def test_resolves_module_app(self):
        from ghagen.app import App

        app = App(lockfile=None)
        resolved, error = resolve_app(SimpleNamespace(app=app), Path("cfg.py"))
        assert error is None
        assert resolved is app

    def test_resolves_create_app_factory(self):
        from ghagen.app import App

        app = App(lockfile=None)
        resolved, error = resolve_app(
            SimpleNamespace(create_app=lambda: app), Path("cfg.py")
        )
        assert error is None
        assert resolved is app

    def test_prefers_create_app_over_app(self):
        from ghagen.app import App

        created = App(lockfile=None)
        exported = App(lockfile=None)
        resolved, _ = resolve_app(
            SimpleNamespace(create_app=lambda: created, app=exported), Path("cfg.py")
        )
        assert resolved is created

    def test_non_app_app_is_error(self):
        resolved, error = resolve_app(SimpleNamespace(app=object()), Path("cfg.py"))
        assert resolved is None
        assert error is not None
        assert error.kind == "app-resolution"

    def test_create_app_returning_non_app_is_error(self):
        resolved, error = resolve_app(
            SimpleNamespace(create_app=lambda: object()), Path("cfg.py")
        )
        assert resolved is None
        assert error is not None
        assert error.kind == "app-resolution"

    def test_neither_app_nor_create_app_is_error(self):
        resolved, error = resolve_app(SimpleNamespace(unrelated=True), Path("cfg.py"))
        assert resolved is None
        assert error is not None
        assert error.kind == "app-resolution"


class TestTrackUserFiles:
    """Integration tests for :func:`track_user_files`.

    ``track_user_files`` now imports the config itself and resolves its ``App``
    through :func:`ghagen.config.resolve_app` — no injected loader. The
    internal-vs-user path classification it applies is unit-tested directly in
    ``tests/test_package_paths.py``; these tests cover the end-to-end wiring.
    """

    def test_returns_app_and_tracks_config(self, tmp_path: Path):
        """The resolved App is returned and the config file is tracked."""
        from ghagen.app import App

        config = tmp_path / "user_wf.py"
        config.write_text("from ghagen.app import App\napp = App(lockfile=None)\n")

        app, user_files = track_user_files(config)

        assert isinstance(app, App)
        assert config.resolve() in user_files

    def test_create_app_factory_is_resolved(self, tmp_path: Path):
        """A ``create_app()`` factory is resolved just like a module ``app``."""
        from ghagen.app import App

        config = tmp_path / "factory_wf.py"
        config.write_text(
            "from ghagen.app import App\n"
            "def create_app():\n"
            "    return App(lockfile=None)\n"
        )

        app, user_files = track_user_files(config)

        assert isinstance(app, App)
        assert config.resolve() in user_files

    def test_lazy_create_app_import_is_tracked(self, tmp_path: Path):
        """A helper imported lazily inside ``create_app()`` is tracked.

        Regression guard (ADR-0004): the module is only added to ``sys.modules``
        when the factory runs, so App resolution must happen inside the
        ``sys.modules`` snapshot window — otherwise the helper's ``uses:`` refs
        would be silently left un-rewritten.
        """
        helper = tmp_path / "lazy_helper.py"
        helper.write_text('CHECKOUT = "actions/checkout@v4"\n')

        config = tmp_path / "lazy_cfg.py"
        config.write_text(
            "from ghagen.app import App\n"
            "def create_app():\n"
            "    import lazy_helper  # imported only when the factory runs\n"
            "    _ = lazy_helper.CHECKOUT\n"
            "    return App(lockfile=None)\n"
        )

        try:
            _app, user_files = track_user_files(config)
            assert helper.resolve() in user_files
        finally:
            sys.modules.pop("lazy_helper", None)

    def test_sys_path_insertion_is_scoped_to_the_import(self, tmp_path: Path):
        """``track_user_files`` leaves ``sys.path`` exactly as it found it.

        Both halves matter. The config's sibling helper must still resolve
        *during* the call (asserting only restoration would also pass if the
        insertion were simply deleted), and the entry must be gone afterwards
        — otherwise every config load permanently prepends its directory to the
        host process's module search path, shadowing later unrelated imports.
        """
        helper = tmp_path / "scoped_helper.py"
        helper.write_text('CHECKOUT = "actions/checkout@v4"\n')

        config = tmp_path / "scoped_cfg.py"
        config.write_text(
            "import scoped_helper\n"
            "from ghagen.app import App\n"
            "_ = scoped_helper.CHECKOUT\n"
            "app = App(lockfile=None)\n"
        )

        parent = str(tmp_path.resolve())
        before = list(sys.path)
        assert parent not in before

        try:
            _app, user_files = track_user_files(config)
            # The insertion was load-bearing during the import.
            assert helper.resolve() in user_files
        finally:
            sys.modules.pop("scoped_helper", None)

        assert sys.path == before

    def test_sys_path_entry_the_caller_owns_is_left_alone(self, tmp_path: Path):
        """Idempotency: only an entry this call inserted is removed."""
        config = tmp_path / "owned_cfg.py"
        config.write_text("from ghagen.app import App\napp = App(lockfile=None)\n")

        parent = str(tmp_path.resolve())
        sys.path.insert(0, parent)
        try:
            track_user_files(config)
            assert parent in sys.path
        finally:
            sys.path.remove(parent)

    def test_sys_path_entry_is_removed_even_if_something_shifts_it(
        self, tmp_path: Path
    ):
        """Regression (issue 28 #2): cleanup must not depend on index 0.

        If anything executed during ``resolve_app`` — the user's own config
        module, most plausibly — inserts its own entry at ``sys.path[0]``,
        the tracked entry this call inserted is pushed to a later index. A
        position-based guard (``sys.path[0] == parent``) then finds a
        different value at index 0 and silently declines to clean up,
        leaking the entry for the life of the process. Removal must be by
        identity, not position.
        """
        other = tmp_path / "other"
        other.mkdir()

        config = tmp_path / "shifting_cfg.py"
        config.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(other)!r})\n"
            "from ghagen.app import App\n"
            "app = App(lockfile=None)\n"
        )

        parent = str(tmp_path.resolve())
        before = list(sys.path)
        assert parent not in before

        leaked = True  # pessimistic default in case track_user_files raises
        try:
            track_user_files(config)
            # Captured *before* any cleanup below — the whole point of this
            # test is to observe whether ``track_user_files`` itself removed
            # the entry, not to clean it up ourselves and then check.
            leaked = parent in sys.path
        finally:
            # Defensive cleanup so this test never pollutes later tests'
            # sys.path, run only *after* `leaked` above was captured. This is
            # exactly the fragility issue 28 calls out; the assertion below,
            # not this cleanup, is what actually proves the fix.
            sys.modules.pop("ghagen_config", None)
            if str(other) in sys.path:
                sys.path.remove(str(other))
            if parent in sys.path:
                sys.path.remove(parent)

        assert not leaked, (
            "sys.path leaked the config's parent directory: something else "
            "inserted ahead of it at index 0 during import, and cleanup did "
            "not follow"
        )

    def test_excludes_ghagen_internals(self, tmp_path: Path):
        """Modules from the ghagen package itself should not appear."""
        config = tmp_path / "my_config.py"
        config.write_text("from ghagen.app import App\napp = App(lockfile=None)\n")

        _app, user_files = track_user_files(config)

        import ghagen

        ghagen_root = Path(ghagen.__file__).resolve().parent
        for f in user_files:
            assert not str(f).startswith(str(ghagen_root)), (
                f"ghagen internal file leaked: {f}"
            )

    def test_excludes_site_packages(self, tmp_path: Path):
        """Modules under a site-packages directory should be excluded."""
        # Simulate a site-packages path the config imports from.
        site_pkg = tmp_path / "lib" / "site-packages" / "vendored.py"
        site_pkg.parent.mkdir(parents=True)
        site_pkg.write_text("X = 1\n")

        config = tmp_path / "user_cfg.py"
        config.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(site_pkg.parent)!r})\n"
            "import vendored\n"
            "from ghagen.app import App\n"
            "app = App(lockfile=None)\n"
        )

        try:
            _app, user_files = track_user_files(config)

            # The user config IS included
            assert config.resolve() in user_files
            # The site-packages module is NOT included
            assert site_pkg.resolve() not in user_files
        finally:
            sys.modules.pop("vendored", None)
            if str(site_pkg.parent) in sys.path:
                sys.path.remove(str(site_pkg.parent))


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
