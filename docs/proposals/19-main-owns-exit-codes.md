# 19 — `main()` owns exit codes end to end

**Status:** proposed | **Ports:** both | **Effort:** L | **Depends on:** nothing; independent of **17** (see _Risks & alternatives_ — the `deps.ts` conflict edge is **dropped**)

Effort is **L**, not M: the Python half is not "add a `main()`" but a `standalone_mode=False` migration
that must reproduce Typer's own error rendering byte-for-byte (measured below — the obvious sketch
destroys it), and the change touches nine existing files including both `CONTEXT.md`s, one ADR, and
two restructured docs pages.

## Files involved

### Modified

| Path                                                      | Lines | Role in this proposal                                                                                                                                                                             |
| --------------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/typescript/src/cli/main.ts`                     | 145   | `main()` traps commander (recursive `exitOverride`), maps `CommanderError` → `0`/`2`, and stops calling `process.exit` in the bin shim                                                            |
| `packages/typescript/src/cli/_errors.ts`                  | 21    | Doc fix: the class docstring (lines 6-7) says `exitCode` is "forwarded to `process.exit()`". That is **true today** and becomes **false at step 2**, when the shim switches to `process.exitCode` |
| `packages/python/src/ghagen/cli/main.py`                  | 103   | New `main(argv=None) -> int` around the Typer app (`standalone_mode=False`, reproducing Typer's rich renderer); `init` template gains `timeout_minutes=10`                                        |
| `pyproject.toml`                                          | 69    | Console script (line 29) `ghagen = "ghagen.cli.main:app"` → `"ghagen.cli.main:main"`                                                                                                              |
| `docs/src/content/docs/python/cli.md`                     | 210   | Delete `:114-120`, `:136-142`, `:179-185`; append one `## Exit codes` section **at end-of-file**; reword the prose at `:57` and `:123`                                                            |
| `docs/src/content/docs/typescript/cli.md`                 | 223   | Mirror: delete `:127-133`, `:149-155`, `:192-198`; append at end-of-file; reword `:70` and `:136`                                                                                                 |
| `packages/python/CONTEXT.md`                              | 114   | Extend the ADR-0007 Surface-notes bullet (`:102-104`); add one `### CLI` glossary term at `:85`                                                                                                   |
| `packages/typescript/CONTEXT.md`                          | 119   | Mirror: ADR-0007 bullet (`:106-109`); glossary term at `:87`                                                                                                                                      |
| `docs/adr/0007-config-discovery-returns-typed-results.md` | 24    | One appended **Consequences** bullet (the section is `:20-24`). The decision itself is not reopened                                                                                               |

### New

