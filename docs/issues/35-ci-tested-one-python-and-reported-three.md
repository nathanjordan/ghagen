# CI tested one Python and reported three

**Status:** closed -- both defects fixed in the same commit. Found by the first CI run in 49
commits, on PR #50

Every gate was green locally. The first push in 49 commits turned `Test (Python 3.12)` red and
fail-fast cancelled 3.11 and 3.13. Two separate defects, both of the round's class -- something
stating an invariant nothing enforced -- and the second was only visible because the first failed.

## 1. Four rendering tests depended on an undeclared environment variable

`test_error_rendering_is_typers_not_clicks` asserts that a usage error still carries Typer's rich
panel rather than click's plain renderer, by looking for fragments (`--version`, `--bogus`,
`Option '--outdir' requires an argument.`) in `capsys`'s `err`.

Rich styles a usage error's tokens individually. With colour on, an option flag arrives as

```
\x1b[1;2;34m-\x1b[0m\x1b[2;34m-version\x1b[0m
```

so `"--version" in err` is **false on the very output that renders it correctly**. The box-drawing
assertions (`╭─`, `╰─`) pass either way, which is why the failure looked like a content bug rather
than a styling one.

Colour is on whenever rich sees a reason, and `CI=true` -- set by GitHub Actions on every runner --
is one of those reasons. Locally it is unset, so all four passed.

Reproduced locally in one command:

```
$ CI=true uv run pytest packages/python/tests/test_cli/test_exit_codes.py -q
4 failed, 17 passed
$ uv run pytest packages/python/tests/test_cli/test_exit_codes.py -q
21 passed
```

**Fix.** A `_plain()` helper strips SGR escapes before the fragment assertions. The test now passes
identically with colour off, with `CI=true`, and with `FORCE_COLOR=1`, and its failure output is
readable instead of escape soup. Proven still load-bearing: changing one expected fragment to
`--bogus-NOT-PRESENT` fails the case.

`CI=true` was run against the **whole** suite in both ports to check for further environment
dependence: exactly those four, and vitest unaffected (1055 passed).

## 2. The `test-py` matrix ran the same interpreter three times, and it was none of the three

The failing job is named `Test (Python 3.12)`. Its own warning output names the interpreter:

```
/home/runner/work/ghagen/ghagen/.venv/lib/python3.14/site-packages/typer/__init__.py:24
```

`actions/setup-python` installs the matrix interpreter and puts it on `PATH`, but nothing in the job
uses it. `scripts/test.sh py` runs `uv run pytest`, and uv resolves its own interpreter: `--python`
outranks `UV_PYTHON`, which outranks `.python-version` -- and `.python-version` in this repo says
`3.14`. None of the three legs ran the version it advertised. All three ran 3.14.

So the matrix cost three runners per push and bought nothing, and the repo's `requires-python =
">=3.11"` claim had never been executed by any gate.

Measured directly:

```
$ UV_PYTHON=3.11 uv run python -c 'import sys; print(sys.version_info[:2])'   -> 3.11
$ UV_PYTHON=3.12 ...                                                          -> 3.12
$ UV_PYTHON=3.13 ...                                                          -> 3.13
$ (unset)                                                                     -> 3.14
```

**Fix**, in `.github/ghagen_workflows.py` (the generated `ci.yml` is never hand-edited):

- `actions/setup-python` **removed** -- it was the step that created the illusion, and uv provisions
  interpreters itself.
- `env: {UV_PYTHON: "${{ matrix.python-version }}"}` on the job, which outranks `.python-version`
  and is read by both `uv sync --locked` and the `uv run` inside `scripts/test.sh`.
- A new **`Assert interpreter`** step between Sync and Test, comparing `sys.version_info[:2]`
  against the matrix value and failing with `matrix says $want, uv ran $got -- the matrix is not
enforced`. This is the part that matters: a matrix nothing verifies is a matrix that can silently
  stop meaning anything, which is precisely what had happened. The repo's standard is that a claim
  must fail when it stops being true.

**The code was fine.** The suite was run locally under all four interpreters before the fix landed:
**995 passed** on 3.11, 3.12, 3.13 and 3.14 alike. The defect was never in the port -- it was that
three years of Python support were being asserted by a job that could not have detected their loss.

## Why local gates could not have caught either

Both are environment divergences, not code defects, and both are invisible from a developer
machine: `CI` is unset locally, and `.python-version` makes the local interpreter the only one
anyone ever runs. That is an argument for pushing more often than once per 49 commits, not for a
new local gate -- a local gate that simulates CI is one more thing that can drift from CI.

## Files

- `packages/python/tests/test_cli/test_exit_codes.py` -- `_plain()`, applied at the one `readouterr`
- `.github/ghagen_workflows.py` -- the `test-py` job; regenerate with `uv run ghagen synth`
- `.python-version` -- `3.14`, unchanged and still correct for local work
