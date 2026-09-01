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

import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

_API_BASE = "https://api.github.com"

#: Wall-clock ceiling on a single :class:`HttpClient` request, body read
#: included.  Part of the transport contract rather than an adapter's private
#: business — a third-party adapter is expected to honour it, so it is public
#: and mirrors the TypeScript port's ``API_TIMEOUT_MS`` (``pin/github.ts``).
API_TIMEOUT_SECONDS = 30.0


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
    """Transport seam: a single authenticated GET returning a :class:`Response`.

    The contract every adapter — production or canned — must satisfy, stated
    here once rather than re-decided per adapter.  It is executable: the
    conformance table in ``tests/test_pin/transport_contract.py`` runs it
    against each of them, and its TypeScript peer runs the identical table.

    **Deadline — wall clock, not per operation, the whole call.**  A ``get``
    completes, or fails, within :data:`API_TIMEOUT_SECONDS` measured on the
    wall clock from the moment it is called — connecting, reading the
    response **head**, and reading the body, all under the one budget.  The
    distinction is the whole point: a per-socket-operation timeout is reset by
    every byte that arrives, so a peer trickling one byte per interval holds
    the call open indefinitely while never exceeding it.  Rows 13 and 14 of
    the conformance table (``dribble-body``, ``dribble-head``) are that peer,
    at each phase, and both are what an adapter must survive.  ``FetchTransport``
    gets this from ``AbortSignal.timeout``, which spans the whole call by
    construction; ``UrllibTransport`` gets it by re-clamping its socket's
    timeout to the wall-clock budget remaining before every read — head bytes
    included — rather than delegating to ``urlopen``'s fixed per-operation
    one.  See ``UrllibTransport._deadline_socket_class``.

    Production adapters take the deadline as one defaulted constructor argument
    so the promise is testable rather than merely stated, and the default
    itself is pinned by a test (``TestDefaultDeadline`` and its TypeScript
    peer) because the table always supplies an explicit one.

    **Error taxonomy — total.**  ``get`` either returns a :class:`Response` or
    raises :class:`TransportError`, and nothing else:

    - it returns a :class:`Response` for **any** HTTP response it obtains,
      including 4xx, 5xx and a body that is not JSON.  The transport never
      parses and never judges a status; :class:`GitHubClient` owns that.
    - it raises :class:`TransportError` for **every** failure to obtain one —
      refusal, DNS, reset, mid-body abort, truncated body, deadline.
    - it never lets the underlying library's exception type escape.

    The totality is load-bearing: the pin engine recovers per ref on
    :class:`ResolveError` (``pin/engine.py``), so an exception outside the
    taxonomy turns one unresolvable ref into an aborted run that writes
    nothing.

    **The body is read by the transport**, inside its own deadline and its own
    failure mapping, so a caller may assume the network is done with once
    ``get`` has returned.
    """

    def get(self, url: str, *, token: str | None = None) -> Response:
        """GET ``url``, returning the response or raising :class:`TransportError`."""
        ...


def _clamp_or_raise(sock: Any, deadline: float) -> None:
    """Set *sock*'s timeout to what remains of *deadline*, or raise if none does.

    Called immediately before every ``recv``/``recv_into`` by the
    deadline-enforcing socket class below.  A fixed per-operation timeout is
    renewed by every byte that arrives, which is precisely how a trickling
    peer — header or body — holds a call open forever without ever tripping
    it; reclamping to the wall-clock budget that is *actually left*, on every
    single read, is what turns the ceiling into one the peer cannot outlast.
    """
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("wall-clock deadline exceeded while reading the response")
    sock.settimeout(remaining)


