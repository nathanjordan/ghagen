import { describe, it, expect } from "vitest";
import {
  action,
  actionInputDef,
  actionOutputDef,
  branding,
  compositeRuns,
  dockerRuns,
  nodeRuns,
} from "./action.js";
import { step } from "./step.js";
import { toData } from "../emitter/yaml-writer.js";

describe("actionInputDef", () => {
  it("creates an input def with description, required, default, and deprecationMessage", () => {
    const inp = actionInputDef({
      description: "The token",
      required: true,
      default: "abc",
      deprecationMessage: "Use token_v2",
    });
    expect(toData(inp)).toEqual({
      description: "The token",
      required: true,
      default: "abc",
      deprecationMessage: "Use token_v2",
    });
    expect(inp.kind).toBe("actionInput");
  });
});

describe("actionOutputDef", () => {
  it("creates an output def with description and value", () => {
    const out = actionOutputDef({
      description: "The result",
      value: "${{ steps.run.outputs.result }}",
    });
    expect(toData(out)).toEqual({
      description: "The result",
      value: "${{ steps.run.outputs.result }}",
    });
    expect(out.kind).toBe("actionOutput");
  });

  it("creates an output def with description only (no value)", () => {
    expect(toData(actionOutputDef({ description: "Some output" }))).toEqual({
      description: "Some output",
    });
  });
});

describe("branding", () => {
  it("creates branding with icon and color", () => {
    const b = branding({ icon: "zap", color: "blue" });
    expect(toData(b)).toEqual({ icon: "zap", color: "blue" });
    expect(b.kind).toBe("branding");
  });
});

describe("compositeRuns", () => {
  it("has using set to composite and includes steps", () => {
    const cr = compositeRuns({ using: "composite", steps: [step({ run: "echo hi" })] });
    expect(toData(cr)).toEqual({ using: "composite", steps: [{ run: "echo hi" }] });
    expect(cr.kind).toBe("compositeRuns");
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
    const data = toData(dr) as Record<string, unknown>;
    expect(data["pre-entrypoint"]).toBe("pre.sh");
    expect(data["post-entrypoint"]).toBe("post.sh");
    expect(data["pre-if"]).toBe("always()");
    expect(data["post-if"]).toBe("success()");
    expect(data).not.toHaveProperty("preEntrypoint");
    expect(data).not.toHaveProperty("postEntrypoint");
    expect(dr.kind).toBe("dockerRuns");
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
    const data = toData(nr) as Record<string, unknown>;
    expect(data["pre-if"]).toBe("always()");
    expect(data["post-if"]).toBe("success()");
    expect(data).not.toHaveProperty("preIf");
    expect(data).not.toHaveProperty("postIf");
    expect(nr.kind).toBe("nodeRuns");
  });
});

describe("action", () => {
  it("creates a full action with name, description, author, branding, inputs, outputs, and runs", () => {
    const a = action({
      name: "My Action",
      description: "Does things",
      author: "me",
      branding: branding({ icon: "zap", color: "blue" }),
      inputs: { token: actionInputDef({ description: "Token", required: true }) },
      outputs: { result: actionOutputDef({ description: "Result", value: "val" }) },
      runs: compositeRuns({ using: "composite", steps: [step({ run: "echo hi" })] }),
    });
    expect(toData(a)).toEqual({
      name: "My Action",
      description: "Does things",
      author: "me",
      branding: { icon: "zap", color: "blue" },
      inputs: { token: { description: "Token", required: true } },
      outputs: { result: { description: "Result", value: "val" } },
      runs: { using: "composite", steps: [{ run: "echo hi" }] },
    });
    expect(a.kind).toBe("action");
  });
});
