# 23 — Dev-script hygiene

**Status:** proposed | **Ports:** dev tooling | **Effort:** M | **Depends on:** none. Merge-order
note only — [18](./18-check-deps-decision-logic.md) and 23 both regenerate
`.github/workflows/ci.yml` from `.github/ghagen_workflows.py`, so whichever lands second re-runs
`uv run ghagen synth`; that is **not** a serialization constraint. The `19 — 23` edge is **dropped**.

Effort stays **M** (not L): sixteen files, but the only Python is a ~20-line rewrite of one `run()`
function, `.github/workflows/ci.yml` is regenerated rather than edited, four rows are two-line or
delete-only, and nothing under `packages/*/src` or either test suite is touched.

## Files involved

### Modified

| Path                                         | Lines | Role in this proposal                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| -------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/lint.sh`                            | 39    | Preamble (`:1-13`) replaced by a `_gate.sh` source; the `all`-only block (`:33-39`) becomes an explicit `meta` scope; the docs step (`:24-25`) moves to a `docs` scope; the `$PATH` `actionlint` call (`:34-35`) is **deleted**; the apology comment (`:28-32`) is deleted.                                                                                                                                                                                                                                                                      |
| `scripts/fmt.sh`                             | 45    | The divergent preamble (`:6-17`) replaced by the same source; docs steps (`:29-30`, `:42-43`) move to the `docs` scope.                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `scripts/typecheck.sh`                       | 23    | Preamble (`:1-13`) replaced by the source. No command changes.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `scripts/test.sh`                            | 23    | Preamble (`:1-13`) replaced by the source. No command changes.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `scripts/docs-dev.sh`                        | 10    | Gains `need_node docs` before `npm run build --prefix docs` (`:6-7`); same failure it shares with the gates. Not a scoped gate — it sources `_gate.sh` and never calls `gate_parse`.                                                                                                                                                                                                                                                                                                                                                             |
| `scripts/ghagen_schema/check.py`             | 40    | **Added by review.** `run()` (`:20-40`) currently regenerates `packages/typescript/src/schema/` **in place** and leaves it there; it becomes snapshot → regenerate → diff → restore, so `check` is read-only. Prerequisite for item 4 — see item 6.                                                                                                                                                                                                                                                                                              |
| `.pre-commit-config.yaml`                    | 28    | `rev: v1.7.11` (`:26`) → `v1.7.12`, matching the generator's pin. Hook entries (`:14`, `:20`) unchanged.                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `renovate.json`                              | 4     | Add `:enablePreCommit` so the two actionlint pins cannot re-drift.                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `.github/ghagen_workflows.py`                | 845   | **Source of truth.** `_ci_workflow()` (`:28-175`) lint jobs only: `lint-ts` (`:50-62`) loses its docs `npm ci` (`:58`); a new `lint-docs` job is inserted after it; `lint-meta` (`:67-97`) loses the apology comment (`:63-66`), the dead `GITHUB_TOKEN` (`:84`), and its two open-coded meta commands (`:81-85`, `:91-95`) in favour of `scripts/lint.sh meta`. The ADR-0003 comment (`:86-90`) is preserved. `_ghagen_update_action()` and every non-lint job untouched **in content** — but see the line-shift note under _Scope boundaries_. |
| `.github/workflows/ci.yml`                   | 169   | **Generated** — never hand-edited. Regenerated by `uv run ghagen synth`. Changed region is the lint jobs (`:14-77`); every line below `:49` shifts.                                                                                                                                                                                                                                                                                                                                                                                              |
| `AGENTS.md`                                  | 78    | "Common Commands" (`:47-55`) gains the scope vocabulary; a Setup subsection documents the three installs (`uv sync`, `npm ci --prefix packages/typescript`, `npm ci --prefix docs`) **and `pre-commit install`** — see the conditionality note below.                                                                                                                                                                                                                                                                                            |
| `docs/architecture-deepening-plan.md`        | 239   | `:65-66` still enumerates the superseded three-value `[py\|ts\|all]` vocabulary that this proposal replaces, while this proposal cites `:56-73` as its authority. Edited **line-neutrally** (two lines → two lines) so `07:51-52`, `10` §Problem and `18` §3c.                                                                                                                                                                                                                                                                                   |     | true does not suppress the failure it appears to suppress do not shift. Form of the edit is an open decision — see _ADR / CONTEXT.md impact_. |
| `docs/issues/06-actionlint-version-drift.md` | 7     | **Deleted** — closed by item 3.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `docs/issues/07-docs-package-tooling-gap.md` | 7     | **Deleted** — closed by item 2.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |

### New

| Path                                            | Lines     | Role in this proposal                                                                                                                                                                                                                                                                                                                        |
| ----------------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/_gate.sh`                              | new (~60) | The gate interface, stated once: usage/error mode, `--fix` admissibility, `REPO_ROOT`, `step`, `in_scope`, `need_node`. The scope _enumeration_ is declared per gate (`GATE_SCOPES`) and read here. Sourced, not executed; the leading underscore matches the repo's private-module convention (`_base.ts`, `_raw.py`, `_package_paths.py`). |
| `docs/issues/08-fixtures-dir-name-collision.md` | new (~14) | **Conditional.** Written only if the Phase 3 decision below defers the `FIXTURES_DIR` asymmetry. Carries the remedy and five-file list from the last section verbatim, plus the stale `docs/specs/0005-typed-engine-report-seam.md:127` reference.                                                                                           |

**Not touched, deliberately:** `docs/proposals/INDEX.md`, any ADR, any `CONTEXT.md`, any file under
`packages/`. The `FIXTURES_DIR` divergence is verified but argued **out** of this proposal; its five
files are listed separately in the last section so the orchestrator can schedule it without reading
them as this proposal's conflict set.

## Problem

`docs/architecture-deepening-plan.md:56-73` already decided the seam: _"scripts are the single seam
for 'what constitutes each gate', with a scope argument"_, so that _"command-set knowledge lives
once; scripts/CI can no longer disagree."_ That landed for the **commands**. It did not land for the
**interface**. The scope argument — which values exist, what the usage string says, what happens on a
bad one, and which toolchains a scope needs installed — is restated in four implementations, and
`.github/ghagen_workflows.py` re-lists two commands the scripts were supposed to own.

**Conditionality note, and it modulates items 2, 3 and 6.** `pre-commit` is **not installed in this
checkout**: `.git/hooks/` contains only `*.sample` files, `pre-commit` is not on `$PATH`, and neither
`AGENTS.md` nor `README.md` mentions it (the only repo-wide hits are `.pre-commit-config.yaml`
itself, two historical `CHANGELOG.md` entries, and `docs/architecture-deepening-plan.md:58`). Every
"on every commit" claim in this proposal — and in the round — is therefore conditional on a
`pre-commit install` that nothing documents. That is itself a finding, and this proposal fixes it in
the `AGENTS.md` Setup subsection it is already adding. Where the text below says "every commit", read
"every commit **in a checkout where the hooks are installed**"; the hooks are the intended local
gate, so the fix is to make installing them documented, not to weaken the claim.

