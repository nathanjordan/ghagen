import type { YAMLMap } from "yaml";
import type { HttpsJsonSchemastoreOrgGithubActionJson as SchemaAction } from "../schema/action-types.generated.js";
import { buildModel, extractMeta } from "./_base.js";
import type {
  StepModel,
  WithMeta,
  Raw,
  ModelSpec,
  ActionModel,
  ActionInputModel,
  ActionOutputModel,
  BrandingModel,
  CompositeRunsModel,
  DockerRunsModel,
  NodeRunsModel,
} from "./_base.js";

// ---------------------------------------------------------------------------
// Input interfaces
// ---------------------------------------------------------------------------

/**
 * Input for defining an action input parameter.
 *
 * Maps to a single entry under the `inputs` key in an `action.yml` file.
 */
export interface ActionInputDefInput {
  /** Human-readable description of this input, shown in the Actions UI. */
  description: string;
  /** Whether this input must be supplied by the caller. Defaults to `false`. */
  required?: boolean;
  /** Default value used when the caller does not supply this input. */
  default?: string;
  /** Message displayed when this input is used, indicating it is deprecated. */
  deprecationMessage?: string;
}

/**
 * Input for defining an action output.
 *
 * Maps to a single entry under the `outputs` key in an `action.yml` file.
 */
export interface ActionOutputDefInput {
  /** Human-readable description of this output. */
  description: string;
  /** The value to set for this output. Required for composite actions. */
  value?: string;
}

/**
 * Input for action branding configuration.
 *
 * Controls the icon and color shown in the GitHub Marketplace listing.
 * See {@link https://docs.github.com/en/actions/sharing-automations/creating-actions/metadata-syntax-for-github-actions#branding}.
 */
export interface BrandingInput {
  /** Feather icon name displayed in the Marketplace, e.g. `"activity"`. */
  icon?: SchemaAction["branding"] extends infer B
    ? B extends { icon?: infer I }
      ? I | Raw<string>
      : string | Raw<string>
    : string | Raw<string>;
  /** Background color for the Marketplace badge (e.g. `"blue"`, `"green"`). */
  color?: SchemaAction["branding"] extends infer B
    ? B extends { color?: infer C }
      ? C | Raw<string>
      : string | Raw<string>
    : string | Raw<string>;
}

/**
 * Input for composite action runs.
 *
 * Defines a composite action whose logic is expressed as a sequence of steps,
 * the same step models used in workflow jobs.
 */
export interface CompositeRunsInput {
  /** Must be `"composite"` to indicate a composite action. */
  using: "composite";
  /** Ordered list of steps that make up the composite action. Items can be `StepModel` objects or raw `YAMLMap` nodes for passthrough. */
  steps: (StepModel | YAMLMap)[];
}

/**
 * Input for Docker action runs.
 *
 * Configures a Docker container action, specifying the image, entrypoint,
 * arguments, and optional pre/post lifecycle hooks.
 */
export interface DockerRunsInput {
  /** Must be `"docker"` to indicate a Docker action. */
  using: "docker";
  /** Docker image to use, e.g. `"Dockerfile"` or `"docker://alpine:3"`. */
  image: string;
  /** Environment variables to pass into the Docker container. */
  env?: Record<string, string | number | boolean>;
  /** Arguments to pass to the container entrypoint. */
  args?: string[];
  /** Overrides the `ENTRYPOINT` in the Dockerfile. */
  entrypoint?: string;
  /** Script to run before the main entrypoint. */
  preEntrypoint?: string;
  /** Condition for running the pre-entrypoint script. */
  preIf?: string;
  /** Script to run after the main entrypoint completes. */
  postEntrypoint?: string;
  /** Condition for running the post-entrypoint script. */
  postIf?: string;
}

/**
 * Input for Node.js action runs.
 *
 * Configures a JavaScript/TypeScript action executed under a specific
 * Node.js runtime version.
 */
export interface NodeRunsInput {
  /** Node.js runtime version, e.g. `"node20"`. Use {@link raw} for unlisted versions. */
  using: "node12" | "node16" | "node20" | "node24" | Raw<string>;
  /** Path to the main entry-point script (relative to the action root). */
  main: string;
  /** Path to a script that runs before the main entry-point. */
  pre?: string;
  /** Path to a script that runs after the main entry-point completes. */
  post?: string;
  /** Condition for running the `pre` script. */
  preIf?: string;
  /** Condition for running the `post` script. */
  postIf?: string;
}

