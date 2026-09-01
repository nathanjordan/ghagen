"""Tests for the Step model."""

from ghagen import Job, Raw, Step, Workflow
from ghagen.emitter import to_data
from ghagen.models.common import ShellType


def test_basic_run_step():
    assert to_data(Step(name="Run tests", run="pytest")) == {
        "name": "Run tests",
        "run": "pytest",
    }


def test_basic_uses_step():
    # Exhaustive ==: absence of name/run is asserted by equality.
    assert to_data(Step(uses="actions/checkout@v4")) == {"uses": "actions/checkout@v4"}


def test_step_with_alias():
    data = to_data(
        Step(
            name="Setup",
            uses="actions/setup-python@v5",
            with_={"python-version": "3.12"},
        )
    )
    assert data == {
        "name": "Setup",
        "uses": "actions/setup-python@v5",
        "with": {"python-version": "3.12"},
    }


def test_step_if_alias():
    data = to_data(
        Step(
            name="Conditional",
            run="echo 'only on main'",
            if_="github.ref == 'refs/heads/main'",
        )
    )
    assert data["if"] == "github.ref == 'refs/heads/main'"
    assert "if_" not in data


def test_step_shell_typed():
    assert to_data(Step(run="echo hi", shell=ShellType.BASH))["shell"] == "bash"


def test_step_shell_raw_escape():
    assert (
        to_data(Step(run="echo hi", shell=Raw("future-shell")))["shell"]
        == "future-shell"
    )


def test_step_extras():
    data = to_data(Step(uses="actions/checkout@v4", extras={"new-feature": True}))
    assert data["new-feature"] is True


def test_step_key_ordering():
    step = Step(
        run="pytest",
        name="Test",
        id="test-step",
        env={"FOO": "bar"},
        shell=ShellType.BASH,
    )
    keys = list(to_data(step))
    assert keys.index("id") < keys.index("name")
    assert keys.index("name") < keys.index("run")
    assert keys.index("run") < keys.index("env")
    assert keys.index("env") < keys.index("shell")


def test_step_excludes_none_and_unset():
    assert to_data(Step(uses="actions/checkout@v4")) == {"uses": "actions/checkout@v4"}


def test_step_post_process():
    def add_key(cm):
        cm["injected"] = "value"

    # post_process is an emit-time hook (it mutates the backend node), so it is
    # observed through the emitted YAML, not to_data.
    step = Step(uses="actions/checkout@v4", post_process=add_key)
    assert "injected: value" in _wrap(step).to_yaml(header=None)


# --- Dedent-at-emit tests (ADR-0002) ---
#
# Dedent is no longer applied at Step construction. ``Step.run`` holds the
# raw string; the emitter dedents at serialization time, gated by the
# ``auto_dedent`` flag.


def _wrap(step: Step) -> Workflow:
    """Wrap a step in a minimal workflow so it can be serialized to YAML."""
    return Workflow(
        name="W",
        on={"push": {}},
        jobs={"j": Job(runs_on="ubuntu-latest", steps=[step])},
    )


def test_run_is_raw_at_construction():
    """Construction no longer dedents: ``run`` holds the raw string."""
    step = Step(
        run="""
            echo hello
            echo world
        """
    )
    assert step.run == "\n            echo hello\n            echo world\n        "


def test_run_none():
    step = Step(uses="actions/checkout@v4")
    assert step.run is None


def test_to_data_defaults_dedent_dedents_run():
    """``to_data`` defaults ``auto_dedent=True``, matching ``to_yaml``."""
    step = Step(name="Build", run="\n    echo building\n    make all\n")
    assert to_data(step)["run"] == "echo building\nmake all\n"


def test_to_data_auto_dedent_false_keeps_raw_run():
    """``to_data(auto_dedent=False)`` keeps a Step's ``run`` string as authored."""
    step = Step(name="Build", run="\n    echo building\n    make all\n")
    data = to_data(step, auto_dedent=False)
    assert data["run"] == "\n    echo building\n    make all\n"


def test_to_yaml_dedents_by_default():
    """Default emit dedents each Step's ``run`` (common indent removed)."""
    step = Step(
        name="Build",
        run="""
            echo building
            make all
        """,
    )
    wf = _wrap(step)
    dedented = wf.to_yaml(header=None)
    raw = wf.to_yaml(header=None, auto_dedent=False)
    # Dedent changes the output, and the deep source indentation is gone.
    assert dedented != raw
    assert "            echo building" not in dedented


def test_to_yaml_auto_dedent_false_skips_dedent():
    """``auto_dedent=False`` emits the raw ``run`` string verbatim."""
    step = Step(
        name="Build",
        run="""
            echo building
            make all
        """,
    )
    yaml = _wrap(step).to_yaml(header=None, auto_dedent=False)
    assert "            echo building" in yaml


def test_to_yaml_does_not_mutate_caller_model():
    """The dedent pass runs on a copy; the caller's ``run`` stays raw."""
    raw = "\n            echo hello\n        "
    step = Step(run=raw)
    _wrap(step).to_yaml(header=None)
    assert step.run == raw
