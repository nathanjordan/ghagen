# 16 — Lift transport policy into the `HttpClient` interface

**Status:** proposed | **Ports:** both | **Effort:** L | **Depends on:** nothing hard; barrel contention on `packages/python/src/ghagen/pin/__init__.py` with **14**, **17**, **18**, and on both TypeScript barrels with **14**, **17**, **18**, **20** (mapped in _Scope boundaries vs siblings_)

Effort is **L**, not M: change (c) retypes every canned response body in the TypeScript suites, which
rewrites **14** call sites in `github.test.ts` and the two helper bodies plus one inline literal in
`engine.test.ts` — mechanical, but it is the whole of both files' fixture layer, on top of two adapter
rewrites and four new test modules.

## Files involved

Line counts are `wc -l` on `main` at `e7a972c`.

### Modified

| Path                                            | Lines | Role in this proposal                                                                                                                                                                                                                                                                                                                                                                                          |
| ----------------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/src/ghagen/pin/github.py`      | 309   | `HttpClient` docstring becomes the normative contract (deadline + total error taxonomy); `_API_TIMEOUT_SECONDS` (`:30`) → `API_TIMEOUT_SECONDS`; `UrllibTransport.get` (`:94-124`) is restructured so the I/O — and only the I/O — sits under a total failure mapping, and gains a deadline constructor argument                                                                                               |
| `packages/python/src/ghagen/pin/__init__.py`    | 58    | add `TransportError` to the `ghagen.pin.github` import block (`:15-21`, inserting at `:20`) and to `__all__` (`:33-58`, inserting at `:46`) — it is missing today. **Contended with 14, 17, 18 — see below**                                                                                                                                                                                                   |
| `packages/typescript/src/pin/github.ts`         | 313   | `HttpResponse` (`:47-56`) becomes an exported **class** carrying the already-read body, with Python's field order; private `FetchResponse` (`:65-83`) deleted; `FetchTransport` (`:93-114`) reads the body inside its own `try` and gains a deadline constructor argument; `getJson`/`getPage`'s duplicated parse catch (`:240-246`, `:256-262`) folds into one `parseJson`; `API_TIMEOUT_MS` (`:15`) exported |
| `packages/typescript/src/pin/index.ts`          | 46    | `type HttpResponse` (`:17`) becomes a value export                                                                                                                                                                                                                                                                                                                                                             |
| `packages/typescript/src/index.ts`              | 203   | same one-token flip at `:179`                                                                                                                                                                                                                                                                                                                                                                                  |
| `packages/python/tests/test_pin/test_github.py` | 309   | delete the local `_json_response` (`:32-44`) and `FakeTransport` (`:47-71`); import the shared double; `TestUrllibTransport` (`:263-297`) is replaced by the conformance run                                                                                                                                                                                                                                   |
| `packages/python/tests/test_pin/test_engine.py` | 251   | delete the second `FakeTransport` (`:52-65`) and `_json_response` (`:68-69`); import the shared double; `_commit` (`:72-73`) / `_tags` (`:76-77`) keep their bodies but call the shared builder                                                                                                                                                                                                                |
| `packages/typescript/src/pin/github.test.ts`    | 222   | delete `CannedInit`/`jsonResponse`/`Canned`/`FakeTransport` (`:17-63`); import the shared double; rewrite all 14 `jsonResponse(…)` call sites onto the shared signature; add the malformed-200 cases Python already has                                                                                                                                                                                        |
| `packages/typescript/src/pin/engine.test.ts`    | 242   | delete `jsonResponse`/`commit`/`tags`/`FakeTransport` (`:54-84`); import the shared double                                                                                                                                                                                                                                                                                                                     |
| `packages/typescript/tsconfig.json`             | 28    | add `src/pin/transport-contract.ts` to `exclude` (precedent: `src/integration/test-utils.ts` at `:25`)                                                                                                                                                                                                                                                                                                         |
| `packages/python/CONTEXT.md`                    | 114   | **Transport** glossary entry + one Surface-notes bullet (implementation phase; see last section)                                                                                                                                                                                                                                                                                                               |
| `packages/typescript/CONTEXT.md`                | 119   | mirror (implementation phase; see last section)                                                                                                                                                                                                                                                                                                                                                                |

### New

| Path                                                        | Role in this proposal                                                                                                                              |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/tests/test_pin/transport_contract.py`      | the one Python double (`FakeTransport`, `canned()`, `canned_raw()`), the raw-socket loopback origin, and `assert_transport_contract(make_adapter)` |
| `packages/python/tests/test_pin/test_transport_contract.py` | runs the contract against `UrllibTransport` **and** `FakeTransport`                                                                                |
| `packages/typescript/src/pin/transport-contract.ts`         | the one TypeScript peer of the above (excluded from the build)                                                                                     |
| `packages/typescript/src/pin/transport-contract.test.ts`    | runs the contract against `FetchTransport` **and** `FakeTransport`                                                                                 |

Deliberately **not** touched: `pin/engine.py` / `pin/engine.ts` (cited only), `cli/deps.py` / `cli/deps.ts`
and their tests (owned by **18**), `docs/astro.config.mjs` (its nine TypeDoc entry points, at
`:126,133,140,147,154,161,168,175,182`, are all `_docs-api-*.ts` and none reaches `pin`), and
`packages/typescript/package.json` (`:29-34` publishes only `"." → dist/index.js`; nothing in this
proposal changes the entry point).

## Problem

`HttpClient` is one of the healthiest seams in the repo. Both ports drive it with a canned transport,
neither mocks the module under test, and the production adapter is injected — `GitHubClient` takes it
at construction (`packages/python/src/ghagen/pin/github.py:135-143`,
`packages/typescript/src/pin/github.ts:127-130`). Two adapters per port, so it is a real seam, not a
hypothetical one.

The friction is that **the policy every adapter must agree on is stated nowhere in the interface.**
`HttpClient` is a bare signature:

