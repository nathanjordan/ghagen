# Modules describing responsibilities they do not have

**Status:** open — from round 2. Found by the whole-branch adversarial review (docs-vs-code)

Round 2's theme was interfaces claiming invariants their implementations did not hold. These are the
same defect in prose: a module's stated responsibility and its actual one differ, and nothing gates
the difference. Each is a small edit; the reason to collect them is that they mislead exactly the
reader who is trying to find where something lives.

Two were re-verified by direct read while triaging; the rest come from the review and should be
re-checked against the tree before editing.

## Verified

**`packages/typescript/CONTEXT.md:39-41` gives `comment-geometry.ts` a responsibility it disclaims.**
CONTEXT.md says comment geometry — "the end-of-line gutter (`EOL_GUTTER`, 2 columns) **and the
block-comment column**" — is a named module. `comment-geometry.ts:29-32` says the opposite in as many
words: "Block-comment _columns_ are not this module's business in TypeScript — the `yaml` backend
indents a `commentBefore` to its node automatically. (The Python peer must own them; ruamel does
not.)" The module is right and the map is wrong; the asymmetry between the ports is the interesting
part and CONTEXT.md flattens it.

**`packages/python/src/ghagen/emitter/nodes.py:3-7` claims comment attachment lives "here and nowhere
else".** `document.py:46` calls `attach_model_comment` directly for the document root's own comment.
Either the claim needs the exception written into it, or the root's attachment should route through
`nodes.py` so the claim becomes true. Prefer the latter if it is cheap — a module that really is the
single home is worth more than an accurate caveat.

## Reported by review, verify before fixing

- **`transport-contract.ts:28` names two different "sole callers"** in one docstring.
- **`AGENTS.md:49-56` overstates what a fresh checkout installs** — `pre-commit` is not in the dev
  dependencies, so following the instructions leaves the hooks unavailable.
- **`docs/specs/0004` says zod "is load-bearing"**; proposal 20 deleted the zod dependency during
  round 2 and the spec carries no amendment note. Round 2 amended specs 0001 and 0005 when their
  claims moved; 0004 was missed.
- **`packages/python/.../CONTEXT.md:176` names a `CliError`** that does not exist in the Python port.

## Glossary gaps — partly closed

**App** and `ModelSpec.patterns` were added to both ports' `CONTEXT.md` during round 2's bookkeeping.
`App` was the sharpest of these: the **UpdatePlan** entry already referred to it in bold, as a defined
term, in a glossary that did not define it.

Still open: `CONTEXT.md` does not name the `pin/update` surface, does not document Python's
`render_update_plan`, and has no TypeScript API `*Input` expansion.

## Why a gate, not just edits

`docs/issues/12` already records that there is no PR-time docs gate. Every item above would have been
caught by one. Fixing the prose without fixing the absence of a gate buys one round of accuracy.
