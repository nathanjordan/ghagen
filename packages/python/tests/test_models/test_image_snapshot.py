"""Tests for the ImageSnapshot model and Job.snapshot (both syntaxes)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ghagen import ImageSnapshot, Job
from ghagen.emitter.nodes import _model_to_map
from ghagen.emitter.yaml_writer import dump_yaml


def test_mapping_syntax_fields():
    """Mapping syntax carries image name and optional version."""
    snap = ImageSnapshot(image_name="custom-ubuntu", version="1.2")
    assert snap.image_name == "custom-ubuntu"
    assert snap.version == "1.2"


def test_image_name_required():
    """image_name is required."""
    with pytest.raises(ValidationError):
        ImageSnapshot()  # type: ignore[call-arg]


def test_version_optional():
    """version defaults to None (image-name only)."""
    snap = ImageSnapshot(image_name="custom-ubuntu")
    assert snap.version is None


@pytest.mark.parametrize("version", ["1", "10", "1.2", "1*", "12.34"])
def test_version_pattern_accepts_valid(version: str):
    """Valid versions (major, major.minor, or major* wildcard) are accepted."""
    assert ImageSnapshot(image_name="img", version=version).version == version


@pytest.mark.parametrize(
    "version", ["1.*", "1.2.3", "v1", "1.", "latest", "*", "1.2.*"]
)
def test_version_pattern_rejects_invalid(version: str):
    """Non-matching versions (patch versions, prefixes, etc.) are rejected."""
    with pytest.raises(ValidationError):
        ImageSnapshot(image_name="img", version=version)


def test_string_syntax_on_job():
    """Job.snapshot accepts the string syntax (image name only)."""
    job = Job(runs_on="ubuntu-latest", snapshot="custom-ubuntu")
    assert job.snapshot == "custom-ubuntu"


def test_mapping_syntax_on_job():
    """Job.snapshot accepts an ImageSnapshot (mapping syntax)."""
    job = Job(runs_on="ubuntu-latest", snapshot=ImageSnapshot(image_name="img"))
    assert isinstance(job.snapshot, ImageSnapshot)


def test_emits_mapping_syntax():
    """A job with an ImageSnapshot emits the image-name/version mapping."""
    job = Job(
        runs_on="ubuntu-latest",
        snapshot=ImageSnapshot(image_name="custom-ubuntu", version="1.0"),
    )
    result = dump_yaml(_model_to_map(job))
    assert "snapshot:" in result
    assert "image-name: custom-ubuntu" in result
    assert "version: '1.0'" in result


def test_emits_string_syntax():
    """A job with a plain-string snapshot emits the string syntax."""
    job = Job(runs_on="ubuntu-latest", snapshot="custom-ubuntu")
    result = dump_yaml(_model_to_map(job))
    assert "snapshot: custom-ubuntu" in result


def test_snapshot_emits_after_container():
    """snapshot is ordered immediately after container in job emission."""
    job = Job(
        runs_on="ubuntu-latest",
        container="python:3.13",
        snapshot="custom-ubuntu",
    )
    keys = list(_model_to_map(job).keys())
    assert keys.index("snapshot") == keys.index("container") + 1
