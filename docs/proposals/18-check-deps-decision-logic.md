# 18 — Pull `check-deps`'s decision logic across the CLI seam

**Status:** proposed | **Ports:** both (plus the shipped composite actions and the workflow generator) | **Effort:** L | **Depends on:** [**17**](./17-upgrade-report-renderer-module.md) (upgrade-report renderer → `pin/render`) — `deps update` writes its body through 17's `render_upgrade_report` / `renderUpgradeReport`, and `plan_update` **reads** 17's `checked_versions` / `checked_lockfile` rather than re-deriving them from `mode`. 17 in turn declares **20** → **19** → **14**, so the whole chain is 20 → 19 → 14 → 17 → **18, last**. **19 is also a direct edge**: this proposal inserts a `## ghagen deps update` section into both `cli.md` pages inside the region 19 restructures, so 19 lands first there too.

Effort is **L**, not M: this rewrites 91 non-blank lines of untested bash inside a _tag-pinned published_ composite action, adds a module, a CLI command and a new composite input/output surface in both ports, and its central regression guard is a CI job — three generated artifacts (`check-deps/action.yml`, `.github/workflows/ci.yml`, one new scheduled workflow) that **no local gate executes**, so every iteration costs a push.

## Files involved

Line counts are `wc -l` on `main` at `e7a972c`. **Note on paths:** the shipped action lives at
`check-deps/action.yml` at the **repo root**, not under `.github/actions/`. The survey this
proposal was written from used the wrong prefix; every citation below was re-read after the
`group`-input hotfix (`558fca4`) landed.

### Modified

