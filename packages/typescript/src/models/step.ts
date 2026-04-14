import type { Step as SchemaStep } from "../generated/workflow-types.js";
import type { StepModel, WithMeta, Raw } from "./_base.js";
import { createModel, extractMeta, mapFields } from "./_base.js";
import { STEP_KEY_ORDER } from "../emitter/key-order.js";
import type { ShellType } from "./common.js";

export interface StepInput {
  id?: string;
  name?: string;
  if_?: string;
  uses?: string;
  run?: string;
  with_?: Record<string, string | number | boolean>;
  env?: Record<string, string>;
  shell?: ShellType | Raw<string>;
  workingDirectory?: string;
  continueOnError?: boolean | string;
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

export function step(input: WithMeta<StepInput>): StepModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, STEP_FIELD_MAP);
  return createModel("step", yamlData, meta, STEP_KEY_ORDER) as StepModel;
}