```python
# packages/python/src/ghagen/pin/github.py:75-81
class HttpClient(Protocol):
    """Transport seam: a single authenticated GET returning a :class:`Response`."""

    def get(self, url: str, *, token: str | None = None) -> Response:
        """GET ``url`` and return the response (raise :class:`TransportError` on
        network failure)."""
```

"Network failure" is not a definition, and there is no mention of a deadline at all. Both facts —
how long a request may take, and what may come out of `get` — are then re-decided per adapter, in
prose comments, and the ports drift. Six things are live on the tree today.

### 1. Python's `UrllibTransport` leaks non-`TransportError` exceptions — two of them. **LIVE.**

The failure branch enumerates two exception types:

```python
# packages/python/src/ghagen/pin/github.py:121-124
        except (urllib.error.URLError, TimeoutError) as exc:
            # A read timeout surfaces as a bare TimeoutError rather than a
            # URLError, so both map onto the transport's failure contract.
            raise TransportError(str(exc)) from exc
```

An enumeration is not a contract. Driving the real adapter against a raw loopback socket, three
ordinary flaky-origin events — measured, at `e7a972c`:

```
abrupt-close  -> LEAKED http.client.RemoteDisconnected: Remote end closed connection without response
truncated     -> LEAKED http.client.IncompleteRead: IncompleteRead(5 bytes read, 95 more expected)
html-200      -> RETURNED status=200 body=b'<html>not json</html>'      (correct)
```

Two distinct leaks, on two distinct lines:

- **`RemoteDisconnected`** (peer accepts the connection and closes it without writing a response) is
  raised by `h.getresponse()` outside the `OSError` wrapping `urllib` applies to the request phase.
- **`IncompleteRead`** (origin declares `Content-Length: 100` and sends 5 bytes) escapes from
  `resp.read()` at `github.py:109` — _inside_ the `urlopen` context manager, but still outside the
  enumeration.

Neither is a `URLError` or a `TimeoutError`, so both escape `get` in violation of the docstring at
`:78-81`. The TypeScript adapter maps the first event correctly because it uses a total `catch`
(`packages/typescript/src/pin/github.ts:109-111`); on the second it is wrong in a different way (§2).

### 2. Neither port's body read is inside its own error taxonomy. **LIVE, both ports.**

`FetchTransport` puts only the response _head_ inside its `try`:

```ts
// packages/typescript/src/pin/github.ts:103-113
let response: Response;
try {
  response = await fetch(url, {
    headers,
    signal: AbortSignal.timeout(API_TIMEOUT_MS),
  });
} catch (err) {
  throw new TransportError((err as Error).message);
}
return new FetchResponse(response);
```

`FetchResponse.json()` (`:76-78`) is lazy — the body is not read until `GitHubClient.getJson` calls it
(`:241`), long after the `try` has closed. Driving the real transport against a loopback origin (same
shape as `FetchTransport`, short deadline so the run finishes) — measured, at `e7a972c`:

```
html-200        -> SyntaxError/SyntaxError: Unexpected token '<', "<html>not "… | instanceof TransportError: false
stall-mid-body  -> DOMException/TimeoutError: The operation was aborted due to timeout
                                                                       | instanceof TransportError: false
abrupt-close    -> TransportError/TransportError: fetch failed         | instanceof TransportError: true
truncated       -> TypeError/TypeError: terminated                     | instanceof TransportError: false
```

Rows 2 and 4 are the defect. The abort and the truncation both fire _after_ the head arrives, so they
surface from `json()`, miss the transport's `catch` entirely, and land in `getJson`'s parse handler:

```ts
// packages/typescript/src/pin/github.ts:240-246
try {
  return await resp.json();
} catch (err) {
  throw new ResolveError(`Failed to parse JSON response from ${url}: ${(err as Error).message}`);
}
```

Driving that whole path end to end produces, verbatim:
`ResolveError: Failed to parse JSON response from <url>: terminated`. A user whose network stalls or
whose origin truncates a response is told the JSON is malformed. `TransportError` — the type whose
entire job is "no response was obtained" — is never involved.

**Python is not a counter-example.** Python is correct for a _pure stall past the deadline_:
`resp.read()` runs inside the `urlopen` context manager under the socket timeout
(`github.py:104-112`), so that event is a `TimeoutError` → `TransportError` →
`ResolveError("Network error reaching GitHub API: …")`. It is wrong on the _truncated_ body, on the
same line — `github.py:109` leaks `IncompleteRead` (§1). So neither port has its body read inside its
taxonomy; they merely fail on different inputs, which is exactly the drift this proposal exists to
end. Both ports fail conformance row 11 today, in two different disguises.

**Why the taxonomy is not cosmetic.** The pin engine does per-ref error recovery keyed exactly on
`ResolveError`:

```python
# packages/python/src/ghagen/pin/engine.py:100-104
        try:
            sha = client.resolve_ref(ref.owner, ref.repo, ref.ref)
        except ResolveError as exc:
            report.errors.append(f"{ref.uses}: {exc}")
            continue
```

and its TypeScript peer rethrows anything else (`packages/typescript/src/pin/engine.ts:86-94`).
`write_lockfile` runs _after_ the loop (`engine.py:111-113`). So an exception outside the taxonomy —
today's `RemoteDisconnected` or `IncompleteRead` — converts a recoverable single-ref failure into an
aborted run that writes **nothing**, discarding every SHA already resolved in that pass. Defect 1 is
not a cosmetic type mismatch; it costs the user the whole run.

### 3. The one number both ports must agree on is held together by a comment. **LATENT.**

```python
# packages/python/src/ghagen/pin/github.py:27-30
# Wall-clock ceiling on a single API request.  Mirrors the TypeScript port's
# ``API_TIMEOUT_MS`` (``pin/github.ts``); without it a stalled connection hangs
# ``ghagen pin`` forever.
_API_TIMEOUT_SECONDS = 30.0
```

versus `const API_TIMEOUT_MS = 30_000;` (`packages/typescript/src/pin/github.ts:15`). They agree
today — nothing is broken on the tree, which is why this is labelled latent and not live. What holds
them together is a prose cross-reference in one direction; the Python name is `_`-prefixed and the
TypeScript one is module-private, so neither is reachable by a third-party adapter that is
nonetheless expected to honour it.

