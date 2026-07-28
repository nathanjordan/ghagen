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
