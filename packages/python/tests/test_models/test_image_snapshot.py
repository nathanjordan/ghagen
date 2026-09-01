"""Tests for the ImageSnapshot model and Job.snapshot (both syntaxes)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ghagen import Commented, ImageSnapshot, Job, with_comment, with_eol_comment
from ghagen.emitter import to_data


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
    "version", ["1.*", "1.2.3", "v1", "1.", "latest", "*", "1.2.*", "", " 1", "1.2*"]
)
def test_version_pattern_rejects_invalid(version: str):
    """Non-matching versions (patch versions, prefixes, etc.) are rejected."""
    with pytest.raises(ValidationError):
        ImageSnapshot(image_name="img", version=version)


@pytest.mark.parametrize("version", ["1\n", "1.2\n", "1*\n"])
def test_version_pattern_rejects_trailing_newline(version: str):
    """A trailing newline is not in the schema language.

    ``re.match`` anchors only the start, and Python's ``$`` matches *before* a
    trailing newline, so the old hand-written validator accepted
    ``version="1\\n"`` and emitted it. ``fullmatch`` is what closes it.
    """
    with pytest.raises(ValidationError):
        ImageSnapshot(image_name="img", version=version)


@pytest.mark.parametrize("version", ["١", "١.٢"])
def test_version_pattern_rejects_unicode_digits(version: str):
    """``\\d`` is Unicode in Python's ``re`` and ASCII-only in ECMA-262.

    JSON Schema's regex dialect is ECMA-262, so the Snapshot rejects
    ARABIC-INDIC DIGIT ONE while an unflagged Python pattern accepts it.
    ``re.ASCII`` matches the schema dialect and leaves ``.pattern``
    byte-identical.
    """
    with pytest.raises(ValidationError):
        ImageSnapshot(image_name="img", version=version)


@pytest.mark.parametrize("version", ["NOT-A-VERSION", "1.2.3", "v1", "1\n", "١"])
def test_version_pattern_survives_a_comment_wrapper(version: str):
    """``with_comment`` must not defeat the value grammar.

    ``_preserve_commented`` is a ``mode="wrap"`` validator that re-attaches the
    ``Commented`` wrapper *after* ``handler(clean)`` returns, so a
    ``mode="after"`` grammar check sees the wrapper, not the string. The
    TypeScript peer peels the wrapper before testing the pattern
    (``buildYamlData``); this pins the same behaviour here.
    """
    with pytest.raises(ValidationError):
        ImageSnapshot(image_name="img", version=with_comment(version, "note"))
    with pytest.raises(ValidationError):
        ImageSnapshot(image_name="img", version=with_eol_comment(version, "note"))


def test_comment_wrapper_survives_a_grammar_valid_value():
    """Peeling for the grammar check must not drop the wrapper itself."""
    snap = ImageSnapshot(image_name="img", version=with_comment("1.2", "note"))
    # `with_comment` is annotated `T -> T` so that a wrapped value stays
    # assignable to the field it decorates; the object it actually returns is a
    # `Commented[T]` (see `ghagen._commented`). The declared type of
    # `version` therefore never mentions the wrapper, and a test that reaches
    # *into* it has to undo the annotation's convenient fiction. The isinstance
    # is the assertion this test's name makes -- that the wrapper survived --
    # so stating it is a gain, not a tax (docs/issues/09).
    assert isinstance(snap.version, Commented)
    assert snap.version.value == "1.2"
    assert snap.version.comment == "note"


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
    assert to_data(job)["snapshot"] == {"image-name": "custom-ubuntu", "version": "1.0"}


def test_emits_string_syntax():
    """A job with a plain-string snapshot emits the string syntax."""
    job = Job(runs_on="ubuntu-latest", snapshot="custom-ubuntu")
    assert to_data(job)["snapshot"] == "custom-ubuntu"


def test_snapshot_emits_after_container():
    """snapshot is ordered immediately after container in job emission."""
    job = Job(
        runs_on="ubuntu-latest",
        container="python:3.13",
        snapshot="custom-ubuntu",
    )
    keys = list(to_data(job))
    assert keys.index("snapshot") == keys.index("container") + 1
