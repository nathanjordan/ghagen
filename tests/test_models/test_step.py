"""Tests for the Step model."""

import ghagen._dedent as _dedent_mod
from ghagen import Raw, Step
from ghagen.models.common import ShellType


def test_basic_run_step():
    step = Step(name="Run tests", run="pytest")
    cm = step.to_commented_map()
    assert cm["name"] == "Run tests"
    assert cm["run"] == "pytest"


def test_basic_uses_step():
    step = Step(uses="actions/checkout@v4")
    cm = step.to_commented_map()
    assert cm["uses"] == "actions/checkout@v4"
    assert "name" not in cm
    assert "run" not in cm


def test_step_with_alias():
    step = Step(
        name="Setup",
        uses="actions/setup-python@v5",
        with_={"python-version": "3.12"},
    )
    cm = step.to_commented_map()
    assert "with" in cm
    assert cm["with"]["python-version"] == "3.12"
    assert "with_" not in cm


def test_step_if_alias():
    step = Step(
        name="Conditional",
        run="echo 'only on main'",
        if_="github.ref == 'refs/heads/main'",
    )
    cm = step.to_commented_map()
    assert "if" in cm
    assert cm["if"] == "github.ref == 'refs/heads/main'"
    assert "if_" not in cm


def test_step_shell_typed():
    step = Step(run="echo hi", shell=ShellType.BASH)
    cm = step.to_commented_map()
    assert cm["shell"] == "bash"


def test_step_shell_raw_escape():
    step = Step(run="echo hi", shell=Raw("future-shell"))
    cm = step.to_commented_map()
    assert cm["shell"] == "future-shell"


def test_step_extras():
    step = Step(
        uses="actions/checkout@v4",
        extras={"new-feature": True},
    )
    cm = step.to_commented_map()
    assert cm["new-feature"] is True


def test_step_key_ordering():
    step = Step(
        run="pytest",
        name="Test",
        id="test-step",
        env={"FOO": "bar"},
        shell=ShellType.BASH,
    )
    cm = step.to_commented_map()
    keys = list(cm.keys())
    assert keys.index("id") < keys.index("name")
    assert keys.index("name") < keys.index("run")
    assert keys.index("run") < keys.index("env")
    assert keys.index("env") < keys.index("shell")


def test_step_excludes_none_and_unset():
    step = Step(uses="actions/checkout@v4")
    cm = step.to_commented_map()
    assert "name" not in cm
    assert "run" not in cm
    assert "shell" not in cm
    assert "timeout-minutes" not in cm


def test_step_post_process():
    def add_key(cm):
        cm["injected"] = "value"

    step = Step(uses="actions/checkout@v4", post_process=add_key)
    cm = step.to_commented_map()
    assert cm["injected"] == "value"


# --- Auto-dedent tests ---


def test_run_auto_dedent_triple_quoted():
    step = Step(
        run="""
            echo hello
            echo world
        """
    )
    assert step.run == "echo hello\necho world"


def test_run_auto_dedent_preserves_relative_indent():
    step = Step(
        run="""
            if [ -f config ]; then
                source config
            fi
        """
    )
    assert step.run == "if [ -f config ]; then\n    source config\nfi"


def test_run_auto_dedent_single_line_noop():
    step = Step(run="pytest")
    assert step.run == "pytest"


def test_run_auto_dedent_newline_concat_noop():
    step = Step(run="echo hello\necho world")
    assert step.run == "echo hello\necho world"


def test_run_none():
    step = Step(uses="actions/checkout@v4")
    assert step.run is None


def test_run_auto_dedent_disabled():
    original = _dedent_mod.auto_dedent
    try:
        _dedent_mod.auto_dedent = False
        step = Step(
            run="""
                echo hello
            """
        )
        # With auto_dedent disabled, the raw string passes through.
        assert "                echo hello" in step.run
    finally:
        _dedent_mod.auto_dedent = original


def test_run_auto_dedent_to_commented_map():
    """End-to-end: triple-quoted run through to CommentedMap."""
    step = Step(
        name="Build",
        run="""
            echo building
            make all
        """,
    )
    cm = step.to_commented_map()
    assert cm["run"] == "echo building\nmake all"