| Path                                           | Lines | Role in this proposal                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ---------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `.github/ghagen_workflows.py`                  | 845   | **Source of truth.** `_ghagen_update_action()` (612-833) rewritten: three `run:` blocks → two, `source`/`dry-run` inputs and composite `outputs:` added. `_ci_workflow()` (28-175) gains two steps inside the existing `test-action` job (161-173). One new `_check_deps_smoke_workflow()` beside `_schema_drift_workflow()` (178-258). **The ADR-0003 staleness-guard comment at `:86-90` is not in any hunk and must survive** — see _Risks_ on `18 — 23`. |
| `check-deps/action.yml`                        | 187   | **Generated.** Regenerated, never hand-edited (`uv run ghagen synth`). Ends ~90 lines shorter.                                                                                                                                                                                                                                                                                                                                                               |
| `.github/workflows/ci.yml`                     | 169   | **Generated.** Two steps appended inside `test-action` (159-169). No new job, no other hunk — see _Risks_ on the `18 — 23` edge.                                                                                                                                                                                                                                                                                                                             |
| `packages/python/src/ghagen/cli/deps.py`       | 360   | New `deps update` command mounted on `deps_app` (24-27). `_ensure_lockfile_path` (30-35) stays as-is for `pin`/`check-synced`.                                                                                                                                                                                                                                                                                                                               |
| `packages/typescript/src/cli/deps.ts`          | 389   | Mirror: `depsUpdate` + its `buildDepsCommand()` registration (345-378) + test re-export (381-389).                                                                                                                                                                                                                                                                                                                                                           |
| `packages/python/src/ghagen/pin/__init__.py`   | 58    | Export **two** names (`UpdatePlan`, `plan_update`) from a new `from ghagen.pin.plan import (…)`, landing at `:29` in the isort region `:3-31`, plus two entries in the alphabetical `__all__` at `:33-58`. **Hand-merge** — see _Risks_.                                                                                                                                                                                                                     |
| `packages/typescript/src/pin/index.ts`         | 46    | Mirror barrel export. **Five claimants on this file** — see _Risks_.                                                                                                                                                                                                                                                                                                                                                                                         |
| `packages/typescript/src/index.ts`             | 203   | Mirror top-level re-export inside the `from "./pin/index.js"` block that ends at `:203`. **Seven claimants.**                                                                                                                                                                                                                                                                                                                                                |
| `packages/python/tests/test_cli/test_deps.py`  | 911   | New `TestDepsUpdate` class appended. **Shared with 17**, which cuts this file 911 → ~330 — see _Risks_.                                                                                                                                                                                                                                                                                                                                                      |
| `packages/typescript/src/cli/deps.test.ts`     | 261   | Mirror; 17 cuts it 261 → ~130.                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `docs/src/content/docs/python/cli.md`          | 210   | New `## ghagen deps update` section inserted _within_ `## ghagen deps upgrade`'s block, after its `### Options` table (169-178) and **above** the `### Exit codes` block 19 deletes (179-185).                                                                                                                                                                                                                                                               |
| `docs/src/content/docs/typescript/cli.md`      | 223   | Mirror: after `### Options` (182-191), above 19's deletion at 192-198.                                                                                                                                                                                                                                                                                                                                                                                       |
| `docs/specs/0005-typed-engine-report-seam.md`  | 439   | **Amended, not rewritten** (17's precedent at `17` §Risks & alternatives). §3 _Design — Part B: dogfood `check-deps`_ (186-370) specifies the shape this proposal replaces; §5's optional-smoke line (403-404) becomes mandatory and split in two. `:348-349` is **superseded** — see _ADR / CONTEXT.md impact_.                                                                                                                                             |
| `docs/issues/05-check-deps-action-untested.md` | 7     | Status → resolved; point at the two new CI exercises.                                                                                                                                                                                                                                                                                                                                                                                                        |

### New

| Path                                                             | Lines      | Role in this proposal                                                                                                                                                                                   |
| ---------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/src/ghagen/pin/plan.py`                         | new (~85)  | `UpdatePlan` + `plan_update()` — the three decision rules, typed and pure.                                                                                                                              |
| `packages/typescript/src/pin/plan.ts`                            | new (~90)  | Mirror.                                                                                                                                                                                                 |
| `packages/python/tests/test_pin/test_plan.py`                    | new (~180) | Offline decision-table tests; `lockfile=None` is case 1. Builds its own `App(root=tmp_path)` + hand-constructed reports; **imports nothing from `test_pin/test_engine.py`** — see _Risks_ on `16 — 18`. |
| `packages/typescript/src/pin/plan.test.ts`                       | new (~180) | Mirror, driven by the same shared table.                                                                                                                                                                |
| `packages/python/tests/test_integration/test_shipped_actions.py` | new (~60)  | Artifact test over the repo's own generated `check-deps/action.yml`. **Red on `main` today.** Python-only, deliberately — see _Test impact_.                                                            |
| `fixtures/expected/update_plan.json`                             | new (~25)  | Cross-port golden for the emitted plan shape, mirroring `fixtures/expected/upgrade_report.json`.                                                                                                        |
| `fixtures/actions/all_pinned/ghagen_workflows.py`                | new (~25)  | CI fixture: every ref written as a 40-char SHA → nothing pinnable, **zero HTTP requests**, `action=none`. Drives the per-PR hermetic exercise.                                                          |
| `fixtures/actions/lockfile_none/ghagen_workflows.py`             | new (~25)  | CI fixture: `App(lockfile=None)` with one deliberately ancient `uses:` ref. The H7 reproducer; drives the **scheduled** exercise.                                                                       |
| `.github/workflows/check-deps-smoke.yml`                         | new (~40)  | **Generated.** `schedule` + `workflow_dispatch`, modelled on `schema-drift.yml` (68) — the repo's only networked-with-token workflow. Carries the two cases that cannot be hermetic.                    |

**Deliberately not in the table:** `.github/workflows/schema-drift.yml` (68) and its generator source
`.github/ghagen_workflows.py:222-254`. The brief asks for the PR-raising shell to be factored into
one place; _Proposed interface_ §4 shows the diff between the three copies and argues, on the
deletion test, that folding schema-drift's copy into a shared generator helper produces a
six-parameter pass-through. This proposal collapses check-deps's three copies into one and stops
there. Also not in the table: `packages/typescript/src/_docs-api-*.ts` — no TypeDoc entry point
covers `pin/` today (`grep -rn 'UpgradeReport\|VersionBump' packages/typescript/src/_docs-api-*.ts`
is empty), so exporting `UpdatePlan` from the barrel does not change the docs surface. And not
`packages/{python,typescript}/CONTEXT.md`: 18 is not in the round's region assignment and 17 already
carries the **UpgradeReport** glossary entry; this proposal's CONTEXT.md wish-list is one appended
Surface-notes bullet plus one glossary term, described in the last section and **not** made here.

## Problem

`check-deps` is the product feature AGENTS.md names as the reason ghagen exists at all — "Custom
ghagen github action to handle this automatically like dependabot or renovate / Generate PRs or
issues (configurable)". It is implemented as **112 lines of bash** (91 non-blank) spread over five
`run:` blocks in `check-deps/action.yml` — lines 53-57, 62-80, 86, 91-150, 158-184. Not one of those
lines is executed by any test or CI job. `grep -rn 'check-deps' packages/python/tests
packages/typescript/src --include='*.py' --include='*.ts'` returns nothing. (The survey said
"roughly 140 lines"; the real figure is 112/91.)

That bash is not glue. It contains the entire decision procedure for the feature.

### 1. A fourth independent encoding of the report shape

The `UpgradeReport` shape is currently written down in four places, in four languages, three of
which are type-checked and one of which is not:

1. **Python model** — `packages/python/src/ghagen/pin/engine.py:162` (`VersionBump`), `:173`
   (`LockfileStaleEntry`), `:183` (`UpgradeReport`, fields `version_bumps` / `lockfile_stale` /
   `changed_files` / `warnings`).
2. **TypeScript model** — `packages/typescript/src/pin/engine.ts:160`, `:170`, `:179`
   (`versionBumps` / `lockfileStale`, camelCase on the report, snake_case on the entries).
3. **The CLI's wire shape** — the `--format json` assembly plus the two serializers, which re-type
   the key names as string literals: `packages/python/src/ghagen/cli/deps.py:229-239` and
   `:252-274`; `packages/typescript/src/cli/deps.ts:212-223` and `:296-320`. This exists once per
   port but is held byte-identical by the shared golden
   `fixtures/expected/upgrade_report.json`, so it counts as one encoding.
4. **The action's reader** — two `python3 -c` one-liners inside a YAML block scalar, generated from
   a Python string literal:

   ```bash
   # check-deps/action.yml:67-68  (generated from .github/ghagen_workflows.py:702-703)
   VERSION_BUMPS=$(python3 -c "import json; d=json.load(open('$JSON_FILE')); print(len(d.get('version_bumps',[])))")
   LOCKFILE_STALE=$(python3 -c "import json; d=json.load(open('$JSON_FILE')); print(len(d.get('lockfile_stale',[])))")
   ```

Encoding 4 is the only one with no type checker, no test, and no golden file.
`docs/architecture-deepening-plan.md:203-217` (§6, "Deps render formats — heredocs die (decided)")
called out a _third_ encoding and killed it — the Python heredocs that used to render the PR/issue
markdown, replaced by `deps upgrade --format {json,pr-body,issue-body}`. What survived that surgery
is the part that was never about rendering: reading the report back in order to **decide what to do
next**.

The `python3 -c` pair is also a supply-chain oddity in its own right: a composite action that has
just `pip install ghagen`'d (`action.yml:51-58`) reaches for the runner's ambient `python3` to parse
ghagen's own output.

### 2. The `--format json` contract the action reads is mode-dependent — **resolved by 17, before this lands**

`--mode versions` emits only `version_bumps` (`cli/deps.py:231-238`); `--mode lockfile` emits only
`lockfile_stale`. But the "nothing to do" early return emits **both** keys regardless of mode
(`cli/deps.py:213-227`, TS `cli/deps.ts:197-210`). Verified on `main`:

```
$ uv run ghagen deps upgrade --check --format json --mode versions --config <fixture>
  → keys: ['version_bumps']
$ uv run ghagen deps upgrade --check --format json --mode lockfile --config <fixture>   # nothing found
  → keys: ['lockfile_stale', 'version_bumps']
```

The action survives this only because `d.get('lockfile_stale',[])` defaults a _missing_ key to
empty — which is also exactly how it acquires defect H7b below.

**This is LIVE on `main` and is 17's to fix, not this proposal's.** 17 makes key presence follow
`report.checked_versions` / `report.checked_lockfile` unconditionally (`17` §(b) pin/render — one function, four formats), which deletes the
carve-out. It is stated here because it is the reason encoding 4 works by accident today, and
because the reader needs to know that by the time 18 lands, the JSON the bash was reading has
already changed shape underneath it — a second, independent argument for deleting the reader rather
than repairing it.

### 3. H7 — the lockfile-refresh guard does not know `lockfile=None` exists

`lockfile=None` is a supported, documented `App` configuration in both ports:
`packages/python/src/ghagen/app.py:42` (`lockfile: str | Path | None = DEFAULT_LOCKFILE_PATH`),
`:69` ("Set to `None` to disable lockfile auto-loading"), `:81`; TypeScript `app.ts:60-63`, `:80-81`.
The pin engine honours it — `upgrade`'s lockfile stage is gated on it
(`pin/engine.py:261`: `if check_lockfile and app.lockfile_path is not None:`; TS `engine.ts:275`).

The action's guard is not:

```bash
# check-deps/action.yml:127-130  (generated from .github/ghagen_workflows.py:769-772)
# Refresh lockfile
if [ "${{ steps.detect.outputs.lockfile_stale }}" != "0" ] || [ "${{ steps.detect.outputs.version_bumps }}" != "0" ]; then
  ghagen deps pin --config "${{ inputs.config }}" --update
fi
```

**Status: LIVE.** Every link verified end to end:

- **`lockfile_stale` is always `0` under `lockfile=None`.** `upgrade` skips the stage
  (`engine.py:261`), so the JSON carries `"lockfile_stale": []`.
- **`version_bumps` can be non-zero.** Confirmed against a fixture `App(lockfile=None)` holding
  `actions/checkout@v4`:

  ```
  $ uv run ghagen deps upgrade --check --format json --mode all --config <lockfile-none fixture>
  { "version_bumps": [ { "uses": "actions/checkout@v4", ..., "severity": "major" } ],
    "lockfile_stale": [] }                                                     EXIT=0
  ```

- **So the guard's second clause fires.**
- **`ghagen deps pin` then exits 1.** `_ensure_lockfile_path` (`cli/deps.py:30-35`) is called before
  any work (`:78`) and does `typer.Exit(1)`. Confirmed:

  ```
  $ uv run ghagen deps pin --config <lockfile-none fixture> --update
  Error: lockfile is disabled (lockfile=None on App)                          EXIT=1
  ```

  The TypeScript port is the same shape — `ensureLockfilePath` throws `CliError`
  (`cli/deps.ts:42-47`, called at `:66`).

- **`set -euo pipefail` is in force** at the top of that step (`action.yml:91`), so the step aborts.
- **Replayed the guard verbatim** with the fixture and the real detect outputs:

  ```
  -- guard: [ 0 != 0 ] || [ 1 != 0 ]
  -- guard fired; running deps pin --update
  Error: lockfile is disabled (lockfile=None on App)
  STEP EXIT=1        ("-- REACHED COMMIT/PUSH" never printed)
  ```

The step dies at `action.yml:129`, after `git checkout -b` (`:120`) and after the version bumps were
written to the user's source files (`:124`), and before `git add` / `git commit` / `git push` /
`gh pr create` (`:145-149`). **One correction to the survey's phrasing:** the branch and its
uncommitted work exist only inside the ephemeral runner workspace and are destroyed with it —
nothing is pushed. The durable, user-visible outcome is a **red job and no PR, on every scheduled
run, forever**, for any repo that sets `lockfile=None`. The pre-rendered `$BODY_FILE`
(`action.yml:115-116`) also leaks, since the `rm -f` at `:150` is never reached.

The root cause is structural, not a typo: the guard is reconstructing `refresh_lockfile` from a
serialized report that deliberately does not carry the one fact needed to compute it — whether the
App has a lockfile at all. 17 keeps it that way on purpose: `checked_lockfile` is true even when
`app.lockfile_path is None` (`17` §Scope boundaries vs siblings), so the _only_ place the two can be told apart is a function
that holds the `App`.

### 3b. H7b — `mode: versions` writes the lockfile anyway

The same guard, same line. With `mode: versions` the JSON has no `lockfile_stale` key at all
(verified above), so `LOCKFILE_STALE=0` — but any version bump makes the second clause true and
`ghagen deps pin --update` re-resolves **every** ref and rewrites `.ghagen.lock.yml`. The action's
own input documents `mode` as a _detection_ mode — "Detection mode: 'versions', 'lockfile', or
'all'" (`action.yml:9-12`) — so writing the lockfile under `mode: versions` is out of contract.
**LIVE**, and independent of H7: it needs neither `lockfile=None` nor any code change. Reproduced
with a real md5 change to `.ghagen.lock.yml` under `mode: versions`.

### 3c. `|| true` does not suppress the failure it appears to suppress

`action.yml:65` ends the detect invocation with `|| true`, and the very next lines read the file it
was supposed to write. The `|| true` is not tolerance — it is a **downgrade**. Measured both ways,
with a stub CLI that exits 2 after printing one diagnostic line, replaying `action.yml:62-71`
verbatim under `set -euo pipefail`:

|                              | step exit | what the log ends with                                                                                                                               |
| ---------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **with `\|\| true`** (today) | **1**     | a ~20-line `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` traceback from `python3 -c`; the CLI's message is nowhere in it |
| **without `\|\| true`**      | **2**     | one line — the CLI's own message                                                                                                                     |

So the exit code the CLI chose (2, for a bad flag value — `cli/deps.py:166-180`) is destroyed and
replaced with 1, and a one-line diagnostic is replaced with a traceback from the _reader_, about the
empty file, not about the failure. Every diagnosable CLI failure — bad `--mode`, missing config, an
unreachable API — is laundered the same way. **LIVE**, and inside this rewrite's blast radius: the
whole detect step is deleted, so it is fixed here, with a red-green guard (see _Test impact_),
rather than filed.

### 4. Four networked CLI invocations per PR run, three of them the same sweep

Counted by reading `check-deps/action.yml`, not assumed. The survey said three; it is four.

| #   | Line | Command                                               | What it costs                                                                  |
| --- | ---- | ----------------------------------------------------- | ------------------------------------------------------------------------------ |
| 1   | 65   | `deps upgrade --check --format json --mode <mode>`    | full sweep: `list_tags` per distinct owner/repo + `resolve_ref` per pinned ref |
| 2   | 116  | `deps upgrade --check --format pr-body --mode <mode>` | **the identical sweep again**, for the body                                    |
| 3   | 124  | `deps upgrade --mode versions`                        | tag sweep a third time, to apply                                               |
| 4   | 129  | `deps pin --config … --update`                        | `resolve_ref` for every ref                                                    |

Plus two `gh` calls (`:107` list, `:149` create). The issue path runs two full sweeps (`:65`, `:181`).

Nothing is shared between them: the per-repo tag cache is a process-local dict built fresh inside
`upgrade` (`pin/engine.py:226`; TS `engine.ts:234`), so four processes means four cold caches. The
CLI itself warns about the budget — "60 req/hr limit" (`cli/deps.py:48-52`) — and the action passes
a token (`action.yml:81-82`), but a repo with many distinct action repos still pays 3-4× the
necessary rate-limit spend and 3-4× the wall time, and gets a **non-atomic** result: sweeps 1 and 2
can observe different upstream tag sets, so the PR body can disagree with the commit it describes.

The two `--check` sweeps exist only because the action needs the same report twice in two different
renderings, from two different processes. That is a seam problem, not a performance problem.

### 5. Three copies of the raise-a-PR/issue shell

Located and diffed. Two are full PR-raising copies; the third is a partial that duplicates two
fragments verbatim.

- **A** — `check-deps/action.yml:91-150` (Create PR), from `ghagen_workflows.py:732-793`
- **B** — `check-deps/action.yml:158-184` (Create issue), from `ghagen_workflows.py:800-828`
- **C** — `.github/workflows/schema-drift.yml:38-65` (Open PR on drift), from `ghagen_workflows.py:224-252`

A and B share the label-args loop **byte-for-byte except one comment word**. `diff` of
`action.yml:96-104` against `:162-170`:

```
1c1
<       # Build label args as an array to avoid eval
---
>       # Build label args as an array
```

Nine lines, twice, differing only in a comment. They also share the dedupe-then-`exit 0` idiom
(`:107-111` vs `:173-177`) with the same `2>/dev/null || echo ""` swallow.

Where A and C actually disagree:

|                  | A — check-deps PR                                                   | B — check-deps issue                                                 | C — schema-drift                                                  |
| ---------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------- |
| branch           | `${{ inputs.branch-prefix }}$(date +%Y%m%d)` (`:93`)                | —                                                                    | hard-coded `schema-drift/$(date +%Y%m%d)` (`schema-drift.yml:44`) |
| dedupe           | `gh pr list --head` + `-n "$EXISTING_PR"` (`:107-111`)              | `gh issue list --search "$TITLE in:title" --state open` (`:173-177`) | `gh pr list --head … \| grep -q .` (`:45-49`)                     |
| dedupe failure   | `2>/dev/null \|\| echo ""` — a `gh` failure reads as "no PR exists" | same                                                                 | no swallow                                                        |
| staged paths     | `git add -A` (`:145`)                                               | —                                                                    | `git add schema/ packages/typescript/src/schema/` (`:54`)         |
| push             | `git push -u origin` (`:147`)                                       | —                                                                    | `git push --force-with-lease -u origin` (`:56`)                   |
| empty-diff guard | `git diff --quiet && git diff --cached --quiet` (`:133`)            | —                                                                    | `git diff --quiet` only (`:40`) — misses staged changes           |
| failure fallback | none — step goes red                                                | —                                                                    | `\|\| gh issue create` (`:56-65`)                                 |
| labels           | `--label` per parsed input (`:96-104`)                              | same                                                                 | hard-coded `--label schema-drift` (`:59`)                         |

Two defects fall out of that table:

- **The dedupe swallow is a duplicate-PR hazard.** `EXISTING_PR=$(gh pr list … 2>/dev/null || echo "")`
  (`:107`): a transient API failure yields an empty string, which the next line reads as "no PR
  exists", and the action opens a second PR for the same branch. Reachable today with no code
  change; requires a `gh` failure to manifest. **LIVE (transient-triggered).**
- **Same-day re-run after a closed PR fails.** `gh pr list` defaults to open PRs only (documented
  `gh` behaviour, not a repo fact), so a closed-but-not-deleted `ghagen-update/YYYYMMDD` branch
  passes the dedupe and then `git push -u origin` (`:147`) is rejected non-fast-forward. **LIVE.**
  C sidesteps this with `--force-with-lease` (`:56`); _Proposed interface_ §3 explains why copying
  that is the _wrong_ fix and what this proposal does instead.

### Net

The action's bash is a **shallow re-implementation** of a decision procedure that the CLI is in a
strictly better position to make: the CLI holds the typed report _and_ the `App`, so it knows the
one fact (`lockfile_path`) that the serialized report deliberately drops. Every bug above — H7,
H7b, the exit-code laundering, the duplicate sweeps, the two drifted dedupes — is a consequence of
re-deriving decisions from a serialization instead of asking the module that made it.

## Current interface

What a caller of `check-deps` must know today, in order to use it:

- **`deps upgrade --check --format json`** emits `version_bumps` / `lockfile_stale` arrays — but
  which keys are present depends on `--mode` _and_ on whether anything was found (§2).
- The caller must itself compute: `total = len(version_bumps) + len(lockfile_stale)`; "apply version
  bumps?" = `version_bumps != 0`; "refresh the lockfile?" = `lockfile_stale != 0 || version_bumps != 0`;
  "PR or issue?" from its own input; the branch name; the title; the commit message; the label list.
- The caller must know the correct **ordering**: render the body _before_ applying, because
  `--check` reports pending state and a post-apply report is empty (the comment at
  `action.yml:113-114` is the only place this invariant is written down).
- The caller must know that `deps pin` exits 1 when the App has no lockfile — a fact stated nowhere
  in the report it is given.
- The caller pays for a fresh sweep per invocation; there is no way to get the report and the body
  and the applied changes from one process.

That is an interface whose complexity is essentially equal to its implementation, spread across a
process boundary and a language boundary. `--format json` is a **shallow** seam: it exports the
data and keeps every decision on the caller's side of the wall.

The Python and TypeScript ports are at parity here and neither is better: `cli/deps.py:229-249` and
`cli/deps.ts:212-230` are the same shape. Only Python is reachable from the shipped actions — and
that is true of **both** of them: `check-deps/action.yml:54,:56` and `check-synth/action.yml:34,:36`
each `pip install` the Python port. There is no path by which CI, or a consumer, exercises the
TypeScript port through a shipped action; the TS half of this proposal is library parity, verified
by `vitest`, not by any action.

## Proposed interface

Move the decisions to the side of the seam that has the facts. Three pieces.

### 1. `pin/plan` — `UpdatePlan`, a typed answer to "what should I do?"

New module beside 17's `pin/render`. It is pure: `App` config plus an `UpgradeReport` in, decisions
out. No network, no filesystem, no markdown.

```python
# packages/python/src/ghagen/pin/plan.py
@dataclass(frozen=True)
class UpdatePlan:
    """What a caller should do about an UpgradeReport."""

    action: Literal["none", "create-pr", "create-issue"]
    total_updates: int
    apply_version_bumps: bool
    refresh_lockfile: bool          # False when the App has no lockfile — H7 lives here, once
    branch: str                     # "" unless action == "create-pr"
    title: str
    commit_message: str
    labels: tuple[str, ...]         # parsed + trimmed from the comma-separated input
    body_format: Literal["pr-body", "issue-body"] | None


def plan_update(
    app: App,
    report: UpgradeReport,
    *,
    output: Literal["pr", "issue"],
    branch_prefix: str,
    commit_message_prefix: str,
    labels: str,
    today: date,
) -> UpdatePlan: ...
```

**There is no `mode` parameter.** 17 adds `checked_versions` / `checked_lockfile` to `UpgradeReport`
specifically to collapse the `mode in (…)` derivation to one site (`17` §(b) pin/render — one function, four formats, `17` §Scope boundaries vs siblings); a `mode`
parameter here would make `plan.py` and `plan.ts` a fifth and sixth site, landing _after_ 17, in the
same round. The three rules read the report:

```python
total_updates = len(report.version_bumps) + len(report.lockfile_stale)

# No mode reference is needed at all: 17 guarantees version_bumps is empty
# unless the versions stage ran.
apply_version_bumps = bool(report.version_bumps)

refresh_lockfile = (
    app.lockfile_path is not None        # H7  — the fact the payload deliberately drops
    and report.checked_lockfile          # H7b — 17's flag, read, not re-derived
    and (bool(report.lockfile_stale) or apply_version_bumps)
)
```

`checked_lockfile` is load-bearing in exactly one of the two rules, and for a reason worth naming:
an empty `lockfile_stale` does not distinguish "the stage ran and found nothing" from "the stage was
not asked for", and the cascade clause (`or apply_version_bumps`) can drive a refresh with **zero**
stale entries. That is H7b in one line. `apply_version_bumps` needs no such flag, so this proposal
adds **zero** new derivation sites.

`today` is injected rather than read from the clock, so the dated branch name
(`f"{branch_prefix}{today:%Y%m%d}"`) and the issue title (`f"… ({today:%Y-%m-%d})"`) are testable
without freezing time — and ADR-0002's "no construction-time config globals" stance extends
naturally to "no ambient clock in a decision function".

TypeScript mirror is `packages/typescript/src/pin/plan.ts` with the same field names in camelCase on
the interface and the same snake_case on the emitted wire shape, exactly as `UpgradeReport` already
does (`pin/engine.ts:160-183`).

### 2. `ghagen deps update` — one process, one sweep, one answer

```
ghagen deps update
  --config PATH
  --mode versions|lockfile|all        (default all)
  --output pr|issue                   (default pr)
  --branch-prefix STR                 (default "ghagen-update/")
  --commit-message-prefix STR
  --labels STR                        (comma-separated, as the action input gives it)
  --body-file PATH                    (where to write the rendered body)
  --dry-run                           (plan only: no source edits, no lockfile write)
  --format github|json                (how to print the plan; default github)
  --token STR
```

`--mode` stays a CLI flag because `upgrade()` still takes it (`pin/engine.py:192-198`); the command
passes it _down_ to the engine and never re-reads it, taking `checked_*` back off the report.

Behaviour, in order, in one process:

1. Load the App, detect — **one** sweep, one warm tag cache.
2. `plan_update(app, report, …)` → `UpdatePlan`.
3. If `plan.body_format` is set and `--body-file` given, render it through **17**'s
   `pin/render` and write the file. This happens _before_ step 4, so the pre-apply invariant that
   is currently a bash comment (`action.yml:113-114`) becomes a statement in one function.
4. Unless `--dry-run`: if `plan.apply_version_bumps`, write the bumps back; if
   `plan.refresh_lockfile`, refresh the lockfile.
5. Print the plan.

`--format github` prints `$GITHUB_OUTPUT`-shaped lines, so the action's step is a single append:

```
action=create-pr
total_updates=3
branch=ghagen-update/20260731
title=chore(deps): update ghagen action dependencies
commit_message=chore(deps): update ghagen action dependencies
labels=deps,automated
refresh_lockfile=false
changed=true
```

`--format json` prints the same fields as JSON — the cross-port golden shape
(`fixtures/expected/update_plan.json`), asserted identically by both suites the way
`upgrade_report.json` already is (`packages/python/tests/test_cli/test_deps.py:763`,
`packages/typescript/src/cli/deps.test.ts:3`).

**The body never enters `$GITHUB_OUTPUT`** — it goes to `--body-file` and only the path travels
through the outputs. That sidesteps the multiline-output delimiter dance entirely, and it is why
`body_format` (not `body`) is on the plan.

Exit codes: 0 on success including `action=none`; 2 on bad flag values (matching
`cli/deps.py:166-180`); 1 on a real failure. No `|| true` anywhere. Under **19** these become rows
in 19's consolidated exit-code table rather than a per-command `### Exit codes` block.

### 3. The action: two `run:` blocks, zero decisions

`_ghagen_update_action()` (`ghagen_workflows.py:612-833`) is rewritten to:

```yaml
- id: plan
  run: |-
    set -euo pipefail
    ghagen deps update \
      --config "${{ inputs.config }}" --mode "${{ inputs.mode }}" \
      --output "${{ inputs.output }}" --labels "${{ inputs.labels }}" \
      --branch-prefix "${{ inputs.branch-prefix }}" \
      --commit-message-prefix "${{ inputs.commit-message-prefix }}" \
      --body-file "$RUNNER_TEMP/ghagen-body.md" \
      ${{ inputs.dry-run == 'true' && '--dry-run' || '' }} \
      --format github >> "$GITHUB_OUTPUT"

- name: Raise PR or issue
  if: steps.plan.outputs.action != 'none' && inputs.dry-run != 'true'
  run: |-
    <one block; branches on "${{ steps.plan.outputs.action }}">
```

#### The complete shipped-surface delta

`check-deps/action.yml:8-44` declares **nine** inputs today. All nine are enumerated, with what
happens to each:

| #     | Input                   | Lines | Default                       | After                                                                                                                                                                                            |
| ----- | ----------------------- | ----- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1     | `mode`                  | 9-12  | `all`                         | unchanged — forwarded to `--mode`                                                                                                                                                                |
| 2     | `output`                | 13-16 | `pr`                          | unchanged — forwarded to `--output`                                                                                                                                                              |
| 3     | `config`                | 17-20 | `.github/ghagen_workflows.py` | unchanged                                                                                                                                                                                        |
| 4     | `python-version`        | 21-24 | `'3.13'`                      | unchanged — consumed by `actions/setup-python` (`:48-50`)                                                                                                                                        |
| 5     | `ghagen-version`        | 25-28 | `''`                          | unchanged — consumed by the install step (`:51-58`)                                                                                                                                              |
| 6     | `token`                 | 29-32 | `${{ github.token }}`         | unchanged — still `GH_TOKEN` for `gh` and `--token` for the sweep                                                                                                                                |
| 7     | `labels`                | 33-36 | `''`                          | unchanged in name/default; **parsing moves into the CLI**, so the nine-line loop at `:96-104` (and its twin at `:162-170`) is deleted                                                            |
| 8     | `branch-prefix`         | 37-40 | `ghagen-update/`              | unchanged                                                                                                                                                                                        |
| 9     | `commit-message-prefix` | 41-44 | `''`                          | unchanged                                                                                                                                                                                        |
| **+** | **`source`**            | new   | `''`                          | local path to `pip install` instead of PyPI. Exact mirror of `check-synth/action.yml:21-24` (generator `:576-583`), including the `if [ -n … ]` install branch at `check-synth/action.yml:33-37` |
| **+** | **`dry-run`**           | new   | `'false'`                     | stop after the plan step; no source edits, no lockfile write, no git, no `gh`                                                                                                                    |

And the composite `outputs:` block it gains — **named exhaustively**, because these are the surface
a tag-pinned consumer can actually read:

| Output             | Value                                        | Meaning                                                       |
| ------------------ | -------------------------------------------- | ------------------------------------------------------------- |
| `action`           | `${{ steps.plan.outputs.action }}`           | `none` \| `create-pr` \| `create-issue`                       |
| `total_updates`    | `${{ steps.plan.outputs.total_updates }}`    | version bumps + stale lockfile entries                        |
| `refresh_lockfile` | `${{ steps.plan.outputs.refresh_lockfile }}` | `true` \| `false` — H7/H7b, observable                        |
| `branch`           | `${{ steps.plan.outputs.branch }}`           | `''` unless `action == create-pr`                             |
| `title`            | `${{ steps.plan.outputs.title }}`            | PR or issue title                                             |
| `changed`          | `${{ steps.plan.outputs.changed }}`          | whether anything was written (always `false` under `dry-run`) |

`ActionOutput` supports this already, with no model change. Note that `value` is **optional on the
model** — `packages/python/src/ghagen/models/action.py:134-135` declares
`description: str | None = None` and `value: str | None = None`, and only the class docstring
(`:123-130`) records that composite actions require `value`; nothing validates it. `Action.outputs`
is at `:247`, the spec key at `:97`, the emit order at `:100`.

**`source` is why `docs/issues/05` stayed open**, and it is worth being explicit about. Without it,
a CI job writing `uses: ./check-deps` gets the action definition from the working tree but
`pip install ghagen` from **PyPI** (`action.yml:56`) — so it would exercise the last published
release against the working tree's fixture, and a regression introduced in the same PR would pass.
`check-synth` has had the input since Part B of spec 0005 (`check-synth/action.yml:21-24`);
`check-deps` never did, which is precisely the gap that made the issue unactionable rather than
merely unaddressed.

Per-step outputs (`steps.plan.outputs.*`) are **not** readable by a consumer of the composite
action; only the `outputs:` block above is. Renaming the internal step `detect` → `plan` is
therefore invisible outside the action, which is what keeps the breaking set in §3 below as small as
it is.

#### Breaking changes, assembled

Three, all against a downstream that has pinned `check-deps` by tag:

1. **`mode: versions` stops refreshing the lockfile.** This is the H7b fix and it is the one with
   real blast radius: a repo running `mode: versions` on a schedule _is_ getting its
   `.ghagen.lock.yml` rewritten today, out of contract with the input's own description
   (`action.yml:9-12`), and will stop. **Migration: switch to `mode: all`**, which is the default
   and is what such a repo meant. Called out in the `docs/issues/05` closure note and in the
   `cli.md` section, because no test will catch it for the consumer.
2. **A `gh` dedupe failure now fails the step.** Today `2>/dev/null || echo ""` (`:107`, `:173`)
   converts a transient GitHub API failure into "no existing PR/issue" and opens a duplicate. After
   this change the step goes red. A downstream whose runs were quietly succeeding through API
   flakiness will start seeing red jobs — correctly, but visibly.
3. **The `Exit early` step and its "Everything is up to date." log line disappear**
   (`action.yml:84-87`). Anyone grepping job logs for that string loses it. The replacement is
   strictly better and machine-readable: `steps.<id>.outputs.action == 'none'` on the composite
   action itself.

Not breaking: `source` and `dry-run` are new inputs with inert defaults; the `outputs:` block is
additive; all nine existing input names, defaults and meanings are preserved.

**`--force-with-lease` is deliberately NOT copied from schema-drift.** Copying C's push mode
(`schema-drift.yml:56`) is the obvious way to close the same-day-reopen defect in §5, and it does
not work. `actions/checkout` fetches a single
ref, so no remote-tracking ref for `$BRANCH` exists in the runner's clone, and bare
`--force-with-lease` (no `<expect>` argument) rejects with "stale info" rather than force-pushing.
It would also add a fourth breaking change — a force-push that can overwrite a same-named branch a
human pushed to. The same-day-reopen case is fixed instead by asking the right question, which is
about the **branch**, not about open PRs:

```bash
set +e
git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null
LS=$?
set -e
case "$LS" in
  0) echo "Branch $BRANCH already exists; skipping."; exit 0 ;;
  2) : ;;                       # no such branch — proceed
  *) echo "::error::git ls-remote failed ($LS)"; exit "$LS" ;;
esac
```

This dedupes on the thing `git push` will actually collide with, distinguishes "absent" (2) from
"failed" (anything else) instead of swallowing both, and never rewrites history.

### 4. Factoring the raise shell — how far, and why not further

Inside `check-deps`, three shell blocks collapse to one: the label-args loop disappears from both
copies (the CLI hands back `labels=` already parsed and trimmed), the dedupe idiom is written once
(as `git ls-remote` above, plus `gh issue list` without the `|| echo ""` swallow for the issue
path), and PR-vs-issue becomes a `case` on `steps.plan.outputs.action` instead of two `if:`-guarded
steps that each re-derive their own title and body. Net: `check-deps/action.yml` loses roughly 90 of
its 112 bash lines, and the survivors do only git and `gh` — operations the CLI has no business
owning.

**Merging copy C into the same place fails the deletion test.** Suppose a generator-level
`_raise_step(...)` in `ghagen_workflows.py` served both `_ghagen_update_action()` and
`_schema_drift_workflow()`. The table in §5 shows the two callers disagree on branch source, dedupe
predicate, staged paths, push mode, empty-diff guard, and failure fallback — six axes, for exactly
two callers, and this proposal _widens_ one of them by giving check-deps a different dedupe
predicate from C's. The helper's interface would be as complex as either implementation: a
**shallow** module by definition, and a pass-through under the deletion test (delete it, and each
caller re-inlines the shell it already had, minus a parameter-threading exercise). Two adapters make
a real seam only when they agree about most of the interface; these agree about roughly a dozen
lines. Recorded criterion for revisiting: if a **third** PR-raising step appears, or if
schema-drift's fallback/force-push semantics converge with check-deps's, the helper becomes correct
— and by then the parameters will have been paid for by three callers rather than two.

## What sits behind the seam

`pin/plan` absorbs the decision procedure that today lives in a YAML block scalar. Concretely,
behind `plan_update` sit: the total-updates arithmetic, the stage→action mapping, the
lockfile-existence check, the dated-branch and title grammar, the commit-message prefixing, and the
label parsing. Behind `deps update` sit: the one-sweep detection, the pre-apply body ordering, and
the apply/refresh sequencing.

**Leverage.** The action's interface to all of that shrinks from "parse this JSON, then reconstruct
six decisions, in the right order, knowing a fact the JSON does not contain" to "run one command,
read `action`, `branch`, `title`, `labels`, `body_file`". The 112 lines of bash become ~25, none of
which decides anything.

**Locality.** The `lockfile=None` question is answered in exactly one place per port, next to the
`App` field that defines it. Today it is answered in `pin/engine.py:261`, in `cli/deps.py:30-35`,
and — wrongly — in `check-deps/action.yml:128`. After this change the third site does not exist and
the first two are the module the action calls.

**Deletion test — `pin/plan`:** delete it and the three rules reappear in three callers: the Python
`deps update` body, the TypeScript one, and (because nothing then stops it) the action's bash. The
`lockfile_path is not None` guard has to be re-derived at each. Three callers, and the module is
pure and network-free, so it is the only place those rules can be unit-tested offline. It earns its
keep.

**Deletion test — `deps update`:** it is not a pass-through over `deps upgrade` + `deps pin`.
Deleting it forces the caller back to the four-invocation sequence of §4, and re-externalizes the
pre-apply-body ordering invariant that currently survives only as a comment. It earns its keep.

**Deletion test — the `source` and `dry-run` inputs:** delete either and the CI exercise
`docs/issues/05` asks for becomes unimplementable — `source` because CI cannot install the working
tree, `dry-run` because the smoke would try to push a branch. Each is load-bearing for exactly the
thing it was added for, and `source` is not new surface in spirit: `check-synth` has carried it
since Part B of `docs/specs/0005` (`check-synth/action.yml:21-24`).

**Deletion test — `--format github`:** this one is close to a pass-through over `--format json`.
It survives because the alternative is `jq` in the action (a new runner dependency, replacing the
`python3` one we just removed) or a `python3 -c` one-liner (the thing this proposal deletes). Six
`key=value` lines written by the module that owns the keys is the cheaper interface. If a reviewer
disagrees, dropping `--format github` and having the action `>> "$GITHUB_OUTPUT"` a here-doc is a
contained retreat — but it re-opens the field-name-typo class of bug that has no test.

## Migration plan

Pre-1.0; clean breaks. `.github/ghagen_workflows.py` is the **source**; every YAML under `.github/`
and under `check-deps/` is **generated**. The implementer edits the generator and runs
`uv run ghagen synth`; `uv run ghagen check-synced` must pass byte-identically afterwards (it passes
on `main` today — verified: "All files are up-to-date."). Hand-editing `check-deps/action.yml`,
`ci.yml` or `schema-drift.yml` is a defect, not a shortcut.

1. **`pin/plan`, both ports.** `UpdatePlan` + `plan_update`, plus the offline decision-table tests.
   This step **cannot** precede 17 — `plan_update` reads `report.checked_lockfile`, which 17 adds.
2. **Barrels.** Export from `pin/__init__.py` (58) / `pin/index.ts` (46) / `index.ts` (203).
   Hand-merge against 17's and 14's entries in the same regions — see _Risks_.
3. **`deps update`, both ports.** Python: a new `@deps_app.command("update")` in `cli/deps.py`;
   TypeScript: `depsUpdate` + registration in `buildDepsCommand()` (`cli/deps.ts:345-378`) and the
   test re-export list (`:381-389`). Neither `cli/main.py` nor `cli/main.ts` changes — the deps
   group is already mounted (`main.py:18`, `main.ts:120`). Body rendering calls 17's
   `render_upgrade_report(report, output_format=plan.body_format)` / `renderUpgradeReport(...)`.
4. **Regenerate the action.** Rewrite `_ghagen_update_action()`; run `uv run ghagen synth`; confirm
   `check-synced` and `actionlint` are green. The artifact test from _Test impact_ flips green here.
5. **CI fixtures + the hermetic exercise.** Add both fixture configs; append the two steps to
   `test-action` in `_ci_workflow()`; regenerate `ci.yml`.
6. **The scheduled exercise.** Add `_check_deps_smoke_workflow()`; regenerate; run it once via
   `workflow_dispatch` before merging, because nothing local can.
7. **Docs.** `## ghagen deps update` in both `cli.md` files, inserted within `## ghagen deps upgrade`
   above 19's deleted `### Exit codes` blocks. Close `docs/issues/05`. Amend spec 0005 §3 and §5.

**Ordering vs 17:** steps 1 and 3 both touch 17's output. There is no stopgap — an earlier draft
suggested rendering through the private `cli/deps.py:277-336` helpers if 17 slipped; that is not
available, because `plan_update` needs `checked_lockfile` regardless of who renders, and a `pin/`
module importing from `cli/` would be a layering inversion. **17 is a hard prerequisite, not a
preference.** The contact surface stays small: one import of `render_upgrade_report` in the command
(not the plan), and two field reads in the plan.

## Test impact

Baseline is pytest 562 / vitest 515.

**New, offline, both ports — the actual regression guard.** `test_plan.py` / `plan.test.ts` drive
one shared decision table. Every case builds `App(root=tmp_path, …)` — never a bare `App()`, which
would resolve `root` to the checkout and let a stray `deps pin` rewrite the repo's real
`.ghagen.lock.yml` — and hand-constructs `UpgradeReport`s inline. Cases, in order:

1. **`lockfile=None` + one version bump + `checked_lockfile=True`** → `refresh_lockfile is False`,
   `apply_version_bumps is True`, `action == "create-pr"`. This is H7; it is the first case because
   it is the live bug, and it is the one case that is _only_ expressible with the `App` in hand.
2. **`lockfile=None` + `checked_lockfile=True` + empty report** → `action == "none"`,
   `total_updates == 0`.
3. **lockfile present + `checked_lockfile=False` + one bump** → `refresh_lockfile is False`.
   This is H7b, and it is exactly the assertion that would fail if a future edit re-derived the
   predicate from `mode`.
4. **lockfile present + `checked_lockfile=True` + one bump, no stale entry** → `refresh_lockfile is
True` (a bump invalidates the pinned SHA, so the cascade is correct _when there is a lockfile_).
5. **lockfile present + `checked_lockfile=True` + one stale entry, no bumps** →
   `apply_version_bumps is False`, `refresh_lockfile is True`.
6. **empty report** → `action == "none"`, `branch == ""`, `body_format is None`.
7. **`output=issue`** → `action == "create-issue"`, `branch == ""`, title carries the injected date.
8. **label parsing** — `" a , b ,, c "` → `("a", "b", "c")`; empty string → `()`. This is the
   nine-line loop (`action.yml:96-104`) turned into an assertion.
9. **commit-message prefixing** — empty prefix must not leave a leading space (the bash at
   `action.yml:139-143` gets this right; the test pins it).

**New, both ports — the wire shape.** `deps update --format json` asserted against the shared
`fixtures/expected/update_plan.json`, and `--format github` asserted to emit exactly the plan's
fields as `key=value` lines. This is the golden that a field rename would break, which the
`python3 -c` reader never had. One note for the implementer: 17 deletes `_UPGRADE_LOCKFILE`
(`test_cli/test_deps.py:139-149`) as unused — correctly, since its call sites are all in classes 17
removes — and `TestDepsUpdate`'s lockfile-present cases will want it back (`17` §Scope boundaries vs siblings anticipates
this). Reinstating a ten-line string constant is not a conflict; it is noted so nobody reads the
deletion as a decision.

