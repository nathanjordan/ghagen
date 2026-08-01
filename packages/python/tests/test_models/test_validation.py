"""Construction-time validation invariants shared by every GhagenModel.

The models' documented promise is that a model validates when it is
constructed. These tests pin the three ways that promise used to be hollow:
unknown keyword arguments were silently dropped, ``Raw[T]`` in a union absorbed
any value at all, and a union that named only ``str`` constrained nothing.

The TypeScript peer is
``packages/typescript/src/models/validation.test.ts``; both files pin the same
invariants, since parity is of the invariant rather than of the exception class
(Pydantic's ``ValidationError`` vs TypeScript's ``ModelInputError``).
"""

from __future__ import annotations

import re
from typing import ClassVar

import pytest
from pydantic import ValidationError

from ghagen import Raw
from ghagen.models._base import GhagenModel
from ghagen.models.common import ShellType
from ghagen.models.job import Job
from ghagen.models.permissions import Permissions
from ghagen.models.spec import ModelSpec
from ghagen.models.step import Step
from ghagen.models.trigger import WorkflowCallInput, WorkflowDispatchInput


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
        assert Permissions(contents=Raw("future-level")).contents == Raw("future-level")

    def test_runs_on_rejects_a_non_string(self):
        with pytest.raises(ValidationError):
            Job(runs_on=object(), steps=[])  # type: ignore[arg-type]

    def test_workflow_dispatch_input_type_constraint_holds(self):
        with pytest.raises(ValidationError):
            WorkflowDispatchInput(type="chioce")  # type: ignore[arg-type]

    def test_workflow_dispatch_input_type_accepts_its_five_members(self):
        for value in ("boolean", "number", "string", "choice", "environment"):
            assert WorkflowDispatchInput(type=value).type == value  # type: ignore[arg-type]

    def test_workflow_dispatch_input_type_escape_hatch_is_explicit(self):
        assert WorkflowDispatchInput(type=Raw("future-type")).type == Raw("future-type")

    def test_workflow_call_input_type_constraint_holds(self):
        with pytest.raises(ValidationError):
            WorkflowCallInput(type="chioce")  # type: ignore[arg-type]

    def test_workflow_call_input_type_rejects_the_dispatch_only_members(self):
        # The schema gives workflow_call a *narrower* set than
        # workflow_dispatch, and the TypeScript port already rejects these two.
        for value in ("choice", "environment"):
            with pytest.raises(ValidationError):
                WorkflowCallInput(type=value)  # type: ignore[arg-type]

    def test_workflow_call_input_type_escape_hatch_is_explicit(self):
        assert WorkflowCallInput(type=Raw("future-type")).type == Raw("future-type")

    def test_workflow_call_input_type_is_required(self):
        # `"required": ["type"]` in the canonical Snapshot; the TypeScript port
        # already declares it non-optional.
        with pytest.raises(ValidationError):
            WorkflowCallInput()  # type: ignore[call-arg]


class TestDeclaredGrammars:
    """``SPEC.patterns`` is enforced at construction, and skips non-strings.

    The peer of TypeScript's `buildYamlData` grammar check. Declared on a
    throwaway model rather than on ``ImageSnapshot`` because the invariant
    belongs to the base class's spec consumption, not to any one model —
    ``ImageSnapshot.version`` is typed ``str | None`` in both ports and so
    cannot carry a ``Raw`` through the type check that runs first.
    """

    class _Patterned(GhagenModel):
        SPEC: ClassVar[ModelSpec] = ModelSpec(
            yaml_keys={"version": "version"},
            order=("version",),
            patterns={"version": re.compile(r"^\d+$", re.ASCII)},
        )

        version: str | Raw[str] | None = None

    def test_pattern_rejects_a_non_matching_string(self):
        with pytest.raises(ValidationError, match="version"):
            self._Patterned(version="v1")

    def test_pattern_accepts_a_matching_string(self):
        assert self._Patterned(version="12").version == "12"

    def test_pattern_skips_a_raw_value(self):
        assert self._Patterned(version=Raw("nightly")).version == Raw("nightly")

    def test_pattern_skips_an_absent_value(self):
        assert self._Patterned().version is None
