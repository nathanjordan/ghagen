# 20 — Delete caller-less pin/spec surface

**Status:** proposed | **Ports:** both | **Effort:** M | **Depends on:** none — this proposal is scheduled to land **first** in the round, so [12](./12-ts-comment-geometry-module.md), [15](./15-lockfile-encoding-single-home.md), [16](./16-httpclient-transport-policy.md) and [22](./22-collapse-ts-factory-bodies.md) build on a pruned tree instead of resolving these deletions as merge conflicts

## Files involved

Twenty-three files, no new files. Eight independent items (**A**–**H** below); the `Role` column
names which one each file serves, so the orchestrator can split the landing if it wants to.

### Modified — Python source

| Path                                         | Lines | Role in this proposal                                                                                                                                                  |
| -------------------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/src/ghagen/pin/engine.py`   | 294   | **B** — delete `repo_tags_cache` (`:225-226`, `:228`, `:236`, `:238`); the guard at `:228` is always true                                                              |
| `packages/python/src/ghagen/pin/lockfile.py` | 167   | **C** — delete `merge` (`:66-68`), `contains` (`:77-79`), `__iter__` (`:88-89`); drop the now-unused `Iterator` import (`:20`); rewrite the class docstring (`:47-53`) |
| `packages/python/src/ghagen/pin/sources.py`  | 128   | **D** — scope the `sys.path` insertion to the import window (`:51-54`, `try/finally` around `:64-65`)                                                                  |
| `packages/python/src/ghagen/cli/_common.py`  | 72    | **D** — same fix at `:59-67` (the `finally` must close **after** `resolve_app` at `:67`, not after `exec_module` at `:65`); refresh the stale docstring (`:50-52`)     |
| `packages/python/src/ghagen/models/job.py`   | 226   | **F** — delete `JOB_OUTPUT_SPEC` (`:48-51`) and `JobOutput` (`:169-175`); narrow `Job.outputs` (`:204`) to `dict[str, OrRaw[str]] \| None`                             |

### Modified — TypeScript source

| Path                                             | Lines | Role in this proposal                                                                                                                                                                                                       |
| ------------------------------------------------ | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/typescript/src/models/spec.ts`         | 91    | **A** — delete `extrasPlacement` (`:73-84`); drop "extras placement" from the interface doc comment (`:53`)                                                                                                                 |
| `packages/typescript/src/emitter/yaml-writer.ts` | 480   | **A** — delete the `withinOrder` branch in `orderedEntries` (`:202-205`; **not** `:201`, which binds `orderKeys` and is consumed at `:207`); drop `extrasPlacement` from the doc comment (`:180`, `:185-187`)               |
| `packages/typescript/src/pin/engine.ts`          | 318   | **B** — delete `tagsCache` (`:234`, `:239-240`, `:250-251`); the `undefined` check at `:240` is always true. The `try/catch` at `:241-249` — including the non-`ResolveError` rethrow at `:248` — is **preserved verbatim** |
| `packages/typescript/src/pin/lockfile.ts`        | 182   | **C** — delete `merge` (`:68-73`) and `[Symbol.iterator]` (`:97-100`); rewrite the class doc comment (`:44-50`)                                                                                                             |
| `packages/typescript/src/models/job.ts`          | 428   | **E** — delete `JobOutputInput` (doc `:281-284`, declaration `:285-290`)                                                                                                                                                    |
| `packages/typescript/src/pin/index.ts`           | 46    | **H** — the versions block (`:21-27`) narrows to `type BumpSeverity` only                                                                                                                                                   |
| `packages/typescript/src/index.ts`               | 203   | **E**, **H** — drop `JobOutputInput` (`:106`) and `ParsedTag` / `parseTag` / `classifyBump` / `findLatestTag` (`:183-186`)                                                                                                  |

### Modified — tests

| Path                                              | Lines | Role in this proposal                                                                                                                                                                                                                           |
| ------------------------------------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/tests/test_pin/test_lockfile.py` | 254   | **C** — rewrite `test_merge` (`:61-75`) to the constructor; **delete** `test_merge_overwrites` (`:77-86`) as redundant with `test_set_replaces` (`:49-59`); drop the `contains` assertions (`:119-120`); drop the `iter(lf)` assertion (`:136`) |
| `packages/python/tests/test_pin/test_sources.py`  | 220   | **D** — add the `sys.path`-restoration regression test                                                                                                                                                                                          |
| `packages/python/tests/test_cli/test_common.py`   | 101   | **D** — add the peer regression test for `_load_app`                                                                                                                                                                                            |
| `packages/typescript/src/pin/lockfile.test.ts`    | 171   | **C** — `:19` becomes a second `.set()`; `:36`, `:100-115`, `:142-145` become constructor arguments; drop the `new Set(lf)` assertion (`:43`); retitle the two tests that name `merge`/`iteration` (`:16`, `:34`)                               |
| `packages/typescript/src/app.test.ts`             | 145   | **C** — one `merge` call site (`:125`)                                                                                                                                                                                                          |
| `packages/typescript/src/synth.test.ts`           | 152   | **C** — one `merge` call site (`:43`)                                                                                                                                                                                                           |
| `packages/typescript/src/pin/transform.test.ts`   | 132   | **C** — one `merge` call site (`:15`)                                                                                                                                                                                                           |

### Modified — packaging and docs

| Path                                      | Lines | Role in this proposal                                                                                                  |
| ----------------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------- |
| `packages/typescript/package.json`        | 76    | **G** — delete the `zod` dependency (`:57`)                                                                            |
| `packages/typescript/package-lock.json`   | 3202  | **G** — regenerated; `zod` is at `:18` and `:3192`                                                                     |
| `packages/typescript/CONTEXT.md`          | 119   | **A** — drop "extras placement" from the **ModelSpec** glossary entry (`:43` only; 22 owns the enclosing `:40-46`)     |
| `docs/src/content/docs/python/api/job.md` | 172   | **F** — the `outputs` row (`:37`) becomes `dict[str, str] \| None`; the `## JobOutput` section (`:105-115`) is deleted |

**Files deliberately NOT touched**, because a sibling owns them or the finding is not mine to fix:
`packages/python/src/ghagen/pin/__init__.py` (58 lines — its `__all__` (`:33-58`) contains **no**
versions symbols, so **H** has no Python half and there is nothing here to edit);
`packages/typescript/src/pin/github.ts` (313 lines — four _over-exported_ helpers, an issue rather
than a proposal; see _Risks & alternatives_); `docs/specs/0004-unified-root-discovery.md` (a landed
spec whose `:165` prediction the implementation diverged from — a historical record, not a file to
correct).

## Problem

Both ports carry surface that no caller reaches. It is not one kind of dead surface, and treating
it as one kind is how a deletion proposal deletes something live. Three distinct kinds are present:

1. **Surface that is dead because nothing ever needed it.** A `ModelSpec` field with zero setters
   in 27 specs; a barrel re-export of four symbols nobody imports; an npm dependency with zero
   importers; a TypeScript interface reachable from no type. The **deletion test** returns
   _nothing_ for each: delete it and no complexity reappears anywhere, because there is no `anywhere`.
2. **Surface that is dead because the implementation makes it unreachable.** A per-repo tag cache
   whose keys are unique by construction, so the cache is written once and read once, immediately.
   This one is a _provable_ dead branch, not a survey observation, and both ports have it.
3. **Surface that is redundant rather than unreached.** Three `Lockfile` members that each spell an
   operation the class already spells another way. Their callers are real — they are all tests —
   so "delete it" here means "rewrite nine call sites onto the surviving spelling", not "delete it
   and nothing happens". This proposal counts those rewrites explicitly rather than claiming a
   free deletion.
4. **Surface that is worse than dead — it is live and wrong.** Python's `JobOutput` models a
   `{description, value}` job output that `schema/workflow_schema.json` forbids, and a user can
   reach it today. A `sys.path` insertion in two Python loaders is never removed, so every config
   load permanently widens the module search path of the host process.

The last kind is the reason this document is not a pure deletion sweep. Item **D** is a **leak to
fix**, not surface to delete: the insertion is load-bearing during the import and only wrong
afterwards. Deleting it would break user configs that import sibling helpers; the fix is to give it
a lifetime.