**New — §3c's `|| true` fix, proven red-green.** Two guards, because the defect has two halves:

- **`packages/python/tests/test_integration/test_shipped_actions.py`** parses the repo's own
  `check-deps/action.yml` (located via `ghagen_schema.paths.REPO_ROOT`; `pyproject.toml` sets
  `pythonpath = ["scripts"]`, and `test_snapshots.py:5` / `test_cli/test_deps.py:9` are the
  precedent) and asserts that no composite `run:` block contains `|| true`, the string `python3 `,
  or `steps.detect.`. **This test is RED on `main` today** — all three strings are present, at
  `:65`, `:67-68` and `:127-130` respectively — and green only once step 4 of the migration lands.
  It is **Python-only on purpose**: the assertion is about a repo-dogfooding _artifact_ produced by
  the Python generator, not about library surface, so a TS mirror would assert on a file the TS port
  does not produce. That is a deliberate exception to the parity mandate, not an oversight; the
  parity-bearing halves of this proposal are `plan.py`/`plan.ts` and the shared golden.
- **A CLI-level exit-code test**: `deps update --mode bogus` exits **2**, prints one line on stderr,
  and emits no traceback. Measured on a replay of `action.yml:62-71`, the current shape produces
  exit **1** and a ~20-line `JSONDecodeError` traceback instead (§3c); the new shape produces exit 2
  and one line. Under **19** this becomes a row in 19's `fixtures/cli-exit-codes.yml` rather than a
  bespoke test.

