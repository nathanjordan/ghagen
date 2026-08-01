# 17 — Move the upgrade-report renderer out of the Typer command into `pin/render`

**Status:** proposed | **Ports:** both | **Effort:** L | **Depends on:** **20** (prunes dead branches in `pin/engine.*`), then **19** (consolidates both `cli.md` pages' `## Exit codes` sections to end-of-file — this proposal inserts _inside_ `## ghagen deps upgrade`, so 19 must land first), then **14** (`versions` owns its comparison — reshapes `pin/engine.*`'s versions stage, renames `Severity` → `BumpSeverity`, and rewrites `test_versions.py`, which this proposal then adds `checked_*` assertions around). 14 already declares "lands after **19** … lands before **17**". Also **16** (lifts transport policy into `HttpClient`), which deletes the `FakeTransport` this proposal's engine tests are built on and replaces it with a shared double. Build on the pruned tree. **18** depends on this proposal.

**16 does not lengthen the critical path.** The chain is 20 → 19 → 14 → 17; 16 shares no file with 19 or 20 and only the Python barrel with 14, so it is a **fourth parallel predecessor**, not a fifth link. 16 is in dispatch batch 1 and this proposal is in batch 3, so the ordering is satisfied without any extra sequencing.

Effort is **L**, not M: the test-surface change is the largest single one in the round (`test_deps.py` 911 → ~330, `deps.test.ts` 261 → ~130, two new test files, one new golden), it touches thirteen existing files across both ports plus a spec and both `CONTEXT.md`s, and it carries a user-visible breaking change to the `--format json` key set that has to be documented in two places and inverted in five existing tests.

## Files involved

Line counts are `wc -l` on `main` at `e7a972c`.

### Modified

| Path                                            | Lines | Role in this proposal                                                                                                                                                                                                                                             |
| ----------------------------------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/src/ghagen/cli/deps.py`        | 360   | `deps_upgrade`'s render tail (199-249) collapses to ~14 lines; the five renderers (252-360) move out. **`valid_formats` (173) is NOT touched** — see _Risks_                                                                                                      |
| `packages/typescript/src/cli/deps.ts`           | 389   | Mirror. **Hunks: imports 8-21; `depsUpgrade`'s render tail 180-230; delete 233-342; export list 380-389.** Neither the format validation (159-170) nor `buildDepsCommand` (344-378) is touched                                                                    |
| `packages/python/src/ghagen/pin/engine.py`      | 294   | `UpgradeReport` (182-189) gains `checked_versions` / `checked_lockfile`; the locals at 215-216 are deleted and the flags set at construction (207), before the no-refs early return (210-211)                                                                     |
| `packages/typescript/src/pin/engine.ts`         | 318   | Mirror: locals at 219-220 deleted, flags set in the report literal at 205-210, before the early return at 213-215                                                                                                                                                 |
| `packages/python/src/ghagen/pin/__init__.py`    | 58    | Export `render_upgrade_report`, `UpgradeFormat` — **two** names, from a new `from ghagen.pin.render import (…)` landing at `:29` (isort sorts `render` after `lockfile`, before `sites`), plus two `__all__` entries in the alphabetical block at `:33-58`        |
| `packages/typescript/src/pin/index.ts`          | 46    | Mirror export (a new `export { … } from "./render.js";`)                                                                                                                                                                                                          |
| `packages/typescript/src/index.ts`              | 203   | Mirror re-export inside the `from "./pin/index.js"` block that ends at `:203`                                                                                                                                                                                     |
| `packages/python/tests/test_cli/test_deps.py`   | 911   | **911 → ~330.** Five engine-re-testing classes deleted; four renderer classes move to `test_render.py`; the CLI keeps only what is genuinely CLI                                                                                                                  |
| `packages/typescript/src/cli/deps.test.ts`      | 261   | **261 → ~130.** The two contract `describe`s (70-164) move to `render.test.ts`; the mode/empty-JSON block (166-261) is replaced except the stderr hotfix test (218-246); `emptyReport()` (42-44) gains the two new fields; a new stdout-half hotfix test is added |
| `packages/python/tests/test_pin/test_engine.py` | 251   | Assert the two new report flags per mode, including the no-refs and `lockfile=None` cases; absorb `test_api_error_continues_with_warning`. **Shared with 16, which lands first and rewrites this file's whole fixture layer** — all line numbers below are pre-16 |
| `packages/typescript/src/pin/engine.test.ts`    | 242   | Mirror flag assertions inside `describe("upgrade()")` (171-242). Same 16 caveat: 16 deletes `:54-84`, so this span shifts up ~30 lines                                                                                                                            |
| `docs/src/content/docs/python/cli.md`           | 210   | Document the `--format json` key-presence rule under `## ghagen deps upgrade` (currently undocumented)                                                                                                                                                            |
| `docs/src/content/docs/typescript/cli.md`       | 223   | Mirror                                                                                                                                                                                                                                                            |
| `docs/specs/0005-typed-engine-report-seam.md`   | 439   | §2.2's invariant list (`:115-121`) is falsified by this change and must be amended; §2.3 (`:141-144`) names `tests/test_cli/test_deps.py` and `src/cli/deps.test.ts` as the assertion homes this proposal relocates. See _ADR / CONTEXT.md impact_                |
| `packages/python/CONTEXT.md`                    | 114   | New **Upgrade report** pin-glossary entry, immediately after 14's **Bump** entry (append order **16 → 14 → 17**), + a new Surface-notes bullet (append order **16 → 17 → 10**)                                                                                    |
| `packages/typescript/CONTEXT.md`                | 119   | Mirror, same two regions and the same two append orders                                                                                                                                                                                                           |

### New

| Path                                            | Lines      | Role in this proposal                                                                                 |
| ----------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------- |
| `packages/python/src/ghagen/pin/render.py`      | new (~150) | The module: `render_upgrade_report(report, *, output_format) -> str`, plus the five private renderers |
| `packages/typescript/src/pin/render.ts`         | new (~140) | Mirror: `renderUpgradeReport(report, outputFormat): string`                                           |
| `packages/python/tests/test_pin/test_render.py` | new (~170) | Direct renderer unit tests — no `CliRunner`                                                           |
| `packages/typescript/src/pin/render.test.ts`    | new (~180) | Mirror — no command invocation                                                                        |
| `fixtures/expected/upgrade_text.txt`            | new (~12)  | Shared golden for the human-text format, which today has **no** direct test in either port            |

Deliberately **not** in the table: `check-deps/action.yml` (187) and `.github/ghagen_workflows.py` (845). The consumer reads `d.get('version_bumps',[])` / `d.get('lockfile_stale',[])` (`check-deps/action.yml:67-68`, generated from `.github/ghagen_workflows.py:702-703`), so the key-presence fix is invisible to it. Rewriting that consumer is **18**'s job.

## Problem

`packages/python/tests/test_cli/test_deps.py` is **911 lines** — the largest file in the repo, and 3.5× its TypeScript peer (`packages/typescript/src/cli/deps.test.ts`, 261). It got that way for two reasons, and the second one has already produced a live defect.

### 1. The renderer has no seam in Python — and the ports have quietly diverged on this

