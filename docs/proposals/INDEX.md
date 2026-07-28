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