### 1. The scope preamble: three byte-identical copies and one silent variant — **LIVE**

Three byte-identical copies, verified by `md5` over lines 1-13 of each:

```
982ec0daba55e9fa959fac71bbd193c8  scripts/lint.sh
982ec0daba55e9fa959fac71bbd193c8  scripts/typecheck.sh
982ec0daba55e9fa959fac71bbd193c8  scripts/test.sh
```

```bash
# scripts/lint.sh:1-13 == scripts/typecheck.sh:1-13 == scripts/test.sh:1-13
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

SCOPE="${1:-all}"
case "$SCOPE" in
  py | ts | all) ;;
  *)
    echo "Usage: $0 [py|ts|all]" >&2
    exit 1
    ;;
esac
```

The fourth, `scripts/fmt.sh:6-17`, is **not** a copy (`md5` `c6e58ecf4fcde217203942cfce7af27e` over
`:1-17`). It is the same interface re-implemented differently, and it has already drifted in three
observable ways:

```bash
# scripts/fmt.sh:6-17
FIX=0
SCOPE="all"
for arg in "$@"; do
  case "$arg" in
    --fix) FIX=1 ;;
    py | ts | all) SCOPE="$arg" ;;
    *)
      echo "Usage: $0 [py|ts|all] [--fix]" >&2
      exit 1
      ;;
  esac
done
```

- **Position-free vs positional.** `fmt.sh --fix py` and `fmt.sh py --fix` both work; the other three
  read `$1` only, so `lint.sh --fix py` fails on `--fix` and `lint.sh py extra` silently ignores
  `extra` and exits 0.
- **Last-wins vs first-only.** `fmt.sh py ts` silently runs the `ts` scope. `lint.sh py ts` runs `py`.
- **Divergent usage strings.** Two different `Usage:` lines for what is meant to be one interface.

All four behaviours were reproduced end-to-end against stubbed toolchains during review.

That drift is the argument. This is a **shallow interface with four implementations**: the
implementation of "parse a scope" is nearly as large as the interface it exposes, and having four of
them bought nothing except the freedom to disagree. Adding a scope value today is four edits, and the
`fmt.sh` variant proves that four edits do not stay in step.

### 2. The docs toolchain trap fires on the default scope, not the `py` scope — **LIVE**

This is the round's most-repeated wrong fact, so it is stated here in the corrected form. The claim
that `scripts/lint.sh` and `scripts/fmt.sh` run the `docs/` npm toolchain _unconditionally_, or _"even
under a `py` scope"_, is **false**. The docs steps are guarded on `ts`/`all`:

```bash
# scripts/lint.sh:20-26
if [[ "$SCOPE" == "ts" || "$SCOPE" == "all" ]]; then
  echo "==> oxlint (typescript)"
  npm run lint --prefix "$REPO_ROOT/packages/typescript"

  echo "==> oxlint (docs)"
  npm run lint --prefix "$REPO_ROOT/docs"      # ← docs, under the *ts* scope
fi
```

Same shape at `scripts/fmt.sh:25-31` (fix) and `:38-44` (check). `scripts/lint.sh py` (`:15-18`) runs
`uv run ruff check` and nothing else. **The `py` scope is clean today**, and CI's `lint-py` job
(`ci.yml:14-28`) correctly installs no Node at all.

The real trap is one step over, and it is worse than the refuted version because it fires on the
**documented default**:

- `scripts/lint.sh:6` — `SCOPE="${1:-all}"`. No argument means `all`, and `all` includes the docs
  branch. Identical at `typecheck.sh:6`, `test.sh:6`, and `fmt.sh:7`.
- `.pre-commit-config.yaml:14` and `:20` — `entry: scripts/lint.sh` / `entry: scripts/fmt.sh`, with
  `pass_filenames: false` and `always_run: true` (`:16-17`, `:22-23`). **No argument.** Every commit
  runs the docs scope.
- `AGENTS.md:50-51` — documents the bare `scripts/lint.sh` / `scripts/fmt.sh`. Every agent and every
  contributor following AGENTS.md runs the docs scope.
- `docs/package.json:9,12` — `"lint": "oxlint src astro.config.mjs"`, `"fmt:check": "oxfmt --check ."`.
  Both binaries come from `docs/devDependencies` only (`docs/package.json:22-23`, `oxfmt ^0.45.0` /
  `oxlint ^1.60.0`), i.e. `docs/node_modules/.bin`. There is no root `package.json`, and the root
  `node_modules/` holds only a `.vite` cache with no `.bin/` at all, so npm's ancestor-`.bin` walk
  finds no fallback. `which oxlint` → not found.

So in a checkout that has run `uv sync` and `npm ci --prefix packages/typescript` but not
`npm ci --prefix docs`, the _default_ gate and _every commit_ die on `oxlint: command not found`
(exit 127, then `set -e`). This checkout has `docs/node_modules/` present, so the failure is proved by
construction rather than executed here; every structural precondition above is verified.
`docs/issues/07:5-7` reports exactly this:

> `scripts/lint.sh ts` / `scripts/fmt.sh` run oxlint/oxfmt in `docs/` where the binaries are absent
> unless `npm ci --prefix docs` ran; every local/agent environment hits "command not found". Either
> guard the docs step on binary presence, or document `npm ci --prefix docs` as a setup step.

The structural fault underneath: **`ts` names two toolchains.** `packages/typescript/` and `docs/` are
separate npm roots with separate `package.json`s, separate `node_modules`, and separate install
commands — but one scope value covers both, so you cannot ask for one without the other. CI has
already paid for this: `lint-ts` (`ci.yml:29-49`) must run `npm ci` twice (`:39-41` and `:42-44`)
because a single `scripts/lint.sh ts` needs both trees.

### 3. actionlint: three pins, and the only unconditional local run is the unpinned one — **LIVE**

Three pins, all confirmed:

| Where                       | Pin          | Cite                                                                                                                                 |
| --------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| pre-commit's dedicated hook | `v1.7.11`    | `.pre-commit-config.yaml:25-28` (`rev: v1.7.11` at `:26`)                                                                            |
| CI's `lint-meta` step       | `v1.7.12`    | `.github/ghagen_workflows.py:79` → `.ghagen.lock.yml:28-30` → `.github/workflows/ci.yml:68` (`rhysd/actionlint@914e7df…  # v1.7.12`) |
| `scripts/lint.sh:34-35`     | **unpinned** | bare `actionlint` off `$PATH` — whatever the developer happens to have installed                                                     |

`docs/issues/06`'s title (`:1`) is "actionlint pinned at three versions in two places"; its body
(`:5-7`) names only the first two. The third is the `$PATH` invocation, which has no pin at all — on
this machine `/opt/homebrew/bin/actionlint` reports `1.7.11`, which is coincidence, not configuration.

