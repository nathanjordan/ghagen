# 07 — Prune hypothetical seams and dead surface

**Status:** proposed | **Ports:** both (per-item scope noted) | **Depends on:** proposal 05 (unblocks the Python `app_loader` removal); cross-references proposal 04 (owns `pin/collect`)

## Problem

Several places in both ports carry the *shape* of an extension seam — an
injected loader, a re-exported helper, a per-file docs stub, a duplicated
predicate — without the second adapter that would make the seam real. The
governing rule: **one adapter is a hypothetical seam; two make it real.** A
single-adapter seam is just indirection, and it fails the **deletion test** —
removing it costs nothing a caller relied on. This proposal sweeps those,
plus genuinely dead public surface, and — crucially — records which
explorer-flagged items turn out to be *load-bearing* and must stay.

Two of the flagged items are not dead at all, and the biggest value of this
sweep is saying so before someone deletes them: `postProcess` and the
`_docs-api-*.ts` stubs. They are addressed first so the "prune" framing does
not sweep them up by momentum.

## Current interface / per-item findings

### A. `postProcess` / `post_process` — KEEP (documented public escape hatch)

**Verdict: keep. Not dead surface.** The explorer's note that it has "zero
production producers" is true but misleading: it is an *escape hatch*, so
ghagen internals are expected never to set it — the producers are users. It is
**documented public API in both ports**:

- `docs/src/content/docs/guides/escape-hatches.mdx:89-141` — a dedicated
  "postProcess — Hook into emission" section with Python and TypeScript
  examples.
- `docs/src/content/docs/python/api/step.md:49` and `workflow.md:45` list
  `post_process` as an accepted parameter.

It is exercised by real tests beyond the snapshot fixture the explorer cited
(`test_snapshots.py:191`): `test_full_workflow.py:363-396` asserts the emitted
YAML contains a `post_process`-injected key, and `test_step.py:93-97` is a
focused unit test. TS has `yaml-writer.test.ts:146` and `_clone.test.ts:40`.

Consumed at TS `yaml-writer.ts:88-90` (`model.meta.postProcess(map)`) and
Python `nodes.py:178-179` (`model.post_process(cm)`). It passes the deletion
test decisively — deleting it removes a documented user capability. **No
change.**

**Consequence for the clone machinery.** Because `postProcess` stays, the TS
clone (`_base.ts:499-514` `cloneMeta`) must keep passing the function by
reference, and `cloneModel` **cannot** move to `structuredClone`. But note the
explorer's premise — that `postProcess` is the *only* reason — is wrong on a
second count: `cloneValueInternal` (`_base.ts:433-489`) documents *two*
independent blockers, and the other one is unconditional:

- `structuredClone` "silently drops Symbol-keyed properties (would lose
  `RAW_BRAND` and `COMMENTED_BRAND`)" — `_base.ts:434-435`.
- `structuredClone` "throws on functions (would crash on `meta.postProcess`)"
  — `_base.ts:436`.

The `Raw` and `Commented` wrappers are symbol-branded (`_base.ts:85,9`) and are
core, non-optional model surface. So even in a hypothetical world where
`postProcess` were removed, `structuredClone` would still corrupt every `Raw`
and `Commented` value. The clone machinery is not unlockable by pruning
`postProcess`; that avenue is closed regardless. This is worth stating so the
idea is not re-proposed.

### B. `_docs-api-*.ts` ×9 — KEEP, load-bearing docs entry points

**Verdict: keep. Not dead, and deletion is not viable.** These are not stubs
awaiting a future TypeDoc run — they are **live entry points consumed today**.
`docs/astro.config.mjs` instantiates nine `starlight-typedoc` plugins
(`createStarlightTypeDocPlugin()` at lines 7-15), each pointed at exactly one
`_docs-api-*.ts` file as its `entryPoints` (lines 125-186). TypeDoc *is* a
dependency — in `docs/package.json` (`typedoc`, `starlight-typedoc`,
`typedoc-plugin-markdown`), not in the TS package, which is why a grep of the
package's own `package.json` finds nothing. Each plugin instance produces one
grouped API section in the docs sidebar (App, Workflow, Job, Step, Triggers,
Permissions, Action, Expressions, Output). One entry point per group is how
`starlight-typedoc` scopes each sidebar.

