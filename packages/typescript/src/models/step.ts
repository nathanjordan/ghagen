import type { Step as SchemaStep } from "../generated/workflow-types.js";
import type { StepModel, WithMeta, Raw } from "./_base.js";
import { createModel, extractMeta, mapFields } from "./_base.js";
import { STEP_KEY_ORDER } from "../emitter/key-order.js";
import type { ShellType } from "./common.js";
import { dedent, getAutoDedent } from "../_dedent.js";

/**
 * Input for defining a single step within a GitHub Actions job.
 * A step either runs a shell command ({@link StepInput.run | run}) or uses
 * an action ({@link StepInput.uses | uses}).
 */
export interface StepInput {
  /** Unique identifier for the step. Used to reference step outputs in expressions (e.g., `steps.<id>.outputs`). */
  id?: string;
  /** Display name for the step. */
  name?: string;
  /** Conditional expression that must evaluate to true for this step to run. Serialized as `if`. The trailing `_` avoids the reserved word; it is stripped during emission. */
  if_?: string;
  /** Action to use (e.g., `"actions/checkout@v4"`). Mutually exclusive with `run`. */
  uses?: string;
  /** Shell command(s) to run. Multi-line strings are automatically dedented. Mutually exclusive with `uses`. */
  run?: string;
  /** Input parameters for the action specified by `uses`. Serialized as `with`. The trailing `_` avoids the reserved word; it is stripped during emission. */
  with_?: Record<string, string | number | boolean>;
  /** Environment variables for this step. */
  env?: Record<string, string>;
  /** Shell to use for `run` commands. Use `Raw<string>` via `raw()` for shell types not covered by `ShellType`. */
  shell?: ShellType | Raw<string>;
  /** Working directory for `run` commands. Serialized as `working-directory`. */
  workingDirectory?: string;
  /** Allow the job to continue when this step fails. Serialized as `continue-on-error`. */
  continueOnError?: boolean | string;
  /** Maximum minutes the step can run before being cancelled. Serialized as `timeout-minutes`. */
  timeoutMinutes?: number;
}

const STEP_FIELD_MAP = {
  id: "id",
  name: "name",
  if_: "if",
  uses: "uses",
  run: "run",
  with_: "with",
  env: "env",
  shell: "shell",
  workingDirectory: "working-directory",
  continueOnError: "continue-on-error",
  timeoutMinutes: "timeout-minutes",
} as const satisfies Record<keyof StepInput, keyof SchemaStep>;

/**
 * Create a step model for use inside a job's `steps` array.
 *
 * @param input - Step properties and optional model metadata.
 * @returns A `StepModel` that serializes to a single step entry in YAML.
 *
 * @example Action step
 * ```ts
 * step({ uses: "actions/checkout@v4" })
 * ```
 *
 * @example Run step
 * ```ts
 * step({
 *   name: "Run tests",
 *   run: "npm test",
 *   env: { CI: "true" },
 * })
 * ```
 */
export function step(input: WithMeta<StepInput>): StepModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, STEP_FIELD_MAP);
  // Auto-dedent the run script when the module-level flag is on.
  if (getAutoDedent() && typeof yamlData["run"] === "string") {
    yamlData["run"] = dedent(yamlData["run"] as string);
  }
  return createModel("step", yamlData, meta, STEP_KEY_ORDER) as StepModel;
}
