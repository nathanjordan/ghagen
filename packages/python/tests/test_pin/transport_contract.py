"""The one canned :class:`HttpClient` double, plus the transport conformance table.

Every adapter behind :class:`~ghagen.pin.github.HttpClient` — the production
:class:`~ghagen.pin.github.UrllibTransport` and the canned
:class:`FakeTransport` alike — must satisfy the same table, so a double cannot
drift into a shape the real adapter is unable to produce.

Two builders construct canned responses: :func:`canned` encodes a JSON value,
:func:`canned_raw` takes a body verbatim (a malformed 200, a truncated payload).

Rows 8-12 put the adapter in front of a **raw socket**, not a request-handling
server: ``http.server`` always frames a well-formed response, so it cannot
express "peer closes without answering" (row 9), "declared
``Content-Length: 100``, delivered 5 bytes" (row 11), or "trickle a byte at a
time forever" (row 12).  Each scenario gets its own listening socket and its
own daemon thread — a scenario whose handler deliberately never returns (row
10) would otherwise block a shared accept loop and deadlock the next one.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import pytest

from ghagen.pin.github import HttpClient, Response, TransportError

# The deadline the adapter under test is built with for the response rows.
# Generous: these rows are about what comes back, not about timing.
RESPONSE_DEADLINE_SECONDS = 5.0

# Row 10's deadline, and the sole caller of the adapters' deadline argument.
FAILURE_DEADLINE_SECONDS = 0.25

# Upper bound on a failure row's wall clock, at 10x the deadline.  No lower
# bound is asserted: a "did it really wait?" check flakes on a fast machine and
# adds nothing the ceiling and the raised type do not already establish.
FAILURE_CEILING_SECONDS = 2.5


# -- the one canned double -------------------------------------------------


def canned(
    obj: object,
    *,
    status: int = 200,
    reason: str = "",
    headers: Mapping[str, str] | None = None,
) -> Response:
    """Build a canned :class:`Response` whose body is *obj* encoded as JSON."""
    return canned_raw(
        json.dumps(obj).encode(), status=status, reason=reason, headers=headers
    )


def canned_raw(
    body: bytes | str,
    *,
    status: int = 200,
    reason: str = "",
    headers: Mapping[str, str] | None = None,
) -> Response:
    """Build a canned :class:`Response` around a verbatim body."""
    return Response(
        status=status,
        body=body.encode() if isinstance(body, str) else body,
        reason=reason,
        headers=dict(headers or {}),
    )


class FakeTransport:
    """Canned :class:`~ghagen.pin.github.HttpClient` keyed by URL substring.

    Each entry maps a URL *substring* to a :class:`Response`, a list of
    responses (consumed in order, for pagination), or an exception to raise.
    Unmatched URLs return a 404.  Requested tokens are recorded on
    :attr:`tokens`, requested URLs on :attr:`calls`.
    """

    def __init__(self, responses: Mapping[str, object] | None = None) -> None:
        self._responses = dict(responses or {})
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


# -- the conformance table -------------------------------------------------


@dataclass(frozen=True)
class ResponseCase:
    """A row that must produce a returned :class:`Response` (rows 1-7).

    One description serves both kinds of adapter: :meth:`wire` is what a raw
    origin writes to the socket, :meth:`response` is the equivalent canned
    :class:`Response`.  That is what stops the double from drifting.
    """

    name: str
    status: int
    reason: str
    body: bytes
    headers: tuple[tuple[str, str], ...] = ()
    token: str | None = None

    def wire(self) -> bytes:
        """The literal bytes a raw origin writes for this row."""
        head = f"HTTP/1.1 {self.status} {self.reason}\r\n"
        for name, value in self.headers:
            head += f"{name}: {value}\r\n"
        head += f"Content-Length: {len(self.body)}\r\n\r\n"
        return head.encode() + self.body

    def response(self) -> Response:
        """The equivalent canned :class:`Response`."""
        return canned_raw(
            self.body,
            status=self.status,
            reason=self.reason,
            headers=dict(self.headers),
        )


_NEXT_LINK = '<https://api.github.com/repos/o/r/git/refs/tags?page=2>; rel="next"'

RESPONSE_CASES: tuple[ResponseCase, ...] = (
    ResponseCase(
        name="json-200",
        status=200,
        reason="OK",
        body=json.dumps({"object": {"type": "commit", "sha": "a" * 40}}).encode(),
    ),
    ResponseCase(
        name="html-200",
        status=200,
        reason="OK",
        body=b"<html>not json</html>",
    ),
    ResponseCase(
        name="not-found-404",
        status=404,
        reason="Not Found",
        body=b'{"message": "Not Found"}',
    ),
    ResponseCase(
        name="server-error-500",
        status=500,
        reason="Internal Server Error",
        body=b'{"message": "boom"}',
    ),
    ResponseCase(
        name="link-header",
        status=200,
        reason="OK",
        body=b"[]",
        headers=(("Link", _NEXT_LINK),),
    ),
    ResponseCase(
        name="token-supplied",
        status=200,
        reason="OK",
        body=b"{}",
        token="s3cret",
    ),
    ResponseCase(
        name="no-token",
        status=200,
        reason="OK",
        body=b"{}",
    ),
)
"""Rows 1-7 — every adapter, real or canned, must satisfy these."""

FAILURE_CASES: tuple[str, ...] = (
    "connection-refused",
    "abrupt-close",
    "stall-mid-body",
    "truncated-body",
    "dribble-body",
)
"""Rows 8-12 — a canned double satisfies these by construction, so it skips them."""

ALL_CASES: tuple[ResponseCase | str, ...] = (*RESPONSE_CASES, *FAILURE_CASES)


def case_id(case: ResponseCase | str) -> str:
    """Test id for a table row."""
    return case.name if isinstance(case, ResponseCase) else case


# -- the loopback origin ---------------------------------------------------


def _read_request(conn: socket.socket) -> bytes:
    """Read one request head off *conn* (through the blank line)."""
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


# A head that promises 100 bytes and is followed by 5, used by rows 10 and 11.
_UNDERDELIVERED_HEAD = b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n"
_UNDERDELIVERED_BODY = b"12345"

# Row 12's shape: one body byte every _DRIBBLE_INTERVAL for _DRIBBLE_SECONDS.
# The interval must exceed FAILURE_DEADLINE_SECONDS/2 so that a *per-socket*
# timeout of one deadline never fires — which is exactly what makes the row
# distinguish a wall-clock deadline from a per-operation one.
_DRIBBLE_INTERVAL = 0.2
_DRIBBLE_SECONDS = 10.0
_DRIBBLE_LENGTH = int(_DRIBBLE_SECONDS / _DRIBBLE_INTERVAL)


class LoopbackOrigin:
    """A raw-socket origin bound to ``127.0.0.1:0``.

    Owns one listening socket and one daemon thread, closed by the context
    manager.  *handler* receives the accepted connection and a
    :class:`threading.Event` that is set during teardown, so a deliberately
    stalling handler can be released rather than joined forever.
    """

    def __init__(
        self, handler: Callable[[socket.socket, threading.Event], None]
    ) -> None:
        self._handler = handler
        self._stop = threading.Event()
        self.requests: list[bytes] = []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(4)
        self._sock.settimeout(0.1)
        self._thread = threading.Thread(target=self._serve, daemon=True)

    @property
    def url(self) -> str:
        """A URL this origin will answer."""
        host, port = self._sock.getsockname()
        return f"http://{host}:{port}/contract"

    def observed_auth(self) -> str | None:
        """The ``Authorization`` header value the origin saw, if any."""
        return _auth_header(self.requests[-1] if self.requests else b"")

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except (TimeoutError, OSError):
                continue
            with conn:
                try:
                    self.requests.append(_read_request(conn))
                    self._handler(conn, self._stop)
                except OSError:  # the client hung up first; nothing to report
                    pass

    def __enter__(self) -> LoopbackOrigin:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join(timeout=FAILURE_CEILING_SECONDS)
        self._sock.close()


def _auth_header(request: bytes) -> str | None:
    """Extract the ``Authorization`` value from a raw request head."""
    for line in request.split(b"\r\n"):
        name, _, value = line.partition(b":")
        if name.strip().lower() == b"authorization":
            return value.strip().decode()
    return None


def _responder(wire: bytes) -> Callable[[socket.socket, threading.Event], None]:
    def handler(conn: socket.socket, _stop: threading.Event) -> None:
        conn.sendall(wire)

    return handler


def _abrupt_close(conn: socket.socket, _stop: threading.Event) -> None:
    """Row 9 — accept the request, then close without writing a response."""
    return None


def _stall_mid_body(conn: socket.socket, stop: threading.Event) -> None:
    """Row 10 — send a head and part of the body, then hold the connection."""
    conn.sendall(_UNDERDELIVERED_HEAD + _UNDERDELIVERED_BODY)
    stop.wait()


def _truncated_body(conn: socket.socket, _stop: threading.Event) -> None:
    """Row 11 — declare 100 bytes, deliver 5, close."""
    conn.sendall(_UNDERDELIVERED_HEAD + _UNDERDELIVERED_BODY)


def _dribble_body(conn: socket.socket, stop: threading.Event) -> None:
    """Row 12 — send one body byte every 200ms for 10s.

    The row rows 10 and 11 cannot express.  A *stalled* peer is caught by a
    per-socket-operation timeout too, because no operation completes; a peer
    that keeps trickling resets that timeout forever, so only an adapter
    honouring a genuine **wall-clock** deadline aborts.  ``AbortSignal.timeout``
    is one; ``urlopen(timeout=)`` alone is not.
    """
    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % _DRIBBLE_LENGTH)
    for _ in range(_DRIBBLE_LENGTH):
        if stop.wait(_DRIBBLE_INTERVAL):
            return
        conn.sendall(b"x")


_FAILURE_HANDLERS: dict[
    str, Callable[[socket.socket, threading.Event], None] | None
] = {
    "connection-refused": None,  # served by a port nobody listens on
    "abrupt-close": _abrupt_close,
    "stall-mid-body": _stall_mid_body,
    "truncated-body": _truncated_body,
    "dribble-body": _dribble_body,
}


@contextmanager
def _closed_port() -> Iterator[str]:
    """Yield a URL on a loopback port that nothing is listening on."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    sock.close()
    yield f"http://{host}:{port}/contract"