/**
 * Input for the top-level action definition.
 *
 * Corresponds to the root-level keys of a GitHub Actions `action.yml` file.
 */
export interface ActionInput {
  /** Display name of the action, shown in the GitHub UI and Marketplace. */
  name: string;
  /** Short description of what the action does. */
  description: string;
  /** Author of the action (individual or organization). */
  author?: string;
  /** Marketplace branding settings (icon and color). */
  branding?: BrandingModel;
  /** Map of input parameter names to their definitions. */
  inputs?: Record<string, ActionInputModel>;
  /** Map of output names to their definitions. */
  outputs?: Record<string, ActionOutputModel>;
  /** Execution configuration: composite steps, Docker, or Node.js. */
  runs: CompositeRunsModel | DockerRunsModel | NodeRunsModel;
}

// ---------------------------------------------------------------------------
// Serialization specs
// ---------------------------------------------------------------------------

/** Serialization spec for {@link ActionInputModel}. */
export const ACTION_INPUT_SPEC: ModelSpec = {
  kind: "actionInput",
  fieldMap: {
    description: "description",
    required: "required",
    default: "default",
    deprecationMessage: "deprecationMessage",
  },
  order: ["description", "required", "default", "deprecationMessage"],
};

/** Serialization spec for {@link ActionOutputModel}. */
export const ACTION_OUTPUT_SPEC: ModelSpec = {
  kind: "actionOutput",
  fieldMap: { description: "description", value: "value" },
  order: ["description", "value"],
};

/** Serialization spec for {@link BrandingModel}. */
export const BRANDING_SPEC: ModelSpec = {
  kind: "branding",
  fieldMap: { icon: "icon", color: "color" },
  order: ["icon", "color"],
};

/** Serialization spec for {@link CompositeRunsModel}. */
export const COMPOSITE_RUNS_SPEC: ModelSpec = {
  kind: "compositeRuns",
  fieldMap: { using: "using", steps: "steps" },
  order: ["using", "steps"],
};

/** Serialization spec for {@link DockerRunsModel}. */
export const DOCKER_RUNS_SPEC: ModelSpec = {
  kind: "dockerRuns",
  fieldMap: {
    using: "using",
    image: "image",
    env: "env",
    args: "args",
    preEntrypoint: "pre-entrypoint",
    preIf: "pre-if",
    entrypoint: "entrypoint",
    postEntrypoint: "post-entrypoint",
    postIf: "post-if",
  },
  order: [
    "using",
    "image",
    "env",
    "args",
    "pre-entrypoint",
    "pre-if",
    "entrypoint",
    "post-entrypoint",
    "post-if",
  ],
};

/** Serialization spec for {@link NodeRunsModel}. */
export const NODE_RUNS_SPEC: ModelSpec = {
  kind: "nodeRuns",
  fieldMap: {
    using: "using",
    main: "main",
    pre: "pre",
    post: "post",
    preIf: "pre-if",
    postIf: "post-if",
  },
  order: ["using", "main", "pre", "post", "pre-if", "post-if"],
};

/** Serialization spec for {@link ActionModel}. */
export const ACTION_SPEC: ModelSpec = {
  kind: "action",
  fieldMap: {
    name: "name",
    description: "description",
    author: "author",
    branding: "branding",
    inputs: "inputs",
    outputs: "outputs",
    runs: "runs",
  } satisfies Record<string, keyof SchemaAction>,
  order: ["name", "description", "author", "branding", "inputs", "outputs", "runs"],
};

// ---------------------------------------------------------------------------
// Factory functions
// ---------------------------------------------------------------------------

/**
 * Create an action input definition model.
 *
 * Produces a model for a single entry in the action's `inputs` map.
 *
 * @param input - Input definition properties and optional metadata.
 * @returns A branded {@link ActionInputModel}.
 *
 * @example
 * ```ts
 * const nameInput = actionInputDef({
 *   description: "Name to greet",
 *   required: true,
 *   default: "World",
 * });
 * ```
 */
