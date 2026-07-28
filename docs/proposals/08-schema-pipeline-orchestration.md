# 08 — Schema pipeline orchestration

**Status:** proposed | **Ports:** dev tooling (both) | **Depends on:** ADR-0003 (amended, see below)

## Problem

The schema pipeline is a set of loose scripts that a maintainer must chain by hand and remember to run in the right order. There is no single module with one interface; there are two half-modules whose shared knowledge is copied rather than referenced, and the one guarantee ADR-0003 leans on — that the committed generated types conform to the committed Snapshot — is never actually checked.

Concrete evidence (all verified against the tree at the time of writing):

- **The verbs are unchained.** `sync` lives in `packages/python/scripts/schema_sync.py` (argparse with a single `sync` subcommand, `main` at lines 94–102; fetches every entry of `schema/manifest.json` via `save_all_schemas`, lines 74–85; deterministic `json.dumps(..., sort_keys=True)` at line 65). `generate` lives in `packages/typescript/scripts/generate-types.ts` (reads the manifest at 49–52, derives output names at 54–57, writes `src/schema/*.generated.ts`, shells `npx oxfmt` at line 86). Nothing runs `sync → generate → verify`. There is no home for the sequence, so it lives only in the maintainer's head.

- **No staleness check exists.** There is no CI step asserting that the committed `src/schema/*.generated.ts` still matches the committed `schema/*.json`. `schema_sync.py` has no `--check` mode (its docstring, lines 10–12, defers drift entirely to `git diff` in CI). If a maintainer edits the Snapshot but forgets to regenerate, the stale codegen passes silently unless `tsc` happens to collide with the change — so ADR-0003's compile-time author-conformance story (the generated types are imported into the hand-written TS models) can silently weaken to nothing.

- **The Snapshot registry is an unvalidated, re-declared interface.** `schema/manifest.json` (name → `{url, filename}`) is consumed by two readers that each re-derive the entry type independently: `schema_sync.py:35–41` (`dict[str, dict[str, str]]`) and `generate-types.ts:39–43` (`interface SchemaManifestEntry`). The `name_schema.json → name-types.generated.ts` filename convention exists only as the regex `entry.filename.replace(/_schema\.json$/, "-types.generated.ts")` at `generate-types.ts:56`. If a manifest entry does not end in `_schema.json`, that regex is a silent no-op — the generated file overwrites its own source name — and nothing tests it.

- **The drift workflow throws away its own fix.** `.github/workflows/schema-drift.yml` is generated from `_schema_drift_workflow()` in `.github/ghagen_workflows.py:166–206`. It runs `schema_sync.py sync` (line 188) on a weekly cron plus dispatch, then `git diff --exit-code schema/` and, on drift, opens an issue whose body is the raw `git diff` (lines 192–201). It never commits, never regenerates types, never opens a PR. The refreshed Snapshot is discarded with the checkout; a human must reproduce the whole thing locally.

- **Repo-root / test-path resolution is duplicated ~6 ways, one of them brittle.** `packages/python/tests/test_integration/conftest.py:14–21` walks up looking for `schema/`; `packages/python/tests/test_cli/test_deps.py:23–30` walks up looking for `fixtures/expected/`; `packages/python/tests/test_schema/test_conformance.py:43` hardcodes `Path(__file__).resolve().parents[4]` with **no assertion** that it landed on the root (the most brittle — any move of the file silently retargets it); `packages/typescript/src/integration/test-utils.ts:7,9` and `packages/typescript/src/models/conformance.test.ts:37` use `../../../../` constants; `generate-types.ts:16–17` does its own two-hop `resolve(ROOT, "../..")`. And `packages/python/tests/test_schema/conftest.py:14` inserts `packages/python/scripts` onto `sys.path` so the tests can `import schema_sync` as a bare top-level module — a hack that exists only because the tooling has no package identity.

- **Conformance-sweep parity is convention, not a test.** The scope tables in `test_conformance.py:69–90` and `conformance.test.ts:56–73` are hand-mirrored; both headers claim they are "mirrored exactly by the other sweep." The shared allow-list `schema/conformance-gaps.yml` is read by both. But nothing fails if the two `SWEEP` tables diverge — a scope added to one port and not the other, or a schema path typed differently, degrades silently.

## Current interface

Two independent entry points, no orchestrator:

```
uv run python packages/python/scripts/schema_sync.py sync   # fetch → overwrite schema/*.json
npm run generate-types  (packages/typescript)               # schema/*.json → src/schema/*.generated.ts
```

Shared knowledge that crosses the seam — the manifest entry shape, the filename convention, the repo-root location, the conformance scope set — is copied into each caller rather than owned by one module. The "interface" a new contributor must reconstruct is therefore the union of six files' private assumptions.

## Proposed interface

