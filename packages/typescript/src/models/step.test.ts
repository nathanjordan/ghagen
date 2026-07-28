import { describe, it, expect } from "vitest";
import { step } from "./step.js";
import { job } from "./job.js";
import { workflow } from "./workflow.js";
import { isModel, raw } from "./_base.js";
import { toData, toYaml } from "../emitter/yaml-writer.js";

describe("step", () => {
  it("creates a basic run step", () => {
    expect(toData(step({ name: "Test", run: "pytest" }))).toEqual({ name: "Test", run: "pytest" });
  });

  it("creates a basic uses step", () => {
    expect(toData(step({ uses: "actions/checkout@v4" }))).toEqual({ uses: "actions/checkout@v4" });
  });

  it("maps with_ to with", () => {
    const data = toData(step({ uses: "actions/setup-node@v4", with_: { "node-version": "20" } }));
    expect(data).toEqual({ uses: "actions/setup-node@v4", with: { "node-version": "20" } });
  });

  it("maps if_ to if", () => {
    const data = toData(step({ run: "echo hi", if_: "github.ref == 'refs/heads/main'" })) as Record<
      string,
      unknown
    >;
    expect(data["if"]).toBe("github.ref == 'refs/heads/main'");
    expect(data).not.toHaveProperty("if_");
  });

  it("passes shell through", () => {
    const data = toData(step({ run: "echo hi", shell: "bash" })) as Record<string, unknown>;
    expect(data.shell).toBe("bash");
  });

  it("unwraps raw() shell to its inner value", () => {
    const data = toData(step({ run: "echo hi", shell: raw("custom-shell") }));
    expect(data).toEqual({ run: "echo hi", shell: "custom-shell" });
  });

  it("maps workingDirectory to working-directory", () => {
    const data = toData(step({ run: "ls", workingDirectory: "/tmp" })) as Record<string, unknown>;
    expect(data["working-directory"]).toBe("/tmp");
    expect(data).not.toHaveProperty("workingDirectory");
  });

  it("maps continueOnError to continue-on-error", () => {
    const data = toData(step({ run: "ls", continueOnError: true })) as Record<string, unknown>;
    expect(data["continue-on-error"]).toBe(true);
    expect(data).not.toHaveProperty("continueOnError");
  });

  it("maps timeoutMinutes to timeout-minutes", () => {
    const data = toData(step({ run: "ls", timeoutMinutes: 10 })) as Record<string, unknown>;
    expect(data["timeout-minutes"]).toBe(10);
    expect(data).not.toHaveProperty("timeoutMinutes");
  });

  it("omits undefined optional fields", () => {
    expect(Object.keys(toData(step({ run: "echo hi" })) as Record<string, unknown>)).toEqual([
      "run",
    ]);
  });

  it("extracts meta into meta and does not emit it as a field", () => {
    const s = step({ run: "echo hi", comment: "Run tests" });
    expect(s.meta).toEqual({ comment: "Run tests" });
    expect(toData(s)).toEqual({ run: "echo hi" });
  });

  it("has correct kind and passes isModel", () => {
    const s = step({ run: "echo hi" });
    expect(s.kind).toBe("step");
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
