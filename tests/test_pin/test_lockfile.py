"""Tests for ghagen.pin.lockfile — data model and TOML I/O."""

from __future__ import annotations

from datetime import UTC, datetime

from ghagen.pin.lockfile import Lockfile, PinEntry, read_lockfile, write_lockfile

SAMPLE_SHA = "a" * 40
SAMPLE_SHA2 = "b" * 40
SAMPLE_TIME = datetime(2026, 4, 9, 14, 30, 0, tzinfo=UTC)


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

    def test_merge(self):
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME)
            }
        )
        lf.merge(
            {
                "actions/setup-python@v5": PinEntry(
                    sha=SAMPLE_SHA2, resolved_at=SAMPLE_TIME
                )
            }
        )
        assert len(lf.pins) == 2
        assert lf.get("actions/setup-python@v5").sha == SAMPLE_SHA2

    def test_merge_overwrites(self):
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME)
            }
        )
        lf.merge(
            {"actions/checkout@v4": PinEntry(sha=SAMPLE_SHA2, resolved_at=SAMPLE_TIME)}
        )
        assert lf.get("actions/checkout@v4").sha == SAMPLE_SHA2

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
        assert "actions/setup-python@v5" not in lf.pins
        assert "actions/checkout@v4" in lf.pins

    def test_prune_nothing(self):
        lf = Lockfile(
            pins={
                "actions/checkout@v4": PinEntry(sha=SAMPLE_SHA, resolved_at=SAMPLE_TIME)
            }
        )
        removed = lf.prune(keep={"actions/checkout@v4"})
        assert removed == 0


class TestRoundTrip:
    def test_write_and_read(self, tmp_path):
        path = tmp_path / ".github" / "ghagen.lock.toml"
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
        assert len(lf2.pins) == 2
        assert lf2.get("actions/checkout@v4").sha == SAMPLE_SHA
        assert lf2.get("actions/setup-python@v5").sha == SAMPLE_SHA2

    def test_read_missing_file(self, tmp_path):
        lf = read_lockfile(tmp_path / "does-not-exist.toml")
        assert len(lf.pins) == 0

    def test_sorted_output(self, tmp_path):
        path = tmp_path / "lock.toml"
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
