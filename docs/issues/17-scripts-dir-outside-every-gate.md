# `scripts/` is inside no gate's checked paths

**Status:** open — from round 2, found by proposal 23 while rewriting a file in that directory

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
