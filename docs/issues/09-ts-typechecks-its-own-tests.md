# Neither port type-checks its own tests

**Status:** closed — both ports type-check their own tests. TypeScript's gate moved to a new
`tsconfig.typecheck.json` (the publish boundary and the gate scope are now two lists); pyright's
`include` and `scripts/_gate.sh`'s `PY_PATHS_TYPED` widened to `packages/python/tests`. From round 2. Deferred out of proposal 09 (item (b)); scope widened by proposals 23 and 10

`packages/typescript/tsconfig.json` excludes:

```json
"exclude": [
  "node_modules", "dist", "src/**/*.test.ts",
  "src/integration/test-utils.ts", "src/pin/transport-contract.ts", "src/paths.ts"
]
```

`scripts/typecheck.sh ts` therefore checks none of them. A `*.test.ts` file can reference a field
that no longer exists and nothing fails until the test runs — and for a type-only mistake, not even
then.

**The list grows.** Proposal 16 added `src/pin/transport-contract.ts` during round 2 — a test-only
module living under `src/`, excluded for exactly the reason `src/integration/test-utils.ts` already
was. That is the shape of the defect: every new shared test helper is a correct-by-local-reasoning
addition to a list nobody is auditing, and each one silently removes a real module from the gate.
Round 2 alone took the list from three entries to four.

**Measured, not inferred.** Proposal 23's implementer probed the gate by injecting
`export const zz: number = "nope";` into `src/paths.ts` and the gate returned **rc=0**. Re-probing
through an included file (`src/models/_base.ts`) returned rc=2, so the gate is sound for what it
covers — the hole is exactly the exclude list.

Note `src/paths.ts` is also the file at the centre of `docs/issues/08` (the `FIXTURES_DIR`
collision). Two round-2 issues land on one unchecked file.

## Why it was deferred, and what to check first

**Not for cost.** Turning it on voids proposal 11's stated rationale for `registry.ts`, which
proposal 22 then quotes approvingly in its own argument. Both siblings were ready at the time;
landing this mid-round would have forced two ready proposals to rewrite their reasoning.

Whoever picks this up must re-read 11 and 22 **as landed** and check whether those rationales still
stand, before touching `tsconfig.json`.

Related: `docs/issues/17` — `scripts/` is outside every Python gate. Same shape of defect in the
other port; worth fixing in one pass.

## The Python port has the same hole, by a different mechanism

`pyproject.toml:71` sets `include = ["packages/python/src"]` for pyright, while
`testpaths = ["packages/python/tests"]` (`:74`) is where every Python test lives. **No Python test
file is type-checked by anything.** There is no exclude list to audit here — the tests were never in
scope to begin with, which is why this was not noticed alongside the TypeScript list.

**Measured.** Proposal 10's implementer left a stale `order=("version",)` argument in
`packages/python/tests/test_validation.py:122` after deleting the `order` field from `ModelSpec`. A
full `./scripts/typecheck.sh all` passed clean. It was found by grep, not by a gate, and would
otherwise have surfaced as a runtime `TypeError` at collection time — or, for a type-only mistake,
not at all.

So the two ports are not asymmetric after all: **neither** type-checks its tests. Fix them in one
pass, and note the shapes differ — TypeScript needs entries removed from an `exclude` list that
keeps growing, Python needs `packages/python/tests` added to `include` (expect a first run to be
noisy: pytest fixtures and `monkeypatch` shims are written without annotations throughout).

## A third measurement, and a known first failure

The whole-branch review of round 2 found a concrete `TS2554` waiting in the excluded set:
`packages/typescript/src/emitter/yaml-writer.test.ts:171,178,185` each pass a **third argument to a
two-parameter function**. It is accepted today only because the file is excluded. Two consequences,
and the second is the worse one:

1. Whoever turns the exclude off gets these three failures immediately — expect them, they are not
   collateral from the config change.
2. Because the third argument is ignored, those three tests now depend on **insertion order** for the
   behaviour they meant to pin explicitly. They pass for a reason other than the one they state.

That is the argument for doing this sooner rather than later: an unchecked test file does not merely
fail to catch type errors, it silently changes what the test asserts.

## Resolution

