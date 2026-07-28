# 04 — Pin engine threads parsed UsesRefs instead of strings

**Status:** proposed | **Ports:** both | **Depends on:** —

## Problem

`collect` already parses every `uses:` occurrence into a `UsesRef` (it has to —
that is how it knows a ref is Pinnable), and then throws the parse away, handing
the engine bare strings. The engine re-parses the same strings, guarding each
re-parse against a `None`/`null` that provably cannot happen. The parsed value
round-trips string → `UsesRef` → string → `UsesRef` for no reason.

**The parse is discarded at the seam.** `iter_uses_sites` yields a `UsesSite`
holding `ref: UsesRef` (`packages/python/src/ghagen/pin/sites.py:39`, and `uses:
str` at `:42`). `collect_uses_refs` reads `site.ref.is_pinnable` but returns
`site.uses` — the string — as a `set[str]`
(`packages/python/src/ghagen/pin/collect.py:13,27`). The TS collector is the same
shape: it reads `site.ref.isPinnable` and adds `site.uses` to a `Set<string>`
(`packages/typescript/src/pin/collect.ts:17-28`).

**The engine re-parses what collect already parsed.** Verified call sites of
`UsesRef.parse` inside the engine, each with its own null-guard:

- Python `engine.py`: line **99** (`pin`), **227** (`upgrade` version grouping),
  **279** (`upgrade` lockfile check), **302** (`upgrade` apply). Four sites.
- TS `engine.ts`: line **86** (`pin`), **228**, **285**, **313** (same three
  `upgrade` stages). Four sites.

Every one of these is dead-defensive: a string only reaches the engine because
`collect` added it, and `collect` only adds strings for which
`iter_uses_sites` already returned `UsesRef.parse(value) is not None`. So
`UsesRef.parse(uses)` in the engine **never** returns `None`. The
`if parsed is None: continue` / `if parsed === null` branches at 99-104, 227-232,
279-281, 302-305 (Python) and 86-90, 228-231, 285-288, 313-316 (TS) are
unreachable. There is no test for any of them (grep for `skipping` / `not a
pinnable` / `malformed` in `test_engine.py` and `engine.test.ts` finds nothing).

**Two entry stacks reach the same traversal.** `collect` and `upgrade` walk
`app.documents()` and call `iter_uses_sites` per document; `pinTransform` walks a
single Document via `iter_uses_sites` and re-checks `!site.ref.isPinnable`
(`transform.py:41`, `transform.ts:36`). These are not duplicates to merge — pin
runs per-document at synth time while collect aggregates across the whole App —
but they confirm `UsesSite` is the one traversal, and that its parsed `ref` is
the value everyone actually wants.

## Current interface

Python:

```python
def collect_uses_refs(app: App) -> set[str]:  # returns authored strings
```

TypeScript:

```ts
export function collectUsesRefs(app: App): Set<string>;  // returns authored strings
```

Consumers then re-derive structure. In `pin`:

```python
for uses in sorted(to_resolve):
    parsed = UsesRef.parse(uses)          # re-parse
    if parsed is None:                     # dead guard
        report.warnings.append(...); continue
    sha = client.resolve_ref(parsed.owner, parsed.repo, parsed.ref)
    lockfile.set(uses, PinEntry(sha=sha, resolved_at=now))
```

Three of `upgrade`'s stages do the same re-parse-and-guard dance.

## Proposed interface

`collect` returns **parsed, deduplicated `UsesRef`s**. Parse failure is handled
exactly once — inside `iter_uses_sites`, where it already is — and every
downstream stage consumes typed values. Only pinnable refs are collected, as
today.

### Collected shape and dedup semantics

- **Element type:** `UsesRef` (the parsed ref). A `UsesRef` losslessly
  represents its authored string: `parse` splits `owner/repo[/path]@ref` and the
  reconstruction `action_part + "@" + ref` is byte-identical to the input, so no
  separate `uses` string need be carried alongside. Add a `uses` accessor to
  `UsesRef` so consumers that need the lockfile key (a string) stay readable.