**Correction to the survey.** The survey's "Python has no timeout" and "Python leaks
`JSONDecodeError`" premises are **dead** — both were fixed by hotfix (`b150bc7`, `7c3964f`). The
constants now match and `_parse_json` (`github.py:229-240`) maps `json.JSONDecodeError` →
`ResolveError` in both ports. Do not re-propose either. What survives is the _reason the divergence
was possible_, which nothing on the tree has addressed.

### 4. `TransportError` is not on Python's public surface. **LIVE parity gap.**

`ghagen.pin` re-exports `GitHubClient`, `HttpClient`, `ResolveError`, `Response`, `UrllibTransport`
(`packages/python/src/ghagen/pin/__init__.py:15-21`) — and not `TransportError`. TypeScript exports it
from both barrels (`packages/typescript/src/pin/index.ts:15`,
`packages/typescript/src/index.ts:177`). A Python user writing an `HttpClient` adapter cannot import
the exception the interface _requires_ them to raise without reaching into the private module path
`ghagen.pin.github`.

### 5. The canned double is written four times, and they disagree.

|                                    | `test_github.py:47-71`                                      | `test_engine.py:52-65`          | `github.test.ts:36-63`                       | `engine.test.ts:71-84`            |
| ---------------------------------- | ----------------------------------------------------------- | ------------------------------- | -------------------------------------------- | --------------------------------- |
| records tokens                     | yes (`:58`,`:62`)                                           | **no**                          | yes (`:43`,`:49`)                            | **no**                            |
| list-of-responses (pagination)     | yes (`:65-66`)                                              | **no**                          | yes (`:52-53`)                               | **no**                            |
| scripted exception                 | yes (`:67-68`)                                              | **no**                          | yes (`:55-56`)                               | **no**                            |
| header lookup on a canned response | case-insensitive via `Response.header`                      | same, but no test ever sets one | case-insensitive via `new Headers()` (`:25`) | **always `null`** (`:59`)         |
| unmatched-URL 404                  | `reason="Not Found"` (`:71`)                                | `reason="Not Found"` (`:65`)    | `statusText: ""` (`:61` via `:28`)           | `statusText: "Not Found"` (`:82`) |
| **can express a malformed body**   | **yes** — `Response(status=200, body=b"…")`, used at `:248` | no                              | **no**                                       | **no**                            |

The last row is the structural one. Python's `Response` is a concrete frozen dataclass carrying
`body: bytes` (`github.py:47-72`, the field at `:58`), so any double can hand the client bytes that
will not parse — and Python has the tests to prove the mapping (`test_github.py:243-260`,
`TestMalformedJson`). TypeScript's `HttpResponse` is an _interface_ whose `json(): Promise<unknown>`
(`github.ts:53`) every double implements by hand, and all four in-repo implementations return an
already-parsed value (`json: async () => init.body`, `github.test.ts:29`). In TypeScript, `json()`
**cannot fail in any test**. The missing malformed-JSON coverage is not an oversight — the seam's own
shape forbids it. Two adapters that behave differently is a divergence; two adapters one of which
cannot be tested is the mechanism that produces divergences.

### 6. TypeScript's production adapter has zero tests. **LIVE.**

`FetchTransport` appears in exactly five places in the tree: its definition (`github.ts:93`), the
module doc comment (`:6`), the default in `GitHubClient`'s constructor (`:128`), and two barrel
re-exports (`pin/index.ts:13`, `index.ts:176`). No test file references it.

Python is better off since the timeout hotfix — `TestUrllibTransport` (`test_github.py:263-297`) has
two tests — but neither has ever seen a socket, and the first asserts plumbing rather than behaviour,
precisely because the deadline is not settable:

```python
# packages/python/tests/test_pin/test_github.py:287-289
        monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
        UrllibTransport().get("https://api.github.com/x")
        assert captured["timeout"] == _API_TIMEOUT_SECONDS
```

That asserts a keyword argument was forwarded. It would still pass if `urlopen` ignored it. Its
sibling, `test_timeout_becomes_transport_error` (`:291-297`), _is_ a behavioural test — it asserts the
`TimeoutError` → `TransportError` mapping — but through a monkeypatched `urlopen` that raises on
demand, so it can only ever exercise exception types the author already thought of. That is why
§1's two leaks survived it. No test in either port has ever put either production adapter in front of
a socket.

## Current interface

Everything a caller — or an adapter author — must know about `HttpClient` today:

- **Signature.** `get(url, *, token=None) -> Response` (Python, `github.py:78`);
  `get(url, options?: RequestOptions): Promise<HttpResponse>` (TypeScript, `github.ts:61`).
- **Deadline.** Unstated. Each adapter picks one privately; the two happen to match; a third adapter
  would have none.
- **Error modes.** "raise `TransportError` on network failure" — an undefined term, implemented as an
  exception-type enumeration in Python (`:121`) and a total `catch` in TypeScript (`:109`), so the two
  adapters classify the same event differently.
- **Who reads the body.** Unstated, and answered differently: Python inside `get` (`:109`),
  TypeScript lazily in `GitHubClient` (`:241`) — and _neither_ answer puts the read inside the
  adapter's error handling.
- **Response shape.** A concrete dataclass in Python (`Response`, `:47-72`), a structural interface in
  TypeScript (`HttpResponse`, `:47-56`), the latter with an async `json()` that every double must
  re-implement.
- **Reachability.** `TransportError` is public in TypeScript and private in Python (§4).

That is a shallow interface in the exact sense: a maintainer reading `HttpClient` learns the argument
list and nothing about the behaviour, so all the behaviour has to be re-derived — and re-decided — at
each of the six implementation sites.

## Proposed interface

Move the deadline, the error taxonomy, and the body-read boundary **into** `HttpClient`, stated once
and enforced by a conformance table every adapter runs. Four changes; each is justified against the
deletion test below.

### (a) The deadline is part of what `HttpClient` means

