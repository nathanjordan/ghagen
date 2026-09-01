"""The Python half of the docs' emitted-output oracle.

Every YAML block the guides show is produced by running the emitter at
docs-build time -- see ``docs/src/snippets/emitted.ts`` and ``docs/issues/18``.
That build has Node and no Python, so it can only run the TypeScript port; it
pins each result to ``fixtures/expected/docs_*.yml``.

This module is the other half of that pin. It builds the mirrored Python model
for each documented example and byte-compares against the same file, so a
cross-port divergence in anything the guides show fails one side or the other
instead of shipping. The snippets in the guides' Python tabs are the models in
:mod:`tests.test_integration.fixture_models` -- keep the two in step.
"""

from __future__ import annotations

import pytest
from pytest_snapshot.plugin import Snapshot

from ghagen_schema.paths import EXPECTED_DIR
from tests.test_integration.fixture_models import DOCS_SNIPPET_DOCS, FixtureDoc

SNAPSHOT_DIR = EXPECTED_DIR


@pytest.mark.parametrize("doc", DOCS_SNIPPET_DOCS, ids=lambda d: d.fixture)
def test_docs_snippet(doc: FixtureDoc, snapshot: Snapshot) -> None:
    """Each documented example emits exactly what the docs build pinned."""
    snapshot.snapshot_dir = SNAPSHOT_DIR
    snapshot.assert_match(doc.render(), doc.fixture)