**New — the CI exercise `docs/issues/05` asks for.** The issue says, verbatim:

> `check-synth` is exercised by CI's test-action job; `check-deps/action.yml` (PR/issue shell logic,
> branch naming, dedup via gh pr/issue list, label args) has zero automated coverage. Add a CI job
> exercising it in --check mode against a fixture, or at minimum a dry-run smoke.

and `docs/specs/0005-typed-engine-report-seam.md:403-404` scoped it as "The `test-action` CI job may
optionally gain a smoke invocation of `uses: ./check-deps` (dry-run `--check`), matching
`./check-synth`."

It is delivered as **two** exercises, split on whether they touch the network — because
**this repo has no precedent for a networked per-PR job, and none may be created here.** There are
only two `secrets.GITHUB_TOKEN` uses under `.github/workflows/`: `ci.yml:71-72`,
which is dead (23 deletes it) and attached to `uv run ghagen deps check-synced` — a command
`docs/src/content/docs/python/cli.md:155` states outright "does not make network calls, so it
doesn't need a GitHub token" — and `schema-drift.yml:67`, which is `gh`-CLI auth on a
`schedule`/`workflow_dispatch` workflow (`schema-drift.yml:4-7`). **Every per-PR job in this repo is
hermetic today**, including the `test-action` job (`ci.yml:159-169`), which declares no
`permissions:` and passes no token. This proposal does not break that.

