# The Snapshot refresh brought two unmodeled upstream features

**Status:** open — filed while resolving issue 31, whose refresh is what exposed them

The 2026-09-01 Snapshot refresh (issue 31) added upstream properties that are not typos or
one-line fields. Seven of them are the surface of two whole capabilities, and both are recorded as
`# TODO: unmodeled (issue 37)` rows in `schema/conformance-gaps.yml` rather than modelled in the
same pass — a refresh should not smuggle in a feature. This is that feature work, stated so the
gap rows have somewhere to point.

## 1. Background and parallel steps (`definitions.step`, five keys)

Upstream grew `background`, `cancel`, `parallel`, `wait`, and `wait-all`, and at the same time
turned `definitions.step` into a six-branch `oneOf`: a step is now required to be exactly one of
`uses`, `run`, `wait`, `wait-all`, `cancel`, or `parallel`. ghagen's `Step` / `StepInput` models the
first two and nothing else, so today a `wait` step cannot be authored at all.

The five keys are not five independent fields:

- `background: boolean` marks a `run`/`uses` step asynchronous. Referencing it later requires the
  step to carry an `id`, which is a cross-field rule of the same class as the one already recorded
  under `constraints` in `schema/conformance-gaps.yml`.
- `cancel: string` names one background step by its id.
- `wait` is `string | string[]` — one or more background step ids.
- `wait-all` is `boolean | null`, i.e. a **present-null keyword**: `wait-all:` with no value is the
  intended spelling. That is exactly the shape issue 36 is about, and modelling it means deciding,
  in both ports, how a present-null field survives the emitter.
- `parallel` is `array<step>` with `minItems: 1` — a **recursive** array of steps. `ModelSpec` has
  no self-referential list wrap today; `wrap` maps a field to a factory, and the factory here is the
  step factory the spec belongs to.

So the work is: a step-kind discriminated shape in both ports, one recursive wrap, one present-null
field, and a cross-field `id` requirement. Four decisions, not five fields.

## 2. Service containers gained `command` and `entrypoint`

Upstream split the single `definitions.container` into `definitions.jobContainer` (the six keys
ghagen models) and `definitions.serviceContainer` (those six **plus** `command` and `entrypoint`).
Both are `string`; `entrypoint` replaces the image's `ENTRYPOINT` and `command` supplies its
arguments.

ghagen's `Container` and `Service` models are the same shape by construction: one
`CONTAINER_FIELD_MAP` in `packages/typescript/src/models/container.ts` is shared by
`CONTAINER_SPEC` and `SERVICE_SPEC` (pinned by identity in `container.test.ts`), and the Python port
mirrors that. Adding the two service-only keys therefore means **un-sharing the field map** — which
is why the shared map is now bound as
`satisfies Record<keyof ContainerInput, keyof SchemaJobContainer & keyof SchemaServiceContainer>`:
the intersection is the statement that these are the keys _both_ upstream nodes declare, and adding
`entrypoint` to the shared map stops compiling. That is the seam the work has to cross, and it is
deliberately left standing rather than loosened.

The refresh's scope work already went in: `serviceContainer` is a scope of its own in
`schema/conformance-scopes.yml`, bound to `Service` / `SERVICE_SPEC` in both sweeps, so the two keys
are _counted_ as gaps rather than invisible.

## What a fix must do

1. Model background/parallel steps in **both** ports at once — the ports are at mandated feature
   parity, and this one adds a step kind, not a field.
2. Decide `wait-all`'s present-null spelling against issue 36's resolution rather than separately.
3. Decide whether `parallel` needs a general recursive-wrap capability in `ModelSpec` or a
   one-off, and record why.
4. Split `Container` and `Service` into distinct field maps and add `command` / `entrypoint` to the
   service half, in both ports. Keep `container.test.ts`'s identity pin honest by replacing it with
   whatever the new relationship actually is.
5. Delete the seven `# TODO: unmodeled (issue 37)` rows from `schema/conformance-gaps.yml` as each
   is closed — the sweep fails on a gap row whose gap no longer exists, so this is enforced, not
   remembered.

## Files

- `schema/conformance-gaps.yml` — the seven TODO rows, under `workflow_schema.step` and
  `workflow_schema.serviceContainer`
- `schema/workflow_schema.json` — `definitions.step`, `definitions.jobContainer`,
  `definitions.serviceContainer`
- `packages/python/src/ghagen/models/step.py`, `packages/typescript/src/models/step.ts`
- `packages/python/src/ghagen/models/container.py`,
  `packages/typescript/src/models/container.ts`
- `docs/issues/36-a-surviving-null-renders-differently-in-the-two-ports.md` — `wait-all` depends on
  its outcome