Landing first matters, but for a narrower reason than an earlier draft of this document claimed,
and the corrected boundaries are worth stating up front because five downstream proposals build on
the tree this one prunes:

- **`pin/lockfile.test.ts` — real, and the reason `20 → 15` is an order edge.** My `merge` rewrite
  at `:142-145` sits inside `:139-152`, the byte-identity test 15 explicitly marks **Kept**
  (`15-lockfile-encoding-single-home.md:434-435`). 15 preserves that block verbatim, so it will
  _not_ incidentally rewrite the `merge` call; if I land second the constructor rewrite has to be
  done by hand against a block 15 has already declared frozen. My other rewrite at `:100-115` is in
  the same `it()` (`:97-137`) that 15 edits at `:120` — different lines, one block.
- **Both TypeScript barrels** (`src/index.ts`, `src/pin/index.ts`), which 16 also edits.
- **`packages/typescript/package.json` and `package-lock.json`**, shared with 14 — a real conflict,
  but an unordered one; see _Risks & alternatives_.
- **`pin/engine.py` / `pin/engine.ts` are NOT a reason to sequence.** My regions and 14's are
  disjoint in both ports: Python ends at `engine.py:238` and 14 begins at `:241`; TypeScript ends at
  `engine.ts:251` and 14's first changed line is `:254`. Nobody should serialize the round on this
  edge.

## Current interface

Each item carries an independent verdict. **DEAD** = no caller anywhere, verified by grep across
both ports, tests, `docs/`, `.github/` and `schema/`. **REDUNDANT** = callers exist, but every one
of them can say the same thing through surface that stays. **ALIVE** = reachable today; the citation
says how.

### A. `ModelSpec.extrasPlacement` (TypeScript) — **DEAD**

Declared at `packages/typescript/src/models/spec.ts:73-84`:

```ts
  /**
   * Where `meta.extras` land relative to the ordered keys.
   * …
   */
  readonly extrasPlacement?: "afterOrdered" | "withinOrder";
```

The only site that reads it is `orderedEntries` in
`packages/typescript/src/emitter/yaml-writer.ts:202`:

```ts
const orderKeys = model.spec.order.keys; // :201 — LIVE, consumed at :207
if ((model.spec.extrasPlacement ?? "afterOrdered") === "withinOrder") {
  // :202
  const pool = [...new Set([...dataKeys, ...extrasKeys])]; // :203
  return orderExplicit(pool, orderKeys).map((key) => [key, valueOf(key)]); // :204
} // :205
```

The deleted range is `:202-205`. `:201` binds `orderKeys`, which the surviving `afterOrdered` path
consumes at `:207` — deleting it would be a compile error, and an earlier draft of this document got
that range wrong.

**Setters: zero.** Every `ModelSpec` literal in the port lives in one of eight files
(`models/{action,container,image-snapshot,job,permissions,step,trigger,workflow}.ts`); grepping all
eight for `extrasPlacement` returns nothing. Repo-wide there are exactly five source hits: the
declaration (`spec.ts:84`), the reader (`yaml-writer.ts:202`), two doc comments (`spec.ts:53`,
`yaml-writer.ts:180`+`:185-187`) and one glossary line (`typescript/CONTEXT.md:43`). **Tests: zero**
— the `withinOrder` body at `:203-204` is untested dead code, not merely unused config.

**Python has no peer field at all.** `packages/python/src/ghagen/models/spec.py:39-41` declares
`yaml_keys`, `order` and `present_null_when_empty` and stops. So the only reachable consequence of
ever setting `extrasPlacement` would be TypeScript emitting a key order Python cannot reproduce —
i.e. a parity break, in a port pair whose parity is enforced by ten shared golden fixtures
(`fixtures/expected/*.yml`).

**This reverses a risk proposal 06 explicitly accepted, and that has to be argued, not assumed.**
`06-close-modelspec-escape-hatches.md:318` reads, verbatim:

> **Risk: `extrasPlacement`/`dynamicKeys` add spec surface few models use.** Accepted — each is
> optional with a behaviour-preserving default, and each replaces a _harder-to-see_ bespoke code path
> with a _visible_ declaration.

The acceptance bundled two fields, and one year-half later they have diverged completely.
`dynamicKeys` acquired its adapter — `MATRIX_SPEC` sets it at `job.ts:79`, read at `_base.ts:355` —
and is **not** touched here. `extrasPlacement` did not, and the reason is specific rather than
accidental: `06:155-159` named its intended adapter outright — "lets the one model that wants
interleaving (`On`) get it declaratively" — and `ON_SPEC` shipped with `order: { kind: "alphabetical" }`
(`trigger.ts:463`) instead. Under `alphabetical`, `extrasPlacement` is moot _by its own
documentation_ (`spec.ts:81-82`: "Under `alphabetical` order this field is moot"). The single
candidate adapter took the other road on the day 06 landed, and no other has appeared since.

**Open — Phase 3 decision:** whether to reverse `06:318`'s accepted risk one round later, or to
leave `extrasPlacement` declared until a spec asks for it. The evidence for reversal is above; the
decision is the user's.

### B. Per-repo tag cache in both pin engines — **DEAD (provably)**

`packages/python/src/ghagen/pin/engine.py:221-238`:

```python
        repo_refs: dict[tuple[str, str], list[UsesRef]] = {}
        for ref in refs:
            repo_refs.setdefault((ref.owner, ref.repo), []).append(ref)

        # Per-repo tag cache stays engine-local.
        repo_tags_cache: dict[tuple[str, str], list[str]] = {}
        for (owner, repo), repo_ref_list in sorted(repo_refs.items()):
            if (owner, repo) not in repo_tags_cache:
                …
                repo_tags_cache[(owner, repo)] = tags

            tags = repo_tags_cache[(owner, repo)]
```

I verified the "unique by construction" argument rather than restating it. `repo_refs` is a `dict`
keyed by `(owner, repo)`; `sorted(repo_refs.items())` yields **each key exactly once**, because that
is what iterating a mapping means. Therefore the guard at `:228` is true on every iteration, the
write at `:236` happens on every iteration, and the read at `:238` reads back the value written two
lines above. `repo_tags_cache` never records a hit — it is a one-element-lifetime holding variable
wearing the name of a cache. Both caches are also **function-local** (`engine.py:226`,
`engine.ts:234`), rebuilt on every `upgrade()` call, so no repeat invocation and no multi-source
sweep can produce a hit either. The number of `list_tags` API calls is unchanged at one per repo.

TypeScript is the same shape at `packages/typescript/src/pin/engine.ts:225-251`, with `Map` in place
of `dict`:

```ts
    const tagsCache = new Map<string, string[]>();          // :234
    for (const [key, repoRefList] of [...repoRefs.entries()].sort(…)) {
      const [owner, repo] = key.split("/", 2) as [string, string];
      let tags = tagsCache.get(key);                        // :239
      if (tags === undefined) {                             // :240
```

`repoRefs` is a `Map` keyed `` `${owner}/${repo}` `` (`:227`), so `tagsCache.get(key)` at `:239` is
`undefined` on every iteration and the `:250` write is never read.

**What must survive the deletion.** `engine.ts:241-249` is a `try/catch` whose catch discriminates:
`ResolveError` becomes a warning and a `continue` (`:244-247`), and **anything else is rethrown**
(`:248`). No test covers that rethrow in either port. It is easy to lose while collapsing the
surrounding `if`, and losing it would silently convert every non-`ResolveError` transport failure
into a skipped repo. The Python peer is narrower — `except ResolveError` (`engine.py:231`) already
lets other exceptions propagate — but the TypeScript half needs the rethrow written back by hand.

This is dead **implementation**, not dead interface — it costs no caller anything, but it makes the
`upgrade()` body claim a caching invariant it does not have. A maintainer reading `:228` reasonably
concludes tag listing is deduplicated across a repeated repo, which is a claim about
`collect_uses_refs`'s output that this code does not actually depend on.

### C. `Lockfile`'s collection facade — **partly REDUNDANT**

