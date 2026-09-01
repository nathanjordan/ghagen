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
import { toData, toYaml } from "../emitter/yaml-writer.js";
import { workflow } from "./workflow.js";

/**
 * The emitted shape of a `workflow_dispatch` / `workflow_call` sub-map: a map
 * of definition name to a map of key to value (`inputs.version.description`).
 * `toData` returns `unknown`, so the depth has to be named to be indexed; the
 * casts below used to stop one level short, which left the leaf `unknown` and
 * only compiled because this file was outside the gate (docs/issues/09).
 */
type DefMap = Record<string, Record<string, unknown>>;

describe("pushTrigger", () => {
  it("creates a push trigger with branches", () => {
    const t = pushTrigger({ branches: ["main"] });
    expect(toData(t)).toEqual({ branches: ["main"] });
    expect(t.kind).toBe("pushTrigger");
  });

  it("maps camelCase fields to kebab-case", () => {
    const data = toData(
      pushTrigger({
        branchesIgnore: ["dev"],
        tagsIgnore: ["v0.*"],
        pathsIgnore: ["docs/**"],
      }),
    ) as Record<string, unknown>;
    expect(data["branches-ignore"]).toEqual(["dev"]);
    expect(data["tags-ignore"]).toEqual(["v0.*"]);
    expect(data["paths-ignore"]).toEqual(["docs/**"]);
  });
});

describe("prTrigger", () => {
  it("creates a PR trigger with types", () => {
    const t = prTrigger({ types: ["opened", "synchronize"] });
    expect(toData(t)).toEqual({ types: ["opened", "synchronize"] });
    expect(t.kind).toBe("prTrigger");
  });

  it("maps camelCase fields to kebab-case", () => {
    const data = toData(
      prTrigger({
        branchesIgnore: ["release/*"],
        tagsIgnore: ["rc-*"],
        pathsIgnore: ["*.md"],
      }),
    ) as Record<string, unknown>;
    expect(data["branches-ignore"]).toEqual(["release/*"]);
    expect(data["tags-ignore"]).toEqual(["rc-*"]);
    expect(data["paths-ignore"]).toEqual(["*.md"]);
  });
});

describe("scheduleTrigger", () => {
  it("creates a schedule trigger with cron", () => {
    const t = scheduleTrigger({ cron: "0 0 * * *" });
    expect(toData(t)).toEqual({ cron: "0 0 * * *" });
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
    expect((toData(t) as Record<string, unknown>).inputs).toBeDefined();
    expect(t.kind).toBe("workflowDispatch");
  });

  it("emits deprecationMessage on an input def", () => {
    // Modelled for *action* inputs in both ports but not for workflow_dispatch
    // inputs — the action side is swept, which is why it never drifted. The
    // Snapshot spells this key camelCase, unlike its five siblings.
    const t = workflowDispatch({
      inputs: { env: { description: "Environment", deprecationMessage: "use `target`" } },
    });
    const inputs = (toData(t) as Record<string, DefMap>).inputs;
    expect(inputs.env.deprecationMessage).toBe("use `target`");
  });
});

