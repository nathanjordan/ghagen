import { YAMLMap } from "yaml";
import { captureSourceLocation, type SourceLocation } from "../_source_location.js";
import type { ModelSpec, WrapRule } from "./spec.js";

export type { ModelSpec, WrapRule } from "./spec.js";

// ---- Commented<T> value wrapper ----

const COMMENTED_BRAND: unique symbol = Symbol("ghagen.commented");

/**
 * Branded wrapper that attaches YAML block or end-of-line comments to a value.
 *
 * Use {@link withComment} and {@link withEolComment} to create instances.
 * Wrappers persist in model `data` at runtime; the serialization pipeline
 * unwraps them and emits the comments onto the YAML nodes.
 */
export interface Commented<T> {
  readonly [COMMENTED_BRAND]: true;
  readonly value: T;
  readonly comment?: string;
  readonly eolComment?: string;
}

/** A value that may or may not be wrapped in a {@link Commented}. */
export type Commentable<T> = T | Commented<T>;

/**
 * Attach a block comment (emitted above the field) to a value.
 *
 * The return type is `T` for type-checker ergonomics, but at runtime the
 * returned object is a {@link Commented} wrapper.
 *
 * Chainable: if `value` is already {@link Commented}, the comment field
 * is merged.
 */
export function withComment<T>(value: T, comment: string): T {
  if (isCommented(value)) {
    return {
      [COMMENTED_BRAND]: true as const,
      value: value.value,
      comment,
      eolComment: value.eolComment,
    } as unknown as T;
  }
  return { [COMMENTED_BRAND]: true as const, value, comment } as unknown as T;
}

/**
 * Attach an end-of-line comment to a value.
 *
 * The return type is `T` for type-checker ergonomics, but at runtime the
 * returned object is a {@link Commented} wrapper.
 *
 * Chainable: if `value` is already {@link Commented}, the eolComment field
 * is merged.
 */
export function withEolComment<T>(value: T, eolComment: string): T {
  if (isCommented(value)) {
    return {
      [COMMENTED_BRAND]: true as const,
      value: value.value,
      comment: value.comment,
      eolComment,
    } as unknown as T;
  }
  return { [COMMENTED_BRAND]: true as const, value, eolComment } as unknown as T;
}

/** Type guard for {@link Commented} values. */
export function isCommented(value: unknown): value is Commented<unknown> {
  return typeof value === "object" && value !== null && COMMENTED_BRAND in value;
}

/** Unwrap a {@link Commented} value, returning the inner value or passthrough. */
export function unwrapCommented<T>(value: T | Commented<T>): T {
  if (isCommented(value)) {
    return value.value as T;
  }
  return value as T;
}

// ---- Raw<T> escape hatch ----

const RAW_BRAND: unique symbol = Symbol("ghagen.raw");

/**
 * Branded wrapper that bypasses type constraints during YAML emission.
 *
 * Use this for fields with constrained types (enums, literals) when the
 * value you need isn't covered by the type definition.
 */
export interface Raw<T> {
  readonly [RAW_BRAND]: true;
  readonly value: T;
}

/** Create a Raw value that bypasses type constraints. */
export function raw<T>(value: T): Raw<T> {
  return Object.freeze({ [RAW_BRAND]: true as const, value }) as Raw<T>;
}

/** Type guard for Raw values. */
export function isRaw(value: unknown): value is Raw<unknown> {
  return typeof value === "object" && value !== null && RAW_BRAND in value;
}

// ---- Comment / metadata ----

/** Metadata attachable to any model for comments and escape hatches. */
export interface ModelMeta {
  /** Block comment emitted above this node in YAML. */
  comment?: string;
  /** End-of-line comment. */
  eolComment?: string;
  /** Arbitrary key/values merged into YAML output. */
  extras?: Record<string, unknown>;
  /** Callback to modify the YAMLMap node before emission. */
  postProcess?: (node: YAMLMap) => void;
}

/**
 * Intersect schema fields with optional metadata.
 *
 * Every factory function accepts `WithMeta<SomeInput>`, allowing callers to
 * attach comments, extras, and post-processing hooks alongside the regular
 * input fields.
 *
 * @example
 * ```ts
 * // Metadata fields mix directly into the input object:
 * const s = step({
 *   name: "Build",
 *   run: withEolComment("npm run build", "requires Node 20"),
 *   comment: "Compile the project",
 * });
 * ```
 */
