"""Coarse schema-conformance check for the hand-written Python models.

This is the test-based replacement for the deleted diff-only generated models
(see ADR-0003). It loads the canonical GitHub Actions workflow schema and walks
its top-level, job, and step properties, asserting that ghagen's hand-written
Pydantic models expose each one -- either as a field name or via a serialization
alias (e.g. ``if_`` -> ``if``, ``run_name`` -> ``run-name``).

Properties ghagen intentionally does not model are listed in explicit,
per-scope allow-lists below. Anything else that appears upstream but is missing
from the models fails the test, surfacing schema drift as a conformance gap.

It needs no code generation -- it reflects over ``model_fields`` directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.workflow import Workflow

REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOW_SCHEMA_PATH = REPO_ROOT / "schema" / "workflow_schema.json"

# ---------------------------------------------------------------------------
# Intentionally-unsupported schema properties, per scope. Each entry is a
# deliberate gap in ghagen's ergonomic model surface, not an oversight.
# ---------------------------------------------------------------------------

# Top-level workflow properties ghagen does not model.
WORKFLOW_ALLOWLIST: set[str] = set()

# Job properties ghagen does not model.
JOB_ALLOWLIST: set[str] = {
    # `snapshot` is a newer, rarely-used runner-snapshot field with no ergonomic
    # model equivalent yet; emitted verbatim via CommentedMap if a user needs it.
    "snapshot",
}

# Step properties ghagen does not model.
STEP_ALLOWLIST: set[str] = set()


def _load_schema() -> dict[str, Any]:
    return json.loads(WORKFLOW_SCHEMA_PATH.read_text())


def _model_property_names(model: type[BaseModel]) -> set[str]:
    """Serialization names a model exposes (alias when set, else field name)."""
    names: set[str] = set()
    for field_name, info in model.model_fields.items():
        names.add(info.serialization_alias or info.alias or field_name)
    return names


def _schema_properties(definition: dict[str, Any]) -> set[str]:
    return set(definition.get("properties", {}).keys())


def _assert_covered(
    schema_props: set[str],
    model: type[BaseModel],
    allow: set[str],
    scope: str,
) -> None:
    covered = _model_property_names(model)
    missing = schema_props - covered - allow
    assert not missing, (
        f"{scope} model {model.__name__} is missing schema properties "
        f"{sorted(missing)}. Add fields, or add them to the allow-list if "
        f"intentionally unsupported."
    )
    # Keep the allow-list honest: every allowed name must still exist upstream
    # so stale entries get flagged.
    stale = allow - schema_props
    assert not stale, (
        f"{scope} allow-list has stale entries no longer in the schema: "
        f"{sorted(stale)}. Remove them."
    )


def test_workflow_top_level_properties_covered() -> None:
    schema = _load_schema()
    props = _schema_properties(schema)
    assert props, "workflow schema exposes no top-level properties"
    _assert_covered(props, Workflow, WORKFLOW_ALLOWLIST, "workflow")


def test_job_properties_covered() -> None:
    schema = _load_schema()
    defs = schema.get("definitions", {})
    # Union of the regular-job and reusable-workflow-call-job property sets:
    # ghagen's single Job model covers both shapes.
    props: set[str] = set()
    for def_name in ("normalJob", "reusableWorkflowCallJob"):
        props |= _schema_properties(defs.get(def_name, {}))
    assert props, "workflow schema exposes no job properties"
    _assert_covered(props, Job, JOB_ALLOWLIST, "job")


def test_step_properties_covered() -> None:
    schema = _load_schema()
    defs = schema.get("definitions", {})
    props = _schema_properties(defs.get("step", {}))
    assert props, "workflow schema exposes no step properties"
    _assert_covered(props, Step, STEP_ALLOWLIST, "step")
