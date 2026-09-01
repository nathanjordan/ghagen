"""Snapshot tests: compare generated YAML against stored expected output.

The models are not written here -- they live in
:mod:`tests.test_integration.fixture_models`, the one binding from a fixture
file to the model that produces it, so the walk sweep in
:mod:`tests.test_integration.test_to_data_sweep` runs over exactly the documents
this oracle covers rather than over a second hand-built list.

Peer: ``packages/typescript/src/integration/snapshots.test.ts``.
"""

from __future__ import annotations

import pytest
from pytest_snapshot.plugin import Snapshot

from ghagen_schema.paths import EXPECTED_DIR
from tests.test_integration.fixture_models import (
    HEADER_GOLDENS,
    SNAPSHOT_DOCS,
    FixtureDoc,
)

SNAPSHOT_DIR = EXPECTED_DIR


@pytest.mark.parametrize("doc", SNAPSHOT_DOCS, ids=lambda d: d.fixture)
def test_snapshot(doc: FixtureDoc, snapshot: Snapshot) -> None:
    """Each bound document emits exactly its fixture file."""
    snapshot.snapshot_dir = SNAPSHOT_DIR
    snapshot.assert_match(doc.render(), doc.fixture)


# --- Header goldens --------------------------------------------------------
#
# The cross-port byte oracle for ``format_header``. These six are read by hand
# rather than through pytest-snapshot because they are an *oracle* -- the
# artefact that proves the two ports' headers agree byte-for-byte -- not a
# regenerable snapshot of current behaviour. Peer:
# ``packages/typescript/src/integration/snapshots.test.ts``.


def _golden(name: str) -> str:
    return (SNAPSHOT_DIR / name).read_text()


@pytest.mark.parametrize("doc", HEADER_GOLDENS, ids=lambda d: d.fixture)
def test_header_golden(doc: FixtureDoc) -> None:
    """Each header shape emits exactly its hand-read golden."""
    out = doc.render()
    assert out == _golden(doc.fixture)
    if doc.fixture == "header_crlf.yml":
        # CRLF and a bare CR are both line breaks: no CR may survive.
        assert "\r" not in out