So "delete + configure TypeDoc differently" would mean collapsing nine grouped
sidebars into one flat module — a docs regression, not a simplification. The
files carry a genuine cost (hand-synced with the `index.ts` barrel; the header
in each says "Hand-synced with the index.ts barrel — index.ts is the source of
truth"), but they fail the deletion test: delete them and the docs build loses
its grouped API reference.

The project has **already decided** the pragmatic answer here:
`docs/architecture-deepening-plan.md:51-52` — "add a header comment in each
pointing at `index.ts` as source of truth; full generation is not worth
tooling yet." That header comment is already present in all nine files. This
proposal **concurs** and records the decision rather than reopening it:

- **Now:** keep the nine files with their source-of-truth header (done).
- **Optional later (low priority):** generate them from a single manifest
  (a `{group → exports}` map) in a docs `prebuild` step, eliminating the
  hand-sync drift. This is only worth doing if the barrel churns; today it does
  not. Not recommended as part of this sweep.

Because they are excluded from nothing in `tsconfig.json` (`include: ["src"]`),
they *are* compiled into `dist`, shipping nine tiny re-export modules in the
published package. If that matters, add `src/_docs-api-*.ts` to the
`tsconfig.json` `exclude` list (they are never imported at runtime — grep finds
no import site) so they serve docs only and stay out of `dist`. This is a safe,
self-contained tidy with no interface impact.

### C. `appLoader` / `app_loader` injection — hypothetical seam (asymmetric)

The injection parameter differs between ports, and so does the verdict.

**TypeScript — delete the parameter.** `trackUserFiles(configPath, appLoader?)`
(`sources.ts:113-115`) takes an *optional* `appLoader`. Production never passes
it: `deps.ts:173` calls `trackUserFiles(configPath)` and the function falls
back to the default `resolveAppFromModule` (`sources.ts:159`). The only callers
that pass it are tests (`sources.test.ts:40,73`, both `async () => new App()`),
and the test file's own comment (`sources.test.ts:19`) admits "The `appLoader`
argument only supplies the returned `App`; it exists to..." — i.e. it is a
test convenience. One production adapter (the default), zero production
overrides: a **hypothetical seam**. Delete the parameter. The ADR-0004
canary's need — not resolving a real `App` from the fixture, only asserting the
tracked `files` set — is met by splitting the return so the canary reads
`files` without forcing app resolution, or by having the fixture export a
trivial `app`. ADR-0004 explicitly puts the `appLoader` parameter in scope
("only the injection parameter is in scope") while the jiti-cache-diff
mechanism stays untouched.

**Python — remove via proposal 05, not standalone.** `track_user_files(config_path,
app_loader)` (`sources.py:56-59`) makes `app_loader` *required*, and production
*does* pass a real one: `deps.py:187` passes `_load_app`. So Python is not the
same "test-only" case as TS. But there is still only **one** production loader
(`_load_app`); the parameter exists not because two loaders need to vary, but
to dodge a `pin/ → cli/` import cycle (`_load_app` lives in `cli/_common.py`,
and `cli/` already imports `pin/`). That is the exact cycle TS neutralised by
homing `resolveAppFromModule` in `_load.ts`. Proposal 05 moves app resolution
into the config module in both ports; once `resolve_app` lives in `config`,
`pin/sources.py` calls it directly and the `app_loader` parameter has no reason
to exist. **Verdict: delete the Python parameter as part of proposal 05's
restructuring**, converging both ports on a no-injection `track_user_files` /
`trackUserFiles`. Tracked here for completeness; the edit lands with 05.

### D. Python `unwrap_commented` — symmetric public surface, wire it

`unwrap_commented` (`_commented.py:112-116`) is exported from `__init__.py`
(imported at line 6, listed in `__all__` at line 46), so it is **public API**,
not internal dead code — and its TS peer `unwrapCommented` is likewise exported
from `index.ts:26`. The two are symmetric public surface. Internally, though,
neither is called: both emitters peel the wrapper inline by reading `.value`
directly — Python `nodes.py:101-102` (`if isinstance(value, Commented): return
_to_node(value.value, ...)`) and `nodes.py:171-174`; TS `yaml-writer.ts:79-82`
and `102-103`. Confirmed by grep: zero internal consumers of either helper.

This is an **asymmetry with `unwrap_raw`**, which *is* load-bearing —
`nodes.py:106,125` route through `unwrap_raw` (and `_raw.py:22` documents it as
the peel path). `unwrap_commented` is its sibling in the public API but earns
its keep nowhere.

**Verdict: keep public, and wire it — in both ports for parity.** Rather than
delete a symmetric, documented companion to `is_commented` / `with_comment`,
make the emitters use it: `nodes.py:173` `value.value` → `unwrap_commented(value)`
and the inline peels route through it; likewise TS `yaml-writer.ts` uses
`unwrapCommented`. This turns dead public surface into load-bearing surface,
mirrors `unwrap_raw`, and keeps the two ports symmetric. It is a small change
with a real payoff: the helper now has exactly the internal adapter that
justifies its export. (Deleting it is the alternative — also symmetric, also
pre-1.0-legal — but it removes a natural member of the `Commented` API for no
gain, so wiring is preferred.)

### E. Python frame-classification predicate — duplicated (Python only)

Two predicates decide "is this path ghagen-internal vs user code," with
**divergent algorithms**:

- `models/_base.py:33-44` — `_GHAGEN_ROOT = Path(__file__).parent.parent`, then
  `_is_internal_frame` checks `"pydantic" in parts` or `resolved == _GHAGEN_ROOT
  or _GHAGEN_ROOT in resolved.parents`.
- `pin/sources.py:20-53` — `_ghagen_package_root()` via `import ghagen`, then
  `_is_user_file` checks `"site-packages" in parts`, `relative_to(ghagen_root)`,
  and a stdlib sweep over `sysconfig.get_paths()`.

They answer the same question differently (one keys on pydantic frames for
stack attribution, the other on site-packages/stdlib for import tracking), and
each is tested separately (`test_frame_markers.py:24-50` vs the `sources`
tests). Same concept, two implementations, two test suites — the classic
duplicated-predicate smell.

**TypeScript already solved this.** The explorer asked whether TS has the
mirror duplication; it does **not**. `_package_paths.ts` is a single shared
module exporting `isInternalFrame` (used by `_source_location.ts:10,32` for
stack attribution) and `isUserFile` (used by `pin/sources.ts:34,137,149` for
tracking), with one `PACKAGE_INTERNAL_DIR` prefix computation serving both
(`_package_paths.ts:1-13` documents exactly this shared-predicate intent). So
this item is **Python-only**: bring Python up to TS's structure.

**Verdict: extract one shared predicate module in Python** — e.g.
`ghagen/_package_paths.py` — exposing `is_internal_frame(filename)` (the
pydantic-or-ghagen-root check for stack attribution) and `is_user_file(path,
...)` (the site-packages/stdlib/ghagen-root check for tracking), with the single
ghagen-root computation shared. `models/_base.py` and `pin/sources.py` import
from it; the two test suites collapse onto the one module. This restores
Python↔TS parity (the mandate) and removes the divergent-algorithm hazard where
a fix to one copy silently skips the other.

### F. TS `transforms.ts` — keep (domain vocabulary), do not inline

`transforms.ts` is a 22-line file whose only export is the `Transform` type
alias (`type Transform = (item: Document) => Document`). It has multiple use
sites — `app.ts:17`, `pin/transform.ts:11`, and the public re-export
`index.ts:161` — so a naive read says "fails the deletion test with ~4 uses,
inline it." That read is wrong here for two reasons:

1. **`Transform` is domain vocabulary.** `CONTEXT.md:30-31` (both ports) defines
   **Transform** as "A synthesis-time mutation applied to a clone of a Document
   before emission (e.g. the pin transform)." It is a named concept in the
   model, not an incidental type. The Python peer is a full `Protocol`
   (`transforms.py:21-30`), exported from `__init__.py:39`.
2. **It is public, user-facing surface.** `index.ts:161` /
   `__init__.py:__all__` export it so users can type their own transforms; the
   `App({ transforms })` option takes it.

Inlining it into `_base.ts` or `app.ts` would either bury a domain term inside
a file that is not about it, or force `pin/transform.ts` and user code to import
the concept from an unrelated module. **Verdict: keep the file.** The one honest
question is *location*, not existence: `transforms.ts` sits at the package root
as a tiny module, which matches the Python `transforms.py` module boundary
(parity). Keeping it there preserves symmetry and gives the domain term a home
whose name states what it is. Do not inline; do not rename. No change.

### G. TS `pin/collect.ts` — out of scope

Handled by **proposal 04**. Not covered here. Cross-referenced only so this
sweep is not assumed to include it.

## Proposed interface (net changes)

Only items that actually change:

- **C (TS):** `trackUserFiles(configPath): Promise<{ app; files }>` — the
  optional `appLoader` parameter is removed.
- **C (Python):** `track_user_files(config_path)` — the `app_loader`
  parameter is removed (lands with proposal 05).
- **D (both):** emitters call `unwrap_commented` / `unwrapCommented`; the
  helpers stay exported and become load-bearing.
- **E (Python):** new `ghagen/_package_paths.py` with `is_internal_frame` and
  `is_user_file`; `models/_base.py` and `pin/sources.py` import from it. No
  public-surface change (both predicates are private today).
- **B (optional):** add `src/_docs-api-*.ts` to `tsconfig.json` `exclude` so
  they stay out of `dist`.

Items A, B (files themselves), F, G: no change.

## What sits behind the seam

- Removing the TS `appLoader` parameter shrinks `trackUserFiles`'s interface to
  exactly what every production caller uses — the jiti-cache-diff + ESM-hook
  union behind it (ADR-0004) is untouched. The seam that remains
  (`trackUserFiles` itself) is real: it has one production caller and one
  canary test, but its *interface* is the tracked-file contract, not a swappable
  loader.
- The Python shared predicate turns two divergent implementations behind two
  test surfaces into one implementation behind one — the same consolidation TS
  already has behind `_package_paths.ts`.
- Wiring `unwrap_commented` gives the public helper the single internal adapter
  that makes its export honest, matching `unwrap_raw`.

## Migration plan

1. **B (tidy):** add `_docs-api-*.ts` to `tsconfig.json` `exclude`; verify the
   docs build (`starlight-typedoc`) still resolves them via `entryPoints`
   (astro reads `src` directly, not `dist`, so exclusion is safe). Record the
   keep-decision in this doc; no file deletions.
2. **D:** point both emitters at `unwrap_commented` / `unwrapCommented`; keep
   exports. Golden files unchanged (behaviour identical).
3. **E:** create `ghagen/_package_paths.py`; move the two predicates in, share
   the root computation; update `models/_base.py` and `pin/sources.py`; merge
   the two test suites onto the new module.
4. **C (TS):** delete the `appLoader` parameter; adjust the ADR-0004 canary to
   read `files` without forcing app resolution (split the return, or export a
   trivial `app` from the fixture).
5. **C (Python):** delete `app_loader` when proposal 05 lands `resolve_app` in
   config; `track_user_files` calls it directly.
6. **A, F, G:** no code change; keep-verdicts recorded.

## Test impact

- **A (`postProcess`):** no change — its tests stay as the guard that the
  escape hatch works. A one-line assertion may be added that `structuredClone`
  is *not* introduced, but the two existing clone tests
  (`_clone.test.ts:40` preserving `postProcess` by reference; the `Raw`/
  `Commented` round-trips) already lock the reference-passing contract.
- **D:** existing `unwrap_commented`/`unwrapCommented` are exercised
  transitively once the emitter uses them; keep the focused unit tests. No
  golden-file changes.
- **E:** `test_frame_markers.py` and the `sources` predicate tests collapse
  onto `_package_paths.py`; assertions unchanged, import paths change. This is
  "replace, don't layer" — one predicate, one test surface.
- **C (TS):** `sources.test.ts` (the ADR-0004 canary, never mocked) drops the
  `appLoader` argument; its file-set assertions are unchanged.
- **C (Python):** `test_sources.py` and the `test_deps.py` `_mock_track_user_files`
  double lose the `app_loader` argument; they mock/monkeypatch the shared
  `resolve_app` instead.

## Breaking changes (pre-1.0, enumerated)

All acceptable under the pre-1.0 clean-break policy; listed for the changelog:

1. **TS `trackUserFiles` signature** — the second parameter `appLoader` is
   removed. Public via `pin/index.ts:31`. Any external caller passing a custom
   loader must stop; the default resolution is the only path.
2. **Python `track_user_files` signature** — the required `app_loader`
   parameter is removed (with proposal 05). Callers pass only `config_path`.
3. **No other public breaks.** `unwrap_commented` / `unwrapCommented` and
   `Transform` stay exported; `postProcess` / `post_process` stay; the
   `_docs-api-*.ts` files stay. The Python predicate extraction touches only
   private (`_`-prefixed) names.

## Risks & alternatives

- **Risk (B):** excluding `_docs-api-*.ts` from `dist` could break the docs
  build if `starlight-typedoc` ever resolved them from `dist`. It does not —
  `astro.config.mjs` points `entryPoints` at `../packages/typescript/src/...`.
  Verify once, then it is safe.
- **Risk (E):** the two Python predicates have subtly different remits
  (pydantic-frame awareness for stack attribution vs stdlib/site-packages for
  tracking). The shared module must expose *both* checks, not force one
  algorithm on both callers — mirror `_package_paths.ts`, which keeps
  `isInternalFrame` and `isUserFile` as two functions over one prefix. Do not
  over-merge into a single function.
- **Alternative for D: delete instead of wire.** Legal pre-1.0 and symmetric,
  but it strips a natural member of the public `Commented` API. Wiring costs
  one line per emitter and makes the export load-bearing, so wiring wins.
- **Alternative for B: generate the stubs now.** Deferred per
  `architecture-deepening-plan.md:51-52`; only worth it if the `index.ts`
  barrel starts churning.
- **Non-alternative: `structuredClone` after pruning `postProcess`.** Closed
  regardless — the symbol-branded `Raw`/`Commented` wrappers block it
  unconditionally (`_base.ts:434-435`). Recorded so it is not re-proposed.

## ADR / CONTEXT.md impact

- **ADR-0004** — its "only the injection parameter is in scope" clause is
  exercised: the TS `appLoader` parameter is removed while the jiti-cache-diff
  + ESM-hook mechanism stays verbatim. Add a one-line note that the parameter
  was removed as hypothetical-seam indirection; the canary is unchanged.
- **CONTEXT.md (Python)** — document the new `_package_paths.py` shared
  predicate, matching the existing TS description of `_package_paths.ts`.
- **`architecture-deepening-plan.md:51-52`** — this proposal formally adopts its
  `_docs-api-*.ts` recommendation (keep + header comment; defer generation) and
  adds the `dist`-exclusion tidy.
- No ADR is needed for the keep-verdicts (A, F); they are recorded here so the
  surface is not re-swept.
