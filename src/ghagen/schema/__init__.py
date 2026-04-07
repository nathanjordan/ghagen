"""Schema pipeline for tracking GitHub Actions schema changes."""

from ghagen.schema.codegen import generate_models
from ghagen.schema.diff import check_drift
from ghagen.schema.fetch import fetch_schema, save_schema

__all__ = ["check_drift", "fetch_schema", "generate_models", "save_schema"]
