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
  | "permissions"
  | "strategy"
  | "matrix"
  | "concurrency"
  | "defaults"
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

  /** Yield child Models found in data. */
  *children(): Iterable<{ key: string; model: Model }> {
    for (const [key, value] of Object.entries(this.data)) {
      yield* scanForModels(key, value);
    }
  }

  /** Depth-first walk. `fn` receives each model + key path.
   * Return false to skip children. */
  walk(fn: (model: Model, path: string[]) => void | false): void {
    function visit(model: Model, path: string[]) {
      if (fn(model, path) === false) {
        return;
      }
      for (const { key, model: child } of model.children()) {
        visit(child, [...path, key]);
      }
    }
    visit(this, []);
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
export type PermissionsModel = ModelOf<"permissions">;
export type StrategyModel = ModelOf<"strategy">;
export type MatrixModel = ModelOf<"matrix">;
export type ConcurrencyModel = ModelOf<"concurrency">;
export type DefaultsModel = ModelOf<"defaults">;
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

/**
 * Map camelCase input fields to YAML keys and apply the spec's inline-input
 * auto-wrap rules, returning the resulting `data` record (no Model built).
 *
 * Replaces the hand-rolled promotion ladders that lived inside `workflow()`,
 * `job()`, and `on()`. A `Commented` wrapper on a field is peeled before
 * wrapping and re-applied after, so `withComment(...)` survives around a
 * plain-object shorthand. `on()` calls this directly because it sorts keys
 * before constructing its Model.
 */
export function buildYamlData(
  spec: ModelSpec,
  data: Record<string, unknown>,
): Record<string, unknown> {
  const wrap = spec.wrap ?? {};
  const yamlData: Record<string, unknown> = {};

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

  return yamlData;
}

/**
 * Build a Model of the spec's kind from raw camelCase input — the common
 * factory path. Thin wrapper over {@link buildYamlData}.
 */
export function buildModel<M extends Model = Model>(
  spec: ModelSpec,
  data: Record<string, unknown>,
  meta: ModelMeta,
): M {
  return new Model(spec, buildYamlData(spec, data), meta) as M;
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

function* scanForModels(key: string, value: unknown): Iterable<{ key: string; model: Model }> {
  if (value instanceof Model) {
    yield { key, model: value };
  } else if (isCommented(value)) {
    yield* scanForModels(key, value.value);
  } else if (Array.isArray(value)) {
    for (const item of value) {
      yield* scanForModels(key, item);
    }
  } else if (typeof value === "object" && value !== null && !isRaw(value)) {
    for (const [k, v] of Object.entries(value)) {
      yield* scanForModels(k, v);
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