export type WithMeta<T> = T & ModelMeta;

const META_KEYS = new Set<string>(["comment", "eolComment", "extras", "postProcess"]);

/** Split a WithMeta<T> input into [dataFields, meta]. */
export function extractMeta<T extends object>(input: T): [Omit<T, keyof ModelMeta>, ModelMeta] {
  const data: Record<string, unknown> = {};
  const meta: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(input)) {
    if (META_KEYS.has(key)) {
      meta[key] = value;
    } else {
      data[key] = value;
    }
  }
  return [data as Omit<T, keyof ModelMeta>, meta as ModelMeta];
}

// ---- Model base class ----

/** Union of all concrete model `kind` discriminants. */
export type ModelKind =
  | "step"
  | "job"
  | "workflow"
  | "action"
  | "on"
  | "pushTrigger"
  | "prTrigger"
  | "scheduleTrigger"
  | "workflowDispatch"
  | "workflowDispatchInput"
  | "workflowCall"
  | "workflowCallInput"
  | "workflowCallOutput"
  | "workflowCallSecret"
  | "permissions"
  | "strategy"
  | "matrix"
  | "concurrency"
  | "defaults"
  | "defaultsRun"
  | "environment"
  | "container"
  | "service"
  | "imageSnapshot"
  | "actionInput"
  | "actionOutput"
  | "branding"
  | "compositeRuns"
  | "dockerRuns"
  | "nodeRuns";

/**
 * The one concrete model type for every ghagen node.
 *
 * A `Model` carries its `data` bag, `meta`, and a {@link ModelSpec} — the spec
 * supplies both the discriminant `kind` and the emission key order, so there is
 * no per-type subclass. Factories build the right kind by passing the matching
 * spec; the discriminated-union aliases below (e.g. {@link StepModel}) narrow a
 * `Model` by its `kind` for callers.
 *
 * Models are intentionally NOT frozen — `data` and `meta` must remain
 * runtime-mutable so synthesis-time transforms (like `PinTransform`) can
 * rewrite fields after a `cloneModel` deep copy.
 */
export class Model {
  readonly spec: ModelSpec;
  readonly data: Record<string, unknown>;
  readonly meta: ModelMeta;
  /**
   * Source file/line that constructed this model, captured via stack
   * walking at factory call time. Skips frames inside `/ghagen/` and
   * `/node_modules/` so the location reflects user code. May be `null`
   * when the model is constructed entirely from inside ghagen internals.
   */
  readonly sourceLocation: SourceLocation | null;

  constructor(
    spec: ModelSpec,
    data: Record<string, unknown>,
    meta: ModelMeta,
    sourceLocation?: SourceLocation | null,
  ) {
    this.spec = spec;
    this.data = data;
    this.meta = meta;
    this.sourceLocation = sourceLocation !== undefined ? sourceLocation : captureSourceLocation();
  }

  /** This model's discriminant, sourced from its spec. */
  get kind(): ModelKind {
    return this.spec.kind;
  }

