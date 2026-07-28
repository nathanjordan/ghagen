# 05 — Config module owns `.ghagen.yml` end to end

**Status:** proposed | **Ports:** both | **Depends on:** spec 0004 (unified root discovery, implemented); interacts with proposal 07 (appLoader pruning)

## Problem

`.ghagen.yml` is read and parsed **twice** on every CLI invocation, by two
readers that disagree on how strict to be, and the discovery/parse/validation
of the file is smeared across three modules per port instead of living behind
one interface.

Spec 0004 already unified the _root locator_ — `findAppRoot` / `find_app_root`
is now the sole ancestor walk, and the TypeScript `config.ts` / `_yaml-config.ts`
/ `_config-schema.ts` trio was merged into one `config.ts`. That work is landed
and is the baseline this proposal builds on. What 0004 deliberately left in
place is the _split parse of the file itself_, and that split is the subject
here.

Concretely, one `ghagen synth` from a project root parses `.ghagen.yml` twice:

- **Entrypoint parse.** `findConfig` (TS `cli/_common.ts:75`) calls
  `entrypointFromGhagenYml` (`cli/_common.ts:36`), which does its own
  `loadYamlConfig` + `ghagenYmlSchema.parse(data)` and reads only
  `config.entrypoint`. Python mirrors this in `_entrypoint_from_ghagen_yml`
  (`cli/_common.py:20`).
- **Options parse.** The `App` constructor (TS `app.ts:82`, Python
  `app.py:82`) calls `loadOptions` / `load_options` (`config.ts:110`,
  `config.py:77`), which re-reads the same file and parses it with a
  _different, narrower_ schema — `optionsSchema.optional().parse(data.options)`
  — reading only `options`.

The two readers use different strictness on purpose, and that divergence is
load-bearing: `loadOptions`'s docstring (`config.ts:104-108`) warns it must
parse only `options` because a malformed `entrypoint:` in the same file would
otherwise throw a `ZodError` on a caller (the header's `{source_file}`
resolution) that never touches `entrypoint`. So the same file has two notions
of "valid" depending on which reader asks. That is exactly the kind of
implicit-interface hazard a single module should absorb.

Three secondary problems ride along:

1. **Errors are framework exceptions, not values.** Python's discovery mixes
   parse + dynamic import + `typer.Exit` rendering inside `cli/_common.py`
   (`_entrypoint_from_ghagen_yml` and `_load_app` both `typer.echo(...)` then
   `raise typer.Exit(1)`). Tests can only assert failure by catching
   `typer.Exit` (`test_cli/test_common.py:72`), and they reach into private
   `_find_config` / `CONFIG_SEARCH_PATHS` (`test_common.py:15`) to do it. This
   is the opposite of the pin engine's typed-report style, whose docstring
   (`pin/engine.py:2-11`) explicitly lifts orchestration out of the Typer
   runner and returns typed reports with `report.warnings` / `report.errors`
   so the logic is testable without a CLI harness. The config path never got
   that treatment.

2. **A cycle-breaking module exists only for this.** TS `_load.ts` holds
   `resolveAppFromModule` + `CliError` solely so `cli/` and `pin/` can share
   the module→App resolution policy without `pin/` importing `cli/`
   (`_load.ts:1-12`). `cli/_common.ts:13` then re-exports `CliError` "so
   existing import sites keep working" — indirection layered on indirection.
   Python has no `_load.py` at all; it breaks the same cycle a different way,
   by injecting `_load_app` as a parameter into `pin/sources.track_user_files`
   (`deps.py:187`) — a divergence between the ports that this proposal can
   collapse.

