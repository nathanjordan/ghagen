import { describe, it, expect } from "vitest";
import { workflow } from "./workflow.js";
import { isModel } from "./_base.js";
import { job, concurrency } from "./job.js";
import { step } from "./step.js";
import { on } from "./trigger.js";
import { permissions } from "./permissions.js";
import { WORKFLOW_KEY_ORDER } from "../emitter/key-order.js";

describe("workflow", () => {
  it("creates a basic workflow with name, on, and jobs", () => {
    const trigger = on({ push: { branches: ["main"] } });
    const j = job({ runsOn: "ubuntu-latest", steps: [step({ run: "echo hi" })] });
    const w = workflow({ name: "CI", on: trigger, jobs: { build: j } });
    expect(w._data.name).toBe("CI");
    expect(w._data.on).toBe(trigger);
    expect(w._data.jobs).toEqual({ build: j });
  });

  it("maps runName to run-name", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [] });
    const w = workflow({
      name: "CI",
      runName: "Build #${{ github.run_number }}",
      on: on({ push: { branches: ["main"] } }),
      jobs: { build: j },
    });
    expect(w._data["run-name"]).toBe("Build #${{ github.run_number }}");
    expect(w._data).not.toHaveProperty("runName");
  });

  it("auto-wraps on plain object into a model", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [] });
    const w = workflow({ name: "CI", on: { push: { branches: ["main"] } }, jobs: { build: j } });
    expect(isModel(w._data.on)).toBe(true);
  });

  it("auto-wraps permissions plain object into a model", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [] });
    const w = workflow({
      name: "CI",
      on: on({ push: { branches: ["main"] } }),
      permissions: { contents: "read" },
      jobs: { build: j },
    });
    expect(isModel(w._data.permissions)).toBe(true);
  });

  it("auto-wraps defaults plain object into a model", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [] });
    const w = workflow({
      name: "CI",
      on: on({ push: { branches: ["main"] } }),
      defaults: { run: { shell: "bash" } },
      jobs: { build: j },
    });
    expect(isModel(w._data.defaults)).toBe(true);
  });

  it("auto-wraps concurrency plain object into a model", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [] });
    const w = workflow({
      name: "CI",
      on: on({ push: { branches: ["main"] } }),
      concurrency: { group: "ci", cancelInProgress: true },
      jobs: { build: j },
    });
    expect(isModel(w._data.concurrency)).toBe(true);
  });

  it("passes through permissions as read-all string", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [] });
    const w = workflow({
      name: "CI",
      on: on({ push: { branches: ["main"] } }),
      permissions: "read-all",
      jobs: { build: j },
    });
    expect(w._data.permissions).toBe("read-all");
  });

  it("passes through concurrency as a plain string", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [] });
    const w = workflow({
      name: "CI",
      on: on({ push: { branches: ["main"] } }),
      concurrency: "ci-group",
      jobs: { build: j },
    });
    expect(w._data.concurrency).toBe("ci-group");
  });

  it("passes through pre-built models unchanged", () => {
    const trigger = on({ push: { branches: ["main"] } });
    const p = permissions({ contents: "read" });
    const c = concurrency({ group: "ci", cancelInProgress: true });
    const j = job({ runsOn: "ubuntu-latest", steps: [] });
    const w = workflow({
      name: "CI",
      on: trigger,
      permissions: p,
      concurrency: c,
      jobs: { build: j },
    });
    expect(w._data.on).toBe(trigger);
    expect(w._data.permissions).toBe(p);
    expect(w._data.concurrency).toBe(c);
  });

  it("has correct _kind and _keyOrder", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [] });
    const w = workflow({
      name: "CI",
      on: on({ push: { branches: ["main"] } }),
      jobs: { build: j },
    });
    expect(w._kind).toBe("workflow");
    expect(w._keyOrder).toEqual(WORKFLOW_KEY_ORDER);
  });
});
