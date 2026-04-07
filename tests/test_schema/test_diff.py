"""Tests for schema drift detection."""

from __future__ import annotations

import json
from pathlib import Path

from ghagen.schema.diff import check_drift

SAMPLE_SCHEMA = {"type": "object", "properties": {"name": {"type": "string"}}}
MODIFIED_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "new_field": {"type": "integer"}},
}

SAMPLE_MODELS = "# generated models\nclass Model:\n    pass\n"
MODIFIED_MODELS = "# generated models\nclass Model:\n    name: str\n"


def _setup_snapshot(
    snapshot_dir: Path, schema: dict, models: str = SAMPLE_MODELS
) -> None:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "workflow_schema.json").write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n"
    )
    (snapshot_dir / "_generated_models.py").write_text(models)


def test_no_drift(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "snapshot"
    _setup_snapshot(snapshot_dir, SAMPLE_SCHEMA)

    def mock_save(dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(SAMPLE_SCHEMA, indent=2, sort_keys=True) + "\n")

    monkeypatch.setattr("ghagen.schema.diff.save_schema", mock_save)  # type: ignore[attr-defined]

    def mock_codegen(schema_path: Path, output_path: Path) -> None:
        output_path.write_text(SAMPLE_MODELS)

    monkeypatch.setattr("ghagen.schema.diff.generate_models", mock_codegen)  # type: ignore[attr-defined]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert not has_drift
    assert diff_output == ""


def test_schema_drift_detected(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "snapshot"
    _setup_snapshot(snapshot_dir, SAMPLE_SCHEMA)

    def mock_save(dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(MODIFIED_SCHEMA, indent=2, sort_keys=True) + "\n"
        )

    monkeypatch.setattr("ghagen.schema.diff.save_schema", mock_save)  # type: ignore[attr-defined]

    def mock_codegen(schema_path: Path, output_path: Path) -> None:
        output_path.write_text(SAMPLE_MODELS)

    monkeypatch.setattr("ghagen.schema.diff.generate_models", mock_codegen)  # type: ignore[attr-defined]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert has_drift
    assert "new_field" in diff_output


def test_models_drift_detected(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "snapshot"
    _setup_snapshot(snapshot_dir, SAMPLE_SCHEMA)

    def mock_save(dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(SAMPLE_SCHEMA, indent=2, sort_keys=True) + "\n")

    monkeypatch.setattr("ghagen.schema.diff.save_schema", mock_save)  # type: ignore[attr-defined]

    def mock_codegen(schema_path: Path, output_path: Path) -> None:
        output_path.write_text(MODIFIED_MODELS)

    monkeypatch.setattr("ghagen.schema.diff.generate_models", mock_codegen)  # type: ignore[attr-defined]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert has_drift
    assert "name: str" in diff_output


def test_missing_snapshot_file(tmp_path: Path, monkeypatch: object) -> None:
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()

    def mock_save(dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(SAMPLE_SCHEMA, indent=2, sort_keys=True) + "\n")

    monkeypatch.setattr("ghagen.schema.diff.save_schema", mock_save)  # type: ignore[attr-defined]

    def mock_codegen(schema_path: Path, output_path: Path) -> None:
        output_path.write_text(SAMPLE_MODELS)

    monkeypatch.setattr("ghagen.schema.diff.generate_models", mock_codegen)  # type: ignore[attr-defined]

    has_drift, diff_output = check_drift(snapshot_dir)
    assert has_drift
    assert "Missing snapshot" in diff_output