def _deadline_socket_class(base: type, deadline: float) -> type:
    """Build a subclass of socket class *base* that reclamps to *deadline*.

    ``recv`` and ``recv_into`` are the two read primitives both plain
    ``socket.socket`` and ``ssl.SSLSocket`` expose, and the two that
    :mod:`http.client`'s buffered reader funnels every read through — head
    and body alike, TLS or not.  Overriding them here, rather than the
    higher-level ``http.client``/``ssl`` objects built on top, is what makes
    the clamp uniform across both.

    ``__slots__ = ()`` keeps the instance layout identical to *base*, which
    ``sock.__class__ = ...`` reassignment (see :func:`_deadline_connection_class`)
    requires to succeed on a live, already-connected socket: CPython refuses
    the assignment with a layout-mismatch ``TypeError`` otherwise — verified
    empirically against both a plain socket and an ``ssl.SSLSocket``.
    """

    class _DeadlineSocket(base):  # type: ignore[misc,valid-type]
        __slots__ = ()

        def recv(self, *args: Any, **kwargs: Any) -> Any:
            _clamp_or_raise(self, deadline)
            return super().recv(*args, **kwargs)

        def recv_into(self, *args: Any, **kwargs: Any) -> Any:
            _clamp_or_raise(self, deadline)
            return super().recv_into(*args, **kwargs)

    return _DeadlineSocket


def _deadline_connection_class(base: type, deadline: float) -> type:
    """Build a subclass of ``http.client`` connection class *base* that puts
    its socket under *deadline* the moment the socket exists.

    ``connect()`` is where ``HTTPConnection``/``HTTPSConnection`` create the
    raw socket and, for the latter, wrap it in TLS — overriding it here, and
    reassigning ``self.sock.__class__`` right after the base implementation
    returns, is the one hook that sees the finished socket regardless of
    which of the two produced it.  Nothing about connecting, the TLS
    handshake, or certificate verification is touched: ``super().connect()``
    runs unmodified, so it is exactly stdlib's own behaviour up to the point
    the socket is handed back.
    """

    class _DeadlineConnection(base):  # type: ignore[misc,valid-type]
        def connect(self) -> None:
            super().connect()
            sock = self.sock
            if sock is not None:
                sock.__class__ = _deadline_socket_class(type(sock), deadline)

    return _DeadlineConnection


class _DeadlineHTTPHandler(urllib.request.HTTPHandler):
    """``HTTPHandler`` whose connections enforce *deadline* on every read."""

    def __init__(self, deadline: float) -> None:
        super().__init__()
        self._deadline = deadline

    def http_open(self, req: urllib.request.Request) -> Any:
        return self.do_open(
            _deadline_connection_class(http.client.HTTPConnection, self._deadline),
            req,
        )


class _DeadlineHTTPSHandler(urllib.request.HTTPSHandler):
    """``HTTPSHandler`` whose connections enforce *deadline* on every read.

    No ``context`` is passed to the connection class, so
    ``http.client.HTTPSConnection.__init__`` resolves it itself — to the
    identical verified default (``http.client._create_https_context``) that
    both ``urlopen``'s default opener and the base ``HTTPSHandler`` resolve
    it to.  TLS verification is inherited from stdlib, not reimplemented.
    """

    def __init__(self, deadline: float) -> None:
        super().__init__()
        self._deadline = deadline

    def https_open(self, req: urllib.request.Request) -> Any:
        return self.do_open(
            _deadline_connection_class(http.client.HTTPSConnection, self._deadline),
            req,
        )