**(a) Per-PR, hermetic — two steps appended to the existing `test-action` job**
(`ci.yml:159-169`, generator `ghagen_workflows.py:161-173`). Using the existing job rather than a
new one keeps the ci.yml diff to a two-step append inside one `steps:` list, which is what makes the
`18 — 23` edge as small as _Risks_ claims:

```yaml
- name: Test check-deps action (offline)
  id: check-deps
  uses: ./check-deps
  with:
    source: .
    dry-run: "true"
    config: fixtures/actions/all_pinned/ghagen_workflows.py
- name: Assert plan
  run: |-
    set -euo pipefail
    [ "${{ steps.check-deps.outputs.action }}" = "none" ]
    [ "${{ steps.check-deps.outputs.total_updates }}" = "0" ]
```

**Zero HTTP requests here is structural, not observed.** `collect_uses_refs` keeps only pinnable
refs (`pin/collect.py:36`, `if site.ref.is_pinnable:`), and `is_pinnable` is `not ref_is_sha`
(`pin/uses.py:61-63`, against the 40-char `_SHA_RE` at `:14`). An all-SHA fixture therefore yields
`refs == []`, and `upgrade()` returns at `pin/engine.py:210-211` — before either stage, before any
`list_tags` or `resolve_ref`. Constructing the `GitHubClient` (`cli/deps.py:38-53`) performs no I/O.
The only observable side effect of running tokenless is the one-line no-token warning on stderr
(`cli/deps.py:48-52`), which is expected output, not a failure.

