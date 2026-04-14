import { describe, it, expect } from "vitest";
import { step } from "./step.js";
import { isModel, raw } from "./_base.js";
import { STEP_KEY_ORDER } from "../emitter/key-order.js";

describe("step", () => {
  it("creates a basic run step", () => {
    const s = step({ name: "Test", run: "pytest" });
    expect(s._data).toEqual({ name: "Test", run: "pytest" });
  });

  it("creates a basic uses step", () => {
    const s = step({ uses: "actions/checkout@v4" });
    expect(s._data.uses).toBe("actions/checkout@v4");
  });

  it("maps with_ to with", () => {
    const s = step({ uses: "actions/setup-node@v4", with_: { "node-version": "20" } });
    expect(s._data["with"]).toEqual({ "node-version": "20" });
    expect(s._data).not.toHaveProperty("with_");
  });

  it("maps if_ to if", () => {
    const s = step({ run: "echo hi", if_: "github.ref == 'refs/heads/main'" });
    expect(s._data["if"]).toBe("github.ref == 'refs/heads/main'");
    expect(s._data).not.toHaveProperty("if_");
  });

  it("passes shell through", () => {
    const s = step({ run: "echo hi", shell: "bash" });
    expect(s._data.shell).toBe("bash");
  });

  it("stores shell as Raw when using raw()", () => {
    const s = step({ run: "echo hi", shell: raw("custom-shell") });
    expect(s._data.shell).toEqual(raw("custom-shell"));
  });

  it("maps workingDirectory to working-directory", () => {
    const s = step({ run: "ls", workingDirectory: "/tmp" });
    expect(s._data["working-directory"]).toBe("/tmp");
    expect(s._data).not.toHaveProperty("workingDirectory");
  });

  it("maps continueOnError to continue-on-error", () => {
    const s = step({ run: "ls", continueOnError: true });
    expect(s._data["continue-on-error"]).toBe(true);
    expect(s._data).not.toHaveProperty("continueOnError");
  });

  it("maps timeoutMinutes to timeout-minutes", () => {
    const s = step({ run: "ls", timeoutMinutes: 10 });
    expect(s._data["timeout-minutes"]).toBe(10);
    expect(s._data).not.toHaveProperty("timeoutMinutes");
  });

  it("omits undefined optional fields from _data", () => {
    const s = step({ run: "echo hi" });
    expect(Object.keys(s._data)).toEqual(["run"]);
  });

  it("extracts meta into _meta", () => {
    const s = step({ run: "echo hi", comment: "Run tests" });
    expect(s._meta).toEqual({ comment: "Run tests" });
    expect(s._data).not.toHaveProperty("comment");
  });

  it("has correct _kind, _keyOrder, and passes isModel", () => {
    const s = step({ run: "echo hi" });
    expect(s._kind).toBe("step");
    expect(s._keyOrder).toEqual(STEP_KEY_ORDER);
    expect(isModel(s)).toBe(true);
  });
});