Both holes closed in one pass, both proved closed by probe, and the exclude list reduced to nothing
the gate can see. No entry was left in the gate's scope for any reason.

### The precondition: proposals 11 and 22, re-read as landed

**Neither proposal's landed reasoning becomes false, because both pre-declared this outcome.** The
issue's framing — that turning the exclude off "voids proposal 11's stated rationale for
`registry.ts`, which proposal 22 then quotes approvingly" — is right about the mechanism and wrong
about the consequence: 11 does not rest on the exclusion, it explicitly disclaims resting on it.

11 §"Why it must be a source module, not `spec.test.ts`" gives two reasons and grades them itself:
two consumers is "the durable reason; it holds under any `tsconfig` arrangement," and of the CI
reason it says, in bold, "**That second reason is not load-bearing and may not survive the round:**
09's item (b) proposes a test-inclusive `tsconfig.typecheck.json`, after which test files _are_
typechecked. The registry stays in `src/` either way, on locality."

22 quotes it with the same grading: "only one is durable … The second … **is voided if 09's item (b)
lands** … This document leans only on the durable reason," and carries an **Open — Phase 3
decision** note requiring that any argument resting on the exclusion be restated if 09 lands. This
resolution is that restatement, and there is nothing to restate: no landed argument rested on it.

Two corrections to the record, both in the direction of the decision being safer than the issue
feared:

- **11's durable reason is now stronger than when written.** It claims two consumers of
  `registry.ts`; as landed there are three, and one is not a test file at all —
  `models/conformance-values.ts:25` (a `src/` module), `models/conformance.test.ts:32`,
  `models/spec.test.ts:2`. The registry could not move into a test file under any `tsconfig`
  arrangement whatsoever.
- **22's Open note predicted a mechanism that was not used.** It says "If it lands,
  `tsconfig.json:24` no longer excludes test files." It still does — see below. What changed is that
  the exclusion no longer has a CI consequence, which is the substance the note was protecting.

### TypeScript: the publish boundary and the gate scope are now two lists

The entries were **not** deleted from `packages/typescript/tsconfig.json`. That file is what
`npm run build` runs `tsc` over, and `package.json`'s `files: ["dist"]` ships whatever it emits;
deleting the entries would put `paths.ts`, `integration/test-utils.ts`, `pin/transport-contract.ts`
and every `*.test.ts` into the published tarball. Proposal 09 item (b) had already weighed the
in-place and new-file variants and chose the new file, and that is what landed:

- **`packages/typescript/tsconfig.typecheck.json`** (new) — `extends: "./tsconfig.json"`,
  `noEmit: true`, and `"exclude": ["node_modules", "dist"]`. Only what `tsc` cannot read at all.
- **`package.json`** — `"typecheck": "tsc --noEmit -p tsconfig.typecheck.json"` (was
  `tsc --noEmit`). `"build"` is untouched and still uses `tsconfig.json`.
- **`tsconfig.json`** — six-entry `exclude` unchanged, with a comment above it naming what the list
  now means: adding an entry here keeps a module out of `dist/`, and does not take it out of `tsc`.

That is the fix for "the list grows." It can still grow — it should, every time a test-only module
lands under `src/` — and growing it can no longer narrow the gate. `docs/astro.config.mjs` points
TypeDoc at `tsconfig.json` but supplies explicit `entryPoints`, so widening the gate's config does
not widen the published API docs; `./scripts/typecheck.sh docs` (astro build) passes unchanged.
`npm run build` was re-run and `dist/` contains no `paths.js` and no `*.test.js`.

### Python: one Python root list, and one thing pyright could not see

- **`scripts/_gate.sh`** — the subtraction that produced `PY_PATHS_TYPED` from `PY_PATHS` is gone;
  `PY_PATHS_TYPED=("${PY_PATHS[@]}")`. Round 3 had already put the scope declaration in one place,
  so this is a two-line change in the file that declares it rather than an edit to a gate script.
  The name is kept so the three `py` gates still read alike, and so a future divergence is forced to
  appear here.
