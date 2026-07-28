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
 * How a model's emitted keys are ordered.
 *
 * - `explicit` — the listed `keys` come first, in that order; any remaining
 *   keys (dynamic passthroughs, extras under `afterOrdered`) follow in
 *   insertion order.
 * - `alphabetical` — every key, including extras, is sorted at emit time. This
 *   is the declarative replacement for the old "empty order" signal, which the
 *   two Emitters disagreed on (Python sorted; TS kept insertion order).
 *
 * The sort now lives in the Emitter, in one place, identically for both ports.
 */
export type OrderMode =
  | { readonly kind: "explicit"; readonly keys: readonly string[] }
  | { readonly kind: "alphabetical" };

/**
 * Per-model serialization spec.
 *
 * The single home for one model type's serialization surface: its
 * discriminant `kind`, the camelCase-input → YAML-key `fieldMap`, the canonical
 * emission `order`, and the optional inline-input auto-`wrap` map. Declared next
 * to the factory and read by both the factory (field mapping + wrapping) and the
 * Emitter (`modelToYamlMap` key ordering). Replaces the old per-factory
 * `*_FIELD_MAP` constants and `emitter/key-order.ts` tables.
 *
 * Every gap that factories once filled by hand is now declarable here: the
 * ordering {@link OrderMode}, extras placement, dynamic-key passthrough, and
 * the present-null-when-empty rule. This keeps `buildModel` the only
 * input→Model path — no factory hand-rolls `data`.
 */
export interface ModelSpec {
  /** Discriminant assigned to every Model built from this spec. */
  readonly kind: ModelKind;
  /** Maps camelCase input field names to their emitted YAML keys. */
  readonly fieldMap: Readonly<Record<string, string>>;
  /** How emitted keys are ordered — see {@link OrderMode}. */
  readonly order: OrderMode;
  /** Optional inline-input auto-wrap rules, keyed by camelCase field name. */
  readonly wrap?: Readonly<Record<string, WrapRule>>;
  /**
   * Pass input keys not named in `fieldMap` straight through to `data` instead
   * of dropping them. Lets a factory (e.g. `matrix()`) route dynamic axis keys
   * through {@link buildModel} while `fieldMap` still names only its static
   * fields. Defaults to `false`.
   */
  readonly dynamicKeys?: boolean;
  /**
   * Where `meta.extras` land relative to the ordered keys.
   *
   * - `afterOrdered` (default) — extras are appended after the ordered keys.
   * - `withinOrder` — extras join the key pool before ordering, so an
   *   `explicit` order may pull them forward and the rest follow in insertion
   *   order.
   *
   * Under `alphabetical` order this field is moot: extras always participate in
   * the single sort.
   */
  readonly extrasPlacement?: "afterOrdered" | "withinOrder";
  /**
   * YAML keys whose value, when it resolves to an empty map, is emitted as a
   * bare null key (`key:`) instead of `key: {}`. The declarative replacement
   * for the model-layer present-null smuggle. Defaults to empty.
   */
  readonly presentNullWhenEmpty?: readonly string[];
}
