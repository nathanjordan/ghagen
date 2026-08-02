"""Tests for ghagen.pin.github — GitHubClient driven through a FakeTransport.

The GitHub logic (URL building, error mapping, pagination, annotated-tag
dereferencing) is exercised without network access via a canned transport.
The pure helpers are unit-tested directly.
"""

from __future__ import annotations

import urllib.request

import pytest

from ghagen.pin.github import (
    API_TIMEOUT_SECONDS,
    GitHubClient,
    ResolveError,
    Response,
    TransportError,
    UrllibTransport,
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


class TestMalformedShape:
    """A 200 that parses but has the wrong *shape* must also be ResolveError.

    ``TestMalformedJson`` covers a body that is not JSON.  This covers a body
    that is JSON and is not what the GitHub API documents — the case that used
    to leave ``resolve_ref`` raising a bare ``KeyError`` and ``list_tags`` a
    bare ``AttributeError``.  Both are outside the module's documented error
    contract, and the engine recovers per ref on :class:`ResolveError` alone
    (``pin/engine.py``), so either one turned a single unusable response into
    an aborted run that wrote nothing.
    """

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param({"unexpected": "shape"}, id="no-object-key"),
            pytest.param({"object": "not-a-mapping"}, id="object-not-a-mapping"),
            pytest.param({"object": None}, id="object-null"),
            pytest.param({"object": {"type": "commit"}}, id="no-sha-key"),
            pytest.param({"object": {"type": "commit", "sha": None}}, id="sha-null"),
            pytest.param({"object": {"type": "commit", "sha": 12345}}, id="sha-number"),
            pytest.param([], id="body-is-a-list"),
            pytest.param("a string", id="body-is-a-string"),
        ],
    )
    def test_resolve_ref_rejects_malformed_shape(self, body):
        transport = FakeTransport({"git/ref/tags/v4": canned(body)})
        client = GitHubClient(transport)
        with pytest.raises(ResolveError, match="Unexpected response shape"):
            client.resolve_ref("actions", "checkout", "v4")

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param({"unexpected": "shape"}, id="not-a-list"),
            pytest.param(["refs/tags/v1"], id="list-of-strings"),
            pytest.param([{"ref": 12345}], id="ref-not-a-string"),
            pytest.param([None], id="list-of-nulls"),
        ],
    )
    def test_list_tags_rejects_malformed_shape(self, body):
        transport = FakeTransport({"git/refs/tags": canned(body)})
        client = GitHubClient(transport)
        with pytest.raises(ResolveError, match="Unexpected response shape"):
            client.list_tags("actions", "checkout")

    @pytest.mark.parametrize(
        "body,detail",
        [
            (
                {"object": {"type": "commit", "sha": 1}},
                "'object.sha' must be a string, got number",
            ),
            ({"object": None}, "'object' must be an object, got null"),
            ([], "expected an object, got array"),
        ],
    )
    def test_message_shape_matches_the_typescript_port(self, body, detail):
        # The exact text its TypeScript peer asserts, character for character;
        # see `a shape-malformed 200 surfaces as ResolveError` there.
        url = "https://api.github.com/repos/actions/checkout/git/ref/tags/v4"
        transport = FakeTransport({"git/ref/tags/v4": canned(body)})
        with pytest.raises(ResolveError) as excinfo:
            GitHubClient(transport).resolve_ref("actions", "checkout", "v4")
        assert str(excinfo.value) == f"Unexpected response shape from {url}: {detail}"

    def test_dereference_tag_rejects_malformed_shape(self):
        transport = FakeTransport({f"git/tags/{TAG_SHA}": canned({"nope": 1})})
        client = GitHubClient(transport)
        with pytest.raises(ResolveError, match="does not point to a commit"):
            client.dereference_tag("actions", "checkout", TAG_SHA)

    def test_a_repo_with_no_tags_is_still_an_empty_list(self):
        # The 404 path must keep meaning "no tags"; only a *malformed* 200 is
        # the error.  Without this, tightening list_tags could turn every
        # tagless repo into a failed run.
        assert GitHubClient(FakeTransport({})).list_tags("o", "r") == []

    def test_an_empty_page_is_still_an_empty_list(self):
        transport = FakeTransport({"git/refs/tags": canned([])})
        assert GitHubClient(transport).list_tags("o", "r") == []


class _StubHTTPResponse:
    """The smallest thing ``UrllibTransport.get`` will accept from ``urlopen``."""

    status = 200
    reason = "OK"
    headers: dict[str, str] = {}

    def read(self, *args: object) -> bytes:
        return b"{}"

    def read1(self, *args: object) -> bytes:
        return b""

    def __enter__(self) -> _StubHTTPResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class TestDefaultDeadline:
    """The production adapter's *default* deadline, which nothing else observes.

    The conformance table always builds the adapter with an explicit deadline
    (``loopback_adapter``'s ``build``), so deleting the default would leave the
    whole suite green while shipping a transport that can hang forever.  These
    tests observe the value the default-constructed adapter actually hands to
    the underlying I/O call.
    """

    def _captured_timeout(self, monkeypatch, transport: UrllibTransport) -> object:
        captured: dict[str, object] = {}

        def fake_urlopen(req: object, **kwargs: object) -> _StubHTTPResponse:
            captured["timeout"] = kwargs.get("timeout")
            return _StubHTTPResponse()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        transport.get("http://origin.test/contract")
        return captured["timeout"]

    def test_default_constructed_adapter_uses_the_declared_deadline(self, monkeypatch):
        assert (
            self._captured_timeout(monkeypatch, UrllibTransport())
            == API_TIMEOUT_SECONDS
        )

    def test_explicit_deadline_overrides_the_default(self, monkeypatch):
        # Pins API_TIMEOUT_SECONDS as the *default argument* rather than a
        # constant hardcoded into the request.
        assert self._captured_timeout(monkeypatch, UrllibTransport(timeout=1.5)) == 1.5

    def test_declared_deadline_matches_the_typescript_port(self):
        # `API_TIMEOUT_MS = 30_000` in packages/typescript/src/pin/github.ts.
        assert API_TIMEOUT_SECONDS == 30.0


class TestResponse:
    def test_header_is_case_insensitive(self):
        resp = Response(status=200, body=b"{}", headers={"Link": '<u>; rel="next"'})
        assert resp.header("link") == '<u>; rel="next"'
        assert resp.header("LINK") == '<u>; rel="next"'
        assert resp.header("missing") is None

    def test_json_parses_body(self):
        resp = Response(status=200, body=b'{"a": 1}')
        assert resp.json() == {"a": 1}
