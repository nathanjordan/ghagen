# Proposals index

## Round 1 — 2026-07-28 (proposals 01–08, all landed)

Authored 2026-07-21, implemented and adversarially reviewed 2026-07-28 on `arch-deepening/impl`.

- 01 — ModelSpec sole key-name authority — **landed** (`serialization_alias` removed, `_yaml_key` + guard tests deleted)
- 02 — Emitter observation surface `to_data`/`toData` — **landed** (two-walk variant; deep cross-check test added post-review; shared-walk refactor → issue 01)
- 03 — Synthesis pipeline `render()`, pin runs last — **landed** (behavior change: pin-last; ADR-0005)
- 04 — Pin engine threads parsed UsesRefs — **landed** (lockfile stays string-keyed; ADR-0006)
- 05 — Config module owns `.ghagen.yml` — **landed** (errors-as-values, `--config` short-circuit restored post-review; ADR-0007)
- 06 — Close ModelSpec escape hatches — **landed** (OrderMode both ports; `defaults()` comment-drop bug fixed)
- 07 — Prune hypothetical seams — **landed** (appLoader/app_loader removed; postProcess and `_docs-api-*.ts` deliberately KEPT — do not re-suggest)
- 08 — Schema pipeline orchestration — **landed** (`ghagen_schema` sync/generate/check; drift → PR; workflow self-defeat fixed post-review)

Adversarial review: 3 reviewers (correctness/parity, test integrity, CI/tooling); 3 majors + 8
minors/nits found, all fixed on-branch. Deferred work: `docs/issues/01`–`07`.

## Round 2 — 2026-08 (proposals 09–24, all landed)

Authored and adversarially reviewed 2026-07-29/30; implemented on `arch-deepening/impl`, merged in
dependency order. Seven hotfixes (H1, H2, H4, H5, H6, H8, H14) landed as standalone commits on `main`
first — a refactor never gates a real fix.

The round's theme: round 1 deepened seams that were _shallow_; round 2's friction was seams that were
**deep but unenforced** — an interface stating an invariant its implementation did not hold, with no
test binding them.

- 09 — Python construction-time validation actually validates — **landed** (`Raw._validate` refuses
  unwrapped values; `extra="forbid"`; grammar bound through `schema/conformance-values.yml`)
- 10 — Delete `ModelSpec.order`'s payload — **landed** (declaration order _is_ emission order;
  `OrderMode` loses its payload; the red proof showed the golden fixtures did not back-stop
  `container` either — spec 0001 §3.3/§4 amended)
- 11 — One shared spec-surface table both ports must satisfy — **landed** (trigger sub-tree swept;
  `satisfies Record<ModelKind, ModelSpec>` makes omission a type error)
- 12 — A real comment-geometry module in the TS Emitter — **landed** (document-wide `String.replace`
  deleted; fixed the 1-space EOL gutter on complex values and stopped orphaning EOL comments)
- 13 — Unify the `format_header` contract, headers under the shared byte oracle — **landed** (six
  `fixtures/expected/header_*.yml`, read by both suites)
- 14 — `versions` owns its comparison — **landed** (`packaging` and `semver` dropped from this path;
  grammar pinned by `schema/tag-grammar.yml`)
- 15 — Single-home the Lockfile's on-disk encoding and error mode — **landed** (golden lockfile both
  ports write byte-identically)
- 16 — Lift transport policy into the `HttpClient` interface — **landed** (one double per port;
  `transport-contract.ts` shared harness)
- 17 — Move the upgrade-report renderer out of the Typer command into `pin/render` — **landed**
  (`checked_versions`/`checked_lockfile` on `UpgradeReport`; `test_deps.py` 887 → ~250)
- 18 — Pull `check-deps`'s decision logic across the CLI seam — **landed** (`deps update` + `UpdatePlan`;
  ~140 lines of untested bash retired; reversed 06's `outputs:` deletion — **ADR-0012**)
- 19 — `main()` owns exit codes end to end — **landed** (`.exitOverride()`; `init` scaffold under a
  shared golden)
- 20 — Delete caller-less pin/spec surface — **landed** (8 items; `extrasPlacement` deleted, reversing
  an accepted risk from 06 — **ADR-0011**)
- 21 — Hoist the duplicated field-collection loop (Python) — **landed** (`collect_fields` shared by
  `_model_to_map` and `_model_to_data`)
- 22 — Collapse the 27 identical TS factory bodies into `defineFactory(SPEC)` — **landed** (TypeDoc
  output verified unchanged against the live `_docs-api-*.ts` entry points)
- 23 — Dev-script hygiene — **landed** (`scripts/_gate.sh`; actionlint once, at one version)
- 24 — Narrow `walk()` — **landed** (part (a); the prune protocol was provably caller-less in both ports)

Declines recorded as ADRs so round 3 does not re-suggest them: **ADR-0010** (the `matrix_` rename),
**ADR-0011** (`extrasPlacement`), **ADR-0012** (composite actions publish their decision — an action
that only sequences steps needs no `outputs:`, one that _decides_ something must publish it).

### Whole-branch review and the fix pass

Five independent reviewers swept the merged branch. Their confirmed criticals were fixed on-branch
by four worktree-isolated agents with disjoint allowlists, each defect shown red before green:

- **The shipped action could report success having done nothing.** `deps update` never called
  `app.synth()`, so every PR it opened failed the consumer's own `check-synced`; and the new
  branch-based dedupe returned 0 for the rest of the day if a run pushed a branch and then died
  before `gh pr create` — a _silent_ regression from the PR-based dedupe it replaced. Dedupe is now
  on the branch for the push and on the PR for the skip. `--mode versions` also produced a tree
  `ghagen synth` could not build (`PinError`): a bump now carries the lockfile refresh with it
  whichever stage found it.
- **Two ports, one grammar, two accept-sets.** Python's tag regex used `\d`, `.` and `$`, each
  wider there than in JavaScript, so `v١.٢.٤` was a version tag in one port and not the other —
  and the wider side is the one that _rewrites the user's files_. **ADR-0008's own regex text was
  the root cause** and is amended: it stated one regex as the authority for both ports without
  naming a dialect.
- **Deep-but-unenforced, again, in the tests themselves.** Cross-port field _order_ was bound
  nowhere — permuting a `fieldMap` left 803/847 green while the emitted bytes moved. The
  tautological guards were worse than absent, since they read as coverage. Three new shared tables
  answer this class: `schema/key-order.yml` (30 kinds), `schema/comment-geometry.yml`, and
  `reject_commented` vectors in `schema/conformance-values.yml`.
- **`with_comment()` was an unintended escape hatch in Python only** — the grammar check ran after
  the wrapper was re-attached, saw a non-`str`, and skipped. Notably, a reviewer read the
  docstring, which asserts the opposite ordering, and marked the code sound without executing it.

Gate: **913 pytest / 965 vitest** (round-1 baseline 548/514; pre-review round 2 803/847).

Deferred work: `docs/issues/08`–`30`. Issues 23–29 come from the whole-branch review rather than from
a proposal's allowlist boundary — the review's confirmed criticals were fixed on-branch and the rest
filed there.
