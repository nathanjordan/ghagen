/**
 * The single `ModelKind` → {@link ModelSpec} map for the whole library.
 *
 * Every "all the model kinds" list that is not derived from the `ModelKind`
 * union eventually loses an entry — `spec.test.ts` maintained two such lists by
 * hand and both silently omitted `imageSnapshot`, so its headline "every
 * ModelKind has exactly one spec" assertion compared one hand list against
 * another and never consulted the type.
 *
 * `satisfies Record<ModelKind, ModelSpec>` moves that from a test to the
 * compiler: adding a member to `ModelKind` without an entry here is `TS2739`
 * (or `TS1360`, depending on the shape of the omission) naming the missing
 * key, and an entry for a kind the union does not declare is `TS2353`. What
 * the type *cannot* express is that each entry's `spec.kind` equals its key —
 * `spec.test.ts` carries the three-line runtime assertion for that.
 *
 * This is a `src/` module rather than a test helper for two reasons. The
 * durable one is that it has two consumers (`spec.test.ts` and
 * `conformance.test.ts`), so living in either means one test file importing the
 * other's internals. The incidental one is that
 * `packages/typescript/tsconfig.json` excludes `src/**\/*.test.ts`, so a
 * `satisfies` clause written in a test file is checked by an editor and by
 * nothing in CI.
 *
 * `registry.ts` is a leaf: it imports the model modules and nothing under
 * `models/` imports it.
 */

import type { ModelKind, ModelSpec } from "./_base.js";
import {
  ACTION_INPUT_SPEC,
  ACTION_OUTPUT_SPEC,
  ACTION_SPEC,
  BRANDING_SPEC,
  COMPOSITE_RUNS_SPEC,
  DOCKER_RUNS_SPEC,
  NODE_RUNS_SPEC,
} from "./action.js";
import { CONTAINER_SPEC, SERVICE_SPEC } from "./container.js";
import { IMAGE_SNAPSHOT_SPEC } from "./image-snapshot.js";
import {
  CONCURRENCY_SPEC,
  DEFAULTS_RUN_SPEC,
  DEFAULTS_SPEC,
  ENVIRONMENT_SPEC,
  JOB_SPEC,
  MATRIX_SPEC,
  STRATEGY_SPEC,
} from "./job.js";
import { PERMISSIONS_SPEC } from "./permissions.js";
import { STEP_SPEC } from "./step.js";
import {
  ON_SPEC,
  PR_TRIGGER_SPEC,
  PUSH_TRIGGER_SPEC,
  SCHEDULE_TRIGGER_SPEC,
  WORKFLOW_CALL_INPUT_SPEC,
  WORKFLOW_CALL_OUTPUT_SPEC,
  WORKFLOW_CALL_SECRET_SPEC,
  WORKFLOW_CALL_SPEC,
  WORKFLOW_DISPATCH_INPUT_SPEC,
  WORKFLOW_DISPATCH_SPEC,
} from "./trigger.js";
import { WORKFLOW_SPEC } from "./workflow.js";

/**
 * Every {@link ModelSpec} in the library, keyed by its `kind` discriminant.
 *
 * Exhaustive by construction — the `satisfies` clause is the assertion.
 */
export const SPECS_BY_KIND = {
  step: STEP_SPEC,
  job: JOB_SPEC,
  workflow: WORKFLOW_SPEC,
  action: ACTION_SPEC,
  on: ON_SPEC,
  pushTrigger: PUSH_TRIGGER_SPEC,
  prTrigger: PR_TRIGGER_SPEC,
  scheduleTrigger: SCHEDULE_TRIGGER_SPEC,
  workflowDispatch: WORKFLOW_DISPATCH_SPEC,
  workflowDispatchInput: WORKFLOW_DISPATCH_INPUT_SPEC,
  workflowCall: WORKFLOW_CALL_SPEC,
  workflowCallInput: WORKFLOW_CALL_INPUT_SPEC,
  workflowCallOutput: WORKFLOW_CALL_OUTPUT_SPEC,
  workflowCallSecret: WORKFLOW_CALL_SECRET_SPEC,
  permissions: PERMISSIONS_SPEC,
  strategy: STRATEGY_SPEC,
  matrix: MATRIX_SPEC,
  concurrency: CONCURRENCY_SPEC,
  defaults: DEFAULTS_SPEC,
  defaultsRun: DEFAULTS_RUN_SPEC,
  environment: ENVIRONMENT_SPEC,
  container: CONTAINER_SPEC,
  service: SERVICE_SPEC,
  imageSnapshot: IMAGE_SNAPSHOT_SPEC,
  actionInput: ACTION_INPUT_SPEC,
  actionOutput: ACTION_OUTPUT_SPEC,
  branding: BRANDING_SPEC,
  compositeRuns: COMPOSITE_RUNS_SPEC,
  dockerRuns: DOCKER_RUNS_SPEC,
  nodeRuns: NODE_RUNS_SPEC,
} satisfies Record<ModelKind, ModelSpec>;

/** Every {@link ModelSpec} in the library — `Object.values` of the registry. */
export const ALL_SPECS: readonly ModelSpec[] = Object.values(SPECS_BY_KIND);