I audited the class member by member in both ports rather than judging the facade as a unit,
because it is not uniformly dead — and none of the three deletions is caller-_less_. Every one has
test callers that this proposal rewrites.

Python (`packages/python/src/ghagen/pin/lockfile.py`), TypeScript
(`packages/typescript/src/pin/lockfile.ts`):

| Member                           | Production callers                                         | Test callers                                                                                                                              | Verdict              |
| -------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| `get` / `get`                    | `engine.py:266`, `engine.ts:278`, `lockfile.ts:170`        | yes                                                                                                                                       | **KEEP**             |
| `set` / `set`                    | `engine.py:105`, `engine.ts:95`                            | yes                                                                                                                                       | **KEEP**             |
| `prune` / `prune`                | `engine.py:109`, `engine.ts:100`                           | yes                                                                                                                                       | **KEEP**             |
| `keys` / `keys`                  | `engine.py:95`, `:151`; `engine.ts:153`, `lockfile.ts:167` | yes                                                                                                                                       | **KEEP**             |
| — / `has`                        | `engine.ts:81`, `:151`                                     | yes                                                                                                                                       | **KEEP**             |
| `__contains__` / —               | none                                                       | `test_engine.py:169`, `test_lockfile.py:101-102`, `:121-122`                                                                              | **KEEP** (see below) |
| `__len__` / `size`               | none                                                       | `test_lockfile.py:47`, `:59`, `:74`, `:137`, `:219`, `:225`; `lockfile.test.ts:21`, `:23`, `:31`, `:94`, `:133`                           | **KEEP** (see below) |
| `merge` / `merge`                | **none**                                                   | `test_lockfile.py:67`, `:83`; `lockfile.test.ts:19`, `:36`, `:100`, `:142`; `app.test.ts:125`; `synth.test.ts:43`; `transform.test.ts:15` | **DELETE**           |
| `contains` / —                   | **none**                                                   | `test_lockfile.py:119-120`                                                                                                                | **DELETE**           |
| `__iter__` / `[Symbol.iterator]` | **none**                                                   | `test_lockfile.py:136` (`set(iter(lf))`), `lockfile.test.ts:43` (`new Set(lf)`)                                                           | **DELETE**           |

Three findings drive the split.

**`merge` is redundant with the constructor, not with nothing.** Both constructors already accept
exactly what `merge` accepts — `Lockfile(pins: Mapping[str, PinEntry] | None)` at `lockfile.py:55`,
`new Lockfile(pins?: Map | Iterable<readonly [string, PinEntry]>)` at `lockfile.ts:54`. `merge` is
`dict.update` (`lockfile.py:68`) and a two-line `Map.set` loop (`lockfile.ts:69-72`). Apply the
deletion test: delete it and complexity reappears in **zero** places. But the rewrite is not nine
uniform substitutions, and saying so would be the kind of hand-wave this document exists to avoid:

- **Six are clean constructor moves** — `lockfile.test.ts:36`, `:100-115`, `:142-145`,
  `app.test.ts:125`, `synth.test.ts:43`, `transform.test.ts:15`, plus `test_lockfile.py:67` in
  `test_merge`, which becomes a two-entry constructor. (Seven, counting the Python one.)
- **One is not a bulk load at all.** `lockfile.test.ts:19` merges _after_ a `set()` on a live
  `Lockfile`, inside `it("get/set/merge/prune")` (`:16-24`). It becomes a second `.set()`, and the
  test title loses `merge`.
- **One should be deleted, not rewritten.** `test_lockfile.py:83` is `test_merge_overwrites`
  (`:77-86`): it merges a single entry onto an existing key and asserts the value replaced. That is
  precisely `test_set_replaces` (`:49-59`), which already asserts the same thing through `set`. Once
  `merge` is gone, the two tests are the same test. Delete it; **pytest drops 562 → 561.**

The TypeScript half has **four** test files, not one — `app.test.ts:125`, `synth.test.ts:43` and
`pin/transform.test.ts:15` each use it as a fixture shortcut. This widens the table but not the
work: each is one line.

**`contains` is a second spelling of `__contains__`.** `lockfile.py:77-79` and `:81-82` are the same
predicate with two names; `:119-120` is the only place the method form is used, immediately adjacent
to `:121-122` which uses the operator form on the same object inside the same test. One predicate,
one spelling; `test_contains` (`:113-122`) keeps its operator assertions and loses two lines.

**`__iter__` / `[Symbol.iterator]` are a third spelling of `keys`, and they do have callers.** An
earlier draft of this document claimed zero callers of any kind. That was false, and the correction
matters because it converts a free deletion into two assertion edits:
`test_lockfile.py:136` calls `set(iter(lf))` and `lockfile.test.ts:43` calls `new Set(lf)`, both
passing today. In each case the _preceding_ line already asserts the identical set through `keys()`
(`test_lockfile.py:135`, `lockfile.test.ts:42`), so the assertion is deleted rather than translated,
and both test bodies keep asserting everything they asserted before. Both bodies return the key
iterator (`lockfile.py:89`, `lockfile.ts:99`), which is what makes them the third spelling.

**Why `__contains__` and `__len__`/`size` stay.** Not because of how many call sites they have —
there are eleven, all in tests, and a call-site count is the wrong argument for keeping something
this document is otherwise deleting for having only test callers. The defensible ground is
**redundancy, or its absence**. Each of the three deletions above is a _second or third spelling of
an operation the class already offers_: `merge` → constructor, `contains` → `__contains__`,
iteration → `keys`. `__contains__` and `__len__`/`size` are the **only** spelling of their
operations. Deleting them does not remove a spelling, it removes the operation, and callers re-grow
it as `len(lf.keys())` and `[...lf.keys()].length` — complexity reappearing, which is the deletion
test failing. Python's `__contains__` also pairs with TS `has`, which has two live production
callers (`engine.ts:81`, `:151`), so deleting it would break the parity mandate. Recording an
explicit KEEP verdict here is deliberate: the next sweep should not re-flag them.

### D. `sys.path` leak in the Python config loaders — **ALIVE (live defect), two sites**

`packages/python/src/ghagen/pin/sources.py:51-54`:

```python
    # Add parent dir to sys.path so the config's relative imports resolve.
    parent = str(config_path.parent.resolve())
    if parent not in sys.path:
        sys.path.insert(0, parent)
```

Nothing removes it. There is no `try/finally`, no context manager, and no later `sys.path` mutation
in the module.

**The survey's causal claim does not hold, and I am correcting it.** The survey attributed the
survival of this entry to the `finally:` blocks in `packages/python/tests/test_pin/test_sources.py`.
It does not. There are two such blocks and neither touches this insertion:

- `test_sources.py:125-126` restores `sys.modules` only (`sys.modules.pop("lazy_helper", None)`).
- `test_sources.py:166-169` pops `sys.modules["vendored"]` and removes `str(site_pkg.parent)` from
  `sys.path` — but that entry was inserted by the **fixture config itself** at `test_sources.py:153`
  (`f"sys.path.insert(0, {str(site_pkg.parent)!r})\n"` inside the generated config source), not by
  `sources.py:54`. The `sources.py` insertion (the config's `tmp_path`) is restored by nobody.

This strengthens the finding rather than weakening it: the test suite is not masking the leak, it is
accumulating it.

**A second site, not in the survey.** `packages/python/src/ghagen/cli/_common.py:59-62` repeats the
pattern verbatim inside `_load_app`, and it is the path every non-`pin` CLI command takes. Its
docstring at `:50-52` still describes the old arrangement in which the import happened "here … so
`pin.track_user_files`'s `sys.modules` snapshot observes it", which `sources.py` no longer relies on.

**Live, and demonstrably shadowing.** The inserted entry goes to `sys.path[0]`, ahead of everything
including the standard library path entries that follow. Loading a config from directory _A_ leaves
_A_ at the front of the search path permanently, so a later, unrelated `import shared_helper`
anywhere in the process resolves to _A_'s copy. I confirmed this empirically: after
`track_user_files` on a config in one temporary directory, a subsequent import of a module name
present in both that directory and the intended one resolved to the config's directory
(`ORIGIN = A`); a second load of a different config **accumulated** a second entry rather than
replacing the first. The blast radius is bounded in a short-lived CLI process, and unbounded in the
562-test suite and in any host that embeds ghagen and loads more than one config.

TypeScript has no peer defect. `packages/typescript/src/pin/sources.ts` loads the config through
jiti (`:119-125`) and mutates no module search path; its one permanent process mutation is the
`module.register` ESM hook, which `:73-78` documents as deliberately permanent-but-inert.

**This is a leak to fix, not surface to delete.** The insertion must remain in place for the whole
import _and_ for `resolve_app`, because ADR-0004's Python tracking window includes App resolution:
`sources.py:63-66` snapshots `sys.modules` around both `exec_module` (`:64`) and `resolve_app`
(`:65`) precisely so a helper imported lazily inside `create_app()` is observed, and
`test_sources.py:102-126` guards exactly that. A `finally:` placed after `exec_module` would break
it. It must go after `resolve_app`.

**The two sites do not have the same line geometry, and the difference is the whole risk of this
step.** In `sources.py` the two calls are adjacent (`:64`, `:65`), so a `try` opened before `:64`
and closed after `:65` is the obvious shape. In `_common.py` they are _not_ adjacent:
`spec.loader.exec_module(module)` is `:65`, and `app, error = resolve_app(module, config_path)` is
**`:67`**, with a blank line between. A `finally` closed after `:65` — which an earlier draft of
this document specified — would close the window before `create_app()` runs, which is the precise
ADR-0004 failure this section warns against. The `_common.py` region is `:59-67`.

### E. `JobOutputInput` (TypeScript) — **DEAD**

`packages/typescript/src/models/job.ts:285-290` (doc comment at `:281-284`), re-exported at
`packages/typescript/src/index.ts:106`.

**The survey's line range was off by one** — it gave `284-290`; `:284` is the closing `*/` of the doc
comment and `export interface JobOutputInput {` is at `:285`.

It is a pure orphan: no type reaches it. `JobInput.outputs` is declared at `job.ts:320` as
`outputs?: Record<string, string>`, so the factory never accepts the interface, and no other
declaration in the port mentions it. Outside its declaration and the barrel line, the identifier
appears nowhere in the repository. The TypeDoc entry points (`docs/astro.config.mjs:140` →
`packages/typescript/src/_docs-api-job.ts`) re-export only `job, strategy, matrix, environment`, so
it is not documented either.

### F. Python `JobOutput` — **ALIVE, wrong, and documented public API**

`packages/python/src/ghagen/models/job.py:169-175`:

```python
class JobOutput(GhagenModel):
    """A job output definition."""

    SPEC: ClassVar[ModelSpec] = JOB_OUTPUT_SPEC

    description: str | None = None
    value: str
```

Unlike its TypeScript counterpart this one is reachable: `job.py:204` declares
`outputs: dict[str, OrRaw[str | JobOutput]] | None = None`, and
`docs/src/content/docs/python/api/job.md:37` and `:105-115` document it as supported input.

**The schema forbids the shape.** `schema/workflow_schema.json`,
`definitions.normalJob.properties.outputs`:

```json
{ "additionalProperties": { "type": "string" }, "minProperties": 1, "type": "object" }
```

Job output _values_ are strings. A user who writes
`Job(outputs={"url": JobOutput(description="…", value="…")})` emits
`outputs: {url: {description: …, value: …}}`, which is invalid workflow YAML. Nothing catches it:
`schema/conformance-scopes.yml` declares no `jobOutput` scope, so the conformance sweep never
compares this model against the schema.

**The shape it models already exists twice, correctly.** The `{description, value}` output does
appear in the schema — under `properties.on.oneOf[2].properties.workflow_call.properties.outputs`
and in `action_schema.json` — and both are already modelled, by `WorkflowCallOutput` and by
`ActionOutput`. `JobOutput` is a third copy of that shape, wired to the one place the schema does
not allow it. Every test that constructs a `{description, value}` output uses the correct class:
`test_integration/test_full_workflow.py:159-162` and `:321-324` use `WorkflowCallOutput`;
`test_integration/test_snapshots.py:340-343` and `test_models/test_action.py:143` use `ActionOutput`
(note there are two `test_action.py` files; this is the `test_models/` one). `Job.outputs` is a plain
`dict[str, str]` at every one of its call sites, e.g. `test_integration/test_full_workflow.py:175`.

**This is a breaking removal of documented public API, and should be labelled as one.** No test ever
constructs a `JobOutput`, and `packages/python/src/ghagen/__init__.py:27` exports `Job, Matrix,
Strategy` from the module but not `JobOutput` — so it is not _top-level_ public API. It is
nevertheless importable as `from ghagen.models.job import JobOutput` and it has a full documented
section of its own (`job.md:105-115`, with a parameter table), which is the strongest signal a
user-facing API gets in this repo. Calling it "internal" would be wrong. Pre-1.0 makes the break
permissible, not invisible: the removal belongs in the changelog as a breaking change, and the
`job.md` deletion is part of the same commit, not a follow-up.

### G. `zod` (TypeScript dependency) — **DEAD**

`packages/typescript/package.json:57` declares `"zod": "^4.3.6"`;
`packages/typescript/package-lock.json:18` (root `dependencies` mirror) and `:3192`
(`node_modules/zod`) carry it. **Importers: zero** — no `from "zod"`, `from 'zod'` or
`require("zod")` anywhere in `packages/`, `scripts/` or `docs/` outside `node_modules`.
`docs/package-lock.json` does contain `zod`, but transitively, via the astro/starlight tree; it is
not a declared dependency of anything here and is correctly absent from the table above.

It was orphaned by `5e9b944` ("refactor(config): unify root discovery on ancestor walk; fix subdir
CLI"), whose `--stat` shows `packages/typescript/src/_config-schema.ts | 19 -` and
`packages/typescript/src/_yaml-config.ts | 32 -` — the only two files that ever imported it, both
deleted whole. The replacement is hand-rolled typed-result validation in `config.ts` (`+74`), the
approach ADR-0007 records. Proposal 09 independently reached the same conclusion and routed the
removal here (`09-construction-time-validation-parity.md:545-547`).

Worth noting for the record: `docs/specs/0004-unified-root-discovery.md:165` planned the opposite —
"The zod schema itself stays: it is load-bearing" — and `:173` described relying on zod's
unknown-key stripping. The landed commit diverged from its own spec. That is a stale prediction in a
historical document, not a file to edit.

### H. Four caller-less TypeScript `pin` barrel exports — **DEAD**

The survey reported "four caller-less TypeScript exports in the pin area" without a list. They are
`ParsedTag`, `parseTag`, `classifyBump` and `findLatestTag`, re-exported from
`packages/typescript/src/pin/index.ts:21-27` and again from `packages/typescript/src/index.ts:183-186`.

I identified them by elimination and then confirmed the identification against 14's own scope
section, which describes its `pin/index.ts` and `index.ts` rows as a "no-op if 20 already removed
the other four symbols" (`14-versions-owns-comparison.md:615-620`) — leaving `BumpSeverity`, which
stays because `UpgradeReport.versionBumps[].severity` (`engine.ts:164`) is public engine surface.

Each of the four is used **only** inside `packages/typescript/src/pin/` — `engine.ts:21` imports
`parseTag`, `classifyBump` and `findLatestTag` directly from `./versions.js`, and `versions.test.ts`
covers them. Outside `pin/` they appear in exactly one place each: the barrel re-export list. No
consumer, no test, no doc.

**Deleting them restores parity rather than breaking it.** `packages/python/src/ghagen/pin/__init__.py`
exports **no** versions symbols at all — its `__all__` (`:33-58`) lists no `parse_tag`, no
`ParsedTag`, no `classify_bump`, no `find_latest_tag`. The current TypeScript barrel is the
asymmetric side, and **this item therefore has no Python half**: `pin/__init__.py` is not in the
table and is not edited.

## Proposed interface

### A — `ModelSpec` loses one optional field

```ts
export interface ModelSpec {
  readonly kind: ModelKind;
  readonly fieldMap: Readonly<Record<string, string>>;
  readonly order: OrderMode;
  readonly wrap?: Readonly<Record<string, WrapRule>>;
  readonly dynamicKeys?: boolean;
  readonly presentNullWhenEmpty?: readonly string[];
}
```

`orderedEntries` loses its middle branch. `:201` stays; `:202-205` go:

```ts
  const orderKeys = model.spec.order.keys;
  const entries: [string, unknown][] = orderExplicit(dataKeys, orderKeys).map(…);
  for (const key of extrasKeys) {
    entries.push([key, extras[key]]);
  }
  return entries;
```

Extras are appended after the ordered keys — which is what every spec in both ports already gets,
and what Python does unconditionally.

### B — the tag loop states what it does

Python:

```python
        for (owner, repo), repo_ref_list in sorted(repo_refs.items()):
            try:
                tags = client.list_tags(owner, repo)
            except ResolveError as exc:
                report.warnings.append(f"failed to list tags for {owner}/{repo}: {exc}")
                continue
```

TypeScript needs the binding written out rather than described, because a `const tags` declared
inside the `try` is not in scope at `:254` where `findLatestTag(ref.ref, tags)` reads it, and because
the non-`ResolveError` rethrow must survive:

```ts
    for (const [key, repoRefList] of [...repoRefs.entries()].sort(([a], [b]) => a.localeCompare(b))) {
      const [owner, repo] = key.split("/", 2) as [string, string];
      let tags: string[];
      try {
        tags = await client.listTags(owner, repo);
      } catch (err) {
        if (err instanceof ResolveError) {
          report.warnings.push(`failed to list tags for ${key}: ${err.message}`);
          continue;
        }
        throw err;
      }

      for (const ref of repoRefList) {
        …
      }
    }
```

`let tags: string[];` is definitely-assigned at the loop body below, because every path through the
`catch` either `continue`s or throws; I compiled this shape under `--strict` to confirm it rather
than assuming TypeScript's control-flow analysis would cooperate.

The deduplication the cache pretended to provide is provided by `repo_refs` / `repoRefs` being a
mapping — one network call per repo, which is the actual invariant.

### C — `Lockfile` keeps one spelling per operation

Python: `get`, `set`, `prune`, `keys`, `__contains__`, `__len__`.
TypeScript: `get`, `set`, `prune`, `keys`, `has`, `size`.

Bulk load moves to the constructor, which already supports it:

```python
lf = Lockfile({"actions/checkout@v4": PinEntry(sha=…, resolved_at=…)})
```

```ts
const lf = new Lockfile([["actions/checkout@v4", { sha, resolvedAt }]]);
```

Incremental load — the one site (`lockfile.test.ts:19`) that merges onto a live object — moves to
`set`:

```ts
lf.set("actions/setup-node@v4", { sha: "b".repeat(40), resolvedAt: new Date() });
```

### D — the `sys.path` insertion gets a lifetime

Both loaders take the same shape, around different line ranges. `sources.py` (`:51-65`):

```python
    parent = str(config_path.parent.resolve())
    inserted = parent not in sys.path
    if inserted:
        sys.path.insert(0, parent)

    module = importlib.util.module_from_spec(spec)

    before = set(sys.modules.keys())
    try:
        spec.loader.exec_module(module)
        app, error = resolve_app(module, config_path)
    finally:
        if inserted and sys.path and sys.path[0] == parent:
            del sys.path[0]
    after = set(sys.modules.keys())
```

Two invariants, both load-bearing:

- **Idempotency** — remove only if this call inserted. A caller who already had the directory on
  `sys.path` (a `conftest.py`, a user's own `sys.path` manipulation, a repeat load of the same
  config) keeps it.
- **Position** — remove by index after checking identity, not `sys.path.remove(parent)`, so a config
  that inserts its _own_ copy of the same string during import is not silently robbed of it.

The window still closes **after** `resolve_app`, preserving ADR-0004's Python tracking window.

`cli/_common.py` (`:59-67`) takes the same shape, and its `try` must span **two non-adjacent
statements** — `spec.loader.exec_module(module)` at `:65` and `app, error = resolve_app(module,
config_path)` at `:67`:

```python
    parent = str(config_path.parent.resolve())
    inserted = parent not in sys.path
    if inserted:
        sys.path.insert(0, parent)

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        app, error = resolve_app(module, config_path)
    finally:
        if inserted and sys.path and sys.path[0] == parent:
            del sys.path[0]

    if error is not None:
        typer.echo(f"Error: {error.message}", err=True)
        raise typer.Exit(1)
```

The `typer.Exit` path stays outside the `try`, so the entry is already removed by the time the CLI
renders the error. Its docstring (`:50-52`) is refreshed to describe the lifetime rather than the
obsolete snapshot arrangement.

### E, F — job outputs converge on the string the schema declares

TypeScript: `JobOutputInput` is deleted; `JobInput.outputs?: Record<string, string>` (`job.ts:320`)
is already correct and unchanged.

Python: `JOB_OUTPUT_SPEC` and `JobOutput` are deleted and `Job.outputs` becomes:

```python
    outputs: dict[str, OrRaw[str]] | None = None
```

The two ports then declare the same thing, and both declare what
`definitions.normalJob.properties.outputs` allows. `OrRaw` is kept: `Raw` is the documented escape
hatch for emitting an expression verbatim, and dropping it here would be an unrelated behaviour change.

### G, H — the public surface of the package shrinks

`zod` leaves `dependencies`. The `pin` barrel and the root barrel stop advertising `ParsedTag`,
`parseTag`, `classifyBump`, `findLatestTag` and `JobOutputInput`. The symbols themselves survive as
`pin`-internal exports from `versions.ts`, which is where `engine.ts:21` already imports them from.

## What sits behind the seam

Nothing new goes behind a seam here; the question is which of these _were_ seams.

`extrasPlacement` was written as one — a spec field is a seam by construction, a place a model can
alter Emitter behaviour without editing the Emitter. It has **zero adapters**. The house rule is
"one adapter = hypothetical seam; two adapters = real seam"; a zero-adapter seam is not even
hypothetical, it is a branch. And because Python declares no peer field, the seam could not be
satisfied symmetrically even if a spec wanted it: the first adapter would break the port parity the
ten shared golden fixtures enforce. That is the distinguishing test this proposal applies throughout —
**is this surface dead today but a deliberate seam awaiting a second adapter, or dead because
nothing ever needed it?** `extrasPlacement` is the second: the design it anticipated (a spec that
wants extras interleaved with an explicit order) had exactly one named candidate, `On`, and `On`
chose `alphabetical` instead (`trigger.ts:463`), under which the field is inert by construction.
The rule generalises, and is worth recording for future rounds: **a proposal that wants declarative
extras placement must arrive with a caller.** A field whose only documented adapter opted out is not
a seam awaiting adoption; it is a branch awaiting deletion.

The `Lockfile` facade is the case where the answer genuinely splits, which is why the audit is per
member rather than per class. `Lockfile` as a **Module** is deep and earns its keep: a small
interface (six members) over a real invariant — "a lockfile only ever holds valid entries", stated
at `lockfile.py:47-53` and `lockfile.ts:44-50` and enforced by routing every mutation through `set`
and `prune`. Nothing here proposes dissolving it. What is deleted is the part of its interface that
is _not_ leverage: `merge` (the constructor's job), `contains` (`__contains__`'s job), iteration
(`keys`'s job). Depth is leverage per unit of interface; removing three redundant spellings raises
it without touching the implementation. The **Locality** benefit is concrete for proposal 15, which
single-homes this class's on-disk encoding: three fewer members is three fewer things whose error
mode 15 has to decide about.

The tag cache is the inverse shape — implementation that pretends to be an optimization. Applying
the deletion test to `repo_tags_cache` specifically: delete it, and no complexity reappears, because
the property it existed to exploit (repeated `(owner, repo)`) is destroyed by the grouping step two
lines above it. It is not a dead seam; it is a dead invariant claim.

`sys.path` is the one place the reasoning inverts. The insertion is not surface at all — it is a
process-global side effect with no interface, and its absence of a lifetime is what makes it a
defect. Giving it a `try/finally` does not add a seam; it makes `track_user_files` and `_load_app`
**deep** in the sense that matters here: a caller can invoke them without needing to know that the
process's module search path is now different. Today that knowledge is part of the interface —
undocumented, and therefore part of the interface anyway.

## Migration plan

Pre-1.0; breaking changes are freely allowed. No deprecation shims, no re-export aliases, no
`@deprecated` markers. Seven independent steps; steps 1, 2 and 5–7 compile or do not, step 3 is
mechanical test rewriting, and step 4 is the only one with behaviour to verify.

1. **A — `extrasPlacement`.** Delete `spec.ts:73-84` and the `withinOrder` branch at
   `yaml-writer.ts:202-205` — **keeping `:201`**, which binds `orderKeys` for the surviving path at
   `:207`. Update the two doc comments that name it (`spec.ts:53`, `yaml-writer.ts:180` and
   `:185-187`) and the TS CONTEXT.md glossary entry (`:43`). TypeScript only — Python has nothing to
   delete. `tsc` proves the sweep: any surviving setter is a compile error.
2. **B — tag cache.** Delete `repo_tags_cache` (`engine.py:225-226`, `:228`, `:236`, `:238` collapse
   to the bare `try` block) and `tagsCache` (`engine.ts:234`, `:239-240`, `:250-251`). **Copy
   `engine.ts:241-249` through verbatim, rethrow included**, and declare `let tags: string[];` above
   the `try`. Behaviour-identical.
3. **C — `Lockfile`.** Delete `merge`, `contains`, `__iter__` (Python) and `merge`,
   `[Symbol.iterator]` (TypeScript); drop the `Iterator` import at `lockfile.py:20`; rewrite both
   class doc comments, which currently name `merge` and iteration explicitly. Then, in the tests:
   seven constructor rewrites, one `merge`→`set` rewrite (`lockfile.test.ts:19`), one deleted test
   (`test_lockfile.py:77-86`), two deleted `contains` assertions (`:119-120`), two deleted iteration
   assertions (`test_lockfile.py:136`, `lockfile.test.ts:43`), and two test titles that stop naming
   `merge` / `iteration` (`lockfile.test.ts:16`, `:34`).
4. **D — `sys.path`.** Apply the `try/finally` to `sources.py:51-65` and `_common.py:59-67` — note
   the different ranges; `_common.py`'s `resolve_app` is at `:67`, two lines below `exec_module`, and
   a `finally` closed after `:65` reintroduces the ADR-0004 failure. Refresh the `_common.py:50-52`
   docstring; add the two regression tests.
5. **E, F — job outputs.** Delete `JobOutputInput` (`job.ts:281-290`); delete `JOB_OUTPUT_SPEC`
   (`job.py:48-51`) and `JobOutput` (`job.py:169-175`); narrow `job.py:204`. Update
   `docs/src/content/docs/python/api/job.md:37` and delete its `:105-115` section **in the same
   commit** — this is a documented-API break and the doc must not outlive the class.
6. **G — `zod`.** Delete `package.json:57`; regenerate `package-lock.json` with
   `npm install --package-lock-only --prefix packages/typescript`. If 14 has already landed,
   regenerate on top of its result rather than merging (see _Risks & alternatives_).
7. **H — barrels.** Narrow `pin/index.ts:21-27` to `type BumpSeverity`; delete `index.ts:106` and
   `index.ts:183-186`. `packages/python/src/ghagen/pin/__init__.py` is **not** touched — it already
   exports none of these.

Gates after each step, in the order the repo defines them: `scripts/typecheck.sh all`,
`scripts/test.sh all`, `uv run ghagen check-synced`, `uv run ghagen deps check-synced`,
`PYTHONPATH=scripts uv run python -m ghagen_schema check`. `scripts/lint.sh` defaults to the `all`
scope (`scripts/lint.sh:6`) and guards the `docs/` npm toolchain on the `ts` and `all` scopes
(`:20-26`), so a bare `scripts/lint.sh` — which is what `.pre-commit-config.yaml:14,:20` and
`AGENTS.md:50-51` invoke — needs `npm ci --prefix docs` first. `scripts/lint.sh py` is ruff only and
needs nothing.

## Test impact

**Baseline: pytest 562, vitest 515. After this proposal: pytest 563, vitest 515.** Two movements,
both in Python and in opposite directions: item **C** deletes `test_merge_overwrites`
(`test_lockfile.py:77-86`), which becomes a duplicate of `test_set_replaces` once `merge` is gone
(**−1**), and item **D** adds one regression test per loader (**+2**). Net **562 − 1 + 2 = 563**.
Vitest is unchanged: item C retitles two TypeScript tests and deletes assertions inside them, but no
`it()` block. This is stated per item below, because an earlier draft of this document claimed a net
of zero, and that was wrong in both directions at once.

I ran step 4 end to end in a detached worktree at `HEAD` — the only step with a behaviour change —
and the Python suite is **562 passed** with both `try/finally` blocks in place. That is the
load-bearing result of this proposal: **no test depends on the leaked `sys.path` entry surviving the
call.** The two `finally:` blocks in `test_sources.py` (`:125-126`, `:166-169`) continue to pass
unchanged, consistent with the finding above that they restore `sys.modules` and a
_fixture-inserted_ path entry, not this one.

Per item:

- **A** — no test touches `extrasPlacement`; the deleted `yaml-writer.ts:203-204` body is untested
  today. Net test change: zero. Coverage does not drop, because there was none.
- **B** — **the regression net is not where an earlier draft said it was, and it is thinner than
  claimed.** Both ports' direct `upgrade()` tests are **single-repo**: `test_engine.py:187-251`
  (`TestUpgrade`, four cases) and `engine.test.ts:171-242` (`describe("upgrade()")`, four cases) each
  drive one `actions/checkout@v4` ref through a fake transport, so neither exercises a second
  iteration of the loop the cache sits in. The only multi-repo coverage
  in the repo is Python's CLI-level `test_cli/test_deps.py`, whose `_mock_list_tags` (`:168-174`)
  answers for both `checkout` and `setup-python`; **TypeScript has no multi-repo upgrade test at
  all.** This does not weaken the deletion — the argument for B is structural (a mapping yields each
  key once), not empirical — but it does mean the suite would not catch a botched collapse of the
  `try/catch`. Two mitigations, in order of preference: copy `engine.ts:241-249` verbatim rather
  than retyping it, and treat the missing TS multi-repo `upgrade()` case as a **test-hole finding
  for `docs/issues/`**, not as work this proposal absorbs.
- **C** — nine `merge` call sites resolve as: **seven** constructor rewrites
  (`test_lockfile.py:67`, `lockfile.test.ts:36`, `:100-115`, `:142-145`, `app.test.ts:125`,
  `synth.test.ts:43`, `transform.test.ts:15`), **one** `merge`→`set` rewrite
  (`lockfile.test.ts:19`), and **one deleted test** (`test_lockfile.py:77-86`). Four further
  assertions are deleted as exact duplicates of the line above them: the two `contains` calls
  (`test_lockfile.py:119-120`, duplicating `:121-122`) and the two iteration calls
  (`test_lockfile.py:136` duplicating `:135`; `lockfile.test.ts:43` duplicating `:42`). Nothing that
  was asserted stops being asserted. **pytest −1; vitest unchanged.**
- **D** — **two new tests, one per port-internal loader.** In `test_sources.py`: snapshot
  `list(sys.path)`, call `track_user_files` on a `tmp_path` config, assert `sys.path` is restored
  _and_ that the config's sibling helper was still importable during the call (both halves matter —
  asserting only restoration would pass if the insertion were simply deleted). In
  `test_cli/test_common.py`: the same shape around `_load_app`, and this one must assert the helper
  is importable from inside `create_app()`, not merely at config import time, so that a `finally`
  mistakenly closed after `exec_module` fails the test. Also worth one negative case: pre-insert the
  parent directory, call, assert it is **still** present — the idempotency invariant. **pytest +2.**
- **E, F** — zero test changes. No test constructs a `JobOutputInput` or a `JobOutput`.
  `test_models/test_spec.py:21-32`'s `_all_model_classes()` derives its list from `__subclasses__()`
  and adapts automatically; nothing hardcodes a model count. The conformance sweep has no
  `jobOutput` scope to drop.
- **G, H** — zero test changes; `tsc` and `vitest`'s module resolution are the proof.

**The suite gets a real improvement in one place only, and it is worth naming:** today a test can
change the module search path for every test that runs after it, from inside a helper that does not
say so. `test_sources.py` and `test_cli/test_deps.py` both load configs from `tmp_path` repeatedly
in one process. Step 4 makes test order irrelevant there, which is the kind of latent
inter-test coupling that is cheap to fix now and expensive to diagnose later.

## Risks & alternatives

**Risk: a deletion with a caller I did not find.** This is the failure mode that matters, so each
item was verified independently — grep across both `packages/`, all tests, `docs/`, `.github/`,
`scripts/` and `schema/` — rather than inherited from the survey. It is also the failure mode this
document hit once: the claim that `__iter__` / `[Symbol.iterator]` had zero callers of any kind was
false (`test_lockfile.py:136`, `lockfile.test.ts:43`), and §C now states the callers and the
rewrite. Three of the survey's premises did not survive verification either and are corrected in
place above: the `sys.path` causal claim (§D), the `JobOutputInput` line range (§E), and the
assumption that `Lockfile`'s facade is uniformly dead (§C, where two members get an explicit KEEP
verdict). `packages/typescript/dist/` is `.gitignore`d (`.gitignore:49`) and stale — it still
contains `_config-schema.js`, deleted from source by `5e9b944` — so it is evidence of nothing and is
not in the table.

**Risk: the tree was mutated mid-audit.** During authoring, proposal 22 briefly left nine
`packages/typescript/src/models/*.ts` files carrying a `defineFactory(SPEC)` prototype in the shared
checkout. Every `models/` finding here was re-verified against `HEAD` afterwards:
`git status --short` shows only untracked `docs/proposals/*.md`; `git hash-object` matches
`git rev-parse HEAD:<path>` for all nine files; `grep -rn "defineFactory" packages/typescript/src`
returns nothing. `JobOutputInput` (`job.ts:285`, `index.ts:106`), the `extrasPlacement` reader
(`yaml-writer.ts:202`), the declaration (`spec.ts:84`) and the zero-setter sweep across all eight
spec-bearing model files are **unchanged**.

**Alternative for A: keep `extrasPlacement` and add the Python peer.** Rejected. That buys symmetry
in an unused field and doubles the untested branch count. If a model ever needs extras interleaved
with an explicit order, `alphabetical` already interleaves them, and the field can come back with
its first real adapter — at which point it will be a hypothetical seam with one adapter, which is
still the weaker case, but at least a real one.

**Alternative for D: delete the `sys.path` insertion entirely.** Rejected, and this is the one place
in the document where deletion is the wrong instinct. The insertion is what makes a user config's
`import my_helper` resolve, which `test_sources.py:110-126` exercises directly. Removing it breaks
user configs. The defect is the missing lifetime, not the mutation.

**Alternative for D: `contextlib.contextmanager`.** A shared `_config_sys_path(config_path)` helper
would single-home the pattern across both call sites. Attractive, and rejected for _this_ proposal:
it introduces new shared surface in a document whose whole argument is subtraction, and the two
sites differ in both error handling (`sources.py` raises `RuntimeError`, `_common.py` renders and
raises `typer.Exit`) and line geometry (`:64-65` adjacent vs `:65`/`:67` split). Worth raising
separately if a third loader ever appears — two call sites is a hypothetical seam.

**Alternative for F: keep `JobOutput` and add schema validation that rejects it.** Rejected. That
adds a check to reject a shape ghagen itself is the only source of. Deleting the class removes the
possibility instead of policing it, and converges the two ports on one declaration.

### Findings routed elsewhere, not claimed here

**`packages/typescript/src/pin/github.ts`'s four extra exports are over-_exported_, not dead — the
characterisation in an earlier draft of this document was wrong, and 16 correctly declined them.**
`refUrls`, `isAnnotatedTag`, `commitSha` and `parseNextLink` (declared at `github.ts:270`, `:277`,
`:282`, `:294`) each have a live caller **inside their own file** — `:139`, `:146`, `:163`, `:263`
respectively. Their only outside importer is `github.test.ts:9-12`, which unit-tests all four at
`:190-220`. They appear in neither `pin/index.ts` nor `src/index.ts`, and `package.json:29-34`
publishes only `"." → ./dist/index.js`, so **they are not on the published surface at all**.
Python's peers are module-private by underscore for exactly the same reason (`_ref_urls:261`,
`_is_annotated_tag:269`, `_commit_sha:274`, `_parse_next_link:283` in `pin/github.py`), so the two
ports are **already at substantive parity**; `export` is simply ESM's only mechanism for a
test-visible module-private helper, and deleting the keyword turns four passing tests red. The
remedy is cosmetic — `/** @internal */` or a `_` prefix — and belongs in `docs/issues/`, not in this
proposal and not in 16.

