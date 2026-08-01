# ghagen (TypeScript)

The TypeScript/JavaScript implementation of ghagen: factory-built models describing GitHub Actions,
serialized to YAML. Shares its domain vocabulary with the [Python](../python/CONTEXT.md) port — see
[`CONTEXT-MAP.md`](../../CONTEXT-MAP.md).

## Language

### Models

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

**ModelSpec**:
The per-model serialization spec — YAML key names (field → emitted key), an **OrderMode**, the
inline-input wrap map, and per-field emission rules (present-null-when-empty, dynamic-keys
passthrough) — declared next to the factory, consumed by the Emitter and
factories. The single home for the emitted-key fact (`fieldMap`, type-checked with `satisfies`
against the generated schema types); every factory builds through `buildModel`.
_Avoid_: field map, key-order table.

**OrderMode**:
A ModelSpec's emission-order rule — an explicit key list, or alphabetical (extras interleaved).

**CommentNode**:
The Emitter's public, backend-neutral representation of a value plus its attached block/EOL
comment, produced by `toData(..., { comments: true })`.

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

### Schema

**Snapshot**:
The committed canonical copy of an upstream JSON schema from SchemaStore.

**Drift**:
Divergence between the committed schema Snapshot and the current upstream schema.

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

## Surface notes (TypeScript)

- Models are products of **factory functions** (`workflow()`, `job()`, `step()`) over a `data` bag,
  with one shared `Model` class carrying `kind` + **ModelSpec** and providing `walk()` /
  `children()`. Models do not serialize themselves — the Emitter owns all recursion (ADR-0001,
  amended).
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
- `defaults()`'s nested `run` map is a promoted `DefaultsRunModel` (mirror of Python's
  `DefaultsRun`), so Commented wrappers on `run.shell` / `run.workingDirectory` survive emission.
- Tests resolve repo paths via `src/paths.ts`, never via hand-rolled `../../../../` constants.
- The pin transport seam is `HttpClient`, and its contract — the deadline, the totality of
  `TransportError`, and the transport reading the body — lives in its doc comment and is executed
  by the conformance table (`src/pin/transport-contract.ts`) that every adapter runs.
  `HttpResponse` is a **class** an adapter author constructs, not an interface they implement. The
  one intentional asymmetry with Python is the response type: `HttpResponse` here, `Response` there
  (the name `Response` is taken by the platform global), carrying `string` here and `bytes` there,
  matching each stdlib. `TransportError` and `ResolveError` are the only two error types crossing
  the pin/network boundary, and the engine's per-ref recovery depends on that totality.

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