The five renderers are pure functions over a typed report:
`_bump_to_json` (`packages/python/src/ghagen/cli/deps.py:252-262`), `_stale_to_json` (`:265-274`),
`_render_pr_body` (`:277-302`), `_render_issue_body` (`:305-336`), `_print_human_report` (`:339-360`).
Four of the five are importable and are imported directly by the tests (`test_deps.py:12-17`).

What has no seam is the **mode × format dispatch** — the 51-line tail at `deps.py:199-249` that decides which keys to emit and which renderer to call. It lives inside `deps_upgrade`, and every one of that command's five parameters defaults to a Typer `OptionInfo` sentinel. Verified:

```text
$ uv run python -c "import inspect; from ghagen.cli import deps; print(inspect.signature(deps.deps_upgrade))"
config        = <typer.models.OptionInfo object at 0x108ed6990>
check         = <typer.models.OptionInfo object at 0x108ed6ad0>
output_format = <typer.models.OptionInfo object at 0x108ed6c10>
mode          = <typer.models.OptionInfo object at 0x108ed6d50>
token         = <typer.models.OptionInfo object at 0x108ed6e90>
```

The function is callable, but a direct call must supply all five arguments **and** still runs `_find_config`, `track_user_files` and `_github_client` (`deps.py:184-189`). No test does it. Every test of the dispatch goes through `CliRunner`.

To be exact about the claim: it is the **dispatch** that is `CliRunner`-only, not the renderers. Four of the five renderers are already imported and called directly by tests in both ports (`test_deps.py:12-17`, `deps.test.ts:39-40`). This proposal is a move plus a bug fix plus a testability win — not a depth win over an opaque wall.

**The TypeScript port does not have this problem.** `depsUpgrade` is exported (`deps.ts:384`) and `deps.test.ts:166-261` drives it directly under `vi.mock("../pin/index.js")` — no CLI runner, no config file, no network. The brief's claim that TS "does the same job in 222 lines" is **wrong on both counts**: the file is 261 lines today (222 was the count at `658a6e1`; the `0cae9b1` stderr hotfix added a test), and it does a _narrower_ job — it mocks `upgrade()` entirely and never exercises the engine. That is precisely why it is short. **LIVE port divergence**, and it is the whole explanation for 911 vs 261.

**Arithmetic for the CLI-driven claim.** Summing the line span of every test function in `test_deps.py` whose body contains `runner.invoke`: **596 lines** of 911. Excluding the three `deps check-synced` tests (`:52-67`, `:70-86`, `:89-109` = 54 lines, a different command), **542 lines** are `CliRunner`-driven `deps upgrade` scenarios. Only **84 lines** (`:730-768`, `:770-781`, `:876-891`, `:893-901`, `:903-906`, `:908-911`) call a renderer directly.

**Five of those classes re-test the engine.** Each has a direct counterpart that asserts the same thing without a CLI:

| Class in `test_deps.py`                                                                                                                        | Span    | Lines | Already covered directly by                                                                                      |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ----- | ---------------------------------------------------------------------------------------------------------------- |
| `TestUpgradeVersionsMode`                                                                                                                      | 199-260 | 62    | `test_pin/test_engine.py:188-204` `test_detects_version_bump`                                                    |
| `TestUpgradeLockfileMode` **minus `test_lockfile_mode_no_lockfile_configured` (304-337)**                                                      | 263-302 | 40    | `test_engine.py:217-230` `test_detects_stale_lockfile_entry`                                                     |
| `TestUpgradeAllMode`                                                                                                                           | 340-357 | 18    | the engine's own `mode` dispatch, `pin/engine.py:215-216`                                                        |
| `TestUpgradeApply` **minus `test_upgrade_modifies_source_files` (363-380) and `test_apply_with_json_format_keeps_stdout_parseable` (382-404)** | 406-423 | 18    | `test_engine.py:206-215` `test_applies_version_bump` + the dry-run asserts at `test_engine.py:202-204`           |
| `TestUpgradeNonSemver`                                                                                                                         | 498-550 | 53    | `test_pin/test_versions.py:45-46` `test_nonsemver_main` and `:108-110` `test_returns_none_for_nonsemver_current` |
| `TestUpgradeNoRefs`                                                                                                                            | 647-716 | 70    | `test_engine.py:232-251` `test_no_refs_returns_empty`                                                            |

**261 lines** that spin up a temp project, write a config, patch two `GitHubClient` methods and run a Typer command in order to re-assert a fact `test_engine.py` already asserts in ~17 lines with a canned transport. That transport is `FakeTransport`, today at `test_engine.py:52-65` — but **16 lands first and moves it**: see the note on 16 in _Scope boundaries vs siblings_. All `test_engine.py` line numbers in this document are against `main` at `e7a972c`; 16 removes ~16 lines above them, so they shift.

Three tests inside those class spans are **not** engine re-tests and are explicitly retained — see _Test impact_. Two of them are the only coverage in either port of facts this proposal must not lose: `test_lockfile_mode_no_lockfile_configured` (`:304-337`) is the **sole** `App(lockfile=None)` upgrade test in the repo, and `test_upgrade_modifies_source_files` (`:363-380`) is the **only** test in either port that exercises the `output_format is None` branch of the `0cae9b1` progress-note routing (`deps.py:205`).

**A second LIVE gap, in the other direction.** `_print_human_report` (`deps.py:339-360`) and `printHumanReport` (`deps.ts:322-342`) have exactly one caller each (`deps.py:249`, `deps.ts:229`) and **zero** test importers — `printHumanReport` is not even in the TS export list (`deps.ts:381-389`). The default output format of the most-used `deps` command is asserted in Python only by substring through `CliRunner` (`test_deps.py:215-218`, `:456`, `:679`) and in TypeScript **not at all**. It is the one `deps upgrade` format with no golden fixture, and therefore the one with no cross-port parity oracle.

### 2. The CLI recomputes a decision the engine already made — and it shows

`packages/python/src/ghagen/cli/deps.py:210-211`:

```python
    check_versions = mode in ("versions", "all")
    check_lockfile = mode in ("lockfile", "all")
```

`packages/python/src/ghagen/pin/engine.py:215-216`:

```python
    check_versions = mode in ("versions", "all")
    check_lockfile = mode in ("lockfile", "all")
```

Byte-identical. TypeScript is the same modulo the receiver — `deps.ts:194-195` uses `mode`, `engine.ts:219-220` uses `opts.mode`; the right-hand sides are character-for-character equal. An `rg` over every non-`.md` source in both packages finds these four sites and no others.

That duplication is the **direct cause** of a user-visible inconsistency: the JSON key set depends on whether the result is empty, because the empty case takes a different branch (`deps.py:213-227`, `deps.ts:197-210`) that ignores the flags entirely and hard-codes both keys.

**Reproduced, Python** (`--check --format json`, `actions/checkout@v4`, tags mocked):

```json
=== --mode versions   (v5 available)              === --mode versions   (already latest)
{                                                 {
  "version_bumps": [                                "version_bumps": [],
    {                                               "lockfile_stale": []
      "uses": "actions/checkout@v4",              }
      "current": "v4",
      "latest": "v5",                             ← one key when non-empty,
      "severity": "major",                          two keys when empty
      "source_files": ["ghagen_config.py"]
    }
  ]
}
```

