# Pin collects parsed refs, not strings

**Status:** accepted (2026-07-28)

`collect_uses_refs` / `collectUsesRefs` return parsed, deduplicated (by full `uses` string),
sorted **UsesRef**s. Parse failure is handled once, in the **UsesSite** iterator; downstream pin
engine stages consume typed refs and carry no `parse(...) is None` guards — they are unreachable.
`UsesRef.uses` reconstructs the authored string losslessly and is the dedup and Lockfile key.

## Why

Collect previously returned bare strings although UsesSite already held the parsed ref, so the
engine re-parsed the same string up to four times, each site re-handling the null branch — a class
of "which stage swallowed the unparseable ref" bugs.

## Consequences

**The Lockfile boundary stays string-keyed** — `uses` strings → SHAs, snake_case keys, identical
across both ports. Do not "simplify" the Lockfile to store structured refs; the on-disk format is
cross-language interop surface. Only the in-memory pin flow is typed.

**The boundary fixes values as well as keys.** The on-disk **encoding and accepted decoding** are
fixed too — double-quoted scalars, UTC whole-second `resolved_at` with an explicit `+00:00` offset,
and `LockfileError` for anything the reader cannot interpret;
`fixtures/expected/lockfile_golden.yml` is the oracle both ports assert against. `pin/lockfile.py`
and `pin/lockfile.ts` state the grammar normatively; neither delegates scalar style or timestamp
tolerance to its YAML library.

**Amendment (docs/issues/23, item 3 and item 4):** "neither delegates ... timestamp tolerance to
its YAML library" was the stated invariant but not, until now, the actual behavior of the
**reader** — `_decode_timestamp` called `datetime.fromisoformat` directly, which accepts several
spellings (a space separator, a colonless or minuteless offset, a comma decimal, basic format, a
non-`:00` UTC offset like `+00:00:00`) that TypeScript's `TIMESTAMP_RE` rejects. Both readers now
check the same named regex (`_TIMESTAMP_RE` / `TIMESTAMP_RE`) before either
`datetime.fromisoformat` or a ruamel `TimeStamp` gets a say, closing the reader to exactly the
grammar rule 7 in `pin/lockfile.py` names. The same principle extended to **keys**: a `uses`
string that would be misread as a different YAML scalar type unquoted (a bool/null keyword, an
int, a float) is now quoted by an explicit predicate (`_key_needs_quoting` /
`needsQuoting`) shared, byte-for-byte the same regex, across both ports, rather than left to each
YAML library's own quoting heuristic (ruamel single-quotes such a key; the TypeScript `yaml`
package double-quotes it). No `uses:` string produced by normal ghagen usage triggers this — every
real ref contains `/`, `@`, or a `docker://` prefix — so it is latent, reachable only by
constructing a `Lockfile` directly through the public API.

**The rule covers tag parsing as well as ref parsing.** `find_latest_tag` used to return a string
it had already parsed, so `upgrade` re-parsed it behind a `parse(...) is None` guard that could
never fire — this shape, one level down. `latest_bump` / `latestBump` returns a `Bump` of parsed
values instead (ADR-0008). Any pin stage that hands a caller a string it has already parsed is
re-growing the same defect.
