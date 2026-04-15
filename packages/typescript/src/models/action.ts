import type { HttpsJsonSchemastoreOrgGithubActionJson as SchemaAction } from "../generated/action-types.js";
import type {
  ActionModel,
  ActionInputModel,
  ActionOutputModel,
  BrandingModel,
  CompositeRunsModel,
  DockerRunsModel,
  NodeRunsModel,
  StepModel,
  WithMeta,
  Raw,
} from "./_base.js";
import { createModel, extractMeta, mapFields } from "./_base.js";
import {
  ACTION_KEY_ORDER,
  ACTION_INPUT_KEY_ORDER,
  ACTION_OUTPUT_KEY_ORDER,
  BRANDING_KEY_ORDER,
  COMPOSITE_RUNS_KEY_ORDER,
  DOCKER_RUNS_KEY_ORDER,
  NODE_RUNS_KEY_ORDER,
} from "../emitter/key-order.js";

// ---------------------------------------------------------------------------
// Input interfaces
// ---------------------------------------------------------------------------

/** Input for defining an action input parameter. */
export interface ActionInputDefInput {
  description: string;
  required?: boolean;
  default?: string;
  deprecationMessage?: string;
}

/** Input for defining an action output. */
export interface ActionOutputDefInput {
  description: string;
  value?: string;
}

/** Input for action branding configuration. */
export interface BrandingInput {
  icon?: SchemaAction["branding"] extends infer B
    ? B extends { icon?: infer I }
      ? I | Raw<string>
      : string | Raw<string>
    : string | Raw<string>;
  color?: SchemaAction["branding"] extends infer B
    ? B extends { color?: infer C }
      ? C | Raw<string>
      : string | Raw<string>
    : string | Raw<string>;
}

/** Input for composite action runs. */
export interface CompositeRunsInput {
  using: "composite";
  steps: StepModel[];
}

/** Input for Docker action runs. */
export interface DockerRunsInput {
  using: "docker";
  image: string;
  env?: Record<string, string | number | boolean>;
  args?: string[];
  entrypoint?: string;
  preEntrypoint?: string;
  preIf?: string;
  postEntrypoint?: string;
  postIf?: string;
}

/** Input for Node.js action runs. */
export interface NodeRunsInput {
  using: "node12" | "node16" | "node20" | "node24" | Raw<string>;
  main: string;
  pre?: string;
  post?: string;
  preIf?: string;
  postIf?: string;
}

/** Input for the top-level action definition. */
export interface ActionInput {
  name: string;
  description: string;
  author?: string;
  branding?: BrandingModel;
  inputs?: Record<string, ActionInputModel>;
  outputs?: Record<string, ActionOutputModel>;
  runs: CompositeRunsModel | DockerRunsModel | NodeRunsModel;
}

// ---------------------------------------------------------------------------
// Field maps (camelCase -> YAML key)
// ---------------------------------------------------------------------------

const ACTION_INPUT_DEF_FIELD_MAP = {
  description: "description",
  required: "required",
  default: "default",
  deprecationMessage: "deprecationMessage",
} as const satisfies Record<string, (typeof ACTION_INPUT_KEY_ORDER)[number]>;

const ACTION_OUTPUT_DEF_FIELD_MAP = {
  description: "description",
  value: "value",
} as const satisfies Record<string, (typeof ACTION_OUTPUT_KEY_ORDER)[number]>;

const BRANDING_FIELD_MAP = {
  icon: "icon",
  color: "color",
} as const satisfies Record<string, (typeof BRANDING_KEY_ORDER)[number]>;

const COMPOSITE_RUNS_FIELD_MAP = {
  using: "using",
  steps: "steps",
} as const satisfies Record<string, (typeof COMPOSITE_RUNS_KEY_ORDER)[number]>;

const DOCKER_RUNS_FIELD_MAP = {
  using: "using",
  image: "image",
  env: "env",
  args: "args",
  preEntrypoint: "pre-entrypoint",
  preIf: "pre-if",
  entrypoint: "entrypoint",
  postEntrypoint: "post-entrypoint",
  postIf: "post-if",
} as const satisfies Record<string, (typeof DOCKER_RUNS_KEY_ORDER)[number]>;

const NODE_RUNS_FIELD_MAP = {
  using: "using",
  main: "main",
  pre: "pre",
  post: "post",
  preIf: "pre-if",
  postIf: "post-if",
} as const satisfies Record<string, (typeof NODE_RUNS_KEY_ORDER)[number]>;

const ACTION_FIELD_MAP = {
  name: "name",
  description: "description",
  author: "author",
  branding: "branding",
  inputs: "inputs",
  outputs: "outputs",
  runs: "runs",
} as const satisfies Record<string, (typeof ACTION_KEY_ORDER)[number]>;

// ---------------------------------------------------------------------------
// Factory functions
// ---------------------------------------------------------------------------

/** Create an action input definition model. */
export function actionInputDef(input: WithMeta<ActionInputDefInput>): ActionInputModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return createModel(
    "actionInput",
    mapFields(data as Record<string, unknown>, ACTION_INPUT_DEF_FIELD_MAP),
    meta,
    ACTION_INPUT_KEY_ORDER,
  ) as ActionInputModel;
}

/** Create an action output definition model. */
export function actionOutputDef(input: WithMeta<ActionOutputDefInput>): ActionOutputModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return createModel(
    "actionOutput",
    mapFields(data as Record<string, unknown>, ACTION_OUTPUT_DEF_FIELD_MAP),
    meta,
    ACTION_OUTPUT_KEY_ORDER,
  ) as ActionOutputModel;
}

/** Create a branding model. */
export function branding(input: WithMeta<BrandingInput>): BrandingModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return createModel(
    "branding",
    mapFields(data as Record<string, unknown>, BRANDING_FIELD_MAP),
    meta,
    BRANDING_KEY_ORDER,
  ) as BrandingModel;
}

/** Create a composite runs model. */
export function compositeRuns(input: WithMeta<CompositeRunsInput>): CompositeRunsModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return createModel(
    "compositeRuns",
    mapFields(data as Record<string, unknown>, COMPOSITE_RUNS_FIELD_MAP),
    meta,
    COMPOSITE_RUNS_KEY_ORDER,
  ) as CompositeRunsModel;
}

/** Create a Docker runs model. */
export function dockerRuns(input: WithMeta<DockerRunsInput>): DockerRunsModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return createModel(
    "dockerRuns",
    mapFields(data as Record<string, unknown>, DOCKER_RUNS_FIELD_MAP),
    meta,
    DOCKER_RUNS_KEY_ORDER,
  ) as DockerRunsModel;
}

/** Create a Node.js runs model. */
export function nodeRuns(input: WithMeta<NodeRunsInput>): NodeRunsModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return createModel(
    "nodeRuns",
    mapFields(data as Record<string, unknown>, NODE_RUNS_FIELD_MAP),
    meta,
    NODE_RUNS_KEY_ORDER,
  ) as NodeRunsModel;
}

/** Create an action model. */
export function action(input: WithMeta<ActionInput>): ActionModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return createModel(
    "action",
    mapFields(data as Record<string, unknown>, ACTION_FIELD_MAP),
    meta,
    ACTION_KEY_ORDER,
  ) as ActionModel;
}