**The invocation count, corrected.** The rhysd hook is _not_ unconditional. Its upstream
`.pre-commit-hooks.yaml` — read from the local pre-commit cache at
`~/.cache/pre-commit/repobgqh1dqf/.pre-commit-hooks.yaml` — declares `types: ["yaml"]` and
`files: ^\.github/workflows/`, and `.pre-commit-config.yaml:27-28` overrides neither. So:

| Commit touches   | actionlint runs today                                                           | after this proposal    |
| ---------------- | ------------------------------------------------------------------------------- | ---------------------- |
| no workflow YAML | **once** — `lint.sh all` → the unpinned `$PATH` binary                          | **zero**               |
| a workflow YAML  | **twice** — the `$PATH` binary _and_ the hook, at two versions free to disagree | **once**, at `v1.7.12` |

That bottom-left cell is the defect: the same files linted twice, at two versions. The top-right cell
is a real **coverage reduction** and is stated rather than sold as a strict improvement. It is
defensible on its own terms: a commit that changes nothing under `.github/workflows/` cannot change
actionlint's verdict on those files, and the one way a workflow changes without a workflow YAML being
staged — editing `.github/ghagen_workflows.py` and forgetting to regenerate — is caught by
`uv run ghagen check-synced`, which this proposal moves into the `meta` scope and therefore into the
same default `all` run. CI is unaffected: one run per CI run, before and after
(`ci.yml:67-68`; `lint-py` and `lint-ts` call `scripts/lint.sh py` / `ts` at `ci.yml:25`, `:46` and
never reach the `all`-only block).

**Why the pins drifted, mechanically:** `renovate.json:3` is bare `"extends": ["config:recommended"]`.
Renovate's `pre-commit` manager ships `"enabled": false` and is opt-in — the documented switches are
the `:enablePreCommit` preset or `{"pre-commit": {"enabled": true}}`, and `config:recommended`
includes neither. So Renovate has been bumping the workflow pin (which is why it reached `v1.7.12`)
and has never looked at `.pre-commit-config.yaml`. Bumping the rev by hand fixes today and re-drifts
next release.

### 4. The `all`-only block is an apology for a missing scope — **LIVE**

`scripts/lint.sh:33-39` is gated on `all` alone and carries a five-line comment explaining why:

```bash
# scripts/lint.sh:28-32
# actionlint and `ghagen deps check-synced` are language-neutral (they don't belong to
# either the Python or TypeScript surface), so they only run under the default `all`
# scope -- a `py` or `ts` scoped call is meant to gate just that language's checks.
# CI's per-language lint jobs therefore call this script with `py`/`ts` and never see
# these two; a separate CI job runs them directly instead (see `.github/ghagen_workflows.py`).
```

The same paragraph is duplicated, near-verbatim, at `.github/ghagen_workflows.py:63-66`. Two copies of
a comment explaining a workaround is the signal: the scope enumeration is missing a value the design
needs. The consequence is that `lint-meta` **re-lists commands the scripts were supposed to own** —
`ghagen_workflows.py:81-85` and `:91-95` open-code `uv run ghagen deps check-synced` and
`uv run python -m ghagen_schema check`, which is precisely the "CI job bodies re-list commands instead
of calling `scripts/*.sh`" failure `docs/architecture-deepening-plan.md:59-60` was written to end. The
schema check is CI-only as a result: no local gate runs it.

### 5. Dead `GITHUB_TOKEN` on the check-synced step — **LIVE**

