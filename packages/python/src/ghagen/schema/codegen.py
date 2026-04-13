"""Generate reference Pydantic v2 models from JSON Schemas.

The generated files under ``src/ghagen/schema/snapshot/`` are for
parity checking only — they are not the models that ghagen users
interact with. Their purpose is to make schema drift visible as a
diff in the snapshot directory.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ghagen.schema.fetch import SCHEMAS, SNAPSHOT_DIR


def _generated_filename(name: str) -> str:
    """Return the generated models filename for a given schema name.

    The workflow models file keeps its historical name
    (``_generated_models.py``) while additional schemas get a
    name-qualified suffix (``_generated_action_models.py``).
    """
    if name == "workflow":
        return "_generated_models.py"
    return f"_generated_{name}_models.py"


def generate_models(schema_path: Path, output_path: Path) -> None:
    """Run ``datamodel-codegen`` to produce Pydantic v2 models.

    Args:
        schema_path: Path to the input JSON Schema.
        output_path: Path to write the generated Python module to.
    """
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


def generate_all_models(snapshot_dir: Path | None = None) -> list[Path]:
    """Codegen models for every known schema under *snapshot_dir*.

    Returns the list of generated file paths in registry order.
    """
    target = snapshot_dir if snapshot_dir is not None else SNAPSHOT_DIR
    written: list[Path] = []
    for name, info in SCHEMAS.items():
        schema_path = target / info["filename"]
        output_path = target / _generated_filename(name)
        generate_models(schema_path, output_path)
        written.append(output_path)
    return written


if __name__ == "__main__":
    for out in generate_all_models():
        print(f"Generated models at {out}")