Promote the constant to a public module-level name in the module that defines `HttpClient`
(`API_TIMEOUT_SECONDS` / `API_TIMEOUT_MS`) and state it in the interface: _a `get` completes, or fails,
within the deadline — including reading the body._ Each production adapter takes it as one defaulted
constructor argument:

```python
class UrllibTransport:
    def __init__(self, timeout: float = API_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout
```

```ts
export class FetchTransport implements HttpClient {
  constructor(private readonly timeoutMs: number = API_TIMEOUT_MS) {}
```

**Deletion test.** Delete the argument and the deadline row of the conformance table has two options:
wait 30 s, or monkeypatch `urlopen` and assert a forwarded kwarg — which is `test_github.py:266-289`
today, and which passes whether or not the adapter honours the value. One defaulted argument, set by
exactly one caller (the conformance test), is what converts an unfalsifiable prose claim into a
behavioural assertion. It is not an unset optional knob; it earns its keep by making the interface's
central promise testable at all. No per-call `timeout` option is added — that _would_ be caller-less
surface, and is explicitly out.

### (b) The error taxonomy becomes total, and both ports state it identically

`HttpClient.get`:

- returns an `HttpResponse`/`Response` for **any** HTTP response it obtains, including 4xx and 5xx,
  including a non-JSON body — the transport never parses and never judges a status;
- raises/rejects **`TransportError`, and nothing else**, for every failure to obtain one — refusal,
  DNS, reset, mid-body abort, truncated body, deadline;
- never raises the underlying library's exception type.

Python's enumeration widens to the same total shape TypeScript already uses. **The widening must not
swallow bugs in this module's own code.** Today's `try` (`github.py:103-112`) spans `urlopen`,
`resp.status`, `resp.read()`, `resp.reason`, `dict(resp.headers.items())` **and** the `Response(...)`
construction; a bare widening would report a defect in response construction as a network failure. So
the I/O is hoisted into locals and the construction moves out from under every handler:

```python
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                status, body = resp.status, resp.read()
                reason, headers = resp.reason or "", dict(resp.headers.items())
        except urllib.error.HTTPError as exc:
            # An HTTPError *is* a response — but reading it is still I/O and can
            # itself truncate, so it gets the same total mapping.
            try:
                status, body = exc.code, exc.read()
                reason, headers = exc.reason or "", dict(exc.headers.items())
            except Exception as read_exc:
                raise TransportError(str(read_exc)) from read_exc
        except Exception as exc:          # total, per the interface contract
            raise TransportError(str(exc)) from exc
        return Response(status=status, body=body, reason=reason, headers=headers)
```

`HTTPError` subclasses `URLError` subclasses `OSError` subclasses `Exception`, so the ordering above
is load-bearing: the response branch must precede the total branch. TypeScript's `FetchTransport` gets
the same treatment under (c) — response construction after the `try`, never inside it.

That closes defect 1: `RemoteDisconnected`, `IncompleteRead`, `ValueError` from a hostile `Link`-header
URL, and any future `http.client` exception all land inside the taxonomy. `TransportError` is added to
`ghagen.pin`'s barrel, closing defect 4.

### (c) The response carries a body the transport has already read

TypeScript's `HttpResponse` stops being a structural interface with an async `json()` and becomes a
concrete exported class mirroring Python's `Response` — **including its constructor order**, so the
one type being made to match does not introduce a fresh parity trap:

```ts
export class HttpResponse {
  constructor(
    readonly status: number,
    readonly body: string, // Python: Response(status, body, reason, headers)
    readonly statusText: string = "", // Python's `reason`; the name stays TS-idiomatic
    private readonly headers: Readonly<Record<string, string>> = {},
  ) {}

  json(): unknown {
    // sync; throws the language's native decode error
    return JSON.parse(this.body);
  }

  header(name: string): string | null {
    /* case-insensitive, mirrors github.py:66-72 */
  }
}
```

`FetchTransport` then does `await response.text()` **inside** its `try`, so the body read is under the
deadline and inside the taxonomy — closing defect 2 on both the stall and the truncation. (Measured:
with the read inside the `try`, a truncated body surfaces as `TypeError: terminated` from `text()` and
is mapped to `TransportError`; today it surfaces from `json()` as
`ResolveError: Failed to parse JSON response from <url>: terminated`.) The private `FetchResponse`
wrapper (`github.ts:65-83`) is deleted; `getJson`/`getPage`'s two identical parse handlers (`:240-246`,
`:256-262`) fold into one `parseJson(resp, url)` peer of Python's `_parse_json` (`github.py:229-240`).

**Deletion test on the new class.** Delete it and TypeScript is back to four hand-written `json()`
implementations that cannot throw, and the malformed-200 case is untestable again. The complexity does
not vanish — it reappears at every double. And the class _removes_ interface surface on net:
`HttpResponse` stops being something an adapter author implements and becomes something they
construct, so `FetchResponse` disappears and the two ports' response types become the same shape.

