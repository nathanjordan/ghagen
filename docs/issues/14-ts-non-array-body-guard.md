# TypeScript pagination breaks on a non-array body; Python has no peer guard

**Status:** closed — from round 2

`packages/typescript/src/pin/github.ts:189-191`:

```ts
if (!Array.isArray(body)) break;
```

Python's paging loop has no equivalent. Under a malformed page the two ports diverge: TypeScript
stops and returns what it has, Python raises.

Left out of round 2 deliberately — hotfix H5 (`JSONDecodeError` → `ResolveError`) covers the
_malformed JSON_ case in Python, and proposal 16 lifts transport policy into the `HttpClient`
interface. Whether "a 200 whose body is the wrong shape" is a transport error or a resolve error is
a decision that belongs with 16's landed interface, not ahead of it.

## Resolution

**Both ports now raise.** A 200 whose body is not the documented shape — including a page that
parses as JSON but is not an array — is a server contract violation, not a signal to stop
pagination early. `GitHubClient.listTags` / `list_tags` turns it into `ResolveError`, exactly like
every other malformed-shape response the module already validates against (`refObject`,
`requireSha`, `commitSha`). Silently truncating and returning a partial tag list, as the old TS
guard did, would make `upgrade()` recommend a wrong version with no signal that anything went
wrong — worse than failing loudly.

By the time this issue was picked up, 16's `HttpClient` interface had landed and a prior fix
(`fix(pin): a shape-malformed 200 raises ResolveError in both ports`) had already replaced the
silent `if (!Array.isArray(body)) break;` with `refNames()` (`github.ts`) / `_ref_names()`
(`github.py`), a shared shape-validation helper that both `resolveRef`/`listTags` and their Python
peers route every parsed body through. That helper throws `ResolveError` with the message
`Unexpected response shape from {url}: expected an array, got {type}` — asserted character-for-
character equal across ports by `test_message_shape_matches_the_typescript_port`
(`test_github.py`) and its TypeScript peer.

**Behaviour change:** yes, for TypeScript only. Before this line of work, `listTags` returned a
truncated (or empty) array when the API answered a page with the wrong shape; it now raises
`ResolveError`. Pre-1.0, so this is a deliberate, disclosed break rather than something requiring a
deprecation path. Python's behaviour also changed from leaking bare `KeyError`/`TypeError`/
`AttributeError` (outside the documented `ResolveError` contract, so the engine's per-ref recovery
missed them) to raising `ResolveError` consistently.

**What this issue's own pass added — the shared transport-contract row.** The malformed-shape
fix above is per-`GitHubClient` business logic, asserted independently in each port's test suite.
Nothing bound the two adapters (`FetchTransport`/`UrllibTransport`, and the canned `FakeTransport`)
to deliver a non-array page identically at the transport layer, so a future adapter change — one
port "helpfully" repairing or re-shaping an odd body before `GitHubClient` sees it — could
reintroduce the divergence beneath the shape-check without either port's tests noticing. Row 8,
`non-array-page`, was added to the shared conformance table
(`packages/typescript/src/pin/transport-contract.ts`, `packages/python/tests/test_pin/transport_contract.py`)
alongside the existing `html-200` row: a 200 whose body is well-formed JSON but the wrong shape
(an object, not an array), asserted byte-for-byte identical through every adapter — real and
canned, on both ports. Every downstream row number shifted by one (rows 8-12 → 9-13); all
"Row N" cross-references in both contract files and in `github.ts`/`github.py`'s deadline
docstrings were updated to match.

A second, narrower regression test was added directly against `GitHubClient.listTags` /
`list_tags` on both ports (`throws when a later page is malformed, not just the first` /
`test_a_later_page_being_malformed_also_raises`): page 1 is well-formed with a `Link` header,
page 2 is not an array. This pins the literal scenario in the issue title — a malformed page
reached mid-pagination, not only the first request — since the shared shape-check function does
not distinguish page position and a first-page-only test would not have caught a regression
specific to the loop's second iteration.

## Files

- `packages/typescript/src/pin/github.ts` — `refNames`/`GitHubClient.listTags`
- `packages/python/src/ghagen/pin/github.py` — `_ref_names`/`GitHubClient.list_tags`
- `packages/typescript/src/pin/transport-contract.ts` — row 8, `non-array-page`
- `packages/python/tests/test_pin/transport_contract.py` — row 8, `non-array-page`
- `packages/typescript/src/pin/github.test.ts`, `packages/python/tests/test_pin/test_github.py` —
  the mid-pagination regression test
