# Document serialization seam

**Status:** accepted

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
