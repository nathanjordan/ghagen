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

**Transform**:
A synthesis-time mutation applied to a deep copy of a Document before emission (e.g. the pin transform).
_Avoid_: plugin, hook, middleware.

**Emitter**:
The module that serializes a model tree to YAML — key ordering, comments, block scalars. Owns all
serialization recursion (see ADR-0001, amended); models never serialize themselves.

**ModelSpec**:
The per-model serialization spec — YAML key names (field → emitted key) and emission order —
declared next to the model, consumed by the Emitter.
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

## Surface notes (Python)

- Models are Pydantic classes. **Document** is a base class; **Workflow** and **Action** extend it.
- `to_yaml()` / `to_yaml_file()` are **methods** on Document that delegate to a private emitter
  free function. Nested models expose `to_commented_map()`.
- User input is validated at construction (Pydantic). Schema faithfulness is checked by integration
  tests, not by generated types (see ADR-0003).

## Example dialogue

> **Dev:** "Can I call `to_yaml()` on a **Step**?"
> **Maintainer:** "No — only a **Document** (a **Workflow** or **Action**) serializes to a file. A
> **Step** has `to_commented_map()` for nesting, but it isn't a **Document**."
