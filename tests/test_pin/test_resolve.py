"""Tests for ghagen.pin.resolve — GitHub API ref resolution."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ghagen.pin.resolve import ResolveError, _ParsedUses, parse_uses, resolve_ref

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