3. **Two constants drift.**
   - Lockfile default: TS `app.ts:23` `DEFAULT_LOCKFILE_REL` duplicates
     `lockfile.ts:24` `DEFAULT_LOCKFILE_PATH` (the comment at `app.ts` says
     App avoids importing `pin/` off the cold path, so it keeps a private
     copy). Python `lockfile.py:29` `DEFAULT_LOCKFILE_PATH` is defined but
     **never read anywhere** — `app.py:41` hardcodes the literal
     `".ghagen.lock.yml"` in the default argument.
   - `auto_dedent` default: stated in four places across two values.
     `config.py:74` `GhagenOptions.auto_dedent = True`; `_base.py:198,232`
     `Document.to_yaml` / `to_yaml_file` default `True`; but the internal
     `emitter/document.py:23,54` `emit` / `emit_file` default **`False`**.
     The Python split is documented as intentional (`document.py:31-33`: "Off
     by default; the `Document.to_yaml` facade defaults it on"). The real
     defect is a **parity mismatch**: TS's internal emitter entry
     `yaml-writer.ts:230` defaults `autoDedent` to **`true`**
     (`options?.autoDedent ?? true`), the opposite of Python's internal
     `emit`. Same layer, two ports, two defaults.

## Current interface

Per port, the `.ghagen.yml` story is spread across:

- `config.{ts,py}` — `findAppRoot`, `loadYamlConfig`, `loadOptions`,
  `GhagenOptions`, the zod/`dataclass` shape, `GHAGEN_YML_MARKER`.
- `cli/_common.{ts,py}` — `entrypointFromGhagenYml` (second parse, strict
  schema), `findConfig` (search-path probe), and — in Python — `_load_app`
  (dynamic import + app resolution). Errors are `CliError` (TS) or
  `typer.Exit` (Python).
- TS `_load.ts` — `resolveAppFromModule`, `CliError`.

The interface a caller must know today is genuinely large: _which_ reader
validates _which_ key at _which_ strictness, that `loadOptions` must be called
against the app root (not cwd), that a bad `entrypoint:` is safe for
`loadOptions` but fatal for `findConfig`, and that Python raises `typer.Exit`
mid-discovery while TS throws `CliError` to be caught at `main`. That breadth is
the shallowness: the implementation leaks into every caller.

`findConfig`'s search still forks into two near-identical loops
(`cli/_common.ts:91-104`): the `root !== null` arm probes `CONFIG_SEARCH_PATHS`
relative to the discovered root _and_ checks the entrypoint key; the
`root === null` arm probes the same paths relative to cwd and skips the
entrypoint check. Only the anchor differs.

## Proposed interface

One **config module** per port owns discovery + parse + validation of
`.ghagen.yml`, parses the file **once**, and returns a **typed result** whose
error modes are values, not exceptions. The CLI renders errors; `App` and
`pin/` consume the value.

### Shared shape (both ports)

```
ProjectConfig:
  root:        directory containing .ghagen.yml, or null (no marker found)
  configPath:  resolved workflow entrypoint, or null when only options exist
  options:     GhagenOptions (auto_dedent, …) — always populated with defaults
  entrypoint:  the raw entrypoint string from the file, or null
  errors:      list of ConfigError (empty on success)

ConfigError:
  kind:    "parse" | "not-a-mapping" | "bad-entrypoint-type"
         | "entrypoint-missing" | "bad-option-type"
  path:    the .ghagen.yml (or resolved entrypoint) the error concerns
  message: human-readable text the CLI can print verbatim
```

The module reads the file at most once per discovery and derives _both_ the
entrypoint and the options from that single parse. Strictness stops being
per-reader: the whole file is validated once, and a malformed `entrypoint:`
becomes a `ConfigError` value that a caller may **choose** to ignore (the
header's `{source_file}` path wants only `options` and can proceed on the
defaults) or surface (the CLI's config resolution treats it as fatal). The
divergence moves from "two schemas" to "one validated result, callers pick
which errors matter" — the safe-vs-fatal decision is explicit at the call
site instead of encoded in a schema choice.

### TypeScript sketch

```ts
// config.ts — the one home for .ghagen.yml.

export interface GhagenOptions {
  auto_dedent: boolean;
}

export type ConfigErrorKind =
  | "parse"
  | "not-a-mapping"
  | "bad-entrypoint-type"
  | "entrypoint-missing"
  | "bad-option-type";

export interface ConfigError {
  readonly kind: ConfigErrorKind;
  readonly path: string;
  readonly message: string;
}

export interface ProjectConfig {
  readonly root: string | null;
  readonly configPath: string | null;
  readonly options: GhagenOptions;
  readonly entrypoint: string | null;
  readonly errors: readonly ConfigError[];
}

/**
 * Discover the project root, parse .ghagen.yml ONCE, resolve the workflow
 * entrypoint (entrypoint key → CONFIG_SEARCH_PATHS), and read options.
 * Never throws for user-input problems: they are returned in `errors`.
 * `cliConfigFlag` short-circuits discovery when the user passed --config.
 */
export function loadProjectConfig(start?: string, cliConfigFlag?: string): ProjectConfig;

/**
 * Read only options for a given root — the header's {source_file} path,
 * which must never fail on a bad entrypoint. Thin wrapper that discards
 * every ConfigError whose kind is not "bad-option-type".
 */
export function loadOptions(start?: string): GhagenOptions;
```

`findConfig`'s two search loops collapse into one: compute the anchor once
(`root ?? cwd`), probe `CONFIG_SEARCH_PATHS` against that single anchor, and
run the entrypoint check only when `root !== null`. The fork disappears
because the only thing that differed between the arms was the anchor.

The module→App resolution (`resolveAppFromModule`) moves **into** the config
module as `resolveApp(mod, configPath): Result<App, ConfigError>` returning an
error value rather than throwing `CliError`. `CliError` is no longer needed as
a shared type at the package root; it becomes a purely CLI-owned concern (see
"\_load.ts" below).

### Python sketch

```py
@dataclass(frozen=True)
class GhagenOptions:
    auto_dedent: bool = True

@dataclass(frozen=True)
class ConfigError:
    kind: str          # "parse" | "not-a-mapping" | "bad-entrypoint-type" | ...
    path: Path
    message: str

@dataclass(frozen=True)
class ProjectConfig:
    root: Path | None
    config_path: Path | None
    options: GhagenOptions
    entrypoint: str | None
    errors: tuple[ConfigError, ...]

def load_project_config(
    start: Path | None = None,
    cli_config_flag: str | None = None,
) -> ProjectConfig: ...

def load_options(start: Path | None = None) -> GhagenOptions:
    # keeps only bad-option-type errors; a bad entrypoint cannot break this.
    ...
```

Discovery + parse + validation carry **no** `typer` import. `cli/_common.py`
shrinks to: call `load_project_config`, and if `config.errors`, `typer.echo`
each `err.message` and `raise typer.Exit(1)` — the render step, and only the
render step, lives in the CLI, exactly as `pin/engine.py` already does for the
pin path.

### Invariants

- `.ghagen.yml` is opened and parsed at most once per `load_project_config`
  call.
- `options` is always a fully-populated `GhagenOptions` (defaults applied),
  even when the file is missing, empty, or has no `options:` section.
- `loadProjectConfig` / `load_project_config` never raise on user-input
  problems (missing file, bad YAML, wrong-typed keys). I/O faults outside the
  user's control (an unreadable file the OS refuses) may still raise — those
  are not config errors.
- `loadOptions` is total: it returns defaults and swallows every non-option
  error, preserving the header path's immunity to a bad `entrypoint:`.
- `root` and the header's per-Document `{source_file}` resolution both keep
  using the same `findAppRoot` primitive; the header calls it with an
  arbitrary start path per file, so `findAppRoot` stays exported and unchanged.

### Error modes (explicit)

| Situation                                | Old behaviour                                                                                                                          | New behaviour                                                                                          |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Malformed YAML                           | TS: `CliError` from `entrypointFromGhagenYml`; Python: `typer.Exit`. `loadOptions` throws separately.                                  | One `ConfigError{kind:"parse"}`. CLI renders + exits; header path ignores it and uses default options. |
| `entrypoint:` wrong type                 | TS: `CliError`; also `loadOptions` throws (`ZodError`) unless it parsed options-only. Python: `typer.Exit`; `load_options` unaffected. | `ConfigError{kind:"bad-entrypoint-type"}`. Fatal to `findConfig`; invisible to `loadOptions`.          |
| `entrypoint:` resolves to a missing file | `CliError` / `typer.Exit`                                                                                                              | `ConfigError{kind:"entrypoint-missing"}`                                                               |
| `options.auto_dedent` wrong type         | TS: `ZodError` in `loadOptions`; Python: `ValueError` in `load_options`                                                                | `ConfigError{kind:"bad-option-type"}`; surfaced by both `loadProjectConfig` and `loadOptions`.         |
| No `.ghagen.yml` anywhere                | `root=null`, probe cwd                                                                                                                 | Unchanged: `root=null`, options defaulted, cwd-anchored search.                                        |

## What sits behind the seam

The interface is small — one function returning one value — but a lot of
behaviour hides behind it: the ancestor walk, the single YAML read, mapping
validation, the entrypoint-key resolution and its fallback to
`CONFIG_SEARCH_PATHS`, options defaulting, and (folded in from `_load.ts`) the
module→App resolution policy. That is the deep-module shape the current layout
lacks: today a maintainer must know all of that _and_ which of three modules
each piece lives in. The **deletion test** is instructive — remove
`loadProjectConfig` and every CLI command, the `App` constructor, and the pin
tracker lose their notion of "where and what is the project config," which is
real leverage; remove today's `entrypointFromGhagenYml` and you have merely
relocated one of two parses.

### The lockfile-default and `auto_dedent`-default constants

**Lockfile default → single home in the config module.** Move the literal
`".ghagen.lock.yml"` to `config.{ts,py}` as `DEFAULT_LOCKFILE_PATH` (the
config module is already framed as "project configuration" and is already
imported by `App`). `App` reads it from there (killing TS's private
`DEFAULT_LOCKFILE_REL` and Python's hardcoded literal in the default arg).
`pin/lockfile.{ts,py}` imports the same constant from config instead of
declaring its own. This resolves the cold-path worry cited at `app.ts` — config
is a leaf-ish module with no `pin/` transform machinery behind it, so `App`
importing the constant from config pulls in nothing it does not already load,
and `pin/` depending on `config` is a clean one-way edge. Python's orphan
`lockfile.py:29` constant and TS's duplicate both disappear.

**`auto_dedent` default → single home in `GhagenOptions`, threaded
explicitly.** ADR-0002 requires options that affect output to be applied at
serialization time and _threaded explicitly_ — "No module-level mutable global
carries configuration." The default value is not a global, but it is currently
a literal restated four times with a port mismatch. Resolution, within
ADR-0002's letter:

- The single default `True` lives once, on `GhagenOptions.auto_dedent`
  (`config.{ts,py}`). This is the source of truth a project's `.ghagen.yml`
  overrides.
- The **public** serialization entry keeps a default that references that one
  value: Python `Document.to_yaml(auto_dedent=True)`, TS `toYaml`'s
  `autoDedent ?? true`. These are the ergonomic facades and should default on.
- The **internal** emitter core takes `auto_dedent` as a **required**
  parameter — no default. Python `emit` / `emit_file` (`document.py`) and the
  TS `dedentSteps`/`modelToYamlMap` path are only ever called with an explicit
  value threaded from `App` or from the public facade, so a default there is
  dead surface that can only drift. Making it required deletes the question and
  forces the two ports back into parity (Python's `False` and TS's `true`
  internal defaults both vanish).

This keeps ADR-0002 satisfied (threaded explicitly, applied at emit) while
single-homing the literal.

### `_load.ts` — does its role dissolve?

Yes. `_load.ts` exists only to give `cli/` and `pin/` a neutral place to share
`resolveAppFromModule` without a `pin/ → cli/` import. Once `resolveApp`
(the renamed, error-value-returning resolver) lives in the config module,
`pin/sources.ts` imports it from `config.js` and `cli/` imports it from
`config.js` — the neutral module is no longer neutral-ground-for-a-cycle, it
just _is_ config. `_load.ts` is deleted. `CliError` relocates to a small
CLI-owned module (e.g. `cli/_errors.ts`) since it is a CLI-exit concern and the
resolver no longer throws it; the `cli/_common.ts:13` re-export "so existing
import sites keep working" is deleted outright (pre-1.0; update the three
import sites in `main.ts`, `deps.ts`, `_common.ts`).

For Python, this is the move that lets proposal 07 delete the `app_loader`
injection: `pin/sources.py` calls the shared `resolve_app` directly (from
`config`) instead of receiving `_load_app` as a parameter, because there is no
longer a `pin/ → cli/` cycle to dodge. The two ports converge on the same
structure.

## Migration plan

1. **Config module gains the typed result.** Add `ProjectConfig`,
   `ConfigError`, and `loadProjectConfig` / `load_project_config` to
   `config.{ts,py}`. Implement the single-parse discovery by folding
   `entrypointFromGhagenYml` logic in and reusing `findAppRoot`. Rewrite
   `loadOptions` / `load_options` as a thin filter over the same result.
2. **Collapse the two search loops** in `findConfig` / `_find_config` into one
   anchored probe.
3. **Move app resolution into config.** Relocate `resolveAppFromModule` →
   `resolveApp` (returns `Result` / `(App | None, errors)`), delete TS
   `_load.ts`, move `CliError` to `cli/_errors.ts`, drop the `_common.ts`
   re-export, update import sites.
4. **CLI renders errors.** `cli/_common.{ts,py}` and the `deps`/`synth`
   commands map `config.errors` to `CliError` / `typer.Exit`. No `typer`
   import remains in discovery/parse code.
5. **Thread config into `App`.** `App` constructor accepts an optional
   pre-loaded `options` (or `ProjectConfig`); when omitted it calls
   `loadProjectConfig` itself (standalone `new App()` / `App()` still works).
   The CLI passes the already-parsed result so `synth` parses `.ghagen.yml`
   exactly once total.
6. **Single-home the constants.** Move `DEFAULT_LOCKFILE_PATH` to config;
   delete the TS duplicate and the Python orphan/hardcode. Make internal
   emitter `auto_dedent` required; keep the single `True` default on
   `GhagenOptions` and the public facades.
7. **Update pin.** `pin/sources.py` calls `config.resolve_app` directly; drop
   the `app_loader` parameter (coordinated with proposal 07). TS
   `pin/sources.ts` imports `resolveApp` from config.

## Test impact

- **Python discovery tests stop catching `typer.Exit`.** `test_cli/test_common.py`
  asserts `ConfigError` values from `load_project_config` directly, no CLI
  harness, no reaching into `_find_config`/`CONFIG_SEARCH_PATHS` privately.
  This is "testing: replace, don't layer" — the test targets the value the
  module returns, not a rendering side effect. A thin CLI-level test still
  covers that `errors` are printed and exit is non-zero.
- **TS `config.test.ts`** keeps its `loadOptions` cases (including the
  regression that a malformed `entrypoint:` must not throw — now guaranteed by
  the `loadOptions` filter rather than a schema choice) and gains
  `loadProjectConfig` cases for the single-parse result and each `ConfigError`
  kind.
- **`findConfig` / `_find_config` tests** (spec 0004's subdir cases) continue
  to pass; they now exercise one loop instead of two. The `--config`
  short-circuit is unchanged.
- **Constant single-homing** is covered by existing lockfile/App tests
  (default path still `.ghagen.lock.yml`) and by an assertion that TS and
  Python internal emitters now require `auto_dedent` (a call without it is a
  type error / `TypeError`), closing the parity gap with a test rather than a
  comment.
- No golden-file (`fixtures/expected/`) output changes: `auto_dedent`'s
  _effective_ default at the public facade stays `True` in both ports.

## Risks & alternatives

- **Risk: `App` double-loading in library use.** If a library caller builds
  `App` and _also_ calls `loadProjectConfig`, the file is read twice. Mitigated
  by letting `App` accept a pre-loaded `ProjectConfig`; the CLI always passes
  one. Standalone `new App()` reads once, as today.
- **Risk: errors-as-values is more code than `throw`.** True, but it is the
  same trade the pin engine already made deliberately (`engine.py:2-11`), and
  it is what makes the config path testable without a Typer/commander runner.
  Consistency across the two orchestration surfaces is worth the few extra
  types.
- **Alternative: keep two parses, just share a schema.** Rejected — a shared
  schema does not remove the double read or the per-reader strictness fork; it
  only renames the divergence. The point is one validated result with callers
  choosing which errors bind.
- **Alternative: leave `_load.ts` alone.** Rejected — with app resolution in
  config, `_load.ts` is a single-adapter module (one production caller each
  side) whose only job was cycle avoidance that no longer exists. Keeping it is
  indirection for its own sake, and it blocks proposal 07's Python `app_loader`
  cleanup.
- **Alternative: home the lockfile default in `app`, not config.** Rejected —
  `pin/lockfile` would then import `app`, and `app` imports `pin` (lazily);
  routing the constant through the config leaf avoids any hint of a cycle.

## ADR / CONTEXT.md impact

- **ADR-0002** is upheld and slightly clarified: add a note that the single
  `auto_dedent` default lives on `GhagenOptions`, the public facades default to
  it, and the internal emitter takes it as a required threaded parameter (no
  internal default). No mutable global is introduced.
- **Spec 0004** is superseded in part: it unified root _discovery_ and the TS
  file layout; this proposal unifies the _file parse_ it left split. Add a
  forward-reference from 0004 to 05.
- **New ADR recommended:** "Config discovery returns typed results, not
  framework exceptions" — parallel to the pin engine's typed-report decision,
  recording that `.ghagen.yml` discovery/parse/validation is exception-free and
  CLI-rendered.
- **CONTEXT.md (both ports):** document the config module as the single owner
  of `.ghagen.yml` (discovery + parse + validation + app resolution) and note
  that `CliError` is CLI-local. Remove any mention of `_load.ts` as a shared
  cycle-breaker.