**This is the change that makes the effort L.** Every canned body in the TypeScript suites is
currently an already-parsed JavaScript value handed to a hand-written `json()`; under a `body: string`
class it has to be encoded. The shared builder does the encoding (`canned(value, opts)` calls
`JSON.stringify`, exactly as Python's `_json_response` calls `json.dumps(...).encode()`), so no call
site grows a literal `JSON.stringify` — but every call site is still rewritten, because the shared
builder's signature replaces `github.test.ts`'s local `CannedInit` bag. That is **14 sites** in
`github.test.ts` (`:61,72,83,93,94,102,103,111,120,143,152,154,169,182`) and, in `engine.test.ts`, the
two helper bodies (`:64`, `:68`) plus the inline unmatched-404 literal (`:82`) — the four
`commit()`/`tags()` call sites (`:140,176,197,213`) are unaffected because they funnel through those
helpers. A second builder, `canned_raw` / `cannedRaw`, takes a body verbatim for the malformed-200 and
truncation rows.

### (d) One double per port, and one conformance table

`FakeTransport` moves to `transport_contract.py` / `transport-contract.ts` in the union of today's
four feature sets: token recording, list-of-responses for pagination, scripted exceptions,
case-insensitive headers, and unparsed bodies. `assert_transport_contract(make_adapter)` /
`runTransportContract(makeAdapter)` runs one table against any adapter:

| #   | scenario                                                     | required outcome                                                            | binds                                  |
| --- | ------------------------------------------------------------ | --------------------------------------------------------------------------- | -------------------------------------- |
| 1   | 200 + JSON body                                              | returns; `status == 200`; `body` is exactly what the origin served          | both                                   |
| 2   | 200 + `<html>` body                                          | **returns**, does not raise; `body` is the raw non-JSON payload             | both                                   |
| 3   | 404                                                          | returns; `status == 404`                                                    | both                                   |
| 4   | 500 + reason phrase                                          | returns; `status == 500`; `reason`/`statusText` carries the phrase          | both                                   |
| 5   | `Link:` response header                                      | `header("link") == header("LINK") == value`                                 | both                                   |
| 6   | token supplied                                               | `Authorization: Bearer <t>` observed at the origin / recorded by the double | both                                   |
| 7   | no token                                                     | no `Authorization` header                                                   | both                                   |
| 8   | connection refused                                           | `TransportError`                                                            | real only                              |
| 9   | peer accepts, closes without a response                      | `TransportError`                                                            | real only — **Python fails today**     |
| 10  | origin stalls past the deadline                              | `TransportError`, within the deadline                                       | real only — **TypeScript fails today** |
| 11  | origin declares `Content-Length: 100`, sends 5 bytes, closes | `TransportError`                                                            | real only — **both ports fail today**  |

Rows 8-11 are satisfied by construction for a canned double (it raises what it is scripted to raise),
so the double runs rows 1-7 only; the table says so rather than pretending to be uniform. That is
**7 + 11 = 18 cases per port**, but the count is not the point and should not be read as coverage:
rows 1-3 and 5 against a canned double are shape assertions that mostly restate the builder. The
load-bearing rows are:

- **row 4** — the `HTTPError`-is-a-response branch (`github.py:113-120`) has **zero coverage today**;
- **rows 6/7** — the only proof either production adapter sends `Authorization: Bearer` at all;
- **rows 8-11** — the four failure modes, three of which fail on `main` (9 on Python, 10 on
  TypeScript, 11 on both).

Rows 1-7 nonetheless bind every adapter, including the double — which is the point: the double stops
being able to drift into a shape the real adapter cannot produce, which is how §5's last row happened.

**Deletion test on the conformance table.** Delete it and defects 1 and 2 are undetectable again, and
the next adapter (or the next hotfix to one adapter) re-opens the divergence with nothing to catch it.
This is the module that stops the drift from recurring; everything else in this proposal is the
one-time patch that makes it passable.

**No new optional knobs.** The only added parameter in the whole proposal is (a)'s deadline, set by
one caller. `RequestOptions` is left exactly as it is — see the boundary note vs 20.

## What sits behind the seam

`HttpClient` absorbs the three facts that were previously restated per adapter: the deadline, the
totality of `TransportError`, and where the body read happens. A caller — `GitHubClient` — gets to
assume that after `get` returns, the network is done with: the body is in hand, the deadline has been
honoured, and any failure already wears the documented type. That is leverage: `GitHubClient` keeps
exactly one `except TransportError` (`github.py:214-217`, `github.ts:213-220`) and one JSON-parse site,
with no residual "what else might urllib/undici throw" reasoning.

For maintainers it is locality. Today the answer to "what happens on a mid-body stall" lives in three
places per port — the adapter, the response wrapper, and the client's parse handler — and the two
ports answer differently. After this, it lives in the `HttpClient` docstring and rows 10-11 of one
table, and a change to it fails both ports' suites at once.

## Migration plan

Pre-1.0; clean breaks, no compatibility shims. Steps 1-2 and 3-4 are independent and can run in
parallel; step 5 lands last because it deletes the per-file doubles both ports' tests still import.

1. **Python interface + adapter.** Rename `_API_TIMEOUT_SECONDS` → `API_TIMEOUT_SECONDS`; rewrite the
   `HttpClient` docstring as the normative contract; add the deadline constructor argument; restructure
   `get` per (b) so only the I/O sits under the total handler and `Response(...)` is constructed after
   it. Add `TransportError` to `pin/__init__.py` (import at `:20`, `__all__` at `:46`).
2. **TypeScript interface + adapter.** Make `HttpResponse` a class in Python's field order; delete
   `FetchResponse`; move the body read inside `FetchTransport`'s `try` and the construction after it;
   add the deadline constructor argument; export `API_TIMEOUT_MS`; fold the two parse handlers into
   `parseJson`. Flip `type HttpResponse` → value in both barrels (`pin/index.ts:17`, `index.ts:179`).
3. **Contract module, Python.** `transport_contract.py` (double + loopback origin) and
   `test_transport_contract.py` running the table against `UrllibTransport` and `FakeTransport`. Rows
   9 and 11 fail before step 1 lands — land them as the regression guards.
4. **Contract module, TypeScript.** The peer. Rows 10 and 11 fail before step 2 lands. Add the helper
   to `tsconfig.json`'s `exclude` (`:21-27`), beside `src/integration/test-utils.ts` (`:25`).
5. **Delete the four doubles.** Rewrite the imports and every construction site in `test_github.py`,
   `test_engine.py`, `github.test.ts`, `engine.test.ts` onto the shared double — see (c) for the
   TypeScript site list. Where the shared double is stricter than a file's local one (headers,
   statusText), adjust the expectation, not the double.
6. Full suite both ports, plus `uv run ghagen check-synced` and `uv run ghagen deps check-synced` —
   neither should move; nothing here changes emitted bytes or lockfile contents.

### The loopback origin: two hang hazards and a shape constraint

The repo has no loopback-server test today (verified at `e7a972c`: no `http.server`, `socketserver`,
`createServer`, `node:net` or `socket.socket` anywhere under `packages/`), so steps 3-4 add a
genuinely new capability rather than reusing a fixture. Three things must be got right in the module
itself, not discovered during implementation:

