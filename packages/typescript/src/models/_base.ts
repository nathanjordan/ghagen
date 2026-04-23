import { YAMLMap, YAMLSeq, Scalar, Pair } from "yaml";
import { captureSourceLocation, type SourceLocation } from "../_source_location.js";
import {
  STEP_KEY_ORDER,
  JOB_KEY_ORDER,
  WORKFLOW_KEY_ORDER,
  ON_KEY_ORDER,
  TRIGGER_KEY_ORDER,
  STRATEGY_KEY_ORDER,
  MATRIX_KEY_ORDER,
  CONCURRENCY_KEY_ORDER,
  DEFAULTS_KEY_ORDER,
  ENVIRONMENT_KEY_ORDER,
  CONTAINER_KEY_ORDER,
  PERMISSIONS_KEY_ORDER,
  WORKFLOW_DISPATCH_KEY_ORDER,
  WORKFLOW_CALL_KEY_ORDER,
  ACTION_KEY_ORDER,
  ACTION_INPUT_KEY_ORDER,
  ACTION_OUTPUT_KEY_ORDER,
  BRANDING_KEY_ORDER,
  COMPOSITE_RUNS_KEY_ORDER,
  DOCKER_RUNS_KEY_ORDER,
  NODE_RUNS_KEY_ORDER,
} from "../emitter/key-order.js";

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
  | "workflowCall"
  | "permissions"
  | "strategy"
  | "matrix"
  | "concurrency"
  | "defaults"
  | "environment"
  | "container"
  | "service"
  | "actionInput"
  | "actionOutput"
  | "branding"
  | "compositeRuns"
  | "dockerRuns"
  | "nodeRuns";

/**
 * Base class for all ghagen model objects.
 *
 * Models are intentionally NOT frozen — `data` and `meta` must remain
 * runtime-mutable so synthesis-time transforms (like `PinTransform`) can
 * rewrite fields after a `cloneModel` deep copy.
 */
export abstract class Model {
  abstract readonly kind: ModelKind;
  abstract readonly keyOrder: readonly string[];

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
    data: Record<string, unknown>,
    meta: ModelMeta,
    sourceLocation?: SourceLocation | null,
  ) {
    this.data = data;
    this.meta = meta;
    this.sourceLocation = sourceLocation !== undefined ? sourceLocation : captureSourceLocation();
  }

  /** Render this model to a YAMLMap with canonical key ordering,
   * comment attachment, extras merging, and postProcess support. */
  toYamlMap(): YAMLMap {
    const map = new YAMLMap();
    const fieldComments: Record<string, string> = {};
    const fieldEolComments: Record<string, string> = {};
    const orderedKeys = getOrderedKeys(Object.keys(this.data), this.keyOrder);

    for (const key of orderedKeys) {
      let value = this.data[key];
      if (isCommented(value)) {
        if (value.comment) {
          fieldComments[key] = value.comment;
        }
        if (value.eolComment) {
          fieldEolComments[key] = value.eolComment;
        }
        value = value.value;
      }
      const pair = new Pair(new Scalar(key), toYamlValue(value));
      map.items.push(pair);
    }

    if (this.meta.extras) {
      for (const [key, value] of Object.entries(this.meta.extras)) {
        let unwrapped = value;
        if (isCommented(value)) {
          if (value.comment) {
            fieldComments[key] = value.comment;
          }
          if (value.eolComment) {
            fieldEolComments[key] = value.eolComment;
          }
          unwrapped = value.value;
        }
        const pair = new Pair(new Scalar(key), toYamlValue(unwrapped));
        map.items.push(pair);
      }
    }

    attachFieldComments(map, fieldComments, fieldEolComments);

    if (this.meta.postProcess) {
      this.meta.postProcess(map);
    }

    return map;
  }

  /** Deep clone. Each subclass returns its own type. */
  abstract clone(): Model;

  /** Yield child Models found in data. Base provides generic scan;
   * subclasses can override for precision. */
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

// ---- Concrete model subclasses ----

