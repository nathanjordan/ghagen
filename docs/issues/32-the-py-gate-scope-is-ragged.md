# The `py` gate scope is ragged, and `.github/ghagen_workflows.py` is in no gate at all

**Status:** resolved — found in round 3 while auditing issue 17's fix

Issue 17 moved `scripts/` into the `py` scope and proved it, but it extended only two of the three
Python gates. `scripts/fmt.sh` was never touched, even though the failure issue 17 cites as its own
evidence was a **`ruff format`** failure. And no gate of any kind sees
`.github/ghagen_workflows.py` — the file that generates every workflow under `.github/workflows/`.

## The coverage matrix, as it actually stands

| path                          | `lint.sh py` | `fmt.sh py` | `typecheck.sh py` |
| ----------------------------- | ------------ | ----------- | ----------------- |
| `packages/python/src/`        | yes          | yes         | yes               |
| `packages/python/tests/`      | yes          | yes         | **no** (issue 09) |
| `scripts/`                    | yes          | **no**      | yes               |
| `.github/ghagen_workflows.py` | **no**       | **no**      | **no**            |

Every gate passes explicit paths on the command line, so config alone cannot close any of these —
issue 17 already learned that for `pyright`, where an explicit path argument overrides `include`
rather than composing with it.

- `scripts/fmt.sh`: `uv run ruff format [--check] packages/python/src/ packages/python/tests/`
- `scripts/lint.sh`: `uv run ruff check [...] packages/python/src/ packages/python/tests/ scripts/`
- `scripts/typecheck.sh`: `uv run pyright packages/python/src/ scripts/`

## Measured, not inferred

Appended a syntactically valid, lint-clean, badly formatted function to **both**
`scripts/ghagen_schema/paths.py` and `.github/ghagen_workflows.py`:

```python
def _probe(  a ,b ):
    return (   a,b   )
```

- `./scripts/fmt.sh all` → **exit 0**
- `./scripts/lint.sh all` → **exit 0**
- `./scripts/typecheck.sh all` → **exit 0**
- `uv run ruff format --check scripts/ .github/ghagen_workflows.py` → `2 files would be reformatted`

Reverted; `git status --porcelain` clean on both paths.

## Why `.github/ghagen_workflows.py` matters more than its size suggests

It is the single source for all seven generated files under `.github/workflows/` and
`check-*/action.yml` — `uv run ghagen check-synced` proves the generated YAML matches it, but
nothing checks the generator's own source. It is also, per ADR-0003's reasoning, exactly the same
category as `scripts/ghagen_schema/`: dev tooling, not shipped package code, but Python source that
`ruff`/`pyright` should see. Issue 17 admitted that category and then enumerated one member of it.

## What a fix must do

1. Add `scripts/` and `.github/ghagen_workflows.py` to `scripts/fmt.sh`'s `py` scope.
2. Add `.github/ghagen_workflows.py` to `scripts/lint.sh` and `scripts/typecheck.sh`'s `py` scope,
   and to `[tool.ruff] src` / `[tool.pyright] include` in `pyproject.toml`.
3. Prove each gate now fails on an injected defect and passes after revert, per the repo standard.
4. Decide whether the enumerate-every-path approach is the right one at all. Four Python roots are
   now listed by hand across three scripts and two config tables, and the failure mode of that
   design is precisely this issue: a new root gets added to some of the ten places. A single
   `PY_PATHS` variable in `scripts/_gate.sh`, consumed by all three gates, would make the list
   impossible to desynchronise.
5. `packages/python/tests/` under `pyright` is **out of scope here** — that is issue 09, which
   covers both ports and has its own analysis.

## A filename note

`docs/issues/09-ts-typechecks-its-own-tests.md` has the H1 "Neither port type-checks its own tests".
The filename says the opposite of the issue. Worth renaming when 09 is picked up.

## Files

- `scripts/fmt.sh`, `scripts/lint.sh`, `scripts/typecheck.sh`, `scripts/_gate.sh`
- `pyproject.toml` — `[tool.ruff] src`, `[tool.pyright] include`
- `.github/ghagen_workflows.py`
- `docs/issues/17-scripts-dir-outside-every-gate.md` — the closed issue this is residue from

## Resolution

`scripts/_gate.sh` now names the repo's Python roots once, as `PY_PATHS`:

```sh
PY_PATHS=(
  packages/python/src/
  packages/python/tests/
  scripts/
  .github/ghagen_workflows.py
)
```

`PY_PATHS_TYPED` is derived from it by subtracting `packages/python/tests/`, rather than being a
second hand-written list, so a root added to `PY_PATHS` cannot miss the typecheck gate. `fmt.sh`,
`lint.sh` and `typecheck.sh` consume the arrays; none of them spells a path out any more. This is
point 4 of "What a fix must do": the enumerate-every-path design was the failure mode, and the ten
places are now one.

`pyproject.toml` was updated to match, so an editor or a bare `ruff`/`pyright` agrees with the
gates: `[tool.ruff] src` gained `.github`, and `[tool.pyright] include` gained
`.github/ghagen_workflows.py`.

### The coverage matrix now

