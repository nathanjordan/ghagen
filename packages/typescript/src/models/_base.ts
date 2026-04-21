import type { YAMLMap } from "yaml";
import { captureSourceLocation, type SourceLocation } from "../_source_location.js";

// ---- Commented<T> value wrapper ----

const COMMENTED_BRAND: unique symbol = Symbol("ghagen.commented");

/**
 * Branded wrapper that attaches YAML block or end-of-line comments to a value.
 *
 * Use {@link withComment} and {@link withEolComment} to create instances.
 * Wrappers persist in model `_data` at runtime; the serialization pipeline
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
    return { [COMMENTED_BRAND]: true as const, value: value.value, comment, eolComment: value.eolComment } as unknown as T;
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
    return { [COMMENTED_BRAND]: true as const, value: value.value, comment: value.comment, eolComment } as unknown as T;
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

const META_KEYS = new Set<string>([
  "comment",
  "eolComment",
  "extras",
  "postProcess",
]);

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

// ---- Internal model ----

const MODEL_BRAND: unique symbol = Symbol("ghagen.model");

/** Base type for all ghagen model objects. */
export interface Model {
  readonly [MODEL_BRAND]: true;
  readonly _kind: string;
  readonly _data: Record<string, unknown>;
  readonly _meta: ModelMeta;
  readonly _keyOrder: readonly string[];
  /**
   * Source file/line that constructed this model, captured via stack
   * walking at factory call time. Skips frames inside `/ghagen/` and
   * `/node_modules/` so the location reflects user code. May be `null`
   * when the model is constructed entirely from inside ghagen internals.
   */
  readonly _sourceLocation: SourceLocation | null;
}

// Branded subtypes for type safety in function signatures

/** Branded model type produced by the {@link step} factory. */
export interface StepModel extends Model {
  readonly _kind: "step";
}
/** Branded model type produced by the {@link job} factory. */
export interface JobModel extends Model {
  readonly _kind: "job";
}
/** Branded model type produced by the {@link workflow} factory. */
export interface WorkflowModel extends Model {
  readonly _kind: "workflow";
}
/** Branded model type produced by the {@link action} factory. */
export interface ActionModel extends Model {
  readonly _kind: "action";
}
/** Branded model type produced by the {@link on} factory. */
export interface OnModel extends Model {
  readonly _kind: "on";
}
/** Branded model type produced by the {@link pushTrigger} factory. */
export interface PushTriggerModel extends Model {
  readonly _kind: "pushTrigger";
}
/** Branded model type produced by the {@link prTrigger} factory. */
export interface PRTriggerModel extends Model {
  readonly _kind: "prTrigger";
}
/** Branded model type produced by the {@link scheduleTrigger} factory. */
export interface ScheduleTriggerModel extends Model {
  readonly _kind: "scheduleTrigger";
}
/** Branded model type produced by the {@link workflowDispatch} factory. */
export interface WorkflowDispatchModel extends Model {
  readonly _kind: "workflowDispatch";
}
/** Branded model type produced by the {@link workflowCall} factory. */
export interface WorkflowCallModel extends Model {
  readonly _kind: "workflowCall";
}
/** Branded model type produced by the {@link permissions} factory. */
export interface PermissionsModel extends Model {
  readonly _kind: "permissions";
}
/** Branded model type produced by the {@link strategy} factory. */
export interface StrategyModel extends Model {
  readonly _kind: "strategy";
}
/** Branded model type produced by the {@link matrix} factory. */
export interface MatrixModel extends Model {
  readonly _kind: "matrix";
}
/** Branded model type produced by the {@link concurrency} factory. */
export interface ConcurrencyModel extends Model {
  readonly _kind: "concurrency";
}
/** Branded model type produced by the {@link defaults} factory. */
export interface DefaultsModel extends Model {
  readonly _kind: "defaults";
}
/** Branded model type produced by the {@link environment} factory. */
export interface EnvironmentModel extends Model {
  readonly _kind: "environment";
}
/** Branded model type produced by the {@link container} factory. */
export interface ContainerModel extends Model {
  readonly _kind: "container";
}
/** Branded model type produced by the {@link service} factory. */
export interface ServiceModel extends Model {
  readonly _kind: "service";
}
/** Branded model type produced by the {@link actionInputDef} factory. */
export interface ActionInputModel extends Model {
  readonly _kind: "actionInput";
}
/** Branded model type produced by the {@link actionOutputDef} factory. */
export interface ActionOutputModel extends Model {
  readonly _kind: "actionOutput";
}
/** Branded model type produced by the {@link branding} factory. */
export interface BrandingModel extends Model {
  readonly _kind: "branding";
}
/** Branded model type produced by the {@link compositeRuns} factory. */
export interface CompositeRunsModel extends Model {
  readonly _kind: "compositeRuns";
}
/** Branded model type produced by the {@link dockerRuns} factory. */
export interface DockerRunsModel extends Model {
  readonly _kind: "dockerRuns";
}
/** Branded model type produced by the {@link nodeRuns} factory. */
export interface NodeRunsModel extends Model {
  readonly _kind: "nodeRuns";
}

