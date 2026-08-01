# No PR-time docs gate exists

**Status:** open — from round 2

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
