import { describe, it, expect } from "vitest";
import {
  WORKFLOW_KEY_ORDER,
  JOB_KEY_ORDER,
  STEP_KEY_ORDER,
  TRIGGER_KEY_ORDER,
  ACTION_KEY_ORDER,
  ON_KEY_ORDER,
  STRATEGY_KEY_ORDER,
  MATRIX_KEY_ORDER,
  CONTAINER_KEY_ORDER,
  CONCURRENCY_KEY_ORDER,
  DEFAULTS_KEY_ORDER,
  PERMISSIONS_KEY_ORDER,
  WORKFLOW_DISPATCH_KEY_ORDER,
  WORKFLOW_DISPATCH_INPUT_KEY_ORDER,
  WORKFLOW_CALL_KEY_ORDER,
  ENVIRONMENT_KEY_ORDER,
  ACTION_INPUT_KEY_ORDER,
  ACTION_OUTPUT_KEY_ORDER,
  BRANDING_KEY_ORDER,
  COMPOSITE_RUNS_KEY_ORDER,
  DOCKER_RUNS_KEY_ORDER,
  NODE_RUNS_KEY_ORDER,
} from "./key-order.js";

const ALL_KEY_ORDERS = {
  ON_KEY_ORDER,
  WORKFLOW_KEY_ORDER,
  JOB_KEY_ORDER,
  STEP_KEY_ORDER,
  TRIGGER_KEY_ORDER,
  ACTION_KEY_ORDER,
  STRATEGY_KEY_ORDER,
  MATRIX_KEY_ORDER,
  CONTAINER_KEY_ORDER,
  CONCURRENCY_KEY_ORDER,
  DEFAULTS_KEY_ORDER,
  PERMISSIONS_KEY_ORDER,
  WORKFLOW_DISPATCH_KEY_ORDER,
  WORKFLOW_DISPATCH_INPUT_KEY_ORDER,
  WORKFLOW_CALL_KEY_ORDER,
  ENVIRONMENT_KEY_ORDER,
  ACTION_INPUT_KEY_ORDER,
  ACTION_OUTPUT_KEY_ORDER,
  BRANDING_KEY_ORDER,
  COMPOSITE_RUNS_KEY_ORDER,
  DOCKER_RUNS_KEY_ORDER,
  NODE_RUNS_KEY_ORDER,
};

describe("key order constants", () => {
  it.each(Object.entries(ALL_KEY_ORDERS))("%s has no duplicate entries", (_name, order) => {
    expect(new Set(order).size).toBe(order.length);
  });

  it("WORKFLOW_KEY_ORDER starts with 'name' and ends with 'jobs'", () => {
    expect(WORKFLOW_KEY_ORDER[0]).toBe("name");
    expect(WORKFLOW_KEY_ORDER[WORKFLOW_KEY_ORDER.length - 1]).toBe("jobs");
  });

  it("JOB_KEY_ORDER has 'runs-on' before 'steps' and 'steps' before 'outputs'", () => {
    const runsOnIdx = JOB_KEY_ORDER.indexOf("runs-on");
    const stepsIdx = JOB_KEY_ORDER.indexOf("steps");
    const outputsIdx = JOB_KEY_ORDER.indexOf("outputs");
    expect(runsOnIdx).toBeLessThan(stepsIdx);
    expect(stepsIdx).toBeLessThan(outputsIdx);
  });

  it("STEP_KEY_ORDER starts with 'id' and second element is 'name'", () => {
    expect(STEP_KEY_ORDER[0]).toBe("id");
    expect(STEP_KEY_ORDER[1]).toBe("name");
  });

  it("TRIGGER_KEY_ORDER starts with 'branches'", () => {
    expect(TRIGGER_KEY_ORDER[0]).toBe("branches");
  });

  it("ACTION_KEY_ORDER starts with 'name' and ends with 'runs'", () => {
    expect(ACTION_KEY_ORDER[0]).toBe("name");
    expect(ACTION_KEY_ORDER[ACTION_KEY_ORDER.length - 1]).toBe("runs");
  });
});
