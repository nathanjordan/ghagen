# ghagen (TypeScript)

The TypeScript/JavaScript implementation of ghagen: factory-built models describing GitHub Actions,
serialized to YAML. Shares its domain vocabulary with the [Python](../python/CONTEXT.md) port — see
[`CONTEXT-MAP.md`](../../CONTEXT-MAP.md).

## Language

### Models

**App**:
The user's whole generation surface — every **Document** to be generated, the output directory, and
the optional lockfile path. Built by the user's config module and returned to the CLI by the config
loader; `synth()` is the one call that turns an App into files on disk. The App, not the Document, is
what the pin subsystem and the `deps` family operate over, and a null lockfile path is a supported
configuration that several decisions turn on (see **UpdatePlan**).
_Avoid_: project, workspace, root config.

**Document**:
A Workflow or Action — the unit that maps 1:1 to a generated YAML file, and the only thing that may
be serialized to a file.
_Avoid_: manifest, item, artifact.

**Workflow**:
A GitHub Actions workflow definition, generated to `.github/workflows/*.yml`.

**Action**:
A composite / docker / node action definition, generated to `action.yml`.

**Step**, **Job**:
The nested units inside a Workflow (a Job contains Steps).

**ImageSnapshot**:
A custom runner-image generation request on a Job (`jobs.<id>.snapshot`) — image name plus optional
version.
_Avoid_: snapshot (reserved for the schema **Snapshot**).

**Transform**:
A synthesis-time mutation applied to a clone of a Document before emission (e.g. the pin transform).
_Avoid_: plugin, hook, middleware.

**Emitter**:
The module that serializes a model tree to YAML — key ordering, comments, block scalars. Owns all
serialization recursion (see ADR-0001, amended); models never serialize themselves. Also exposes
the plain-data observation surface `toData()` — the supported way to inspect a model's emitted
structure (see **CommentNode**).
Comment _geometry_ — the end-of-line gutter (`EOL_GUTTER`, 2 columns) and the block-comment
column — is a named module, `emitter/comment-geometry.ts`, and every comment payload is rendered
through it at attach time. No Emitter pass rewrites emitted text. The Emitter also owns the emitted
**Header** bytes end to end — the backend never sees them.

**ModelSpec**:
The per-model serialization spec — YAML key names (field → emitted key), an **OrderMode**, the
inline-input wrap map, and per-field emission rules (present-null-when-empty, dynamic-keys
passthrough) — declared next to the factory, consumed by the Emitter and
factories. The single home for the emitted-key fact (`fieldMap`, type-checked with `satisfies`
against the generated schema types); every factory _is_ `defineFactory(SPEC)` — there is one
construction body in the port, and a factory declaration carries no code. Its `fieldMap`
**declaration order is the emission order** — there is no second list beside it. Its `patterns` map
binds a _value grammar_ to a field, checked in `buildYamlData` on the peeled value so that `raw()`
stays the deliberate escape hatch and `withComment(...)` is not one.
_Avoid_: field map, key-order table.

**OrderMode**:
A ModelSpec's emission-order rule. Two cases, no third and no placement modifier (ADR-0011):
`"explicit"` (the default — emit in `fieldMap` declaration order, then extras) or `"alphabetical"`
(sort every key, extras interleaved). A bare string union, not a tagged one: `explicit` used to
carry a `keys` array naming the sequence a second time, restating `Object.values(fieldMap)` in
every spec.

**CommentNode**:
The Emitter's public, backend-neutral representation of a value plus its attached block/EOL
comment, produced by `toData(..., { comments: true })`.

**Header**:
The auto-generated comment block at the top of every emitted file. `format_header` /
`formatHeader` resolves the four input shapes (default, `None`/`null`, string, closure) to the
exact bytes that precede the YAML body — `#`-prefixed, one trailing newline, blank lines as a
bare `#`, one trailing line break in the input dropped — or to `None`/`null` for "no header".
The writer concatenates; it never re-wraps, pads, or re-indents. Byte parity is asserted by
`fixtures/expected/header_*.yml`.
_Avoid_: banner, preamble, file comment.

### Pinning

**UsesRef**:
A parsed `owner/repo[/path]@ref` action reference; knows whether it is **Pinnable**. Carries its
authored `uses` string (the **Lockfile** key) via the `uses` accessor.

**UsesSite**:
One `uses:` occurrence inside a Document — a parsed **UsesRef** plus the ability to replace the
ref in place. Pin's collect and transform both iterate UsesSites; the "which models carry `uses`"
policy — and parse failure — live only in the UsesSite iterator. Collect returns parsed,
deduplicated UsesRefs, never strings (ADR-0006).

**Pinnable**:
A UsesRef that is remote and not already a commit SHA, so it can be pinned. A ref already written as
a SHA is left untouched (never re-pinned, never an error).

**Pin** (verb):
Replace a `uses:` ref with its locked commit SHA at synthesis time.

**Lockfile**:
Maps `uses:` strings to resolved commit SHAs (`.ghagen.lock.yml`); always holds valid entries.

**PinEntry**:
One resolved pin — a commit SHA plus a resolved-at timestamp.

