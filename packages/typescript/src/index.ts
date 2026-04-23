/**
 * ghagen - Generate GitHub Actions workflow YAML from TypeScript/JavaScript.
 *
 * Core concepts:
 *
 * - **Factory functions** ({@link workflow}, {@link job}, {@link step}, etc.)
 *   create immutable model objects
 * - **Models** are serialized to YAML via {@link toYaml} / {@link toYamlFile}
 * - **{@link App}** coordinates multi-file synthesis with transforms and
 *   lockfile pinning
 * - **Helpers** ({@link expr}, {@link secrets}, {@link github}, {@link vars})
 *   build GitHub Actions expressions
 * - **{@link raw | Raw\<T\>}** bypasses type constraints for escape-hatch scenarios
 *
 * @packageDocumentation
 */

// Models
export {
  raw,
  isRaw,
  isModel,
  withComment,
  withEolComment,
  isCommented,
  unwrapCommented,
  Model,
  StepModel,
  JobModel,
  WorkflowModel,
  ActionModel,
  OnModel,
  PushTriggerModel,
  PRTriggerModel,
  ScheduleTriggerModel,
  WorkflowDispatchModel,
  WorkflowCallModel,
  PermissionsModel,
  StrategyModel,
  MatrixModel,
  ConcurrencyModel,
  DefaultsModel,
  EnvironmentModel,
  ContainerModel,
  ServiceModel,
  ActionInputModel,
  ActionOutputModel,
  BrandingModel,
  CompositeRunsModel,
  DockerRunsModel,
  NodeRunsModel,
} from "./models/_base.js";
export type {
  Commented,
  Commentable,
  Raw,
  ModelKind,
  ModelMeta,
  WithMeta,
} from "./models/_base.js";

export { step } from "./models/step.js";
export type { StepInput } from "./models/step.js";

export {
  on,
  pushTrigger,
  prTrigger,
  scheduleTrigger,
  workflowDispatch,
  workflowCall,
} from "./models/trigger.js";
export type {
  OnInput,
  PushTriggerInput,
  PRTriggerInput,
  ScheduleTriggerInput,
  WorkflowDispatchInput,
  WorkflowDispatchInputDef,
  WorkflowCallInput,
  WorkflowCallInputDef,
  WorkflowCallOutputDef,
  WorkflowCallSecretDef,
} from "./models/trigger.js";

export { permissions } from "./models/permissions.js";
export type { PermissionsInput } from "./models/permissions.js";

export { container, service } from "./models/container.js";
export type { ContainerInput } from "./models/container.js";

export { job, strategy, matrix, concurrency, defaults, environment } from "./models/job.js";
export type {
  JobInput,
  JobOutputInput,
  StrategyInput,
  MatrixInput,
  ConcurrencyInput,
  DefaultsInput,
  DefaultsRunInput,
  EnvironmentInput,
} from "./models/job.js";

export { workflow } from "./models/workflow.js";
export type { WorkflowInput } from "./models/workflow.js";

export {
  action,
  actionInputDef,
  actionOutputDef,
  branding,
  compositeRuns,
  dockerRuns,
  nodeRuns,
} from "./models/action.js";
export type {
  ActionInput,
  ActionInputDefInput,
  ActionOutputDefInput,
  BrandingInput,
  CompositeRunsInput,
  DockerRunsInput,
  NodeRunsInput,
} from "./models/action.js";

export type { ShellType, PermissionLevel } from "./models/common.js";

// Emitter
export { toYaml, toYamlFile } from "./emitter/yaml-writer.js";
export type { ToYamlOptions } from "./emitter/yaml-writer.js";

// Helpers
export { expr, secrets, github, vars } from "./helpers/expressions.js";

// Source location
export type { SourceLocation } from "./_source_location.js";

// Utilities
export { findAppRoot } from "./paths.js";
export { loadOptions, type GhagenOptions } from "./config.js";
export { default as dedent } from "dedent";
export { getAutoDedent, setAutoDedent } from "./config.js";

// Model utilities
export { cloneModel } from "./models/_base.js";

// App
export { App, DEFAULT_WORKFLOWS_DIR as WORKFLOWS_DIR } from "./app.js";

// Transforms
export type { Transform, SynthContext, SynthItem } from "./transforms.js";

// Pin subsystem
export {
  DEFAULT_LOCKFILE_PATH,
  Lockfile,
  type PinEntry,
  readLockfile,
  writeLockfile,
  ResolveError,
  type ParsedUses,
  type ResolveOptions,
  parseUses,
  resolveRef,
  listTags,
  type BumpSeverity,
  type ParsedTag,
  parseTag,
  classifyBump,
  findLatestTag,
  collectUsesRefs,
  PinError,
  type PinTransform,
  pinTransform,
} from "./pin/index.js";