**(b) Scheduled, networked — `.github/workflows/check-deps-smoke.yml`**, generated by a new
`_check_deps_smoke_workflow()` beside `_schema_drift_workflow()` (`ghagen_workflows.py:178-258`),
on `schedule` + `workflow_dispatch`, modelled on the one workflow in this repo that is already
allowed to call GitHub with a token. Two cases, both `dry-run: 'true'`, both against
`fixtures/actions/lockfile_none/`:

1. **`mode: versions`** → assert `refresh_lockfile == 'false'` and `action == 'create-pr'`.
   This is H7 and H7b observed on the real shipped artifact.
2. **`output: issue`** → assert `action == 'create-issue'` and `branch == ''`.

The `action == 'create-pr'` assertion in case 1 is time-dependent only if the fixture's ref can stop
being outdated. **The fixture pins `actions/checkout@v1`**, so a newer tag exists for as long as the
repository does. Residual upstream dependency, stated rather than hidden: if `actions/checkout` were
deleted or its tags rewritten, this workflow goes red — on a schedule, not on anyone's PR, which is
the correct blast radius for an assertion about someone else's repository.

**What neither exercise proves, stated so nobody over-reads it.** Both run with `dry-run: 'true'`,
so `git push` and `gh pr create` remain untested — after this change they are ~15 lines of pure I/O
rather than 112 lines of I/O and decisions. And both are **invisible to every local gate**:
`scripts/test.sh` runs pytest and vitest only, so the entire CI half of this proposal can only be
validated by pushing. That is the practical reason the effort is L, and the reason the artifact test
above exists — it is the one piece of the CI story that `scripts/test.sh py` _can_ run.

