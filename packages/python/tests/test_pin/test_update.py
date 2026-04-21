"""Tests for ghagen.pin.update — source file string replacement."""

from __future__ import annotations

from pathlib import Path

from ghagen.pin.update import apply_updates


class TestApplyUpdates:
    def test_single_replacement(self, tmp_path: Path):
        f = tmp_path / "wf.py"
        f.write_text('Step(uses="actions/checkout@v4")\n')

        changed = apply_updates(
            {"actions/checkout@v4": "actions/checkout@v5"},
            {"actions/checkout@v4": [f]},
        )

        assert changed == [f]
        assert f.read_text() == 'Step(uses="actions/checkout@v5")\n'

    def test_same_ref_in_multiple_files(self, tmp_path: Path):
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text('uses="actions/checkout@v4"\n')
        f2.write_text('Step(uses="actions/checkout@v4")\n')

        changed = apply_updates(
            {"actions/checkout@v4": "actions/checkout@v5"},
            {"actions/checkout@v4": [f1, f2]},
        )

        assert sorted(changed) == sorted([f1, f2])
        assert "actions/checkout@v5" in f1.read_text()
        assert "actions/checkout@v5" in f2.read_text()

    def test_multiple_different_refs(self, tmp_path: Path):
        f = tmp_path / "wf.py"
        f.write_text(
            'Step(uses="actions/checkout@v4")\nStep(uses="actions/setup-python@v5")\n'
        )

        changed = apply_updates(
            {
                "actions/checkout@v4": "actions/checkout@v5",
                "actions/setup-python@v5": "actions/setup-python@v6",
            },
            {
                "actions/checkout@v4": [f],
                "actions/setup-python@v5": [f],
            },
        )

        assert changed == [f]
        content = f.read_text()
        assert "actions/checkout@v5" in content
        assert "actions/setup-python@v6" in content

    def test_helper_ref_skipped(self, tmp_path: Path):
        """Refs not in ref_locations (helper-provided) are not touched."""
        f = tmp_path / "wf.py"
        f.write_text('Step(uses="custom/action@v1")\n')

        changed = apply_updates(
            {"actions/checkout@v4": "actions/checkout@v5"},
            {},  # no locations → nothing to update
        )

        assert changed == []
        assert f.read_text() == 'Step(uses="custom/action@v1")\n'

    def test_preserves_surrounding_content(self, tmp_path: Path):
        f = tmp_path / "wf.py"
        original = (
            "# My workflow\n"
            "from ghagen import Step\n"
            "\n"
            'step = Step(uses="actions/checkout@v4", with_={"fetch-depth": 0})\n'
            "# end\n"
        )
        f.write_text(original)

        apply_updates(
            {"actions/checkout@v4": "actions/checkout@v5"},
            {"actions/checkout@v4": [f]},
        )

        expected = original.replace("actions/checkout@v4", "actions/checkout@v5")
        assert f.read_text() == expected

    def test_noop_when_old_equals_new(self, tmp_path: Path):
        f = tmp_path / "wf.py"
        f.write_text('Step(uses="actions/checkout@v4")\n')

        changed = apply_updates(
            {"actions/checkout@v4": "actions/checkout@v4"},
            {"actions/checkout@v4": [f]},
        )

        assert changed == []

    def test_empty_updates(self, tmp_path: Path):
        f = tmp_path / "wf.py"
        f.write_text('Step(uses="actions/checkout@v4")\n')

        changed = apply_updates({}, {"actions/checkout@v4": [f]})
        assert changed == []
