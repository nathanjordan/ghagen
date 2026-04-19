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

// Models — factory functions
export { raw } from "./models/_base.js";
export type { Raw, StepModel, JobModel, WorkflowModel, ActionModel } from "./models/_base.js";

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

// Helpers
export { expr, secrets, github, vars } from "./helpers/expressions.js";

// App
export { App } from "./app.js";