/**
 * Create a model object.
 *
 * The returned object is intentionally NOT frozen — `_data` and `_meta`
 * must remain runtime-mutable so synthesis-time transforms (like
 * `PinTransform`) can rewrite fields after a `cloneModel` deep copy.
 * Public types keep `readonly` modifiers so external consumers don't
 * accidentally mutate models.
 */
export function createModel(
  kind: string,
  data: Record<string, unknown>,
  meta: ModelMeta,
  keyOrder: readonly string[],
): Model {
  return {
    [MODEL_BRAND]: true as const,
    _kind: kind,
    _data: data,
    _meta: meta,
    _keyOrder: keyOrder,
    _sourceLocation: captureSourceLocation(),
  };
}

/** Type guard for Model values. */
export function isModel(value: unknown): value is Model {
  return typeof value === "object" && value !== null && MODEL_BRAND in value;
}

/**
 * Map camelCase input fields to kebab-case YAML keys.
 * Skips undefined values.
 */
export function mapFields(
  data: Record<string, unknown>,
  fieldMap: Record<string, string>,
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [camelKey, yamlKey] of Object.entries(fieldMap)) {
    if (data[camelKey] !== undefined) {
      result[yamlKey] = data[camelKey];
    }
  }
  return result;
}

// ---- cloneModel ----

/**
 * Deep-clone a Model so synthesis-time transforms can mutate it without
 * touching the user's original.
 *
 * `structuredClone` is intentionally NOT used because:
 *   - it silently drops Symbol-keyed properties (would lose `MODEL_BRAND`
 *     and `RAW_BRAND`), and
 *   - it throws on functions (would crash on `_meta.postProcess`).
 *
 * Functions and the `_sourceLocation` reference are passed through by
 * reference; everything else (Models, Raw values, plain objects, arrays)
 * is cloned.
 */
export function cloneModel<M extends Model>(model: M): M {
  return cloneValueInternal(model) as M;
}

function cloneValueInternal(value: unknown): unknown {
  // Primitives (and null/undefined)
  if (value === null || value === undefined) return value;
  const t = typeof value;
  if (t !== "object" && t !== "function") return value;

  // Functions are passed by reference (no way to deep-clone a closure)
  if (t === "function") return value;

  // Raw<T> — preserve the symbol brand
  if (isRaw(value)) {
    return { [RAW_BRAND]: true as const, value: cloneValueInternal(value.value) };
  }

  // Commented<T> — preserve the symbol brand and recurse into the value
  if (isCommented(value)) {
    return { [COMMENTED_BRAND]: true as const, value: cloneValueInternal(value.value), comment: value.comment, eolComment: value.eolComment };
  }

  // Model — recurse into _data and _meta; preserve _sourceLocation by reference
  if (isModel(value)) {
    const m = value as Model;
    return {
      [MODEL_BRAND]: true as const,
      _kind: m._kind,
      _data: cloneRecord(m._data),
      _meta: cloneMeta(m._meta),
      _keyOrder: m._keyOrder,
      _sourceLocation: m._sourceLocation,
    };
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
  if (meta.comment !== undefined) out.comment = meta.comment;
  if (meta.eolComment !== undefined) out.eolComment = meta.eolComment;
  if (meta.extras !== undefined) {
    out.extras = cloneRecord(meta.extras);
  }
  // postProcess is a function — pass by reference.
  if (meta.postProcess !== undefined) out.postProcess = meta.postProcess;
  return out;
}