**Existing `deps upgrade` tests do change — under 17, not under this proposal.** 17 relocates
`TestUpgradeJsonContract` (`test_cli/test_deps.py:727`) and `TestUpgradeMarkdownContract` (`:873`)
to `test_pin/test_render.py` and **inverts** `test_empty_report_emits_both_keys_regardless_of_mode`
(`:821-862`) plus
`deps.test.ts:248-260`. This proposal neither causes nor blocks any of that: it _appends_ a
`TestDepsUpdate` class after `:911`, and 17's last deletion also ends at `:911`, so the append lands
after — not inside — a deleted region (`17` §Scope boundaries vs siblings). 18 reshapes nothing about `deps upgrade` itself.

## Risks & alternatives

**Scope boundaries vs siblings.**

- [**17**](./17-upgrade-report-renderer-module.md) creates the surface `deps update` consumes and
  the two report fields `plan_update` reads. **`17 → 18` is a hard order edge; 17 goes first.** This
  proposal does not reshape `UpgradeReport`, does not move the renderers, and does not touch
  `cli/deps.py:277-336` beyond leaving them where 17 finds them. **The `lockfile=None` fix lands in
  `pin/plan`, a sibling of `pin/render`, not inside 17's renderer** — a renderer that decides
  whether to refresh a lockfile would be the same category error this proposal exists to remove.
  Nothing in these amendments moves where H7 is fixed; if a later amendment tried to, it would be
  putting an `App`-scoped decision into a function that has only a report.
  Shared files, all ordering rather than exclusion: `test_cli/test_deps.py` (17 cuts 911 → ~330, 18
  appends after `:911`), `deps.test.ts` (261 → ~130), the three barrels, both `cli.md` pages, and
  `docs/specs/0005-typed-engine-report-seam.md` — where the two claims are **disjoint sections**
  (17 amends §2.2 `:115-121` and §2.3 `:141-144`; 18 amends §3 `:186-370` and §5 `:403-404`), so
  17-first leaves 18 with a line-shift, not a conflict.
- **19** (`main()` owns exit codes end to end). **`19 → 18` is ALIVE on both `cli.md` pages, in a
  four-way with 14 and 17 — 19 goes FIRST.** 19 deletes `python/cli.md:114-120,136-142,179-185` and
  `typescript/cli.md:127-133,149-155,192-198` and anchors one consolidated `## Exit codes` section
  at end-of-file. **18's insertions land inside `## ghagen deps upgrade`, above `python/cli.md:179`
  and `typescript/cli.md:192`** — i.e. above every deleted range — so they are safe post-19, and
  `deps update`'s codes become rows in 19's table rather than a new `### Exit codes` block.
  `deps update` must also obey 19's mechanism rather than raising `typer.Exit` / `CliError`
  directly.
- **23** (dev-script hygiene) shares `.github/workflows/ci.yml` and `.github/ghagen_workflows.py`.
  **The `18 — 23` edge is _regenerate-after-merge_, not serializing:** whichever lands second re-runs
  `uv run ghagen synth` and re-verifies `check-synced`. There is no overlapping hunk. 23's ci.yml
  territory is the lint jobs (`:14-77`), and it collapses `lint-meta`, after which "every line below
  `:49` shifts"; 18's ci.yml change is a two-step append inside `test-action` (`:159-169`), which
  moves wholesale and does not conflict. Three citations in this document are **pre-23 by
  construction** and will need re-deriving if 23 lands first: `ci.yml:71-72` (the dead token, which
  23 deletes — the argument that no per-PR job is networked only gets _stronger_),
  `ci.yml:159-169` and `ghagen_workflows.py:161-173` (both shift, neither changes content).
  **`.github/ghagen_workflows.py:86-90` — the ADR-0003 staleness-guard comment — is not inside any
  hunk this proposal touches and must survive 23's `lint-meta` collapse.**
- **16** (Transport seam) — **new conflict edge, and it is CLOSED.** 16's scope note asserts that
  "18 also appends to `packages/python/tests/test_pin/test_engine.py`", where 16 rewrites the entire
  fixture layer (14 and 17 also touch that file). **18 does not touch `test_engine.py` at all** —
  `grep -n test_engine` over this document returns nothing but this line, and `test_plan.py`
  constructs its own `App(root=tmp_path)` and its own `UpgradeReport`s, importing no fixture from
  it. 16 should drop 18 from that claimant list.
- **Barrel line-shift is the real conflict, not name collision.** In `pin/__init__.py` the
  `ghagen.pin.github` import block at `:15-21` is 16's alone; 18 adds **two** names from a new
  `ghagen.pin.plan` at `:29`, 17 adds three at `:29`, 14 adds `BumpSeverity` at `:32`. Nothing
  collides by name — what collides is **line placement inside the isort region `:3-31` and the
  shared alphabetical `__all__` at `:33-58`**. Hand-merge, do not rebase blindly.
  `packages/typescript/src/index.ts` has **seven** claimants and `pin/index.ts` has **five**; same
  treatment.
- **20** (delete caller-less pin/spec surface) — once the action stops calling
  `deps upgrade --format pr-body|issue-body`, those two format values are exercised only by tests.
  This proposal **keeps** them (documented user-facing surface, and 17 owns their new home).
  Flagged for 20 to judge, not pre-empted.
- **14** (`versions` owns its comparison) touches `pin/engine.py`'s versions stage. `pin/plan`
  consumes `UpgradeReport` and never touches severity computation, so the only contact is the barrel
  line-shift above.

**Both shipped actions install the Python port.** `check-deps/action.yml:54,:56` and
`check-synth/action.yml:34,:36` each `pip install` ghagen. Any claim in this document about "what
the shipped action exercises" means the Python port in both cases; the `source: .` input added here
mirrors `check-synth`'s exactly, and neither action has, or gains, a path to the TypeScript port.

**Risk: `deps update` overlaps `deps upgrade` + `deps pin`.** Accepted, and it is not duplication.
`deps upgrade` / `deps pin` are the interactive verbs a human runs; `deps update` is the automation
verb that does the whole job atomically in one sweep. The deletion test above shows the alternative
is the caller re-growing the four-invocation sequence. The one real cost is a third `deps` command
to document — paid down by deleting 90 lines of undocumented bash.

