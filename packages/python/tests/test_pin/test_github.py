"""Tests for ghagen.pin.github — GitHubClient driven through a FakeTransport.

The GitHub logic (URL building, error mapping, pagination, annotated-tag
dereferencing) is exercised without network access via a canned transport.
The pure helpers are unit-tested directly.
"""

from __future__ import annotations

import pytest

from ghagen.pin.github import (
    GitHubClient,
    ResolveError,
    Response,
    TransportError,
    _commit_sha,
    _is_annotated_tag,
    _parse_next_link,
    _ref_urls,
)
from tests.test_pin.transport_contract import FakeTransport, canned, canned_raw

SHA = "a" * 40
TAG_SHA = "b" * 40


class TestResolveRef:
    def test_lightweight_tag(self):
        transport = FakeTransport(
            {"tags/v4": canned({"object": {"sha": SHA, "type": "commit"}})}
        )
        client = GitHubClient(transport)
        assert client.resolve_ref("actions", "checkout", "v4") == SHA
        assert transport.calls[0] == (
            "https://api.github.com/repos/actions/checkout/git/ref/tags/v4"
        )

    def test_falls_back_to_heads(self):
        transport = FakeTransport(
            {"heads/main": canned({"object": {"sha": SHA, "type": "commit"}})}
        )
        client = GitHubClient(transport)
        assert client.resolve_ref("actions", "checkout", "main") == SHA
        # tags/ tried first (404), then heads/.
        assert "/tags/main" in transport.calls[0]
        assert "/heads/main" in transport.calls[1]

    def test_annotated_tag_dereference(self):
        transport = FakeTransport(
            {
                "git/ref/tags/v4": canned({"object": {"sha": TAG_SHA, "type": "tag"}}),
                f"git/tags/{TAG_SHA}": canned(
                    {"object": {"sha": SHA, "type": "commit"}}
                ),
            }
        )
        client = GitHubClient(transport)
        assert client.resolve_ref("actions", "checkout", "v4") == SHA

    def test_annotated_tag_not_a_commit_raises(self):
        transport = FakeTransport(
            {
                "git/ref/tags/v4": canned({"object": {"sha": TAG_SHA, "type": "tag"}}),
                f"git/tags/{TAG_SHA}": canned({"object": {"sha": SHA, "type": "tree"}}),
            }
        )
        client = GitHubClient(transport)
        with pytest.raises(ResolveError, match="does not point to a commit"):
            client.resolve_ref("actions", "checkout", "v4")

    def test_not_found_raises(self):
        transport = FakeTransport({})  # everything 404s
        client = GitHubClient(transport)
        with pytest.raises(ResolveError, match="Could not resolve"):
            client.resolve_ref("actions", "checkout", "nonexistent")

    def test_token_passed_to_transport(self):
        transport = FakeTransport(
            {"tags/v4": canned({"object": {"sha": SHA, "type": "commit"}})}
        )
        client = GitHubClient(transport, token="my-token")
        client.resolve_ref("actions", "checkout", "v4")
        assert transport.tokens == ["my-token"]

    def test_network_error_becomes_resolve_error(self):
        transport = FakeTransport({"tags/v4": TransportError("boom")})
        client = GitHubClient(transport)
        with pytest.raises(ResolveError, match="Network error"):
            client.resolve_ref("actions", "checkout", "v4")

    def test_server_error_raises(self):
        transport = FakeTransport({"tags/v4": canned({}, status=500)})
        client = GitHubClient(transport)
        with pytest.raises(ResolveError, match="500"):
            client.resolve_ref("actions", "checkout", "v4")


