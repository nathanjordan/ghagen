# Architecture deepening plan — round 2

Round 1 (traversal, Document seam, UsesRef, GitHub transport, Lockfile, pin engine, config unify,
schema parity) landed in full — see git history `261a9bd`..`ba404c9`. This is the second review
pass over the post-round-1 codebase. Goal unchanged: turn shallow modules into deep ones — better
testability and AI-navigability. Vocabulary: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md); decisions:
[`docs/adr/`](./adr/).

## Ground rules (carried from round 1)

- **Design fresh per candidate** — both languages converge on the best shape.
- **Lockstep both languages** — each unit lands Python + TypeScript together.
- **Incremental, dependency-ordered PRs** — one branch per unit.
- **Cleanup sweep first.**
- Breaking changes are fine (pre-1.0).

## Dependency order

```
0. Cleanup sweep
1. CI parity gate        [first real unit — everything after lands under BOTH test suites]
2. ModelSpec             [both ports; feeds 3 and 7]
3. Emitter seam round 2  [Python-heavy; dedent folds in; needs 2; amends ADR-0001]
   ── independent after 2/3 ──
4. Pin UsesSite + App accessors
5. Sources hardening     [see ADR-0004]
6. Deps render formats
7. Conformance sweep     [needs 2]
```

---

## 0. Cleanup sweep

Mechanical deletions, no design:

- **Top-level `tests/` shadow tree** — zero git-tracked files, 47 stale `.pyc` under
  `tests/**/__pycache__` (+ `.github/__pycache__`). Live suite is `packages/python/tests`.
  Delete; grep trap for humans and agents.
- **`pin/resolve.py` / `pin/resolve.ts`** — one-`Error` modules. Python's cycle justification is
  false (transports live inside `github.py`); TS's exists only for the compiler. Fold
  `ResolveError` into `github.*` alongside `TransportError`.
- **TS `SynthItem`** — identical union to `Document` (`_base.ts:376`), both exported. Keep
  `Document` (the domain term), delete `SynthItem`, update `app.ts` / `pin/transform.ts` /
  `index.ts`.
- **Python `| CommentedMap` ×~60 field annotations** — one type alias (e.g.
  `OrRaw = T | CommentedMap`) declared once in `models/_base.py`; mechanical sweep (sed-friendly).
- **`config.py:67-119`** — ~50 LOC options machinery (`_parse_bool`, `_extract_from_ghagen_yml`,
  separate loader) surfacing one boolean. Collapse to a direct `load_options() -> GhagenOptions`.
  Keep `find_app_root` / `load_yaml_config` untouched (genuinely deep, three consumers).
- **`_docs-api-*.ts`** (9 stubs, hand-synced with barrel) — add a header comment in each pointing
  at `index.ts` as source of truth; full generation is not worth tooling yet.

---

## 1. CI parity gate — scoped scripts (decided)

**Problem:** `fixtures/expected/` is the parity seam, but vitest never runs in CI or pre-commit —
TS Emitter regressions against shared golden files pass CI. CI job bodies also re-list commands
instead of calling `scripts/*.sh`, and have already drifted (CI test job omits vitest).

**Design (decided): scripts are the single seam for "what constitutes each gate", with a scope
argument.**

- `scripts/test.sh [py|ts|all]`, `scripts/lint.sh [py|ts|all]`, `scripts/typecheck.sh [py|ts|all]`
  (default `all`). `fmt.sh` likewise for symmetry.
- `.github/ghagen_workflows.py` CI jobs call the scripts with a scope — per-language jobs keep
  parallel caches (`test-py` → `scripts/test.sh py`, `test-ts` → `scripts/test.sh ts`, etc.).
- Pre-commit and humans call with default `all`.
- Regenerate workflows; **vitest becomes a required gate**.

**Benefits:** parity invariant test-enforced on both sides; command-set knowledge lives once;
scripts/CI can no longer disagree.

---

## 2. ModelSpec — per-model serialization spec (decided)

**Problem:** one model's serialization knowledge is split across 3–4 files in both ports:
Python has 180 LOC of key-order lists (`emitter/key_order.py`) + ~20 two-line `_get_key_order()`
pass-through overrides; TS has `key-order.ts` (152 LOC) + `FIELD_MAP`s stating the same kebab keys
twice with no compile-time link + 24 near-identical `Model` subclasses (~235 LOC of `kind` +
`keyOrder` + copy-paste `clone()`).

