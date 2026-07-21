import { describe, it, expect } from "vitest";
import type { ModelKind, ModelSpec } from "./_base.js";
import { STEP_SPEC } from "./step.js";
import { PERMISSIONS_SPEC } from "./permissions.js";
import { CONTAINER_SPEC, SERVICE_SPEC } from "./container.js";
import {
  MATRIX_SPEC,
  STRATEGY_SPEC,
  CONCURRENCY_SPEC,
  DEFAULTS_SPEC,
  ENVIRONMENT_SPEC,
  JOB_SPEC,
} from "./job.js";
import { WORKFLOW_SPEC } from "./workflow.js";
import {
  PUSH_TRIGGER_SPEC,
  PR_TRIGGER_SPEC,
  SCHEDULE_TRIGGER_SPEC,
  WORKFLOW_DISPATCH_INPUT_SPEC,
  WORKFLOW_DISPATCH_SPEC,
  WORKFLOW_CALL_SPEC,
  ON_SPEC,
} from "./trigger.js";
import {
  ACTION_INPUT_SPEC,
  ACTION_OUTPUT_SPEC,
  BRANDING_SPEC,
  COMPOSITE_RUNS_SPEC,
  DOCKER_RUNS_SPEC,
  NODE_RUNS_SPEC,
  ACTION_SPEC,
} from "./action.js";

/** Every ModelSpec in the library. */
const ALL_SPECS: ModelSpec[] = [
  STEP_SPEC,
  PERMISSIONS_SPEC,
  CONTAINER_SPEC,
  SERVICE_SPEC,
  MATRIX_SPEC,
  STRATEGY_SPEC,
  CONCURRENCY_SPEC,
  DEFAULTS_SPEC,
  ENVIRONMENT_SPEC,
  JOB_SPEC,
  WORKFLOW_SPEC,
  PUSH_TRIGGER_SPEC,
  PR_TRIGGER_SPEC,
  SCHEDULE_TRIGGER_SPEC,
  WORKFLOW_DISPATCH_INPUT_SPEC,
  WORKFLOW_DISPATCH_SPEC,
  WORKFLOW_CALL_SPEC,
  ON_SPEC,
  ACTION_INPUT_SPEC,
  ACTION_OUTPUT_SPEC,
  BRANDING_SPEC,
  COMPOSITE_RUNS_SPEC,
  DOCKER_RUNS_SPEC,
  NODE_RUNS_SPEC,
  ACTION_SPEC,
];

/** Every ModelKind the discriminant union declares. */
const ALL_KINDS: ModelKind[] = [
  "step",
  "job",
  "workflow",
  "action",
  "on",
  "pushTrigger",
  "prTrigger",
  "scheduleTrigger",
  "workflowDispatch",
  "workflowDispatchInput",
  "workflowCall",
  "permissions",
  "strategy",
  "matrix",
  "concurrency",
  "defaults",
  "environment",
  "container",
  "service",
  "actionInput",
  "actionOutput",
  "branding",
  "compositeRuns",
  "dockerRuns",
  "nodeRuns",
];

describe("ModelSpec self-consistency", () => {
  it("every ModelKind has exactly one spec", () => {
    const kinds = ALL_SPECS.map((s) => s.kind).sort();
    expect(kinds).toEqual([...ALL_KINDS].sort());
    expect(new Set(kinds).size).toBe(ALL_SPECS.length);
  });

  it.each(ALL_SPECS)("$kind: order has no duplicates", (spec) => {
    expect(new Set(spec.order).size).toBe(spec.order.length);
  });

  it.each(ALL_SPECS)("$kind: order is complete (== fieldMap values) or empty", (spec) => {
    if (spec.order.length === 0) {
      return; // alphabetical-emission opt-in (the `on:` section)
    }
    const emitted = new Set(Object.values(spec.fieldMap));
    expect(new Set(spec.order)).toEqual(emitted);
  });

  it.each(ALL_SPECS)("$kind: every wrap key is a field in the map", (spec) => {
    for (const camelKey of Object.keys(spec.wrap ?? {})) {
      expect(spec.fieldMap).toHaveProperty(camelKey);
    }
  });

  it("only the `on` spec uses empty order (alphabetical emission)", () => {
    const empty = ALL_SPECS.filter((s) => s.order.length === 0).map((s) => s.kind);
    expect(empty).toEqual(["on"]);
  });
});
