"""Tests for GhagenModel._source_location capture via frame walking.

The source location is captured in model_post_init by walking up the call
stack until a non-internal frame is found. Internal frames are those in
pydantic, ghagen.models, ghagen.helpers, or ghagen.emitter.
"""

from __future__ import annotations

import sys

from ghagen import Job, Step, Workflow, setup_python


def test_step_direct_construction_captures_caller_line() -> None:
    """A Step constructed on a single line records this file and that line."""
    step = Step(run="echo hello")
    expected_line = sys._getframe().f_lineno - 1  # construction line above

    assert step._source_location is not None
    file, line = step._source_location
    assert file.endswith("test_source_location.py")
    assert line == expected_line


def test_step_via_helper_attributes_to_caller_not_helper() -> None:
    """A Step built by a helper (setup_python) reports the user's call site,
    not the helper's internal line in ghagen/helpers/steps.py."""
    step = setup_python("3.12")
    expected_line = sys._getframe().f_lineno - 1

    assert step._source_location is not None
    file, line = step._source_location
    assert file.endswith("test_source_location.py")
    assert line == expected_line
    # Must not point at the helper file
    assert "helpers/steps.py" not in file


def test_nested_model_construction_captures_user_file() -> None:
    """Each nested model captures a location in user code (this test file).

    Exact line-number assertions are avoided for multi-line constructions
    because Python's f_lineno semantics for a multi-line call can vary
    slightly by Python version.
    """
    inner_step = Step(run="echo inner")
    job = Job(
        runs_on="ubuntu-latest",
        steps=[inner_step],
    )
    wf = Workflow(
        name="test",
        jobs={"build": job},
    )

    for model in (inner_step, job, wf):
        assert model._source_location is not None
        file, _ = model._source_location
        assert file.endswith("test_source_location.py"), (
            f"expected this test file, got {file}"
        )


def test_internal_frames_do_not_leak_into_location() -> None:
    """Frame walking must skip all pydantic internals and ghagen internals."""
    step = Step(uses="actions/checkout@v4")

    assert step._source_location is not None
    file, _ = step._source_location
    assert "pydantic" not in file
    assert "/ghagen/models/" not in file
    assert "/ghagen/helpers/" not in file
    assert "/ghagen/emitter/" not in file


def test_helper_chain_still_resolves_to_user_code() -> None:
    """Through multiple helper layers the location still lands on user code."""
    step = setup_python("3.11", cache="pip")

    assert step._source_location is not None
    file, _ = step._source_location
    assert file.endswith("test_source_location.py")