**TypeScript has no multi-repo `upgrade()` test.** Established under _Test impact_ **B**. A
test-hole finding for `docs/issues/`; not absorbed here, because item B's argument does not depend
on it.

### Scope boundaries vs siblings

- **10 (delete `order` from `ModelSpec`) — `extrasPlacement` is mine in full; 10 has ceded it.**
  This was contested during authoring: 10's pre-revision text claimed `spec.ts:73-84` in its table
  (`10-delete-modelspec-order.md:30`), argued at `:202-206` and `:281-282` that the field becomes
  _unimplementable_ once `order` collapses, and asked at `:462` that "20 should not also claim it".
  Arbitration went the other way, on schedule grounds: I land **first** and 10 lands **solo and
  last** (`10` §What sits behind the seam), so a field 10 deletes at the end is a field that lives in the tree the whole
  round. 10's round-2 revision withdraws its Problem item 4, the `extrasPlacement` clause of its
  `spec.ts` row, its "loses two branches" wording, and its `typescript/CONTEXT.md:43` edit. Nothing
  further is needed from either side; the orchestrator does not need to re-decide this.
  One correction to an earlier draft of this document: my hunk is **not** a strict subset of 10's at
  line granularity — I edit `spec.ts:53`, `yaml-writer.ts:180` and `:185-187`, three doc-comment
  regions 10 never declares. It is a subset _conceptually_ (I touch neither `OrderMode` nor
  `orderExplicit`), which is what made either ownership direction safe.
