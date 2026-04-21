"""Tests for the expression builder."""

from __future__ import annotations

import pytest

from ghagen.helpers.expressions import expr
from ghagen.models.step import Step

# --- attribute access ---


def test_simple_attribute():
    assert str(expr.github) == "${{ github }}"


def test_nested_attribute():
    assert str(expr.github.ref) == "${{ github.ref }}"


def test_deep_attribute():
    assert str(expr.github.event.pull_request.merged) == (
        "${{ github.event.pull_request.merged }}"
    )


def test_runner_os():
    assert str(expr.runner.os) == "${{ runner.os }}"


# --- subscript access ---


def test_subscript_secrets():
    assert str(expr.secrets["PYPI_TOKEN"]) == "${{ secrets.PYPI_TOKEN }}"


def test_subscript_env():
    assert str(expr.env["CI"]) == "${{ env.CI }}"


def test_subscript_then_attr():
    assert str(expr.steps["build"].outputs.dist) == ("${{ steps.build.outputs.dist }}")


# --- functions ---


def test_contains():
    result = str(expr.contains(expr.github.ref, "refs/tags/"))
    assert result == "${{ contains(github.ref, 'refs/tags/') }}"


def test_starts_with():
    result = str(expr.startsWith(expr.github.ref, "refs/heads/"))
    assert result == "${{ startsWith(github.ref, 'refs/heads/') }}"


def test_format_func():
    result = str(expr.format("v{0}", expr.github.run_number))
    assert result == "${{ format('v{0}', github.run_number) }}"


def test_to_json():
    assert str(expr.toJSON(expr.matrix)) == "${{ toJSON(matrix) }}"


def test_from_json():
    result = str(expr.fromJSON(expr.needs["setup"].outputs.config))
    assert result == "${{ fromJSON(needs.setup.outputs.config) }}"


def test_hash_files():
    result = str(expr.hashFiles("**/requirements*.txt"))
    assert result == "${{ hashFiles('**/requirements*.txt') }}"


def test_always():
    assert str(expr.always()) == "${{ always() }}"


def test_failure():
    assert str(expr.failure()) == "${{ failure() }}"


def test_cancelled():
    assert str(expr.cancelled()) == "${{ cancelled() }}"


def test_success():
    assert str(expr.success()) == "${{ success() }}"


# --- nested function calls ---


def test_nested_functions():
    result = str(expr.contains(expr.toJSON(expr.github.event.labels), "deploy"))
    assert result == "${{ contains(toJSON(github.event.labels), 'deploy') }}"


# --- argument formatting ---


def test_numeric_arg():
    result = str(expr.format("v{0}", 42))
    assert result == "${{ format('v{0}', 42) }}"


def test_boolean_arg_true():
    result = str(expr.contains(expr.github.event.labels, True))
    assert result == "${{ contains(github.event.labels, true) }}"


def test_boolean_arg_false():
    result = str(expr.contains(expr.github.event.labels, False))
    assert result == "${{ contains(github.event.labels, false) }}"


# --- comparison operators ---


def test_eq():
    assert str(expr.github.ref == "refs/heads/main") == (
        "${{ github.ref == 'refs/heads/main' }}"
    )


def test_ne():
    assert str(expr.github.event_name != "pull_request") == (
        "${{ github.event_name != 'pull_request' }}"
    )


def test_gt():
    assert str(expr.github.run_number > 10) == "${{ github.run_number > 10 }}"


def test_ge():
    assert str(expr.github.run_number >= 10) == "${{ github.run_number >= 10 }}"


def test_lt():
    assert str(expr.github.run_number < 100) == "${{ github.run_number < 100 }}"


def test_le():
    assert str(expr.github.run_number <= 100) == "${{ github.run_number <= 100 }}"


def test_eq_builder_to_builder():
    result = str(expr.github.ref == expr.github.base_ref)
    assert result == "${{ github.ref == github.base_ref }}"


# --- boolean operators ---


def test_and():
    result = str((expr.github.ref == "main") & (expr.github.event_name == "push"))
    assert result == "${{ github.ref == 'main' && github.event_name == 'push' }}"


def test_or():
    result = str(
        (expr.github.event_name == "push") | (expr.github.event_name == "schedule")
    )
    assert result == (
        "${{ github.event_name == 'push' || github.event_name == 'schedule' }}"
    )


def test_invert():
    assert str(~expr.github.event.pull_request.draft) == (
        "${{ !github.event.pull_request.draft }}"
    )


# --- compound expressions ---


def test_compound_and_or():
    result = str(
        ((expr.github.ref == "main") & (expr.github.event_name == "push"))
        | (expr.github.event_name == "schedule")
    )
    assert result == (
        "${{ github.ref == 'main' && github.event_name == 'push'"
        " || github.event_name == 'schedule' }}"
    )


# --- f-string embedding ---


def test_fstring_embedding():
    result = f"prefix-{expr.runner.os}-suffix"
    assert result == "prefix-${{ runner.os }}-suffix"


def test_fstring_multiple():
    result = f"pip-{expr.runner.os}-{expr.hashFiles('**/requirements*.txt')}"
    assert result == ("pip-${{ runner.os }}-${{ hashFiles('**/requirements*.txt') }}")


# --- builder immutability ---


def test_immutability():
    a = expr.github
    b = a.ref
    assert str(a) == "${{ github }}"
    assert str(b) == "${{ github.ref }}"


# --- safety guards ---


def test_bool_raises():
    with pytest.raises(TypeError, match="boolean context"):
        bool(expr.github.ref)


def test_bool_raises_on_comparison_result():
    with pytest.raises(TypeError, match="boolean context"):
        bool(expr.github.ref == "main")


def test_if_guard():
    with pytest.raises(TypeError, match="boolean context"):
        if expr.github.ref == "main":  # type: ignore[truthy-bool]
            pass


def test_unhashable():
    with pytest.raises(TypeError):
        {expr.github.ref}  # noqa: B018


# --- repr ---


def test_repr():
    assert "github.ref" in repr(expr.github.ref)


# --- private attr ---


def test_private_attr_raises():
    with pytest.raises(AttributeError):
        expr._private  # noqa: B018


# --- integration with Step ---


def test_expr_in_step_if():
    step = Step(name="Test", run="echo hi", if_=str(expr.github.ref == "main"))
    cm = step.to_commented_map()
    assert cm["if"] == "${{ github.ref == 'main' }}"