- **Dedup key:** the **full ref string** (`ref.uses`, i.e.
  `owner/repo[/path]@ref`). This is the same key the lockfile uses, so a
  collected ref and its lockfile entry line up by construction. Two authored
  occurrences of `actions/checkout@v4` collapse to one `UsesRef`;
  `actions/checkout@v4` and `actions/checkout@v5` stay distinct (different ref
  component); `owner/repo@v1` and `owner/repo/sub@v1` stay distinct (different
  path).
- **Return type:** a `list[UsesRef]` sorted by `uses`, so the engine drops its
  top-level `sorted(refs)` calls and iteration is deterministic. (A flat list,
  not a repo-grouped map: only `upgrade`'s versions stage wants grouping, and it
  can group locally now that parsing is free — see below.)

Add to `UsesRef` (both ports):

```python
@property
def uses(self) -> str:
    """The authored `owner/repo[/path]@ref` string — the lockfile key."""
    return f"{self.action_part}@{self.ref}"
```

```ts
/** The authored `owner/repo[/path]@ref` string — the lockfile key. */
get uses(): string {
  return `${this.actionPart}@${this.ref}`;
}
```

### collect — Python

```python
def collect_uses_refs(app: App) -> list[UsesRef]:
    """Return every pinnable `uses:` ref across the app, parsed and deduped.

    Dedup is by full ref string (`UsesRef.uses`). Parse failure and the
    pinnable filter live in `iter_uses_sites` / `UsesRef`; a ref that reaches
    this list is guaranteed parseable and Pinnable.
    """
    by_key: dict[str, UsesRef] = {}
    for document in app.documents():
        for site in iter_uses_sites(document):
            if site.ref.is_pinnable:
                by_key[site.uses] = site.ref
    return [by_key[k] for k in sorted(by_key)]
```

### collect — TypeScript

```ts
export function collectUsesRefs(app: App): UsesRef[] {
  const byKey = new Map<string, UsesRef>();
  for (const document of app.documents()) {
    for (const site of iterUsesSites(document)) {
      if (site.ref.isPinnable) byKey.set(site.uses, site.ref);
    }
  }
  return [...byKey.keys()].sort().map((k) => byKey.get(k)!);
}
```

A `Map` keyed by the ref string is the dedup mechanism because TS `UsesRef` is a
class with no value-equality, so a bare `Set<UsesRef>` would not dedup. Keying by
`site.uses` (string) preserves the "dedup by full ref string" semantics.

### Engine consumers — the re-parse and its guards disappear

`pin` (Python):

```python
refs = collect_uses_refs(app)                     # list[UsesRef]
have = set(lockfile.keys())
to_resolve = refs if update else [r for r in refs if r.uses not in have]
for ref in to_resolve:                            # already sorted, already parsed
    try:
        sha = client.resolve_ref(ref.owner, ref.repo, ref.ref)
    except ResolveError as exc:
        report.errors.append(f"{ref.uses}: {exc}"); continue
    lockfile.set(ref.uses, PinEntry(sha=sha, resolved_at=now))
    report.resolved.append(ResolvedPin(uses=ref.uses, sha=sha))
```

`check_sync` — needs only strings for the set difference, so it projects
`ref.uses`:

```python
refs = {r.uses for r in collect_uses_refs(app)}
keys = set(lockfile.keys())
missing = sorted(refs - keys)
extra = sorted(keys - refs) if prune else []
```

`upgrade` — the three re-parses (227, 279, 302) and their guards all go:

```python
refs = collect_uses_refs(app)
if not refs:
    return report
ref_locations = locate_uses_refs({r.uses for r in refs}, user_files)

# versions: group locally by owner/repo — parse is already done
repo_refs: dict[tuple[str, str], list[UsesRef]] = {}
for ref in refs:
    repo_refs.setdefault((ref.owner, ref.repo), []).append(ref)
...
for ref in uses_list:
    latest_tag = find_latest_tag(ref.ref, tags)
    ...
    report.version_bumps.append(VersionBump(uses=ref.uses, current=ref.ref, ...))

# lockfile check
for ref in refs:
    entry = lockfile.get(ref.uses)
    if entry is None: continue
    current_sha = client.resolve_ref(ref.owner, ref.repo, ref.ref)
    ...

# apply
updates = {ref.uses: ref.with_sha(bump.latest) for ...}
```