Deepen the pipeline into **one orchestrator module** with a three-verb interface. A caller (maintainer or CI) needs to know only the three verbs and their contract; everything else — fetch, serialize, codegen, formatting, filename derivation, path resolution — sits behind the seam.

### Verbs

```
schema sync       # network: fetch upstream → overwrite the canonical Snapshot (schema/*.json)
schema generate   # offline: committed Snapshot → regenerate src/schema/*.generated.ts (oxfmt-stable)
schema check      # offline, CI-safe: regenerate into place, assert git-clean; fail loudly on staleness
```

The verbs compose but stay orthogonal:

- `sync` is the only verb that touches the network. It is what the weekly drift job runs.
- `generate` is a pure function of the committed Snapshot. It is what a maintainer runs after editing (or after `sync`).
- `check` = `generate` + `git diff --exit-code src/schema/`. It is the missing CI guarantee: "the committed generated types match the committed Snapshot." It never fetches, so it is deterministic and offline — safe to run on every PR.

Drift (upstream divergence) and staleness (generated-vs-Snapshot divergence) become two clearly separated checks: drift = `sync` then diff the Snapshot (weekly); staleness = `check` (every PR).

### Home and language

Put the orchestrator in Python, as a dev-only package with real module identity, at the **repo root** rather than buried under `packages/python/scripts/`:

```
scripts/ghagen_schema/
  __init__.py
  __main__.py        # argparse dispatch: sync | generate | check   (python -m ghagen_schema)
  manifest.py        # the validated manifest interface (see below)
  paths.py           # repo_root(), SCHEMA_DIR, FIXTURES_DIR — the one Python resolver
  sync.py            # fetch + deterministic serialize (today's schema_sync body)
  generate.py        # shells the TS codegen; owns the sync→generate→check sequencing
  check.py           # generate + assert git-clean
```

Rationale:

- **It genuinely spans both ports**, so it does not belong under `packages/python`. `sync`/`check` are Python (fetch, serialize, orchestration), and `generate` shells into the TS toolchain (`json-schema-to-typescript` only exists there). A top-level home makes the cross-cutting nature visible and stops the "why is cross-language tooling inside the Python package?" confusion that the current `conftest.py:14` comment has to apologize for.
- **The Python project root is already the repo root** (single `pyproject.toml`, wheel built from `packages/python/src/ghagen`; `httpx`/`jsonschema` already live in the `dev` dependency group). So `uv run python -m ghagen_schema ...` works with zero new dependencies, and the tooling is naturally excluded from the shipped wheel (it is not under `src/ghagen`).
- **It earns package identity**, which deletes the `sys.path` hack: register `pythonpath = ["scripts"]` under `[tool.pytest.ini_options]` (pytest natively prepends it), and the schema tests `import ghagen_schema` like any package. `test_schema/conftest.py` shrinks to nothing.

The single canonical Snapshot stays at the repo-root `schema/` directory (unchanged, per ADR-0003). Only the _tooling_ moves; the data does not.

### CI wiring (via `.github/ghagen_workflows.py`)

Every workflow edit below is a change to the dogfooded generator, never to the generated YAML.

**1. Add staleness to the meta-lint job.** In `_ci_workflow()`, the `lint-meta` job (`ghagen_workflows.py:67–85`) already carries the language-neutral checks. Add one offline step so stale codegen fails on every PR:

```python
Step(
    name="Schema types up to date",
    run="uv run python -m ghagen_schema check",
),
```

`check` is offline and deterministic, so it needs no `GITHUB_TOKEN` and adds no network flake. This is the single line that repairs ADR-0003's conformance guarantee.

**2. Rewrite the drift job to detect → PR.** Replace `_schema_drift_workflow()` (`ghagen_workflows.py:166–206`) so it refreshes the Snapshot _and_ regenerates types, then opens a PR carrying the fix instead of an issue carrying a diff:

