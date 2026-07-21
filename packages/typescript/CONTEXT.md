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

**Transform**:
A synthesis-time mutation applied to a clone of a Document before emission (e.g. the pin transform).
_Avoid_: plugin, hook, middleware.

**Emitter**:
The module that serializes a model tree to YAML — key ordering, comments, block scalars. Owns all
serialization recursion (see ADR-0001, amended); models never serialize themselves.

**ModelSpec**:
The per-model serialization spec — YAML key names (field → emitted key), emission order, and the
inline-input wrap map — declared next to the factory, consumed by the Emitter and factories.
_Avoid_: field map, key-order table.

### Pinning

**UsesRef**:
A parsed `owner/repo[/path]@ref` action reference; knows whether it is **Pinnable**.

**UsesSite**:
One `uses:` occurrence inside a Document — a parsed **UsesRef** plus the ability to replace the
ref in place. Pin's collect and transform both iterate UsesSites; the "which models carry `uses`"
policy lives only in the UsesSite iterator.

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

## Surface notes (TypeScript)

- Models are products of **factory functions** (`workflow()`, `job()`, `step()`) over a `data` bag,
  with one shared `Model` class carrying `kind` + **ModelSpec** and providing `walk()` /
  `children()`. Models do not serialize themselves — the Emitter owns all recursion (ADR-0001,
  amended).
- `toYaml()` / `toYamlFile()` are **free functions**, narrowed to `WorkflowModel | ActionModel`
  (the **Document** types) so a bare model cannot be serialized to a file.
- Generated types are imported into the models for compile-time author-conformance against the
  schema (see ADR-0003). There is no runtime validation.

## Example dialogue

> **Dev:** "`toYaml` takes a `Model` — can I pass a step model?"
> **Maintainer:** "The signature is narrowed to `WorkflowModel | ActionModel` — the **Document**
> types. A step model isn't a **Document**, so `toYaml` rejects it at compile time; the **Emitter**
> recurses into it while emitting its containing Document."