`--mode lockfile` against a stale lockfile behaves the same way: non-empty emits `{"lockfile_stale": [...]}` only; empty emits both keys. `--mode all` emits both keys in either case.

**Reproduced, TypeScript** — identical, verified by driving the exported `depsUpgrade` with a mocked `upgrade()`:

```json
=== --mode versions   (non-empty)                 === --mode versions   (empty)
{                                                 {
  "version_bumps": [                                "version_bumps": [],
    { "uses": "actions/checkout@v4",                "lockfile_stale": []
      "current": "v4", "latest": "v5",            }
      "severity": "major",
      "source_files": ["ghagen.workflows.ts"] }
  ]
}
=== --mode lockfile   (non-empty)
{ "lockfile_stale": [] }
```

**LIVE, both ports, no divergence.** A consumer of `ghagen deps upgrade --check --format json --mode versions` cannot write `data["version_bumps"]` — the key is present only when there is something to report, which is exactly backwards from what a machine-readable contract should do.

It is worse than an accident: it is **enshrined**. `test_deps.py:821-862` (`test_empty_report_emits_both_keys_regardless_of_mode`) and `deps.test.ts:248-260` both assert the inconsistency as intended behaviour — the Python test's own docstring says so — and `docs/specs/0005-typed-engine-report-seam.md:118-121` records the choice being made:

> - Edge case to lock down: the "everything up to date" early return
>   (deps.py:196-206 / deps.ts:180-189) emits _both_ keys as `[]` regardless of
>   `mode`. Tests must assert this exactly (or the code is changed to honor `mode`
>   in the empty case too — pick one and pin it).

Spec 0005 picked "assert as-is" because at the time there was no cheap way to make the empty case honour `mode` — the flag lived only as a local inside a Typer command. This proposal removes that constraint. Reversing that choice is an **Open — Phase 3 decision**; see _Risks & alternatives_.

And the reason nobody noticed: ghagen's own consumer masks it. `check-deps/action.yml:67-68` reads `d.get('version_bumps',[])` / `d.get('lockfile_stale',[])` — defensive `.get`, silently returning `[]` for a missing key. That is the _identical_ failure mode as the phantom `helper_provided` field that spec 0005 §1.1 was written to kill: a producer/consumer seam that drifts with zero signal because every read is defaulted.

**LATENT, and the reason to fix the cause rather than the symptom:** the duplication has no guard. Add a fourth mode, or change the engine's derivation, and the CLI silently disagrees. `test_deps.py` cannot catch it — the classes above pin the _engine's_ behaviour, not the CLI's agreement with it.

