# The HTTP deadline does not cover the response head in Python

**Status:** open — from round 2's whole-branch review fix pass

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
