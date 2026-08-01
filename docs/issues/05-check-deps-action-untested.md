# check-deps action has no CI exercise

**Status:** closed by proposal 18 — from exploration + round 1 CI review

`check-synth` is exercised by CI's test-action job; `check-deps/action.yml` (PR/issue shell logic,
branch naming, dedup via gh pr/issue list, label args) has zero automated coverage. Add a CI job
exercising it in --check mode against a fixture, or at minimum a dry-run smoke.

## Resolution

Three layers, because the gap had three parts and no one layer covers them all.

1. **Most of the shell was deleted rather than tested.** The decision the shell
   was making — apply bumps? refresh the lockfile? open a PR or an issue? — moved
   into `ghagen deps update`, which is a CLI command with unit tests in both
   ports. `pin/plan.py` and `pin/plan.ts` are pure functions covered by
   `test_plan.py` / `plan.test.ts`. What is left in YAML is a `case` on
   `steps.plan.outputs.action` and two `gh` calls.

2. **The generated YAML is asserted as text.**
   `packages/python/tests/test_integration/test_shipped_actions.py` reads the
   shipped `action.yml` of every action in the repo and asserts on it directly:
   no `|| true`, no `python3`, no `deps pin`, no `steps.detect.*`, the six
   `outputs:` keys each with a `value`, and the `source` / `dry-run` inputs.
   `ghagen check-synced` proves the file matches the model; this proves the
   model is right.

3. **The action is executed by CI.**
   - `ci.yml`'s `test-action` job runs `uses: ./check-deps` with
     `dry-run: 'true'` against `fixtures/actions/all_pinned/`, then asserts the
     plan outputs. Offline by construction — every ref in that fixture is a SHA,
     so no ref is pinnable and `upgrade()` returns before any HTTP — which is
     why it can sit in a job with no `permissions:` and no token.
   - `check-deps-smoke.yml` runs weekly and on `workflow_dispatch` against
     `fixtures/actions/lockfile_none/`, a `lockfile=None` project with a
     floating ref. That is the H7 reproducer: the old action cascaded into
     `ghagen deps pin --update` there, which exits 1, aborting the run under
     `set -euo pipefail`. The smoke asserts exit 0 and
     `refresh_lockfile=false`.

Neither workflow had run at the time proposal 18 landed — no local gate
executes a GitHub Actions workflow. The first real run is the first execution
of either.
