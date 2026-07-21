import { describe, it, expect } from "vitest";
import {
  action,
  actionInputDef,
  actionOutputDef,
  branding,
  compositeRuns,
  dockerRuns,
  nodeRuns,
  ACTION_SPEC,
  ACTION_INPUT_SPEC,
  ACTION_OUTPUT_SPEC,
  BRANDING_SPEC,
  COMPOSITE_RUNS_SPEC,
  DOCKER_RUNS_SPEC,
  NODE_RUNS_SPEC,
} from "./action.js";
import { step } from "./step.js";

describe("actionInputDef", () => {
  it("creates an input def with description, required, default, and deprecationMessage", () => {
    const inp = actionInputDef({
      description: "The token",
      required: true,
      default: "abc",
      deprecationMessage: "Use token_v2",
    });
    expect(inp.data.description).toBe("The token");
    expect(inp.data.required).toBe(true);
    expect(inp.data.default).toBe("abc");
    expect(inp.data.deprecationMessage).toBe("Use token_v2");
    expect(inp.kind).toBe("actionInput");
    expect(inp.spec).toBe(ACTION_INPUT_SPEC);
  });
});

describe("actionOutputDef", () => {
  it("creates an output def with description and value", () => {
    const out = actionOutputDef({
      description: "The result",
      value: "${{ steps.run.outputs.result }}",
    });
    expect(out.data.description).toBe("The result");
    expect(out.data.value).toBe("${{ steps.run.outputs.result }}");
    expect(out.kind).toBe("actionOutput");
    expect(out.spec).toBe(ACTION_OUTPUT_SPEC);
  });

  it("creates an output def with description only (no value)", () => {
    const out = actionOutputDef({ description: "Some output" });
    expect(out.data.description).toBe("Some output");
    expect(out.data).not.toHaveProperty("value");
  });
});

describe("branding", () => {
  it("creates branding with icon and color", () => {
    const b = branding({ icon: "zap", color: "blue" });
    expect(b.data.icon).toBe("zap");
    expect(b.data.color).toBe("blue");
    expect(b.kind).toBe("branding");
    expect(b.spec).toBe(BRANDING_SPEC);
  });
});

describe("compositeRuns", () => {
  it("has using set to composite and includes steps", () => {
    const s = step({ run: "echo hi" });
    const cr = compositeRuns({ using: "composite", steps: [s] });
    expect(cr.data.using).toBe("composite");
    expect(cr.data.steps).toEqual([s]);
    expect(cr.kind).toBe("compositeRuns");
    expect(cr.spec).toBe(COMPOSITE_RUNS_SPEC);
  });
});

describe("dockerRuns", () => {
  it("maps preEntrypoint, postEntrypoint, preIf, postIf to kebab-case", () => {
    const dr = dockerRuns({
      using: "docker",
      image: "Dockerfile",
      preEntrypoint: "pre.sh",
      postEntrypoint: "post.sh",
      preIf: "always()",
      postIf: "success()",
    });
    expect(dr.data["pre-entrypoint"]).toBe("pre.sh");
    expect(dr.data["post-entrypoint"]).toBe("post.sh");
    expect(dr.data["pre-if"]).toBe("always()");
    expect(dr.data["post-if"]).toBe("success()");
    expect(dr.data).not.toHaveProperty("preEntrypoint");
    expect(dr.data).not.toHaveProperty("postEntrypoint");
    expect(dr.kind).toBe("dockerRuns");
    expect(dr.spec).toBe(DOCKER_RUNS_SPEC);
  });
});

describe("nodeRuns", () => {
  it("maps preIf and postIf to kebab-case", () => {
    const nr = nodeRuns({
      using: "node20",
      main: "dist/index.js",
      pre: "dist/setup.js",
      post: "dist/cleanup.js",
      preIf: "always()",
      postIf: "success()",
    });
    expect(nr.data["pre-if"]).toBe("always()");
    expect(nr.data["post-if"]).toBe("success()");
    expect(nr.data).not.toHaveProperty("preIf");
    expect(nr.data).not.toHaveProperty("postIf");
    expect(nr.kind).toBe("nodeRuns");
    expect(nr.spec).toBe(NODE_RUNS_SPEC);
  });
});

describe("action", () => {
  it("creates a full action with name, description, author, branding, inputs, outputs, and runs", () => {
    const b = branding({ icon: "zap", color: "blue" });
    const inp = actionInputDef({ description: "Token", required: true });
    const out = actionOutputDef({ description: "Result", value: "val" });
    const runs = compositeRuns({ using: "composite", steps: [step({ run: "echo hi" })] });

    const a = action({
      name: "My Action",
      description: "Does things",
      author: "me",
      branding: b,
      inputs: { token: inp },
      outputs: { result: out },
      runs,
    });
    expect(a.data.name).toBe("My Action");
    expect(a.data.description).toBe("Does things");
    expect(a.data.author).toBe("me");
    expect(a.data.branding).toBe(b);
    expect(a.data.inputs).toEqual({ token: inp });
    expect(a.data.outputs).toEqual({ result: out });
    expect(a.data.runs).toBe(runs);
    expect(a.kind).toBe("action");
    expect(a.spec).toBe(ACTION_SPEC);
  });
});