| path                          | `lint.sh py` | `fmt.sh py` | `typecheck.sh py` |
| ----------------------------- | ------------ | ----------- | ----------------- |
| `packages/python/src/`        | yes          | yes         | yes               |
| `packages/python/tests/`      | yes          | yes         | **no** (issue 09) |
| `scripts/`                    | yes          | yes         | yes               |
| `.github/ghagen_workflows.py` | yes          | yes         | yes               |

The one remaining hole is deliberate and belongs to `docs/issues/09`, which covers both ports.

### pyright was excluding `.github/` silently

Adding the path to the command line was not enough. pyright's default `exclude` is
`["**/node_modules", "**/__pycache__", "**/.*"]`, and that last pattern swallows everything under
`.github/`. An explicit path argument does not override it -- it just analyses nothing:

```
$ uv run pyright --outputjson .github/ghagen_workflows.py
{'filesAnalyzed': 0, 'errorCount': 0, ...}
```

which prints `0 errors, 0 warnings, 0 informations` and exits 0. The gate would have been green and
empty, which is the same hole wearing a passing exit code. Only the injected-defect proof caught it.
`[tool.pyright] exclude` now restates the defaults without the blanket dot-glob and names the
dot-directories that must stay out.

### What the newly applied gates actually found

- **`ruff format`** -- 15 reformats in `.github/ghagen_workflows.py`. Generated YAML byte-identical
  (`ghagen check-synced` passes). `scripts/` was already clean under the formatter.
- **`ruff check`** -- 38 findings, all E501. `ruff format` cleared 15; two were plain Python (the
  `release-please` `outputs=` dict) and are wrapped properly. The remaining 21 are lines inside
  `run=` shell bodies whose width is set by the command being run: the schema-drift PR body is 222
  characters of one quoted argument, irreducible at any indentation. Those seven string literals
  carry a per-literal `# noqa: E501` (ruff scopes such a directive to the whole literal) with the
  reasoning recorded at the top of the file. E501 still applies to every line of Python in it, as
  does every other selected rule. No file-level or config-level suppression was added.
- **`pyright`** -- 172 errors on first real run. 171 were `reportCallIssue` "Arguments missing for
  parameters" at every model construction site, from `Field(None, ...)` in
  `packages/python/src/ghagen/models/`: pydantic treats a positional default and `default=` alike,
  but pyright's PEP 681 field-specifier handling only recognises the keyword form, so it synthesised
  an `__init__` where those fields were _required_. Nothing inside the type-checked scope
  constructed a model until the generator joined it, which is why the defect was latent. All 15
  sites now spell `default=` out, with a comment in `_base.py` saying why. The last error was
  `shell="bash"`: valid at runtime (pydantic coerces to the `ShellType` StrEnum) but not
  type-correct; the five call sites now pass `ShellType.BASH`, matching the file's existing
  `PermissionLevel.READ` style. Generated YAML unchanged.

### CI

No workflow change was needed. `lint-py` already runs `scripts/lint.sh py` and `scripts/fmt.sh py`,
and `typecheck-py` runs `scripts/typecheck.sh py`, so widening the scripts widened CI. `.github/`
is checked out by `actions/checkout` like everything else. `uv run ghagen check-synced` confirms the
generated YAML is unchanged by any of the above. `.pre-commit-config.yaml` shells the same two
scripts, so the hooks widened too.

### Proof, per newly covered path

Each defect injected, gate run, then reverted; `git status --porcelain` clean afterwards.

`.github/ghagen_workflows.py` under `fmt.sh py` -- appended `def _probe(  a ,b ):` / `return (   a,b   )`:

```
==> Ruff format (check)
unformatted: File would be reformatted
    --> .github/ghagen_workflows.py:1175:12
1 file would be reformatted, 120 files already formatted
fmt.sh py exit=1
```

`.github/ghagen_workflows.py` under `lint.sh py` -- appended `import os`:

```
==> Ruff check
E402 Module level import not at top of file
    --> .github/ghagen_workflows.py:1175:1
F401 [*] `os` imported but unused
    --> .github/ghagen_workflows.py:1175:8
Found 2 errors.
lint.sh py exit=1
```

`.github/ghagen_workflows.py` under `typecheck.sh py` -- appended `def _probe() -> int: return "not an int"`:

```
==> Pyright (python)
  .github/ghagen_workflows.py:1176:12 - error: Type "Literal['not an int']" is not assignable to return type "int"
    "Literal['not an int']" is not assignable to "int" (reportReturnType)
1 error, 0 warnings, 0 informations
typecheck.sh py exit=1
```

`scripts/` under `fmt.sh py` -- appended the same badly formatted function to
`scripts/ghagen_schema/paths.py`:

```
==> Ruff format (check)
unformatted: File would be reformatted
  --> scripts/ghagen_schema/paths.py:42:12
1 file would be reformatted, 120 files already formatted
fmt.sh py exit=1
```

The pyright proof is the load-bearing one: before the `exclude` fix, that same injected error
produced `0 errors, 0 warnings, 0 informations` and exit 0.

### Not done here

- `packages/python/tests/` under pyright -- `docs/issues/09`, deliberately untouched.
- `docs/issues/09-ts-typechecks-its-own-tests.md` still has the H1 "Neither port type-checks its own
  tests", contradicting its own filename. Not renamed, to avoid colliding with 09's own agent.
