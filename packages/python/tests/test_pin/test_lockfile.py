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
        assert len(lf) == 2
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
        assert lf.contains("actions/checkout@v4")
        assert not lf.contains("actions/setup-python@v5")
        assert "actions/checkout@v4" in lf
        assert "actions/setup-python@v5" not in lf

    def test_iteration_and_keys(self):
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
        assert set(iter(lf)) == {"actions/checkout@v4", "actions/setup-python@v5"}
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
