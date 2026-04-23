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
    expect(t.data.branches).toEqual(["main"]);
    expect(t.kind).toBe("pushTrigger");
  });

  it("maps camelCase fields to kebab-case", () => {
    const t = pushTrigger({
      branchesIgnore: ["dev"],
      tagsIgnore: ["v0.*"],
      pathsIgnore: ["docs/**"],
    });
    expect(t.data["branches-ignore"]).toEqual(["dev"]);
    expect(t.data["tags-ignore"]).toEqual(["v0.*"]);
    expect(t.data["paths-ignore"]).toEqual(["docs/**"]);
  });
});

describe("prTrigger", () => {
  it("creates a PR trigger with types", () => {
    const t = prTrigger({ types: ["opened", "synchronize"] });
    expect(t.data.types).toEqual(["opened", "synchronize"]);
    expect(t.kind).toBe("prTrigger");
  });

  it("maps camelCase fields to kebab-case", () => {
    const t = prTrigger({
      branchesIgnore: ["release/*"],
      tagsIgnore: ["rc-*"],
      pathsIgnore: ["*.md"],
    });
    expect(t.data["branches-ignore"]).toEqual(["release/*"]);
    expect(t.data["tags-ignore"]).toEqual(["rc-*"]);
    expect(t.data["paths-ignore"]).toEqual(["*.md"]);
  });
});

describe("scheduleTrigger", () => {
  it("creates a schedule trigger with cron", () => {
    const t = scheduleTrigger({ cron: "0 0 * * *" });
    expect(t.data.cron).toBe("0 0 * * *");
    expect(t.kind).toBe("scheduleTrigger");
  });
});

describe("workflowDispatch", () => {
  it("creates a workflow dispatch with inputs", () => {
    const t = workflowDispatch({
      inputs: {
        env: { description: "Environment", type: "choice", options: ["prod", "staging"] },
      },
    });
    expect(t.data.inputs).toBeDefined();
    expect(t.kind).toBe("workflowDispatch");
  });
});

describe("workflowCall", () => {
  it("creates a workflow call with inputs, outputs, and secrets", () => {
    const t = workflowCall({
      inputs: { version: { description: "Version", type: "string", required: true } },
      outputs: { result: { description: "Result", value: "${{ jobs.build.outputs.result }}" } },
      secrets: { token: { description: "API token", required: true } },
    });
    expect(t.data.inputs).toBeDefined();
    expect(t.data.outputs).toBeDefined();
    expect(t.data.secrets).toBeDefined();
    expect(t.kind).toBe("workflowCall");
  });
});

describe("on", () => {
  it("auto-wraps push plain object into a model", () => {
    const o = on({ push: { branches: ["main"] } });
    expect(isModel(o.data.push)).toBe(true);
  });

  it("auto-wraps pullRequest plain object into a model", () => {
    const o = on({ pullRequest: { branches: ["main"] } });
    expect(isModel(o.data.pull_request)).toBe(true);
  });

  it("auto-wraps workflowDispatch plain object into a model", () => {
    const o = on({ workflowDispatch: { inputs: {} } });
    expect(isModel(o.data.workflow_dispatch)).toBe(true);
  });

  it("auto-wraps schedule array items into models", () => {
    const o = on({ schedule: [{ cron: "0 0 * * *" }, { cron: "0 12 * * *" }] });
    const items = o.data.schedule as unknown[];
    expect(items).toHaveLength(2);
    expect(isModel(items[0])).toBe(true);
    expect(isModel(items[1])).toBe(true);
  });

  it("passes through pre-built models unchanged", () => {
    const push = pushTrigger({ branches: ["main"] });
    const o = on({ push });
    expect(o.data.push).toBe(push);
  });

  it("keeps workflowDispatch boolean as-is", () => {
    const o = on({ workflowDispatch: true });
    expect(o.data.workflow_dispatch).toBe(true);
  });

  it("maps pullRequest key to pull_request in data", () => {
    const o = on({ pullRequest: { branches: ["main"] } });
    expect(o.data).toHaveProperty("pull_request");
    expect(o.data).not.toHaveProperty("pullRequest");
  });

  it("maps delete_ to delete", () => {
    const o = on({ delete_: null });
    expect(o.data).toHaveProperty("delete");
    expect(o.data).not.toHaveProperty("delete_");
  });

  it("maps issueComment to issue_comment", () => {
    const o = on({ issueComment: { types: ["created"] } });
    expect(o.data).toHaveProperty("issue_comment");
    expect(o.data).not.toHaveProperty("issueComment");
  });

  it("has correct kind", () => {
    const o = on({ push: { branches: ["main"] } });
    expect(o.kind).toBe("on");
  });
});