describe("workflowCall", () => {
  it("creates a workflow call with inputs, outputs, and secrets", () => {
    const t = workflowCall({
      inputs: { version: { description: "Version", type: "string", required: true } },
      outputs: { result: { description: "Result", value: "${{ jobs.build.outputs.result }}" } },
      secrets: { token: { description: "API token", required: true } },
    });
    const data = toData(t) as Record<string, unknown>;
    expect(data.inputs).toBeDefined();
    expect(data.outputs).toBeDefined();
    expect(data.secrets).toBeDefined();
    expect(t.kind).toBe("workflowCall");
  });

  // Python models each workflow_call sub-map entry as its own model with its
  // own spec, so it emits in canonical key order. TypeScript had no spec for
  // any of the three, so the values reached the Emitter as plain objects and
  // emitted in the author's insertion order — the same program produced three
  // different YAML orderings across the ports. Python is the reference order.
  it("emits input defs in canonical key order, not insertion order", () => {
    const t = workflowCall({
      inputs: { version: { type: "string", description: "Version", required: true } },
    });
    const inputs = (toData(t) as Record<string, DefMap>).inputs;
    expect(Object.keys(inputs.version)).toEqual(["description", "required", "type"]);
  });

  it("emits output defs in canonical key order, not insertion order", () => {
    const t = workflowCall({
      outputs: { result: { value: "${{ jobs.build.outputs.result }}", description: "Result" } },
    });
    const outputs = (toData(t) as Record<string, DefMap>).outputs;
    expect(Object.keys(outputs.result)).toEqual(["description", "value"]);
  });

  it("emits secret defs in canonical key order, not insertion order", () => {
    const t = workflowCall({
      secrets: { token: { required: true, description: "API token" } },
    });
    const secrets = (toData(t) as Record<string, DefMap>).secrets;
    expect(Object.keys(secrets.token)).toEqual(["description", "required"]);
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
    const data = toData(on({ pullRequest: { branches: ["main"] } })) as Record<string, unknown>;
    expect(data).toHaveProperty("pull_request");
    expect(data).not.toHaveProperty("pullRequest");
  });

  it("maps delete_ to delete", () => {
    const data = toData(on({ delete_: null })) as Record<string, unknown>;
    expect(data).toHaveProperty("delete");
    expect(data).not.toHaveProperty("delete_");
  });

  it("emits pullRequestReview and pullRequestReviewComment", () => {
    // Two schema-declared events neither port modelled: `on({ pullRequestReview:
    // {} })` was TS2561 before, and `On(pull_request_review={})` raised.
    const data = toData(
      on({
        pullRequestReview: { types: ["submitted"] },
        pullRequestReviewComment: { types: ["created"] },
      }),
    ) as Record<string, unknown>;
    expect(data.pull_request_review).toEqual({ types: ["submitted"] });
    expect(data.pull_request_review_comment).toEqual({ types: ["created"] });
  });

  it("maps issueComment to issue_comment", () => {
    const data = toData(on({ issueComment: { types: ["created"] } })) as Record<string, unknown>;
    expect(data).toHaveProperty("issue_comment");
    expect(data).not.toHaveProperty("issueComment");
  });

  it("has correct kind", () => {
    const o = on({ push: { branches: ["main"] } });
    expect(o.kind).toBe("on");
  });

  it("emits keys alphabetically, interleaving a dynamic extra event", () => {
    // `workflowRun` (→ workflow_run) and a dynamic `merge_group` extra must
    // interleave alphabetically with the typed fields — the sort lives in the
    // Emitter (alphabetical OrderMode), not a factory pre-sort.
    const o = on({
      workflowRun: { types: ["completed"] },
      push: { branches: ["main"] },
      extras: { merge_group: {} },
    });
    expect(Object.keys(toData(o) as Record<string, unknown>)).toEqual([
      "merge_group",
      "push",
      "workflow_run",
    ]);
  });

  it("emits an empty workflowDispatch as a present-null key (toData)", () => {
    const data = toData(on({ workflowDispatch: {} })) as Record<string, unknown>;
    expect(data).toHaveProperty("workflow_dispatch");
    expect(data["workflow_dispatch"]).toBeNull();
  });

  it("emits an empty workflowDispatch as a bare `workflow_dispatch:` key (YAML)", () => {
    const yaml = toYaml(workflow({ name: "W", on: on({ workflowDispatch: {} }), jobs: {} }), {
      header: null,
    });
    expect(yaml).toContain("workflow_dispatch:\n");
    expect(yaml).not.toContain("workflow_dispatch: {}");
  });

  it("keeps a boolean workflowDispatch untouched (not present-null)", () => {
    const data = toData(on({ workflowDispatch: true })) as Record<string, unknown>;
    expect(data["workflow_dispatch"]).toBe(true);
  });
});
