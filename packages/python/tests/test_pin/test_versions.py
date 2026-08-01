"""Tests for ghagen.pin.versions — a driver over the shared tag grammar table.

The accept-set, the canonical release, the total order, the prefix filter and
the severity classification are declared once in ``schema/tag-grammar.yml``
and read here *and* by the TypeScript suite
(``packages/typescript/src/pin/versions.test.ts``). Both ports held to the
same table means both implement the same grammar — cross-port behaviour
agreement, structurally.

Each section carries a consumed-every-key guard, mirroring the scope-key
parity assertion the conformance sweeps already use: a row this driver does
not run fails a test, so a case added for one port cannot silently skip the
other.
"""

from __future__ import annotations

from typing import Any

import pytest
from ghagen_schema.paths import SCHEMA_DIR
from ruamel.yaml import YAML

from ghagen.pin.versions import latest_bump, parse_tag

TABLE_PATH = SCHEMA_DIR / "tag-grammar.yml"

_TABLE: dict[str, Any] = YAML(typ="safe").load(TABLE_PATH.read_text())

#: (tag, expected) for every row of the shared ``parse`` map.
_PARSE_CASES: list[tuple[str, dict[str, Any] | None]] = sorted(_TABLE["parse"].items())

#: (index, case) for every row of the shared ``compare`` list.
_COMPARE_CASES: list[tuple[int, dict[str, Any]]] = list(enumerate(_TABLE["compare"]))


@pytest.mark.parametrize(
    "tag,expected", _PARSE_CASES, ids=[tag for tag, _ in _PARSE_CASES]
)
def test_parse_grammar(tag: str, expected: dict[str, Any] | None) -> None:
    """``parse_tag`` accepts exactly the declared shapes, with the declared release."""
    parsed = parse_tag(tag)
    if expected is None:
        assert parsed is None
    else:
        assert parsed is not None
        assert parsed.tag == tag
        assert parsed.prefix == expected["prefix"]
        assert list(parsed.release) == expected["release"]


@pytest.mark.parametrize(
    "case",
    [case for _, case in _COMPARE_CASES],
    ids=[str(i) for i, _ in _COMPARE_CASES],
)
def test_compare_grammar(case: dict[str, Any]) -> None:
    """``latest_bump`` picks the declared winner and classifies it as declared."""
    bump = latest_bump(case["current"], case["available"])
    if case["latest"] is None:
        assert bump is None
    else:
        assert bump is not None
        assert bump.current.tag == case["current"]
        assert bump.latest.tag == case["latest"]
        assert bump.severity == case["severity"]


def test_every_parse_row_is_driven() -> None:
    """Every key of the shared ``parse`` map is a collected case."""
    assert {tag for tag, _ in _PARSE_CASES} == set(_TABLE["parse"])


def test_every_compare_row_is_driven() -> None:
    """Every element of the shared ``compare`` list is a collected case."""
    assert [case for _, case in _COMPARE_CASES] == list(_TABLE["compare"])