```python
def _schema_drift_workflow() -> Workflow:
    return Workflow(
        name="Schema Drift Check",
        on=On(
            schedule=[ScheduleTrigger(cron="0 9 * * 1")],
            workflow_dispatch=WorkflowDispatchTrigger(),
        ),
        permissions=Permissions(
            contents=PermissionLevel.WRITE,        # was READ
            pull_requests=PermissionLevel.WRITE,   # new
            issues=PermissionLevel.WRITE,          # kept for the fallback
        ),
        jobs={
            "check-drift": Job(
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Set up uv", uses="astral-sh/setup-uv@v7"),
                    Step(name="Setup Node.js", uses="actions/setup-node@v6",
                         with_={"node-version": "24"}),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Install TS deps", run="npm ci",
                         working_directory="packages/typescript"),
                    # Refresh the Snapshot AND regenerate the types from it, so the
                    # PR is a complete, mergeable fix rather than a diff to reproduce.
                    Step(name="Refresh Snapshot", run="uv run python -m ghagen_schema sync"),
                    Step(name="Regenerate types", run="uv run python -m ghagen_schema generate"),
                    Step(
                        name="Open PR on drift (else issue fallback)",
                        run="""
                            if git diff --quiet; then
                              echo "No schema drift."
                              exit 0
                            fi
                            BRANCH="schema-drift/$(date +%Y%m%d)"
                            if gh pr list --head "$BRANCH" --json number \\
                                 --jq '.[0].number' | grep -q .; then
                              echo "Drift PR already open for $BRANCH."
                              exit 0
                            fi
                            git config user.name  "github-actions[bot]"
                            git config user.email \\
                              "41898282+github-actions[bot]@users.noreply.github.com"
                            git checkout -b "$BRANCH"
                            git add schema/ packages/typescript/src/schema/
                            git commit -m "chore(schema): sync upstream drift + regenerate types"
                            git push -u origin "$BRANCH"
                            gh pr create --title "Schema drift: refreshed Snapshot + types" \\
                              --body "Automated upstream schema refresh. Review the Snapshot \\
                                      diff and the regenerated types before merging." \\
                              --label schema-drift
                        """,
                        env={"GH_TOKEN": str(expr.secrets["GITHUB_TOKEN"])},
                    ),
                ],
            ),
        },
    )
```

This reuses the exact branch-guard / `git config` / `gh` idiom already proven in `_ghagen_update_action()`'s "Create PR" step (`ghagen_workflows.py:678–748`) and the homebrew-bump step, so it introduces no new mechanism.

## What sits behind the seam

Callers see three verbs. Hidden behind them:

- **The manifest as a validated interface.** `manifest.py` becomes the one loader and the sole owner of the filename convention. A single `load_manifest()` returns typed entries and, for each, derives the generated-types filename by the `_schema.json → -types.generated.ts` rule — **validating loudly** that every `filename` ends in `_schema.json` (raise, listing the offending entry, instead of silently no-op'ing). The TS codegen calls the same derivation rather than re-implementing the regex, so the convention has exactly one definition and one failure mode. (Mechanically: TS reads a tiny derived index the Python tool writes next to the manifest, or re-implements the _validated_ rule against a shared fixture test — either kills the untested regex at `generate-types.ts:56`.)
- **Deterministic serialization** (`sort_keys`, trailing newline) — today's `_serialize`, unchanged.
- **oxfmt-stable codegen.** `generate` runs `json-schema-to-typescript` then reformats with `oxfmt` (today's `generate-types.ts:83–86`). Commit `fb688cc` established _why_ this matters: `json-schema-to-typescript` ships its own prettier whose style fights the repo's `oxfmt`, so without the reformat pass regeneration and `fmt.sh` churn the files and `check` would flap. The same commit made generated **headers** environment-independent (the `.ghagen.yml` app-root marker so embedded paths are relative, not absolute). Both properties are preconditions for a reliable `check`: identical inputs must produce byte-identical output on any machine. The `generate-types.ts` `BANNER` is already a static string, so it is safe.
- **One repo-root resolver per port** (see Test impact).

## Migration plan

Pre-1.0; clean breaks are fine (no compat shims).

1. Create `scripts/ghagen_schema/` and move the body of `schema_sync.py` into `sync.py`; add `generate.py` (shells `npm --prefix packages/typescript run generate-types`) and `check.py`. Add `__main__.py` with the three-verb argparse dispatch. Delete `packages/python/scripts/schema_sync.py`.
2. Add `manifest.py`; route both `sync` and the TS codegen through the validated loader + filename derivation. Add a test that a non-`_schema.json` entry raises.
3. Add `pythonpath = ["scripts"]` to `[tool.pytest.ini_options]`; delete `packages/python/tests/test_schema/conftest.py` (the `sys.path` hack).
4. Add `paths.py` (Python) and `src/paths.ts` (TS); replace the six duplicated resolutions.
5. Update `.github/ghagen_workflows.py`: add the `check` step to `lint-meta`; rewrite `_schema_drift_workflow()`. Regenerate workflows via `ghagen` and commit the YAML (the `check-sync` job keeps them honest).
6. Update docs/CLI references (the `docs/src/content/docs/*/cli.md` pages already touched by `fb688cc`) and the `schema_sync.py` usage line.

## Test impact

- **Python path helper.** `paths.py` exposes `repo_root()` (walk up to the directory containing `schema/`, **asserting** it is found — no bare `parents[N]`), plus `SCHEMA_DIR` and `FIXTURES_DIR`. `test_integration/conftest.py:14–21`, `test_deps.py:23–30`, and `test_conformance.py:43` all import it. The brittle `parents[4]` dies; the two walk-up copies collapse to one.
- **TS path helper.** `src/paths.ts` exports `REPO_ROOT`, `SCHEMA_DIR`, `FIXTURES_DIR`, resolved once from `import.meta.dirname` with an assertion that `schema/` exists there. `test-utils.ts:7,9`, `conformance.test.ts:37`, and `generate-types.ts:16–19` import it; the `../../../../` constants and the codegen's private two-hop math go away.
- **Manifest validation test.** A unit test feeds a bad entry (`"filename": "workflow.json"`) and asserts the loader raises, so the filename convention gains the enforcement it never had.
- **New `check` verb is itself the test surface** for staleness: the interface is the test. Running it in `lint-meta` is the assertion.
- **Conformance-sweep parity guard (proportional).** Lift the _scope table_ — snapshot → scope name → schema path(s) — out of both ports into shared data at `schema/conformance-scopes.yml` (the model/spec binding stays per-port, since a Python type or a TS `ModelSpec` cannot be serialized). Each sweep then reads the scope set from that file and maps its own models onto it, and each sweep asserts `set(port scope keys) == set(shared scope keys)`. Divergence now fails a test instead of drifting silently. This is the cheap structural guard; it reuses the exact pattern already proven for `conformance-gaps.yml`, so it adds a file, not a mechanism. (A heavier alternative — each sweep emitting a normalized coverage manifest for CI to diff — is not worth it here.)

## Risks & alternatives

- **Auto-PR on upstream churn (main risk).** SchemaStore can change often; naive auto-PR could be noisy. Mitigations: the job is weekly, not per-push; it dedupes on a date-stamped branch (`schema-drift/YYYYMMDD`) so a run never stacks duplicate PRs; and a PR is _reviewed_, never auto-merged — the human still gates every Snapshot change, exactly as today, but now reviews a complete fix (Snapshot + regenerated types) instead of reproducing it by hand. Net risk is lower than the status quo, where the fix is discarded and must be redone locally.
- **Bot PRs don't trigger CI.** `GITHUB_TOKEN`-authored events do not start new workflow runs (already documented in `_release_workflow()`'s homebrew comment, `ghagen_workflows.py:293–295`). So the drift PR's own CI (including the new `schema check`) will not run automatically. Options, cheapest first: (a) accept it and rely on the reviewer plus a manual re-run; (b) have the job run `uv run python -m ghagen_schema check` itself before pushing and note the result in the PR body; (c) use a PAT if pre-merge CI on the PR is required. Recommend (b) — it keeps the guarantee visible without new secrets.
- **Keep the issue path as fallback.** Retain `issues: write` and open an issue only when PR creation is not possible (e.g. a fork without push, or `gh pr create` failing). Honest and cheap.
- **Alternative staleness designs considered.** _Hash the manifest / Snapshot_ instead of regenerate-and-diff: rejected — a hash catches Snapshot edits but not a `json-schema-to-typescript` version bump that changes output for an unchanged Snapshot, which is precisely a staleness case. Regenerate-and-diff catches both and is only viable _because_ `fb688cc` made codegen output deterministic (oxfmt + env-independent headers). _Keep the two scripts, just document the order_: rejected — it leaves the guarantee unenforced and the seam un-owned, which is the whole problem.

## ADR / CONTEXT.md impact

- **ADR-0003 amendment (append a Consequences note).** ADR-0003 already establishes the single canonical Snapshot, dev-only sync, hand-written models, and schema-as-conformance-target — this proposal _extends_ it and contradicts nothing. Add: (1) the three-verb `ghagen_schema` orchestrator is the interface to that pipeline; (2) TS author-conformance is now actively enforced in CI by `schema check` (previously it "rested on `tsc` happening to collide"), closing the silent-weakening gap the ADR's compile-time story implicitly assumed; (3) drift now detect → PR, not detect → issue. Reaffirm the ADR's explicit warning that the two ports enforce _different_ things (TS compile-time, Python runtime) — the shared scope table drives _coverage parity_, not false structural parity, and does not re-wire generated Python models back in.
- **`packages/*/CONTEXT.md`** should point at the new shared path helpers so future tests reach for `paths` instead of hand-rolling `../../../../` or `parents[N]`.

## Out of scope / adjacent gaps

- **`check-deps` action has zero CI exercise.** `check-deps/action.yml` (generated from `_ghagen_update_action()`, `ghagen_workflows.py:560–786`) — its PR/issue shell logic is never run in CI, in contrast to `check-synth`, which the `test-action` job exercises (`ghagen_workflows.py:149–161`). Worth a smoke job, but that is CI _test coverage_, not schema-module deepening — track separately.
- **actionlint version drift.** `.pre-commit-config.yaml:26` pins `rhysd/actionlint` at `v1.7.11` while `ghagen_workflows.py:77` pins `v1.7.12`. Local and CI lint can disagree. A one-line bump, unrelated to this proposal — track separately.