**Design (decided): an explicit spec object per model, declared next to the class/factory:**

```python
STEP_SPEC = ModelSpec(
    yaml_keys={"name": "name", "if_": "if", "working_directory": "working-directory", ...},
    order=["name", "id", "if", "uses", "run", ...],
)
```

- **Python:** models reference their spec; `_get_key_order()` overrides and
  `emitter/key_order.py` die. The Emitter consumes the spec.
- **TypeScript:** spec subsumes `FIELD_MAP` + `*_KEY_ORDER`; `emitter/key-order.ts` dies. The 24
  `Model` subclasses collapse to one `Model` carrying `kind` + `spec` — `instanceof StepModel` (2
  sites: `pin/transform.ts:29`, `pin/collect.ts:25`) becomes `model.kind === "step"`.
- **Auto-wrap unification (TS):** the spec also carries the inline-input wrap map
  (field → sub-factory), replacing the three drifted hand-rolled ladders in `workflow()`
  (`workflow.ts:91-125`, incl. the Commented-peel dance), `job()` (`job.ts:345-387`), `on()`
  (`trigger.ts:396-440`).
- **`workflow_dispatch` inputs get a real model + spec (decided)** in both ports, so
  `WORKFLOW_DISPATCH_INPUT_KEY_ORDER`'s promise finally becomes true (today it is defined + tested
  but wired to nothing; inputs emit unordered).

**Benefits:** add a field = one edit in one file; ordering cannot drift from the field map; new
model type = one spec, not four edits; spec doubles as machine-readable model surface for unit 7.

---

## 3. Emitter seam round 2 — Emitter owns all recursion (decided; amends ADR-0001)

