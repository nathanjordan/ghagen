"""GitHub REST API client for resolving Action refs to commit SHAs.

The HTTP transport is injected (:class:`HttpClient`) so the GitHub logic —
URL building, error mapping, pagination, annotated-tag dereferencing — is
testable without network access.  :class:`UrllibTransport` is the default
adapter and keeps ``pin`` dependency-free (stdlib :mod:`urllib.request`);
tests supply a fake transport with canned responses.

Pure decisions (Link-header parsing, the tag-vs-head fallback order, and the
annotated-tag "is this a commit" check) stay free module-level functions so
they can be unit-tested directly.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

_API_BASE = "https://api.github.com"


class TransportError(Exception):
    """Raised by a transport when a request fails at the network level.

    Signals that no HTTP response was received (connection refused, DNS
    failure, timeout).  HTTP responses with error status codes are *not*
    transport errors — they are returned as :class:`Response` objects for
    :class:`GitHubClient` to map.
    """


class ResolveError(Exception):
    """Raised when a ref cannot be resolved to a commit SHA."""


@dataclass(frozen=True)
class Response:
    """An HTTP response returned by a transport.

    Carries the status code, the raw body (parsed on demand via
    :meth:`json`), and case-insensitive header access (:meth:`header`),
    which is all :class:`GitHubClient` needs — including the ``Link`` header
    for pagination.
    """

    status: int
    body: bytes
    reason: str = ""
    headers: Mapping[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        """Parse and return the JSON body."""
        return json.loads(self.body)

    def header(self, name: str) -> str | None:
        """Return a header value by name (case-insensitive), or ``None``."""
        lowered = name.lower()
        for key, value in self.headers.items():
            if key.lower() == lowered:
                return value
        return None


class HttpClient(Protocol):
    """Transport seam: a single authenticated GET returning a :class:`Response`."""

    def get(self, url: str, *, token: str | None = None) -> Response:
        """GET ``url`` and return the response (raise :class:`TransportError` on
        network failure)."""
        ...


class UrllibTransport:
    """Default :class:`HttpClient` backed by stdlib :mod:`urllib.request`.

    Holds the raw ``urlopen`` call and header building.  HTTP error responses
    (4xx/5xx) are captured as :class:`Response` objects rather than raised, so
    the client owns all status-based error mapping; genuine network failures
    raise :class:`TransportError`.
    """

    def get(self, url: str, *, token: str | None = None) -> Response:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ghagen-pin",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url, headers=headers)  # noqa: S310
        try:
            with urllib.request.urlopen(req) as resp:  # noqa: S310
                return Response(
                    status=resp.status,
                    body=resp.read(),
                    reason=resp.reason or "",
                    headers=dict(resp.headers.items()),
                )
        except urllib.error.HTTPError as exc:
            # HTTPError is itself a response — capture its status/headers/body.
            return Response(
                status=exc.code,
                body=exc.read(),
                reason=exc.reason or "",
                headers=dict(exc.headers.items()),
            )
        except urllib.error.URLError as exc:
            raise TransportError(str(exc)) from exc


class GitHubClient:
    """Resolve GitHub Action refs to commit SHAs via the REST API.

    URL building, error mapping, pagination, and annotated-tag dereferencing
    live here.  The HTTP transport and the token are injected once at
    construction (the token moved off the per-call signature).
    """

    def __init__(
        self,
        transport: HttpClient | None = None,
        token: str | None = None,
    ) -> None:
        self._transport: HttpClient = (
            transport if transport is not None else UrllibTransport()
        )
        self._token = token

    def resolve_ref(self, owner: str, repo: str, ref: str) -> str:
        """Resolve a git ref to a commit SHA.

        Tries ``tags/{ref}`` first, then ``heads/{ref}``.  Annotated tags are
        dereferenced to their underlying commit.

        Raises:
            ResolveError: If the ref cannot be resolved.
        """
        for url in _ref_urls(owner, repo, ref):
            data = self._get_json(url)
            if data is None:
                continue  # 404 for this prefix — try the next.

            obj = data["object"]
            sha = obj["sha"]
            if _is_annotated_tag(obj):
                sha = self.dereference_tag(owner, repo, sha)
            return sha

        raise ResolveError(
            f"Could not resolve ref '{ref}' for {owner}/{repo}. "
            "Tried tags/ and heads/ — neither exists."
        )

    def dereference_tag(self, owner: str, repo: str, tag_sha: str) -> str:
        """Dereference an annotated tag object to its underlying commit SHA."""
        url = f"{_API_BASE}/repos/{owner}/{repo}/git/tags/{tag_sha}"
        data = self._get_json(url)
        obj = data.get("object", {}) if data is not None else {}
        sha = _commit_sha(obj)
        if sha is not None:
            return sha
        raise ResolveError(
            f"Tag {tag_sha} in {owner}/{repo} does not point to a commit "
            f"(type={obj.get('type')!r})"
        )

    def list_tags(self, owner: str, repo: str) -> list[str]:
        """List all tags for a repository (paginated via the ``Link`` header).

        Returns tag names with the ``refs/tags/`` prefix stripped, or an empty
        list when the repo has no tags (the API returns 404).

        Raises:
            ResolveError: On non-404 API errors (e.g. rate limiting).
        """
        url: str | None = f"{_API_BASE}/repos/{owner}/{repo}/git/refs/tags"
        tags: list[str] = []
        while url is not None:
            page = self._get_page(url)
            if page is None:
                return []  # 404 — no tags.
            data, next_url = page
            for ref in data:
                full_ref = ref.get("ref", "")
                if full_ref.startswith("refs/tags/"):
                    tags.append(full_ref[len("refs/tags/") :])
            url = next_url
        return tags

    # -- internal request helpers ------------------------------------------

    def _fetch(self, url: str) -> Response:
        """GET ``url`` and map status codes to errors.

        Returns the response for 2xx and 404 (the caller distinguishes 404);
        warns on 403 and raises :class:`ResolveError` for any other non-2xx.
        """
        try:
            resp = self._transport.get(url, token=self._token)
        except TransportError as exc:
            raise ResolveError(f"Network error reaching GitHub API: {exc}") from exc

        if resp.status == 404:
            return resp
        if resp.status == 403:
            _warn_rate_limit(resp)
        if not 200 <= resp.status < 300:
            raise ResolveError(
                f"GitHub API error {resp.status} for {url}: {resp.reason}"
            )
        return resp

    def _get_json(self, url: str) -> Any | None:
        """Fetch and parse JSON, or ``None`` on 404."""
        resp = self._fetch(url)
        if resp.status == 404:
            return None
        return resp.json()

    def _get_page(self, url: str) -> tuple[list[dict], str | None] | None:
        """Fetch one page: ``(data, next_url)``, or ``None`` on 404."""
        resp = self._fetch(url)
        if resp.status == 404:
            return None
        return resp.json(), _parse_next_link(resp.header("Link"))


# -- pure helpers (unit-testable without a transport) ----------------------


def _ref_urls(owner: str, repo: str, ref: str) -> list[str]:
    """Return the candidate ref-lookup URLs in tag-then-head fallback order."""
    return [
        f"{_API_BASE}/repos/{owner}/{repo}/git/ref/{prefix}/{ref}"
        for prefix in ("tags", "heads")
    ]


def _is_annotated_tag(obj: dict) -> bool:
    """Return ``True`` if a ref object points to an annotated tag (needs deref)."""
    return obj.get("type") == "tag"


def _commit_sha(obj: dict) -> str | None:
    """Return the SHA if ``obj`` is a commit object, else ``None``."""
    if obj.get("type") == "commit":
        sha = obj.get("sha")
        if isinstance(sha, str):
            return sha
    return None


def _parse_next_link(link_header: str | None) -> str | None:
    """Extract the ``next`` URL from a GitHub ``Link`` header.

    Example header value::

        <https://api.github.com/repos/o/r/git/refs/tags?page=2>; rel="next",
        <https://api.github.com/repos/o/r/git/refs/tags?page=5>; rel="last"

    Returns ``None`` when there is no ``next`` relation.
    """
    if not link_header:
        return None
    for part in link_header.split(","):
        match = re.search(r'<([^>]+)>;\s*rel="next"', part)
        if match:
            return match.group(1)
    return None


def _warn_rate_limit(resp: Response) -> None:
    """Print a warning about rate limiting to stderr."""
    remaining = resp.header("X-RateLimit-Remaining") or "?"
    print(
        f"warning: GitHub API rate limit hit (remaining={remaining}). "
        "Set $GITHUB_TOKEN or use --token for higher limits.",
        file=sys.stderr,
    )