class UrllibTransport:
    """Default :class:`HttpClient` backed by stdlib :mod:`urllib.request`.

    Builds a fresh :class:`urllib.request.OpenerDirector` per call via
    :func:`urllib.request.build_opener`, exactly as ``urlopen`` would, but
    with two handlers substituted: :class:`_DeadlineHTTPHandler` and
    :class:`_DeadlineHTTPSHandler` in place of the stock ``HTTPHandler`` /
    ``HTTPSHandler``.  ``build_opener`` skips a default handler class whenever
    a passed-in instance is one of it (see its docstring) — since our two
    *are* ``HTTPHandler`` and ``HTTPSHandler`` instances (they subclass them),
    every other default — ``ProxyHandler`` (``HTTP_PROXY``/``HTTPS_PROXY``/
    ``NO_PROXY``), ``HTTPRedirectHandler`` (301/302/303/307/308, reusing this
    same opener across hops), ``HTTPErrorProcessor``, ``HTTPDefaultErrorHandler``
    — is still installed, unmodified.  Nothing about proxying, redirects, or
    header handling changes from what ``urlopen`` provided; only how deep
    into the connection the deadline reaches does.
    """

    #: Bytes requested per underlying read while draining a body.
    _CHUNK = 65536

    def __init__(self, timeout: float = API_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout

    def get(self, url: str, *, token: str | None = None) -> Response:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ghagen-pin",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url, headers=headers)  # noqa: S310
        deadline = time.monotonic() + self._timeout
        opener = urllib.request.build_opener(
            _DeadlineHTTPHandler(deadline), _DeadlineHTTPSHandler(deadline)
        )
        # Only the I/O sits under the handlers, and the Response is built after
        # all of them: a defect in this module's own construction must surface
        # as itself, not as a network failure.
        try:
            with opener.open(req, timeout=self._timeout) as resp:  # noqa: S310
                status = resp.status
                reason, response_headers = resp.reason or "", dict(resp.headers.items())
                body = self._read_within(resp)
        except urllib.error.HTTPError as exc:
            # An HTTPError *is* a response — but reading it is still I/O and can
            # itself truncate or stall, so it gets the same total mapping and
            # the same deadline (the same socket, in fact: HTTPError wraps the
            # same connection this opener produced).  HTTPError subclasses
            # URLError subclasses OSError, so this branch must precede the
            # total one below.
            try:
                status = exc.code
                reason, response_headers = exc.reason or "", dict(exc.headers.items())
                body = self._read_within(exc)
            except Exception as read_exc:
                raise TransportError(str(read_exc)) from read_exc
        except Exception as exc:
            # Total, per the interface contract.  An enumeration is what let
            # RemoteDisconnected and IncompleteRead escape; the next leak would
            # be a type nobody thought of either.
            raise TransportError(str(exc)) from exc
        return Response(
            status=status, body=body, reason=reason, headers=response_headers
        )

    def _read_within(self, resp: Any) -> bytes:
        """Drain *resp*'s body under the same per-read deadline as the head.

        The deadline is no longer enforced here: it is enforced once, at the
        socket, by the connection this ``resp`` was read through (see
        :func:`_deadline_socket_class`) — the same clamp that already bounded
        the status line and headers this ``resp`` was constructed from. A
        ``TimeoutError`` raised there during a body read propagates up through
        ``read1`` unchanged and is mapped by :meth:`get`'s own total handler.

        ``read1`` rather than ``read``: ``read`` loops internally until it has
        the full ``Content-Length``, so control would not come back until a
        trickling peer finished (or the socket-level clamp fired mid-loop
        anyway — but ``read1`` is what makes each step observable, not just
        eventually bounded).

        Truncation is re-detected explicitly.  ``read`` raised
        :class:`http.client.IncompleteRead` when a peer delivered fewer bytes
        than ``Content-Length`` promised; ``read1`` reports the same EOF as an
        ordinary end of body, so row 12 (``truncated-body``) would pass a short
        body off as a complete one without this check.
        """
        chunks: list[bytes] = []
        while True:
            chunk = resp.read1(self._CHUNK)
            if not chunk:
                body = b"".join(chunks)
                _reject_short_body(resp, body)
                return body
            chunks.append(chunk)


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
            ResolveError: If the ref cannot be resolved, or the API answers
                200 with a body that is not the documented shape.
        """
        for url in _ref_urls(owner, repo, ref):
            data = self._get_json(url)
            if data is None:
                continue  # 404 for this prefix — try the next.

            obj = _ref_object(data, url)
            sha = _require_sha(obj, url)
            if _is_annotated_tag(obj):
                sha = self.dereference_tag(owner, repo, sha)
            return sha

        raise ResolveError(
            f"Could not resolve ref '{ref}' for {owner}/{repo}. "
            "Tried tags/ and heads/ — neither exists."
        )

    def dereference_tag(self, owner: str, repo: str, tag_sha: str) -> str:
        """Dereference an annotated tag object to its underlying commit SHA.

        Raises:
            ResolveError: If the tag does not point to a commit — which
                includes a 200 whose body is not the documented shape, since
                such a body evidences no commit either.
        """
        url = f"{_API_BASE}/repos/{owner}/{repo}/git/tags/{tag_sha}"
        data = self._get_json(url)
        obj = data.get("object") if isinstance(data, dict) else None
        if not isinstance(obj, dict):
            obj = {}
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

        "No tags" is the 404 alone.  A 200 whose body is not an array of ref
        objects raises rather than degrading to ``[]``: an empty list here is
        indistinguishable from a genuinely tagless repo, and it would suppress
        every available update for that repo without a word.

        Raises:
            ResolveError: On non-404 API errors (e.g. rate limiting), or a 200
                whose body is not the documented shape.
        """
        url: str | None = f"{_API_BASE}/repos/{owner}/{repo}/git/refs/tags"
        tags: list[str] = []
        while url is not None:
            page = self._get_page(url)
            if page is None:
                return []  # 404 — no tags.
            data, next_url = page
            tags.extend(_ref_names(data, url))
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

    def _parse_json(self, resp: Response, url: str) -> Any:
        """Parse a response body, mapping malformed JSON onto ``ResolveError``.

        The module's documented error contract is :class:`ResolveError`; a
        malformed 200 must not escape as a raw ``JSONDecodeError``.
        """
        try:
            return resp.json()
        except json.JSONDecodeError as exc:
            raise ResolveError(
                f"Failed to parse JSON response from {url}: {exc}"
            ) from exc

    def _get_json(self, url: str) -> Any | None:
        """Fetch and parse JSON, or ``None`` on 404."""
        resp = self._fetch(url)
        if resp.status == 404:
            return None
        return self._parse_json(resp, url)

    def _get_page(self, url: str) -> tuple[list[dict], str | None] | None:
        """Fetch one page: ``(data, next_url)``, or ``None`` on 404."""
        resp = self._fetch(url)
        if resp.status == 404:
            return None
        data = self._parse_json(resp, url)
        return data, _parse_next_link(resp.header("Link"))


def _reject_short_body(resp: Any, body: bytes) -> None:
    """Raise if *resp* stopped short of the ``Content-Length`` it promised.

    ``http.client.HTTPResponse.length`` counts the bytes still owed; it is
    ``None`` for a chunked or unbounded body, where nothing was promised and
    so nothing is owed.
    """
    owed = getattr(resp, "length", None)
    if isinstance(owed, int) and owed > 0:
        raise http.client.IncompleteRead(body, owed)


# -- response-shape validation ---------------------------------------------
#
# A 200 that parses as JSON has still told us nothing until its *shape* is
# checked.  Skipping the check does not avoid the failure, it relocates it: to
# a bare ``KeyError`` here (outside the documented ``ResolveError`` contract,
# so ``pin/engine.py``'s per-ref recovery does not catch it and one bad
# response aborts a whole run), or to a ``None`` that reaches the lockfile as
# an unquoted ``sha: null`` this same package then refuses to read back.
# Both ports raise from here, with the same message shape.


def _json_type(value: Any) -> str:
    """Name *value*'s JSON type the way both ports name it in messages."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _shape_error(url: str, detail: str) -> ResolveError:
    """The one message shape for a well-formed-JSON, wrong-shape 200."""
    return ResolveError(f"Unexpected response shape from {url}: {detail}")


def _ref_object(data: Any, url: str) -> dict:
    """The ``object`` member of a ref response, or :class:`ResolveError`."""
    if not isinstance(data, dict):
        raise _shape_error(url, f"expected an object, got {_json_type(data)}")
    obj = data.get("object")
    if not isinstance(obj, dict):
        raise _shape_error(url, f"'object' must be an object, got {_json_type(obj)}")
    return obj


def _require_sha(obj: dict, url: str) -> str:
    """``object.sha`` as a string, or :class:`ResolveError`."""
    sha = obj.get("sha")
    if not isinstance(sha, str):
        raise _shape_error(url, f"'object.sha' must be a string, got {_json_type(sha)}")
    return sha


def _ref_names(data: Any, url: str) -> list[str]:
    """Tag names from one page of ``git/refs/tags``, ``refs/tags/`` stripped."""
    if not isinstance(data, list):
        raise _shape_error(url, f"expected an array, got {_json_type(data)}")
    names: list[str] = []
    for index, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise _shape_error(
                url, f"[{index}] must be an object, got {_json_type(entry)}"
            )
        full_ref = entry.get("ref")
        if not isinstance(full_ref, str):
            raise _shape_error(
                url, f"[{index}].ref must be a string, got {_json_type(full_ref)}"
            )
        if full_ref.startswith("refs/tags/"):
            names.append(full_ref[len("refs/tags/") :])
    return names


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
