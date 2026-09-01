# No PR-time docs gate exists

**Status:** closed — folded the docs build into CI's `lint-docs` job, renamed it `docs`

`.github/workflows/docs.yml:4-8` triggers on push-to-`main` and `workflow_dispatch` only. Nothing
runs the docs toolchain before a merge.

Consequence for round 2: proposal 22's TypeDoc byte oracle is a **pre-merge acceptance step run by
hand**, not a standing gate. If the `_docs-api-*.ts` entry points drift after 22 lands, `main` breaks
and the first signal is the post-merge docs build.

Making it standing needs a new PR-triggered workflow. Nobody owned that in round 2. Note the cost
interaction: the docs npm toolchain is heavy, and round 2's proposal 23 stopped it running
unconditionally on every commit (which closed the old `docs/issues/07`, now deleted). A naive PR
gate re-introduces that cost at PR time, so scope the trigger to paths that can actually change
TypeDoc output rather than running it on every PR.

## Resolution

The "new workflow" framing above was stale by the time this was picked up. `ci.yml`'s `lint-docs`
job (`.github/ghagen_workflows.py`) already ran on every pull request and already paid for
`npm ci` in `docs/` — the heavy part proposal 23 was protecting against. The only thing missing was
`npm run build` itself, plus `npm ci` for `packages/typescript/` (TypeDoc documents that package).
So instead of a new workflow, the job was extended and renamed `docs` (`.github/ghagen_workflows.py`,
regenerated into `.github/workflows/ci.yml` — the file is generated, never hand-edited):

```
docs:                       # was: lint-docs
  Checkout / Setup Node 24
  npm ci   (packages/typescript)   # NEW
  npm ci   (docs)                  # already there
  scripts/lint.sh docs             # already there
  scripts/fmt.sh docs              # already there
  npm run build (docs)             # NEW — the actual gate
  timeout-minutes: 20              # was 10
```

Lint and format checks stay ordered before the build: `npm run build` writes generated TypeDoc
markdown into `docs/src/content/docs/typescript/api/` (gitignored), and `oxfmt`, unlike `oxlint`,
does not honor `.gitignore` — checking format after generating would trip over content the build
itself produced.

**`docs.yml` is unchanged.** It still triggers on push-to-`main` plus `workflow_dispatch` and still
builds-then-deploys to Pages. This issue adds a pre-merge gate; it does not move where the site
actually gets published, and there was no reason to touch the deploy path.

**Local gate now matches.** `scripts/lint.sh docs` covered lint/format but nothing built the site
locally, so a contributor could pass every local gate and still fail CI on this — the exact
asymmetry this repo tracks as a defect class. `scripts/typecheck.sh` gained a `docs` scope
(`py ts docs`, AGENTS.md's gate table updated) that runs the same `npm run build`: there is no
separate "check without building" step for the docs site, so the build **is** the type check here,
same as CI. Because that build writes the same gitignored generated content noted above, the new
scope cleans it up in an `EXIT` trap regardless of pass or fail, so it stays read-only like the
other gates (`docs/.astro/`, `docs/dist/`, `docs/src/content/docs/typescript/api/` — verified
`scripts/typecheck.sh all` followed by `scripts/fmt.sh all` both pass, in the documented gate
order, with the tree byte-identical afterward).

**The gate was proven against a deliberate break, and the result reshapes what it's proven to
catch.** `docs/astro.config.mjs`'s `sharedTypeDocConfig` sets `skipErrorChecking: true`. Three
breaks were tried in `packages/typescript/src/_docs-api-job.ts`:

- Re-exporting a symbol that does not exist on `./models/job.js` (`thisSymbolDoesNotExist`) — TS2305.
- Re-exporting from a module path that does not exist (`./models/job-renamed-does-not-exist.js`) — TS2307.
- Outright invalid syntax appended to the file.

All three left `npm run build` in `docs/` exit **0** — `skipErrorChecking` suppresses exactly these
diagnostics, and the affected exports were silently dropped from the generated site (`job`,
`strategy`, `matrix`, `environment` vanished from `docs/dist/typescript/api/job/functions/` with no
warning). So the build does **not** catch the entry-point-content drift this issue's premise
described — but all three of those breaks are already caught pre-merge by the pre-existing,
unconditional `typecheck-ts` job (`tsc --noEmit` over `packages/typescript/src/`, which
`_docs-api-*.ts` lives under), so nothing regressed: that gate already ran on every PR before this
change.

What the build _does_ catch, proven the same way: deleting an entry-point file outright
(`packages/typescript/src/_docs-api-job.ts`, config still pointing at it in
`docs/astro.config.mjs`) makes `npm run build` fail hard — `starlight-typedoc-plugin` logs
`Unable to find any entry points` and astro aborts the build with a non-zero exit. That is a real
class of drift `typecheck-ts` cannot see (astro.config.mjs's entry-point paths are not typechecked
by `packages/typescript`'s own `tsconfig.json`), and it is now caught pre-merge. General docs-site
build breakage (broken content collections, bad frontmatter, sitemap/Pagefind failures) is caught
the same way and was not caught by anything before.

Both breaks were reverted after observing the result; `git status` confirms the working tree
returned to clean.

**Gate numbers** (branch point, before and after — no test files were touched):
pytest 913 passed, vitest 965 passed (45 files). `./scripts/typecheck.sh all`,
`./scripts/lint.sh all`, `./scripts/fmt.sh all`, `./scripts/test.sh all`,
`uv run ghagen check-synced`, `uv run ghagen deps check-synced`, and
`PYTHONPATH=scripts uv run python -m ghagen_schema check` all pass, run in that order.