**Risk: applying before the dedupe check.** Today the action dedupes (`:107`) _before_ rendering and
applying, to avoid a wasted sweep. Under the new shape the plan step runs first and the dedupe moves
into the raise step, so a run that ends up skipping has still applied edits to the runner's working
tree. That is free: the edits are local, uncommitted, and discarded with the ephemeral runner, and
the trade buys the drop from four networked sweeps to one.

**Risk: `--format github` couples the CLI to GitHub Actions.** Mild. It is one output format on one
command whose entire purpose is to be driven by a composite action, sitting beside `pr-body` and
`issue-body`, which are already GitHub-shaped. If the coupling ever bites, `--format json` is the
neutral escape hatch and is the golden-tested one.

**Risk: the new CI fixtures live outside every static gate.** `fixtures/actions/*/ghagen_workflows.py`
are real Python files that neither ruff nor pyright will see — `pyproject.toml` sets ruff
`src = ["packages/python/src"]` and pyright `include = ["packages/python/src"]`, and `scripts/lint.sh`
runs ruff over `packages/python/src/ packages/python/tests/` only. A syntax error in a fixture
surfaces as a red CI job, not a red lint. Accepted: they are two ~25-line files whose entire job is
to be executed by the exercises that consume them, and the alternative (widening ruff's scope to
`fixtures/`) is a change to every author's lint surface for no other benefit.

**Alternative rejected: adopt 17's `checked_lockfile = "the stage actually ran"` (`17` §Risks & alternatives).** 17
names this and routes the decision here, so it is decided here rather than rediscovered. Defining
`checked_lockfile` as `mode in ("lockfile","all") and app.lockfile_path is not None` would let
`plan_update` take only a report and drop the `app` parameter. **Rejected.** It destroys
information: after the merge, a JSON consumer can no longer tell "not asked for" from "no lockfile
configured", where today `checked_lockfile=True` + `lockfile_stale: []` is at least unambiguous
about the first. It also makes `--mode lockfile` with `lockfile=None` emit `{}` — a document with no
keys at all — which is a second user-visible break stacked on 17's, and it inverts
`test_cli/test_deps.py:304-337`, the repo's only test of that path, which 17 explicitly retains
(`17` §Test impact). And it buys little: `plan_update` legitimately wants the `App`, because `refresh_lockfile`
is a fact about _this App_, not about the sweep. **Consequence for 17:** `17` §Test impact's note that 18's
H7 fix "will invert" `test_lockfile_mode_no_lockfile_configured` is now incorrect — 18 changes no
`deps upgrade` behaviour, so that assertion stands unchanged after 18 lands.

**Alternative rejected: fix the guard in place.** Adding a `lockfile_enabled` field to the
`--format json` output and a third clause to the bash would close H7 and H7b for ~4 lines. Rejected:
it deepens encoding #4 rather than deleting it, leaves the four sweeps, leaves the exit-code
laundering, leaves the two drifted dedupes, and leaves 112 lines of bash that no test can reach. It
also does not answer the question the deletion test asks — after such a fix, deleting the bash still
makes complexity vanish, which is the definition of a module that is not earning its keep.

**Alternative rejected: keep the `python3 -c` readers but validate them.** Adding `set -o pipefail`
discipline and a schema check to the one-liners makes encoding #4 _more_ elaborate while leaving it
the only untypechecked, untested copy of the shape. The problem is not that the parser is fragile;
it is that a parser exists at all.

**Alternative rejected: a generator-level `_raise_step()` shared with schema-drift.** Argued at
length in _Proposed interface_ §4 — six parameters, two callers, a shallow interface. Recorded with
the criterion under which it becomes right.

**Open — Phase 3 decision:** whether `FIXTURES_DIR`'s Python/TypeScript asymmetry is fixed this
round or deferred to `docs/issues/08-fixtures-dir-name-collision.md`. **Default: defer**, per the
review's recommendation — nothing fails today, and a pre-implementation hotfix would force four
authors (12, 14, 15, 19) to re-verify citations mid-round. One new datum for whoever writes that
issue: this proposal adds `fixtures/actions/`, so `fixtures/` stops containing only `expected/`.
The "no wrong-but-real file can be read" argument survives — a golden lookup is `fixtures/<name>`
against a file, and `actions` is a directory — but the premise it rests on is no longer "there is
nothing else in `fixtures/`".

## ADR / CONTEXT.md impact

Intended edits, noted here rather than made:

- **No ADR contradicted.** ADR-0006 (pin collects parsed refs) and ADR-0005 (synthesis pipeline /
  pin runs last) are untouched — `pin/plan` sits downstream of the engine and never walks Documents.
  ADR-0002 (no construction-time config globals) is reinforced: `plan_update` takes `today` as a
  parameter rather than reading the clock, and takes the `App` rather than re-discovering config.
  ADR-0007 (typed results at the seam, CLI owns exit codes) is extended in spirit, not amended.
  ADR-0001 and ADR-0003 are not in scope — and specifically, the ADR-0003 staleness-guard comment at
  `.github/ghagen_workflows.py:86-90` is outside every hunk here.
- **`docs/specs/0005-typed-engine-report-seam.md` — amended, not rewritten**, the same treatment
  17 gives §2.2 (`17` §Risks & alternatives). Three edits:
  - **§3, `:186-370`** (_Design — Part B: dogfood `check-deps`_) specifies `_ghagen_update_action()`
    as three `run:` blocks with a `detect` step and `steps.detect.outputs.*` guards (`:340-347`).
    That shape is replaced by the two-block form in _Proposed interface_ §3. The spec's _intent_ —
    the action is generated, not hand-maintained — is unchanged and is the reason this proposal
    edits the generator rather than the YAML.
  - **`:348-349` is superseded.** It reads: "The action exposes no action-level `outputs:`; it only
    uses per-step `$GITHUB_OUTPUT` + `steps.detect.outputs.*`, so no `ActionOutput` is needed."
    After this proposal the action exposes six composite outputs and does need `ActionOutput`. This
    is a deliberate reversal of a recorded decision, made because the CI exercise `docs/issues/05`
    asks for is unimplementable without a caller-readable output.
  - **§5, `:403-404`** — "The `test-action` CI job **may optionally** gain a smoke invocation of
    `uses: ./check-deps` (dry-run `--check`), matching `./check-synth`" — becomes mandatory and
    splits in two: a hermetic step inside `test-action`, and a scheduled workflow for the networked
    cases.
- **Possible new ADR — "the CLI answers, the action asks".** Worth one short ADR recording the rule
  that shipped composite actions must not reconstruct decisions from ghagen's serialized output;
  they invoke a command that returns a decision. That rule is what makes H7 unrepeatable in a future
  action, and it is the reusable half of this proposal. Author it during implementation if the
  reviewer agrees; otherwise the rule lives in the CONTEXT.md glossary entry below.
- **CONTEXT.md (both), "Pinning" glossary — one new term only.** 18 is not in the round's region
  assignment, so it claims the minimum: **UpdatePlan** — what a caller should _do_ about an
  UpgradeReport: raise a PR, raise an issue, or nothing; whether to apply version bumps; whether to
  refresh the Lockfile; the branch, title, commit message and labels. Derived from an UpgradeReport
  plus the App's Lockfile configuration. _Avoid_: "decision object", "action config".
  **The UpgradeReport entry is 17's**, which already proposes it; 18 does not duplicate it.
- **CONTEXT.md (both), "Relationships"** — one line: an **UpdatePlan** is derived from an
  **UpgradeReport** and the **App**; the shipped `check-deps` action consumes the plan and performs
  only git/`gh` I/O.
- **CONTEXT.md (Python), "Surface notes"** — one **appended** bullet: `deps update` is the
  automation entry point, performing detect → plan → render → apply in one process, and the shipped
  actions install this port. **The existing note at `packages/python/CONTEXT.md:104` is not
  edited** — 19 claims `py:102-104`; appending a new bullet (the same treatment 10 and 16 use)
  avoids the collision entirely.
- **`docs/issues/05-check-deps-action-untested.md`** — closed by the two exercises in _Test impact_;
  the closure note carries the `mode: versions` breaking change so a reader of the issue finds it.
- **AGENTS.md** — no change needed; "Custom ghagen github action … Generate PRs or issues
  (configurable)" already describes the behaviour, which this proposal preserves exactly.