class TestListTags:
    def _refs(self, *names: str) -> list[dict]:
        return [{"ref": f"refs/tags/{name}"} for name in names]

    def test_basic_listing(self):
        transport = FakeTransport(
            {"git/refs/tags": canned(self._refs("v1", "v2", "v3.0.0"))}
        )
        client = GitHubClient(transport)
        assert client.list_tags("actions", "checkout") == ["v1", "v2", "v3.0.0"]

    def test_pagination_via_link_header(self):
        next_url = "https://api.github.com/repos/o/r/git/refs/tags?page=2"
        transport = FakeTransport(
            {
                "git/refs/tags?page=2": canned(self._refs("v3")),
                # First page (no ?page=2): served before the more specific match
                # only if it precedes; use a distinct pattern.
                "git/refs/tags": [
                    canned(
                        self._refs("v1", "v2"),
                        headers={"Link": f'<{next_url}>; rel="next"'},
                    ),
                ],
            }
        )
        client = GitHubClient(transport)
        assert client.list_tags("o", "r") == ["v1", "v2", "v3"]

    def test_no_tags_404(self):
        transport = FakeTransport({})  # 404
        client = GitHubClient(transport)
        assert client.list_tags("empty-org", "empty-repo") == []

    def test_rate_limit_403(self, capsys):
        transport = FakeTransport(
            {
                "git/refs/tags": canned(
                    {"message": "rate limited"},
                    status=403,
                    headers={"X-RateLimit-Remaining": "0"},
                )
            }
        )
        client = GitHubClient(transport)
        with pytest.raises(ResolveError, match="403"):
            client.list_tags("actions", "checkout")
        err = capsys.readouterr().err
        assert "rate limit hit" in err
        assert "remaining=0" in err

    def test_token_passed_to_transport(self):
        transport = FakeTransport({"git/refs/tags": canned([])})
        client = GitHubClient(transport, token="secret")
        client.list_tags("actions", "checkout")
        assert transport.tokens == ["secret"]


class TestPureHelpers:
    def test_ref_urls_fallback_order(self):
        urls = _ref_urls("actions", "checkout", "v4")
        assert urls == [
            "https://api.github.com/repos/actions/checkout/git/ref/tags/v4",
            "https://api.github.com/repos/actions/checkout/git/ref/heads/v4",
        ]

    def test_is_annotated_tag(self):
        assert _is_annotated_tag({"type": "tag"}) is True
        assert _is_annotated_tag({"type": "commit"}) is False
        assert _is_annotated_tag({}) is False

    def test_commit_sha(self):
        assert _commit_sha({"type": "commit", "sha": SHA}) == SHA
        assert _commit_sha({"type": "tag", "sha": SHA}) is None
        assert _commit_sha({"type": "commit"}) is None
        assert _commit_sha({}) is None

    def test_parse_next_link_extracts_next(self):
        header = (
            '<https://api.github.com/repos/o/r/git/refs/tags?page=2>; rel="next", '
            '<https://api.github.com/repos/o/r/git/refs/tags?page=5>; rel="last"'
        )
        assert _parse_next_link(header) == (
            "https://api.github.com/repos/o/r/git/refs/tags?page=2"
        )

    def test_parse_next_link_none_cases(self):
        assert _parse_next_link(None) is None
        assert _parse_next_link("") is None
        assert _parse_next_link('<https://api.github.com/x?page=1>; rel="last"') is None


class TestMalformedJson:
    """A malformed 200 must surface as ResolveError, not JSONDecodeError."""

    def test_resolve_ref_malformed_body(self):
        transport = FakeTransport({"tags/v4": canned_raw(b"<html>not json</html>")})
        client = GitHubClient(transport)
        with pytest.raises(ResolveError, match="Failed to parse JSON response"):
            client.resolve_ref("actions", "checkout", "v4")

    def test_list_tags_malformed_body(self):
        transport = FakeTransport(
            {"git/refs/tags": canned_raw(b"<html>not json</html>")}
        )
        client = GitHubClient(transport)
        with pytest.raises(ResolveError, match="Failed to parse JSON response"):
            client.list_tags("actions", "checkout")


class TestResponse:
    def test_header_is_case_insensitive(self):
        resp = Response(status=200, body=b"{}", headers={"Link": '<u>; rel="next"'})
        assert resp.header("link") == '<u>; rel="next"'
        assert resp.header("LINK") == '<u>; rel="next"'
        assert resp.header("missing") is None

    def test_json_parses_body(self):
        resp = Response(status=200, body=b'{"a": 1}')
        assert resp.json() == {"a": 1}
