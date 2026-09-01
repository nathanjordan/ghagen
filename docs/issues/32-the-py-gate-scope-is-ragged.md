# The `py` gate scope is ragged, and `.github/ghagen_workflows.py` is in no gate at all

**Status:** open — found in round 3 while auditing issue 17's fix

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
