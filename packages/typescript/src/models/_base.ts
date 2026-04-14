import type { YAMLMap } from "yaml";

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
  return (
    typeof value === "object" && value !== null && RAW_BRAND in value
  );
}

// ---- Comment / metadata ----

/** Metadata attachable to any model for comments and escape hatches. */
export interface ModelMeta {
  /** Block comment emitted above this node in YAML. */
  comment?: string;
  /** End-of-line comment. */
  eolComment?: string;
  /** Per-field block comments, keyed by YAML key name. */
  fieldComments?: Record<string, string>;
  /** Per-field end-of-line comments, keyed by YAML key name. */
  fieldEolComments?: Record<string, string>;
  /** Arbitrary key/values merged into YAML output. */
  extras?: Record<string, unknown>;
  /** Callback to modify the YAMLMap node before emission. */
  postProcess?: (node: YAMLMap) => void;
}

/** Intersect schema fields with optional metadata. */
export type WithMeta<T> = T & ModelMeta;

const META_KEYS = new Set<string>([
  "comment",
  "eolComment",
  "fieldComments",
  "fieldEolComments",
  "extras",
  "postProcess",
]);

/** Split a WithMeta<T> input into [dataFields, meta]. */
export function extractMeta<T extends object>(
  input: T,
): [Omit<T, keyof ModelMeta>, ModelMeta] {
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
}

// Branded subtypes for type safety in function signatures
export interface StepModel extends Model {
  readonly _kind: "step";
}
export interface JobModel extends Model {
  readonly _kind: "job";
}
export interface WorkflowModel extends Model {
  readonly _kind: "workflow";
}
export interface ActionModel extends Model {
  readonly _kind: "action";
}
export interface OnModel extends Model {
  readonly _kind: "on";
}
export interface PushTriggerModel extends Model {
  readonly _kind: "pushTrigger";
}
export interface PRTriggerModel extends Model {
  readonly _kind: "prTrigger";
}
export interface ScheduleTriggerModel extends Model {
  readonly _kind: "scheduleTrigger";
}
export interface WorkflowDispatchModel extends Model {
  readonly _kind: "workflowDispatch";
}
export interface WorkflowCallModel extends Model {
  readonly _kind: "workflowCall";
}
export interface PermissionsModel extends Model {
  readonly _kind: "permissions";
}
export interface StrategyModel extends Model {
  readonly _kind: "strategy";
}
export interface MatrixModel extends Model {
  readonly _kind: "matrix";
}
export interface ConcurrencyModel extends Model {
  readonly _kind: "concurrency";
}
export interface DefaultsModel extends Model {
  readonly _kind: "defaults";
}
export interface EnvironmentModel extends Model {
  readonly _kind: "environment";
}
export interface ContainerModel extends Model {
  readonly _kind: "container";
}
export interface ServiceModel extends Model {
  readonly _kind: "service";
}
export interface ActionInputModel extends Model {
  readonly _kind: "actionInput";
}
export interface ActionOutputModel extends Model {
  readonly _kind: "actionOutput";
}
export interface BrandingModel extends Model {
  readonly _kind: "branding";
}
export interface CompositeRunsModel extends Model {
  readonly _kind: "compositeRuns";
}
export interface DockerRunsModel extends Model {
  readonly _kind: "dockerRuns";
}
export interface NodeRunsModel extends Model {
  readonly _kind: "nodeRuns";
}

/** Create a frozen model object. */
export function createModel(
  kind: string,
  data: Record<string, unknown>,
  meta: ModelMeta,
  keyOrder: readonly string[],
): Model {
  return Object.freeze({
    [MODEL_BRAND]: true as const,
    _kind: kind,
    _data: data,
    _meta: meta,
    _keyOrder: keyOrder,
  });
}

/** Type guard for Model values. */
export function isModel(value: unknown): value is Model {
  return (
    typeof value === "object" && value !== null && MODEL_BRAND in value
  );
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
