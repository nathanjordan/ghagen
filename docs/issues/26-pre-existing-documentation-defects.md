# Pre-existing documentation defects (predate round 2)

**Status:** open — from round 2. Found by the whole-branch adversarial review; all predate the round.
The cookbook bullet is resolved (see below); the auto-dedent bullet is closed as a duplicate of
`docs/issues/13`; the remaining three bullets (README, `AGENTS.md`, `--outdir`) are still open.

These were surfaced by round 2's review but are not round-2 regressions — each is verifiable on
`main`. They are filed rather than fixed because none of them fell inside any proposal's allowlist,
and a docs sweep is its own change with its own review.

- ~~**The cookbook imports helpers that do not exist.** A reader following it gets an `ImportError`
  on the first snippet.~~ **Resolved.** `checkout`, `setup_python`/`setupPython`, `cache`,
  `download_artifact`/`downloadArtifact`, and `upload_artifact`/`uploadArtifact` were never
  implemented in either port; the repo owner decided to rewrite the snippets against the real API
  (`Step(uses=...)` / `step({ uses: ... })`) rather than add the helpers. All ~25 call sites in
  `docs/src/content/docs/guides/cookbook.mdx` (Python and TypeScript) now use `actions/checkout@v4`,
  `actions/setup-python@v5`, `actions/cache@v4`, `actions/upload-artifact@v4`, and
  `actions/download-artifact@v4` directly, matching the versions already used elsewhere in the repo
  (`ghagen init`'s scaffold, `dry-patterns.mdx`). The prose describing the removed helpers'
  behavior (e.g. the `cache()` kwargs, `upload_artifact`/`download_artifact`) was rewritten to
  describe the real API instead. Every Python and TypeScript snippet in the file was extracted and
  executed against the built package to confirm it runs. Two unrelated pre-existing corruptions in
  the same file (`runs*on`, `if*=`, `with\_=` — stray `*`/`\` where `_` belonged, breaking Python
  syntax) were fixed in passing since they sat in sections already being rewritten and would
  otherwise have kept those snippets broken. Fixing this surfaced a related formatter defect:
  `oxfmt` also mangles fenced **Python/TypeScript** blocks in this file (de-indenting them and
  turning `_` next to a word character into `*`/`\_`), not just the `yaml` blocks `docs/issues/18`
  documents — see that issue for the broader writeup; `./scripts/fmt.sh docs` now flags this file
  and the corrupted rewrite was deliberately not accepted.
- ~~**Auto-dedent is documented as Python-only; TypeScript defaults it on too.**~~ Closed as a
  duplicate — this question is already tracked on its own in `docs/issues/13` (the `to_data` /
  `to_yaml` `auto_dedent` default disagreement), so it does not need separate action here.
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

The README and cookbook items were the highest priority of the five: they are what a new user
executes first. The cookbook now runs cleanly; the README bullet is still open.
