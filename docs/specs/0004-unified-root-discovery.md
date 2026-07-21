# 0004 — Unified Root Discovery

Status: implemented

## 1. Problem

Each port has two unrelated project-root locators that disagree with each
other, plus a TypeScript-only structural and validation-coupling defect.

### 1.1 Two locators per port

**Python:**

- `config.py:26` `find_app_root(start=None)` — walks upward from `start`
  (default `Path.cwd()`) through every ancestor directory looking for
  `.ghagen.yml`. Used by `load_options` (`config.py:112`) and by the
  emitter header's `{source_file}` resolution
  (`emitter/header.py:111`, `root = find_app_root(abs_path.parent)`).
- `cli/_common.py:63-89` `_find_config(config)` — when no `--config` flag is
  given, calls `_entrypoint_from_ghagen_yml(Path.cwd())` (line 72), which
  reads `.ghagen.yml` **only** in `Path.cwd()` (`cli/_common.py:31-33`,
  `ghagen_yml = cwd / GHAGEN_YML_PATH; if not ghagen_yml.is_file(): return
None`) — no ancestor walk. If that misses, it probes
  `CONFIG_SEARCH_PATHS` (`.github/ghagen_workflows.py`,
  `ghagen_config.py`) also relative to `Path.cwd()` only
  (`cli/_common.py:76-79`).

**TypeScript — same bug, confirmed by reading `cli/_common.ts` in full:**

- `config.ts:26` `findAppRoot(start?)` — ancestor walk from
  `process.cwd()` by default (same semantics as the Python version,
  including the file-vs-directory `start` handling). Used by `loadOptions`
  (`config.ts:59`) and `emitter/header.ts:79`
  (`findAppRoot(dirname(absPath))`).
- `cli/_common.ts:83-111` `findConfig(cliFlag?, cwd = process.cwd())` —
  calls `entrypointFromGhagenYml(cwd)` (line 92), which resolves
  `.ghagen.yml` directly under the given `cwd` only
  (`cli/_common.ts:45`, `resolve(cwd, GHAGEN_YML_PATH)`) — no ancestor
  walk — then falls back to probing `CONFIG_SEARCH_PATHS` resolved
  against the same flat `cwd` (`cli/_common.ts:97-101`).

The TS CLI has the identical split-locator defect as the Python CLI: one
locator (`findAppRoot`) walks ancestors, the other (`findConfig` /
`entrypointFromGhagenYml`) does not.

### 1.2 Concrete repro (both ports, symmetric)

Given a project laid out as:

```
repo/
  .ghagen.yml         # entrypoint: workflows/ci.py (or .ts)
  workflows/ci.py
  subdir/
```

Running the CLI with `cwd = repo/subdir`:

- **Options / header resolution** (`load_options()` /
  `find_app_root()`, or `loadOptions()` / `findAppRoot()`): ancestor walk
  from `repo/subdir` finds `repo/.ghagen.yml` → root resolves to `repo`.
  `auto_dedent` options and `{source_file}` header values are computed
  correctly relative to `repo`.
- **Config/entrypoint resolution** (`_find_config()` / `findConfig()`):
  checks only `repo/subdir/.ghagen.yml` (absent) and then
  `repo/subdir/.github/ghagen_workflows.py`,
  `repo/subdir/ghagen_config.py` (absent). No ancestor walk. Result:
  `Error: no config file found`, even though `repo/.ghagen.yml` with a
  valid `entrypoint` exists one level up.

So the same invocation resolves two different notions of "project root"
depending on which code path asks — the CLI fails outright from a
subdirectory while the parts of the system that already use
`find_app_root`/`findAppRoot` would have resolved correctly. This is a
real, user-facing bug, not just a structural inconsistency: `cd subdir &&
ghagen synth` fails where `ghagen synth` (from the root) succeeds, with no
indication that moving to a subdirectory is the cause.