- **22 (collapse the TS factory bodies) — two shared files, both resolved by region.**
  `packages/typescript/src/models/job.ts`: 22's regions are the factory bodies and their doc blocks
  (`:51-74`, `:82`, `:100-125`, `:167`, `:177-190`, `:192-236`, `:274`, `:393-400`); mine is the
  `JobOutputInput` interface at `:281-290`, which is not a factory and not a doc block 22
  re-attaches. Disjoint. `packages/typescript/CONTEXT.md`: per the round's region map 22 owns the
  **ModelSpec** entry `:40-46` and `:98`, and I own `:43` — a line _inside_ 22's block. That is a
  genuine nesting, not an adjacency: whoever lands second edits a paragraph the other has rewritten.
  My edit is the deletion of two words ("extras placement") from the declarable-rules list; if 22
  lands first it should simply drop them while rewriting, and my CONTEXT.md row becomes a no-op.
- **09 (construction-time validation parity) — one new edge, from a round-level decision.** The
  round settled 09's `imageSnapshot` grammar as a fourth declarative `ModelSpec` field
  (`patterns?: Readonly<Record<string, RegExp>>` / `Mapping[str, re.Pattern[str]]`), which puts 09
  into `models/spec.ts` and `models/spec.py` — files I also edit. The regions differ: 09 _adds_ a
  field beside `wrap`, `dynamicKeys` and `presentNullWhenEmpty`, and I _delete_ `extrasPlacement`
  (`:73-84`) between `dynamicKeys` (`:72`) and `presentNullWhenEmpty` (`:85-90`). Same interface
  body, different lines; land me first and 09 adds to a five-field interface instead of a six-field
  one. 09 also routed `zod` here explicitly (`09` §(c) One home for the version grammar: a fourth declarative ModelSpec field, bound by a shared value table) rather than claiming it.
