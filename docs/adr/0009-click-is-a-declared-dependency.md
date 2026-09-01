# click is a declared dependency, and typer is bounded below its vendoring

**Status:** accepted (2026-07-31)

`pyproject.toml` declares `click>=8.2.1` directly and bounds `typer>=0.12,<0.25`. The Python port
imports `click.exceptions` in `cli/main.py`; that import is a first-class dependency of ghagen, not
an incidental reach through typer's own requirements.

## Why

`main()` runs the Typer command with `standalone_mode=False` so it can **return** an exit code
rather than let click call `sys.exit` (ADR-adjacent: proposal 19). Under that mode click's
`ClickException` and `Abort` escape to the caller, so `main()` must name those classes. They come
from click.

Until this change ghagen declared only `typer>=0.12` and imported click anyway, relying on typer to
drag it in. Two facts made that quietly wrong:

- **typer 0.25 vendors click** as `typer._click` and no longer depends on the top-level
  distribution. `uv pip compile` on the old `typer>=0.12` resolves **typer 0.27.0 with no `click`
  entry at all**, so `from click.exceptions import Abort, ClickException` raises
  `ModuleNotFoundError` and the four `test_cli/` modules fail to collect.
- **`uv.lock` is gitignored** (`.gitignore:31`, `git ls-files uv.lock` is empty). The only thing
  holding the old resolution together was an untracked file on one machine. Three separate
  round-2 implementation worktrees resolved fresh and hit the break before making a single edit.

The manifest is the artefact a fresh checkout reads. It has to be true on its own.

## Consequences

**Do not "modernize" to `typer._click`.** It is typer's private vendored copy. Importing it makes
ghagen depend on a name typer does not publish, and under any typer that still uses top-level click
the vendored exception classes are _different class objects_ from the ones actually raised — so
`except ClickException` silently stops matching and every usage error becomes an unhandled
traceback. That failure is invisible to a type checker and to any test that does not assert the
exit code of a _malformed_ invocation.

**Raising the typer ceiling is a real migration, not a bump.** It means choosing how `main()`
obtains the escaping exception types across a vendoring boundary. The ceiling exists so that choice
is made deliberately, with the resolver refusing the upgrade until someone does.

**The gitignored `uv.lock` is a separate, still-open problem.** This ADR makes the manifest honest;
it does not make the Python build reproducible. `packages/typescript/package-lock.json` is tracked
and `uv.lock` is not, so the two ports have different reproducibility guarantees.
See `docs/issues/19-untracked-python-lockfile.md`.

## Amendment (2026-08-31): `uv.lock` is now tracked

`uv.lock` is committed and CI's `uv sync` steps now pass `--locked`, so a stale lockfile fails CI
instead of silently re-resolving. `packages/typescript/package-lock.json` and `uv.lock` now carry
the same reproducibility guarantee. See `docs/issues/19-untracked-python-lockfile.md`'s Resolution
section. This does not relax anything above: the manifest still has to be honest on its own, because
`uv sync -U`/a lockfile refresh re-resolves against it, and the typer ceiling still guards the
vendoring boundary.