/** Model produced by the {@link step} factory. */
export class StepModel extends Model {
  readonly kind = "step" as const;
  readonly keyOrder = STEP_KEY_ORDER;
  clone(): StepModel {
    return new StepModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link job} factory. */
export class JobModel extends Model {
  readonly kind = "job" as const;
  readonly keyOrder = JOB_KEY_ORDER;
  clone(): JobModel {
    return new JobModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link workflow} factory. */
export class WorkflowModel extends Model {
  readonly kind = "workflow" as const;
  readonly keyOrder = WORKFLOW_KEY_ORDER;
  clone(): WorkflowModel {
    return new WorkflowModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link action} factory. */
export class ActionModel extends Model {
  readonly kind = "action" as const;
  readonly keyOrder = ACTION_KEY_ORDER;
  clone(): ActionModel {
    return new ActionModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link on} factory. */
export class OnModel extends Model {
  readonly kind = "on" as const;
  readonly keyOrder = ON_KEY_ORDER;
  clone(): OnModel {
    return new OnModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link pushTrigger} factory. */
export class PushTriggerModel extends Model {
  readonly kind = "pushTrigger" as const;
  readonly keyOrder = TRIGGER_KEY_ORDER;
  clone(): PushTriggerModel {
    return new PushTriggerModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link prTrigger} factory. */
export class PRTriggerModel extends Model {
  readonly kind = "prTrigger" as const;
  readonly keyOrder = TRIGGER_KEY_ORDER;
  clone(): PRTriggerModel {
    return new PRTriggerModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link scheduleTrigger} factory. */
export class ScheduleTriggerModel extends Model {
  readonly kind = "scheduleTrigger" as const;
  readonly keyOrder = [] as const;
  clone(): ScheduleTriggerModel {
    return new ScheduleTriggerModel(
      cloneRecord(this.data),
      cloneMeta(this.meta),
      this.sourceLocation,
    );
  }
}

/** Model produced by the {@link workflowDispatch} factory. */
export class WorkflowDispatchModel extends Model {
  readonly kind = "workflowDispatch" as const;
  readonly keyOrder = WORKFLOW_DISPATCH_KEY_ORDER;
  clone(): WorkflowDispatchModel {
    return new WorkflowDispatchModel(
      cloneRecord(this.data),
      cloneMeta(this.meta),
      this.sourceLocation,
    );
  }
}

/** Model produced by the {@link workflowCall} factory. */
export class WorkflowCallModel extends Model {
  readonly kind = "workflowCall" as const;
  readonly keyOrder = WORKFLOW_CALL_KEY_ORDER;
  clone(): WorkflowCallModel {
    return new WorkflowCallModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link permissions} factory. */
export class PermissionsModel extends Model {
  readonly kind = "permissions" as const;
  readonly keyOrder = PERMISSIONS_KEY_ORDER;
  clone(): PermissionsModel {
    return new PermissionsModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link strategy} factory. */
export class StrategyModel extends Model {
  readonly kind = "strategy" as const;
  readonly keyOrder = STRATEGY_KEY_ORDER;
  clone(): StrategyModel {
    return new StrategyModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link matrix} factory. */
export class MatrixModel extends Model {
  readonly kind = "matrix" as const;
  readonly keyOrder = MATRIX_KEY_ORDER;
  clone(): MatrixModel {
    return new MatrixModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link concurrency} factory. */
export class ConcurrencyModel extends Model {
  readonly kind = "concurrency" as const;
  readonly keyOrder = CONCURRENCY_KEY_ORDER;
  clone(): ConcurrencyModel {
    return new ConcurrencyModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link defaults} factory. */
export class DefaultsModel extends Model {
  readonly kind = "defaults" as const;
  readonly keyOrder = DEFAULTS_KEY_ORDER;
  clone(): DefaultsModel {
    return new DefaultsModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link environment} factory. */
export class EnvironmentModel extends Model {
  readonly kind = "environment" as const;
  readonly keyOrder = ENVIRONMENT_KEY_ORDER;
  clone(): EnvironmentModel {
    return new EnvironmentModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link container} factory. */
export class ContainerModel extends Model {
  readonly kind = "container" as const;
  readonly keyOrder = CONTAINER_KEY_ORDER;
  clone(): ContainerModel {
    return new ContainerModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link service} factory. */
export class ServiceModel extends Model {
  readonly kind = "service" as const;
  readonly keyOrder = CONTAINER_KEY_ORDER;
  clone(): ServiceModel {
    return new ServiceModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link actionInputDef} factory. */
export class ActionInputModel extends Model {
  readonly kind = "actionInput" as const;
  readonly keyOrder = ACTION_INPUT_KEY_ORDER;
  clone(): ActionInputModel {
    return new ActionInputModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link actionOutputDef} factory. */
export class ActionOutputModel extends Model {
  readonly kind = "actionOutput" as const;
  readonly keyOrder = ACTION_OUTPUT_KEY_ORDER;
  clone(): ActionOutputModel {
    return new ActionOutputModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link branding} factory. */
export class BrandingModel extends Model {
  readonly kind = "branding" as const;
  readonly keyOrder = BRANDING_KEY_ORDER;
  clone(): BrandingModel {
    return new BrandingModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link compositeRuns} factory. */
export class CompositeRunsModel extends Model {
  readonly kind = "compositeRuns" as const;
  readonly keyOrder = COMPOSITE_RUNS_KEY_ORDER;
  clone(): CompositeRunsModel {
    return new CompositeRunsModel(
      cloneRecord(this.data),
      cloneMeta(this.meta),
      this.sourceLocation,
    );
  }
}

/** Model produced by the {@link dockerRuns} factory. */
export class DockerRunsModel extends Model {
  readonly kind = "dockerRuns" as const;
  readonly keyOrder = DOCKER_RUNS_KEY_ORDER;
  clone(): DockerRunsModel {
    return new DockerRunsModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
  }
}

/** Model produced by the {@link nodeRuns} factory. */
export class NodeRunsModel extends Model {
  readonly kind = "nodeRuns" as const;
  readonly keyOrder = NODE_RUNS_KEY_ORDER;
  clone(): NodeRunsModel {
    return new NodeRunsModel(cloneRecord(this.data), cloneMeta(this.meta), this.sourceLocation);
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

// ---- YAML serialization helpers (used by Model.toYamlMap) ----

/** Convert any value to a YAML node. */
function toYamlValue(value: unknown): unknown {
  if (value === null || value === undefined) {
    return null;
  }

  // Commented values — unwrap and recurse
  if (isCommented(value)) {
    return toYamlValue(value.value);
  }

  // Raw values — unwrap and emit as plain scalar
  if (isRaw(value)) {
    const scalar = new Scalar(value.value);
    scalar.type = Scalar.PLAIN;
    return scalar;
  }

  // Nested Model — recurse
  if (value instanceof Model) {
    const childMap = value.toYamlMap();

    // Attach block comment from the nested model's meta
    if (value.meta.comment && childMap.items.length > 0) {
      const firstPair = childMap.items[0] as Pair;
      const key = firstPair.key instanceof Scalar ? firstPair.key : new Scalar(firstPair.key);
      key.commentBefore = value.meta.comment;
      firstPair.key = key;
    }

    // Attach EOL comment to the first value in the map (the entry-point line)
    if (value.meta.eolComment && childMap.items.length > 0) {
      const firstPair = childMap.items[0] as Pair;
      const val = firstPair.value instanceof Scalar ? firstPair.value : new Scalar(firstPair.value);
      val.comment = value.meta.eolComment;
      firstPair.value = val;
    }

    return childMap;
  }

  // Arrays
  if (Array.isArray(value)) {
    const seq = new YAMLSeq();
    for (let i = 0; i < value.length; i++) {
      const item = value[i];
      const node = toYamlValue(item);

      // If the item is a Model with a comment, attach it to the seq entry
      if (item instanceof Model && item.meta.comment && node instanceof YAMLMap) {
        // Comment is already attached to the first key inside toYamlMap's caller above.
        // For sequence items, we need to set commentBefore on the map node itself.
        (node as YAMLMap).commentBefore = item.meta.comment;
        // Remove the duplicate from the first key if it was set
        const firstPair = (node as YAMLMap).items[0] as Pair | undefined;
        if (firstPair && firstPair.key instanceof Scalar) {
          firstPair.key.commentBefore = null;
        }
      }

      seq.add(node);
    }
    return seq;
  }

  // Plain objects (Record<string, unknown>)
  if (typeof value === "object" && value !== null) {
    const map = new YAMLMap();
    for (const [k, v] of Object.entries(value)) {
      if (v === undefined) {
        continue;
      }
      const pair = new Pair(new Scalar(k), toYamlValue(v));
      map.items.push(pair);
    }
    return map;
  }

  // Strings — use block literal for multiline
  if (typeof value === "string" && value.includes("\n")) {
    const scalar = new Scalar(value);
    scalar.type = Scalar.BLOCK_LITERAL;
    return scalar;
  }

  // Primitives (string, number, boolean)
  return value;
}

/**
 * Sort keys by canonical order: ordered keys first (in specified order),
 * then remaining keys in their original insertion order.
 */
function getOrderedKeys(keys: string[], keyOrder: readonly string[]): string[] {
  const orderSet = new Set(keyOrder);
  const ordered: string[] = [];
  const remaining: string[] = [];

  // Add keys that appear in the canonical order
  for (const key of keyOrder) {
    if (keys.includes(key)) {
      ordered.push(key);
    }
  }

  // Add remaining keys in insertion order
  for (const key of keys) {
    if (!orderSet.has(key)) {
      remaining.push(key);
    }
  }

  return [...ordered, ...remaining];
}

/**
 * Attach field-level comments (block and EOL) to map pairs.
 */
function attachFieldComments(
  map: YAMLMap,
  fieldComments: Record<string, string>,
  fieldEolComments: Record<string, string>,
): void {
  const hasComments = Object.keys(fieldComments).length > 0;
  const hasEolComments = Object.keys(fieldEolComments).length > 0;
  if (!hasComments && !hasEolComments) {
    return;
  }

  for (const pair of map.items as Pair[]) {
    const keyName = pair.key instanceof Scalar ? String(pair.key.value) : String(pair.key);

    // Block comment before this field
    if (hasComments && keyName in fieldComments) {
      const key = pair.key instanceof Scalar ? pair.key : new Scalar(pair.key);
      key.commentBefore = fieldComments[keyName];
      pair.key = key;
    }

    // End-of-line comment on this field's value
    if (hasEolComments && keyName in fieldEolComments) {
      if (pair.value instanceof YAMLMap || pair.value instanceof YAMLSeq) {
        // For complex values, set comment on the key so it appears on the key line
        const key = pair.key instanceof Scalar ? pair.key : new Scalar(pair.key);
        key.comment = fieldEolComments[keyName];
        pair.key = key;
      } else if (pair.value instanceof Scalar) {
        pair.value.comment = fieldEolComments[keyName];
      } else {
        const val = new Scalar(pair.value);
        val.comment = fieldEolComments[keyName];
        pair.value = val;
      }
    }
  }
}
