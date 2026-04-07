"""Shared fixtures for integration tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from ruamel.yaml import YAML

SCHEMA_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "ghagen"
    / "schema"
    / "snapshot"
    / "workflow_schema.json"
)


@pytest.fixture(scope="session")
def workflow_schema() -> dict[str, Any]:
    """Load the GitHub Actions workflow JSON Schema from the local snapshot."""
    return json.loads(SCHEMA_PATH.read_text())


def validate_and_roundtrip(yaml_str: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Parse YAML, validate against schema, and return as a plain dict.

    Args:
        yaml_str: The YAML string to validate.
        schema: The JSON Schema to validate against.

    Returns:
        The parsed YAML as a plain dict (CommentedMap stripped).
    """
    yaml = YAML()
    data = yaml.load(yaml_str)
    # Convert CommentedMap/CommentedSeq to plain dict/list for jsonschema
    plain: dict[str, Any] = json.loads(json.dumps(data, default=str))
    jsonschema.validate(plain, schema)
    return plain
