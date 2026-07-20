# Architecture deepening plan

Deepening refactors surfaced by an architecture review. Goal: turn shallow modules into deep ones —
better testability and AI-navigability. Vocabulary: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md);
decisions: [`docs/adr/`](./adr/).

## Ground rules (agreed)

- **Design fresh per candidate** — pick the best shape for each seam; both languages converge on it.
  Where TypeScript already has the better shape, Python converges toward it (and vice versa).
- **Lockstep both languages** — each unit lands Python + TypeScript together; parity never drifts.
- **Incremental, dependency-ordered PRs** — one branch per unit.
- **Cleanup sweep first** — delete dead code before the real work.
- Breaking changes are fine (pre-1.0).

## Dependency order

```
0. Cleanup sweep
   ↓
1. #2 Model traversal  walk()/children()          [foundational]
2. #1 Emitter seam     Document + generic emitter  [needs 0; uses walk]
   ── pin track ──
3. #4 UsesRef          canonical parse + pinnability (+ ParsedTag)
4. #5 GitHub transport HttpClient + GitHubClient
5. #6 Lockfile seam    deepen around validation invariant
6. #3 Pin engine       orchestration out of CLI     [needs 2,4,5,6]
   ── independent ──
7. #7 Config + root    unify discovery, kill auto_dedent global
8. #8 Schema parity    dev-only tooling, one canonical snapshot   [+ stretch]
```

---

## 0. Cleanup sweep

Mechanical deletions, no design:

- Orphaned `lint/` subsystem — `.pyc` (Python) + `.d.ts` (TypeScript) for 5 rules with **no source
  in git**. Remove the residue; update the stale `app.ts` "exposed for transforms/lint" comment.
- No-op `to_commented_map` overrides: `models/workflow.py:59-67`, `models/job.py:163-171` (dead
  `pass` branches).
- Dead helpers/aliases: `container.py` `_serialize_service_value` + `ServiceMap`, `step.py`
  `StepList`, `permissions.py` `PermissionsValue`.
- Duplicate `Container` / `Service` classes (byte-identical) — collapse.

---

## 1. #2 Model traversal — `walk()` / `children()`

**Deepen:** add generic tree traversal to the Python model base, matching TypeScript's.

- **`children()`** — generic field-scan: iterate `model_fields`, recurse through Commented / dict /
  list, yield `(key, GhagenModel)`, skip `Raw`. Mirrors TS `scanForModels`. Zero per-model code.
- **`walk()`** — depth-first **generator** yielding `(path, model)`. No skip-control (no consumer
  needs it yet). TypeScript keeps its callback form (idiomatic there); same semantics.
- **Consumers:** `pin/collect` (read) and `pin/transform` (mutate the yielded model's scalar field)
  rewrite onto `walk()`. Delete `_collect_from_steps`, `_pin_workflow`, `_pin_steps` — 4 hand-coded
  traversals collapse to one primitive.
- **Driver:** `walk()` is model-only; `collect_uses_refs` stays the App-level driver
  (`for item in app._items: item.walk()`). No `App.walk()` (single caller → shallow).
- **Separate from the emitter** — traversal (enumerate + mutate) and serialization (rebuild an
  ordered map) stay distinct walkers; #2 does not share a spine with #1.

**Tests:** `walk()` / `children()` unit-testable on a plain constructed model — no network, no synth.

---

## 2. #1 Emitter seam — Document + generic serializer

**Deepen:** pull serialization off the model into a deep emitter; Python converges to TypeScript's
already-clean shape. See **ADR-0001**.

- **`Document` base** (new) between `GhagenModel` and `Workflow`/`Action`, carrying `to_yaml()` /
  `to_yaml_file()` **once** (Python methods → private `_to_yaml(model, header)` free function in the
  emitter). Kills the ~46-line dup across `workflow.py` + `action.py`. `App._Item` becomes `Document`.
- **Generic `to_commented_map()`** on the base — a **single** method, **zero** subclass overrides.
  The god-method's internals (`_serialize_value`, `_restore_nested_models`,
  `_collect_commented_fields`, alias-resolution ×2, Raw-unwrap ×3, Commented ×5) consolidate into
  emitter free helpers (one alias-resolver, one Raw-unwrap), mirroring TS `toYamlValue`.