**Transport**:
The injected HTTP adapter behind `HttpClient`. Returns a response for any status it obtains,
raises `TransportError` for every failure to obtain one, and honours the module deadline —
including reading the body. Every adapter, real or canned, passes the transport conformance table.

**Version tag**:
A `uses:` ref that matches ghagen's declared tag grammar (optional `prefix-`/`prefix/`, optional
`v`, dot-separated integers, each ≤ 10^15 − 1); its **canonical release** is the integer tuple
padded to three and stripped of trailing zeros beyond the third. Refs that are not version tags
(`main`, `release/v1`) are never upgrade candidates. The grammar is declared once, in
`schema/tag-grammar.yml`, and pinned by both suites.

**Bump**:
A version tag strictly newer than the current one, with the same prefix, plus its severity
(major/minor/patch). `pin/versions` is the sole authority on both; the engine consumes Bumps and
never compares versions itself. Equal versions produce no Bump.

**Upgrade report**:
What one `upgrade` run was **asked to check** and what it found — the **Bumps**, the stale lockfile
entries, and a flag per stage recording what the run's mode asked for. The flags are set before the
engine's no-refs early return, so every run carries them, and the rendered output's shape follows
them rather than following what the run happened to find. "Asked for" is not "ran": the lockfile
flag stays true when no lockfile is configured and the stage is skipped.

**UpdatePlan**:
What a caller should **do** about an **Upgrade report** — whether to apply bumps, whether to
refresh the lockfile, what to raise, and under what branch, title, and labels. Every field is a
decision, never data, and a caller never re-derives one from another. Deciding needs the **App**
as well as the report, because one rule turns on `app.lockfilePath`, a fact the serialized report
deliberately does not carry. Its ten-field wire shape (both `--format json` and `--format github`)
is declared once, in `schema/update-plan-fields.yml`, and pinned by both suites.

### Schema

**Snapshot**:
The committed canonical copy of an upstream JSON schema from SchemaStore.

**Drift**:
Divergence between the committed schema Snapshot and the current upstream schema.

**Scope**:
A named node in a Snapshot (`schema/conformance-scopes.yml`) that both ports must bind to a
covering model, and whose declared property set that model must emit in full. A path segment may
be an integer, indexing a `oneOf` alternative. A scope one port cannot bind is a parity failure.

**Gap**:
A scope property both ports intentionally do not model, allow-listed by name in
`schema/conformance-gaps.yml`. Both sweeps hold every row to three claims, not just "listed":
the name must still exist upstream (else stale), must still be uncovered by the model (else the
gap has been closed and the row must go), and the file's own snapshot/scope keys must equal the
sweep's exactly — so a gap entry is a live regression guard against a re-introduced gap, not a
comment that happens to be YAML.

### CLI

**Exit code**:
One of three numbers `main()` returns — `0` success, `1` expected failure, `2` usage error. The
contract is `fixtures/cli-exit-codes.yml`, which both ports drive through their `main()`; the CLI
framework renders the text, `main()` decides the number.

## Relationships

- A **Document** is a **Workflow** or an **Action**.
- A **Workflow** contains **Jobs**, each containing **Steps**.
- The **Emitter** serializes any model to a node; only a **Document** can be emitted to a file.
- Every model declares a **ModelSpec**; the **Emitter** reads it for key names and ordering.
- **Pin** iterates **UsesSites** over each **Document**; only **Pinnable** refs are pinned.
- `upgrade` compares only **version tags** with the same prefix; the comparison lives in
  `pin/versions`, never in a third-party library.
- An **UpdatePlan** is derived from an **Upgrade report** _and_ an **App**; the report alone is not
  enough, and no consumer may reconstruct a plan from `deps upgrade --format json`.

## Surface notes (TypeScript)