**LATENT, and deliberately left as-is by this proposal:** neither `check_lockfile` nor its replacement is sufficient to know whether the lockfile stage actually _ran_. `engine.py:261` guards it with `and app.lockfile_path is not None`; with `lockfile=None` the stage is skipped entirely, yet the payload still says `"lockfile_stale": []` (asserted at `test_deps.py:304-337`, the repo's only test of that path). "Checked and found nothing" and "never checked" remain indistinguishable in the payload after this proposal. That is a conscious scope boundary, not an oversight — see _Proposed interface (a)_ and the note to **18**.

## Current interface

**`UpgradeReport`** (`pin/engine.py:182-189`, `pin/engine.ts:179-184`) — four fields, all lists: `version_bumps` / `lockfile_stale` / `changed_files` / `warnings`. It reports _what was found_. It does not report _what was looked for_, so any consumer that needs the second fact must re-derive it from `mode` — which is exactly what the CLI does.

**The renderers** — five module-private functions per port, taking `(list[VersionBump], list[LockfileStaleEntry])`. Four return `str`; `_print_human_report` / `printHumanReport` return `None` and write to stdout themselves. Their interface is not the type signature: a caller must additionally know

- which of the four formats needs a trailing newline (`typer.echo(..., nl=False)` for pr-body and issue-body at `deps.py:222,224,242,246`; plain `typer.echo` for json and text),
- that the empty case is a _different_ code path with different key semantics,
- that `mode` must be re-derived to decide the JSON keys,
- that `_print_human_report` prints nothing for an empty report, so the caller must print `"Everything is up to date."` itself (`deps.py:226`).

Four facts that live in the command, about the renderers. That is a shallow interface: the caller must know nearly as much as the implementation does.

**The command tail** (`deps.py:199-249`, `deps.ts:180-230`) — 51 lines each, doing five different jobs: emit warnings to stderr, emit the apply-progress note to stdout-or-stderr, re-derive the mode flags, branch on empty, and branch on format.

## Proposed interface

### (a) `UpgradeReport` reports what it looked for

```python
# pin/engine.py
@dataclass
class UpgradeReport:
    version_bumps: list[VersionBump] = field(default_factory=list)
    lockfile_stale: list[LockfileStaleEntry] = field(default_factory=list)
    changed_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    checked_versions: bool = False
    """The run was asked for newer version tags (``mode`` in versions/all)."""

    checked_lockfile: bool = False
    """The run was asked for stale lockfile SHAs (``mode`` in lockfile/all).

    "Asked for", not "ran": this stays True when ``app.lockfile_path is None``,
    where ``engine.py:261`` skips the stage. A consumer that must distinguish
    "no lockfile configured" from "checked, nothing stale" still has to consult
    ``app.lockfile_path`` — this field does not carry that fact. See the note
    to **18** in _Scope boundaries vs siblings_.
    """
```

Both fields are, and are intended to be, **pure functions of `mode`**. What they buy is not new information — it is _where the information lives_: one derivation in the module that owns the decision, read by both the engine and the renderer, instead of four independent restatements of the same two expressions.

**TypeScript field optionality.** The TS `UpgradeReport` is an `interface` with all-required fields (`engine.ts:179-184`), and the mirror fields are **required** too — parity with Python, and an optional `checkedVersions?: boolean` would let a caller silently drop to `undefined`, which is exactly the defaulted-read failure mode spec 0005 §1.1 exists to prevent. Consequence, stated because it changes the migration: two TS `UpgradeReport` object literals must be updated in the same commit or `tsc` fails TS2739 — `engine.ts:205-210` (the real one) and `deps.test.ts:42-44` (`emptyReport()`). Python's dataclass defaults hide this asymmetry; the TS half of migration step 1 is not a pure addition.

`upgrade()` sets both **in the report literal**, not as locals, and — critically — **before the no-refs early return** (`engine.py:210-211`, `engine.ts:213-215`), so a project with no pinnable refs renders the same key set as any other:

```python
    report = UpgradeReport(
        checked_versions=mode in ("versions", "all"),
        checked_lockfile=mode in ("lockfile", "all"),
    )

    refs = collect_uses_refs(app)
    if not refs:
        return report            # flags already set

    ...
    if report.checked_versions:  # engine.py:215-216 deleted; the locals are gone
```

That ordering is the single fact the whole design turns on, so it gets its own named assertion in both ports rather than being implied by the mode tests: `test_no_refs_report_still_reports_checked_flags` in `test_engine.py` and `"a no-refs report still reports the checked flags"` inside `describe("upgrade()")` (`engine.test.ts:171-242`) — build an app with no `uses:` refs, run each of the three modes, assert the flags match the mode even though every result list is empty.

The engine's two stages read `report.checked_versions` / `report.checked_lockfile` instead of locals. TypeScript mirrors this exactly (`checkedVersions` / `checkedLockfile` in the `UpgradeReport` literal at `engine.ts:205-210`).

### (b) `pin/render` — one function, four formats

```python
# packages/python/src/ghagen/pin/render.py
UpgradeFormat = Literal["text", "json", "pr-body", "issue-body"]

def render_upgrade_report(
    report: UpgradeReport, *, output_format: UpgradeFormat = "text"
) -> str:
    """Render an upgrade report, returning the exact bytes to write.

    Pure: no console I/O, no CLI types. The returned string is already
    terminated as it should be written — the caller writes it verbatim.
    Which JSON keys appear is decided by ``report.checked_versions`` /
    ``report.checked_lockfile``, never re-derived from ``mode``.
    """
```

```ts
// packages/typescript/src/pin/render.ts
export type UpgradeFormat = "text" | "json" | "pr-body" | "issue-body";
export function renderUpgradeReport(
  report: UpgradeReport,
  outputFormat: UpgradeFormat = "text",
): string;
```

(Python uses `output_format`, not `format`: ruff's flake8-builtins rules are enabled — `select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM"]`, `pyproject.toml:54` at the **repo root** — so a `format` keyword argument trips A002. `output_format` also matches the existing CLI variable name at `deps.py:145`.)

**Full interface, stated:**

- **Returns** the complete output, newline-terminated exactly as it must be written. The caller never adds or suppresses a newline. `pr-body` and `issue-body` already satisfy this (`"\n".join([..., ""])`); `json` and `text` gain the trailing `"\n"` that `typer.echo` used to add.
- **Empty is not a special case.** An empty report renders through the same branch as a non-empty one. `pr-body` yields the bare `## ghagen dependency update` header; `issue-body` yields `""`; `text` yields `"Everything is up to date.\n"`; `json` yields the mode-selected keys with `[]` values.
- **JSON key presence** is `report.checked_versions` → `version_bumps`, `report.checked_lockfile` → `lockfile_stale`. Unconditionally. **This is the breaking change** — the wart above is gone.
- **`source_files` is omitted when empty** (unchanged; `deps.py:259-260`, `deps.ts:303-305`).
- **No I/O, no exceptions on well-formed input.** An unknown `output_format` is a programmer error; the CLI validates before calling.
- **Byte-parity across ports** is the standing invariant, now enforced by four shared goldens instead of two.

**No `MACHINE_FORMATS` constant.** An earlier draft of this proposal exported the accepted `--format` values from `pin/render` and pointed `deps.py:173` / `deps.ts:160-170` at them. Dropped: it would have one caller per port, and the values keep being restated anyway in the error message (`deps.py:176-177`) and the help text (`deps.py:148-151`, `deps.ts:370-371`), so the claimed de-duplication is not actually collected. It is also CLI flag vocabulary, which does not belong in a pure `pin/` module. The `--format` validation stays exactly where it is, untouched, in both ports. `UpgradeFormat` stays, because it is the renderer's own parameter type.

### (c) The command shrinks to orchestration

```python
    for warning in report.warnings:
        typer.echo(f"warning: {warning}", err=True)

    if report.changed_files:
        # Under --format the report itself owns stdout; this progress note goes
        # to stderr so `--format json` (without --check) stays machine-parseable.
        progress_to_stderr = output_format is not None
        typer.echo("Applied version bumps:", err=progress_to_stderr)
        for f in report.changed_files:
            typer.echo(f"  modified {f}", err=progress_to_stderr)

    typer.echo(
        render_upgrade_report(report, output_format=output_format or "text"),
        nl=False,
    )
```

`deps.py:199-249` (51 lines) → 14. `deps.py:252-360` (109 lines) leaves the file.

**The stdout/stderr split from the `0cae9b1` hotfix is preserved by construction, not by care.** The renderer returns a string and writes nothing, so it _cannot_ interleave with the progress note. The command keeps sole ownership of destinations: warnings → stderr always (`deps.py:199-200`); the apply-progress note → stderr iff `--format` is set (`deps.py:202-208`); the rendered report → stdout always. Both halves of the hotfix keep their guard tests in the _command_ test files, where they belong — they assert a routing fact, not a rendering fact. See _Test impact_ for the two guards this proposal retains and the one it adds, because today the routing is only half-asserted.

## What sits behind the seam

`pin/render` absorbs every fact a caller currently has to know about producing `deps upgrade` output:

- the four output formats and their exact bytes,
- the trailing-newline discipline that today is four scattered `nl=False` decisions,
- the empty-report shape per format, which today is a separate 15-line branch that contradicts the non-empty branch,
- the mapping from "what the engine looked for" to "which JSON keys appear".

What remains at the CLI edge is genuinely CLI: flag parsing, validation, exit codes, and **which stream** each piece of output goes to. That is the right division, and it is the one ADR-0007 already describes for config — pure result types at the seam, presentation at the edge. `pin/render` does not move presentation into the engine; it gives presentation its own module, still called from the edge, and makes it a _pure_ module so the edge stays in charge of I/O.

**Deletion test on `pin/render`.** Delete it and the five renderers plus the format dispatch return to `cli/deps.py` and `cli/deps.ts`. Within a single port that is **one** caller — so by call-count alone this is a hypothetical seam, and the honest answer is that it **fails the deletion test on leverage** and passes it on locality. What reappears is not duplication; it is the _coupling_:

- The dispatch becomes reachable only through `CliRunner` again (Python), so the 542 lines of CLI-driven scenarios come back with it.
- The empty-vs-non-empty key inconsistency comes back, because there is nowhere else to put the "which keys" decision.
- The human-text format loses its string-returning shape and becomes untestable without capturing stdout, which is why it has no golden fixture today.

So `pin/render` is deep in **locality**, not leverage: it concentrates one changing thing — output shape — in one module with one interface, and it makes that thing reachable. **One adapter = hypothetical seam.** Proposal **18** adds the second: it pulls `check-deps`'s bash decision logic across the CLI seam and consumes exactly this surface, at which point `pin/render` has two independent callers and the seam is real. This proposal is honest about landing at one and about 18 being the thing that justifies the barrel export.

**Deletion test on `checked_versions` / `checked_lockfile`.** Delete them and the renderer needs `mode`, which re-creates today's duplication one level down and puts a CLI flag value into a pure `pin/` function's signature. Two booleans on a report the engine already builds replace a derivation that currently exists in four places (`engine.py:215-216`, `deps.py:210-211`, `engine.ts:219-220`, `deps.ts:194-195`) with one derivation in two, and they make the dispatch reachable without a CLI runner. **Earned keep — on locality and reachability.** They carry no information `mode` does not; any argument that they are _more accurate_ than `mode` is false, including in the `lockfile=None` case (see the docstring in (a)).

## Migration plan

Pre-1.0; clean break. Lands **after 20** (which prunes `pin/engine.*`), **after 19** (which restructures both `cli.md` pages), and **after 14** (which rewrites the versions stage of `upgrade()` and moves `Severity` into `pin/versions`).

1. **Engine flags first, no behaviour change.** Add `checked_versions` / `checked_lockfile` to both `UpgradeReport`s; set them in the report literal ahead of the no-refs early return; delete the `check_versions` / `check_lockfile` locals and read the report fields instead. **In the same commit**, update the two TS `UpgradeReport` literals that would otherwise fail `tsc` TS2739 — `engine.ts:205-210` and `emptyReport()` at `deps.test.ts:42-44`. Add the per-mode flag assertions plus the named no-refs ordering test and a `lockfile=None` test to `test_engine.py` / `engine.test.ts`. Suite is green at the end of the step, but _not_ mid-step in TypeScript.
2. **Create `pin/render`.** Move the five renderers verbatim except `_print_human_report` / `printHumanReport`, which change from writing to returning. Add `render_upgrade_report` / `renderUpgradeReport` with the four-way dispatch, the flag-driven JSON key selection, and the empty-text case. Export `render_upgrade_report` + `UpgradeFormat` from the pin barrels and `packages/typescript/src/index.ts`.
3. **Add `fixtures/expected/upgrade_text.txt`** and the two `test_render` files; assert all four formats against shared goldens in both ports. This is the first direct coverage the human-text format has ever had.
4. **Rewire the commands.** Replace `deps.py:199-249` / `deps.ts:180-230` with the 14-line tail; delete `deps.py:252-360` / `deps.ts:233-342`; trim the export list at `deps.ts:380-389` to `depsPin, depsCheckSynced, depsUpgrade`. The `--format` validation is left alone in both ports.
5. **Cut the test files down.** Delete the five engine-re-testing class bodies, keeping the three retained tests listed in _Test impact_; move the four contract classes into `test_render.py` / `render.test.ts`; **invert** the two wart-pinning tests; add the two new CLI tests (stdout-half routing in TypeScript, warning echo in Python).
6. **Docs.** Add the key-presence rule to the `## ghagen deps upgrade` section of both `cli.md` files (AGENTS.md: "Update documentation when making any user-facing changes"). Anchors are given in _Scope boundaries vs siblings_.
7. Gates: `scripts/test.sh all`, `scripts/typecheck.sh all`, `scripts/lint.sh all`, `uv run ghagen check-synced`, `uv run ghagen deps check-synced`. No workflow regenerates differently — `check-deps/action.yml` is untouched. (Note that `scripts/lint.sh` defaults to the `all` scope at `lint.sh:6` and `lint.sh:20-26` guards the `docs/` npm toolchain on `ts`/`all`, so a bare `scripts/lint.sh` needs `npm ci --prefix docs` first; `scripts/lint.sh py` is ruff-only and safe.)

Note for **19**: step 4 removes `raise typer.Exit(0)` at `deps.py:227` (the empty-report early return). Falling off the end of the command exits 0 identically, so this is not an exit-code change — but it is an exit-code-_adjacent_ line. 19 lands first, so it will not see the removal; flagged so it is not read later as a regression against 19's landed state.

## Test impact

**Deleted from `test_deps.py` — redundant with existing direct tests** (five class bodies, **261 lines** after excluding the three retained tests):

| Deleted                                                                                 | Redundant with                                                               |
| --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `TestUpgradeVersionsMode` (199-260)                                                     | `test_engine.py:188-204`                                                     |
| `TestUpgradeLockfileMode` (263-302), minus the retained `:304-337`                      | `test_engine.py:217-230`                                                     |
| `TestUpgradeAllMode` (340-357)                                                          | the engine's mode dispatch, now asserted via `checked_*` in `test_engine.py` |
| `TestUpgradeApply` (406-423), minus the two retained tests at `:363-380` and `:382-404` | `test_engine.py:206-215` and `:202-204`                                      |
| `TestUpgradeNonSemver` (498-550)                                                        | `test_versions.py:45-46`, `:108-110`                                         |
| `TestUpgradeNoRefs` (647-716)                                                           | `test_engine.py:232-251`, plus the new no-refs flag-ordering test            |

**Retained in `test_deps.py` — genuinely CLI, and three of these are load-bearing:**

- `test_lockfile_mode_no_lockfile_configured` (`:304-337`). It is the **only** test in either port that runs `deps upgrade` against `App(lockfile=None)` — an `rg` for `lockfile=None` / `lockfile: null` across both test trees otherwise hits only `test_app.py`, `app.test.ts` and `config.test.ts`. It keeps its `class TestUpgradeLockfileMode` shell, and its assertion stands unchanged: **18 declined** the `checked_lockfile = "the stage actually ran"` alternative this proposal routed to it (see _Risks & alternatives_), so 18 changes no `deps upgrade` behaviour and does not invert this test. A _new_ engine-level counterpart is added in step 1 (`upgrade()` with `lockfile=None`, `mode="lockfile"` → `checked_lockfile is True`, `lockfile_stale == []`), but it does not subsume the CLI test: only the CLI test proves config loading + the full command survive a null lockfile.
- `test_upgrade_modifies_source_files` (`:363-380`) — **retained and tightened.** It is the only test in either port that runs the `output_format is None` branch of `deps.py:205`, i.e. the stdout half of the `0cae9b1` hotfix. Its current assertion at `:374` is `assert "Applied version bumps" in result.output`, and under click 8.3.2 `Result.output` is an interleaved mix of stdout and stderr (`Result.output`'s own docstring: "No longer a proxy for `self.stdout`. Now has its own independent stream that is mixing `<stdout>` and `<stderr>`"), so it never asserted the _stream_. Change `:374` to `result.stdout` so the hotfix's stdout half is actually pinned for the first time.
- `test_apply_with_json_format_keeps_stdout_parseable` (`:382-404`) — the stderr half of the same hotfix; already stream-precise (`:396` `result.stdout`, `:399` `result.stderr`). Unchanged.
- The three `deps check-synced` tests (`:52-109`).
- `TestUpgradeTokenHandling` (`:553-593`), covering `_github_client`'s flag > `$GITHUB_TOKEN` > `$GH_TOKEN` chain at `deps.py:38-53`.
- `test_invalid_mode` (`:599-606`), plus a new `--format` mirror.
- **New:** a ~14-line CLI test that a `report.warnings` entry is echoed to **stderr** with the `warning: ` prefix. `test_api_error_continues_with_warning` (`:609-644`) is the only test today that reaches the echo loop at `deps.py:199-200`, and it moves to `test_engine.py`; without this replacement the loop loses all coverage.

**Moved to `test_pin/test_render.py` — same assertions, no `CliRunner`:**

- `TestUpgradeJsonContract::test_serializers_match_golden_fixture` (730-768) and `::test_source_files_omitted_when_empty` (770-781), now asserted through the public `render_upgrade_report(..., output_format="json")` rather than the private `_bump_to_json` / `_stale_to_json`.
- `TestUpgradeMarkdownContract` (873-911) whole.
- `TestUpgradeNoUpdates` (426-495, 70 lines of `CliRunner`) → a 3-line assertion that an empty report renders `"Everything is up to date.\n"`.

**Replaced — 78 lines of `CliRunner` become ~12 lines of direct assertion:**

- `TestUpgradeJsonContract::test_mode_versions_omits_lockfile_stale_key` (783-800) and `::test_mode_lockfile_omits_version_bumps_key` (802-819) → construct a report with `checked_versions=True, checked_lockfile=False` (and the converse) and assert the key set.
- `TestUpgradeJsonContract::test_empty_report_emits_both_keys_regardless_of_mode` (821-862, 42 lines) → **inverted.** The new test asserts that an _empty_ report with `checked_versions=True, checked_lockfile=False` renders `{"version_bumps": []}` and nothing else. This is the wart's regression guard, and it is the one place the reader will learn that spec 0005 §2.2's open choice was resolved the other way.
- `TestUpgradeErrorHandling::test_api_error_continues_with_warning` (608-644) → `test_engine.py` (it asserts `report.warnings`, an engine fact, and a canned transport scripted to raise `ResolveError` on the tag list covers it in ~12 lines). **Write it against 16's shared double, not `test_engine.py`'s local `FakeTransport`** — 16 lands first and deletes the local one; construction is `FakeTransport(...)` imported from `tests/test_pin/transport_contract.py`, with responses built by `canned()` (or `canned_raw()` for a verbatim body) rather than the local `_json_response` / `_commit` / `_tags` helpers, whose bodies 16 rewires onto the same builder. The same applies to the new `lockfile=None` and no-refs flag tests added in step 1, and to their TypeScript mirrors, which import `FakeTransport` / `canned` / `cannedRaw` from `src/pin/transport-contract.ts`. Its CLI-side half is replaced by the new warning-echo test above.

**Result: 911 → ~330 lines.** The arithmetic, since an earlier draft of this proposal said `~250` and that was optimistic: the surviving blocks are the module header and fixtures (~40 after dropping the four renderer imports at `:12-17`, the `VersionBump` / `LockfileStaleEntry` import at `:19` and the `FIXTURES_DIR` binding at `:23`), the `deps check-synced` block (~61), the upgrade helper block (~78 — `_UPGRADE_LOCKFILE` at `:139-149` and `_mock_resolve_ref` at `:177-185` both become unused, and `_setup_upgrade_project`'s `with_lockfile` branch goes with them), the retained `lockfile=None` class (~40), the retained `TestUpgradeApply` pair (~47), `TestUpgradeTokenHandling` (~43), and the error-handling class with `test_invalid_mode` plus the two new tests (~33). Collapsing the three near-identical token tests into one parametrized test would take it to ~310; that is optional and not assumed above. `CliRunner`-driven `deps upgrade` lines go **542 → ~140**, not to ~85 — the retained `lockfile=None`, apply-routing, token and warning-echo tests are all `CliRunner`-driven by necessity.

**TypeScript:**

- New `src/pin/render.test.ts` (~180) absorbs `deps.test.ts:70-129` (JSON contract) and `:131-164` (markdown contract) — 95 lines that already call the renderers directly and merely need their import path changed — plus the new flag and text-format cases.
- `deps.test.ts` **261 → ~130**: keeps the `vi.mock` harness (1-68, with `emptyReport()` at 42-44 updated for the two new required fields) and the stderr hotfix test (218-246); deletes `:167-216` (mode key behaviour → renderer unit tests); **inverts** `:248-260`, the empty-report both-keys assertion; and **adds** the missing stdout-half mirror of `test_upgrade_modifies_source_files` — drive `depsUpgrade({ mode: "versions", token: "fake" })` with no `format`, and assert the progress note lands on `captureStdout()` and not on `captureStderr()`. TypeScript has never asserted that branch; parity (AGENTS.md) requires it once Python's is made stream-precise.
- `engine.test.ts` gains ~30 lines inside `describe("upgrade()")` (171-242): `checkedVersions` / `checkedLockfile` per mode, the no-refs ordering test, and the `lockfile: null` case.

**New shared golden:** `fixtures/expected/upgrade_text.txt`, asserted by both ports against the same `VersionBump` / `LockfileStaleEntry` data already used by `upgrade_report.json`:

```text
Version updates available:

  actions/checkout@v5  →  v6  [major]
    in .github/ghagen_workflows.py
  actions/setup-node@v3  →  v4  [major]

Stale lockfile entries:

  actions/setup-python@v6
    current SHA: ece7cb06caef...
    latest SHA:  aaaa1111bbbb...

```

This closes the parity gap identified above: `deps upgrade`'s default output currently has no cross-port oracle at all.

Suite counts shift (fewer, faster Python tests; more TypeScript tests), so the recorded baselines of pytest 562 / vitest 515 both move.

## Risks & alternatives

**Breaking change: JSON key presence.** `--format json --mode versions` stops emitting `lockfile_stale` when the report is empty, and `--mode lockfile` stops emitting `version_bumps`. Pre-1.0, and the repo's own consumer is immune (`check-deps/action.yml:67-68` uses `.get(…, [])`). It also makes the contract _more_ useful, not less: the key set now depends only on `--mode`, which the caller chose, instead of on data the caller cannot predict. Documented in both `cli.md` files.

**Open — Phase 3 decision:** this proposal reopens a decision already recorded in `docs/specs/0005-typed-engine-report-seam.md:118-121`, which reads verbatim:

> - Edge case to lock down: the "everything up to date" early return
>   (deps.py:196-206 / deps.ts:180-189) emits _both_ keys as `[]` regardless of
>   `mode`. Tests must assert this exactly (or the code is changed to honor `mode`
>   in the empty case too — pick one and pin it).

The spec offered two options and the implementation took "assert this exactly". The friction that warrants reopening it: the choice was made when the flag existed only as a local inside a Typer command, so honouring `mode` in the empty case meant duplicating the derivation a fifth time; with `checked_*` on the report it is a _deletion_ of the special-cased branch rather than an addition. The cost of reopening is a user-visible payload change plus five test inversions (`test_deps.py:821-862`, `deps.test.ts:248-260`, and the three key-set tests listed in _Test impact_), and it obsoletes the §2.2 invariant at `:115-116` as well as the carve-out. **The reversal is not decided here.** If it is declined, everything else in this proposal still lands — `render_upgrade_report` keeps the empty-report special case behind its own interface instead of in the command, which is strictly better than today even without the behaviour change, and 18's dependency on the module is unaffected.

**Alternative: fix the wart in place and skip the module.** Delete the empty early return (`deps.py:213-227`) and let the existing flags drive both cases. This is a five-line change and fixes the LIVE defect — but it leaves the derivation duplicated in four places, leaves the human-text renderer untestable, leaves `test_deps.py` at 911 lines, and leaves the seam that **18** needs unbuilt. Rejected as the whole answer; noted here as the fallback if 17 is descoped, because the fix is genuinely independent of the module move.

**Alternative: pass `mode` to the renderer instead of adding two report fields.** Rejected — it moves the duplication rather than removing it, and it puts a CLI flag value in a pure `pin/` function's signature. It is _not_ rejected for being less accurate: `mode` and `checked_*` carry identical information, and any claim otherwise is wrong.

**Alternative: define `checked_lockfile` as "the stage actually ran"** — i.e. `mode in ("lockfile", "all") and app.lockfile_path is not None`. This would make the field carry genuinely new information, close the LATENT "checked vs never checked" gap named in _Problem_, and let **18**'s `plan_update` take only a report. Rejected **for this proposal** — it is a second, independent user-visible change, and it belongs with 18's H7 where the `lockfile=None` behaviour is actually being decided — and then **routed to 18, which considered and declined it**, for three reasons: it collapses "not asked for" and "no lockfile configured" into a single bit; it makes `--mode lockfile` with `lockfile=None` emit `{}`, no keys at all; and it inverts `test_cli/test_deps.py:304-337`, which this proposal explicitly retains. The question is therefore **closed, not open**: `checked_lockfile` stays a pure function of `mode` on both sides of the seam, 18's `plan_update` consults `app.lockfile_path` directly, and no `deps upgrade` behaviour changes in 18.

**Alternative: keep the renderers in `cli/` but export them.** This is what TypeScript already does (`deps.ts:381-389`), and it is why `deps.test.ts` is 261 lines rather than 911. It would bring Python to parity cheaply. Rejected because it leaves the _dispatch_ — the part that contains the defect — inside a function that also does config discovery and client construction, and because it puts a module that `check-deps` consumes under `cli/`, where **18** cannot reach it without importing a Typer/commander module.

**Risk: `pin/render` starts as a one-caller module.** Stated plainly in _What sits behind the seam_: it fails the deletion test on leverage today. It is justified on locality and on the test surface (542 → ~140 CLI-driven lines in Python, plus the first direct coverage the human-text format has ever had), not on leverage. If **18** is descoped, **20**'s standing rule — delete caller-less pin surface — should be applied to the barrel _exports_ (`pin/__init__.py`, `pin/index.ts`, `src/index.ts`), keeping the module itself as a `cli/`-internal import. The module earns its keep either way; only its public visibility is contingent.

### Scope boundaries vs siblings

- **20 — delete caller-less pin/spec surface. Lands first.** Owns deletion of dead branches in `pin/engine.*`, including the per-repo tag cache (`engine.py:225-226`, `engine.ts:233-234`). This proposal re-proposes none of it; step 1 edits the report literal and the two stage guards only, both of which survive 20's pruning. Two facts from 20's revision that this proposal is written against: 20's `cli/_common.*` `try/finally` region is `:59-67` (the two lazy-import call sites are non-adjacent, at `:65` and `:67`), and `engine.ts:243-249` — including the non-`ResolveError` rethrow at `:248` — is **preserved verbatim** by 20, so the `warnings.push(…); continue` path this proposal's moved `test_api_error_continues_with_warning` exercises is still there.
- **19 — `main()` owns exit codes. Lands second, before this proposal.** The `deps.ts` conflict edge is **DROPPED**, confirmed from both sides: 19 has re-verified `trapExits` against the real `buildDepsCommand()` and the intersection with this proposal's declared hunks is **empty**, including `deps.ts:159-170` — which 19 does not need severed, and which this proposal no longer touches at all now that `MACHINE_FORMATS` is dropped. 19's own header now records that it is independent of 17.
  **The live edge is on `docs/src/content/docs/{python,typescript}/cli.md`, and it is four-way with 14 and 18.** 19 deletes `python/cli.md:114-120,136-142,179-185` and `typescript/cli.md:127-133,149-155,192-198`, consolidating them into one `## Exit codes` section anchored at **end-of-file** (both files currently end with `### Example` — `python:200`, `typescript:213` — plus a trailing paragraph, so the anchor is clean). This proposal inserts _within_ `## ghagen deps upgrade` (`python:157-185`, `typescript:170-198`), immediately after the Options table (`python:171-177`, `typescript:184-190`) — i.e. above `python:179` / `typescript:192`, exactly the lines 19 deletes. **Once 19 has landed, both insertions are safe**: the `### Exit codes` subsection is gone and the Options table is the last block in the section, so the new key-presence prose appends to the end of `## ghagen deps upgrade` with no ambiguity about ordering against 19's consolidated table.
- **14 — `versions` owns its comparison. Lands third, immediately before this proposal.** `14 → 17` is a real order edge _and_ a file conflict, in two places beyond `pin/engine.*`. (i) 14 rewrites `test_versions.py` wholesale; this proposal then adds `checked_versions` / `checked_lockfile` assertions around the same report, and cites `test_versions.py:45-46` / `:108-110` as the direct coverage that makes `TestUpgradeNonSemver` deletable — those citations must be re-resolved against 14's rewritten file at implementation time. (ii) 14 edits `test_deps.py`, which this proposal rewrites 911 → ~330. **14 goes first** in both cases; this proposal's cuts are then applied to 14's version of the file. 14 also edits both `cli.md` pages; it documents tag grammar and this documents JSON key presence — adjacent subsections, not the same lines. This proposal does not touch the comparison path, `parse_tag`, or `classify_bump`; it only adds two fields to `UpgradeReport` and deletes two locals.
- **18 — pull `check-deps`'s decision logic across the CLI seam. Downstream of this proposal.** 18 consumes `render_upgrade_report` / `renderUpgradeReport` plus the `checked_*` flags. Three things 18 needs stated plainly, because **H7 lands in this seam and that is why 17 is on the critical path**:
  1. **This proposal's interface is sufficient for both of 18's rules without re-deriving anything.** `apply_version_bumps` is `report.checked_versions and bool(report.version_bumps)`; `refresh_lockfile` is `app.lockfile_path is not None and report.checked_lockfile and (…)`. Any re-derivation from `mode` inside 18 is 18's defect, not a gap here. `plan_update` should take `report`, not `mode`.
  2. **This proposal does NOT remove the fact H7 needs.** `checked_lockfile` is True even when `app.lockfile_path is None` (see (a)), so `plan_update` still needs `app` — or an explicit `lockfile_path` parameter — to distinguish "no lockfile configured" from "checked, nothing stale". The alternative that would remove that need was routed to 18 and **18 declined it** — see _Risks & alternatives_ for 18's three reasons. `checked_lockfile` therefore stays a pure function of `mode` on both sides of the seam, and no `deps upgrade` behaviour changes in 18.
  3. **18's claim that "every existing `deps upgrade` test is unchanged" is wrong.** This proposal relocates `TestUpgradeJsonContract` (`test_deps.py:727`) and `TestUpgradeMarkdownContract` (`:873`) to `test_pin/test_render.py`, and **inverts** `test_empty_report_emits_both_keys_regardless_of_mode` (`:821-862`) along with `deps.test.ts:248-260`. Sequencing is otherwise clean: 18 appends `TestDepsUpdate` after `test_deps.py:911` and this proposal's last deletion ends at `:911`, so the append lands after, not inside, a deleted region. One thing 18 may need to reinstate: `_UPGRADE_LOCKFILE` (`:139-149`) is removed here as unused, correctly — all its call sites are in deleted classes — but 18's `deps update` tests will likely want it back.
     This proposal deliberately stops at the seam: it does not touch `check-deps/action.yml`, `.github/ghagen_workflows.py`, or the bash that counts `version_bumps` / `lockfile_stale`.
- **16 — lift transport policy into the `HttpClient` interface. Lands first (batch 1); this proposal is batch 3.** The dependency is on **16's test double, not on transport policy** — nothing in this proposal touches an adapter, a header, a timeout, or an exception type. It is purely that 16's migration step 5 deletes the four hand-written canned transports, two of which this proposal's engine tests are written against: `FakeTransport` at `test_engine.py:52-65` plus `_json_response` at `:68-69` (Python), and `jsonResponse`/`commit`/`tags`/`FakeTransport` at `engine.test.ts:54-84` (TypeScript). Verified against `main` at `e7a972c`: both regions are exactly as 16's Files-involved rows describe them.
  **Loudly, because it changes what "deleted" means here: `FakeTransport` survives 16 — by name and by role — it _moves_.** 16 relocates it to `packages/python/tests/test_pin/transport_contract.py` and `packages/typescript/src/pin/transport-contract.ts` as one shared double per port, in the union of the four local feature sets, with `canned()` / `canned_raw()` (`canned` / `cannedRaw`) as the response builders; `_commit` / `_tags` keep their bodies and call the shared builder. So the migration for this proposal is an import change plus a builder-call change, not a rewrite: no test this proposal adds or moves needs different _assertions_ because of 16. That is why 16 is a parallel predecessor rather than a link in the chain.
  Consequence for citations: every `test_engine.py` and `engine.test.ts` line number in this document is pre-16 and shifts once 16 lands (~16 lines up in Python, ~30 in TypeScript). They are stated pre-16 deliberately — they are the ones verifiable against `e7a972c` today.
- **16 — barrel contention.** Separately from the double, a real merge hazard on `packages/python/src/ghagen/pin/__init__.py`. It is _not_ a shared edit of one statement: `:15-21` is the `from ghagen.pin.github import (…)` block and only 16 edits it. The collision is line-shift across the isort region `:3-31` plus the shared alphabetical `__all__` at `:33-58` — this proposal inserts a new `ghagen.pin.render` import at `:29`, 14 adds `BumpSeverity` at `:32`, and 18 adds two names from a new `ghagen.pin.plan` at `:29`. **Hand-merge; not a reason to serialize.** The same hazard applies to the barrels: `packages/typescript/src/index.ts` has seven claimants (09, 11, 14, 16, 17, 18, 20) and `packages/typescript/src/pin/index.ts` has five (14, 16, 17, 18, 20). One correction back to 16, whose scope-boundary bullet reads "17 adds **three** names to all three barrels": this revision dropped `MACHINE_FORMATS`, so it adds **two** (`render_upgrade_report` + `UpgradeFormat`). 16's insertion offsets shift by two or three lines from this proposal, not three or four — and since 16 lands first, it is this proposal's offsets that move, not 16's.
- **11 — shared spec-surface table.** `docs/specs/0005-typed-engine-report-seam.md` becomes a shared file with three claimants: 11 is in flight on the spec surface generally, this proposal amends **§2.2** (`:85-122`) and **§2.3** (`:123-154`), and **18** amends §3 (`:186-370`), §4 (`:371-388`) and §5 (`:389-407`) — also amending, not rewriting. Disjoint sections in every pair; flagged so it is not a surprise. (Section spans re-derived here by `grep -n "^#\{1,3\} "` over the file; the round-2 verdicts circulated at least one wrong span for this document.)
- Not mine, noted for whoever owns it: both `cli.md` exit-code tables claim `1` for "Updates available (`--check`)" (`python:184`, `typescript:198`), but the reproduction above shows `--check` with pending bumps exits **0** in both ports. That is a doc/behaviour mismatch inside exactly the rows **19** consolidates; since 19 lands first, it should be fixed there.

## ADR / CONTEXT.md impact

- **No ADR is contradicted.** **ADR-0007** ("The CLI renders errors and owns exit codes; `CliError` is CLI-local… pure result types at the seam, presentation at the edge") is _reinforced_: `pin/render` is a pure `report → str` module that performs no I/O and raises nothing, and the CLI keeps sole ownership of stream selection and exit codes. Nothing moves into the engine — `pin/engine`'s docstring promise of no console I/O (`engine.py:8-10`, `engine.ts:9-10`) still holds, because the renderer writes nothing either.
- **ADR-0001** (Emitter owns serialization) is untouched — this is CLI report output, not Document emission. **ADR-0006** (collect returns parsed refs) is untouched.
- **`docs/specs/0005-typed-engine-report-seam.md`** needs two amendments, both contingent on the Open decision above being taken:
  - **§2.2, `:115-121`.** The invariant at `:115-116` ("`version_bumps` is present only when `mode ∈ {versions, all}`; `lockfile_stale` only when `mode ∈ {lockfile, all}` (deps.py:210-217 / deps.ts:196-201)") keeps its intent but loses its citation — those lines move to `pin/render` — and the carve-out at `:118-121` is replaced by the resolved rule: key presence follows `report.checked_versions` / `report.checked_lockfile` in **all** cases, empty included. Record that "pick one and pin it" was reopened and reversed once the renderer gained a seam. If the Open decision is declined, `:115-121` stands as written and only the citations need refreshing.
  - **§2.3, `:141-144`.** It names `tests/test_cli/test_deps.py` and `src/cli/deps.test.ts` as the homes of the serializer assertions. Both move to `tests/test_pin/test_render.py` / `src/pin/render.test.ts`; the shared-fixture mechanism and the `helper_provided` negative assertion at `:148-149` are unchanged. Separately, and **not this proposal's to answer**: `:127` names Python's `conftest.py → FIXTURES_DIR` against TypeScript's `loadFixture`, which is the asymmetry raised as an open `FIXTURES_DIR` question elsewhere in the round.
    Amending a spec is outside a proposal's remit; noted here for the implementation phase.
- **`packages/python/CONTEXT.md` and `packages/typescript/CONTEXT.md`.** Two edits, identical in both ports:
  1. A new **Upgrade report** entry in the **Pinning** glossary, placed immediately after **14**'s new **Bump** entry. Append order at that anchor is **16 → 14 → 17**: on the tree at `e7a972c` the glossary ends with **PinEntry** (`python:75-76`, `typescript:77-78`), 16 appends its **Transport** entry there, 14 appends **Version tag** / **Bump**, and this entry lands last.

     > **Upgrade report**:
     > The typed outcome of an upgrade run: the version bumps and stale lockfile entries found, the
     > files changed, the warnings collected, and **which stages were asked for** (`checked_versions` /
     > `checked_lockfile`). The renderer reads the last two to decide the JSON key set; nothing
     > re-derives them from the CLI's `--mode`. "Asked for" is not "ran" — with no lockfile configured
     > the stage is skipped and `checked_lockfile` is still true.

  2. A new **Surface notes** bullet naming the split: the **engine** decides and reports, `pin/render` turns a report into bytes, and the CLI chooses the stream and the exit code. Avoid "formatter" and "serializer" — "renderer" is already the word both ports use in their docstrings (`deps.py:281`, `deps.ts:234`). Note that this is a **new** bullet, not an extension of an existing one: neither `## Surface notes` list has a pin-engine bullet today (`python:96-107`, `typescript:98-112`). Three proposals append a bullet at that anchor (`python:107` / `typescript:112`) in the order **16 → 17 → 10**.

- **Region assignment — resolved.** An earlier draft flagged that this proposal had no assigned region and that its natural glossary anchor (`ts:79` / `py:77`) was the one the map gave **16**. The round has since assigned it: the **Upgrade report** entry goes after 14's **Bump** entry, append order **16 → 14 → 17**, and the Surface-notes bullet appends in the order **16 → 17 → 10**. Both are pure appends of independent blocks, so the merges are mechanical and no serialization is implied beyond the stated order. Non-overlap across the map's claimants holds.