- **Kill the last serialize-time override:** move `On`'s `schedule` reshape + `workflow_dispatch`
  empty→null to a **construction-time** `model_validator` (matching TS's `on()` factory).
- **TypeScript:** narrow `toYaml` / `toYamlFile` to `WorkflowModel | ActionModel`; construction-time
  normalization already present. Otherwise minimal.
- **Misuse guard:** `step.to_yaml()` no longer exists; the file-level serializer only accepts a
  Document.

**Depends on:** cleanup #0 (removes the no-op overrides first).

---

## 3. #4 UsesRef — canonical parse + pinnability (+ ParsedTag)

**Deepen:** one parsed reference type replaces 5 ad-hoc `@`-splits and a divergent predicate.

- **`pin/uses.py` → `UsesRef`** `{owner, repo, path, ref}`, retiring private `_ParsedUses`.
  ```
  UsesRef.parse(s) -> UsesRef | None    # None for ./, docker://, no '@' (unpinnable by shape)
    .ref_is_sha   -> bool               # 40-char hex
    .is_pinnable  -> bool               # parsed AND not already a SHA
    .with_sha(sha) -> str               # rebuild owner/repo[/path]@sha
  ```
- **collect and transform both gate on the same `.is_pinnable`.** A hand-written SHA ref →
  `is_pinnable` False → transform skips it, never looks up the lockfile, **never raises PinError**.
  The divergent-predicate trap (collect skipped SHAs, transform didn't) dies structurally.
- **Fold in the `versions.py` fix:** Python gains a `ParsedTag {tag, prefix, version}` struct so
  `parse_tag` runs the regex **once** — retire `_extract_prefix`'s double-regex, matching TS.
- **Both languages.**

---

## 4. #5 GitHub transport seam

**Deepen:** inject an HTTP transport so the GitHub logic becomes testable without network.

- **`HttpClient` protocol** (`get(url, *, token) -> Response`) — the injected seam. Adapters:
  `UrllibTransport` (stdlib default, no dep) and a `FakeTransport` for tests.
- **`GitHubClient(transport, token)`** in `pin/github.py` — the deep module: URL building, error
  mapping, pagination, annotated-tag deref. `resolve_ref` / `list_tags` / `dereference_tag` become
  methods; `token` moves from per-call param to construction.
- **Pure helpers stay free functions** — `_parse_next_link`, tag-vs-head fallback, deref decision,
  semver — unit-testable directly. GitHub logic tested via `FakeTransport` with canned responses.
- **Scope: pin only.** `schema/fetch`'s httpx is a separate host (SchemaStore) and resolves under
  #8, which makes it explicitly dev-only (httpx stays fine there — no transport seam needed).
- **Both languages** (TypeScript injects a `fetch`-like transport).

---

## 5. #6 Lockfile seam

**Deepen** around the real invariant: **a Lockfile always holds valid entries.**

- Construction/read **validates** (raise on malformed) — Python catches up to TypeScript's
  `readLockfile`; add a typed `LockfileError`.
- Make `.pins` **private** (read-only view + `keys()` / iteration + `get` / `merge` / `prune`). The
  raw-map mutation in `deps` migrates to methods — that migration lands in **#3** (where the
  orchestration moves). `merge` becomes live (the pin engine uses it) instead of dead.
- **Both languages** aligned on validation.

---

## 6. #3 Pin engine — orchestration out of the CLI

**Deepen:** lift the pin/upgrade *engine* out of the Typer/commander handlers into a pin-layer
module returning typed reports. Composes #2, #4, #5, #6.

- **`pin/engine.py`** — three free functions, each taking the `App` + an injected `GitHubClient`,
  returning a typed report:
  ```
  pin(app, client, *, update, prune)   -> PinReport      {resolved, errors, pruned, written}
  check_sync(app, *, prune)            -> SyncReport     {missing, extra}          # pure, NO network
  upgrade(app, client, *, mode, apply) -> UpgradeReport  {version_bumps, lockfile_stale,
                                                           changed_files, warnings}
  ```
- **Typed reports** replace untyped `list[dict]` — `VersionBump`, `LockfileStaleEntry`, wrappers.
  Drop the speculative `origin: "user"` field (no second case).
- **No I/O in the engine except its job:** warnings become structured `report.warnings` (CLI
  renders); the engine still owns writing the lockfile (pin) and mutating source files (upgrade,
  gated by `apply`). Network via injected client; file I/O via tmp-testable paths.
- **Fold in the `sources` parity fix:** app-load + user-file tracking returns `(app, files)`
  together (TS already does), killing Python's `ghagen_app_holder` mutable-list hack and the manual
  `user_files.add(config_path)`.
- **Token resolution + no-token warning** move to the CLI (it builds the client) — kills the
  duplication. The per-repo `list_tags` cache stays engine-local (GitHubClient may memoize later).
- **CLI shrinks to:** resolve token → build client → call op → render.
- **Testability:** `check_sync` needs no client (zero mocking); `pin` / `upgrade` via `FakeTransport`
  + tmp dirs.
- **Both languages.**

---

## 7. #7 Config + root unify, kill the `auto_dedent` global

See **ADR-0002**.

- **Part 1 — kill the global (both languages).** Dedent moves to **serialization time** — a
  normalization over the model tree (walk Steps via #2, dedent `run`) in the emit path, gated by an
  `auto_dedent` flag threaded explicitly: `.ghagen.yml` → `App` → `to_yaml_file(auto_dedent=...)`;
  standalone `to_yaml(auto_dedent=True)`. A fixed pre-serialize pass, **not** a pipeline Transform,
  so standalone and synth behave identically and #1's generic emitter stays clean. Delete the module
  global and TypeScript's public `setAutoDedent` / `getAutoDedent`. **Semantic change:** `run` holds
  the raw string until emit.
- **Part 2 — unify discovery.** `.ghagen.yml` is found two ways today (`config` uses `cwd`; `header`
  walks ancestors). Consolidate Python `config.py` + `paths.py` + `_yaml_config.py` into one
  `config` module with a **single** `find_app_root` (ancestor-walk) used by both `load_options` and
  header `{source_file}`. TypeScript consolidates `config.ts` likewise.

---

## 8. #8 Schema-sync parity

See **ADR-0003**.

- **Schema tooling is dev-only.** Move Python `schema/` (fetch / codegen / diff) out of the shipped
  package into dev tooling (mirroring TypeScript's `scripts/`). It already imported dev-only httpx,
  so it never shipped as a runtime feature.
- **One canonical snapshot.** Collapse the 3× byte-identical schema JSON (`fixtures/schema/`, Python
  snapshot, TS snapshot) to a single repo-root `schema/` copy consumed by both test suites, TS
  codegen, and drift detection.
- **Delete Python generated models** — diff-only dead weight (no prod import, lint/type-excluded).
  Drift is detected from the JSON diff alone; drop the `datamodel-code-generator` dependency.
- **Drift = JSON comparison, one repo-level dev/CI tool** (kept in Python). httpx stays fine here
  (explicitly dev-only) — no transport seam.
- **TypeScript codegen stays** (`generate-types.ts` → types imported by models for compile-time
  conformance). The conformance asymmetry (TS compile-time, Python runtime + tests) is **inherent**
  and intentional — not parity to force.

### Stretch — Python coarse conformance test

Optional, tracked separately: load the canonical snapshot, walk schema properties, assert ghagen's
Python models cover them (with an explicit allow-list for intentional gaps). More valuable than the
deleted diff-only generated models; needs no code generation.
