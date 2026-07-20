"""Tests for ghagen.pin.github — GitHubClient driven through a FakeTransport.

The GitHub logic (URL building, error mapping, pagination, annotated-tag
dereferencing) is exercised without network access via a canned transport.
The pure helpers are unit-tested directly.
"""

from __future__ import annotations

import json

import pytest

from ghagen.pin.github import (
    GitHubClient,
    Response,
    TransportError,
    _commit_sha,
    _is_annotated_tag,
    _parse_next_link,
    _ref_urls,
)
from ghagen.pin.resolve import ResolveError

SHA = "a" * 40
TAG_SHA = "b" * 40


def _json_response(
    obj: object,
    *,
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> Response:
    """Build a canned JSON :class:`Response`."""
    return Response(
        status=status,
        body=json.dumps(obj).encode(),
        reason="",
        headers=headers or {},
    )


class FakeTransport:
    """Canned :class:`~ghagen.pin.github.HttpClient` keyed by URL substring.

    Each entry maps a URL *substring* to either a :class:`Response`, a list of
    responses (consumed in order, for pagination), or an exception to raise.
    Unmatched URLs return a 404.  Requested tokens are recorded.
    """

    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses
        self.calls: list[str] = []
        self.tokens: list[str | None] = []

    def get(self, url: str, *, token: str | None = None) -> Response:
        self.calls.append(url)
        self.tokens.append(token)
        for pattern, value in self._responses.items():
            if pattern in url:
                if isinstance(value, list):
                    return value.pop(0)
                if isinstance(value, BaseException):
                    raise value
                assert isinstance(value, Response)
                return value
        return Response(status=404, body=b"{}", reason="Not Found")


class TestResolveRef:
    def test_lightweight_tag(self):
        transport = FakeTransport(
            {"tags/v4": _json_response({"object": {"sha": SHA, "type": "commit"}})}
        )
        client = GitHubClient(transport)
        assert client.resolve_ref("actions", "checkout", "v4") == SHA
        assert transport.calls[0] == (
            "https://api.github.com/repos/actions/checkout/git/ref/tags/v4"
        )

    def test_falls_back_to_heads(self):
        transport = FakeTransport(
            {"heads/main": _json_response({"object": {"sha": SHA, "type": "commit"}})}
        )
        client = GitHubClient(transport)
        assert client.resolve_ref("actions", "checkout", "main") == SHA
        # tags/ tried first (404), then heads/.
        assert "/tags/main" in transport.calls[0]
        assert "/heads/main" in transport.calls[1]

    def test_annotated_tag_dereference(self):
        transport = FakeTransport(
            {
                "git/ref/tags/v4": _json_response(
                    {"object": {"sha": TAG_SHA, "type": "tag"}}
                ),
                f"git/tags/{TAG_SHA}": _json_response(
                    {"object": {"sha": SHA, "type": "commit"}}
                ),
            }
        )
        client = GitHubClient(transport)
        assert client.resolve_ref("actions", "checkout", "v4") == SHA

    def test_annotated_tag_not_a_commit_raises(self):
        transport = FakeTransport(
            {
                "git/ref/tags/v4": _json_response(
                    {"object": {"sha": TAG_SHA, "type": "tag"}}
                ),
                f"git/tags/{TAG_SHA}": _json_response(
                    {"object": {"sha": SHA, "type": "tree"}}
                ),
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
            {"tags/v4": _json_response({"object": {"sha": SHA, "type": "commit"}})}
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
        transport = FakeTransport({"tags/v4": _json_response({}, status=500)})
        client = GitHubClient(transport)
        with pytest.raises(ResolveError, match="500"):
            client.resolve_ref("actions", "checkout", "v4")


class TestListTags:
    def _refs(self, *names: str) -> list[dict]:
        return [{"ref": f"refs/tags/{name}"} for name in names]

    def test_basic_listing(self):
        transport = FakeTransport(
            {"git/refs/tags": _json_response(self._refs("v1", "v2", "v3.0.0"))}
        )
        client = GitHubClient(transport)
        assert client.list_tags("actions", "checkout") == ["v1", "v2", "v3.0.0"]

    def test_pagination_via_link_header(self):
        next_url = "https://api.github.com/repos/o/r/git/refs/tags?page=2"
        transport = FakeTransport(
            {
                "git/refs/tags?page=2": _json_response(self._refs("v3")),
                # First page (no ?page=2): served before the more specific match
                # only if it precedes; use a distinct pattern.
                "git/refs/tags": [
                    _json_response(
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
                "git/refs/tags": _json_response(
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
        transport = FakeTransport({"git/refs/tags": _json_response([])})
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


class TestResponse:
    def test_header_is_case_insensitive(self):
        resp = Response(status=200, body=b"{}", headers={"Link": '<u>; rel="next"'})
        assert resp.header("link") == '<u>; rel="next"'
        assert resp.header("LINK") == '<u>; rel="next"'
        assert resp.header("missing") is None

    def test_json_parses_body(self):
        resp = Response(status=200, body=b'{"a": 1}')
        assert resp.json() == {"a": 1}