- **Use a raw socket, not a request-handling server.** Rows 9 and 11 require an origin that closes
  without writing a response, and one that under-delivers a declared `Content-Length`. Neither is
  expressible through `http.server.BaseHTTPRequestHandler` or `node:http`'s `createServer`, both of
  which always frame a well-formed response. The origin is a `socket.socket` / `node:net`
  `createServer` that writes literal bytes; rows 1-7 write a hand-built status line and headers. This
  was the shape used to produce §1's and §2's measurements.
- **Python: never share one accept loop across scenarios.** `http.server.HTTPServer` is
  `socketserver.TCPServer` — single-threaded. A scenario whose handler deliberately never returns
  (row 10) blocks the accept loop, and the next scenario deadlocks rather than failing. Each scenario
  gets its own listening socket on `127.0.0.1:0` and its own `threading.Thread(daemon=True)`, closed
  in a context manager.
- **Node: `server.close()` is not always enough.** Measured on Node v24.14.0: `close()` _does_ now
  reap idle keep-alive connections (the pre-Node-19 hazard is gone), and a client-side abort takes its
  own socket down with it. But a connection with an **in-flight request the handler never answers**
  still blocks the `close` callback indefinitely — measured at >3 s, released only by
  `closeAllConnections()`. Row 10's stalling origin is exactly that shape, so teardown calls
  `closeAllConnections()` before `close()`, and awaits the callback.