- **`pyproject.toml`** — `[tool.pyright] include` gained `"packages/python/tests"`, and needed
  `extraPaths = ["scripts"]` alongside it. That second line is the peer of
  `[tool.pytest.ini_options] pythonpath = ["scripts"]`: the schema tests import `ghagen_schema` as a
  top-level package from `scripts/` (ADR-0003), which pytest arranges with its own `sys.path` entry
  that pyright has no view of. Without it every such import is `reportMissingImports` — 20 errors
  that are entirely an artefact of the tool not reading pytest's config.

### The probes

`./scripts/typecheck.sh ts` before means the command as it stood: `tsc --noEmit` over
`tsconfig.json`. `./scripts/typecheck.sh py` before means pyright over the pre-fix
`PY_PATHS_TYPED` (`packages/python/src/ scripts/ .github/ghagen_workflows.py`).

| Injection                                                                   | Gate before | Gate after                        |
| --------------------------------------------------------------------------- | ----------- | --------------------------------- |
| `export const zz: number = "nope";` → `src/paths.ts`                        | **rc=0**    | **rc=2** (`TS2322`)               |
| `export const zz: number = "nope";` → `src/emitter/yaml-writer.test.ts`     | **rc=0**    | **rc=2** (`TS2322`)               |
| `zz: int = "nope"` → `packages/python/tests/test_models/test_validation.py` | **rc=0**    | **rc=1** (`reportAssignmentType`) |

Both files restored; `git status` clean of them. The `paths.ts` row reproduces proposal 23's
original measurement exactly, and the second row extends it to the `src/**/*.test.ts` glob, which is
the bulk of the hole by file count.

### The three `yaml-writer.test.ts` cases

Found where the issue said, one round later: lines **223, 230, 237** (not 171/178/185 — round 3
moved them). Each passed `["name", "on"]` as a third argument to `simpleModel`, which has taken two
parameters since proposal 10 deleted `ModelSpec.order`. The argument was silently dropped, and
`tsc` never saw the call.

The extra argument was not noise. It named the premise the test's own title rests on — that `on` is
emitted _after_ `name`, so the commented `name` really is a _neighbouring_ key. With the argument
inert, three of the four cases were getting that ordering from the object literal's insertion order
instead: they passed, but not for the reason they stated, and a change to how `data` is ordered
would have left them green while testing nothing.

The parameter is gone and is not coming back (an `explicit` spec emits `data` as it stands, so the
literal _is_ the order). So the premise is pinned the way this file already pins its header cases:
all four assertions changed from `toContain` on the gutter substring to `toBe` on the **whole
emitted document**, in which key order is a byte fact rather than an assumption —
`"# the name\nname: ci\non: push  # trigger\n"` and the three peers. The gutter strings the
cross-port parity note refers to (`test_comments.py`) are still asserted, now as substrings of a
document whose ordering is stated. Deleting the third argument to quiet `tsc` would have left the
tests weaker than they were written to be; this leaves them stronger.

### What else the gate caught the moment it was opened

TypeScript went from **46 errors to 0**, Python from **131 to 0**. Most were narrowing noise, but
these were real:

- **`src/integration/test-utils.ts` had two mis-modelled imports** (`TS2351`, `TS2349`). Both `ajv`
  and `ajv-formats` are CommonJS, so under `moduleResolution: "node16"` a default import binds the
  module namespace, not the value: `new Ajv(...)` has no construct signature and `addFormats(...)`
  is not callable. Now `import { Ajv } from "ajv"` (a real named export) and
  `import addFormatsPlugin from "ajv-formats"; const addFormats = addFormatsPlugin.default` (that
  package's CJS entry sets both `module.exports` and `exports.default` to the plugin, so `.default`
  is the callable under either interpretation).
- **Four `src/models/trigger.test.ts` casts stopped one level short**, leaving the leaf they index
  typed `unknown`. Named the shape once (`type DefMap = Record<string, Record<string, unknown>>`)
  and cast to it.
- **Three test fixtures omitted required discriminants** — `walk.test.ts` built a `compositeRuns`
  without `using: "composite"`, `pin/collect.test.ts` and `pin/sites.test.ts` built `dockerRuns`
  without `using: "docker"`; `trigger.test.ts` built a `workflow` without `jobs`.
- **`packages/python/tests/test_pin/transport_contract.py` carried a `# type: ignore[assignment]`
  that nothing had ever checked.** It papered over a narrowing lost between two lookups of the same
  dict. Restructured to read the table once; the suppression is deleted rather than re-justified.

