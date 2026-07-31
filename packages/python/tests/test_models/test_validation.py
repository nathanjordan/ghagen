"""Construction-time validation invariants shared by every GhagenModel.

The models' documented promise is that a model validates when it is
constructed. These tests pin the two ways that promise used to be hollow:
unknown keyword arguments were silently dropped, and ``Raw[T]`` in a union
absorbed any value at all.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ghagen import Raw
from ghagen.models.common import ShellType
from ghagen.models.job import Job
from ghagen.models.permissions import Permissions
from ghagen.models.step import Step


class TestUnknownFieldsRejected:
    """``extra="forbid"`` — a misspelled field name is an error, not a no-op."""

    def test_misspelled_field_raises(self):
        with pytest.raises(ValidationError, match="nmae"):
            Step(nmae="build")  # type: ignore[call-arg]

    def test_misspelled_field_on_nested_model_raises(self):
        with pytest.raises(ValidationError, match="runs_onn"):
            Job(runs_onn="ubuntu-latest", steps=[])  # type: ignore[call-arg]

    def test_extras_is_still_the_sanctioned_channel(self):
        step = Step(name="build", extras={"x-custom": "value"})
        assert step.extras == {"x-custom": "value"}


class TestRawIsOptIn:
    """``Raw[T]`` in a union must not absorb unwrapped values.

    Auto-wrapping made every union containing ``Raw`` accept anything, which
    disabled the enum / ``Literal`` constraint sitting beside it.
    """

    def test_shell_enum_constraint_holds(self):
        with pytest.raises(ValidationError):
            Step(run="echo hi", shell="powershel")  # type: ignore[arg-type]

    def test_shell_accepts_the_enum(self):
        assert Step(run="echo hi", shell=ShellType.BASH).shell == "bash"

    def test_shell_escape_hatch_is_explicit(self):
        step = Step(run="echo hi", shell=Raw("future-shell-type"))
        assert step.shell == Raw("future-shell-type")

    def test_permission_level_constraint_holds(self):
        with pytest.raises(ValidationError):
            Permissions(contents="reed")  # type: ignore[arg-type]

    def test_permission_escape_hatch_is_explicit(self):
        assert Permissions(contents=Raw("future-level")).contents == Raw(
            "future-level"
        )

    def test_runs_on_rejects_a_non_string(self):
        with pytest.raises(ValidationError):
            Job(runs_on=object(), steps=[])  # type: ignore[arg-type]
