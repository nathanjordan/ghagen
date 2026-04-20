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

export { step } from "./models/step.js";

export {
  on,
  pushTrigger,
  prTrigger,
  scheduleTrigger,
  workflowDispatch,
  workflowCall,
} from "./models/trigger.js";

export { permissions } from "./models/permissions.js";

export { container, service } from "./models/container.js";

export { job, strategy, matrix, concurrency, defaults, environment } from "./models/job.js";

export { workflow } from "./models/workflow.js";

export {
  action,
  actionInputDef,
  actionOutputDef,
  branding,
  compositeRuns,
  dockerRuns,
  nodeRuns,
} from "./models/action.js";

// Emitter
export { toYaml, toYamlFile } from "./emitter/yaml-writer.js";

// Helpers
export { expr, secrets, github, vars } from "./helpers/expressions.js";

// App
export { App } from "./app.js";
