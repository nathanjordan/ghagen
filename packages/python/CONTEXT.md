# ghagen (Python)

The Python implementation of ghagen: Pydantic models describing GitHub Actions, serialized to YAML.
Shares its domain vocabulary with the [TypeScript](../typescript/CONTEXT.md) port — see
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
A synthesis-time mutation applied to a deep copy of a Document before emission (e.g. the pin transform).
_Avoid_: plugin, hook, middleware.

**Emitter**:
The module that serializes a model tree to YAML — key ordering, comments, block scalars. Owns all
serialization recursion (see ADR-0001, amended); models never serialize themselves. Also exposes
the plain-data observation surface `to_data()` — the supported way to inspect a model's emitted
structure (see **CommentNode**).
Comment _geometry_ — the end-of-line gutter (`EOL_GUTTER`, 2 columns) and the block-comment
column — is a named module, `emitter/comment_geometry.py`, applied as a node pass before the dump.
No Emitter pass rewrites emitted text.

**ModelSpec**:
The per-model serialization spec — YAML key names (field → emitted key), an **OrderMode**, and
per-field emission rules (present-null-when-empty) — declared next to the model, consumed by the
Emitter. The single home for the emitted-key fact: models carry no `serialization_alias`.
_Avoid_: field map, key-order table.

**OrderMode**:
A ModelSpec's emission-order rule — an explicit key list, or alphabetical (extras interleaved).

**CommentNode**:
The Emitter's public, backend-neutral representation of a value plus its attached block/EOL
comment, produced by `to_data(..., comments=True)`.

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

### Schema

**Snapshot**:
The committed canonical copy of an upstream JSON schema from SchemaStore.

**Drift**:
Divergence between the committed schema Snapshot and the current upstream schema.

## Relationships

- A **Document** is a **Workflow** or an **Action**.
- A **Workflow** contains **Jobs**, each containing **Steps**.
- The **Emitter** serializes any model to a node; only a **Document** can be emitted to a file.
- Every model declares a **ModelSpec**; the **Emitter** reads it for key names and ordering.
- **Pin** iterates **UsesSites** over each **Document**; only **Pinnable** refs are pinned.

## Surface notes (Python)

- Models are Pydantic classes. **Document** is a base class; **Workflow** and **Action** extend it.
- `to_yaml()` / `to_yaml_file()` are **methods** on Document that delegate to the Emitter's
  `emit()` / `emit_file()`. Models do not serialize themselves — the Emitter owns all recursion
  (ADR-0001, amended).
- User input is validated at construction (Pydantic). Schema faithfulness is checked by integration
  tests, not by generated types (see ADR-0003).
- The config module (`config.py`) solely owns `.ghagen.yml` — discovery, single parse, validation,
  App resolution — returning typed results with errors as values (ADR-0007); `CliError` is
  CLI-local. The synthesis pipeline is `synth.render()`; pin runs last (ADR-0005).
- `_package_paths.py` is the shared "is this file ghagen-internal / a user file" predicate (peer of
  the TS `_package_paths.ts`). Tests resolve repo paths via `ghagen_schema.paths`, never via
  hand-rolled `parents[N]`.

## Example dialogue

> **Dev:** "Can I call `to_yaml()` on a **Step**?"
> **Maintainer:** "No — only a **Document** (a **Workflow** or **Action**) serializes to a file. A
> **Step** doesn't serialize itself at all; the **Emitter** recurses into it while emitting the
> Document that contains it."
