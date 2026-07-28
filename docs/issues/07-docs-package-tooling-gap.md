# docs package: oxlint/oxfmt not installed locally

**Status:** open — recurring agent friction in round 1

`scripts/lint.sh ts` / `scripts/fmt.sh` run oxlint/oxfmt in `docs/` where the binaries are absent
unless `npm ci --prefix docs` ran; every local/agent environment hits "command not found". Either
guard the docs step on binary presence, or document `npm ci --prefix docs` as a setup step.