**Problem (Python):** serialization recursion ping-pongs `models/_base.to_commented_map` →
`emitter/yaml_writer.to_yaml_node` → back into `child.to_commented_map()`. The
Commented/Raw/model/dict/list dispatch is written three times (`_scan_for_models`,
`to_yaml_node`, `to_commented_map`'s loop); the Raw→`PlainScalarString` rule three times; a
comment's final column is decided in two modules sharing hard-coded ruamel indent constants;
bidirectional imports are dodged with function-local imports; `emitter/__init__.py` is empty so
callers assemble five submodules; tests consequently poke private ruamel internals.

**Design (decided): the Emitter owns recursion end to end; models carry only data + ModelSpec.**

- Public surface: `emit(document, *, auto_dedent=False, header=None) -> str` (+ file variant) in
  a curated `emitter/__init__.py`.
- One internal `_to_node(value)` dispatcher — the only home for Commented/Raw/model/dict/list
  dispatch and wrapper see-through.
- `Document.to_yaml()` / `to_yaml_file()` stay the public API, now thin delegates to `emit()`
  (ADR-0001's file-gating is untouched).
- `to_commented_map()` (Py) / model-side `toYamlMap()` (TS) are **removed** — recursion never
  leaves the Emitter in either port. **ADR-0001 amended** (see the ADR's amendment section).
- Comment placement single-owner: the `atSeqItem`-style container decision moves inside the
  Emitter's recursion (today made at 3 call sites in TS; split across `comments.py` +
  `yaml_writer.py` column-rewriting in Python). Ruamel indent constants get one home.
- **Unit 7 of round 1's dedent folds in (decided):** `_to_node` sees `Step.run` during the walk —
  dedent applies at node-build time. Kills the second full `model_copy(deep=True)` per Document
  (`emit.py:33` on top of `app.py:143`) and the separate `_dedent_steps` walk. ADR-0002 preserved:
  still serialization-time, still explicitly threaded.
- `models/_base` loses its four emitter imports; the import cycle dies.

**Tests:** the Emitter interface is the test surface — Document-in/YAML-out golden tests replace
private-node poking. Nested composite-action dedent + transform/dedent interaction get direct
coverage (currently untested).

---

## 4. Pin UsesSite — one traversal policy, App stops leaking privates (decided)

**Problem:** "which models carry a pinnable `uses`, and how to extract it through a possible
Commented wrapper" is written twice per port (`pin/collect` + `pin/transform`); a third
`uses`-bearing model means editing both. Pin also reads `App._items`
(`pin/collect.py:30`) — App's private storage is the de-facto contract.

**Design (decided): pin-owned UsesSite iterator.**

```python
# pin/sites.py
@dataclass
class UsesSite:
    ref: UsesRef                      # parsed; knows is_pinnable
    def replace(self, new: str): ...  # Commented-peel/re-wrap internal

def iter_uses_sites(doc: Document) -> Iterator[UsesSite]: ...
```

- The Step/Job selection lives once, in pin. Models stay pin-ignorant.
- `collect` = iterate + read; `transform` = iterate + `replace`. Both gate on the same
  `ref.is_pinnable`.
- `App` grows a public `documents()` accessor; pin stops touching `_items`.
- Both ports.

**Tests:** iterator unit-testable on a constructed Workflow — no App, no network.

---

## 5. Sources hardening — keep cache-diff, test it (decided; ADR-0004)

**Problem:** `pin/sources.ts` (user-file tracking that scopes `deps upgrade --apply`) has zero
direct tests — only ever mocked — and its failure mode is silent (empty file set → no-op
upgrades). Two policies are duplicated-and-drifted: module→App resolution
(`sources.ts:38-55` vs `cli/_common.ts:155-184`, whose doc comment falsely claims sources uses
it) and the internal-file predicate (`sources.ts:113-140` vs `_source_location.ts:30-55`).

**Design (decided — transform-hook migration investigated and rejected, see ADR-0004):**

- **Keep the `jiti.cache` diff.** Spike findings: `cache` is typed, non-deprecated public surface
  in jiti's own `types.d.ts` (`Jiti extends NodeRequire { cache: ModuleCache }`); the supported
  `transform` hook alternative misses plain-CJS modules (native require path → no transform call)
  and is skipped on fsCache hits — strictly worse coverage. Correct the stale
  "not formally documented" header comment.
- `sources.ts` calls `resolveAppFromModule` from `cli/_common.ts` — one resolution policy.
- One internal-file predicate module shared by `sources.ts` and `_source_location.ts`.
- **Real-jiti integration test**: fixture project (config + TS helper + ESM helper + one
  plain-CJS helper), assert the exact tracked file set. A jiti upgrade changing cache behavior
  turns from silent no-op into red test.
- **Python cousin:** `_base.py:24-55` frame markers are substring-coupled to `/ghagen/models/` and
  `/ghagen/emitter/` — a model built via `helpers/` or `pin/` mis-attributes the user frame.
  Derive the internal prefix from the package root instead of a directory list; unit-test the
  skip logic.

---

## 6. Deps render formats — heredocs die (decided)

**Problem:** `check-deps/action.yml` (generated from `.github/ghagen_workflows.py:712-801`)
embeds Python heredocs that parse `deps upgrade --json` output and render PR/issue markdown —
re-encoding the report shape (`version_bumps`, `lockfile_stale`, `severity`, …) in a third place
that is never type-checked or tested. Pre-commit already has to exclude the file from
`check-yaml`.

**Design (decided):** `deps upgrade --format {json, pr-body, issue-body}` in both ports.

- The two markdown renderers live in the CLI layer, golden-file tested against
  `fixtures/expected/` (new `upgrade_pr_body.md`, `upgrade_issue_body.md`) exactly like the JSON
  contract.
- `check-deps` regenerates to: run the command with the right `--format`, pass output through.
  Heredocs deleted; the `check-yaml` exclusion should become removable.

---

## 7. Conformance sweep — shared allow-list (decided)

**Problem:** the round-1 stretch item's blind spots. The Python conformance test walks only
`workflow_schema.json`; the action Snapshot is unswept; nothing asserts the two ports model the
same property set. Separately: Drift is detected two different ways (`schema_sync.py check-drift`

- difflib — tested but dead in CI — vs `schema-drift.yml`'s `sync` + `git diff`), and the schema
  registry is forked (`schema_sync.py:39-48` `SCHEMAS` vs `generate-types.ts:38-47` `TARGETS`).

**Design (decided): shared allow-list.**

- `schema/conformance-gaps.yml` — one file naming intentional gaps per Snapshot.
- pytest walks **both** Snapshots (workflow + action) against the Pydantic model surface;
  vitest walks both against the ModelSpecs (unit 2). Both read the same gaps file — cross-port
  agreement falls out structurally: both pass against the same allow-list ⇒ same coverage.
- **One drift mechanism:** keep `sync` + `git diff` (already CI-proven, simpler); delete the
  `check-drift` subcommand, its difflib helper, and `test_diff.py`.
- **One schema registry:** `schema/manifest.json` (name → upstream URL → filename) read by both
  `schema_sync.py` and `generate-types.ts`.
