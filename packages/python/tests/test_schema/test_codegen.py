"""Tests for the schema code generator."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ghagen.schema.codegen import generate_models

MINIMAL_SCHEMA = {
    "type": "object",
    "title": "TestModel",
    "properties": {
        "name": {"type": "string"},
        "count": {"type": "integer"},
    },
}


def test_generate_models_creates_output(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(MINIMAL_SCHEMA))
    output_path = tmp_path / "models.py"

    generate_models(schema_path, output_path)

    assert output_path.exists()
    content = output_path.read_text()
    assert "BaseModel" in content


def test_generate_models_contains_fields(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(MINIMAL_SCHEMA))
    output_path = tmp_path / "models.py"

    generate_models(schema_path, output_path)

    content = output_path.read_text()
    assert "name" in content
    assert "count" in content


def test_generate_models_raises_on_invalid_input(tmp_path: Path) -> None:
    schema_path = tmp_path / "bad.json"
    schema_path.write_text("not valid json {{{")
    output_path = tmp_path / "models.py"

    with pytest.raises(subprocess.CalledProcessError):
        generate_models(schema_path, output_path)