| Path                                                   | Lines      | Role in this proposal                                                                 |
| ------------------------------------------------------ | ---------- | ------------------------------------------------------------------------------------- |
| `fixtures/cli-exit-codes.yml`                          | new (~60)  | The shared `(id, argv, exit)` table — the proposed interface, as data                 |
| `fixtures/expected/init_scaffold.yml`                  | new (16)   | Byte oracle for what `ghagen init` scaffolds, emitted with no header                  |
| `packages/python/tests/test_cli/test_exit_codes.py`    | new (~110) | Drives every table row through `main()`, **plus** the stderr-rendering fidelity cases |
| `packages/typescript/src/cli/exit-codes.test.ts`       | new (~70)  | Mirror (commander's rendering is untouched by this change, so no fidelity cases)      |
| `packages/python/tests/test_cli/test_init_scaffold.py` | new (~50)  | Scaffolds, loads the written template, compares emission to the fixture               |
| `packages/typescript/src/cli/init-scaffold.test.ts`    | new (~55)  | Mirror, via `jiti`                                                                    |

Deliberately **not** in the table, each verified unnecessary rather than assumed:

- `packages/typescript/src/cli/deps.ts` (389) and `packages/python/src/ghagen/cli/deps.py` (360) — the
  recursive `exitOverride` walk reaches the `addCommand`-mounted `deps` subtree from `main.ts` alone
  (probed below against the **real** `buildDepsCommand()`). Their hand-rolled `Exit(2)` / `CliError(…, 2)`
  paths already produce the proposed codes. **This drops the `17 — 19` conflict edge.**
- `packages/typescript/src/cli/main.test.ts` (153), `packages/python/tests/test_cli/test_main.py` (303),
  `packages/python/tests/test_cli/test_deps.py` (911) — every existing exit-code assertion is `0`, `1`, or
  `2`, and every one of them keeps its value under the proposed table (`test_main.py:32,162,169,225,237,248`;
  `test_deps.py:83,107,605`). No existing test changes.
- `.github/ghagen_workflows.py`, `.github/workflows/ci.yml`, `scripts/*` — both new suites run under
  the existing `scripts/test.sh` (`pytest` / `vitest`). No new gate. See the **23** boundary below.
- `packages/typescript/src/paths.ts`, `scripts/ghagen_schema/paths.py` — these two disagree
  (`FIXTURES_DIR` is `<root>/fixtures` in Python at `paths.py:35`, `<root>/fixtures/expected` in TS at
  `paths.ts:41`). The TS driver therefore uses the _other_ export from the same module,
  `resolve(REPO_ROOT, "fixtures", "cli-exit-codes.yml")` (`paths.ts:35`) — not a `".."` hop off
  `FIXTURES_DIR`. **14** already declared that asymmetry out of scope; 19 routes around it identically
  rather than racing 14 for the file.

## Problem

Two defects, one theme: a documented interface neither port actually holds.

### 1. `main()` documents a return value it can never produce — **LIVE**, both ports

`packages/typescript/src/cli/main.ts:124` says:

```ts
/** Run the CLI. Returns the exit code. */
export async function main(argv: readonly string[]): Promise<number> {
  const program = buildCli();
  try {
    await program.parseAsync(argv as string[], { from: "user" });   // ← process.exit() fires in here
    return 0;
  } catch (err) { …
```

Neither port calls its framework's exit trapdoor. Grepped repo-wide across `packages/`, `scripts/`,
`docs/`, `fixtures/`, `schema/`, `check-deps/`, `check-synth/`, `.github/`: **zero first-party
occurrences** of `exitOverride`. The only hits in the tree are inside vendored copies of commander
itself (`packages/typescript/node_modules/commander/lib/command.js:492`) — i.e. the trapdoor exists
and is unused.

**Why it escapes is not "nobody called `exitOverride`" — it is _where the callback lives_.**
Commander's `_exit` (`command.js:517-521`) reads `this._exitCallback`:

```js
_exit(exitCode, code, message) {
  if (this._exitCallback) { … }
  process.exit(exitCode);          // ← reached whenever THIS command has no callback
}
```

`_exitCallback` is **per-`Command`, and never looked up through the parent chain.** A subcommand gets
one only by copying it from its parent, and only at **creation** time:

- `.command()` ends with `cmd.copyInheritedSettings(this)` (`command.js:170`), which copies
  `_exitCallback` at `command.js:98`.
- `.addCommand()` (`command.js:279-294`) does **not** call `copyInheritedSettings` at all.

`buildCli()` (`main.ts:96-122`) constructs the _entire_ tree — `synth`, `check-synced`, `init` via
`.command()`, and the whole `deps` subtree via `program.addCommand(buildDepsCommand())` at
`main.ts:120` — and only then hands the object back to `main()`. So an `exitOverride()` applied to the
root _after_ construction propagates to **nothing**: the `.command()` children copied the callback
before it existed, and the `addCommand` child never copies it. Post-construction, a root-only
override is inherited by neither kind of subcommand.

Probed against the **real** `buildDepsCommand()` imported from `dist/`, with `buildCli()`'s exact
shape and `process.exit` instrumented (zero lines of `deps.ts` opened):

```
# program.exitOverride() only, applied after buildCli() returns:
["bogus"]                         -> THREW code=commander.unknownCommand      exitCode=1
[]                                -> THREW code=commander.help                exitCode=1
["--help"]                        -> THREW code=commander.helpDisplayed       exitCode=0
["--version"]                     -> THREW code=commander.unknownOption       exitCode=1
["synth","--bogus"]               -> ESCAPED via process.exit(1)   ← .command() child
["init","--outdir"]               -> ESCAPED via process.exit(1)   ← .command() child
["deps"]                          -> ESCAPED via process.exit(1)   ← addCommand child
["deps","upgrade","--bogus"]      -> ESCAPED via process.exit(1)
["deps","pin","--bogus"]          -> ESCAPED via process.exit(1)
["deps","check-synced","--bogus"] -> ESCAPED via process.exit(1)
["deps","upgrade","--mode"]       -> ESCAPED via process.exit(1)
["deps","bogussub"]               -> ESCAPED via process.exit(1)
```

Only the four cases commander resolves _at the root itself_ are trapped; every case that reaches a
subcommand kills the process. `main()` does not return for those; it is a `Promise<number>` that, for
most of the usage-error class, never settles. The `Returns the exit code` docstring is false.

(`_errors.ts:6-7`'s claim that `exitCode` is "forwarded to `process.exit()`" is, by contrast, **true
today** — `main.ts:144` really does hand the returned code to `process.exit()`. It becomes false only
once step 2 switches the shim to `process.exitCode`, which is why it is a doc fix _in this proposal_
and not a pre-existing error.)

**Python is not innocent, it is worse.** `pyproject.toml:29` binds the console script to
`ghagen = "ghagen.cli.main:app"` — the `typer.Typer` object itself (`main.py:12-16`). There is no
Python `main()` at all; `rg "def main"` over `packages/python/src` returns nothing. Click's standalone
mode owns the code end to end. Under `standalone_mode=False` the framework hands the decision back
(click 8.3.2 / typer 0.24.1), and `typer/core.py:185-235` is explicit about it:

```
[probe] ["bogus-command"]   -> ClickException(UsageError)        exit_code=2
[probe] ["synth","--bogus"] -> ClickException(NoSuchOption)      exit_code=2
[probe] ["init","--outdir"] -> ClickException(BadOptionUsage)    exit_code=2
[probe] []                  -> ClickException(NoArgsIsHelpError) exit_code=2
[probe] ["--help"]          -> RETURNED 0
[probe] ["synth"]           -> RETURNED 1   (a typer.Exit(1) from _find_config, returned not raised)
```

So **both** ports leak their framework's exit-code policy, and the two frameworks disagree. This is
not "commander is badly behaved"; it is that nothing in ghagen ever claimed the decision.

### 2. The consequence: the same usage error is 2 under Typer and 1 under commander — **LIVE**

Every row below was run. Python via `uv run ghagen …`; TypeScript via `node packages/typescript/dist/cli/main.js …`
(`package.json` `bin` → `./dist/cli/main.js`, built with `npm run build --prefix packages/typescript`).

**The stream column was measured out of process**, with `1>` and `2>` redirected to separate files —
**not** through `click.testing.Result.output`, which cannot answer a routing question at all (see
below). Any implementer re-deriving the column must do the same.

| #   | Failure class                   | Invocation                    | Python  | TypeScript | Help/error stream |
| --- | ------------------------------- | ----------------------------- | ------- | ---------- | ----------------- |
| 1   | success                         | `synth` (valid config)        | `0`     | `0`        | —                 |
| 2   | explicit help                   | `--help`                      | `0`     | `0`        | stdout / stdout   |
| 3   | **no arguments**                | `ghagen`                      | **`2`** | **`1`**    | stdout / stderr   |
| 4   | **sub-app, no subcommand**      | `deps`                        | **`2`** | **`1`**    | stdout / stderr   |
| 5   | **unknown command**             | `bogus-command`               | **`2`** | **`1`**    | stderr / stderr   |
| 6   | **unknown option**              | `synth --bogus`               | **`2`** | **`1`**    | stderr / stderr   |
| 7   | **unknown top-level option**    | `--version`                   | **`2`** | **`1`**    | stderr / stderr   |
| 8   | **missing option argument**     | `init --outdir`               | **`2`** | **`1`**    | stderr / stderr   |
| 9   | bad enum value (hand-validated) | `deps upgrade --format bogus` | `2`     | `2`        | stderr / stderr   |
| 10  | config not found (discovery)    | `synth`, empty dir            | `1`     | `1`        | stderr / stderr   |
| 11  | config not found (`--config`)   | `synth --config /nonexistent` | `1`     | `1`        | stderr / stderr   |
| 12  | user config raises              | `synth`, config raises        | `1`     | `1`        | stderr / stderr   |
| 13  | generated YAML stale            | `check-synced`                | `1`     | `1`        | stderr / stderr   |
| 14  | lockfile stale / absent         | `deps check-synced`           | `1`     | `1`        | stderr / stderr   |
| 15  | updates available               | `deps upgrade --check`        | `0`     | `0`        | —                 |

Rows 3-8 diverge. Note where they _don't_: row 9 is the one usage error both ports validate
themselves, in application code, and both chose **2** — `deps.py:171,180` and `deps.ts:156,166-169`.
The ports already agree on the policy; they just never applied it to the framework's own errors.

`--version` (row 7) is implemented by neither port. Out of scope here; the table just records that
it lands in the usage-error class.

**Why nobody noticed the stream half of this: the Python CLI test surface cannot see it.** In click
8.3.2 `click.testing.Result.output` is not stdout — its own docstring (`click/testing.py`, `Result.output`)
says _"No longer a proxy for `self.stdout`. Now has its own independent stream that is mixing
`<stdout>` and `<stderr>`, in the order they were written."_ (changed in 8.2, when `mix_stderr` was
removed and `output_bytes` introduced). The repo proves it: `test_deps.py:604-606` asserts
`"unknown --mode value" in result.output` for a message written with `err=True` (`deps.py:167-170`),
and passes **only because `output` includes stderr**. Across `packages/python/tests/test_cli/`, 78
assertions read `.output` and **4** read `result.stdout`/`result.stderr`. So the port has ~78
assertions that are structurally incapable of detecting a stream regression, and 4 that can. That is
the same shape as the exit-code defect and the same argument for locality: when nothing can observe
the contract, the contract drifts. This proposal does not fix those 78 — they are content
assertions and correct as content assertions — but it does not add a 79th.

