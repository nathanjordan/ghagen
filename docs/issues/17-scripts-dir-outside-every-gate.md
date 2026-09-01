# `scripts/` is inside no gate's checked paths

**Status:** closed — from round 2, found by proposal 23 while rewriting a file in that directory

Neither Python gate covers `scripts/`:

- `pyproject.toml:61` — pyright `include = ["packages/python/src"]`
- `pyproject.toml:51` — ruff `src = ["packages/python/src"]`; the lint gate invokes it on
  `packages/python/src/ packages/python/tests/`

So `scripts/ghagen_schema/` — the schema sync/generate/check pipeline that proposal 08 built in
round 1, and that `scripts/lint.sh meta` now runs on every commit — is neither linted nor
type-checked by anything.

**Proof it was already hiding a real failure:** `scripts/ghagen_schema/__main__.py` failed
`ruff format --check` (docstring indentation) and nobody could have known. Fixed on the round-2
integration branch as `5396a95`; the _reason_ it went unnoticed is what this issue is about.

Proposal 23 deliberately did not widen the gate paths — `pyproject.toml` was outside its
Files-involved table, and widening a gate in the same change that rewrites the files the gate would
newly cover makes the two indistinguishable.

**Remedy:** add `scripts` to pyright's `include` and to ruff's invocation, then fix whatever falls
out. Do it as its own change, on a tree where `scripts/` is otherwise untouched.

## Resolution

`scripts/` now sits in the `py` scope, not `meta`. `meta` (`scripts/lint.sh meta`) is the
language-neutral scope -- it _runs_ `ghagen_schema` as a program (`python -m ghagen_schema check`)
and checks repo-level consistency; it was never meant to also be the place that lints and
type-checks that program's own source. `py` is exactly "the ruff/pyright scope for Python source,"
and `scripts/ghagen_schema/` is Python source (dev tooling per ADR-0003, not shipped package code,
but source all the same) -- so it belongs where `packages/python/src/` and `tests/` already are.

1. `pyproject.toml`: `[tool.ruff] src` and `[tool.pyright] include` both gained `"scripts"`,
   each with a comment pointing at this issue.
2. `scripts/lint.sh` and `scripts/typecheck.sh`: the `py`-scope `ruff check` / `ruff check --fix`
   and `pyright` invocations gained a trailing `scripts/` argument. Config alone was not enough --
   both gates pass explicit paths on the command line, and for `pyright` an explicit path argument
   overrides `include` rather than composing with it.
3. `AGENTS.md`'s scope table note for `py`/`ts`/`docs` now says the `py` scope also covers
   `scripts/ghagen_schema/` and why.

**Fallout, and why it was small.** `scripts/ghagen_schema/` itself was already clean under both
tools -- the docstring-indentation `ruff format` failure this issue's proof cites was already fixed
separately (`5396a95`) before this change landed. The only fallout was indirect: adding `"scripts"`
to `[tool.ruff] src` makes ruff's import sorter (`I001`) treat `ghagen_schema` as first-party
(it has a `src` root now) instead of third-party, which reordered the `ghagen_schema` import line
relative to third-party imports in 12 files under `packages/python/tests/` that import it (e.g.
`test_schema/test_fetch.py`, `test_integration/conftest.py`, `test_pin/test_lockfile.py`). All 12
were mechanical reorders applied with `ruff check --fix`; nothing else changed, and pyright reported
zero errors on `scripts/` from the start.

**Proof the gates now really cover `scripts/`.** In `scripts/ghagen_schema/paths.py`, temporarily
added an assignment `deliberate_type_error: int = "not an int"` plus an unused `import os` inside
`repo_root()`:

- `./scripts/typecheck.sh all` failed: `pyright` reported
  `reportAssignmentType: "Literal['not an int']" is not assignable to declared type "int"` at
  `scripts/ghagen_schema/paths.py:20`, exit 1.
- `./scripts/lint.sh all` failed: `ruff check` reported `F841` (unused local), `E501` (line too
  long), and `F401` (unused import `os`), exit 1.

Reverted both; `./scripts/typecheck.sh all` and `./scripts/lint.sh all` returned to exit 0 with the
tree byte-identical to before the probe (`git status --porcelain` clean on that file).

**Gate numbers after the fix** (same branch point as before this change): `pytest` 913 passed;
`vitest` 965 passed (45 files) -- unchanged by this issue; `./scripts/typecheck.sh all`,
`./scripts/lint.sh all`, `./scripts/fmt.sh all`, `uv run ghagen check-synced`,
`uv run ghagen deps check-synced`, and `PYTHONPATH=scripts uv run python -m ghagen_schema check`
all pass.

`scripts/fmt.sh` (the `ruff format` gate) was left untouched -- out of this issue's stated scope
(pyright `include` and the ruff _lint_ invocation only) and `scripts/` was already
`ruff format --check`-clean, so there is no live failure hiding behind it today. It is the same
gap in shape, though: `scripts/fmt.sh py` still only checks `packages/python/src/` and
`packages/python/tests/`. Worth a follow-up if the repo wants every ruff-backed gate symmetric.