- **Row 10 needs stated numbers.** The adapter under test is constructed with a **0.25 s / 250 ms**
  deadline (this is the sole caller of (a)'s argument). The assertion is `TransportError` **and**
  elapsed wall time **< 2.5 s** — an upper bound only, at 10× the deadline. No lower bound is asserted:
  a "did it really wait?" check flakes on a fast machine and adds nothing that the upper bound and the
  raised type do not already establish.

## Test impact

Baseline for the four touched test files: **34 pytest / 28 vitest** (measured at `e7a972c`; the
six-test gap is Python's `TestUrllibTransport`, `TestMalformedJson`, and `TestResponse`, which
TypeScript has no peer for).

- **New, both ports:** `test_transport_contract.py` / `transport-contract.test.ts` — 18 cases per port
  (rows 1-11 against the real adapter, rows 1-7 against the double). This is the first coverage
  `FetchTransport` has ever had, and the first coverage of `github.py:113-120` in either port.
- **New, TypeScript:** the malformed-200 peers of `test_github.py:243-260` (`resolveRef` and
  `listTags` against a `<html>` 200 → `ResolveError` matching `/Failed to parse JSON response/`).
  These are impossible to write today (§5) and become possible under (c).
- **New regression guards:** row 9 (Python, `RemoteDisconnected` → `TransportError`), row 10
  (TypeScript, mid-body deadline → `TransportError` → `ResolveError("Network error…")`), and row 11
  (**both** ports — Python leaks `IncompleteRead`, TypeScript mislabels it as a parse failure). All
  three fail on `main`.
- **Rewritten:** `TestUrllibTransport` (`test_github.py:263-297`) — the `urlopen` monkeypatch, the
  forwarded-kwarg assertion, and the synthetic `TimeoutError` are deleted in favour of rows 8-11,
  which observe the adapter in front of a socket instead of in front of a stub.
- **Rewritten (bulk):** all 14 canned-response construction sites in `github.test.ts` and the fixture
  helpers in `engine.test.ts` — see (c). The assertions do not move; only the constructions do.
- **Deleted:** four `FakeTransport` classes and their four response builders
  (`test_github.py:32-44,47-71`; `test_engine.py:52-65,68-69`; `github.test.ts:17-63`;
  `engine.test.ts:54-84`) — roughly 90 lines of near-duplicate test infrastructure, replaced by one
  module per port.
- **Unchanged:** every `GitHubClient` behaviour test. They construct the double differently and assert
  the same things; the client's observable behaviour does not move except where a defect is fixed.
- **Out of scope:** `test_cli/test_deps.py` patches `GitHubClient.list_tags`/`resolve_ref` directly
  (`:203`, `:267`, …) and `cli/deps.test.ts` mocks the whole `pin/index.js` module (`:17-29`) — a
  fifth and sixth doubling pattern, both above this seam, both owned by 18.

## Risks & alternatives

- **Alternative: fix the defects and stop.** This is the honest null hypothesis, and it is what the
  survey would have produced. Rejected on the evidence: the two defects that _were_ hotfixed were
  fixed the same way — per-adapter, in one port — and the fix for a Python timeout landed a comment
  (`github.py:27-29`) as the only link to the TypeScript constant. That process is also what left
  `IncompleteRead` behind: the hotfix that added `TimeoutError` to the enumeration widened it by
  exactly one exception type, because an enumeration can only ever be widened by the cases someone
  thought of. Patching adapter #1 and adapter #2 separately is precisely what produced six
  implementation sites with four different answers. The conformance table is the part that does not
  need re-doing next time.
- **Alternative: keep `HttpResponse` structural and give it a `bodyText()` method.** Rejected — it
  keeps `json()` (or its replacement) as something each double implements, which is the mechanism
  behind §5's last row. A class is what makes the double a _construction_ rather than an
  _implementation_.
- **Alternative: a per-call `timeout` in `RequestOptions` / the `get` keyword args.** Rejected
  outright. No caller would set it, `GitHubClient` has no reason to vary it per request, and it is
  exactly the caller-less optional surface 20 exists to remove.
- **Risk: `except Exception` in `UrllibTransport` is blunt.** Accepted, and deliberate — it is what
  the interface now _promises_, and it is what the TypeScript adapter has always done
  (`github.ts:109-111`). The bluntness is bounded by (b)'s restructuring: only `urlopen`, the reads
  and the header copies are inside it, and `Response(...)` is constructed outside every handler, so a
  defect in this module's own response construction surfaces as itself rather than as a
  `TransportError`. A narrower `except (OSError, http.client.HTTPException)` would be a third
  enumeration, and enumerations are the defect — `IncompleteRead` is `HTTPException`, but the next
  leak may not be. `KeyboardInterrupt`/`SystemExit` derive from `BaseException` and are unaffected.
- **Risk: (a) adds a constructor argument.** Bounded to one per adapter, defaulted, with a caller. See
  the deletion test in (a) — without it the deadline is a claim no test can check.
- **Risk: `HttpResponse` is a breaking change to the published TypeScript surface.** Yes; pre-1.0, and
  the repo mandate prefers a clean break. Third-party adapters go from implementing `HttpResponse` to
  constructing it — strictly less work.
- **Risk: the loopback tests are the repo's first socket-bound tests.** They bind `127.0.0.1:0`, never
  a fixed port, and never leave the loopback interface, so they are CI-safe; the hang hazards are
  addressed explicitly in _Migration plan_. If a sandbox ever forbids loopback binds, rows 8-11 are
  the only cases affected and can be skipped as a group.
- **Out of scope, deliberately: `Link`-header URL validation.** `_parse_next_link` (`github.py:283-299`)
  returns whatever the origin put in the header and it is fetched unchecked (`github.py:195`+`:203`,
  `github.ts:184`+`:198`). Under (b) a hostile value now at least lands as `TransportError` rather than
  a raw `ValueError`, but "which hosts may a transport be asked to fetch" is a separate policy question
  and a separate proposal.
- **Out of scope, recorded for the orchestrator: a port divergence inside a file this proposal
  rewrites.** `listTags`'s `if (!Array.isArray(body)) break;` (`github.ts:189-191`) has **no Python
  peer** — `list_tags` iterates `data` unconditionally (`github.py:199-202`), so a 200 whose body is a
  JSON object rather than an array silently yields `[]` in TypeScript and raises in Python. It is not
  transport policy and this proposal does not touch it, but it sits fifty lines below the parse
  handlers being folded, so whoever lands 16 will read it. Route to `docs/issues/`.

### Scope boundaries vs siblings

**The Python pin barrel is contested four ways, and this is the file to schedule around.**
`packages/python/src/ghagen/pin/__init__.py` (58 lines) has one isort-ordered import region (`:3-31`,
one `from ghagen.pin.X import …` statement per submodule) and one alphabetical `__all__` (`:33-58`).
Four round-2 proposals write to it:

| proposal      | adds                                                        | import-region effect                                                           | `__all__` insertion                              |
| ------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------ |
| **16** (this) | `TransportError`                                            | one name into the **existing** `ghagen.pin.github` block (`:15-21`), at `:20`  | `:46` (between `SyncReport` and `UpgradeReport`) |
| **14**        | `BumpSeverity`                                              | a **new** `from ghagen.pin.versions import …` statement after `uses` (`:31`)   | `:34` — first in the list, above `GitHubClient`  |
| **17**        | `render_upgrade_report`, `UpgradeFormat`, `MACHINE_FORMATS` | a **new** `from ghagen.pin.render import …` statement after `lockfile` (`:28`) | three entries                                    |
| **18**        | `UpdatePlan`, `plan_update`                                 | a **new** `from ghagen.pin.plan import …` statement after `lockfile` (`:28`)   | two entries                                      |

16 is the only one of the four editing an _existing_ import statement; the other three insert new
ones, and 17's and 18's insertions at `:29` shift every line below — including 16's `__all__` anchor.
All four then contend for the same alphabetical list. This is a mechanical merge, not a semantic one,
but it needs an order: whichever lands first, the rest rebase their line offsets. The same shape holds
on `packages/typescript/src/pin/index.ts` (46 lines — five claimants: 14, 16, 17, 18, 20) and
`packages/typescript/src/index.ts` (203 lines — seven claimants by Files-involved row: 09, 11, 14, 16,
17, 18, 20).

Per-sibling:

- **vs 20 (delete caller-less pin/spec surface) — real on the two TypeScript barrels, disjoint lines;
  no Python edge.** 16 flips `type HttpResponse` to a value export at `pin/index.ts:17` and
  `index.ts:179`; 20 narrows `pin/index.ts:21-27` and deletes `index.ts:106` and `:183-186`
  (`20-…:29-30`, `:676-682`). Same files, different lines — mechanical, not semantic. On
  `packages/python/src/ghagen/pin/__init__.py` there is **no edge at all**: 20 states it does not touch
  the file and has nothing there to touch (`20-…:553`, `:683-684`). Two substantive asks of 20:
  (i) 16 _adds_ `TransportError` to Python's barrel, so it must not be swept as unused — it is the type
  the `HttpClient` contract obliges an adapter author to raise; (ii) `RequestOptions`
  (`github.ts:41-44`, one optional field) is a legitimate 20 candidate and 16 deliberately leaves it
  alone. If 20 inlines it, `HttpClient.get`'s signature changes with it — schedule 16 first, or have
  20 rebase on 16's `github.ts`.
- **vs 20, arbitration: the four handed-off `pin/github.ts` exports — 16 DECLINES them.** 20 reports
  `refUrls`, `isAnnotatedTag`, `commitSha` and `parseNextLink` as caller-less and leaves them to this
  proposal (`20-…:684-688`). They are not caller-less and the characterisation should be corrected in 20. All four are **live inside their own module** — `refUrls` at `github.ts:139`, `isAnnotatedTag` at
  `:146`, `commitSha` at `:163`, `parseNextLink` at `:263` — so they are over-_exported_, not dead. The
  sole importer outside the file is `github.test.ts:9-12`, which unit-tests all four in
  `describe("pure helpers")` at `:189-222`; deleting the keyword breaks five passing tests, and `export`
  is the only mechanism ESM has for a test-visible module-private helper. They appear in neither
  `pin/index.ts` nor `src/index.ts`, and `package.json:29-34` publishes only `"." → dist/index.js`, so
  they are not on the published surface at all. Python's peers `_ref_urls` (`github.py:261`),
  `_is_annotated_tag` (`:269`), `_commit_sha` (`:274`) and `_parse_next_link` (`:283`) are
  underscore-private and imported by `test_github.py:22-25` for the identical reason — **the two ports
  are already at substantive parity.** The only remedy is cosmetic (`/** @internal */` or a `_` prefix
  on the TypeScript names), which is worth doing and is worth nobody's proposal. Route to
  `docs/issues/` as a hygiene item.
- **vs 15 (single-home the Lockfile's on-disk encoding) — no edge.** 15's encoder/decoder pair stays
  module-private and 15 touches none of the three barrels, stating so explicitly and by name
  (`15-…:28-30`, `:378-379`, `:482-486`). On the Python side 15 touches `pin/lockfile.py` and 16
  touches `pin/github.py`; 15 adds no export, and `LockfileError` — the symbol a barrel edge would have
  hinged on — is already present at `pin/__init__.py:24` and `:37`. 16 does not touch `pin/lockfile.py`,
  `pin/lockfile.ts`, or their tests. **No scheduling constraint between 15 and 16.**
- **vs 14 (`versions` owns comparison) — Python barrel, plus `test_engine.py`.** 14 adds
  `BumpSeverity` to `pin/__init__.py` (`14-…:15`, `:526`) via a new import statement, and describes
  its `pin/index.ts` / `index.ts` rows as no-ops if 20 lands first (`14-…:16-17`). It also carries
  `packages/python/tests/test_pin/test_engine.py` (251) as a Files-involved row (`14-…:27`), adding
  one `upgrade` case — a file whose entire fixture layer 16 rewrites (step 5). Different regions of
  the file, but it needs one owner at merge time. No ordering preference otherwise.
- **vs 17 (upgrade-report renderer) — Python barrel + both TS barrels, plus `test_engine.py`.** 17
  adds three names to all three barrels (`17-…:15-17`). Its new `from ghagen.pin.render import …`
  statement lands above 16's `__all__` anchor, so if 17 lands first 16's insertion offsets move by
  three or four lines. 17 also carries `test_engine.py` (251) as a Files-involved row (`17-…:24`),
  asserting two new report flags and absorbing `test_api_error_continues_with_warning` — and it
  builds on the very `FakeTransport` at `test_engine.py:52-65` that 16 deletes (`17-…:85`, `:361`),
  so 17 must be written against the shared double if 16 lands first. Same one-owner caveat as 14. No
  semantic interaction otherwise: 17 works downstream of `upgrade()` and touches no transport code.
- **vs 18 (pull `check-deps`'s decision logic across the CLI seam) — barrels only.** 18 adds
  `UpdatePlan` / `plan_update` to all three barrels (`18-…:21-23`, `:535`) and owns `cli/deps.*` and
  `test_deps.py` / `deps.test.ts`, which double `GitHubClient` at the _method_ and _module_ level. 16
  deliberately does not consolidate those into its double — they sit above this seam, and merging
  them is 18's call. **18 does not touch `packages/python/tests/test_pin/test_engine.py`** — its new
  tests live in `test_pin/test_plan.py`, which builds its own `App(root=tmp_path)` and
  hand-constructed reports and imports nothing from the engine test file (`18-…:39`, `:845-846`).
  There is no test-file edge between 16 and 18.
- **vs 19 (`main()` owns exit codes end to end).** 16 changes which exception type reaches
  `pin/engine`; 19 changes what the CLI does with the resulting report. Disjoint; 16 touches no CLI
  file. Note for 19: after 16, `pin`'s "one ref failed" path is genuinely total, so 19 can rely on a
  `PinReport` rather than on a traceback never escaping.

## ADR / CONTEXT.md impact

- **No ADR is contradicted, and none should be minted.** No ADR covers the transport seam. ADR-0006
  (pin collects parsed refs) is upstream of `GitHubClient` and unaffected; ADR-0005 (synthesis
  pipeline and transform ordering) is unaffected — pin still runs last, with the same report shape.
  An ADR is explicitly _not_ recommended here: the transport contract's whole value is that it is
  executable (the conformance table), and an ADR would be a second, non-executable copy of it that can
  silently fall out of date — which is the failure this proposal exists to end.
- **`packages/python/CONTEXT.md` — a new glossary term at `:77`,** the blank line between the
  **PinEntry** entry (`:75-76`) and `### Schema` (`:78`). **`packages/typescript/CONTEXT.md` — the
  same term at `:79`,** between **PinEntry** (`:77-78`) and `### Schema` (`:80`). One term only, in
  each file; no existing term is edited, and the anchor itself is uncontested.

  The pin glossary is nonetheless a **three-way append point**, not an exclusive region: 16 adds
  **Transport**, 14 adds **Version tag** and **Bump**, 17 adds **Upgrade report** (placed after 14's
  **Bump**). Assigned order **16 → 14 → 17**; 16 appends against today's tree, and 14 and 17 rebase
  their offsets. Hand-merge, not conflict.

  > **Transport**:
  > The injected HTTP adapter behind `HttpClient`. Returns a response for any status it obtains,
  > raises `TransportError` for every failure to obtain one, and honours the module deadline —
  > including reading the body. Every adapter, real or canned, passes the transport conformance table.

- **Surface notes — one appended bullet in each file,** at the tail of the list
  (`packages/python/CONTEXT.md:94-107`, last bullet ending `:107`;
  `packages/typescript/CONTEXT.md:96-112`, last bullet ending `:112`). This is a **shared append
  point, not an exclusive region**: three proposals append here — **16, 17, 10** — in that assigned
  order, matching dispatch batches, so 16 appends against today's tree and 17 and 10 follow. (19 is
  _not_ an appender; it edits inside an existing bullet.) Hand-merge, not conflict. The bullet
  records the one intentional asymmetry and the one
  invariant callers depend on: the response type is `Response` in Python and `HttpResponse` in
  TypeScript (the name `Response` is taken by the platform global), and the body is `bytes` in Python
  and `string` in TypeScript, matching each stdlib; `TransportError` and `ResolveError` are the only
  two error types crossing the pin/network boundary, and the pin engine's per-ref recovery
  (`engine.py:100-104`, `engine.ts:86-94`) depends on that totality. Everything else about the seam —
  the deadline, the taxonomy, the conformance table, the single double — is identical across the
  ports.