### 3. `deps upgrade --check` exits `0` while both docs say `1` — **LIVE, and the docs are the wrong side**

`docs/src/content/docs/python/cli.md:184` and `typescript/cli.md:197` both say:

> `| 1 | Updates available (--check) or one or more updates failed to apply |`

Observed independently in **both** ports, each with a real upgrade pending — not inferred from one
port and mirrored:

```
$ uv run ghagen deps upgrade --check --format json          # python, this repo
py exit=0    # JSON lists actions/checkout@v6 -> v7.0.1 [major], actions/setup-node@v6 -> v7 [major]

$ node …/dist/cli/main.js deps upgrade --check --mode versions --format json   # typescript, temp project
ts exit=0    # JSON lists actions/checkout@v4 -> v7.0.1 [major]
```

`depsUpgrade` has no throw on that path either (`deps.ts:195-232` contains a bare `return` at `:209`
and no `CliError`). **The docs are wrong, not the code**, and the evidence is stronger than "a `1`
would be inconvenient":

- `check-deps/action.yml:116` runs `deps upgrade --check --format pr-body … > "$BODY_FILE"` and
  `:181` runs `--format issue-body … > "$BODY_FILE"`. Both are under `set -euo pipefail` (`:91`,
  `:158`), with no `|| true`. Both are `>` redirects, not pipes, so `pipefail` is irrelevant — plain
  `set -e` is enough to abort.
- Crucially, **both steps are gated on `total_updates != '0'`** (`:89` and `:156`). They run _only_
  in the case the docs claim exits `1`. A documented `1` would abort the action on **100% of the runs
  that reach those lines** — the action would never have shipped a single PR or issue.

The documented `1` therefore cannot ever have been true. It is deleted, not edited.

The `|| true` at `check-deps/action.yml:65` is a vestige of the same confusion; it belongs to **18**
and 19 does not touch `check-deps/action.yml`.

### 4. Blast radius: nothing anywhere distinguishes `2` from `1` — this is what makes the change safe

The change moves TypeScript's usage errors from `1` to `2`. Every first-party `ghagen` invocation was
audited for exit-code sensitivity. There are **nine**, and not one of them can observe the difference:

| Site                           | Invocation                                                    | How the code is consumed                                |
| ------------------------------ | ------------------------------------------------------------- | ------------------------------------------------------- |
| `check-synth/action.yml:40`    | `ghagen check-synced --config …`                              | bare step, composite `shell: bash` — zero/non-zero only |
| `check-deps/action.yml:65`     | `deps upgrade --check --format json > "$JSON_FILE" \|\| true` | suppressed entirely                                     |
| `check-deps/action.yml:116`    | `deps upgrade --check --format pr-body > "$BODY_FILE"`        | `set -euo pipefail`, redirect                           |
| `check-deps/action.yml:124`    | `deps upgrade --mode versions --config …`                     | `set -euo pipefail`                                     |
| `check-deps/action.yml:129`    | `deps pin --config … --update`                                | `set -euo pipefail`                                     |
| `check-deps/action.yml:181`    | `deps upgrade --check --format issue-body > "$BODY_FILE"`     | `set -euo pipefail`, redirect                           |
| `.github/workflows/ci.yml:70`  | `uv run ghagen deps check-synced`                             | bare `run:` step                                        |
| `.github/workflows/ci.yml:157` | `uv run ghagen check-synced`                                  | bare `run:` step                                        |
| `scripts/lint.sh:38`           | `uv run ghagen deps check-synced`                             | `set -euo pipefail` (`lint.sh:2`)                       |

No `$?` capture, no `case $?`, no `if ghagen …; then`, no `continue-on-error:` anywhere. Every site is
a pure zero/non-zero `set -e` test plus the one `|| true`. All three `> "$FILE"` sites are redirects,
not pipes.

And the move is not even _reachable_ from this repo's CI: **both composite actions install the Python
port** — `check-deps/action.yml:54,:56` and `check-synth/action.yml:34,:36` are `pip install ghagen`.
Python's codes do not move. The only consumer who can see the `1` → `2` change is a user who scripts
the npm-installed CLI and branches on a specific non-zero value, which is precisely the caller the
new contract exists to serve.

### 5. The two `init` templates scaffold different workflows — **LIVE**, no test

`packages/python/src/ghagen/cli/main.py:73-100` writes a template whose job is:

```python
"test": Job(
    runs_on="ubuntu-latest",
    steps=[…],
),
```

`packages/typescript/src/cli/main.ts:11-46` writes one whose job is:

```ts
test: job({
  runsOn: "ubuntu-latest",
  timeoutMinutes: 10,          // main.ts:36
  steps: […],
}),
```

Scaffolded and emitted both, in temp directories. One key of divergence — `timeout-minutes: 10` —
and no test in either port covers it: the shared byte oracle in `fixtures/expected/` is driven by
`packages/python/tests/test_integration/test_snapshots.py` (451) and
`packages/typescript/src/integration/snapshots.test.ts` (293), and neither has an `init` entry.
`test_main.py:12` (`test_init`) asserts only that the file was created.

The Python side is the outlier, not the TypeScript side: this repo's own dogfooded workflows set a
timeout on **every** job — 17 `timeout_minutes=` sites in `.github/ghagen_workflows.py`
(`:41,53,70,101,112,123,142,153,164,195,266,306,324,355,432,500,534`; the values are `5`, `10` or
`15`). A scaffold that omits it teaches the opposite of what the project practises.

### 6. The bin shim exits before stdout can drain — **LATENT**

`main.ts:144`:

```ts
main(process.argv.slice(2)).then((code) => process.exit(code));
```

`process.exit()` does not wait for pending async writes. Node's stdout is synchronous to a file but
asynchronous to a pipe on POSIX, so `ghagen deps upgrade --check --format json | jq` can truncate
where `> file` does not. Latent because it needs a large piped payload to manifest; it is squarely
in scope, because "`main()` owns the exit code" is exactly the claim that makes the fix one line.

