# Modules describing responsibilities they do not have

**Status:** closed — from round 2. Found by the whole-branch adversarial review (docs-vs-code)

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

## Resolution

All seven items were re-verified against the tree (which had moved 33 commits since triage) and all
seven reproduced — nothing in the "reported by review" group had already been fixed.

**Verified group:**

1. **`packages/typescript/CONTEXT.md:39-41`** (`comment-geometry.ts`). Confirmed:
   `comment-geometry.ts` still disclaims block-comment columns in as many words, and CONTEXT.md still
   claimed the module owned both. Rewrote the **Emitter** entry to say `comment-geometry.ts` owns
   only `EOL_GUTTER`, that the block-comment column is explicitly not its business (the `yaml`
   backend indents `commentBefore` automatically), and added the one sentence the old text was
   missing — that the Python peer owns both columns because ruamel does not do this for it. The
   asymmetry is now stated, not flattened.

2. **`packages/python/src/ghagen/emitter/nodes.py:3-7`** (comment attachment). Confirmed:
   `document.py:46` still called `attach_model_comment` directly, bypassing `nodes.py`. Routed it:
   added `nodes.attach_root_comment(cm, model)` — a thin wrapper around the same
   `attach_model_comment` call, kept in `nodes.py` — and changed `document.py` to import and call
   that instead of `emitter.comments.attach_model_comment` directly. This was cheap (one new
   4-line function, one import swap, no behavior change — `_model_to_map`'s docstring already
   documented the root as the one exception, so the new function's job was already anticipated) and
   makes `nodes.py`'s "here and nowhere else" claim literally true rather than needing a caveat.
   `pytest -k "document or emitter or node"` (141 tests) still passes.

**Reported-by-review group — all four reproduced:**

3. **`transport-contract.ts:28`**. Confirmed: two docstrings each called a different thing "the
   sole caller of the adapters' deadline argument" — `FAILURE_DEADLINE_MS` (a constant, which
   cannot literally be a "caller" of anything) at the old line 29, and `loopbackAdapter`'s returned
   closure at line 330. Reworded both to say what is actually true and stop colliding: the constant
   is now "the only value ever passed as `deadlineMs` for a failure row," and the closure is
   "`build`'s sole caller."

4. **`AGENTS.md:49-56`**. Confirmed: `pre-commit` was absent from `pyproject.toml`'s
   `[dependency-groups] dev` list, and `uv run pre-commit --version` failed with "No such file or
   directory" before the fix. Decision: added `pre-commit` to the dev dependency group (rather than
   just correcting the instructions) — it is the tool AGENTS.md already tells every contributor to
   install, "four installs, all four required" is the explicit promise, and the rest of the repo's
   convention is that every dev tool is invoked through `uv run` (ruff, pyright, pytest all are), so
   the missing dependency was the actual bug, not the instruction. Also changed the setup snippet's
   `pre-commit install` to `uv run pre-commit install` for consistency with that convention.
   Verified: `uv sync` now installs `pre-commit==4.6.2`, and `uv run pre-commit --version` succeeds.

5. **`docs/specs/0004`** (zod). Confirmed: `docs/specs/0004-unified-root-discovery.md:165` still
   says the zod schema "is load-bearing... so 'delete it' is not on the table," zod is absent from
   `packages/typescript/package.json` and from every `src/` import, and the spec carried no
   amendment note (proposal 20 itself, §G, called the stale prediction "not a file to edit" at the
   time). Followed the convention specs 0001 and 0005 already established (a bolded **Amended by
   proposal N.** note left inline, prediction kept for the record) rather than inventing a new one:
   added an amendment note under the zod paragraph explaining that the merge commit replaced the
   zod schema with hand-rolled typed-result validation (ADR-0007) before proposal 20 deleted the
   now-callerless dependency.

6. **`packages/python/.../CONTEXT.md:176`** (`CliError`). Confirmed: Python's CONTEXT.md line 195
   said "`CliError` is CLI-local," but `CliError` is a TypeScript-only class
   (`packages/typescript/src/cli/_errors.ts`) — the Python port's CLI-local error type is
   `typer.Exit`, used throughout `cli/_common.py`, `cli/main.py`, `cli/deps.py`. Rewrote the bullet
   to name the real Python mechanism (`cli/_common.py` renders a `ConfigError` to `typer.Exit`) and
   to note, rather than assume, that the TypeScript peer's equivalent is `CliError` — Python has no
   such class.

**Glossary gaps**, addressed in both ports' `CONTEXT.md`:

- **`pin/update` surface**: named in the existing "sweep, write, plan" prose in both Surface-notes
  sections — Python's now says `pin/update`'s `apply_updates` writes the version bumps back into
  user source, TypeScript's says `pin/update.ts`'s `applyUpdates` does the same. Left at the prose
  level, not promoted to a bolded glossary term: it is an implementation module, not a domain noun,
  and the domain concepts it serves (**Upgrade report**, **UpdatePlan**) already have entries.
- **Python's `render_update_plan`**: added to the Python Surface-notes `pin/plan` paragraph,
  naming it as the **UpdatePlan** renderer and the `plan`-layer peer of `pin/render`'s
  `render_upgrade_report` — the same two-format (`json`/`github`) shape. (TypeScript's
  `renderUpdatePlan` was already documented; this was a Python-only gap.)
- **TypeScript API `*Input` expansion**: added a new glossary entry, `*Input`, in
  `packages/typescript/CONTEXT.md`'s Models section, defining the `WorkflowInput`/`StepInput`/etc.
  naming convention as the `I` in `defineFactory<M, I>(SPEC)` and distinguishing it from the
  **Model** the factory returns.

## What the new docs gate would and would not have caught

`docs/issues/12` is closed; there is now a PR-time `docs` CI job (`scripts/typecheck.sh docs`)
locally. Read what it actually runs: `astro build` over `docs/src/content/docs/` (the guide pages)
plus TypeDoc extraction from `packages/typescript/src/_docs-api-*.ts` (the public TypeScript API
reference). It fails the build on broken links, malformed MDX/JSDoc, or a TypeDoc reflection-kind
mismatch (the `@function` tag guard mentioned in `CONTEXT.md`'s Surface notes is a _test_, not part
of this gate).

None of that build touches any of the seven files this issue fixed:

- `packages/python/CONTEXT.md` and `packages/typescript/CONTEXT.md` live in `packages/`, not
  `docs/src/content/`, and are not TypeDoc entry points — the astro build never reads them.
- `AGENTS.md` and `docs/specs/0004-unified-root-discovery.md` are likewise outside
  `docs/src/content/`.
- `transport-contract.ts` is excluded from the TypeScript build itself
  (`tsconfig.json`'s `exclude`), so TypeDoc — which only walks what the compiler configuration
  reaches — never processes its docstrings either.

Honest answer: **the new docs gate would have caught none of these seven items.** It verifies that
the _published_ documentation site builds — links resolve, MDX/JSDoc parses, TypeDoc extraction
succeeds — not that prose claims about module responsibilities match the code. CONTEXT.md, AGENTS.md,
and `docs/specs/`/`docs/adr/`/`docs/issues/`/`docs/proposals/` are all outside its reach entirely, and
the one in-reach file (`transport-contract.ts`) is a test-only module the build config explicitly
excludes. A gate that would have caught these would need to diff prose claims against the modules
they describe — a substantially different (and harder) thing than "does the docs site build," and
still an open gap after this round.
