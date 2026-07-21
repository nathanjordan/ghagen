import { describe, it, expect } from "vitest";
import { step, STEP_SPEC } from "./step.js";
import { job } from "./job.js";
import { workflow } from "./workflow.js";
import { isModel, raw } from "./_base.js";
import { toYaml } from "../emitter/yaml-writer.js";

describe("step", () => {
  it("creates a basic run step", () => {
    const s = step({ name: "Test", run: "pytest" });
    expect(s.data).toEqual({ name: "Test", run: "pytest" });
  });

  it("creates a basic uses step", () => {
    const s = step({ uses: "actions/checkout@v4" });
    expect(s.data.uses).toBe("actions/checkout@v4");
  });

  it("maps with_ to with", () => {
    const s = step({ uses: "actions/setup-node@v4", with_: { "node-version": "20" } });
    expect(s.data["with"]).toEqual({ "node-version": "20" });
    expect(s.data).not.toHaveProperty("with_");
  });

  it("maps if_ to if", () => {
    const s = step({ run: "echo hi", if_: "github.ref == 'refs/heads/main'" });
    expect(s.data["if"]).toBe("github.ref == 'refs/heads/main'");
    expect(s.data).not.toHaveProperty("if_");
  });

  it("passes shell through", () => {
    const s = step({ run: "echo hi", shell: "bash" });
    expect(s.data.shell).toBe("bash");
  });

  it("stores shell as Raw when using raw()", () => {
    const s = step({ run: "echo hi", shell: raw("custom-shell") });
    expect(s.data.shell).toEqual(raw("custom-shell"));
  });

  it("maps workingDirectory to working-directory", () => {
    const s = step({ run: "ls", workingDirectory: "/tmp" });
    expect(s.data["working-directory"]).toBe("/tmp");
    expect(s.data).not.toHaveProperty("workingDirectory");
  });

  it("maps continueOnError to continue-on-error", () => {
    const s = step({ run: "ls", continueOnError: true });
    expect(s.data["continue-on-error"]).toBe(true);
    expect(s.data).not.toHaveProperty("continueOnError");
  });

  it("maps timeoutMinutes to timeout-minutes", () => {
    const s = step({ run: "ls", timeoutMinutes: 10 });
    expect(s.data["timeout-minutes"]).toBe(10);
    expect(s.data).not.toHaveProperty("timeoutMinutes");
  });

  it("omits undefined optional fields from data", () => {
    const s = step({ run: "echo hi" });
    expect(Object.keys(s.data)).toEqual(["run"]);
  });

  it("extracts meta into meta", () => {
    const s = step({ run: "echo hi", comment: "Run tests" });
    expect(s.meta).toEqual({ comment: "Run tests" });
    expect(s.data).not.toHaveProperty("comment");
  });

  it("has correct kind, spec, and passes isModel", () => {
    const s = step({ run: "echo hi" });
    expect(s.kind).toBe("step");
    expect(s.spec).toBe(STEP_SPEC);
    expect(isModel(s)).toBe(true);
  });
});

describe("step dedent (emit-time, ADR-0002)", () => {
  const indented = "\n        echo hello\n        echo world\n    ";

  function wrap(s: ReturnType<typeof step>) {
    return workflow({
      name: "W",
      on: { push: {} },
      jobs: { j: job({ runsOn: "ubuntu-latest", steps: [s] }) },
    });
  }

  it("stores run raw at construction (no dedent)", () => {
    const s = step({ run: indented });
    expect(s.data["run"]).toBe(indented);
  });

  it("dedents run by default at emit time", () => {
    const s = step({ run: indented });
    const dedented = toYaml(wrap(s), { header: null });
    const rawEmit = toYaml(wrap(s), { header: null, autoDedent: false });
    expect(dedented).toContain("echo hello");
    // Dedent removes the source indentation, so default output differs from
    // the raw (undedented) emit.
    expect(dedented).not.toBe(rawEmit);
    // The caller's model is untouched.
    expect(s.data["run"]).toBe(indented);
  });

  it("skips dedent when autoDedent is false", () => {
    const s = step({ run: indented });
    // The extra source indentation survives on top of YAML's own block indent.
    const yaml = toYaml(wrap(s), { header: null, autoDedent: false });
    const dedented = toYaml(wrap(s), { header: null });
    expect(yaml).not.toBe(dedented);
    expect(yaml.includes("        echo hello")).toBe(true);
  });
});