export function actionInputDef(input: WithMeta<ActionInputDefInput>): ActionInputModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return buildModel<ActionInputModel>(ACTION_INPUT_SPEC, data as Record<string, unknown>, meta);
}

/**
 * Create an action output definition model.
 *
 * Produces a model for a single entry in the action's `outputs` map.
 *
 * @param input - Output definition properties and optional metadata.
 * @returns A branded {@link ActionOutputModel}.
 *
 * @example
 * ```ts
 * const timeOutput = actionOutputDef({
 *   description: "The greeting timestamp",
 *   value: "${{ steps.greet.outputs.time }}",
 * });
 * ```
 */
export function actionOutputDef(input: WithMeta<ActionOutputDefInput>): ActionOutputModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return buildModel<ActionOutputModel>(ACTION_OUTPUT_SPEC, data as Record<string, unknown>, meta);
}

/**
 * Create a branding model for a GitHub Actions Marketplace listing.
 *
 * @param input - Icon and color settings, plus optional metadata.
 * @returns A branded {@link BrandingModel}.
 *
 * @example
 * ```ts
 * const badge = branding({ icon: "award", color: "green" });
 * ```
 */
export function branding(input: WithMeta<BrandingInput>): BrandingModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return buildModel<BrandingModel>(BRANDING_SPEC, data as Record<string, unknown>, meta);
}

/**
 * Create a composite runs model.
 *
 * Defines the `runs` section of a composite action, containing an ordered
 * list of {@link StepModel} entries.
 *
 * @param input - Composite runs configuration and optional metadata.
 * @returns A branded {@link CompositeRunsModel}.
 *
 * @example
 * ```ts
 * const runs = compositeRuns({
 *   using: "composite",
 *   steps: [step({ run: "echo Hello" })],
 * });
 * ```
 */
export function compositeRuns(input: WithMeta<CompositeRunsInput>): CompositeRunsModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return buildModel<CompositeRunsModel>(COMPOSITE_RUNS_SPEC, data as Record<string, unknown>, meta);
}

/**
 * Create a Docker runs model.
 *
 * Defines the `runs` section of a Docker container action, specifying the
 * image, entrypoint, arguments, and lifecycle hooks.
 *
 * @param input - Docker runs configuration and optional metadata.
 * @returns A branded {@link DockerRunsModel}.
 *
 * @example
 * ```ts
 * const runs = dockerRuns({
 *   using: "docker",
 *   image: "Dockerfile",
 *   args: ["--name", "${{ inputs.name }}"],
 * });
 * ```
 */
export function dockerRuns(input: WithMeta<DockerRunsInput>): DockerRunsModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return buildModel<DockerRunsModel>(DOCKER_RUNS_SPEC, data as Record<string, unknown>, meta);
}

/**
 * Create a Node.js runs model.
 *
 * Defines the `runs` section of a JavaScript/TypeScript action, specifying
 * the Node.js version, entry-point script, and optional pre/post hooks.
 *
 * @param input - Node.js runs configuration and optional metadata.
 * @returns A branded {@link NodeRunsModel}.
 *
 * @example
 * ```ts
 * const runs = nodeRuns({
 *   using: "node20",
 *   main: "dist/index.js",
 *   post: "dist/cleanup.js",
 * });
 * ```
 */
export function nodeRuns(input: WithMeta<NodeRunsInput>): NodeRunsModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return buildModel<NodeRunsModel>(NODE_RUNS_SPEC, data as Record<string, unknown>, meta);
}

/**
 * Create an action model representing a complete `action.yml` definition.
 *
 * This is the top-level factory for GitHub Actions action metadata. Pass the
 * returned model to {@link toYaml} or {@link toYamlFile} to emit the YAML.
 *
 * @param input - Action definition properties and optional metadata.
 * @returns A branded {@link ActionModel}.
 *
 * @example
 * ```ts
 * const myAction = action({
 *   name: "Hello World",
 *   description: "Greet someone",
 *   inputs: { name: actionInputDef({ description: "Who to greet", required: true }) },
 *   runs: nodeRuns({ using: "node20", main: "dist/index.js" }),
 * });
 * ```
 */
export function action(input: WithMeta<ActionInput>): ActionModel {
  const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
  return buildModel<ActionModel>(ACTION_SPEC, data as Record<string, unknown>, meta);
}