Confirmed untested: every CLI test in
`packages/python/tests/test_cli/test_main.py` (`test_entrypoint_*`,
`test_cli_config_overrides_ghagen_yml`, `test_ghagen_yml_without_entrypoint_falls_back`,
etc.) does `monkeypatch.chdir(tmp_path)` where `tmp_path` **is** the
`.ghagen.yml` directory — never a subdirectory of it. No TS CLI test file
exists at all under `packages/typescript/src/cli/` (only implementation
files: `_common.ts`, `deps.ts`, `main.ts`). The subdirectory case has zero
coverage in either port.

### 1.3 TypeScript three-file split + validation coupling

Python keeps root discovery, YAML loading, and options in one module,
`config.py` (its docstring states this explicitly: "This module unifies
three concerns that used to live apart"). TypeScript splits the
equivalent surface across three files with no Python counterpart split:

- `config.ts` (69 lines) — `findAppRoot`, `loadOptions`.
- `_yaml-config.ts` (33 lines) — generic `loadYamlConfig`, used only by
  `config.ts:11` and `cli/_common.ts:8` (not exported from `index.ts`).
- `_config-schema.ts` (19 lines) — zod `optionsSchema` /
  `ghagenYmlSchema`, used only by `config.ts:10` and `cli/_common.ts:7`
  (not exported from `index.ts`; only the inferred `GhagenOptions` type
  is re-exported, via `config.ts`).

None of the three has any consumer outside this cluster (confirmed by
grep across `packages/typescript/src`), so the split buys no reuse or
layering benefit — it's pure parity drift against the Python module
boundary.

Beyond the split, `ghagenYmlSchema` (`_config-schema.ts:13-16`) declares
both `options` and `entrypoint`, but the two call sites each parse the
**whole** schema and use only their half:

- `config.ts:62`, `loadOptions`: `const config =
ghagenYmlSchema.parse(data);` then reads `config.options` only
  (`config.ts:63-65`) — `entrypoint` is parsed and discarded.
- `cli/_common.ts:58`, `entrypointFromGhagenYml`: `config =
ghagenYmlSchema.parse(data);` then reads `config.entrypoint` only
  (`cli/_common.ts:62-72`) — `options` is parsed and discarded.

The `entrypoint` field is not dead code in the "unused" sense — it is
consumed by `cli/_common.ts`. But `loadOptions` parsing the full schema
means a malformed `entrypoint:` value in `.ghagen.yml` (e.g. a number
instead of a string) makes `loadOptions()` throw a `ZodError`, even for
callers that never touch `entrypoint` — e.g. `emitter/header.ts`'s
`{source_file}` computation, or a CLI invocation that passes an explicit
`--config` path and never calls `entrypointFromGhagenYml` at all. Python
has no such coupling: `_extract_from_ghagen_yml`
(`config.py:85-96`) only ever inspects `data.get("options")` and never
looks at `entrypoint`, so a bad `entrypoint` value cannot break
`load_options()`.

## 2. Design

One root-discovery interface per port; `find_app_root`/`findAppRoot`
becomes the sole locator, and the CLI's config/entrypoint lookup rides
it instead of re-deriving "root" from a raw, non-walking `cwd`.

**Python (`config.py` + `cli/_common.py`):**

- `find_app_root` unchanged (already correct, already the primary
  interface used by `load_options` and the header).
- `_entrypoint_from_ghagen_yml` changes its parameter from a raw `cwd:
Path` to a resolved `root: Path` (the caller now supplies the already
  ancestor-walked root, not `Path.cwd()`). Body is otherwise unchanged —
  it still just reads `root / GHAGEN_YML_MARKER`.
- `_find_config` calls `find_app_root()` once (ancestor walk from cwd) and
  reuses the result for both the entrypoint check and the
  `CONFIG_SEARCH_PATHS` probe (resolved against the discovered root, not
  `Path.cwd()`). If `find_app_root()` returns `None` (no `.ghagen.yml`
  anywhere in the ancestry), `CONFIG_SEARCH_PATHS` is probed against
  `Path.cwd()` as today — this preserves the existing "no `.ghagen.yml`,
  drop a conventional file in cwd" fallback for projects that don't use
  `.ghagen.yml` at all.
- Drop the duplicate `GHAGEN_YML_PATH` constant in `cli/_common.py`;
  import `GHAGEN_YML_MARKER` from `config.py` (both already hold
  `Path(".ghagen.yml")`; keeping two names for one value is exactly the
  kind of drift this spec removes).

**TypeScript:** same shape, plus the structural collapse.

- Merge `_yaml-config.ts` and `_config-schema.ts` into `config.ts`,
  matching the Python module boundary (one `config.py` ↔ one `config.ts`).
  Both merged files have zero consumers outside this cluster, so the
  merge is a pure internal move — `cli/_common.ts` updates its two
  imports to pull from `../config.js` instead of `../_yaml-config.js` /
  `../_config-schema.js`. The zod schema itself stays: it is load-bearing
  (single source of truth for shape/defaults, consumed by two call
  sites), so "delete it" is not on the table — only its file location
  changes.
- Decouple `loadOptions` from the `entrypoint` field to close the
  validation-coupling bug in §1.3: `loadOptions` parses only the
  `options` key (`optionsSchema.optional().parse(data.options)`, or a
  narrower object schema containing just `options`) instead of
  `ghagenYmlSchema.parse(data)`. zod object schemas strip unrecognized
  keys by default, so an `entrypoint` field with a bad type present in
  the same file no longer causes `loadOptions()` to throw. This is the
  "wire it or delete it" call for the `entrypoint` field: it's already
  wired into `cli/_common.ts` (keep it there, unchanged), and it gets
  _un_-wired from `loadOptions`, which never needed it. This mirrors
  Python's existing `_extract_from_ghagen_yml`, which already only
  touches `options`.
- `entrypointFromGhagenYml` changes its parameter from `cwd: string` to
  `root: string` (the resolved root), same rationale as the Python side.
- `findConfig` calls `findAppRoot(cwd)` once and reuses the result for
  both the entrypoint check and the `CONFIG_SEARCH_PATHS` probe. Same
  `null`-root fallback to probing `CONFIG_SEARCH_PATHS` against `cwd` as
  today.
- Drop the duplicate `GHAGEN_YML_PATH` constant in `cli/_common.ts`;
  import `GHAGEN_YML_MARKER` from `config.ts`.

`--config` / `--config <path>` behavior is unchanged in both ports: an
explicit flag bypasses root discovery entirely and resolves relative to
`cwd`, exactly as today.

## 3. Before / After

### 3.1 Python — before (two locators)

```python
# config.py:26
def find_app_root(start: Path | None = None) -> Path | None:
    base = (start or Path.cwd()).resolve()
    if base.is_file():
        base = base.parent
    for parent in [base, *base.parents]:
        if (parent / GHAGEN_YML_MARKER).is_file():
            return parent
    return None

# cli/_common.py:22
def _entrypoint_from_ghagen_yml(cwd: Path) -> Path | None:
    ghagen_yml = cwd / GHAGEN_YML_PATH   # no ancestor walk
    if not ghagen_yml.is_file():
        return None
    ...

# cli/_common.py:63
def _find_config(config: str | None) -> Path:
    if config:
        ...
    from_yml = _entrypoint_from_ghagen_yml(Path.cwd())  # cwd only
    if from_yml is not None:
        return from_yml
    for candidate in CONFIG_SEARCH_PATHS:
        path = Path(candidate)                          # cwd-relative
        if path.exists():
            return path
    ...
```

### 3.2 Python — after (one locator)

```python
# config.py: find_app_root unchanged

# cli/_common.py
def _entrypoint_from_ghagen_yml(root: Path) -> Path | None:
    ghagen_yml = root / GHAGEN_YML_MARKER
    if not ghagen_yml.is_file():
        return None
    ...  # body otherwise unchanged

def _find_config(config: str | None) -> Path:
    if config:
        ...
    root = find_app_root()
    if root is not None:
        from_yml = _entrypoint_from_ghagen_yml(root)
        if from_yml is not None:
            return from_yml
        for candidate in CONFIG_SEARCH_PATHS:
            path = root / candidate
            if path.exists():
                return path
    else:
        for candidate in CONFIG_SEARCH_PATHS:
            path = Path(candidate)
            if path.exists():
                return path
    ...  # error message unchanged
```

### 3.3 TypeScript — before (trio + two locators)

```
config.ts            findAppRoot, loadOptions (imports _yaml-config, _config-schema)
_yaml-config.ts       loadYamlConfig
_config-schema.ts     optionsSchema, ghagenYmlSchema

// cli/_common.ts:44
function entrypointFromGhagenYml(cwd: string): string | null {
  const ghagenYml = resolve(cwd, GHAGEN_YML_PATH);   // no ancestor walk
  ...
  config = ghagenYmlSchema.parse(data);              // parses entrypoint AND options
  ...
}

// cli/_common.ts:83
export function findConfig(cliFlag?: string, cwd = process.cwd()): string {
  if (cliFlag) { ... }
  const fromYml = entrypointFromGhagenYml(cwd);      // cwd only
  if (fromYml !== null) return fromYml;
  for (const candidate of CONFIG_SEARCH_PATHS) {
    const path = resolve(cwd, candidate);             // cwd-relative
    ...
  }
  ...
}
```

### 3.4 TypeScript — after (single file, one locator)

```
config.ts   findAppRoot, loadOptions, loadYamlConfig, optionsSchema,
            ghagenYmlSchema, GhagenOptions/GhagenYmlConfig types,
            GHAGEN_YML_MARKER

// config.ts
export function loadOptions(start?: string): GhagenOptions {
  const root = findAppRoot(start);
  if (root !== null) {
    const data = loadYamlConfig(resolve(root, GHAGEN_YML_MARKER));
    const parsed = optionsSchema.optional().parse(data.options); // options only
    if (parsed) return parsed;
  }
  return { auto_dedent: true };
}

// cli/_common.ts
import { GHAGEN_YML_MARKER, ghagenYmlSchema, loadYamlConfig, findAppRoot } from "../config.js";

function entrypointFromGhagenYml(root: string): string | null {
  const ghagenYml = resolve(root, GHAGEN_YML_MARKER);
  ...
  config = ghagenYmlSchema.parse(data);   // still full schema; this call site owns entrypoint
  ...
}

export function findConfig(cliFlag?: string, cwd = process.cwd()): string {
  if (cliFlag) { ... }                    // unchanged, cwd-relative
  const root = findAppRoot(cwd);
  if (root !== null) {
    const fromYml = entrypointFromGhagenYml(root);
    if (fromYml !== null) return fromYml;
    for (const candidate of CONFIG_SEARCH_PATHS) {
      const path = resolve(root, candidate);
      ...
    }
  } else {
    for (const candidate of CONFIG_SEARCH_PATHS) {
      const path = resolve(cwd, candidate);
      ...
    }
  }
  ...
}
```

## 4. Behaviour changes

Breaking changes are acceptable — ghagen is pre-1.0.

- **CLI-from-subdirectory now works.** `ghagen synth` (and `check`,
  `deps`, etc.) invoked from any descendant of the project root now
  resolves `.ghagen.yml`'s `entrypoint` and `CONFIG_SEARCH_PATHS`
  candidates via the same ancestor walk as `load_options`/`loadOptions`
  and the header's `{source_file}`. Previously this failed with "no
  config file found" from anywhere but the exact root directory.
- **`CONFIG_SEARCH_PATHS` search anchor changes** when a `.ghagen.yml` is
  present in an ancestor but the CLI runs from a subdirectory: candidates
  (`.github/ghagen_workflows.py`, `ghagen_config.py`, etc.) are now
  probed relative to the discovered root, not `cwd`. A project that
  happened to have a stray `ghagen_config.py` in a subdirectory _and_ a
  `.ghagen.yml` at the root will no longer pick up the subdirectory file
  by accident — this is a narrowing, not a widening, of what gets
  matched, and only affects the (already-fragile) implicit-filename
  fallback, not the explicit `entrypoint:` key or `--config`.
  When no `.ghagen.yml` exists anywhere in the ancestry, behavior is
  unchanged: `CONFIG_SEARCH_PATHS` is probed against `cwd`.
  `--config <path>` is unchanged in all cases (still `cwd`-relative).
- **TS: `loadOptions` no longer throws on a malformed `entrypoint` key.**
  A `.ghagen.yml` with e.g. `entrypoint: 42` previously broke
  `loadOptions()` (and therefore header rendering and `synth`/`check`
  even when `--config` was passed explicitly). After this change,
  `loadOptions` ignores `entrypoint` entirely; only `cli/_common.ts`'s
  entrypoint-resolution path validates and errors on it, matching
  Python's existing behavior.
- **TS: `_yaml-config.ts` / `_config-schema.ts` removed**; their exports
  move into `config.ts`. Nothing outside `config.ts` and
  `cli/_common.ts` imports them today (confirmed by grep), and neither
  file is re-exported from `index.ts`, so this is an internal-only move
  with no public API change.
- **Both ports:** `_entrypoint_from_ghagen_yml`/`entrypointFromGhagenYml`
  signature changes from `cwd`/raw-directory to `root`/discovered-root.
  Internal-only (not exported from either package's public surface —
  confirm before merge that neither leaked via `index.ts` /
  `__init__.py`; grep at time of writing shows only `find_app_root` /
  `findAppRoot`, `load_options`/`loadOptions`, and `GhagenOptions` are
  public).

## 5. Test plan

- **Unified locator (already largely covered, keep as regression base):**
  `packages/python/tests/test_paths.py` and
  `packages/typescript/src/paths.test.ts` already cover
  `find_app_root`/`findAppRoot` marker-at-start, walk-up-N-levels,
  no-marker, and file-as-start cases via `tmp_path`/`mkdtempSync` trees.
  No change needed here — `find_app_root`/`findAppRoot` themselves are
  not modified.
- **New: `_find_config`/`findConfig` unit tests** (neither port has a
  dedicated test file for this today — add
  `packages/python/tests/test_cli/test_common.py` and
  `packages/typescript/src/cli/_common.test.ts`):
  - Root `.ghagen.yml` with `entrypoint:` resolved when invoked with
    `cwd` = root (existing behavior, regression-guard).
  - Root `.ghagen.yml` with `entrypoint:` resolved when invoked with
    `cwd` = a nested subdirectory (**the fix** — this is the case with
    zero coverage today).
  - `CONFIG_SEARCH_PATHS` candidate at root found when invoked from a
    subdirectory, no `entrypoint:` key present.
  - No `.ghagen.yml` anywhere in the tree: `CONFIG_SEARCH_PATHS` probed
    against `cwd` only (unchanged fallback — must not start walking
    ancestors in this branch).
  - `--config <path>` bypasses discovery entirely regardless of `cwd`
    (unchanged).
  - TS only: malformed `entrypoint:` (wrong type) does not break
    `loadOptions()`/header rendering when accessed via a code path that
    never calls `entrypointFromGhagenYml` (e.g. `--config` given
    explicitly) — regression test for the coupling bug in §1.3.
- **CLI-from-subdir regression test** (both ports, at the CLI-command
  level, alongside existing `test_entrypoint_*` cases in
  `test_cli/test_main.py`): create a `tmp_path` with `.ghagen.yml`
  (`entrypoint: workflows/ci.py`) and `workflows/ci.py` at the root,
  `monkeypatch.chdir(tmp_path / "subdir")` (a directory with no config
  files of its own), run `ghagen synth`/`ghagen check`, assert success
  and correct output — mirrors the existing root-level tests but from
  one level down. TS needs an equivalent CLI-level test file under
  `packages/typescript/src/cli/` since none currently exists.
- Existing `_yaml-config.test.ts` cases move to wherever `loadYamlConfig`
  ends up (`config.test.ts` or equivalent) with the merge in §2; no
  behavioral changes to `loadYamlConfig` itself, so bodies are unchanged.

**Implementation deviation:** the TS CLI-level regression test
(`packages/typescript/src/cli/main.test.ts`) mocks `jiti`'s `createJiti`
rather than dynamically importing a written-to-disk fixture config module.
`jiti` loads modules through its own transform/loader — a genuine dynamic
import of a fixture that constructs `new App()` produces an `App` instance
from a _different_ module graph than the one `resolveAppFromModule`'s
`instanceof App` check runs against under Vitest's transform, so it
spuriously fails that check. This is a pre-existing property of the
`loadApp`/`resolveAppFromModule` design (unrelated to this spec — no CLI
test exercised `loadApp` before) and out of scope to fix here. The mock
still exercises the real, unmocked `findConfig`/`entrypointFromGhagenYml`
ancestor-walk logic end to end through `main()`, including asserting the
exact resolved entrypoint path passed to the (mocked) loader; only the
module-loading step itself is stubbed.

## 6. Acceptance criteria

- Exactly one ancestor-walking root locator per port
  (`find_app_root`/`findAppRoot`); `_find_config`/`findConfig` and
  `_entrypoint_from_ghagen_yml`/`entrypointFromGhagenYml` consume its
  result rather than deriving root independently from raw `cwd`.
- `ghagen synth`/`check`/`deps` succeed when invoked from a subdirectory
  of a project root that has `.ghagen.yml` with `entrypoint:` set, in
  both ports, with a passing regression test.
- TS: `config.ts`, `_yaml-config.ts`, `_config-schema.ts` collapsed into
  a single `config.ts`; `_yaml-config.ts`/`_config-schema.ts` deleted;
  `cli/_common.ts` imports updated accordingly; public exports in
  `index.ts` unchanged.
- TS: `loadOptions` parses only the `options` key; a malformed
  `entrypoint:` value does not raise from `loadOptions()`, with a
  regression test.
- Duplicate `GHAGEN_YML_PATH`/`GHAGEN_YML_MARKER` constants removed in
  both ports' `cli/_common` modules in favor of importing the single
  constant from `config`.
- All existing tests in `test_paths.py`, `paths.test.ts`,
  `test_cli/test_main.py`, `test_cli/test_deps.py`, and
  `_yaml-config.test.ts` (relocated) continue to pass unmodified in
  behavior (only import paths / parameter names change where noted
  above).

## 7. Conflicts

Touches `config`/`config.py`/`config.ts` and `cli/_common.py`/
`cli/_common.ts` in both ports. Per the architecture review's spec
split:

- No overlap with 0001/0003 (emitter `_base`) or 0002 (transforms/app) —
  those touch different modules entirely.
- No overlap with 0005 (engine JSON output / `check-deps`) in terms of
  file edits, but 0005 has a **soft dependency**: `cli/deps.py`
  (`from ghagen.cli._common import _find_config, _load_app`) and
  `cli/deps.ts` (`import { CliError, findConfig, loadApp } from
"./_common.js"`) both import from the module this spec modifies. The
  signature of `_find_config`/`findConfig` (parameters, return type,
  error behavior) must stay stable across both specs' implementation
  windows, or land this spec first — 0005 only needs `_find_config`'s
  external contract, not its internals, so parallel work is safe as long
  as that contract (accepts `config: str | None`, returns `Path`/raises
  `typer.Exit`; accepts `cliFlag?, cwd?`, returns `string`/throws
  `CliError`) doesn't change shape.
- Otherwise parallel-safe: no other spec in the 0001–0005 set touches
  `config.py`, `config.ts`, `_yaml-config.ts`, `_config-schema.ts`, or
  `cli/_common.py`/`cli/_common.ts`.