# -- adapter factories -----------------------------------------------------


@dataclass(frozen=True)
class Bound:
    """An adapter bound to one scenario: the client, the URL, the origin's view."""

    client: HttpClient
    url: str
    observed_auth: Callable[[], str | None]


MakeAdapter = Callable[[Any, float], Any]
"""``make_adapter(case, deadline)`` -> context manager yielding a :class:`Bound`."""


def loopback_adapter(build: Callable[[float], HttpClient]) -> MakeAdapter:
    """Run a *real* adapter against a raw loopback origin.

    ``build(deadline)`` constructs the adapter under test with that wall-clock
    deadline in seconds — the deadline argument's sole caller.
    """

    @contextmanager
    def make(case: ResponseCase | str, deadline: float) -> Iterator[Bound]:
        if isinstance(case, ResponseCase):
            handler = _responder(case.wire())
        elif _FAILURE_HANDLERS[case] is None:
            with _closed_port() as url:
                yield Bound(build(deadline), url, lambda: None)
            return
        else:
            handler = _FAILURE_HANDLERS[case]  # type: ignore[assignment]
        with LoopbackOrigin(handler) as origin:
            yield Bound(build(deadline), origin.url, origin.observed_auth)

    return make


def canned_adapter() -> MakeAdapter:
    """Run :class:`FakeTransport` against the same table (response rows only)."""

    @contextmanager
    def make(case: ResponseCase | str, _deadline: float) -> Iterator[Bound]:
        assert isinstance(case, ResponseCase), (
            "a canned double satisfies rows 8-11 by construction; it runs rows 1-7"
        )
        transport = FakeTransport({"/contract": case.response()})

        def observed_auth() -> str | None:
            token = transport.tokens[-1] if transport.tokens else None
            return f"Bearer {token}" if token else None

        yield Bound(transport, "https://origin.test/contract", observed_auth)

    return make


