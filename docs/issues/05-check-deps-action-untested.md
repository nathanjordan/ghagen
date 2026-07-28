# check-deps action has no CI exercise

**Status:** open — from exploration + round 1 CI review

`check-synth` is exercised by CI's test-action job; `check-deps/action.yml` (PR/issue shell logic,
branch naming, dedup via gh pr/issue list, label args) has zero automated coverage. Add a CI job
exercising it in --check mode against a fixture, or at minimum a dry-run smoke.
