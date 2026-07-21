# Document serialization seam

**Status:** accepted (amended 2026-07-21)

Workflow and Action share a common base type, **Document** — the unit that maps 1:1 to a
generated YAML file. Only a Document exposes `to_yaml()` / `to_yaml_file()` (Python methods;
TypeScript narrows the free `toYaml` / `toYamlFile` to `WorkflowModel | ActionModel`). Every
model still has `to_commented_map()` / `toYamlMap()` for nested serialization, but a bare `Step`,
`Job`, or `Permissions` cannot be serialized to a file.

## Why

The file-producing serializers previously accepted any model, so `step.to_yaml()` was expressible
nonsense. Gating the file-level entry point on Document makes the misuse a type error rather than a
runtime surprise, and gives the duplicated `to_yaml` / `to_yaml_file` logic a single home.

## Consequences

A future reader may notice TypeScript's serializer could structurally accept any `Model` and be
tempted to widen it — this narrowing is deliberate. The private `_to_yaml(model, header)` helper
still takes any model (it recurses through nested `to_commented_map`); only the public surface is
constrained.

## Amendment (2026-07-21): the Emitter owns all recursion

The second architecture review found the recursion split this ADR described — model-side
`to_commented_map()` / `toYamlMap()` calling into the Emitter and back — caused the
Commented/Raw/model/dict/list dispatch to be implemented three times, forced a bidirectional
models↔emitter import dodged with function-local imports, and pushed tests onto private ruamel
internals.

Decision: serialization recursion lives **entirely inside the Emitter**, behind one public
`emit(document, ...)` surface with a single internal node dispatcher. Models carry only data plus
their **ModelSpec** (YAML key names + emission order). `to_commented_map()` / model-side
`toYamlMap()` are removed in both ports.

Unchanged from the original decision: file-level serialization stays gated on **Document** —
`Document.to_yaml()` / `to_yaml_file()` remain the public entry points, now thin delegates to the
Emitter's `emit()`.
