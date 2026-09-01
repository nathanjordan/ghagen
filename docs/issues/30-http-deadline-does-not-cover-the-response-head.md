# The HTTP deadline does not cover the response head in Python

**Status:** closed — `UrllibTransport` rewritten on stdlib `http.client` handlers; both ports'
`HttpClient` docstring restored to the whole-call contract

Round 2 made `HttpClient`'s deadline a real wall clock over the whole call in both ports. Python's
was previously a **per-socket-operation** timeout, which is not the same thing: a server dribbling
one byte every 200 ms for 10 s returned after **10.13 s** under a 1.0 s deadline, because no single
`recv` ever exceeded 1.0 s. TypeScript aborted at ~1.0 s. That is fixed — `UrllibTransport` now
reads the body through a deadline-aware `read1()` loop and aborts at 1.00 s, and the shared
`dribble-body` contract row holds both ports to it.

## What is still open

The fix covers the response **body**. It does not cover the response **head**. `urlopen` admits only
a per-operation timeout for connect-and-read-headers, so a server that dribbles _header_ bytes still
overruns — measured at **10.31 s under a 1.0 s deadline**.

Rather than let the interface overstate what it delivers, the `HttpClient` deadline docstring in
**both** ports was downgraded to the honest intersection: wall clock over the whole call including
the body, head excluded. TypeScript in fact exceeds that floor — `AbortSignal.timeout` covers the
head too — so the written contract is currently weaker than one port's behaviour, deliberately.

## Why it was not closed

Closing it means replacing `urlopen` with a hand-rolled `http.client` connection so the head read is
under the same clock as the body. That is a real rewrite of the production adapter, disproportionate
to the round it surfaced in, and it deserves its own red-green proof rather than riding a fix pass.

## What a fix must do

1. Put the head read under the same wall clock as the body in `UrllibTransport`.
2. Add a `dribble-head` row to `transport_contract.py` / `transport-contract.ts`, the peer of the
   `dribble-body` row that already exists.
3. Restore the `HttpClient` docstring in both ports to the stronger contract — whole call, head
   included — once both satisfy it. **The docstring is the deliverable**, not an afterthought: the
   whole class of defect this round chased was interfaces stating invariants their implementations
   did not hold.

## A note on the measurement that found it

The reported symptom was "no test pins the production timeout, delete it and both suites stay
green." That is not quite right and the correction is worth keeping: deleting the timeout **usage**
hangs Python's `stall-mid-body` row forever and fails TypeScript's. The real blind spot was
narrower — removing only the **default value**, so a default-constructed adapter gets no deadline.
Both suites passed that mutation except the newly added tests. `grep -rn API_TIMEOUT packages/`
previously found zero test references.

## Files

- `packages/python/src/ghagen/pin/github.py` — `UrllibTransport`, `API_TIMEOUT_SECONDS`
- `packages/typescript/src/pin/github.ts` — `FetchTransport`, `API_TIMEOUT_MS`
- `packages/python/tests/test_pin/transport_contract.py`,
  `packages/typescript/src/pin/transport-contract.ts` — the shared harness the new row goes in

## Resolution

`urlopen` was replaced with a hand-rolled `urllib.request` opener, per "What a fix must do" above.

1. **The head read is now under the same wall clock as the body.** `UrllibTransport.get` no longer
   calls `urlopen`; it builds a fresh `urllib.request.OpenerDirector` per call via
   `urllib.request.build_opener(_DeadlineHTTPHandler(deadline), _DeadlineHTTPSHandler(deadline))` —
   two new handler classes that install a deadline-aware `http.client` connection. The mechanism:
   `_deadline_connection_class` overrides `connect()` to reassign the just-created socket's `__class__`
   to a dynamically built subclass (`_deadline_socket_class`) whose `recv`/`recv_into` re-clamp
   `settimeout()` to the wall-clock budget remaining, via `_clamp_or_raise`, before every single read —
   status line, headers, and body alike, TLS or not. A trickling peer therefore has its socket timeout
   shortened on every byte it sends, rather than renewed. `__slots__ = ()` on the socket subclass is
   required: CPython refuses a bare `sock.__class__ = ...` reassignment on a live, already-connected
   socket with a layout-mismatch `TypeError` otherwise (verified empirically against both a plain
   `socket.socket` and an `ssl.SSLSocket`). `_read_within` (the body-drain loop) no longer takes a
   `deadline` argument or does its own clamping — enforcement is now uniform at the socket layer, so
   the loop is back to draining via `read1()` plus the existing `_reject_short_body` truncation check.