  /** Deep clone carrying the same spec. */
  clone(): Model {
    return new Model(this.spec, cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }

  /** Yield every child Model, in traversal order: data fields, then extras.
   *
   * Extras live on `meta` rather than `data`, so they need their own pass —
   * without it `walk()` never sees a model nested in `extras`, and both
   * `iterUsesSites` and `dedentSteps` skip it. Python reaches extras through
   * its `model_fields` loop and orders them last; this matches.
   *
   * This is *traversal* order, not emission order — emission order is the
   * spec's, resolved by `orderedEntries` in the emitter. */
  *children(): Iterable<Model> {
    for (const value of Object.values(this.data)) {
      yield* scanForModels(value);
    }
    for (const value of Object.values(this.meta.extras ?? {})) {
      yield* scanForModels(value);
    }
  }

  /** Depth-first pre-order visit of this model and every descendant.
   *
   * The root is visited first. Read the passed models to inspect the tree, or
   * mutate their `data` in place (e.g. the pin transform rewrites `uses`). */
  walk(fn: (model: Model) => void): void {
    function visit(model: Model) {
      fn(model);
      for (const child of model.children()) {
        visit(child);
      }
    }
    visit(this);
  }
}

// ---- Model kind aliases (discriminated narrowing over the single Model) ----

/** A {@link Model} narrowed to a specific `kind` discriminant. */
export type ModelOf<K extends ModelKind> = Model & { readonly kind: K };

export type StepModel = ModelOf<"step">;
export type JobModel = ModelOf<"job">;
export type WorkflowModel = ModelOf<"workflow">;
export type ActionModel = ModelOf<"action">;
export type OnModel = ModelOf<"on">;
export type PushTriggerModel = ModelOf<"pushTrigger">;
export type PRTriggerModel = ModelOf<"prTrigger">;
export type ScheduleTriggerModel = ModelOf<"scheduleTrigger">;
export type WorkflowDispatchModel = ModelOf<"workflowDispatch">;
export type WorkflowDispatchInputModel = ModelOf<"workflowDispatchInput">;
export type WorkflowCallModel = ModelOf<"workflowCall">;
export type WorkflowCallInputModel = ModelOf<"workflowCallInput">;
export type WorkflowCallOutputModel = ModelOf<"workflowCallOutput">;
export type WorkflowCallSecretModel = ModelOf<"workflowCallSecret">;
export type PermissionsModel = ModelOf<"permissions">;
export type StrategyModel = ModelOf<"strategy">;
export type MatrixModel = ModelOf<"matrix">;
export type ConcurrencyModel = ModelOf<"concurrency">;
export type DefaultsModel = ModelOf<"defaults">;
export type DefaultsRunModel = ModelOf<"defaultsRun">;
export type EnvironmentModel = ModelOf<"environment">;
export type ContainerModel = ModelOf<"container">;
export type ServiceModel = ModelOf<"service">;
export type ImageSnapshotModel = ModelOf<"imageSnapshot">;
export type ActionInputModel = ModelOf<"actionInput">;
export type ActionOutputModel = ModelOf<"actionOutput">;
export type BrandingModel = ModelOf<"branding">;
export type CompositeRunsModel = ModelOf<"compositeRuns">;
export type DockerRunsModel = ModelOf<"dockerRuns">;
export type NodeRunsModel = ModelOf<"nodeRuns">;

/**
 * A top-level model that maps 1:1 to a generated YAML file (ADR-0001).
 *
 * Only a Workflow or Action is a Document — the sole models that may be
 * serialized to a file via {@link toYaml} / {@link toYamlFile}. Nested
 * models (steps, jobs, …) are serialized by the emitter for embedding but are
 * not Documents. Models carry only data + spec; the recursion lives entirely
 * in the emitter (ADR-0001 amendment).
 */
export type Document = WorkflowModel | ActionModel;

// ---- Construction-time input validation ----

/**
 * Why a factory rejected its input — a discriminated data shape, not a
 * callback, so callers can branch on `reason` and the shared conformance
 * sweep can read the grammar back out.
 *
 * - `unknownKeys` — input carried keys the model's `fieldMap` does not name
 *   and the spec does not declare `dynamicKeys`. The peer of Python's
 *   `extra="forbid"` (`models/_base.py`).
 * - `pattern` — a string field's value fell outside the grammar its spec
 *   declares in {@link ModelSpec.patterns}.
 * - `integerKey` — a user-supplied YAML key (dynamic key or `extras` key) is a
 *   decimal-integer string, which this port cannot keep in its declared
 *   position. See {@link isIntegerLikeKey}.
 */
export type ModelInputProblem =
  | { readonly reason: "unknownKeys"; readonly keys: readonly string[] }
  | { readonly reason: "integerKey"; readonly keys: readonly string[] }
  | {
      readonly reason: "pattern";
      readonly field: string;
      readonly value: string;
      readonly pattern: string;
    };

function formatModelInputProblem(kind: ModelKind, problem: ModelInputProblem): string {
  if (problem.reason === "unknownKeys") {
    return (
      `${kind}(): unknown input ${problem.keys.length === 1 ? "key" : "keys"} ` +
      `${problem.keys.map((k) => JSON.stringify(k)).join(", ")}. ` +
      `Use \`extras\` for unmodeled YAML keys.`
    );
  }
  if (problem.reason === "integerKey") {
    return (
      `${kind}(): integer-like YAML ${problem.keys.length === 1 ? "key" : "keys"} ` +
      `${problem.keys.map((k) => JSON.stringify(k)).join(", ")}. ` +
      `A decimal-integer key cannot hold its position in JavaScript object ` +
      `key order, so the two ports would emit different YAML. Prefix it ` +
      `(e.g. "v2") or place the value under a named parent key.`
    );
  }
  return (
    `${kind}(): ${problem.field} ${JSON.stringify(problem.value)} must match ` +
    `${problem.pattern}. Wrap the value in \`raw()\` to bypass the grammar.`
  );
}

/**
 * A decimal-integer string key — one JavaScript enumerates ahead of insertion
 * order.
 *
 * `OrdinaryOwnPropertyKeys` lists array-index-like keys first, in ascending
 * numeric order, then the remaining string keys in creation order. A YAML key
 * of `"2"` therefore jumps to the front of `data` (and of `toData`'s result
 * record) no matter where it was written, while Python's `dict` leaves it
 * where it was put — so the same input emits different YAML in the two ports.
 * ghagen rejects such keys rather than trying to preserve them.
 *
 * Equivalent to `String(Number.parseInt(key, 10)) === key`, which is the shape
 * the `fieldMap` guard in `spec.test.ts` has always used: `"0"`, `"1"`, `"-1"`
 * match; `"01"`, `"-0"`, `"1.0"`, `"+1"` do not. `"-1"` is not in fact an
 * array index, so rejecting it is marginally over-strict — deliberately kept,
 * so that one regex covers the declared keys and the user-supplied ones alike.
 *
 * The peer of `_integer_like_key` in `models/_base.py`.
 */
export function isIntegerLikeKey(key: string): boolean {
  return /^(0|-?[1-9][0-9]*)$/.test(key);
}

/** Throw when any of *keys* is integer-like. */
function rejectIntegerLikeKeys(kind: ModelKind, keys: readonly string[]): void {
  const bad = keys.filter(isIntegerLikeKey);
  if (bad.length > 0) {
    throw new ModelInputError(kind, { reason: "integerKey", keys: bad });
  }
}

/**
 * Thrown by a factory when its input violates the model's construction-time
 * contract. The peer of Pydantic's `ValidationError` on the Python side —
 * parity is of the invariant, not of the exception class.
 */
export class ModelInputError extends Error {
  constructor(
    readonly kind: ModelKind,
    readonly problem: ModelInputProblem,
  ) {
    super(formatModelInputProblem(kind, problem));
    this.name = "ModelInputError";
  }
}

/**
 * Map camelCase input fields to YAML keys and apply the spec's inline-input
 * auto-wrap rules, returning the resulting `data` record (no Model built).
 *
 * Replaces the hand-rolled promotion ladders that lived inside `workflow()`,
 * `job()`, and `on()`. A `Commented` wrapper on a field is peeled before
 * wrapping and re-applied after, so `withComment(...)` survives around a
 * plain-object shorthand.
 *
 * This is the single input→`data` path in the port, so it is where the two
 * construction-time invariants live:
 *
 * - an input key not named in `fieldMap` throws {@link ModelInputError} unless
 *   the spec declares `dynamicKeys` (the peer of Python's `extra="forbid"`);
 * - a string value for a field named in `spec.patterns` must match that
 *   grammar. `Raw` values are objects, not strings, so the escape hatch stays
 *   opt-in exactly as it does in Python.
 *
 * When `spec.dynamicKeys` is set, any input key not named in `fieldMap` (after
 * `extractMeta` has removed the meta keys) passes straight through to `data`
 * instead of being dropped — the declared path for dynamic axes (`matrix()`).
 *
 * The loop iterates `Object.entries(spec.fieldMap)`, so `data`'s insertion
 * order is the **`fieldMap` declaration order**, whatever order the caller
 * supplied the input keys in — and under the default `explicit`
 * {@link OrderMode} that is exactly the emitted key order (`orderedEntries`
 * returns `Object.entries(data)` unchanged). The field map is therefore the one
 * place emission order is stated; there is no `order` array beside it to drift.
 * `OrdinaryOwnPropertyKeys` would list integer-like string keys first, ahead of
 * creation order, so no emitted YAML key may be a decimal integer string — a
 * constraint Python's `dict` does not have. That covers all three ways a key
 * reaches the record: `fieldMap` values (no field map in either port has one,
 * asserted by `spec.test.ts`), the dynamic-key passthrough below, and the
 * `extras` merge ({@link buildModel}). The latter two are user-supplied, so
 * they are rejected at construction — see {@link isIntegerLikeKey}.
 */
export function buildYamlData(
  spec: ModelSpec,
  data: Record<string, unknown>,
): Record<string, unknown> {
  const wrap = spec.wrap ?? {};
  const patterns = spec.patterns ?? {};
  const yamlData: Record<string, unknown> = {};

  if (!spec.dynamicKeys) {
    const known = new Set(Object.keys(spec.fieldMap));
    const unknown = Object.keys(data).filter((key) => !known.has(key));
    if (unknown.length > 0) {
      throw new ModelInputError(spec.kind, { reason: "unknownKeys", keys: unknown });
    }
  }

  for (const [camelKey, yamlKey] of Object.entries(spec.fieldMap)) {
    let value = data[camelKey];
    if (value === undefined) {
      continue;
    }

    // Peel a Commented wrapper before auto-wrapping, re-apply it after.
    let commented: { comment?: string; eolComment?: string } | null = null;
    if (isCommented(value)) {
      commented = { comment: value.comment, eolComment: value.eolComment };
      value = value.value;
    }

    // Value grammar, checked on the peeled value so `withComment(...)` cannot
    // defeat it and skipped for non-strings so `raw()` stays the escape hatch.
    const pattern = patterns[camelKey];
    if (pattern !== undefined && typeof value === "string" && !pattern.test(value)) {
      throw new ModelInputError(spec.kind, {
        reason: "pattern",
        field: camelKey,
        value,
        pattern: pattern.source,
      });
    }

    const rule = wrap[camelKey];
    if (rule !== undefined) {
      value = applyWrapRule(rule, value);
    }

    if (commented) {
      if (commented.comment) {
        value = withComment(value, commented.comment);
      }
      if (commented.eolComment) {
        value = withEolComment(value, commented.eolComment);
      }
    }

    yamlData[yamlKey] = value;
  }

  // Dynamic-key passthrough: input keys not named in `fieldMap` reach `data`
  // as-is (e.g. matrix axis keys like "node-version"), keeping the factory on
  // the common `buildModel` path.
  if (spec.dynamicKeys) {
    const mapped = new Set(Object.keys(spec.fieldMap));
    const dynamic = Object.keys(data).filter((key) => !mapped.has(key));
    rejectIntegerLikeKeys(spec.kind, dynamic);
    for (const key of dynamic) {
      const value = data[key];
      if (value !== undefined) {
        yamlData[key] = value;
      }
    }
  }

  return yamlData;
}

/**
 * Build a Model of the spec's kind from raw camelCase input — the common
 * factory path. Thin wrapper over {@link buildYamlData}.
 *
 * `extras` is the second channel by which a user-chosen YAML key reaches the
 * emitted map, so it is checked for integer-like keys here, on the same rule
 * {@link buildYamlData} applies to dynamic keys.
 */
export function buildModel<M extends Model = Model>(
  spec: ModelSpec,
  data: Record<string, unknown>,
  meta: ModelMeta,
): M {
  if (meta.extras !== undefined) {
    rejectIntegerLikeKeys(spec.kind, Object.keys(meta.extras));
  }
  return new Model(spec, buildYamlData(spec, data), meta) as M;
}

/**
 * Build the factory function for one {@link ModelSpec}.
 *
 * The single implementation of "split meta off the input, map fields through
 * the spec, return a Model of the spec's kind" — the body every model factory
 * used to repeat verbatim. Declare a factory by binding its spec and its two
 * type parameters; the `Record<string, unknown>` casts that each factory
 * carried live here once.
 *
 * The returned closure is a plain arrow function that wraps nothing in
 * `try`/`catch`, so a {@link ModelInputError} from {@link buildYamlData}
 * propagates with the caller's frame intact, and `captureSourceLocation`
 * (which skips internal frames by predicate, not by a fixed count) still
 * attributes the model to user code.
 *
 * Mark the resulting `const` with `@function` in its doc comment so TypeDoc
 * renders it as a function, not a variable.
 */
export function defineFactory<M extends Model, I extends object>(
  spec: ModelSpec,
): (input: WithMeta<I>) => M {
  return (input: WithMeta<I>): M => {
    const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
    return buildModel<M>(spec, data as Record<string, unknown>, meta);
  };
}

/** Apply one {@link WrapRule} to a field value; see {@link WrapRule.mode}. */
function applyWrapRule(rule: WrapRule, value: unknown): unknown {
  const factory = rule.factory as (input: unknown) => Model;
  switch (rule.mode) {
    case "model":
      return isModel(value) ? value : factory(value);
    case "objectModel":
      return typeof value === "object" && value !== null && !isModel(value)
        ? factory(value)
        : value;
    case "list":
      return Array.isArray(value)
        ? value.map((item) => (isModel(item) ? item : factory(item)))
        : value;
    case "map": {
      if (typeof value !== "object" || value === null || isModel(value)) {
        return value;
      }
      const out: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(value)) {
        out[k] = typeof v === "string" || isModel(v) ? v : factory(v);
      }
      return out;
    }
    case "dispatch":
      if (typeof value === "boolean" || value === null) {
        return value;
      }
      return isModel(value) ? value : factory(value);
  }
}

