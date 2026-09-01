"""Tests for ghagen.pin.lockfile — data model and YAML I/O."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ghagen.pin.lockfile import (
    Lockfile,
    LockfileError,
    PinEntry,
    read_lockfile,
    write_lockfile,
)
from ghagen_schema.paths import EXPECTED_DIR

SAMPLE_SHA = "a" * 40
SAMPLE_SHA2 = "b" * 40
SAMPLE_TIME = datetime(2026, 4, 9, 14, 30, 0, tzinfo=UTC)

GOLDEN_PATH = EXPECTED_DIR / "lockfile_golden.yml"

#: The exact entries ``fixtures/expected/lockfile_golden.yml`` encodes. Both
#: ports write these to the golden's bytes and read the golden back to them.
GOLDEN_ENTRIES = {
    "actions/checkout@v4": PinEntry(
        sha="3df4ab11eba7bda6032a0b82a6bb43b11571feac",
        resolved_at=datetime(2026, 4, 9, 14, 30, 0, tzinfo=UTC),
    ),
    # An all-digit SHA: the case where ruamel and the `yaml` package pick
    # different quotes when left to their own heuristics.
    "docker://alpine:3.19": PinEntry(
        sha="1234567890123456789012345678901234567890",
        resolved_at=datetime(2026, 4, 9, 14, 30, 0, tzinfo=UTC),
    ),
    "pypa/gh-action-pypi-publish@release/v1": PinEntry(
        sha="b" * 40,
        resolved_at=datetime(2026, 4, 8, 0, 0, 0, tzinfo=UTC),
    ),
}


def _lock_doc(resolved_at_literal: str) -> str:
    """A one-entry lockfile document with *resolved_at_literal* verbatim."""
    return (
        "pins:\n"
        "  actions/checkout@v4:\n"
        f'    sha: "{SAMPLE_SHA}"\n'
        f"    resolved_at: {resolved_at_literal}\n"
    )


class TestPinEntry:
    def test_frozen(self):
        entry = PinEntry(sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME)
        assert entry.sha == SAMPLE_SHA
        assert entry.resolved_at == SAMPLE_TIME


class TestLockfile:
    def test_get_existing(self):
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME)
            }
        )
        assert lf.get("actions/checkout@v4") is not None
        assert lf.get("actions/checkout@v4").sha == SAMPLE_SHA

    def test_get_missing(self):
        lf = Lockfile()
        assert lf.get("actions/checkout@v4") is None

    def test_set(self):
        lf = Lockfile()
        lf.set("actions/checkout@v4", PinEntry(sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME))
        assert lf.get("actions/checkout@v4").sha == SAMPLE_SHA
        assert len(lf) == 1

    def test_set_replaces(self):
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME)
            }
        )
        lf.set(
            "actions/checkout@v4", PinEntry(sha=SAMPLE_SHA2, resolved_at=SAMPLE_TIME)
        )
        assert lf.get("actions/checkout@v4").sha == SAMPLE_SHA2
        assert len(lf) == 1

    def test_constructor_bulk_load(self):
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(
                    sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME
                ),
                "actions/setup-python@v5": PinEntry(
                    sha=SAMPLE_SHA2, resolved_at=SAMPLE_TIME
                ),
            }
        )
        assert len(lf) == 2
        assert lf.get("actions/setup-python@v5").sha == SAMPLE_SHA2

    def test_prune(self):
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(
                    sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME
                ),
                "actions/setup-python@v5": PinEntry(
                    sha=SAMPLE_SHA2, resolved_at=SAMPLE_TIME
                ),
            }
        )
        removed = lf.prune(keep={"actions/checkout@v4"})
        assert removed == 1
        assert "actions/setup-python@v5" not in lf
        assert "actions/checkout@v4" in lf

    def test_prune_nothing(self):
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME)
            }
        )
        removed = lf.prune(keep={"actions/checkout@v4"})
        assert removed == 0

    def test_contains(self):
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME)
            }
        )
        assert "actions/checkout@v4" in lf
        assert "actions/setup-python@v5" not in lf

    def test_keys(self):
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(
                    sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME
                ),
                "actions/setup-python@v5": PinEntry(
                    sha=SAMPLE_SHA2, resolved_at=SAMPLE_TIME
                ),
            }
        )
        assert set(lf.keys()) == {"actions/checkout@v4", "actions/setup-python@v5"}
        assert len(lf) == 2


class TestReadValidation:
    def _write(self, path, body: str) -> None:
        path.write_text(body)

    def test_missing_sha_raises(self, tmp_path):
        path = tmp_path / "lock.yml"
        self._write(
            path,
            "pins:\n"
            "  actions/checkout@v4:\n"
            '    resolved_at: "2026-04-09T14:30:00+00:00"\n',
        )
        with pytest.raises(LockfileError) as exc:
            read_lockfile(path)
        assert "sha" in str(exc.value)
        assert "actions/checkout@v4" in str(exc.value)

    def test_non_mapping_entry_raises(self, tmp_path):
        path = tmp_path / "lock.yml"
        self._write(
            path,
            "pins:\n  actions/checkout@v4: just-a-string\n",
        )
        with pytest.raises(LockfileError) as exc:
            read_lockfile(path)
        assert "actions/checkout@v4" in str(exc.value)

    def test_bad_resolved_at_raises(self, tmp_path):
        path = tmp_path / "lock.yml"
        self._write(
            path,
            "pins:\n"
            "  actions/checkout@v4:\n"
            f'    sha: "{SAMPLE_SHA}"\n'
            '    resolved_at: "not-a-timestamp"\n',
        )
        with pytest.raises(LockfileError) as exc:
            read_lockfile(path)
        assert "resolved_at" in str(exc.value)

    def test_missing_resolved_at_raises(self, tmp_path):
        path = tmp_path / "lock.yml"
        self._write(
            path,
            f'pins:\n  actions/checkout@v4:\n    sha: "{SAMPLE_SHA}"\n',
        )
        with pytest.raises(LockfileError) as exc:
            read_lockfile(path)
        assert "resolved_at" in str(exc.value)

    def test_pins_not_mapping_raises(self, tmp_path):
        path = tmp_path / "lock.yml"
        self._write(path, "pins:\n  - actions/checkout@v4\n")
        with pytest.raises(LockfileError) as exc:
            read_lockfile(path)
        assert "pins" in str(exc.value)


class TestRoundTrip:
    def test_write_and_read(self, tmp_path):
        path = tmp_path / ".ghagen.lock.yml"
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(
                    sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME
                ),
                "actions/setup-python@v5": PinEntry(
                    sha=SAMPLE_SHA2, resolved_at=SAMPLE_TIME
                ),
            }
        )
        write_lockfile(lf, path)

        # File should exist and have the header.
        content = path.read_text()
        assert "Auto-generated" in content

        # Read back and verify.
        lf2 = read_lockfile(path)
        assert len(lf2) == 2
        assert lf2.get("actions/checkout@v4").sha == SAMPLE_SHA
        assert lf2.get("actions/setup-python@v5").sha == SAMPLE_SHA2

    def test_read_missing_file(self, tmp_path):
        lf = read_lockfile(tmp_path / "does-not-exist.yml")
        assert len(lf) == 0

    def test_sorted_output(self, tmp_path):
        path = tmp_path / "lock.yml"
        lf = Lockfile(
            pins={
                "z-org/z-repo@v1": PinEntry(sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME),
                "a-org/a-repo@v2": PinEntry(sha=SAMPLE_SHA2, resolved_at=SAMPLE_TIME),
            }
        )
        write_lockfile(lf, path)
        content = path.read_text()
        # "a-org" should appear before "z-org" in sorted output.
        assert content.index("a-org") < content.index("z-org")

    def test_round_trip_byte_identical(self, tmp_path):
        path1 = tmp_path / "lock1.yml"
        lf = Lockfile(
            pins={
                "z-org/z-repo@v1": PinEntry(sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME),
                "a-org/a-repo@v2": PinEntry(sha=SAMPLE_SHA2, resolved_at=SAMPLE_TIME),
            }
        )
        write_lockfile(lf, path1)
        first = path1.read_bytes()

        # read -> write must reproduce the exact same bytes.
        path2 = tmp_path / "lock2.yml"
        write_lockfile(read_lockfile(path1), path2)
        assert path2.read_bytes() == first


class TestGoldenConformance:
    """``fixtures/expected/lockfile_golden.yml`` is the cross-port byte oracle."""

    def test_write_matches_golden_bytes(self, tmp_path):
        path = tmp_path / "lock.yml"
        write_lockfile(Lockfile(pins=GOLDEN_ENTRIES), path)
        assert path.read_bytes() == GOLDEN_PATH.read_bytes()

    def test_read_golden_yields_entries(self):
        lf = read_lockfile(GOLDEN_PATH)
        assert set(lf.keys()) == set(GOLDEN_ENTRIES)
        for uses, expected in GOLDEN_ENTRIES.items():
            entry = lf.get(uses)
            assert entry.sha == expected.sha
            assert entry.resolved_at == expected.resolved_at
            assert entry.resolved_at.utcoffset().total_seconds() == 0

    def test_microseconds_truncated_to_whole_seconds(self, tmp_path):
        path = tmp_path / "lock.yml"
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(
                    sha=SAMPLE_SHA,
                    resolved_at=datetime(2026, 4, 9, 14, 30, 0, 123456, tzinfo=UTC),
                )
            }
        )
        write_lockfile(lf, path)
        assert '    resolved_at: "2026-04-09T14:30:00+00:00"\n' in path.read_text()

    def test_all_digit_sha_is_double_quoted(self, tmp_path):
        path = tmp_path / "lock.yml"
        lf = Lockfile(
            pins={
                "docker://alpine:3.19": PinEntry(sha="1" * 40, resolved_at=SAMPLE_TIME)
            }
        )
        write_lockfile(lf, path)
        assert f'    sha: "{"1" * 40}"\n' in path.read_text()

    def test_ordinary_sha_is_double_quoted(self, tmp_path):
        path = tmp_path / "lock.yml"
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME)
            }
        )
        write_lockfile(lf, path)
        assert f'    sha: "{SAMPLE_SHA}"\n' in path.read_text()

    def test_header_names_the_real_command(self, tmp_path):
        path = tmp_path / "lock.yml"
        write_lockfile(Lockfile(), path)
        assert path.read_text().startswith(
            "# Auto-generated by `ghagen deps pin`. Do not edit manually.\n\n"
        )

    def test_naive_resolved_at_rejected_at_write(self, tmp_path):
        """No TypeScript peer: a ``Date`` cannot be naive (see CONTEXT.md)."""
        path = tmp_path / "lock.yml"
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(
                    sha=SAMPLE_SHA, resolved_at=datetime(2026, 4, 9, 14, 30, 0)
                )
            }
        )
        with pytest.raises(LockfileError) as exc:
            write_lockfile(lf, path)
        assert "resolved_at" in str(exc.value)


class TestKeyQuoting:
    """LATENT (docs/issues/23 item 4): an ambiguous ``uses`` key must be quoted.

    No fixture in ``fixtures/expected/`` reaches this through the CLI --
    every realistic ``uses:`` string already contains a ``/``, an ``@``, or a
    ``docker://`` prefix, none of which is YAML-ambiguous. ``Lockfile``'s
    public API accepts any ``str`` key, though, so this constructs the input
    directly: ``"123456"`` parses as a YAML int unless quoted. Before the fix,
    ruamel single-quoted it (``'123456':``) while the TypeScript peer's
    ``yaml`` package double-quoted it (``"123456":``) -- same semantic key,
    different bytes, and thus a lockfile written by one port and committed
    would read back correctly in both, but re-writing it in the other port
    would produce a byte-level diff with no functional cause.

    ``fixtures/expected/lockfile_key_quoting.yml`` is the shared oracle: both
    ports write this exact ``Lockfile`` and must produce identical bytes.
    """

    def test_write_matches_golden_bytes(self, tmp_path):
        path = tmp_path / "lock.yml"
        lf = Lockfile(
            pins={
                "123456": PinEntry(sha="a" * 40, resolved_at=SAMPLE_TIME),
                "actions/checkout@v4": PinEntry(sha="b" * 40, resolved_at=SAMPLE_TIME),
            }
        )
        write_lockfile(lf, path)
        golden = EXPECTED_DIR / "lockfile_key_quoting.yml"
        assert path.read_bytes() == golden.read_bytes()

    def test_read_round_trips_the_quoted_key(self, tmp_path):
        path = tmp_path / "lock.yml"
        path.write_bytes((EXPECTED_DIR / "lockfile_key_quoting.yml").read_bytes())
        lf = read_lockfile(path)
        assert set(lf.keys()) == {"123456", "actions/checkout@v4"}
        assert lf.get("123456").sha == "a" * 40


class TestDecodeGrammar:
    """Grammar rule 7 — one accepted ``resolved_at`` shape, in both ports."""

    @pytest.mark.parametrize(
        ("literal", "expected"),
        [
            ("2026-04-09T14:30:00+00:00", datetime(2026, 4, 9, 14, 30, tzinfo=UTC)),
            ('"2026-04-09T14:30:00+00:00"', datetime(2026, 4, 9, 14, 30, tzinfo=UTC)),
            ('"2026-04-09T14:30:00Z"', datetime(2026, 4, 9, 14, 30, tzinfo=UTC)),
            (
                '"2026-04-09T14:30:00.123456+00:00"',
                datetime(2026, 4, 9, 14, 30, tzinfo=UTC),
            ),
        ],
    )
    def test_accepted(self, tmp_path, literal, expected):
        path = tmp_path / "lock.yml"
        path.write_text(_lock_doc(literal))
        entry = read_lockfile(path).get("actions/checkout@v4")
        assert entry.resolved_at == expected
        assert entry.resolved_at.utcoffset().total_seconds() == 0

    @pytest.mark.parametrize(
        "literal",
        [
            "2026-04-09",  # bare date
            '"2026-04-09"',  # quoted date
            '"April 9, 2026"',  # non-ISO
            '"2026/04/09"',  # non-ISO
            '"2026-04-09T14:30:00"',  # quoted, naive
            "2026-04-09T14:30:00",  # bare, naive
            '"2026-04-09T14:30:00+02:00"',  # explicit non-UTC offset
            # The following are all forms `datetime.fromisoformat` accepts on
            # its own (and the old, regex-less implementation therefore
            # silently accepted) but the TypeScript peer's `TIMESTAMP_RE`
            # never has -- docs/issues/23 item 3. Each is individually
            # verified in the module docstring's `_TIMESTAMP_RE` discussion.
            '"2026-04-09 14:30:00+00:00"',  # space separator, not T
            '"2026-04-09T14:30:00+0000"',  # offset without a colon
            '"2026-04-09T14:30:00+00"',  # offset with no minutes
            '"2026-04-09T14:30:00,123456+00:00"',  # comma decimal separator
            '"20260409T143000+0000"',  # basic format, no separators
            '"2026-04-09T14:30:00+00:00:00"',  # offset carrying seconds
            '"2026-04-09T14:30:00-00:00"',  # negative-zero offset
        ],
    )
    def test_rejected(self, tmp_path, literal):
        path = tmp_path / "lock.yml"
        path.write_text(_lock_doc(literal))
        with pytest.raises(LockfileError) as exc:
            read_lockfile(path)
        assert "resolved_at" in str(exc.value)


class TestDecodeGrammarFixture:
    """The one tightened-grammar case with its own shared-file oracle.

    ``fixtures/expected/lockfile_space_separator_rejected.yml`` pins the
    space-separator form (accepted by ``datetime.fromisoformat`` alone,
    rejected by the shared ``_TIMESTAMP_RE`` -- docs/issues/23 item 3) as an
    actual on-disk document, read by both ports, rather than only as an
    in-process literal. Flipping the space to ``T`` (one byte) makes the
    fixture a valid timestamp and the read no longer raises, so the test
    goes from a pass to a failure -- proof the fixture is load-bearing.
    """

    def test_rejects_the_golden_space_separator_document(self):
        with pytest.raises(LockfileError) as exc:
            read_lockfile(EXPECTED_DIR / "lockfile_space_separator_rejected.yml")
        assert "resolved_at" in str(exc.value)


class TestErrorMode:
    """One error mode: ``LockfileError`` for anything the reader cannot interpret."""

    @pytest.mark.parametrize(
        "document",
        [
            "just-a-string\n",  # top-level scalar
            "- a\n- b\n",  # top-level sequence
            "0\n",  # top-level int
            '""\n',  # top-level empty string
            "false\n",  # top-level bool
        ],
    )
    def test_top_level_not_a_mapping_raises(self, tmp_path, document):
        path = tmp_path / "lock.yml"
        path.write_text(document)
        with pytest.raises(LockfileError) as exc:
            read_lockfile(path)
        assert "mapping" in str(exc.value)

    def test_yaml_syntax_error_raises_lockfile_error(self, tmp_path):
        path = tmp_path / "lock.yml"
        path.write_text("pins:\n  - [unclosed\n")
        with pytest.raises(LockfileError) as exc:
            read_lockfile(path)
        assert str(path) in str(exc.value)

    def test_empty_document_is_an_empty_lockfile(self, tmp_path):
        path = tmp_path / "lock.yml"
        path.write_text("")
        assert len(read_lockfile(path)) == 0

    def test_missing_file_is_an_empty_lockfile(self, tmp_path):
        assert len(read_lockfile(tmp_path / "nope.yml")) == 0