```yaml
# .github/workflows/ci.yml:69-72  (from .github/ghagen_workflows.py:81-85)
- name: ghagen deps check-synced
  run: uv run ghagen deps check-synced
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

`deps check-synced` calls `check_sync`, whose contract is explicit:

```python
# packages/python/src/ghagen/pin/engine.py:138-155
def check_sync(app: App, *, prune: bool) -> SyncReport:
    """Compare the lockfile against the app's refs — pure, no network.
```

Its body (`:144-155`) is `collect_uses_refs` + `read_lockfile` + two set differences. No transport, no
resolver, no token read. The env entry hands a credential to a step that cannot use it. Harmless
today, but it is also load-bearing misinformation: `18` §What sits behind the seam cites this exact step as
precedent that _"`lint-meta` already makes authenticated API calls in CI."_ It does not.

### 6. `ghagen_schema check` writes the files it is checking — **LIVE**, and it blocks item 4

Found in review, and it is the reason item 4's fix cannot be applied naively. `check` is not a check:

```python
# scripts/ghagen_schema/check.py:20-30
def run() -> int:
    """Execute the ``check`` verb: regenerate, then assert git-clean."""
    rc = generate.run()
    ...
    diff = subprocess.run(
        ["git", "diff", "--exit-code", "--", str(rel)],
        cwd=REPO_ROOT,
    )
```

`generate.run()` (`scripts/ghagen_schema/generate.py:19-26`) shells
`npm --prefix packages/typescript run generate-types`, and that script writes into
`packages/typescript/src/schema/` (`packages/typescript/scripts/generate-types.ts:18,81,96`) and then
reformats exactly those output paths with `npx oxfmt` (`:104`). So
`PYTHONPATH=scripts uv run python -m ghagen_schema check` **regenerates tracked files in place** and
leaves them there — including on the failure path, which makes `check.py:32-36`'s own instruction
("Run `uv run python -m ghagen_schema generate` and commit the result") false: it has already been run.

In CI this is invisible, because the checkout is fresh and the regenerate-then-diff _is_ the test
(`ci.yml:73-76`). Locally it is a working-tree mutation. Folding this command into `scripts/lint.sh
meta` — i.e. into `all`, into the AGENTS.md-documented bare invocation, and into the pre-commit `lint`
hook — would make an ordinary commit rewrite tracked files. Item 4's remedy is only admissible once
this is fixed; the fix is in _(d)_ below.

`GENERATED_TYPES_DIR` (`check.py:17`) is the complete write set — verified against
`generate-types.ts`, whose only `writeFileSync` target is `OUTPUT_DIR` and whose `oxfmt` call takes
`outputPaths` explicitly rather than a directory — so a snapshot/restore fix is sound.

## Current interface

Four gate scripts advertise one interface and implement it four times:

- **Values:** `py | ts | all`, positional, default `all` (`lint.sh:6-13`, `typecheck.sh:6-13`,
  `test.sh:6-13`) — except `fmt.sh:6-17`, where they are position-free and last-wins.
- **Flags:** `--fix`, accepted by `fmt.sh` only; rejected as an unknown argument by the other three,
  even though `lint:fix` exists in both npm packages (`packages/typescript/package.json:46`,
  `docs/package.json:10`) and `ruff check --fix` exists.
- **Error mode:** `echo Usage… >&2; exit 1`, with two different usage strings.
- **Prerequisites:** undeclared. A scope silently assumes its toolchains are installed; a missing one
  surfaces as `command not found` from three frames down.
- **`ts` means two toolchain roots** — `packages/typescript/` and `docs/` — with no way to select one.
- **`all` additionally means "and the language-neutral meta checks"**, an undeclared extra that exists
  only in `lint.sh` and is explained by a comment in two files.

A maintainer adding a scope value edits four scripts and hopes they agree. A contributor running the
documented default needs a toolchain nothing told them to install.

## Proposed interface

State the gate interface once, in one sourced module; let each gate declare **which scopes it has**;
and make the scope enumerate **toolchain roots** rather than loosely-grouped languages.

### (a) `scripts/_gate.sh` — the interface, and `GATE_SCOPES` is per gate

The enumeration is declared **once per gate, in that gate**, and `_gate.sh` reads it in two places —
to print it and to enforce it. It is never restated in `_gate.sh` itself. Every conditional is written
as an `if` block rather than an `&&` list, because `_gate.sh` is sourced under `set -e` and a bare
`[[ … ]] && …` that evaluates false would abort the caller.

```bash
#!/usr/bin/env bash
# The gate interface: usage, error mode, flag admissibility, prerequisites.
# Sourced by scripts/{lint,fmt,typecheck,test,docs-dev}.sh -- never executed.
#
# Each gate declares its own scope set:
#     GATE_NAME=lint GATE_SCOPES="py ts docs meta" GATE_ALLOW_FIX=1
# `all` is implicit and always means "every scope this gate declares".

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${GATE_NAME:?_gate.sh: set GATE_NAME before sourcing}"
: "${GATE_ALLOW_FIX:=0}"        # gates that support --fix set this to 1

SCOPE="all"
FIX=0

gate_usage() {                                  # reader 1 of GATE_SCOPES
  if [[ $# -gt 0 ]]; then
    echo "error: scripts/$GATE_NAME.sh: $1" >&2
  fi
  local flags=""
  if [[ "$GATE_ALLOW_FIX" -eq 1 ]]; then flags=" [--fix]"; fi
  local vals
  vals="$(echo "$GATE_SCOPES all" | tr ' ' '|')"
  echo "Usage: scripts/$GATE_NAME.sh [$vals]$flags   (default: all)" >&2
  exit 1
}

_gate_declares() {                              # reader 2 of GATE_SCOPES
  local s
  for s in $GATE_SCOPES all; do
    if [[ "$s" == "$1" ]]; then return 0; fi
  done
  return 1
}

gate_parse() {
  : "${GATE_SCOPES:?_gate.sh: set GATE_SCOPES before calling gate_parse}"
  local seen=0
  for arg in "$@"; do
    if [[ "$arg" == "--fix" ]]; then
      if [[ "$GATE_ALLOW_FIX" -ne 1 ]]; then gate_usage "--fix is not accepted by this gate"; fi
      FIX=1
      continue
    fi
    if ! _gate_declares "$arg"; then gate_usage "no '$arg' scope"; fi
    if [[ "$seen" -ne 0 ]]; then gate_usage "one scope per invocation"; fi
    SCOPE="$arg"
    seen=1
  done
}

in_scope() { [[ "$SCOPE" == "$1" || "$SCOPE" == "all" ]]; }

step() { echo "==> $1"; }

# Declared prerequisite. Turns `oxlint: command not found` into a diagnosis.
need_node() {
  if [[ -d "$REPO_ROOT/$1/node_modules" ]]; then return 0; fi
  echo "error: scripts/$GATE_NAME.sh needs the '$1' toolchain, which is not installed." >&2
  echo "       run: npm ci --prefix $1" >&2
  exit 1
}
```

The declarations, complete:

| Gate           | `GATE_SCOPES`                                                                                        | `--fix` |
| -------------- | ---------------------------------------------------------------------------------------------------- | ------- |
| `lint.sh`      | `py ts docs meta`                                                                                    | yes     |
| `fmt.sh`       | `py ts docs`                                                                                         | yes     |
| `typecheck.sh` | `py ts`                                                                                              | no      |
| `test.sh`      | `py ts`                                                                                              | no      |
| `docs-dev.sh`  | _(none — not a scoped gate; sources `_gate.sh` for `need_node`/`step` and never calls `gate_parse`)_ | no      |

Every gate becomes its command list and nothing else:

```bash
#!/usr/bin/env bash
set -euo pipefail
GATE_NAME=lint GATE_SCOPES="py ts docs meta" GATE_ALLOW_FIX=1
source "$(dirname "$0")/_gate.sh"
gate_parse "$@"

if [[ "$FIX" -eq 1 ]]; then NPM_LINT=lint:fix; else NPM_LINT=lint; fi

if in_scope py; then
  step "Ruff check"
  if [[ "$FIX" -eq 1 ]]; then
    uv run ruff check --fix packages/python/src/ packages/python/tests/
  else
    uv run ruff check packages/python/src/ packages/python/tests/
  fi
fi

if in_scope ts; then
  need_node packages/typescript
  step "oxlint (typescript)"
  npm run "$NPM_LINT" --prefix "$REPO_ROOT/packages/typescript"
fi

if in_scope docs; then
  need_node docs
  step "oxlint (docs)"
  npm run "$NPM_LINT" --prefix "$REPO_ROOT/docs"
fi

if in_scope meta; then
  step "ghagen deps check-synced"
  uv run ghagen deps check-synced
  need_node packages/typescript   # ghagen_schema/generate.py:21-25 shells `npm run generate-types`
  step "Schema types up to date"
  PYTHONPATH=scripts uv run python -m ghagen_schema check
fi
```

Note what is **absent**: no `actionlint` call, and no `# actionlint and ghagen deps check-synced are
language-neutral…` comment. Both are deleted; see (c).

**Invariants and error modes, now stated once:**

- Exactly one scope value per invocation; `lint.sh py ts` is an error, not a silent last-wins.
- `--fix` is admissible iff the gate declares `GATE_ALLOW_FIX=1`; `typecheck.sh --fix` errors with a
  usage string that does not mention `--fix`.
- **A scope a gate does not declare is a usage error, not a no-op.** `test.sh docs`, `typecheck.sh
meta` and `fmt.sh meta` exit 1 with `no 'docs' scope` / `Usage: … [py|ts|all]`. They never exit 0
  having checked nothing — that would be the same "green over an unchecked surface" failure this
  proposal rejects in _Risks_ for the docs step, and it is why `GATE_SCOPES` is per gate rather than
  one global list.
- `all` means "every scope **this gate** declares", so it stays the union and stays meaningful for
  every gate without any gate having to no-op.

`lint.sh --fix` becomes real, wiring up `ruff check --fix`, `packages/typescript/package.json:46` and
`docs/package.json:10` — three fix paths that exist today and no gate exposes.

### (b) `docs` is its own scope, and CI splits accordingly

`ts` stops naming two npm roots. `scripts/lint.sh ts` needs only `packages/typescript/node_modules`;
`scripts/lint.sh docs` needs only `docs/node_modules`. In the generator:

- `lint-ts` (`ghagen_workflows.py:50-62`) drops `Step(name="Install docs deps", …)` (`:58`), which
  removes `ci.yml:42-44`. The TypeScript lint job stops installing an Astro site to run oxlint.
- A new `lint-docs` job is inserted after it: checkout, setup-node, `npm ci` in `docs`,
  `scripts/lint.sh docs`, `scripts/fmt.sh docs`. Docs linting stays a required gate and now runs in
  parallel with `lint-ts` instead of serially inside it.

The two toolchains become uncoupled at the same time in the script and in CI — the same move at both
layers, which is the point.

### (c) One actionlint, one runner per context

Delete `scripts/lint.sh:34-35`'s `$PATH` `actionlint` call outright (`:37-38`'s `check-synced` moves to
the `meta` scope; the whole `:33-39` block and the `:28-32` comment go). Its two remaining runners
already cover every path that can change a workflow file:

- **Local:** `.pre-commit-config.yaml:25-28`, bumped `rev: v1.7.11` → `v1.7.12`, firing on any staged
  YAML under `.github/workflows/`.
- **CI:** `ci.yml:67-68` / `ghagen_workflows.py:77-80`, `rhysd/actionlint@v1.7.12`, SHA-pinned through
  `.ghagen.lock.yml:28-30`, on every PR.

Result: **one version** (was three), **one invocation on a workflow-touching commit** (was two, at two
versions), **one per CI run** (unchanged), and — stated plainly, per the table in item 3 — **zero on a
commit that touches no workflow file** (was one, unpinned). Add `:enablePreCommit` to `renovate.json`
so the two remaining pins move together and item 3 cannot recur.

### (d) `meta` is a scope, so CI stops re-listing commands — and `check` stops writing

Two changes, in this order, because the second is a precondition for the first.

**First, make `ghagen_schema check` read-only.** `scripts/ghagen_schema/check.py:20-40`'s `run()`
becomes snapshot → regenerate → diff → restore:

```python
def run() -> int:
    """Execute the ``check`` verb: regenerate, assert git-clean, restore the tree."""
    with tempfile.TemporaryDirectory() as tmp:
        backup = Path(tmp) / "schema"
        shutil.copytree(GENERATED_TYPES_DIR, backup)
        try:
            rc = generate.run()
            if rc != 0:
                return rc
            rel = GENERATED_TYPES_DIR.relative_to(REPO_ROOT)
            diff = subprocess.run(
                ["git", "diff", "--exit-code", "--", str(rel)], cwd=REPO_ROOT
            )
        finally:
            shutil.rmtree(GENERATED_TYPES_DIR)
            shutil.copytree(backup, GENERATED_TYPES_DIR)
    # ... unchanged staleness message / return
```

The tree is byte-identical afterwards on both the pass and the fail path, so the command is safe in a
local gate and in a pre-commit hook — and `check.py:32-36`'s instruction to _"run `generate` and commit
the result"_ becomes true, which it is not today. CI behaviour is unchanged: the diff still runs
against the regenerated content, before the restore. `GENERATED_TYPES_DIR` is the complete write set
(item 6), so nothing escapes the snapshot.

**Then, collapse `lint-meta`.** It keeps its `uses: rhysd/actionlint@v1.7.12` step — that one is an
_action_, not a command, and cannot live in a shell script — and replaces its two open-coded `run:`
steps (`ghagen_workflows.py:81-85`, `:91-95`) with a single
`Step(name="Meta lint", run="scripts/lint.sh meta")`. The apology comments at
`ghagen_workflows.py:63-66` and `lint.sh:28-32` are deleted along with the condition they were
apologising for. The dead `env={"GITHUB_TOKEN": …}` (`:84`) goes with them — `check_sync` is pure
(`pin/engine.py:139`) and `ghagen_schema check` documents the same
(`scripts/ghagen_schema/check.py:5-6`: _"It never fetches … and needs no `GITHUB_TOKEN`"_).

**Side effect worth naming, with its cost.** `scripts/lint.sh all` now runs the schema-staleness check
locally, where today it is CI-only (`ci.yml:73-76`) and a stale `packages/typescript/src/schema/` is
only discoverable after push. The cost is that the bare default gate — and therefore the pre-commit
`lint` hook — now shells `npm run generate-types`, which runs `json-schema-to-typescript` over both
Snapshots plus `npx oxfmt`. That is not free, and it was not measured here (running it would write
tracked files in a shared checkout). **Migration step 8 measures it.** If it is too slow for a
per-commit hook, the recorded fallback is to move the expensive scope to its own pre-commit hook under
`stages: [pre-push]` rather than to weaken the scope vocabulary — a config change the per-gate scope
design makes expressible, which the single global enumeration would not have.

## What sits behind the seam

`scripts/_gate.sh` is the single **adapter point** for "how a gate is invoked." Behind it: the parse,
the usage text, the flag-admissibility rule, the one-scope-per-invocation rule, the meaning of `all`,
the ordering guarantee that a scope's prerequisites are checked before its first command, and the
diagnosis for a missing toolchain. Five callers (`lint`, `fmt`, `typecheck`, `test`, `docs-dev`) know
only `GATE_NAME`, `GATE_SCOPES`, `GATE_ALLOW_FIX`, `in_scope`, `need_node`, `step`. Changing what a
missing toolchain prints, or how an unknown scope is rejected, is one edit. Adding a scope value to one
gate is one edit _in that gate_ — and, importantly, does not silently add a no-op to the other four.

The **leverage** is small but real (each gate loses 8-12 lines of preamble). The **locality** is the
prize: the interface is one file, so the `fmt.sh`-style drift documented in item 1 has nowhere to
happen, and `.github/ghagen_workflows.py` goes back to naming gates instead of re-listing their
contents — which is `docs/architecture-deepening-plan.md:56-73`'s stated design, finished.

**Deletion test on `_gate.sh`:** delete it and each of five scripts re-grows a usage string, a
`--fix` decision, a one-scope-per-invocation rule, and — new, and the part that actually costs — two
`node_modules` presence checks apiece. Five copies of a five-part contract, with `fmt.sh`'s history as
direct evidence that five copies do not stay in step. Earned, not a pass-through.

**Deletion test on the `meta` scope:** delete it and `ghagen_workflows.py` must re-grow two open-coded
`run:` steps _and_ the four-line comment explaining why they are open-coded, and the schema check
returns to being CI-only. Earned.

**Deletion test on `scripts/lint.sh`'s `actionlint` call:** delete it and nothing reappears anywhere.
Pre-commit still lints staged workflow YAML locally, CI still lints them on every PR. Its only distinct
contribution is a third, unpinned version — plus a run on commits where no workflow file changed, which
is the coverage this proposal gives up knowingly (item 3). Delete.

**Deletion test on a `scripts/setup.sh` (considered, rejected):** delete it and three documented
commands reappear in `AGENTS.md`. Pass-through. `need_node` printing the exact command at the moment
of failure is strictly better than a script you have to know exists.

## Migration plan

Pre-1.0; clean breaks. `.github/ghagen_workflows.py` is the source — `.github/workflows/ci.yml` is
regenerated, never hand-edited, and `uv run ghagen check-synced` must stay green (`ci.yml:146-158`).

1. Add `scripts/_gate.sh`. Convert `typecheck.sh` and `test.sh` first (`GATE_SCOPES="py ts"`) — they
   have no docs/meta work, so the conversion is pure preamble replacement and any behaviour change is
   a bug.
2. Make `scripts/ghagen_schema/check.py`'s `run()` restore the tree (item 6 / (d)). Verify by running
   it on a clean tree and confirming `git status --short` is unchanged on **both** the pass path and a
   deliberately-dirtied fail path. This step lands before the `meta` scope exists.
3. Convert `lint.sh`: `_gate.sh` source, `GATE_SCOPES="py ts docs meta"`, `docs` scope split out of
   `ts`, `meta` scope added, `$PATH` `actionlint` (`:34-35`) and the `:28-32` comment deleted,
   `need_node` guards added, `--fix` wired to the existing `lint:fix` scripts.
4. Convert `fmt.sh` (`GATE_SCOPES="py ts docs"`; its `--fix` semantics are preserved, only the parser
   moves) and `docs-dev.sh` (`need_node docs`, no `gate_parse`).
5. `.pre-commit-config.yaml:26` → `v1.7.12`; `renovate.json` adds `:enablePreCommit`.
6. Edit `_ci_workflow()`'s lint jobs: drop `:58`, insert `lint-docs`, collapse `lint-meta`'s two `run:`
   steps into `scripts/lint.sh meta`, drop the `GITHUB_TOKEN` env (`:84`) and the `:63-66` comment,
   preserve the ADR-0003 comment (`:86-90`).
7. `uv run ghagen synth`; confirm `uv run ghagen check-synced` is green and the only `ci.yml` diff is
   the lint jobs. **Re-derive every `ci.yml` and `ghagen_workflows.py` line citation in sibling
   proposals afterwards** — see _Scope boundaries_.
8. `AGENTS.md`: Setup subsection (three installs + `pre-commit install`) + scope vocabulary in Common
   Commands. Time `scripts/lint.sh meta` on a warm checkout and record it; if the schema check
   dominates, apply the `stages: [pre-push]` fallback from (d).
9. `docs/architecture-deepening-plan.md:65-66` per the Phase 3 decision (amend in place, line-neutral,
   or mark the section historical).
10. Gates: `scripts/lint.sh all`, `scripts/fmt.sh all`, `scripts/typecheck.sh all`,
    `scripts/test.sh all`, `uv run ghagen check-synced`. Baseline **pytest 562 / vitest 515** must be
    unchanged — this proposal touches no file under `packages/*/src` or either test suite.
11. Delete `docs/issues/06-actionlint-version-drift.md` and `docs/issues/07-docs-package-tooling-gap.md`.

## Test impact

No pytest or vitest case changes; the suite baseline (562 / 515) is a control, not a target. The test
surface improves in three places that are not the unit suites:

- **CI is the test for the gates**, and it gets stricter without getting slower. `lint-docs` runs in
  parallel with `lint-ts` rather than serially inside it, and `lint-ts` stops paying an Astro
  `npm ci` it never needed.
- **`scripts/lint.sh all` gains the schema-staleness check** — and, per (d), gains it in a form that
  no longer rewrites the working tree. Today its only runner is `ci.yml:73-76`, i.e. post-push.
- **The gates become runnable on a partial checkout.** `scripts/test.sh py`, `scripts/typecheck.sh py`,
  `scripts/lint.sh py` already needed no Node; `scripts/lint.sh ts` now needs one npm root instead of
  two, and any missing root reports the install command instead of `command not found`.

Manual verification for the implementer, in a scratch clone (do not do this in a working checkout):

- with `docs/node_modules` absent, `scripts/lint.sh py` and `scripts/lint.sh ts` must pass and
  `scripts/lint.sh docs` must fail with `run: npm ci --prefix docs`;
- `scripts/test.sh docs`, `scripts/typecheck.sh meta` and `scripts/fmt.sh meta` must each exit **1**
  with a usage string listing only that gate's scopes;
- `scripts/lint.sh py ts` must exit 1 (`one scope per invocation`), and `scripts/typecheck.sh --fix`
  must exit 1 with a usage string that does not mention `--fix`;
- `git status --short` must be unchanged after `scripts/lint.sh meta`, both when the schema types are
  current and when they are deliberately stale.

## Risks & alternatives

- **Alternative: guard the docs step on binary presence and skip.** This is `docs/issues/07:6-7`'s
  first suggestion, and it is the wrong one. A gate that reports green over a surface it did not check
  is worse than a gate that fails: `fmt.sh` would silently stop checking `docs/` formatting on every
  machine that has not run `npm ci --prefix docs`, including CI if an install step is ever dropped.
  Take the issue's **second** remedy — document the setup — and add a precise failure. Hard-fail plus
  the exact command is the honest shape. The same reasoning is why an undeclared scope errors instead
  of no-opping.
- **Alternative: one global `GATE_SCOPES` in `_gate.sh`.** Rejected in review and correctly.
  A single five-value list would be assigned in the module whose thesis is stating things once and
  then read by nobody — the usage string and the parse `case` would each hard-code the list again, so
  the enumeration would appear three times — and it would give `test.sh` a `docs` scope and
  `typecheck.sh` a `meta` scope that exit 0 having checked nothing. Per-gate `GATE_SCOPES`, read by
  `gate_usage` and `_gate_declares`, is the version where the declaration is load-bearing.
- **Alternative: leave `actionlint` in `scripts/lint.sh` and just align the versions.** Rejected. Even
  aligned, it is a third pin that nothing enforces (the `$PATH` binary takes no version from any file),
  and on a workflow-touching commit it lints the workflows twice. The pass-through deletion test above
  settles it; the coverage it costs is priced in item 3.
- **Alternative: keep the schema check CI-only and give `meta` only `check-synced`.** Smaller, and it
  sidesteps item 6 entirely. Rejected: it leaves `lint-meta` re-listing one command in the generator,
  which is exactly the failure item 4 exists to close, and it leaves the ADR-0003 guarantee
  unverifiable before push.
- **Alternative: keep `meta` out of `all` so the bare default stays cheap.** Rejected: it would make
  `all` mean "every declared scope _except one_", the one exception nobody would remember, and it
  would re-create the undeclared-extra problem item 4 is about — in mirror image.
- **Alternative: a `just`/`make` front end.** Explicitly not proposed.
  `docs/architecture-deepening-plan.md:62-70` decided the scripts are the seam and CI calls them with a
  scope. That is a settled choice, this proposal completes it rather than reopening it, and adding a
  task runner would put the scope vocabulary back in two places.
- **Alternative: keep `docs` inside the `ts` scope and only add `need_node`.** Smaller, and it does fix
  the error message. Rejected because it leaves the interface lying: `ts` would still be the only way
  to ask for docs linting, and CI's `lint-ts` would still install two npm trees to run one linter.
- **Risk: `need_node` tests for a directory, not a binary.** A partially-installed or stale
  `node_modules` passes the check and the failure reverts to `command not found`. Accepted: the
  binary names differ per gate and per package, so testing them would put a toolchain inventory back
  into the shared module. `-d node_modules` covers the case that actually happens — never installed.
- **Risk: `_gate.sh` is a small module.** ~60 lines behind a six-symbol interface is not deep in
  absolute terms. Accepted — the justification is locality, not leverage, and the evidence that
  locality is the binding constraint is `fmt.sh:6-17`, which drifted from its three siblings without
  anyone noticing.
- **Risk: `bash` sourcing and pre-commit.** `.pre-commit-config.yaml:12-23` uses `language: script`,
  which executes the entry from the repo root; `_gate.sh` resolves `REPO_ROOT` from `BASH_SOURCE[0]`,
  not `$0`, so it is correct under both direct invocation and sourcing. `_gate.sh` must be committed
  non-executable so nothing mistakes it for a gate. Every `_gate.sh` conditional is an `if` block,
  never a bare `&&` list, so a false test cannot abort a caller running under `set -e`.
- **Risk: `all` still requires the docs toolchain**, so a fresh checkout's first commit still fails
  until `npm ci --prefix docs` runs. Accepted and intended — with a one-line diagnosis instead of a
  stack of npm noise, and with `AGENTS.md` naming the three installs up front.

### Scope boundaries vs siblings

- **[18](./18-check-deps-decision-logic.md) — no overlapping hunk; regenerate after merge.** 18 reports
  its `ci.yml` hunk as one job appended after `test-action` (`ci.yml:159-169`), and its generator hunks
  as `_ci_workflow()`'s jobs-dict tail (`ghagen_workflows.py:161-173`) plus `_ghagen_update_action()`
  (`:612-833`). My `ci.yml` territory is the lint jobs — `lint-py` (`:14-28`), `lint-ts` (`:29-49`),
  `lint-meta` (`:50-77`) — and my generator territory is `:50-97`, including the actionlint step at
  `:77-80`. Content-disjoint in both files, far enough apart for git to auto-merge. The `18 — 23` edge
  is therefore a **regenerate-after-merge constraint, not a serialization constraint**: whichever lands
  second re-runs `uv run ghagen synth` and confirms `uv run ghagen check-synced`.
- **Correction to this proposal's earlier line-stability claim.** An earlier draft told 18 that only
  `ci.yml` coordinates would move. That was **false**. This proposal changes the line count of
  `_ci_workflow()` itself — deleting `ghagen_workflows.py:58` and `:63-66`, inserting a `lint-docs`
  `Job(...)` after `:62`, and collapsing `:81-95` into one `Step` — so **both** files shift below the
  edit, with a non-zero net delta that only regeneration settles. Every citation below
  `ghagen_workflows.py:62` and below `ci.yml:49` must be re-derived after 23 lands. Known stale
  citations: 18's `ci.yml:159-169`, `ghagen_workflows.py:161-173` and `:612-833`; and 09's `ci.yml:105`
  (`scripts/typecheck.sh ts` in `typecheck-ts` — verified, and outside my region). Their _content_ is
  unaffected in every case.
- **Correction owed to 18.** `18` §What sits behind the seam cites `ci.yml:69-72` as precedent that
  `lint-meta` makes authenticated API calls in CI. It does not — `check_sync` is pure and takes no
  network (`packages/python/src/ghagen/pin/engine.py:138-155`), and this proposal deletes the unused
  `GITHUB_TOKEN`. 18's argument for its own non-hermetic job needs a different precedent.
- **[19](./19-main-owns-exit-codes.md) — edge dropped.** 19 states at `:39-40` that both its new suites
  run under the existing `scripts/test.sh` and that it adds no new gate. Confirmed from this side: 19
  touches `packages/**` CLI entry points and fixture files; this proposal touches no file under
  `packages/`. No shared file, no ordering constraint.
- **[09](./09-construction-time-validation-parity.md), [10](./10-delete-modelspec-order.md),
  [11](./11-shared-spec-surface-table.md), [14](./14-versions-owns-comparison.md),
  [17](./17-upgrade-report-renderer-module.md)** each _cite_ `scripts/*.sh` in their migration plans
  (`09` §(c) One home for the version grammar: a fourth declarative ModelSpec field, bound by a shared value table, `10` §Proposed interface, `11` §(c) An exhaustive-by-construction spec registry in TypeScript, `14` §The engine call site, `17` §What sits behind the seam) as the gates they run. They do not modify them.
  The gate invocations they name — `scripts/test.sh all`, `scripts/typecheck.sh all`,
  `scripts/lint.sh all` — are all still valid after this proposal; `all` remains the default and
  remains the union of each gate's declared scopes. Only 09 also cites a `ci.yml` line (`09` §Modified — (b) only, pending the Phase 3 decision below →
  `ci.yml:105`), covered by the regenerate-after-merge note above.

### `FIXTURES_DIR`: verified, and deliberately **not** in this proposal

The divergence is real, and the doc comment is textually identical modulo comment syntax:

```python
# scripts/ghagen_schema/paths.py:34-35
#: Shared golden fixtures consumed by both ports' test suites.
FIXTURES_DIR = REPO_ROOT / "fixtures"
```

```ts
// packages/typescript/src/paths.ts:40-41
/** Shared golden fixtures consumed by both ports' test suites. */
export const FIXTURES_DIR = resolve(REPO_ROOT, "fixtures", "expected");
```

One name, one sentence of documentation, two directories. `fixtures/` contains exactly one entry,
`expected/`, so the Python constant points at the parent of the only thing anyone wants — and both its
callers say so immediately:

- `packages/python/tests/test_integration/test_snapshots.py:5,39` — imports `FIXTURES_DIR`, then
  `SNAPSHOT_DIR = FIXTURES_DIR / "expected"`.
- `packages/python/tests/test_cli/test_deps.py:9,23` — imports it _as_ `_FIXTURES_ROOT`, then
  `FIXTURES_DIR = _FIXTURES_ROOT / "expected"`, rebinding the name to mean what the TS port already
  means by it.

The TS caller (`packages/typescript/src/integration/test-utils.ts:6,8,11`) uses it directly.

**Label: LIVE divergence, LATENT breakage — and the breakage would be loud, not silent.** Nothing fails
today; both ports resolve real paths and the suites are green. An earlier draft called the failure mode
"silent"; that was wrong. Under the remedy below the failure is an `ImportError` in Python and a `tsc`
error in TypeScript. Under any align-one-port variant it is `ENOENT`, because `fixtures/` contains
**only** `expected/` — so `fixtures/<golden>` can never resolve to a real-but-wrong file. There is no
path on which a wrong file is read quietly. What is live is the _authoring_ trap: someone writing a
cross-port test reads one doc comment and gets different directories depending on which port they are
in, and `test_deps.py:23` shows someone has already worked around it. The Python constant also fails
the deletion test on its own terms: every caller strips it back to a pass-through by re-appending
`expected`.

**Four siblings have taken a hard dependency on today's values**, not two:

1. `15` §(b) The encoders and decoders, single-homed and explicit states its new byte-oracle test _"Python resolves it as
   `FIXTURES_DIR / "expected" / …`; TypeScript imports `FIXTURES_DIR` … which already points at
   `fixtures/expected` — neither `paths.ts` nor `ghagen_schema/paths.py` is modified,"_ and `15` §New
   names both files in its non-conflict list.
2. `12` §2. The gutter is nobody's decision — in either port. Live, and it diverges. cites `paths.ts:41` and `paths.py:35` as the coordinates of the shared
   byte oracle.
3. `19` §New writes `resolve(FIXTURES_DIR, "..", "cli-exit-codes.yml")` — a `..`
   traversal against today's TypeScript value, the most fragile of the four.
4. `14` §Modified and `14` §The shared table declare the asymmetry out of scope and route around it;
   `15` §What sits behind the seam records that 14 deferred it to **23**.

**The remedy, so it is actionable wherever it lands.** Delete the ambiguous name from both ports and
replace it with two unambiguous ones, mirrored:

```python
FIXTURES_ROOT = REPO_ROOT / "fixtures"            # the directory
EXPECTED_DIR = FIXTURES_ROOT / "expected"         # the golden files both ports read
```

```ts
export const FIXTURES_ROOT = resolve(REPO_ROOT, "fixtures");
export const EXPECTED_DIR = resolve(FIXTURES_ROOT, "expected");
```

Then `EXPECTED_DIR` means one directory in both ports, and `test_deps.py`'s rebinding and
`test_snapshots.py`'s re-append both disappear. Files, for the orchestrator's graph — **not this
proposal's conflict set**: `scripts/ghagen_schema/paths.py` (35), `packages/typescript/src/paths.ts`
(41), `packages/python/tests/test_integration/test_snapshots.py` (451),
`packages/python/tests/test_cli/test_deps.py` (911),
`packages/typescript/src/integration/test-utils.ts` (52). One more file carries a stale reference to
the same constant and belongs with it: `docs/specs/0005-typed-engine-report-seam.md:127` says the
golden fixtures are loaded by Python `tests/test_integration/` via `conftest.py` → `FIXTURES_DIR`, but
that `conftest.py` imports only `SCHEMA_DIR` (`:10`); the `FIXTURES_DIR` import is in
`test_snapshots.py:5`.

**Why it is not in 23, whatever the schedule.** Fixing it means touching five files under `packages/`
and `scripts/ghagen_schema/` that this proposal otherwise goes near only for `check.py`. Folding it in
turns a dev-tooling proposal into a two-port proposal and serialises 23 against test-file work in four
siblings.

**Open — Phase 3 decision:** whether the `FIXTURES_DIR` Python/TypeScript asymmetry is fixed this round
— as a standalone hotfix on `main`, sequenced after 12, 14, 15 and 19 land — or deferred by writing the
remedy above into `docs/issues/08-fixtures-dir-name-collision.md`. Review's recommendation is **defer**,
on the grounds that nothing fails today and a pre-implementation hotfix would force four authors to
re-verify citations mid-round; the `docs/issues/08` row in _Files involved_ is conditional on that
choice. Not decided here.

## ADR / CONTEXT.md impact

- **No ADR is contradicted.** ADRs 0001-0007 cover the Document serialization seam, config globals,
  schema sync, user-file tracking, the synthesis pipeline, pin's parsed refs, and config discovery.
  None speaks to the dev-gate interface, and this proposal touches no runtime module.
- **ADR-0003 (schema sync is dev-only; conformance is test-based)** is _reinforced_, not reopened.
  `ghagen_schema check` is described at `.github/ghagen_workflows.py:86-90` as _"the single line that
  actively enforces ADR-0003's author-conformance guarantee"_ — item (d) gives it a local runner
  (`scripts/lint.sh meta`) in addition to its CI one, and makes it non-mutating so that local runner is
  safe. Preserve that comment when the step moves; it is the only place the connection is written down.
- **No new ADR proposed.** The gate design was already decided in
  `docs/architecture-deepening-plan.md:56-73`; this is its completion, not a new decision. If the
  orchestrator wants the scope vocabulary pinned somewhere more durable than a plan document, the
  right home is an ADR titled _"Dev gates are the seam; scope enumerates toolchain roots"_ — flagged,
  not written here.
- **`docs/architecture-deepening-plan.md:65-66` supersession.** That document is this proposal's stated
  authority, and `:65-66` currently reads:

  > - `scripts/test.sh [py|ts|all]`, `scripts/lint.sh [py|ts|all]`, `scripts/typecheck.sh [py|ts|all]`
  >   (default `all`). `fmt.sh` likewise for symmetry.

  Citing a document as authority while leaving it stating the vocabulary you replaced is the exact
  defect this proposal is about, so **23 owns the edit** rather than routing it to `docs/issues/`. Two
  forms are available and the choice is a reversal of a decided detail:

  **Open — Phase 3 decision:** amend `:65-66` in place to the per-gate five-value vocabulary
  (line-neutral, two lines → two lines, so `07:51-52`, `10` §Problem and `18` §3c. || true does not suppress the failure it appears to suppress do not shift), **or**
  mark `## 1. CI parity gate — scoped scripts (decided)` (`:56-73`) as a landed historical record and
  leave its text untouched. Not decided here.

- **`AGENTS.md:47-64`** (the only file outside `docs/` that documents the gates) is the doc change and
  is in the Files-involved table. It needs: a Setup subsection naming `uv sync`,
  `npm ci --prefix packages/typescript`, `npm ci --prefix docs`, **and `pre-commit install`** — the
  last because `.git/hooks/` holds only samples in this checkout and nothing in the repo tells a
  contributor to install the hooks, which makes every local-gate claim in this proposal conditional on
  an undocumented step. It also needs the per-gate scope values from the table in (a); the note that
  `--fix` is accepted by `fmt.sh` and `lint.sh`; and `uv run ghagen deps check-synced` /
  `python -m ghagen_schema check` replaced by `scripts/lint.sh meta`.
- **No `CONTEXT.md` change.** `CONTEXT-MAP.md` and the per-package `CONTEXT.md` files carry domain
  vocabulary (Document, ModelSpec, Emitter, pin, uses-site, lockfile); "gate" and "scope" are dev
  tooling and belong in `AGENTS.md`. This proposal claims **no region** in the round's
  `packages/typescript/CONTEXT.md` allocation. If a reviewer disagrees, the one-line addition is a
  **gate** entry meaning "a `scripts/*.sh` entry point taking a toolchain scope", added to
  `CONTEXT-MAP.md` only — flagged here rather than made, per the authoring rules.
