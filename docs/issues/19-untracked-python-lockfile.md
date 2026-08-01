# The Python build is not reproducible: `uv.lock` is untracked

**Status:** open — from round 2. Surfaced by three separate implementation worktrees

`uv.lock` is gitignored (`.gitignore:31`; `git ls-files uv.lock` returns nothing).
`packages/typescript/package-lock.json` **is** tracked. The two ports therefore ship different
reproducibility guarantees, and nothing in the repo says so.

## LIVE. It broke three worktrees this round

Round 2 dispatched sixteen implementation agents into fresh git worktrees. A fresh worktree has no
`uv.lock`, so `uv sync` re-resolves from `pyproject.toml`. Three agents (proposals 19, 14, 13) hit
the same wall before making a single edit:

```
ModuleNotFoundError: No module named 'click'
```

Four `test_cli/` modules failed to collect. The cause was a manifest that declared `typer>=0.12`
while `cli/main.py` imported `click`: a fresh resolve picked typer 0.27.0, which vendors click as
`typer._click` and drops the top-level dependency. The checkout's _untracked_ `uv.lock` happened to
pin typer 0.24.1 / click 8.3.2, so it worked on one machine and nowhere else.

Two of the three worked around it by copying the parent checkout's `uv.lock` in and running
`uv sync --frozen`. One did not, diagnosed the environment instead of the manifest, and landed
`from typer._click.exceptions import …` — which then failed on the integration tree and had to be
reverted.

**The specific import is fixed** (ADR-0009: `click>=8.2.1` declared, `typer>=0.12,<0.25` capped,
guarded by `tests/test_declared_dependencies.py`). **The reproducibility gap is not.** The manifest
is now honest about _what_ is required; it still does not fix _which versions_ a build gets. Any
future dependency whose upstream reshapes itself reproduces this exact incident.

## It happened a second time in the same round, on the same dependency

A later worktree (proposal 17's) resolved **click 8.4.2** and arrived with a red baseline. click
reworded its usage errors in 8.4 — `No such option: --bogus` became `No such option '--bogus'.` —
and two cases in `tests/test_cli/test_exit_codes.py` asserted the old prose verbatim.
`click>=8.2.1` has no ceiling, so both wordings are manifest-legal and which one a checkout gets is
decided by resolution date.

That one was a test defect and is fixed by asserting the error kind and the offending token instead
of click's punctuation; the suite passes under 8.3.2 and 8.4.2 both, verified with
`uv run --with 'click==8.4.2'`. **No ceiling was added** — capping a direct dependency to keep a
string literal alive is the wrong trade, and unlike the `typer<0.25` cap there is no removed API
behind it.

It is listed here because the _shape_ is the point: two incidents, one round, one dependency, both
found by an agent losing time to a red baseline rather than by any gate. Both would have been
impossible with a tracked lockfile, and the second would have been caught the week upstream shipped
by a scheduled fresh-resolve CI run. That is options 1 and 2 below, and this is the second data
point for each.

## Why the obvious fix is a real decision, not a chore

The convention that libraries do not commit lockfiles is genuine — a lockfile in an installed
package is ignored by consumers' resolvers and can mislead contributors into thinking it constrains
downstream. ghagen is published to PyPI, so it is on the library side of that convention.

But ghagen is also a repo with a CI matrix, a byte-oracle test suite whose fixtures assert exact
emitted output, and a sixteen-worktree development workflow. It behaves like an application at
development time. That is precisely the case the convention does not cover well, and it is why
`package-lock.json` is tracked on the other side of the same repo.

The decision worth making is which of these the repo wants — not which is generically correct:

1. **Track `uv.lock`.** Matches `package-lock.json`, makes every worktree and CI run identical,
   ends this class of incident. Cost: a lockfile in the sdist unless excluded, and dependency-update
   churn in the diff.
2. **Keep it untracked and make CI resolve fresh, on a schedule.** Then unbounded constraints break
   in CI on the day upstream changes, not in a developer's worktree three months later. Cost: a
   red build caused by someone else's release.
3. **Keep it untracked and rely on the manifest test.** `tests/test_declared_dependencies.py`
   already catches _undeclared_ imports. It does **not** catch an upstream that reshapes a package
   ghagen already declares — the typer vendoring would have sailed past it if click had never been
   imported directly.

Option 1 and option 2 are complementary, not alternatives. Option 3 alone is what the repo has now,
and it is the weakest of the three.

## Whatever is chosen, do this

Say it out loud somewhere a contributor reads. `CONTRIBUTING`/`README` currently do not mention that
a fresh Python environment may not match anyone else's, and the developer-facing symptom is an
import error in an unrelated subsystem.

## Files

- `.gitignore:31`
- `pyproject.toml` — the constraint set that is now load-bearing
- `packages/typescript/package-lock.json` — tracked; the asymmetry
- `packages/python/tests/test_declared_dependencies.py` — the partial guard that exists today
- `docs/adr/0009-click-is-a-declared-dependency.md` — the incident this came from
- `.github/workflows/` — where option 2 would live

## Why it was deferred

Found mid-round while unblocking implementation agents. The import break was fixed inline because it
was blocking; committing or not committing a lockfile is a repo-policy call with an sdist-packaging
consequence, and it has no business being decided as a side effect of a refactor round.