// ---- children() helpers ----

function* scanForModels(value: unknown): Iterable<Model> {
  if (value instanceof Model) {
    yield value;
  } else if (isCommented(value)) {
    yield* scanForModels(value.value);
  } else if (Array.isArray(value)) {
    for (const item of value) {
      yield* scanForModels(item);
    }
  } else if (typeof value === "object" && value !== null && !isRaw(value)) {
    for (const v of Object.values(value)) {
      yield* scanForModels(v);
    }
  }
}

// ---- isModel / cloneModel ----

/** Type guard for Model values. */
export function isModel(value: unknown): value is Model {
  return value instanceof Model;
}

/**
 * Deep-clone a Model so synthesis-time transforms can mutate it without
 * touching the user's original.
 */
export function cloneModel<M extends Model>(model: M): M {
  return model.clone() as M;
}

// ---- Deep clone helpers ----

/**
 * Deep-clone any value, preserving symbol-branded wrappers and Model
 * subclass types.
 *
 * `structuredClone` is intentionally NOT used because:
 *   - it silently drops Symbol-keyed properties (would lose `RAW_BRAND`
 *     and `COMMENTED_BRAND`), and
 *   - it throws on functions (would crash on `meta.postProcess`).
 *
 * Functions and the `sourceLocation` reference are passed through by
 * reference; everything else (Models, Raw values, plain objects, arrays)
 * is cloned.
 */