- **12 (TS comment geometry) — disjoint, confirmed.** 12 names the collision itself
  (`12-ts-comment-geometry-module.md:506-509`): it observes that my `extrasPlacement` edit is at
  `yaml-writer.ts:202` inside `orderedEntries` (`:189-215`) and states its own work is in
  `formatYamlComment` / `fixInlineCommentSpacing` / `toYaml` (`:389-451`). Verified from my side:
  nothing in this proposal touches `yaml-writer.ts` outside `:180`, `:185-187` and `:202-205`.
- **14 (`versions` owns its comparison) — one real edge, and it is not the one either of us first
  wrote down.**
  - **`pin/engine.py` / `pin/engine.ts`: CLOSED, not an order edge.** The regions are disjoint in
    both ports. Python: my last touched line is `engine.py:238` (`tags = repo_tags_cache[…]`) and
    14's first is `:241` (`find_latest_tag`). TypeScript: my last is `engine.ts:251` (the closing
    brace of the cache `if`) and 14's first is `:254` (`findLatestTag`). In particular
    **`engine.ts:243-249` — the `try/catch` with the untested non-`ResolveError` rethrow — is not
    touched by 14 at all**, so its preservation is entirely my responsibility and nobody should
    serialize the round waiting for 14. Either order works; git resolves it.
  - **`packages/typescript/package.json` + `package-lock.json`: real, and the one to watch.** I
    delete `package.json:57` (`zod`, in `dependencies`); 14 deletes `:55` (`semver`, same object)
    and `:62` (`@types/semver`, in `devDependencies`). Three lines across two objects, five lines
    apart at the closest — the `package.json` conflict is mechanical. The `package-lock.json`
    conflict is not: **both of us regenerate a 3202-line generated file, and a regenerated lockfile
    does not merge.** Whichever lands second must discard its own lockfile diff and re-run
    `npm install --package-lock-only --prefix packages/typescript` on top of the first one's result.
    14 does list both files in its own table (`14` §Modified) but does not name this interaction; it is
    documented here so the orchestrator has it in one place.
  - **Barrels:** 14 has written its side assuming I land first (`14` §The shared table calls its
    `pin/index.ts` / `index.ts` rows a no-op if 20 removed the four symbols).
