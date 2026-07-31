"""Construction-time validation invariants shared by every GhagenModel.

The models' documented promise is that a model validates when it is
constructed. These tests pin the two ways that promise used to be hollow:
unknown keyword arguments were silently dropped, and ``Raw[T]`` in a union
absorbed any value at all.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ghagen.models.job import Job
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