function cloneValueInternal(value: unknown): unknown {
  // Primitives (and null/undefined)
  if (value === null || value === undefined) {
    return value;
  }
  const t = typeof value;
  if (t !== "object" && t !== "function") {
    return value;
  }

  // Functions are passed by reference (no way to deep-clone a closure)
  if (t === "function") {
    return value;
  }

  // Raw<T> — preserve the symbol brand
  if (isRaw(value)) {
    return { [RAW_BRAND]: true as const, value: cloneValueInternal(value.value) };
  }

  // Commented<T> — preserve the symbol brand and recurse into the value
  if (isCommented(value)) {
    return {
      [COMMENTED_BRAND]: true as const,
      value: cloneValueInternal(value.value),
      comment: value.comment,
      eolComment: value.eolComment,
    };
  }

  // Model — delegate to subclass clone()
  if (value instanceof Model) {
    return value.clone();
  }

  // Date — recreate
  if (value instanceof Date) {
    return new Date(value.getTime());
  }

  // Array — recurse
  if (Array.isArray(value)) {
    return value.map((item) => cloneValueInternal(item));
  }

  // Plain object — recurse
  return cloneRecord(value as Record<string, unknown>);
}

function cloneRecord(obj: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    out[k] = cloneValueInternal(v);
  }
  return out;
}

function cloneMeta(meta: ModelMeta): ModelMeta {
  const out: ModelMeta = {};
  if (meta.comment !== undefined) {
    out.comment = meta.comment;
  }
  if (meta.eolComment !== undefined) {
    out.eolComment = meta.eolComment;
  }
  if (meta.extras !== undefined) {
    out.extras = cloneRecord(meta.extras);
  }
  // postProcess is a function — pass by reference.
  if (meta.postProcess !== undefined) {
    out.postProcess = meta.postProcess;
  }
  return out;
}