## Current interface

To invoke ghagen and branch on the result today, a caller must know:

- **TypeScript:** `main(argv): Promise<number>` — except for rows 3-8, where it never returns and the
  process is killed from inside `parseAsync` with commander's code, which is `1` for every usage
  error regardless of kind.
- **Python:** there is no callable interface. The console script _is_ `typer.Typer.__call__`, so the
  code is whatever click's standalone mode decides (`2` for `UsageError`, the `typer.Exit` argument
  otherwise, `1` for an uncaught exception via the default traceback path).
- **Both:** an application-chosen `2` for `--format`/`--mode` (`deps.py:165-180`, `deps.ts:155-170`),
  which happens to match Python's framework and not TypeScript's.
- **The docs:** three per-command tables in each CLI page listing only `0` and `1`, one row of which
  (`deps upgrade --check`) contradicts both implementations.

Four authorities, no agreement. ADR-0007 already legislates the correct one —
`docs/adr/0007-config-discovery-returns-typed-results.md:9-10`: _"The CLI renders errors and **owns
exit codes**; `CliError` is CLI-local."_ The config module was made to return errors as values
precisely so the CLI could own this. It doesn't.

**The exit code is also restated in prose in nine other places.** They are enumerated here because
the proposal's "one authority" claim is a claim about _code_, not about prose, and the difference has
to be checkable rather than trusted:

| Site                    | Text                                                                 | Status after this change                   |
| ----------------------- | -------------------------------------------------------------------- | ------------------------------------------ |
| `python/cli.md:57`      | `check-synced` "Exits with code 0 … or code 1 if any file is stale." | true; reworded to point at `## Exit codes` |
| `python/cli.md:123`     | `deps check-synced` "Exits with code 1 if the lockfile is stale."    | true; reworded                             |
| `typescript/cli.md:70`  | mirror of `:57`                                                      | true; reworded                             |
| `typescript/cli.md:136` | mirror of `:123`                                                     | true; reworded                             |
| `deps.py:31`            | `_ensure_lockfile_path` docstring "…or exit 1 if disabled."          | true, unchanged                            |
| `deps.py:113`           | `deps check-synced` docstring — **user-visible help text**           | true, unchanged                            |
| `deps.ts:107`           | `depsCheckSynced` JSDoc "Exits with code 1 if…"                      | true, unchanged                            |
| `deps.ts:359`           | `.description("… (exit 1 if stale).")` — **user-visible help text**  | true, unchanged                            |
| `main.ts:63`            | `cmdCheckSynced` JSDoc "(exit 1 if stale)"                           | true, unchanged                            |

All nine describe expected-failure paths and all nine stay `1` under the proposed table, so none of
them is a defect. The only prose that is _false_ is the pair of `deps upgrade --check` rows in §3,
and those are deleted.

## Proposed interface

**One table, three codes, both ports, bound by a test.**

| Code | Meaning                                                                                                                                                                                            |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `0`  | The command did what it was asked. Includes "no upgrades available" **and** "upgrades available" under `--check` — a report is not a failure.                                                      |
| `1`  | Expected failure: generated files stale, lockfile stale, refs unresolved, config not found, user config raised.                                                                                    |
| `2`  | Usage error: unknown command, unknown option, missing option argument, invalid option value, no arguments. Framework-detected and hand-validated usage errors are indistinguishable to the caller. |

Rows 3-8 of the observed table become `2` in both ports — **TypeScript moves, Python does not.**
Row 15 stays `0` in both and the docs are corrected to match. Rows 1-2, 9-14 are already correct and
become binding.

The table is not prose. It is `fixtures/cli-exit-codes.yml`, alongside `fixtures/expected/`:

```yaml
# The one exit-code contract. Both ports drive this through main().
# Rows are project-independent: none of them loads a user config module.
- id: help
  argv: ["--help"]
  exit: 0
- id: no-args
  argv: []
  exit: 2
- id: subapp-no-subcommand
  argv: ["deps"]
  exit: 2
- id: unknown-command
  argv: ["bogus-command"]
  exit: 2
- id: unknown-option
  argv: ["synth", "--bogus"]
  exit: 2
- id: missing-option-argument
  argv: ["init", "--outdir"]
  exit: 2
- id: bad-format-value
  argv: ["deps", "upgrade", "--format", "bogus"]
  exit: 2
- id: bad-mode-value
  argv: ["deps", "upgrade", "--mode", "bogus"]
  exit: 2
- id: config-not-found-discovery
  argv: ["synth"]
  exit: 1
- id: config-not-found-flag
  argv: ["synth", "--config", "does-not-exist.py"]
  exit: 1
```

Every row is deliberately config-independent — `deps upgrade`'s enum validation runs _before_
`_find_config` / `findConfig` (`deps.py:165-180` precedes `:184`; `deps.ts:155-170` precedes `:173`),
and the two `config-not-found` rows resolve before any module load — so the driver needs only a
`chdir` into an empty temp directory. The config-dependent codes (rows 12-15) stay where they are
already asserted, in `test_main.py` / `test_deps.py` / `main.test.ts`.

### TypeScript `main()` takes the decision back

Because the callback is copied at creation and never inherited at parse time (§1), the trap must be
applied to every node of the already-built tree — a post-construction walk, not a root call:

```ts
/** Give every command in the tree back to `main()` instead of `process.exit`. */
function trapExits(cmd: Command): void {
  cmd.exitOverride();
  for (const sub of cmd.commands) trapExits(sub);
}

export async function main(argv: readonly string[]): Promise<number> {
  const program = buildCli();
  trapExits(program);
  try {
    await program.parseAsync(argv as string[], { from: "user" });
    return 0;
  } catch (err) {
    if (err instanceof CommanderError) {
      // commander has already written help/error text; only the code is ours.
      return err.exitCode === 0 ? 0 : EXIT_USAGE;
    }
    if (err instanceof CliError) { … return err.exitCode; }
    process.stderr.write(`Error: ${(err as Error).message}\n`);
    return 1;
  }
}
```

Same probe, same real `buildDepsCommand()`, with `trapExits` applied instead of the root-only call:

```
["bogus"]                         -> THREW code=commander.unknownCommand       exitCode=1
["synth","--bogus"]               -> THREW code=commander.unknownOption        exitCode=1
["init","--outdir"]               -> THREW code=commander.optionMissingArgument exitCode=1
["deps"]                          -> THREW code=commander.help                 exitCode=1
[]                                -> THREW code=commander.help                 exitCode=1
["--help"]                        -> THREW code=commander.helpDisplayed        exitCode=0
["--version"]                     -> THREW code=commander.unknownOption        exitCode=1
["deps","upgrade","--bogus"]      -> THREW code=commander.unknownOption        exitCode=1
["deps","pin","--bogus"]          -> THREW code=commander.unknownOption        exitCode=1
["deps","check-synced","--bogus"] -> THREW code=commander.unknownOption        exitCode=1
["deps","upgrade","--mode"]       -> THREW code=commander.optionMissingArgument exitCode=1
["deps","bogussub"]               -> THREW code=commander.unknownCommand       exitCode=1
```