### Suppressions

**Eight added, all in Python, all with an in-place justification; two removed.** No
`@ts-expect-error`, no `eslint-disable`, and no entry left in any gate's scope.

Seven are in `packages/python/tests/test_models/test_trigger.py`:

- `On(**{field: value})` and `On(**{typo: {}})` — `# type: ignore[arg-type]`. A `**dict[str, object]`
  splat cannot be checked against a keyword signature; the dict is the parametrization, which is the
  point of these two tests.
- Five `# type: ignore[call-arg]` on the deliberate-misspelling negative tests (`PRTrigger(tag=…)`,
  `ScheduleTrigger(time_zone=…)`, `WorkflowDispatchInput(deprecationMessage=…)`,
  `Permissions(artifact_metadta=…)`, `Environment(deployments=…)`). Each asserts that
  `extra="forbid"` rejects the name at runtime. A static checker that accepted the call would mean
  the test was testing nothing; suppressing the compile error is what keeps the runtime assertion
  reachable.

The eighth is `Step(shell=Raw(None))` in `packages/python/tests/test_emitter/test_field_collection.py`
— `# type: ignore[arg-type]`. `Raw` is invariant, so `Raw(None)` is `Raw[None]` and outside
`shell`'s declared `ShellType | Raw[str] | None`. That is what the test is for: `collect_fields`
reads the attribute before any `Raw` see-through, so what the escape hatch wraps is not its
business. Widening `Raw[str]` to `Raw[Any]` is a published-API decision (`docs/issues/27`) whose
present-null semantics belong to `docs/issues/04`.

Removed: the inert `# type: ignore[assignment]` in `transport_contract.py` (above), and a
`# noqa: B018` in `test_helpers/test_expressions.py` — binding the set (`_ = {expr.github.ref}`) is
what raises, and naming the result satisfies both ruff and pyright's `reportUnusedExpression`.

One TypeScript assertion was added: `simpleModel` in `yaml-writer.test.ts` now returns
`as unknown as Document`. The claim is false — its spec's `kind` is `"step"`, and only a workflow or
an action is a `Document` — and the JSDoc says so. These tests deliberately drive the writer with a
model whose shape they control completely, and `toYaml` reads only `data` and `spec`, never the
brand. One documented assertion at the seam replaces 33 at the call sites.

### Deliberately not done

- **`shell="bash"` is a pyright error in Python and compiles in TypeScript.** Python's `ShellType`
  and `PermissionLevel` are `StrEnum`s (`models/common.py:8,18`); TypeScript's are string unions
  (`models/common.ts:15`), which it also exports from `src/index.ts:142` while Python's
  `ghagen/__init__.py` exports neither. The docs are inconsistent with themselves about it
  (`python/api/step.md:58` uses `ShellType.BASH`; `guides/cookbook.mdx:868` and
  `models/action.py:215` use `shell="bash"`). Nine test files were moved to the enum rather than the
  public type being widened — this is `docs/issues/27`-shaped work and does not belong in a gate-scope
  change. **It is a published-API divergence and should be filed against 27.**
- **`Raw[str]` was not widened** — see the eighth suppression above; `docs/issues/27` and
  `docs/issues/04`.
- **`packages/python/tests/test_cli/test_main.py:112` still says `shell="bash"`.** It is inside a
  triple-quoted string fixture of generated user code, so it is not Python the checker reads.
- **`docs/issues/17` needed nothing.** The issue proposed fixing it "in one pass" with this one, but
  round 3's `scripts/_gate.sh` already put `scripts/` in `PY_PATHS`; the only residue was the
  subtraction that kept it out of the typecheck gate, which is the same line this fix deletes.

### Final state

All gates green: `./scripts/typecheck.sh all`, `./scripts/lint.sh all`, `./scripts/fmt.sh all`,
`uv run ghagen check-synced`, `uv run ghagen deps check-synced`,
`PYTHONPATH=scripts uv run python -m ghagen_schema check`. **pytest 1008 passed** (and 1008 again
under `CI=true`), **vitest 1069 passed / 46 files** — both exactly the pre-change baseline. 31 files
changed; 21 of them are Python test files whose only change is a narrowing the checker now demands.
