"""Generate reference Pydantic v2 models from the workflow JSON Schema."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ghagen.schema.fetch import SNAPSHOT_DIR


def generate_models(schema_path: Path, output_path: Path) -> None:
    """Run ``datamodel-codegen`` to produce Pydantic v2 models from *schema_path*."""
    subprocess.run(
        [
            "datamodel-codegen",
            "--input",
            str(schema_path),
            "--input-file-type",
            "jsonschema",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


if __name__ == "__main__":
    schema = SNAPSHOT_DIR / "workflow_schema.json"
    out = SNAPSHOT_DIR / "_generated_models.py"
    generate_models(schema, out)
    print(f"Generated models at {out}")
