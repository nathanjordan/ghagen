// Models
export { raw, isRaw, isModel } from "./models/_base.js";
export type {
  Raw,
  Model,
  ModelMeta,
  WithMeta,
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
export { dedentScript, getAutoDedent, setAutoDedent } from "./_dedent.js";

// Model utilities
export { cloneModel } from "./models/_base.js";

// App
export { App, WORKFLOWS_DIR, type AppOptions } from "./app.js";

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

// Lint subsystem
export {
  runLint,
  loadLintConfig,
  type LintConfig,
  type LoadLintConfigResult,
  formatHuman,
  formatJson,
  formatGithub,
  type Severity,
  type Violation,
  SEVERITY_VALUES,
  ALL_RULES,
  type Rule,
  type RuleMeta,
  type RuleContext,
  rule,
  makeRuleContext,
} from "./lint/index.js";
