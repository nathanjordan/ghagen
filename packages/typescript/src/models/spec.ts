import type { Model, ModelKind } from "./_base.js";

/**
 * Auto-wrap rule for one factory input field.
 *
 * Factory inputs may be either a pre-built {@link Model} or a plain-object
 * shorthand; a `WrapRule` promotes the shorthand by calling `factory`. The
 * `mode` selects how the value is inspected before wrapping — mirroring the
 * hand-rolled ladders that previously lived inline in `workflow()`, `job()`,
 * and `on()`.
 */
export interface WrapRule {
  /** Sub-factory that promotes a plain-object shorthand into a Model. */
  readonly factory: (input: never) => Model;
  /**
   * How the value is inspected before wrapping:
   * - `model`       — wrap unless already a Model.
   * - `objectModel` — wrap only when a non-Model object (leaves strings/Raw).
   * - `list`        — map an array, wrapping each non-Model item.
   * - `map`         — map an object's values, wrapping each non-string/-Model.
   * - `dispatch`    — pass booleans/null through, else wrap unless a Model.
   */
  readonly mode: "model" | "objectModel" | "list" | "map" | "dispatch";
}

/**
 * Per-model serialization spec.
 *
 * The single home for one model type's serialization surface: its
 * discriminant `kind`, the camelCase-input → YAML-key `fieldMap`, the canonical
 * emission `order`, and the optional inline-input auto-`wrap` map. Declared next
 * to the factory and read by both the factory (field mapping + wrapping) and the
 * Emitter (`modelToYamlMap` key ordering). Replaces the old per-factory
 * `*_FIELD_MAP` constants and `emitter/key-order.ts` tables.
 */
export interface ModelSpec {
  /** Discriminant assigned to every Model built from this spec. */
  readonly kind: ModelKind;
  /** Maps camelCase input field names to their emitted YAML keys. */
  readonly fieldMap: Readonly<Record<string, string>>;
  /**
   * Emitted YAML key names in canonical order. Keys absent from `order` are
   * appended in insertion order. An empty `order` emits all keys in insertion
   * order (the `on:` section pre-sorts alphabetically before construction).
   */
  readonly order: readonly string[];
  /** Optional inline-input auto-wrap rules, keyed by camelCase field name. */
  readonly wrap?: Readonly<Record<string, WrapRule>>;
}