2. **What `urlopen` provided, and how each was verified preserved:**
   - **TLS verification.** `_DeadlineHTTPSHandler` passes no `context` to `HTTPSConnection`, so
     `http.client.HTTPSConnection.__init__` resolves it itself via `http.client._create_https_context`
     — the identical verified default `urlopen`'s own `HTTPSHandler` resolves to. Verified live, not
     just by reading: a loopback TLS server with a self-signed cert (`CN=127.0.0.1`, matching SAN) was
     hit through the new `UrllibTransport`, and `get()` raised `TransportError` wrapping
     `SSL: CERTIFICATE_VERIFY_FAILED: self-signed certificate` — the same failure `urlopen` would
     produce. A second run confirmed the deadline clamp fires over the TLS path too (a head-dribbling
     TLS peer, deadline 1.0 s, aborted at 1.00 s with `SSLError: The read operation timed out`),
     proving the socket-class swap survives `ssl.SSLSocket` wrapping and not just plain sockets.
   - **Proxy handling.** `urllib.request.build_opener` skips installing its default handler class
     whenever a passed-in instance is one (see its own docstring); `_DeadlineHTTPHandler` and
     `_DeadlineHTTPSHandler` subclass `HTTPHandler`/`HTTPSHandler`, so those two defaults are skipped,
     but every other default — including `ProxyHandler`, which reads `HTTP_PROXY`/`HTTPS_PROXY`/
     `NO_PROXY` — is still installed unmodified, exactly as `urlopen`'s own default opener installs it.
   - **Redirect handling.** Same mechanism: `HTTPRedirectHandler` (301/302/303/307/308, `max_redirections
= 10`, reusing the same `OpenerDirector` and its handlers across hops via
     `self.parent.open(new, timeout=req.timeout)`) is untouched — the new handlers only replace the two
     that talk to a raw connection, not the ones deciding whether to follow a redirect.
   - **Header handling.** Request header construction (`Accept`, `User-Agent`, `Authorization`) is
     unchanged; response header extraction (`dict(resp.headers.items())`) is unchanged — the new
     handlers only intervene inside `do_open`, below where headers are read.

3. **The `dribble-head` row (14) was added to both ports' harness**, the peer of `dribble-body` (13):
   a raw-socket handler that sends one head byte (`"H"`) every `DRIBBLE_INTERVAL` for
   `DRIBBLE_LENGTH` iterations and never completes a status line — Python's `_dribble_head` in
   `transport_contract.py`, TypeScript's `"dribble-head"` entry in `FAILURE_HANDLERS` in
   `transport-contract.ts`. Both reuse the existing dribble timing constants; no new ones were needed.
   TypeScript's `FetchTransport` required no code change — `AbortSignal.timeout` already spans
   connect-through-body — confirmed by running the full `packages/typescript/src/pin/` suite
   (275 tests, all passing) after adding the row.

4. **Both ports' `HttpClient` docstring is restored to the whole-call contract** — wall clock from the
   moment `get` is called, connect through head through body, one budget, no exception carved out for
   Python. Python's now reads (in part): _"A `get` completes, or fails, within `API_TIMEOUT_SECONDS`
   measured on the wall clock from the moment it is called — connecting, reading the response head, and
   reading the body, all under the one budget. ... Rows 13 and 14 of the conformance table
   (`dribble-body`, `dribble-head`) are that peer, at each phase, and both are what an adapter must
   survive."_ TypeScript's mirrors it, referencing the same two rows and pointing at
   `UrllibTransport._deadline_socket_class` instead of the retired `_read_within`-does-the-clamping
   language.

**Red measurement (pre-fix, reproduced against the unmodified `UrllibTransport` with the new
`dribble-head` row):** `TransportError` after **10.20 s** under a 1.0 s deadline — matching the shape
of the issue's own **10.31 s** figure; the head-dribbling peer held the per-operation-timeout
connection open through the full 10 s dribble.

**Green measurement (same scenario, fixed `UrllibTransport`):** `TransportError` after **1.00 s**
under a 1.0 s deadline — `timed out`.

**The "default value only" mutation blind spot is still caught.** `UrllibTransport.__init__`'s default
was changed from `timeout: float = API_TIMEOUT_SECONDS` to a detached literal (`= 3600.0`) and the
suite re-run: `TestDefaultDeadline::test_default_constructed_adapter_uses_the_declared_deadline` failed
(`3600.000... != 30.0 ± 0.1`), because that test was rewritten to run a real loopback request and spy on
`_deadline_connection_class` — the one seam the constructor's `timeout` value passes through on its way
to actually governing a request — rather than monkeypatching `urllib.request.urlopen`, which the new
implementation no longer calls. Its TypeScript peer (`describe("FetchTransport's default deadline",
...)`, spying on `AbortSignal.timeout`) was unaffected by this issue and needed no change.

**Wall-clock cost added.** The `dribble-head` row runs at `FAILURE_DEADLINE_SECONDS` / `FAILURE_DEADLINE_MS`
(0.25 s / 250 ms) in the conformance table, the same budget every other failure row already uses — about
+0.25 s to each port's suite. `TestDefaultDeadline`'s two rewritten cases now open a real (instant,
localhost) loopback connection instead of calling a stub directly, adding low tens of milliseconds.
Full-suite totals after the change: **929 pytest passed** (was 928), **983 vitest / 45 files passed**
(was 982) — both suites complete in a few seconds, unchanged in character.