- Models are products of **factory functions** (`workflow()`, `job()`, `step()`) over a `data` bag,
  with one shared `Model` class carrying `kind` + **ModelSpec** and providing `walk()` /
  `children()`. Both yield **bare `Model`s** — no key path, no prune protocol: `walk(fn)` is every
  model in this document, root first, depth-first; within a model, its `data` fields in declaration
  order, then its `extras`. That is _traversal_ order, not emission order (emission order is the
  spec's, via `orderedEntries`), and it is the same sequence Python's `walk()` produces.
  Models do not serialize themselves — the Emitter owns all recursion (ADR-0001,
  amended). Each factory is a one-line spec binding, `export const f = defineFactory<M, I>(SPEC)`;
  its doc comment **must** carry `@function`, or TypeDoc reflects it as a Variable and the
  published page moves from `functions/` to `variables/`. A guard test in `models/_base.test.ts`
  enforces the tag on every exported binding.
- `toYaml()` / `toYamlFile()` are **free functions**, narrowed to `WorkflowModel | ActionModel`
  (the **Document** types) so a bare model cannot be serialized to a file.
- Generated types are imported into the models for compile-time author-conformance against the
  schema (ADR-0003); separately, factories enforce their construction-time input contract at
  runtime — unknown input keys raise `ModelInputError` (use `extras`), and a **value grammar**
  declared in a spec's `patterns` (e.g. `ImageSnapshot.version`) is checked against the canonical
  Snapshot's pattern.
- The config module (`config.ts`) solely owns `.ghagen.yml` — discovery, single parse, validation,
  App resolution — returning typed results with errors as values (ADR-0007); `CliError` lives in
  `cli/_errors.ts`. commander runs under `exitOverride()`, applied **recursively after tree
  construction** (`_exitCallback` is per-`Command` and `addCommand()` never copies it), so `main()`
  returns the exit code and the bin shim only assigns it to `process.exitCode`. The synthesis
  pipeline is `synth.ts`'s `render()`, fully synchronous; pin runs last (ADR-0005).
- The upgrade path is three layers with one direction of dependency: `pin/engine` produces an
  **Upgrade report** and never formats; `pin/render` turns that report into a string and never
  writes, exits, or touches the network (`renderUpgradeReport(report, format)` — one function over
  all four formats, `text` the default); `cli/deps` owns stream selection and exit codes only, and
  writes the returned string verbatim. The report's `checkedVersions` / `checkedLockfile` flags
  exist so the renderer never has to re-derive `--mode`, which is what makes the `--format json`
  key set identical for empty and non-empty runs (ADR-0007;
  `docs/specs/0005-typed-engine-report-seam.md` §2.2). All four formats are byte-compared against
  shared goldens in `fixtures/expected/` by both ports.
- `pin/plan.ts` is the sibling of `pin/render.ts` at the same layer: `render` answers "what bytes do
  I write?", `plan` answers "what do I do next?". Both are pure — no network, no filesystem, no
  console, and no clock either: `planUpdate` takes `today` as an argument, the same reasoning
  ADR-0002 applies to construction-time config globals. `planUpdate(app, report, options)` takes the
  **App** for exactly one fact, `app.lockfilePath`, which is why `refreshLockfile` is not
  `report.lockfileStale.length > 0`. `renderUpdatePlan` takes its format **positionally**, matching
  `renderUpgradeReport`, and emits snake_case keys in both encodings because the field names are a
  cross-port wire contract, not this port's interface. `ghagen deps update` is the one command that
  runs a whole automation pass — sweep, write, plan — and prints the plan and nothing else on
  stdout. `check-deps/action.yml` runs the Python port of it; the shell there branches on the plan
  and computes nothing.
- `defaults()`'s nested `run` map is a promoted `DefaultsRunModel` (mirror of Python's
  `DefaultsRun`), so Commented wrappers on `run.shell` / `run.workingDirectory` survive emission.
- `models/registry.ts` is the one `ModelKind` → **ModelSpec** map (`SPECS_BY_KIND`, plus
  `ALL_SPECS`). `satisfies Record<ModelKind, ModelSpec>` makes a missing kind a compile error, so
  "every kind has a spec" is a property of the type rather than of a hand-maintained list. Add a
  `ModelKind` member and its entry together. Every sub-map def with a canonical key order gets its
  own spec and kind (e.g. `workflowCallInput`), which is what keeps emission order equal to
  Python's.
- Tests resolve repo paths via `src/paths.ts`, never via hand-rolled `../../../../` constants.
- The pin transport seam is `HttpClient`, and its contract — the deadline, the totality of
  `TransportError`, and the transport reading the body — lives in its doc comment and is executed
  by the conformance table (`src/pin/transport-contract.ts`) that every adapter runs.
  `HttpResponse` is a **class** an adapter author constructs, not an interface they implement. The
  one intentional asymmetry with Python is the response type: `HttpResponse` here, `Response` there
  (the name `Response` is taken by the platform global), carrying `string` here and `bytes` there,
  matching each stdlib. `TransportError` and `ResolveError` are the only two error types crossing
  the pin/network boundary, and the engine's per-ref recovery depends on that totality.
- A `fieldMap` **value** may not be a decimal-integer string. `OrdinaryOwnPropertyKeys` lists
  array-index keys ahead of creation order, so such a key would jump to the front of `data`
  whatever position the map declares — and Python's `dict`, which has no such rule, would not
  follow. This is the only place the two ports' key-order guarantees are not the same rule;
  `spec.test.ts` asserts no field map has one.

## Example dialogue

> **Dev:** "`toYaml` takes a `Model` — can I pass a step model?"
> **Maintainer:** "The signature is narrowed to `WorkflowModel | ActionModel` — the **Document**
> types. A step model isn't a **Document**, so `toYaml` rejects it at compile time; the **Emitter**
> recurses into it while emitting its containing Document."

> **Dev:** "My lockfile diff shows nine changed lines and I only added one action."
> **Maintainer:** "Both ports write one canonical encoding — every value double-quoted,
> `resolved_at` UTC at whole seconds — and a reader raises `LockfileError` rather than degrading to
> an empty **Lockfile**. `fixtures/expected/lockfile_golden.yml` is the byte oracle both suites
> assert against. The Python port carries one extra write-time guard against a naive timestamp; a
> `Date` is always an absolute instant, so there is nothing here to guard."