Twelve for twelve, from `main.ts` alone, `deps.ts` untouched — including the four cases the root-only
override lost.

**`exitCode` is the discriminator, not `code`.** `commander.helpDisplayed` (`--help`, `synth --help`)
always carries `0`. `commander.help` carries **`0`** for the explicit `help` command
(`ghagen help`, `ghagen help synth`, `ghagen deps help` — all probed) and **`1`** for the no-args
path (`[]`, `["deps"]`) and for `help bogus`. Keying the branch on `err.exitCode === 0` is therefore
correct for all of them; keying it on `err.code` would not be. `CommanderError` must be tested
before `CliError`; both extend `Error`. `CommanderError` is a named export of `commander`
(`typings/index.d.ts:16`), so this adds one import to `main.ts`.

And the shim stops exiting:

```ts
main(process.argv.slice(2)).then((code) => {
  process.exitCode = code;
});
```

### Python grows the `main()` it never had — without losing Typer's error rendering

This is the delicate half, and the obvious version of it is wrong. Under `standalone_mode=False`
click stops rendering `ClickException`s, so `main()` must render them — but **`exc.show()` is not
what Typer does.** Typer overrides exactly this step (`typer/core.py:204-215`):

```python
except click.ClickException as e:
    if not standalone_mode:
        raise
    # Typer override
    if HAS_RICH and rich_markup_mode is not None:
        from . import rich_utils
        rich_utils.rich_format_error(e)      # typer/core.py:211
    else:
        e.show()                             # typer/core.py:213
    # Typer override end
    sys.exit(e.exit_code)
```

Measured, on this repo, with `prog_name="ghagen"` and stderr redirected to a file (stderr bytes):

| argv            | today                     | `exc.show()`       | `rich_format_error` |
| --------------- | ------------------------- | ------------------ | ------------------- |
| `bogus-command` | 625                       | **113**            | 625                 |
| `synth --bogus` | 619                       | **98**             | 619                 |
| `init --outdir` | 553                       | **47**             | 553                 |
| `--version`     | 625                       | **106**            | 625                 |
| `[]` (no args)  | 0 (help → stdout, 2011 B) | **1** (stray `\n`) | 0                   |
| `deps`          | 0 (help → stdout, 1671 B) | **1** (stray `\n`) | 0                   |

`exc.show()` silently downgrades every user from this:

```
Usage: ghagen synth [OPTIONS]
Try 'ghagen synth --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such option: --bogus                                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

to this:

```
Usage: ghagen synth [OPTIONS]
Try 'ghagen synth --help' for help.

