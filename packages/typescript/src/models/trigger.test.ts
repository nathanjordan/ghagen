import { describe, it, expect } from "vitest";
import {
  pushTrigger,
  prTrigger,
  scheduleTrigger,
  workflowDispatch,
  workflowCall,
  on,
} from "./trigger.js";
import { isModel } from "./_base.js";

describe("pushTrigger", () => {
  it("creates a push trigger with branches", () => {
    const t = pushTrigger({ branches: ["main"] });
    expect(t._data.branches).toEqual(["main"]);
    expect(t._kind).toBe("pushTrigger");
  });

  it("maps camelCase fields to kebab-case", () => {
    const t = pushTrigger({
      branchesIgnore: ["dev"],
      tagsIgnore: ["v0.*"],
      pathsIgnore: ["docs/**"],
    });
    expect(t._data["branches-ignore"]).toEqual(["dev"]);
    expect(t._data["tags-ignore"]).toEqual(["v0.*"]);
    expect(t._data["paths-ignore"]).toEqual(["docs/**"]);
  });
});

describe("prTrigger", () => {
  it("creates a PR trigger with types", () => {
    const t = prTrigger({ types: ["opened", "synchronize"] });
    expect(t._data.types).toEqual(["opened", "synchronize"]);
    expect(t._kind).toBe("prTrigger");
  });

  it("maps camelCase fields to kebab-case", () => {
    const t = prTrigger({
      branchesIgnore: ["release/*"],
      tagsIgnore: ["rc-*"],
      pathsIgnore: ["*.md"],
    });
    expect(t._data["branches-ignore"]).toEqual(["release/*"]);
    expect(t._data["tags-ignore"]).toEqual(["rc-*"]);
    expect(t._data["paths-ignore"]).toEqual(["*.md"]);
  });
});

describe("scheduleTrigger", () => {
  it("creates a schedule trigger with cron", () => {
    const t = scheduleTrigger({ cron: "0 0 * * *" });
    expect(t._data.cron).toBe("0 0 * * *");
    expect(t._kind).toBe("scheduleTrigger");
  });
});

describe("workflowDispatch", () => {
  it("creates a workflow dispatch with inputs", () => {
    const t = workflowDispatch({
      inputs: {
        env: { description: "Environment", type: "choice", options: ["prod", "staging"] },
      },
    });
    expect(t._data.inputs).toBeDefined();
    expect(t._kind).toBe("workflowDispatch");
  });
});

describe("workflowCall", () => {
  it("creates a workflow call with inputs, outputs, and secrets", () => {
    const t = workflowCall({
      inputs: { version: { description: "Version", type: "string", required: true } },
      outputs: { result: { description: "Result", value: "${{ jobs.build.outputs.result }}" } },
      secrets: { token: { description: "API token", required: true } },
    });
    expect(t._data.inputs).toBeDefined();
    expect(t._data.outputs).toBeDefined();
    expect(t._data.secrets).toBeDefined();
    expect(t._kind).toBe("workflowCall");
  });
});

describe("on", () => {
  it("auto-wraps push plain object into a model", () => {
    const o = on({ push: { branches: ["main"] } });
    expect(isModel(o._data.push)).toBe(true);
  });

  it("auto-wraps pullRequest plain object into a model", () => {
    const o = on({ pullRequest: { branches: ["main"] } });
    expect(isModel(o._data.pull_request)).toBe(true);
  });

  it("auto-wraps workflowDispatch plain object into a model", () => {
    const o = on({ workflowDispatch: { inputs: {} } });
    expect(isModel(o._data.workflow_dispatch)).toBe(true);
  });

  it("auto-wraps schedule array items into models", () => {
    const o = on({ schedule: [{ cron: "0 0 * * *" }, { cron: "0 12 * * *" }] });
    const items = o._data.schedule as unknown[];
    expect(items).toHaveLength(2);
    expect(isModel(items[0])).toBe(true);
    expect(isModel(items[1])).toBe(true);
  });

  it("passes through pre-built models unchanged", () => {
    const push = pushTrigger({ branches: ["main"] });
    const o = on({ push });
    expect(o._data.push).toBe(push);
  });

  it("keeps workflowDispatch boolean as-is", () => {
    const o = on({ workflowDispatch: true });
    expect(o._data.workflow_dispatch).toBe(true);
  });

  it("maps pullRequest key to pull_request in _data", () => {
    const o = on({ pullRequest: { branches: ["main"] } });
    expect(o._data).toHaveProperty("pull_request");
    expect(o._data).not.toHaveProperty("pullRequest");
  });

  it("maps delete_ to delete", () => {
    const o = on({ delete_: null });
    expect(o._data).toHaveProperty("delete");
    expect(o._data).not.toHaveProperty("delete_");
  });

  it("maps issueComment to issue_comment", () => {
    const o = on({ issueComment: { types: ["created"] } });
    expect(o._data).toHaveProperty("issue_comment");
    expect(o._data).not.toHaveProperty("issueComment");
  });

  it("has correct _kind", () => {
    const o = on({ push: { branches: ["main"] } });
    expect(o._kind).toBe("on");
  });
});
