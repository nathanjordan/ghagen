"""Tests for ghagen.pin.versions — a driver over the shared tag grammar table.

The accept-set, the canonical release, the total order, the prefix filter and
the severity classification are declared once in ``schema/tag-grammar.yml``
and read here *and* by the TypeScript suite
(``packages/typescript/src/pin/versions.test.ts``). Both ports held to the
same table means both implement the same grammar — cross-port behaviour
agreement, structurally.

Each section carries a consumed-every-row guard, mirroring the scope-key
parity assertion the conformance sweeps already use: a row this driver does
not *execute* fails a test, so a case added for one port cannot silently skip
the other.  The guards compare the ids the test bodies recorded against the
file read fresh from disk — never two views of the same in-memory object,
which is a comparison that cannot fail.
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

#: Row ids the drivers below actually ran, recorded by the test bodies.
#:
#: The guards at the end of this module compare these against the table read
#: fresh from disk.  Comparing the collected-cases list against ``_TABLE``
#: instead would be a tautology — both sides come from the same object, so a
#: driver that is handed every row and quietly declines to check some of them
#: (an early ``return``, a body that ignores its argument, a ``parametrize``
#: list that was sliced) still looks complete.  Only what a body executed
#: counts as driven.
_DRIVEN_PARSE: set[str] = set()
_DRIVEN_COMPARE: set[int] = set()


@pytest.mark.parametrize(
    "tag,expected", _PARSE_CASES, ids=[tag for tag, _ in _PARSE_CASES]
)
def test_parse_grammar(tag: str, expected: dict[str, Any] | None) -> None:
    """``parse_tag`` accepts exactly the declared shapes, with the declared release."""
    _DRIVEN_PARSE.add(tag)
    parsed = parse_tag(tag)
    if expected is None:
        assert parsed is None
    else:
        assert parsed is not None
        assert parsed.tag == tag
        assert parsed.prefix == expected["prefix"]
        assert list(parsed.release) == expected["release"]


@pytest.mark.parametrize(
    "index,case",
    _COMPARE_CASES,
    ids=[str(i) for i, _ in _COMPARE_CASES],
)
def test_compare_grammar(index: int, case: dict[str, Any]) -> None:
    """``latest_bump`` picks the declared winner and classifies it as declared."""
    _DRIVEN_COMPARE.add(index)
    bump = latest_bump(case["current"], case["available"])
    if case["latest"] is None:
        assert bump is None
    else:
        assert bump is not None
        assert bump.current.tag == case["current"]
        assert bump.latest.tag == case["latest"]
        assert bump.severity == case["severity"]


def _table_on_disk() -> dict[str, Any]:
    """The table as it is on disk right now, read independently of ``_TABLE``."""
    return YAML(typ="safe").load(TABLE_PATH.read_text())


# The two guards below need the drivers above to have run, so they are defined
# last (pytest runs a module in definition order) and are meaningful only in a
# whole-module run.  Selecting one of them alone reports the whole table as
# undriven, which is the truth for that selection.


def test_every_parse_row_is_driven() -> None:
    """``test_parse_grammar`` checked every key of the shared ``parse`` map."""
    declared = set(_table_on_disk()["parse"])
    assert declared == _DRIVEN_PARSE, (
        f"declared but never checked: {sorted(declared - _DRIVEN_PARSE)!r}; "
        f"checked but not declared: {sorted(_DRIVEN_PARSE - declared)!r}"
    )


def test_every_compare_row_is_driven() -> None:
    """``test_compare_grammar`` checked every element of the ``compare`` list."""
    declared = set(range(len(_table_on_disk()["compare"])))
    assert declared == _DRIVEN_COMPARE, (
        f"declared but never checked: {sorted(declared - _DRIVEN_COMPARE)}; "
        f"checked but not declared: {sorted(_DRIVEN_COMPARE - declared)}"
    )
