"""Tests for ghagen.pin.resolve — GitHub API ref resolution."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ghagen.pin.resolve import (
    ResolveError,
    _ParsedUses,
    _parse_next_link,
    list_tags,
    parse_uses,
    resolve_ref,
)

SHA = "a" * 40
TAG_SHA = "b" * 40


class TestParseUses:
    def test_simple(self):
        result = parse_uses("actions/checkout@v4")
        assert result == _ParsedUses(
            owner="actions", repo="checkout", path=None, ref="v4"
        )

    def test_with_path(self):
        result = parse_uses("octo-org/repo/.github/workflows/ci.yml@v1")
        assert result == _ParsedUses(
            owner="octo-org", repo="repo", path=".github/workflows/ci.yml", ref="v1"
        )

    def test_no_at(self):
        with pytest.raises(ValueError, match="No @ref"):
            parse_uses("actions/checkout")

    def test_no_slash(self):
        with pytest.raises(ValueError, match="Cannot parse owner/repo"):
            parse_uses("checkout@v4")


class TestResolveRef:
    def _mock_api(self, responses: dict[str, dict | None]):
        """Return a side_effect function for _api_get that looks up URL patterns."""
        from ghagen.pin.resolve import _NotFoundError

        def side_effect(url, *, token=None):
            for pattern, data in responses.items():
                if pattern in url:
                    if data is None:
                        raise _NotFoundError
                    return data
            raise _NotFoundError

        return side_effect

    def test_lightweight_tag(self):
        responses = {
            "tags/v4": {
                "object": {"sha": SHA, "type": "commit"},
            },
        }
        with patch(
            "ghagen.pin.resolve._api_get", side_effect=self._mock_api(responses)
        ):
            result = resolve_ref("actions", "checkout", "v4")
        assert result == SHA

    def test_annotated_tag_dereference(self):
        responses = {
            "tags/v4": {
                "object": {"sha": TAG_SHA, "type": "tag"},
            },
            f"git/tags/{TAG_SHA}": {
                "object": {"sha": SHA, "type": "commit"},
            },
        }
        with patch(
            "ghagen.pin.resolve._api_get", side_effect=self._mock_api(responses)
        ):
            result = resolve_ref("actions", "checkout", "v4")
        assert result == SHA

    def test_falls_back_to_heads(self):
        responses = {
            "tags/main": None,
            "heads/main": {
                "object": {"sha": SHA, "type": "commit"},
            },
        }
        with patch(
            "ghagen.pin.resolve._api_get", side_effect=self._mock_api(responses)
        ):
            result = resolve_ref("actions", "checkout", "main")
        assert result == SHA

    def test_not_found_raises(self):
        responses = {
            "tags/nonexistent": None,
            "heads/nonexistent": None,
        }
        with patch(
            "ghagen.pin.resolve._api_get", side_effect=self._mock_api(responses)
        ), pytest.raises(ResolveError, match="Could not resolve"):
            resolve_ref("actions", "checkout", "nonexistent")

    def test_token_passed_through(self):
        calls = []

        def mock_get(url, *, token=None):
            calls.append(token)
            return {"object": {"sha": SHA, "type": "commit"}}

        with patch("ghagen.pin.resolve._api_get", side_effect=mock_get):
            resolve_ref("actions", "checkout", "v4", token="my-token")

        assert calls[0] == "my-token"


class TestListTags:
    """Tests for list_tags()."""

    def _make_refs(self, *tag_names: str) -> list[dict]:
        """Build a list of GitHub git/refs responses for the given tag names."""
        return [
            {"ref": f"refs/tags/{name}", "object": {"sha": SHA, "type": "commit"}}
            for name in tag_names
        ]

    def test_basic_listing(self):
        """Single-page response returns stripped tag names."""
        refs = self._make_refs("v1", "v2", "v3.0.0")
        with patch(
            "ghagen.pin.resolve._api_get_page",
            return_value=(refs, None),
        ):
            result = list_tags("actions", "checkout")
        assert result == ["v1", "v2", "v3.0.0"]

    def test_pagination(self):
        """Multi-page responses are collected into a single list."""
        page1 = self._make_refs("v1", "v2")
        page2 = self._make_refs("v3")
        next_url = "https://api.github.com/repos/actions/checkout/git/refs/tags?page=2"

        call_count = 0

        def mock_get_page(url, *, token=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return page1, next_url
            return page2, None

        with patch(
            "ghagen.pin.resolve._api_get_page",
            side_effect=mock_get_page,
        ):
            result = list_tags("actions", "checkout")
        assert result == ["v1", "v2", "v3"]
        assert call_count == 2

    def test_no_tags_404(self):
        """Repos with no tags return an empty list (API returns 404)."""
        from ghagen.pin.resolve import _NotFoundError

        with patch(
            "ghagen.pin.resolve._api_get_page",
            side_effect=_NotFoundError,
        ):
            result = list_tags("empty-org", "empty-repo")
        assert result == []

    def test_rate_limit_error(self):
        """403 rate-limit errors propagate as ResolveError."""
        with patch(
            "ghagen.pin.resolve._api_get_page",
            side_effect=ResolveError("GitHub API error 403 for ...: rate limit"),
        ), pytest.raises(ResolveError, match="403"):
            list_tags("actions", "checkout")

    def test_token_passed_through(self):
        """The token kwarg is forwarded to the underlying API call."""
        calls: list[str | None] = []

        def mock_get_page(url, *, token=None):
            calls.append(token)
            return [], None

        with patch(
            "ghagen.pin.resolve._api_get_page",
            side_effect=mock_get_page,
        ):
            list_tags("actions", "checkout", token="secret-token")

        assert calls == ["secret-token"]


class TestParseNextLink:
    """Tests for _parse_next_link() Link header parsing."""

    def test_extracts_next_url(self):
        header = (
            '<https://api.github.com/repos/o/r/git/refs/tags?page=2>; rel="next", '
            '<https://api.github.com/repos/o/r/git/refs/tags?page=5>; rel="last"'
        )
        assert _parse_next_link(header) == (
            "https://api.github.com/repos/o/r/git/refs/tags?page=2"
        )

    def test_none_when_no_header(self):
        assert _parse_next_link(None) is None

    def test_none_when_no_next_rel(self):
        header = '<https://api.github.com/repos/o/r/git/refs/tags?page=1>; rel="last"'
        assert _parse_next_link(header) is None

    def test_empty_string(self):
        assert _parse_next_link("") is None