# -- the runner ------------------------------------------------------------


def assert_transport_contract(
    make_adapter: MakeAdapter,
    *,
    cases: Sequence[ResponseCase | str] = ALL_CASES,
) -> None:
    """Assert that *make_adapter*'s adapter satisfies the conformance table.

    Defaults to the full table; the test modules pass one row at a time so a
    failure names the row.
    """
    for case in cases:
        if isinstance(case, ResponseCase):
            _assert_response_case(make_adapter, case)
        else:
            _assert_failure_case(make_adapter, case)


def _assert_response_case(make_adapter: MakeAdapter, case: ResponseCase) -> None:
    with make_adapter(case, RESPONSE_DEADLINE_SECONDS) as bound:
        resp = bound.client.get(bound.url, token=case.token)
        observed = bound.observed_auth()

    assert resp.status == case.status
    assert resp.body == case.body
    assert resp.reason == case.reason
    for name, value in case.headers:
        assert resp.header(name.lower()) == value
        assert resp.header(name.upper()) == value
    assert observed == (f"Bearer {case.token}" if case.token else None)


def _assert_failure_case(make_adapter: MakeAdapter, name: str) -> None:
    with make_adapter(name, FAILURE_DEADLINE_SECONDS) as bound:
        started = time.monotonic()
        with pytest.raises(TransportError):
            bound.client.get(bound.url)
        elapsed = time.monotonic() - started

    assert elapsed < FAILURE_CEILING_SECONDS, (
        f"{name}: took {elapsed:.2f}s, deadline was {FAILURE_DEADLINE_SECONDS}s"
    )