The TS engine changes identically (drop `UsesRef.parse` at 86/228/285/313 and
their `=== null` guards; group by `${ref.owner}/${ref.repo}`; key the lockfile by
`ref.uses`). `locate_uses_refs` / `locateUsesRefs` keep their string interface —
`upgrade` passes `{r.uses for r in refs}` — because they grep file *contents* for
the authored string, which is what a `UsesRef` reconstructs.

### Lockfile interop is untouched

The lockfile still maps **authored `uses:` strings → SHAs**; nothing about its
on-disk format changes. `Lockfile.get` / `set` / `keys` / `prune` stay
string-keyed (`lockfile.py:61-89`), and the engine feeds them `ref.uses`. The
YAML keys stay snake_case (`pins`, `sha`, `resolved_at`) and byte-identical
across ports, so the mandatory Python↔TypeScript lockfile-format interop is
unaffected — this proposal changes only the in-memory type that flows *between
collect and the engine*, never the serialized boundary.

## What sits behind the seam

`collect` stops being a string pass-through and becomes the place where "walk
every Document, keep the Pinnable refs, dedup them, and hand back typed values
ready to resolve" lives — once, for all three engine stages. The depth it now
holds:

- **The parse result** (`owner`, `repo`, `path`, `ref`) travels with the ref
  instead of being reconstructed 3× per `upgrade`.
- **Parse-failure handling** is single-sourced in `iter_uses_sites` +
  `UsesRef.parse`; no consumer re-checks for `None`.
- **Dedup and ordering** (by full ref string) are decided at the seam, so the
  engine drops its `sorted(refs)` scaffolding.

`iter_uses_sites` remains the single traversal policy (which models carry
`uses:`, how to peel a `Commented` wrapper); `collect` is the App-level
aggregate over it. Those two are distinct layers — per-Document iteration vs.
across-App dedup — and both survive the deletion test below.

## Migration plan

Pre-1.0, clean breaks; no compat shims.

1. **Both ports — add `UsesRef.uses`** (`uses.py`, `uses.ts`). Pure accessor; no
   behaviour change.
2. **Python — change `collect_uses_refs`** return type to `list[UsesRef]` with
   dict-dedup by `site.uses`.
3. **Python — update the three engine consumers** (`pin`, `check_sync`,
   `upgrade`) to consume `UsesRef`s: delete the four `UsesRef.parse` calls (99,
   227, 279, 302) and their guards, project `ref.uses` where a string is needed
   (lockfile keys, `locate_uses_refs`, report fields).
4. **TypeScript — mirror 2-3** in `collect.ts` and `engine.ts` (drop parses at
   86/228/285/313 and their `=== null` guards).
5. **Rewrite `test_collect.py` / add `collect` assertions** to compare on
   `UsesRef`s (or `{r.uses for r in refs}`); see *Test impact*.
6. **Barrel exports** — `collect_uses_refs` / `collectUsesRefs` stay exported
   (`pin/__init__.py:52`, `index.ts:184`, `pin/index.ts:28`); only their return
   type changes.

Lockstep: steps 2-3 (Python) and step 4 (TS) land together — the invariant
"collect yields parsed, deduped, pinnable refs; the engine never re-parses" must
hold on both sides at once, even though the surface differs (`list[UsesRef]` vs
`UsesRef[]`, dict vs `Map` for dedup).

## Test impact

**Does `collect` survive the deletion test? Yes — in both ports.** Delete
`collect_uses_refs`/`collectUsesRefs` and its three responsibilities — walk
`app.documents()`, filter `is_pinnable`, dedup by ref string — reappear at all
three engine call sites (`engine.py:92,154,214`; `engine.ts:77,151,214`). That
is an earned keep, not a pass-through. The prior review framed the TS collector
as *failing* the deletion test because, as a **string** pass-through, it added
nothing beyond `iterUsesSites` — the parse it computed was thrown away and
re-derived downstream. This proposal is the resolution: by returning the parsed,
deduped refs, `collect` stops being a pass-through and earns its depth. So the
recommendation is **keep and deepen**, not fold into the iterator. (Folding it
into `iter_uses_sites` was the other option; rejected because per-Document
iteration and across-App dedup are different jobs, and the transform path wants
the un-deduped per-Document iterator.)

**Null-guards / tests that die:**