- **15 (single-home the Lockfile's encoding) — the sources are disjoint; one test file is not, and
  the reason is the opposite of what an earlier draft said.** My `merge` removals in
  `packages/typescript/src/pin/lockfile.test.ts` sit at `:100-115` and `:142-145`. 15's declared
  regions in that file are `:154-170` (the "Python-written lockfile" literal it replaces with the
  golden) and `:120` (the header assertion) — plus `:139-152`, which `15` §(b) The encoders and decoders, single-homed and explicit marks explicitly
  **Kept**. So:
  - `:142-145` is **inside a block 15 preserves verbatim**. 15 will not rewrite that `merge` for me;
    if 15 lands first, the rewrite has to be applied by hand to a block 15 has frozen. **`20 → 15`
    stands as an order edge — for this reason, not because 15 rewrites the cases.**
  - `:100-115` is in the same `it()` (`:97-137`) as 15's `:120` edit — different lines, one block, a
    mechanical conflict at worst.
  - Neither of my sites is in `:154-170`.
    The Python half is genuinely disjoint: my `test_lockfile.py` edits are at `:61-86`, `:119-120` and
    `:136`, and 15's region begins at `:240`. In `lockfile.py` / `lockfile.ts` themselves we do not
    overlap at all — I delete class members, 15 rewrites `read_lockfile` / `write_lockfile` and the
    error mode.
- **16 (transport policy in `HttpClient`) — the suspected edge is half real, and the Python half is
  DROPPED.** **CONFIRMED** on `packages/typescript/src/index.ts` and
  `packages/typescript/src/pin/index.ts`: I edit `index.ts:106` and `:183-186`, and
  `pin/index.ts:21-27`, while 16 flips `type HttpResponse` to a value export in the same two barrels
  — `pin/index.ts:17` and `index.ts:179`, single-token edits its own table marks "**Confirms the
  barrel edge**" (`16-httpclient-transport-policy.md:14-15`). Same two files, adjacent-but-different
  lines: a mechanical conflict, not a semantic one, and my deletions at `pin/index.ts:23-26` sit six
  lines below 16's `:17`. **DROPPED** on `packages/python/src/ghagen/pin/__init__.py`: 16's table
  claims the edge there (`16` §Files involved), but I do not touch that file and there is nothing in it for me to
  touch — its `__all__` (`:33-58`) exports no versions symbols, so item **H** has no Python half.
  That row is 16's alone. Separately, the four `pin/github.ts` helpers I once offered to 16 are not
  16's either — see _Findings routed elsewhere_ above.
- **17 (upgrade-report renderer) — sequential, not conflicting.** 17 reshapes the `deps upgrade`
  path downstream of `upgrade()`; my edits to that path are the `engine.py` / `engine.ts` cache
  deletion (item B) and the `_common.py` loader fix (item D), both upstream of the renderer. 17
  acknowledges the split from its side (`17` §Test impact). It does also edit `upgrade()`'s report literal
  (`engine.py:207-216`), which is above my region and does not change the verdict: disjoint,
  five to fourteen lines apart. Landing me first means 17 moves already-pruned code, and item D
  should land before 17 regardless, since 17 reshapes the path that calls `track_user_files`.
- **11, 13, 18, 19, 21, 23, 24 — no file overlap.** Note for **11** (the shared spec-surface
  conformance table): 11's document already records both `JobOutputInput` (`11` §Migration plan) and Python
  `JobOutput` (`11` §Migration plan) as parity defects it observes but does not fix; this proposal fixes
  them, so those two rows in 11's table should resolve to "already converged".

## ADR / CONTEXT.md impact

- **No ADR is contradicted, and one is actively defended.** ADR-0004
  (`docs/adr/0004-user-file-tracking-via-jiti-cache-diff.md`), with its 2026-07-28 note (`:72-76`)
  that the Python tracking window includes App resolution, is the reason item D's `finally:` is
  placed after `resolve_app` rather than after `exec_module` — in `sources.py` after `:65`, and in
  `_common.py` after `:67`. Implementation should not "tidy" either forward.
  ADR-0007 (typed config-discovery results) is reinforced by item G: deleting `zod` removes the last
  trace of the schema-validation approach that ADR-0007 replaced with errors-as-values.
  ADR-0006 (pin collects parsed refs) is what makes item B provable — `collect_uses_refs` returning
  parsed refs is why grouping by `(owner, repo)` is a free local step and a cache buys nothing.
  ADR-0001 (Document serialization seam) is untouched: `extrasPlacement` is not part of the seam it
  defines.
- **`packages/typescript/CONTEXT.md:43`, and only `:43`.** The **ModelSpec** glossary entry
  (`:40-46`) lists "extras placement" among the rules a spec can declare, on line `:43`. Drop those
  two words. Per the round's CONTEXT.md region map, **22 owns the enclosing `:40-46`** and **10 has
  ceded `:43`**; this is the only line in this file this proposal touches.
  `packages/python/CONTEXT.md` does not mention it and needs no edit — the asymmetry in the
  glossaries is itself evidence for item A.
- **No CONTEXT.md change for items B–H.** No domain vocabulary is added or removed: Lockfile,
  PinEntry, pin, uses-site and ModelSpec all keep their meanings; only spellings of existing
  operations go away.
- **No new ADR.** Nothing here establishes a decision worth recording — item D restores an
  invariant the code already meant to have, and the rest is subtraction. If the orchestrator wants
  the `sys.path` lifetime written down, the natural home is a sentence in ADR-0004's Consequences,
  not a new record.
- **Two entries for `docs/issues/`**, described here rather than written: the four over-exported
  `pin/github.ts` helpers (cosmetic `@internal` / `_`-prefix fix), and the missing TypeScript
  multi-repo `upgrade()` test.
