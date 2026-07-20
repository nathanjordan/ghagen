"""Tests for schema drift detection (JSON-only, no model generation).

Drift is a pure comparison between the committed canonical snapshot and the
freshly fetched upstream schemas -- see ADR-0003.
"""

from __future__ import annotations

import json
from pathlib import Path

import schema_sync
from schema_sync import check_drift

SAMPLE_WORKFLOW_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
}
SAMPLE_ACTION_SCHEMA = {
    "type": "object",
    "properties": {"description": {"type": "string"}},
}
MODIFIED_WORKFLOW_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "new_field": {"type": "integer"},
    },
}
MODIFIED_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "deprecated_field": {"type": "boolean"},
    },
}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _setup_snapshot(
    snapshot_dir: Path,
    workflow_schema: dict = SAMPLE_WORKFLOW_SCHEMA,
    action_schema: dict = SAMPLE_ACTION_SCHEMA,
) -> None:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    _write_json(snapshot_dir / "workflow_schema.json", workflow_schema)
    _write_json(snapshot_dir / "action_schema.json", action_schema)


def _install_upstream(
    monkeypatch,  # type: ignore[no-untyped-def]
    workflow_schema: dict = SAMPLE_WORKFLOW_SCHEMA,
    action_schema: dict = SAMPLE_ACTION_SCHEMA,
) -> None:
    """Stub the upstream fetch so ``check_drift`` sees the given schemas."""

    def mock_save_all(schema_dir: Path | None = None) -> list[Path]:
        assert schema_dir is not None
        _write_json(schema_dir / "workflow_schema.json", workflow_schema)
        _write_json(schema_dir / "action_schema.json", action_schema)
        return [
            schema_dir / "workflow_schema.json",
            schema_dir / "action_schema.json",
        ]

    monkeypatch.setattr(schema_sync, "save_all_schemas", mock_save_all)


def test_no_drift(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "schema"
    _setup_snapshot(snapshot_dir)
    _install_upstream(monkeypatch)  # type: ignore[arg-type]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert not has_drift
    assert diff_output == ""


def test_workflow_schema_drift_detected(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "schema"
    _setup_snapshot(snapshot_dir)
    _install_upstream(monkeypatch, workflow_schema=MODIFIED_WORKFLOW_SCHEMA)  # type: ignore[arg-type]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert has_drift
    assert "new_field" in diff_output


def test_action_schema_drift_detected(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "schema"
    _setup_snapshot(snapshot_dir)
    _install_upstream(monkeypatch, action_schema=MODIFIED_ACTION_SCHEMA)  # type: ignore[arg-type]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert has_drift
    assert "deprecated_field" in diff_output


def test_missing_workflow_snapshot_file(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "schema"
    snapshot_dir.mkdir()
    _install_upstream(monkeypatch)  # type: ignore[arg-type]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert has_drift
    assert "Missing snapshot" in diff_output
