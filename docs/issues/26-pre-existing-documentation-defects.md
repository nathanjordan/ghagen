# Pre-existing documentation defects (predate round 2)

**Status:** open — from round 2. Found by the whole-branch adversarial review; all predate the round

These were surfaced by round 2's review but are not round-2 regressions — each is verifiable on
`main`. They are filed rather than fixed because none of them fell inside any proposal's allowlist,
and a docs sweep is its own change with its own review.

- **The cookbook imports helpers that do not exist.** A reader following it gets an `ImportError` on
  the first snippet.
- **Auto-dedent is documented as Python-only; TypeScript defaults it on too.** Related to
  `docs/issues/13`, which records the `to_data` dedent default as a separate open question — check
  whether one decision closes both.
- **The README example's shown output does not match what the code emits.** The README is the first
  thing a reader runs.
- **`AGENTS.md` describes a `ghagen.toml`** that the repo does not use.
- **`--outdir workflows` examples produce a config outside `CONFIG_SEARCH_PATHS`**, so the documented
  follow-up `ghagen synth` cannot find the config the example just wrote. Both CLI reference pages.

## Why they are grouped

All five are "run the documented thing, get a different result" — the class a docs gate catches
mechanically. `docs/issues/12` (no PR-time docs gate) is the structural fix; this issue is the
backlog that gate would have prevented from accumulating. Fixing these five without landing 12 means
round 3 files the same kind of list.

The README and cookbook items are the highest priority of the five: they are what a new user
executes first, and both currently fail.
