"""The walk oracle: ``parse(to_yaml(doc))`` must equal ``to_data(doc)`` for
every fixture document.

``to_data`` and ``to_yaml`` are two renderings of one collection stage
(``emitter.nodes.emit_entries``). This sweep is what makes that claim testable
on real documents: it runs over the same
:mod:`tests.test_integration.fixture_models` list the byte oracle in
:mod:`tests.test_integration.test_snapshots` runs over, so any decision the
shared stage owns -- membership, YAML keys, order, the extras merge, the Step
``run`` dedent, present-null -- that the two renderings resolve differently
fails here.

The cross-check it replaces was a single hand-built document: an existence
proof over the shapes its author happened to remember (docs/issues/01). That
document is kept, in ``tests/test_emitter/test_to_data.py``, because it
deliberately packs shapes no fixture contains.

Comments are dropped by a YAML parse, so the comparison runs with comments off
-- the default. ``auto_dedent`` is left at its default too, which is
``to_yaml``'s.

Peer: ``packages/typescript/src/integration/to-data-sweep.test.ts``.
"""

from __future__ import annotations

from typing import Any

import pytest
from ruamel.yaml import YAML

from ghagen.emitter import to_data
from ghagen_schema.paths import EXPECTED_DIR
from tests.test_integration.fixture_models import (
    ALL_FIXTURE_DOCS,
    NON_DOCUMENT_FIXTURES,
    UNBOUND_DOC_FIXTURES,
    FixtureDoc,
)


def _parse(text: str) -> Any:
    yaml = YAML(typ="safe")
    return yaml.load(text)


@pytest.mark.parametrize("doc", ALL_FIXTURE_DOCS, ids=lambda d: d.fixture)
def test_to_data_matches_emitted_yaml(doc: FixtureDoc) -> None:
    """``to_data`` agrees with the parsed YAML for every bound fixture."""
    model = doc.build()
    parsed = _parse(model.to_yaml(doc.header))
    # ``post_process`` runs on the backend node, so it is in the YAML and, by
    # contract, never in ``to_data``. Subtract its effect -- asserting it was
    # there, so the subtraction cannot hide a real difference.
    for key in doc.post_process_root_keys:
        assert key in parsed
        del parsed[key]
    assert to_data(model) == parsed


def test_accounts_for_every_yml_fixture() -> None:
    """The sweep's edge, asserted rather than described.

    Every ``.yml`` under ``fixtures/expected/`` is either swept above, a known
    non-document, or listed as unbound with a reason. A new fixture lands in
    none of the three and fails here, so the set cannot quietly shrink.
    """
    swept = {doc.fixture for doc in ALL_FIXTURE_DOCS}
    unaccounted = sorted(
        path.name
        for path in EXPECTED_DIR.glob("*.yml")
        if path.name not in swept
        and path.name not in UNBOUND_DOC_FIXTURES
        and path.name not in NON_DOCUMENT_FIXTURES
    )
    assert unaccounted == []