- The `if parsed is None` / `=== null` branches at all eight engine sites
  (Python 99-104, 227-232, 279-281, 302-305; TS 86-90, 228-231, 285-288,
  313-316) are deleted as unreachable. No test covers them today, so nothing
  breaks — but the `pin` "skipping … not a pinnable action reference" warning
  path (`engine.py:101-103`, `engine.ts:88`) is removed, and if either port later
  wants that warning it belongs at the *source* of unparseable strings
  (`iter_uses_sites`), not the engine.

**Rewritten — `test_collect.py`:** every assertion of the form `refs ==
{"actions/checkout@v4"}` becomes a `UsesRef` comparison. Before / after:

```python
# before
refs = collect_uses_refs(_make_app(wf))
assert refs == {"actions/checkout@v4"}

# after
refs = collect_uses_refs(_make_app(wf))
assert [r.uses for r in refs] == ["actions/checkout@v4"]
# and, now that the type is richer, assert the parse the engine relies on:
assert refs[0].owner == "actions" and refs[0].ref == "v4"
```

The `test_deduplicates` case (currently `assert len(refs) == 1`) is unchanged in
spirit — `len(collect_uses_refs(...)) == 1` — but now also pins the ordering
guarantee (sorted `list`, so `test_multiple_actions` can assert a stable order
instead of comparing sets). The skip cases (`test_skips_local`,
`test_skips_docker`, `test_skips_already_sha_pinned`, `test_skips_run_steps`,
`test_skips_commented_map_steps`) assert `refs == []` instead of `== set()`.

**Added — `uses.py` / `uses.test.ts`:** one round-trip test that
`UsesRef.parse(s).uses == s` for a plain action, a pathful reusable-workflow ref,
and a SHA-pinned ref, locking the lossless-reconstruction invariant the dedup key
depends on.

TS `collect` currently has **no dedicated test file** — it is exercised only
through `engine.test.ts`. This proposal is the moment to add `collect.test.ts`
mirroring the Python cases, closing that parity gap.

## Risks & alternatives

- **`UsesRef.uses` reconstruction must be exactly lossless**, or dedup keys and
  lockfile keys drift. It is: `parse` derives `owner`/`repo`/`path`/`ref` by
  pure string splitting with no normalization, and `action_part + "@" + ref`
  re-joins them identically (verified for plain, pathful, and reusable-workflow
  shapes). The round-trip test in *Test impact* guards it. *Alternative:* carry
  the original string alongside the `UsesRef` in a small record `(uses, ref)`.
  Rejected as redundant given losslessness, but it is the fallback if a future
  `parse` ever normalizes.
- **Richer grouping at the seam** (return `dict[(owner,repo), list[UsesRef]]`)
  was considered because `upgrade`'s versions stage groups by repo. Rejected:
  `pin` and `check_sync` want a flat list, so a grouped return would force them
  to flatten, and grouping is now a cheap local step in `upgrade` (no parse).
  The flat sorted list serves all three consumers.
- **Removing the `pin` warning path** is a small behaviour loss. It only ever
  fired for a string that could not be produced under the current traversal, so
  in practice nothing changes; documented here so a future reader does not
  reintroduce a re-parse to "restore" it.

## ADR / CONTEXT.md impact

- No existing ADR is contradicted. **ADR-0001 / ADR-0002** are untouched (this
  is pin-internal data flow, not serialization or config threading).
  **ADR-0004** (user-file tracking) is untouched — `locate_uses_refs` keeps its
  string interface.
- **Consider a short ADR: "Pin collects parsed refs, not strings."** Records
  that `collect` returns deduped `UsesRef`s, that parse failure is single-sourced
  in `iter_uses_sites`, and — critically for the cross-language mandate — that
  the **lockfile boundary stays string-keyed** (`uses` strings → SHAs,
  snake_case, identical across ports) even though the in-memory pin flow is now
  typed. This is the note that prevents someone "simplifying" the lockfile to
  store `UsesRef`s and breaking format interop.
- **CONTEXT.md (both ports):** refine the **UsesRef** entry to note it carries
  its authored `uses` string (the lockfile key) via the `uses` accessor, and the
  **UsesSite** / collect note to say collect returns *parsed, deduplicated*
  UsesRefs rather than strings. The **Lockfile** entry already states "maps
  `uses:` strings" — reinforce that the string keying is the deliberate
  cross-language interop boundary.
