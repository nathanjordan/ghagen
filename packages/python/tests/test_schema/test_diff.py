"""Tests for schema drift detection across workflow + action schemas."""

from __future__ import annotations

import json
from pathlib import Path

from ghagen.schema.diff import check_drift

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

SAMPLE_WORKFLOW_MODELS = "# generated workflow models\nclass Model:\n    pass\n"
SAMPLE_ACTION_MODELS = "# generated action models\nclass Model:\n    pass\n"
MODIFIED_WORKFLOW_MODELS = "# generated workflow models\nclass Model:\n    name: str\n"
MODIFIED_ACTION_MODELS = (
    "# generated action models\nclass Model:\n    description: str\n"
)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _setup_snapshot(
    snapshot_dir: Path,
    workflow_schema: dict = SAMPLE_WORKFLOW_SCHEMA,
    action_schema: dict = SAMPLE_ACTION_SCHEMA,
    workflow_models: str = SAMPLE_WORKFLOW_MODELS,
    action_models: str = SAMPLE_ACTION_MODELS,
) -> None:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    _write_json(snapshot_dir / "workflow_schema.json", workflow_schema)
    _write_json(snapshot_dir / "action_schema.json", action_schema)
    (snapshot_dir / "_generated_models.py").write_text(workflow_models)
    (snapshot_dir / "_generated_action_models.py").write_text(action_models)


def _install_mocks(
    monkeypatch,  # type: ignore[no-untyped-def]
    workflow_schema: dict = SAMPLE_WORKFLOW_SCHEMA,
    action_schema: dict = SAMPLE_ACTION_SCHEMA,
    workflow_models: str = SAMPLE_WORKFLOW_MODELS,
    action_models: str = SAMPLE_ACTION_MODELS,
) -> None:
    def mock_save_all(snapshot_dir: Path | None = None) -> list[Path]:
        assert snapshot_dir is not None
        _write_json(snapshot_dir / "workflow_schema.json", workflow_schema)
        _write_json(snapshot_dir / "action_schema.json", action_schema)
        return [
            snapshot_dir / "workflow_schema.json",
            snapshot_dir / "action_schema.json",
        ]

    def mock_generate_all(snapshot_dir: Path | None = None) -> list[Path]:
        assert snapshot_dir is not None
        (snapshot_dir / "_generated_models.py").write_text(workflow_models)
        (snapshot_dir / "_generated_action_models.py").write_text(action_models)
        return [
            snapshot_dir / "_generated_models.py",
            snapshot_dir / "_generated_action_models.py",
        ]

    monkeypatch.setattr("ghagen.schema.diff.save_all_schemas", mock_save_all)
    monkeypatch.setattr("ghagen.schema.diff.generate_all_models", mock_generate_all)


def test_no_drift(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "snapshot"
    _setup_snapshot(snapshot_dir)
    _install_mocks(monkeypatch)  # type: ignore[arg-type]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert not has_drift
    assert diff_output == ""


def test_workflow_schema_drift_detected(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "snapshot"
    _setup_snapshot(snapshot_dir)
    _install_mocks(monkeypatch, workflow_schema=MODIFIED_WORKFLOW_SCHEMA)  # type: ignore[arg-type]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert has_drift
    assert "new_field" in diff_output


def test_action_schema_drift_detected(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "snapshot"
    _setup_snapshot(snapshot_dir)
    _install_mocks(monkeypatch, action_schema=MODIFIED_ACTION_SCHEMA)  # type: ignore[arg-type]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert has_drift
    assert "deprecated_field" in diff_output


def test_workflow_models_drift_detected(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "snapshot"
    _setup_snapshot(snapshot_dir)
    _install_mocks(monkeypatch, workflow_models=MODIFIED_WORKFLOW_MODELS)  # type: ignore[arg-type]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert has_drift
    assert "name: str" in diff_output


def test_action_models_drift_detected(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "snapshot"
    _setup_snapshot(snapshot_dir)
    _install_mocks(monkeypatch, action_models=MODIFIED_ACTION_MODELS)  # type: ignore[arg-type]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert has_drift
    assert "description: str" in diff_output


def test_missing_workflow_snapshot_file(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()
    _install_mocks(monkeypatch)  # type: ignore[arg-type]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert has_drift
    assert "Missing snapshot" in diff_output
