# Architecture proposals

Deepening proposals from the architecture review rounds. Each turns a shallow seam into a deeper
module — more behaviour behind a smaller interface — with testability and cross-port parity as the
driving goals.

**[`INDEX.md`](./INDEX.md) is the authority on status.** Numbering is monotonic across rounds and
never restarts; a proposal file describes what was proposed, not necessarily what landed. Where the
two disagree, the ADRs in `docs/adr/` and the code win over both.

Deferred work lives in [`../issues/`](../issues/).

## Round 1 — reading order

The ModelSpec/Emitter cluster is one theme and should be read (and, if accepted, landed) in order:

The ModelSpec/Emitter cluster is one theme and should be read (and, if accepted, landed) in order:

1. [01 — ModelSpec as the sole key-name authority](./01-modelspec-key-authority.md) (Python)
2. [02 — A public Emitter observation surface](./02-emitter-test-seam.md) (both ports)
3. [06 — Close the ModelSpec/Emitter escape hatches](./06-close-modelspec-escape-hatches.md) (TS-led)

The rest are independent of that cluster and of each other, except 07 which partly rides on 05:

- [03 — One synthesis pipeline behind App](./03-synthesis-pipeline.md) (both ports)
- [04 — Pin engine threads UsesRefs instead of strings](./04-pin-engine-threads-usessites.md) (both ports)
- [05 — Config module owns `.ghagen.yml` end to end](./05-config-module-owns-ghagen-yml.md) (both ports)
- [07 — Prune hypothetical seams and dead surface](./07-prune-hypothetical-seams.md) (both ports; depends on 05)
- [08 — Schema pipeline orchestration](./08-schema-pipeline-orchestration.md) (dev tooling)

## Round 1 — decisions that needed explicit sign-off

Points where a round-1 proposal recommended a behaviour change or picked between live options. All
were signed off and landed; kept here as the record of what was chosen and why.

- **03**: flips Transform ordering from pin-first to pin-last — user Transforms then see refs, not
  SHAs, and refs they inject get pinned. Deliberate behaviour change; alternatives documented in
  the proposal.
- **01**: deletes pydantic `serialization_alias` from the Python models (direction (a)) rather
  than deriving `yaml_keys` from the aliases (direction (b)).
- **06**: introduces an explicit `OrderMode`, resolving a live port divergence — with an empty
  `order`, Python's Emitter alphabetizes while TypeScript's keeps insertion order.
- **05**: makes the internal emitter `auto_dedent` parameter required (no default), fixing a
  TS/Python internal-default mismatch; the sole `True` default lives on `GhagenOptions`.
- **08**: upgrades the schema-drift workflow from detect→issue to detect→PR, with the
  `GITHUB_TOKEN`-authored-PRs-don't-trigger-CI caveat addressed in its Risks section.

## Round 1 — findings that reversed the initial survey

The proposal writers verified every claim against source; these survey claims were wrong and the
proposals reflect the corrected reality. **Do not re-suggest the reversed items.**

- `postProcess` / `post_process` is documented public escape-hatch API with real tests — **kept**,
  not pruned (07). Its removal would not unlock `structuredClone` either; the symbol-branded
  `Raw`/`Commented` wrappers block that unconditionally.
- The `_docs-api-*.ts` files are live TypeDoc entry points consumed by `docs/astro.config.mjs` —
  **kept** (07).
- TypeScript has no frame-classification duplication (already unified in `_package_paths.ts`);
  the shared-predicate work in 07 is Python-only.
- `collect` passes the deletion test in both ports (three real engine callers); 04 deepens it to
  return parsed `UsesRef`s rather than deleting it.
- The `defaults()` comment drop happens in the Emitter's plain-object branch, not in the factory;
  06 fixes it by mirroring Python's `DefaultsRun` model shape.
