"""Tests for ghagen.pin.versions — version comparison for action tags."""

from __future__ import annotations

from packaging.version import Version

from ghagen.pin.versions import classify_bump, find_latest_tag, parse_tag


class TestParseTag:
    def test_major_only(self):
        assert parse_tag("v4") == Version("4.0.0")

    def test_major_minor(self):
        assert parse_tag("v4.1") == Version("4.1.0")

    def test_full_semver(self):
        assert parse_tag("v4.1.2") == Version("4.1.2")

    def test_no_v_prefix(self):
        assert parse_tag("4.1.2") == Version("4.1.2")

    def test_prefix_dash(self):
        assert parse_tag("prefix-v1.0.0") == Version("1.0.0")

    def test_prefix_slash(self):
        assert parse_tag("prefix/v1.0.0") == Version("1.0.0")

    def test_nonsemver_main(self):
        assert parse_tag("main") is None

    def test_nonsemver_release_branch(self):
        """release/v1 looks like a branch ref, not a tag."""
        assert parse_tag("release/v1") is None

    def test_empty_string(self):
        assert parse_tag("") is None

    def test_sha_like(self):
        assert parse_tag("a" * 40) is None

    def test_prefix_with_major_minor(self):
        assert parse_tag("action-v2.1") == Version("2.1.0")

    def test_prefix_slash_with_full_semver(self):
        assert parse_tag("tools/v3.2.1") == Version("3.2.1")


class TestClassifyBump:
    def test_major(self):
        assert classify_bump(Version("1.0.0"), Version("2.0.0")) == "major"

    def test_minor(self):
        assert classify_bump(Version("1.0.0"), Version("1.1.0")) == "minor"

    def test_patch(self):
        assert classify_bump(Version("1.0.0"), Version("1.0.1")) == "patch"

    def test_major_with_minor_change(self):
        """Major bump takes precedence even when minor also differs."""
        assert classify_bump(Version("1.2.3"), Version("2.0.0")) == "major"

    def test_minor_with_patch_change(self):
        """Minor bump takes precedence even when patch also differs."""
        assert classify_bump(Version("1.0.0"), Version("1.1.1")) == "minor"

    def test_same_version(self):
        """Same version classifies as patch (no actual bump)."""
        assert classify_bump(Version("1.0.0"), Version("1.0.0")) == "patch"


class TestFindLatestTag:
    def test_returns_latest(self):
        result = find_latest_tag("v1.0.0", ["v1.0.0", "v1.1.0", "v2.0.0"])
        assert result == "v2.0.0"

    def test_returns_none_when_current_is_latest(self):
        result = find_latest_tag("v2.0.0", ["v1.0.0", "v1.1.0", "v2.0.0"])
        assert result is None

    def test_handles_mixed_semver_and_nonsemver(self):
        tags = ["v1.0.0", "v2.0.0", "main", "release/v1", "nightly"]
        result = find_latest_tag("v1.0.0", tags)
        assert result == "v2.0.0"

    def test_returns_none_for_nonsemver_current(self):
        result = find_latest_tag("main", ["v1.0.0", "v2.0.0"])
        assert result is None

    def test_preserves_v_prefix(self):
        result = find_latest_tag("v1", ["v1", "v2", "v3"])
        assert result == "v3"

    def test_single_segment_tags(self):
        result = find_latest_tag("v3", ["v1", "v2", "v3", "v4", "v5"])
        assert result == "v5"

    def test_prefix_filtering(self):
        """Tags with a different prefix are excluded."""
        tags = ["action-v1.0.0", "action-v2.0.0", "other-v3.0.0"]
        result = find_latest_tag("action-v1.0.0", tags)
        assert result == "action-v2.0.0"

    def test_empty_available_tags(self):
        result = find_latest_tag("v1.0.0", [])
        assert result is None

    def test_no_newer_tags(self):
        result = find_latest_tag("v3.0.0", ["v1.0.0", "v2.0.0"])
        assert result is None
