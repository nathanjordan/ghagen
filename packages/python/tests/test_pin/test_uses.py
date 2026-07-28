"""Tests for ghagen.pin.uses — the canonical parsed ``uses:`` reference."""

from __future__ import annotations

from ghagen.pin.uses import UsesRef

SHA = "a" * 40


class TestParse:
    def test_owner_repo_ref(self):
        parsed = UsesRef.parse("actions/checkout@v4")
        assert parsed == UsesRef(owner="actions", repo="checkout", path=None, ref="v4")

    def test_owner_repo_path_ref(self):
        parsed = UsesRef.parse("owner/repo/path/sub@ref")
        assert parsed == UsesRef(owner="owner", repo="repo", path="path/sub", ref="ref")

    def test_reusable_workflow_path(self):
        parsed = UsesRef.parse("octo-org/repo/.github/workflows/ci.yml@v1")
        assert parsed == UsesRef(
            owner="octo-org",
            repo="repo",
            path=".github/workflows/ci.yml",
            ref="v1",
        )

    def test_local_ref_is_none(self):
        assert UsesRef.parse("./local-action") is None

    def test_docker_ref_is_none(self):
        assert UsesRef.parse("docker://node:18") is None

    def test_no_at_is_none(self):
        assert UsesRef.parse("actions/checkout") is None

    def test_no_slash_is_none(self):
        assert UsesRef.parse("checkout@v4") is None


class TestPinnability:
    def test_version_ref_is_pinnable(self):
        parsed = UsesRef.parse("actions/checkout@v4")
        assert parsed is not None
        assert parsed.ref_is_sha is False
        assert parsed.is_pinnable is True

    def test_sha_ref_is_not_pinnable(self):
        parsed = UsesRef.parse(f"actions/checkout@{SHA}")
        assert parsed is not None
        assert parsed.ref_is_sha is True
        assert parsed.is_pinnable is False

    def test_uppercase_sha_is_not_a_sha(self):
        """SHA detection requires lowercase hex."""
        parsed = UsesRef.parse(f"actions/checkout@{'A' * 40}")
        assert parsed is not None
        assert parsed.ref_is_sha is False
        assert parsed.is_pinnable is True


class TestActionPart:
    def test_without_path(self):
        parsed = UsesRef.parse("actions/checkout@v4")
        assert parsed is not None
        assert parsed.action_part == "actions/checkout"

    def test_with_path(self):
        parsed = UsesRef.parse("octo-org/repo/.github/workflows/ci.yml@v1")
        assert parsed is not None
        assert parsed.action_part == "octo-org/repo/.github/workflows/ci.yml"


class TestUses:
    """``UsesRef.uses`` losslessly reconstructs the authored string.

    This is the dedup key and the lockfile key, so the round-trip must be
    byte-identical for every ref shape.
    """

    def test_roundtrip_plain_action(self):
        s = "actions/checkout@v4"
        parsed = UsesRef.parse(s)
        assert parsed is not None
        assert parsed.uses == s

    def test_roundtrip_pathful_reusable_workflow(self):
        s = "octo-org/repo/.github/workflows/ci.yml@v1"
        parsed = UsesRef.parse(s)
        assert parsed is not None
        assert parsed.uses == s

    def test_roundtrip_sha_pinned(self):
        s = f"actions/checkout@{SHA}"
        parsed = UsesRef.parse(s)
        assert parsed is not None
        assert parsed.uses == s


class TestWithSha:
    def test_rebuild_without_path(self):
        parsed = UsesRef.parse("actions/checkout@v4")
        assert parsed is not None
        assert parsed.with_sha(SHA) == f"actions/checkout@{SHA}"

    def test_rebuild_with_path(self):
        parsed = UsesRef.parse("octo-org/repo/.github/workflows/ci.yml@v1")
        assert parsed is not None
        assert parsed.with_sha(SHA) == f"octo-org/repo/.github/workflows/ci.yml@{SHA}"