Error: No such option: --bogus
```

`rich_utils.rich_format_error(exc)` is byte-identical to today on **all six** cases, on both streams.
The proposed `main()` mirrors Typer's branch rather than calling `rich_format_error` unconditionally,
because the unconditional form is byte-identical only while `TYPER_USE_RICH` is unset: re-running the
whole matrix under `TYPER_USE_RICH=0` (the env var read at `typer/core.py:29`) makes the
unconditional form differ on all six, while the mirrored branch stays byte-identical there too —
**12/12 across both settings.**

```python
def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI. Returns the exit code."""
    command = typer.main.get_command(app)
    try:
        return (
            command.main(
                args=None if argv is None else list(argv),
                prog_name="ghagen",
                standalone_mode=False,
            )
            or 0
        )
    except click.ClickException as exc:       # UsageError, NoSuchOption, NoArgsIsHelpError, …
        # Reproduce Typer's own standalone-mode rendering (typer/core.py:208-213).
        if typer.core.HAS_RICH and command.rich_markup_mode is not None:
            rich_utils.rich_format_error(exc)
        else:
            exc.show()
        return exc.exit_code
    except click.Abort:
        typer.echo("Aborted.", err=True)
        return 1
```

`rich_utils` needs an explicit `from typer import rich_utils` — it is not reachable as a `typer`
attribute from a plain `import typer`.

**There is no `except click.exceptions.Exit` branch, because it would be dead code.** Under
`standalone_mode=False`, `command.main()` _returns_ the exit code instead of raising:
`typer/core.py:223-235` catches `click.exceptions.Exit` and, when not in standalone mode,
`return e.exit_code` (`:235`). The one path that bypasses that `try` — shell completion at
`typer/core.py:183` — ends in a bare `sys.exit(rv)` (`click.core.Command._main_shell_completion`),
raising `SystemExit`, which this handler would not have caught either. So the branch can never fire
on any path.

`pyproject.toml:29` becomes `ghagen = "ghagen.cli.main:main"`; the generated console script wraps it
in `sys.exit(...)`, so the argv-less default is what the entry point uses. The `app` object stays
exported — `typer.testing.CliRunner` in `test_main.py` and `test_deps.py` keeps working unchanged.
An uncaught exception from a user's config still propagates out of `main()` with its traceback
(row 12 stays `1`); a crash should not be laundered into a tidy message.

Python's codes do not move, so `no_args_is_help=True` stays (`main.py:15`, `deps.py:26`): click's
`NoArgsIsHelpError` is a `UsageError` with `exit_code=2`, which is already the proposed value. (Its
help text reaches stdout from inside `command.main`, not from the handler — `rich_format_error`
deliberately early-returns for `NoArgsIsHelpError` — which is why both no-args rows show 0 stderr
bytes above.)

### Streams are recorded, not legislated

Rows 3-4 print help to stdout under click and stderr under commander. That is each framework's
rendering of its own help text; no CI consumer and no first-party action parses it, and forcing
either framework off its default costs more than the divergence does. The table's `exit` column is
the interface; the stream column is documentation.

This is a deliberate scope line, not an oversight, and §2's `Result.output` finding sharpens it: a
stream contract would need a test surface that can _see_ streams, and the Python port's 78 existing
`.output` assertions cannot. Legislating routing here would mean rewriting them — a much larger,
much less well-evidenced change than the one this proposal makes. Recorded as available work for a
later round; the four fidelity cases are the only place 19 asserts a stream, and they do it because
the _rendering_ regression they guard is invisible otherwise.

### The `init` scaffold gets a byte oracle

`fixtures/expected/init_scaffold.yml` — 16 lines, the same header-free shape as `ci_basic.yml` (15):

```yaml
name: CI
on:
  pull_request:
    branches:
      - main
  push:
    branches:
      - main
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: echo 'Add your test command here'
    timeout-minutes: 10
```

The TypeScript template wins; `main.py:73-100` gains `timeout_minutes=10`. Verified by emitting from
**both** ports independently — the real scaffolded Python file with `timeout_minutes=10` added, and
the TypeScript template's object graph through `toYaml(…, { header: null })` — and both produce the
16 lines above **byte-for-byte**, including `timeout-minutes` after `steps`. No emitter change is
needed on either side.

### The docs get one section, anchored at end-of-file

Both CLI pages lose their three `### Exit codes` subsections and gain a single top-level
`## Exit codes` section listing the three codes. **That section is appended at end-of-file, after the
final `### Example` block** (`python/cli.md:200-208` + its closing paragraph at `:210`;
`typescript/cli.md:213-221` + `:223`). The anchor is a commitment, not a preference: it is the
condition on which the four-way `docs/…/cli.md` collision with **14**, **17** and **18** was resolved
in 19's favour — **19 edits both pages first** — and it is what makes 19's deletions and their
insertions non-overlapping. See the **14** boundary below.

The four surviving prose statements (`python/cli.md:57,:123`, `typescript/cli.md:70,:136`) are
reworded to name the outcome without re-stating the number — e.g. "Fails if any file is stale (see
[Exit codes](#exit-codes))" — so the number itself appears once per page.

## What sits behind the seam

`main()` becomes the one place that **decides** what the shell sees, in both ports. Today that
decision is spread across click's standalone mode, commander's `_exit`, two hand-rolled `Exit(2)`
sites per port, and three docs tables. After this, the frameworks render text and `main()` decides
the number.

The claim is deliberately narrower than "the number is written down once". Nine prose sites still
describe per-command outcomes (enumerated under _Current interface_), and that is fine — they are
descriptions of one command's behaviour, they all remain true, and none of them is consulted by code.
What disappears is the possibility of two _implementations_ disagreeing.

That is depth in the precise sense: a two-symbol interface (`main(argv) -> int`, plus the table it
must satisfy) sitting in front of every parse path, every validation path, and every command body,
where before the caller had to know which of four authorities would answer for their particular
argv. It is also the ADR-0007 seam finally being real — the config module was made to return errors
as values _so that_ the CLI could own the exit code, and now it does.

Locality follows: the `1` vs `2` question has exactly one answer, in one file per port, checked by
one fixture. A new command cannot invent a third convention without failing the table.

**Deletion test, applied to what this adds:**

- `fixtures/cli-exit-codes.yml` — delete it and each port re-grows its own list of cases. That is
  exactly the state that produced a 2/1 split nobody noticed: complexity reappears across two
  callers, in the form of two drifting opinions. **Earns its keep.**
- `fixtures/expected/init_scaffold.yml` — delete it and the two templates are free to drift again,
  which is how `timeoutMinutes: 10` came to exist on one side only. **Earns its keep**, and it is a
  data file, not an interface.
- `trapExits` / Python's `main()` — delete either and the framework takes the decision back and the
  divergence returns immediately. **Earns its keep.**
- An `EXIT_OK`/`EXIT_FAILURE`/`EXIT_USAGE` constants module — **fails the deletion test.** Delete it
  and each of ~4 call sites writes `2`. Nothing reappears; it is a pass-through with a name. Not
  proposed. `EXIT_USAGE` above is a file-local `const` in `main.ts`, not a module.
- A shared `CliResult` type threaded through every command — **fails.** Both ports already have a
  perfectly good channel for "expected failure with a code" (`CliError` / `typer.Exit`), and one
  adapter is a hypothetical seam. Not proposed.

## Migration plan

Pre-1.0; clean break. No compatibility shim for the old codes.

1. Add `fixtures/cli-exit-codes.yml` with the ten rows above. Add both drivers. They fail on `main`
   today: six rows red in TypeScript, zero in Python — which is itself the finding, recorded as a
   test.
2. TypeScript: add `trapExits`, the `CommanderError` import and branch, and `EXIT_USAGE` to
   `main.ts`. Change the shim to `process.exitCode`. Fix the `_errors.ts:6-7` docstring (it is
   accurate until this step and inaccurate after it). `deps.ts` is not opened.
3. Python: add `main(argv=None) -> int` to `main.py` with the Typer-mirroring render branch; repoint
   `pyproject.toml:29` to it. Add the stderr-fidelity cases **in the same commit** — the exit-code
   rows alone cannot catch a rendering regression. `app` stays exported. `deps.py` is not opened.
4. Add `timeout_minutes=10` to the Python `init` template (`main.py:73-100`).
5. Add `fixtures/expected/init_scaffold.yml` and both scaffold-golden tests.
6. Rewrite the exit-code sections of both CLI docs pages: delete `python/cli.md:114-120,136-142,179-185`
   and `typescript/cli.md:127-133,149-155,192-198`; append one `## Exit codes` section **at
   end-of-file** on each; reword `python/cli.md:57,:123` and `typescript/cli.md:70,:136`. The
   `deps upgrade` `1` row is deleted, not edited — it never described either port.
7. Append the ADR-0007 Consequences bullet and both CONTEXT.md edits.
8. `scripts/test.sh all`; `uv run ghagen check-synced`; `uv run ghagen deps check-synced`. No
   workflow regeneration is required — nothing in `.github/ghagen_workflows.py` changes.

## Test impact

- **New — `fixtures/cli-exit-codes.yml` driver, both ports.** Each row `chdir`s into an empty temp
  directory and asserts `main(argv) == row.exit`. Python: `test_exit_codes.py` reads the table via
  `ghagen_schema.paths.FIXTURES_DIR / "cli-exit-codes.yml"` (`paths.py:35`). TypeScript:
  `exit-codes.test.ts` reads it via `resolve(REPO_ROOT, "fixtures", "cli-exit-codes.yml")`
  (`paths.ts:35`) — `FIXTURES_DIR` is not usable there because the TS export already points one level
  deeper, at `fixtures/expected` (`paths.ts:41`). Six rows are red in TypeScript on `main` today; all
  ten are green in Python.
  The TypeScript driver is a new file rather than an addition to `main.test.ts` because that file
  mocks `jiti` at module scope (`main.test.ts:34-53`).
- **New — Python stderr-rendering fidelity, four cases** (`bogus-command`, `synth --bogus`,
  `init --outdir`, `--version`). Exit codes alone would not catch the `exc.show()` regression, which
  is a silent 5×-shrink of every error message with no exit-code change. Each case asserts the rich
  rendering survives: the `Usage:` line, the `Try 'ghagen … --help' for help.` hint, and the
  box-drawn `╭─ Error` panel. Asserting the panel marker rather than a byte count keeps the test
  stable against Typer's own formatting changes while still failing on any downgrade to the plain
  renderer, which emits no panel at all.
  **These four cases must read `result.stderr`, never `result.output`** — `output` interleaves both
  streams (§2), so an `in result.output` assertion would pass identically whether the panel went to
  stderr, to stdout, or nowhere in particular. They are the only assertions this proposal adds that
  are about _routing_ as well as content; every other new assertion is an integer exit code.
- **New — scaffold golden, both ports.** Python (`test_init_scaffold.py`): call
  `main(["init", "--outdir", str(tmp_path)])`, import the written `ghagen_workflows.py`, and assert
  `app.documents()[0].to_yaml(header=None)` equals the fixture. Verified working against the real
  scaffolded file; it currently emits the fixture **minus** `timeout-minutes: 10`, so it is red until
  step 4.
- **New — scaffold golden, TypeScript** (`init-scaffold.test.ts`): call `main(["init", "--outdir", tmp])`,
  then rewrite the single import specifier `"@ghagen/ghagen"` → an absolute path to `src/index.ts`,
  load through **one** `createJiti` instance (module cache **on**), and assert
  `toYaml(app.documents()[0], { header: null })` equals the fixture. Verified end to end; it produces
  the fixture byte-for-byte today. Two details are non-obvious and were established by experiment:
  the specifier rewrite is unavoidable because nothing links `@ghagen/ghagen` into a temp directory
  and `package.json`'s `exports` points at `dist/` (which the test suite must not require a build
  for); and `moduleCache: false` — the setting `loadApp` uses (`_common.ts:72`) — yields a second
  copy of the model classes and the emitter throws `Tag not resolved for Function value`. This is
  the same module-identity hazard `main.test.ts:10-20` documents.
- **Unchanged:** every existing exit-code assertion. `test_main.py:32,162,169,225,237,248` and
  `test_deps.py:83,107` assert `1`; `test_deps.py:605` asserts `2`; `main.test.ts:85,104,124,135,150`
  assert `0`/`1`. All keep their values.
- **Explicitly not touched: the 78 `result.output` assertions.** They are content assertions and
  they are correct as content assertions — including `test_deps.py:606`, which reads a stderr message
  out of the mixed stream deliberately and sits one line below the `2` this proposal makes binding.
  An implementer must **not** "fix" them to `result.stderr` as part of this change: doing so would
  silently expand the diff into every CLI test file, and the routing question they cannot answer is
  not one this proposal legislates (see _Streams are recorded, not legislated_). The only new
  `result.stderr` assertions are the four fidelity cases above.
- Baseline moves from pytest 562 / vitest 515 by roughly +16 / +11 (ten table rows plus one scaffold
  golden per port, plus Python's four fidelity cases).

## Risks & alternatives

**Scope boundaries vs siblings.**

- **17 (upgrade-report renderer, restructures `deps.ts`).** **This proposal touches no hunk of
  `packages/typescript/src/cli/deps.ts` and no hunk of `packages/python/src/ghagen/cli/deps.py`
  — zero lines, not "a small hunk".** Against 17's declared hunks (imports `8-21`, `depsUpgrade`
  `159-170` and `180-230`, deleted block `233-342`, exports `380-389`) the intersection is empty,
  including the format-validation hunk at `159-170` that 17 offered to sever — **19 does not need it
  severed**, and 17's own revision has since dropped `MACHINE_FORMATS`, so 17 no longer touches that
  hunk at all. Confirmed independently three times, from both sides. 19 reads `deps.ts:156,166-169` and `deps.py:171,180` as _evidence_ that both ports
  already chose `2`; it does not edit them, and 17 may move, rename, or re-home that validation
  freely, because the table asserts the code the process returns, not the site that raises it. The
  reason no edit is required is the probe above, run against the **real** `buildDepsCommand()`
  (`deps.ts:345-378`) imported from `dist/`: `trapExits` walks `program.commands` after `buildCli()`
  returns, so the `addCommand`-mounted `deps` subtree — and everything 17 rearranges inside it — is
  reached without editing the file. **The `17 — 19` conflict edge drops; the two can land in either
  order, with no severing and no coordination.** The one property 17 must preserve is that `deps`'s
  subcommands stay reachable from `program.commands` — true for `.command()` and `.addCommand()`
  alike.
- **14 (`versions` owns comparison).** Shared files: **`docs/src/content/docs/python/cli.md`** and
  **`typescript/cli.md`**. **19 edits both files first**, by round-level decision, on the condition
  stated above: 19's new `## Exit codes` section is anchored at **end-of-file, after `### Example`**.
  That anchor has since been verified against both files and accepted, so the ordering is now
  **unconditional**: 19 lands on these two pages before 14, 17 and 18.
  19's deletions are `python/cli.md:114-120,136-142,179-185` and
  `typescript/cli.md:127-133,149-155,192-198` — each terminal within its own subsection, ending at
  the next heading — while 14 (and 17, 18) insert _within_ `## ghagen deps upgrade`'s body, above
  `:179`/`:192`. With the end-of-file anchor, the deletions and the insertions do not overlap and all
  four land conflict-free. 14 also declared `paths.ts` / `ghagen_schema/paths.py` out of scope; 19
  makes the same call, so neither races the other for those files.
- **23 (dev-script hygiene, `scripts/` + `.github/workflows/ci.yml`).** **No overlap.** Both new
  suites are ordinary pytest/vitest files picked up by `scripts/test.sh` (`uv run pytest`,
  `npm run test --prefix packages/typescript`), which CI already runs in "Test (Python …)" and
  "Test (TypeScript)". No new gate, no `scripts/` change, no workflow regeneration. Had a gate been
  needed it would have gone in `.github/ghagen_workflows.py` **and** the generated
  `.github/workflows/ci.yml` — flagging that only to record that it was considered and is not needed.
- **13 (unify `format_header`).** Adjacent and deliberately disjoint. Both ports' scaffolded files
  differ in the header too — TypeScript emits a blank line between `# Do not edit manually.` and
  `name: CI`, Python does not — and that is 13's. The `init_scaffold.yml` golden is emitted with
  `header: null` / `header=None`, matching every existing fixture in `fixtures/expected/`, so it
  cannot collide with 13. When 13 lands, the header may be brought under the same golden; nothing
  here blocks it.
- **18 (`check-deps` decision logic across the CLI seam).** The vestigial `|| true` at
  `check-deps/action.yml:65` belongs to 18. This proposal only cites it, and the
  `total_updates != '0'` guards at `:89`/`:156`, as evidence that row 15's documented `1` was never
  true. 19 does not edit `check-deps/action.yml`.
- **11 (shared spec surface table)** owns `packages/typescript/CONTEXT.md:85-87` (a new entry after
  **Drift**). 19's one new glossary term goes at the very end of the `## Language` section,
  immediately before `## Relationships` (`ts:87` / `py:85`) — textually adjacent to 11's insertion
  point. Both are pure insertions at the same seam, so the merge is trivial and order-independent;
  recorded so whoever lands second expects it.

**Alternative: leave the codes alone and just fix the docs.** Rejected. It documents a divergence
rather than removing one, and the parity mandate is not "describe the difference". A user running
`ghagen synth --bogus` in a script that branches on `2` gets different behaviour depending on which
port their team installed, for identical input.

**Alternative: standardise on `1` for usage errors (move Python, not TypeScript).** Rejected on
evidence. `2` for usage errors is the POSIX/GNU convention click implements deliberately, and both
ports _already independently chose 2_ for the usage errors they validate themselves
(`deps.py:171,180`, `deps.ts:156,169`). Moving Python would mean changing the one port that is
right, breaking its agreement with its own hand-rolled validation.

**Alternative: keep `main()` returning and simply document that it may not return.** Rejected — it
is not a docstring problem. A `main()` that sometimes kills the process cannot be tested for the
usage-error class at all, which is why the divergence survived to now: there is no test that _could_
have caught it without `exitOverride`.

**Alternative: call `rich_utils.rich_format_error(exc)` unconditionally** instead of mirroring
Typer's `HAS_RICH and rich_markup_mode is not None` guard. Rejected on measurement: it is
byte-identical to today only while `TYPER_USE_RICH` is unset, and differs on all six cases under
`TYPER_USE_RICH=0`. The guard costs one line and makes the rendering identical under both settings.

**Risk: `standalone_mode=False` changes Python's rendering, not just its codes.** This is the
proposal's largest risk and the reason effort is L. It is bounded by measurement rather than by
argument: the six-case × two-setting matrix above is byte-identical to today, and the four fidelity
cases in _Test impact_ keep it that way. The residual exposure is that `main()` now depends on two
Typer internals — `typer.core.HAS_RICH` and `rich_utils.rich_format_error` — neither of which is a
documented public API. A Typer upgrade that moves them breaks the build loudly (`AttributeError` /
`ImportError` at import time), not silently, and the fidelity tests cover the case where they stay
importable but change behaviour.

**Risk: `process.exitCode` instead of `process.exit` lets a stray handle hang the CLI.** Accepted.
Nothing in the CLI opens a persistent handle — `GitHubClient` uses one-shot `fetch`, and
`_common.ts:72` builds a fresh `jiti` per invocation. If a hang ever appears it is a leak worth
finding, which `process.exit()` was hiding.

**Reproduction disclosure.** The TypeScript runs above used `node packages/typescript/dist/cli/main.js`
after `npm run build`, with a temp project linking `node_modules/@ghagen/ghagen` by symlink to
`packages/typescript`. In that specific arrangement the emitted header path is mangled
(`…/tmp/ts/file:/Users/…/dist/_source_location.js`) because `callsites()` reports a `file:` URL and
`_package_paths.ts:34` compares it with `startsWith` against a plain path. Under a real
`npm i @ghagen/ghagen` the path contains `/node_modules/` and short-circuits at
`_package_paths.ts:31`, so this is an artifact of the reproduction harness, not a shipped defect. It
does not touch any exit code, and the `init` golden is header-free. Recorded so the runs above can be
reproduced without surprise; not proposed for fixing here.

## ADR / CONTEXT.md impact

- **ADR-0007 is not reopened; it is enforced.** `docs/adr/0007-config-discovery-returns-typed-results.md:9-10`
  already says the CLI "renders errors and owns exit codes". This proposal is the first time that is
  true. Append one bullet to its **Consequences** section (currently `:20-24`, two bullets):
  _"The exit-code contract is `fixtures/cli-exit-codes.yml`, driven through `main()` by both ports:
  `0` success, `1` expected failure, `2` usage error. The CLI frameworks render text; `main()` decides
  the number."_ No line of the decision paragraph changes.
- **No other ADR is contradicted.** ADR-0001 (serialization seam) and ADR-0005 (pipeline ordering)
  are untouched — the `init` golden emits through the existing `to_yaml` / `toYaml` seam with
  `header=None`, exactly as `test_snapshots.py` and `snapshots.test.ts` already do. ADR-0002 (no
  construction-time config globals) is unaffected: `trapExits` runs on a `Command` tree built per
  invocation, and nothing module-level is introduced.
- **`packages/python/CONTEXT.md` (114), `## Surface notes (Python)` (`:94`).** The ADR-0007 bullet
  spans `:102-104` and ends _"…`CliError` is CLI-local. The synthesis pipeline is `synth.render()`;
  pin runs last (ADR-0005)."_ — the exit-code sentence is inserted after "`CliError` is CLI-local."
  and before the pipeline sentence, leaving that clause intact: the CLI entry point is
  `main(argv) -> int`, not the Typer app; click runs in `standalone_mode=False`, so the exit code is
  ghagen's decision and Typer's error rendering is reproduced explicitly.
- **`packages/typescript/CONTEXT.md` (119), `## Surface notes (TypeScript)` (`:96`).** Mirror; the
  ADR-0007 bullet spans `:106-109` and its `CliError` clause reads _"`CliError` lives in
  `cli/_errors.ts`."_ Same insertion point: commander runs under `exitOverride` applied **recursively
  after tree construction** (a root-only call reaches no subcommand), `main()` returns the code, and
  the bin shim sets `process.exitCode`.
- **The Surface-notes list is a hand-merge point, not an exclusive region.** Four proposals — **10**,
  **16**, **17** and **19** — all edit it. The other three _append_ a new bullet at the list tail
  (`python/CONTEXT.md:107`, `typescript/CONTEXT.md:112`); 19 alone edits _inside_ an existing bullet
  (the ADR-0007 one, `py:102-104` / `ts:106-109`), so 19's hunk does not overlap any of theirs and no
  ordering between them is needed. Whoever lands second, third and fourth among the appenders
  resolves a trivial same-line-anchor merge; 19 is unaffected either way. Recorded so nobody treats
  the list as owned.
- **New glossary term, both CONTEXT.md files: exit-code contract** — appended at the end of the
  `## Language` section, immediately before `## Relationships` (`ts:87` / `py:85`), as a short
  `### CLI` subsection. Definition: the three-value (`0` success / `1` expected failure / `2` usage
  error) table in `fixtures/cli-exit-codes.yml` that both ports' `main()` must satisfy. Sibling of
  the existing shared byte oracle in `fixtures/expected/`, to which this adds `init_scaffold.yml`.
  See the **11** adjacency note above.
