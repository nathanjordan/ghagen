import { describe, it, expect } from "vitest";
import { checkout, setupNode, setupPython } from "./steps.js";
import { isModel } from "../models/_base.js";

describe("checkout", () => {
  it("returns defaults with no arguments", () => {
    const s = checkout();
    expect(s._data.uses).toBe("actions/checkout@v4");
    expect(s._data.name).toBe("Checkout");
    expect((s._data.with as Record<string, unknown>)["fetch-depth"]).toBe(1);
  });

  it("sets ref when provided", () => {
    const s = checkout({ ref: "main" });
    expect((s._data.with as Record<string, unknown>).ref).toBe("main");
  });

  it("overrides fetch-depth", () => {
    const s = checkout({ fetchDepth: 0 });
    expect((s._data.with as Record<string, unknown>)["fetch-depth"]).toBe(0);
  });

  it("overrides action version", () => {
    const s = checkout({ version: "actions/checkout@v3" });
    expect(s._data.uses).toBe("actions/checkout@v3");
  });

  it("accepts comment meta", () => {
    const s = checkout({ comment: "clone the repo" });
    expect(s._meta.comment).toBe("clone the repo");
  });

  it("returns a step model", () => {
    const s = checkout();
    expect(isModel(s)).toBe(true);
    expect(s._kind).toBe("step");
  });
});

describe("setupNode", () => {
  it("returns defaults for a given version", () => {
    const s = setupNode({ version: "20" });
    expect(s._data.uses).toBe("actions/setup-node@v4");
    expect((s._data.with as Record<string, unknown>)["node-version"]).toBe("20");
  });

  it("sets registry-url when provided", () => {
    const s = setupNode({ version: "20", registryUrl: "https://npm.pkg.github.com" });
    expect((s._data.with as Record<string, unknown>)["registry-url"]).toBe(
      "https://npm.pkg.github.com",
    );
  });

  it("overrides action version", () => {
    const s = setupNode({ version: "18", actionVersion: "actions/setup-node@v3" });
    expect(s._data.uses).toBe("actions/setup-node@v3");
  });
});

describe("setupPython", () => {
  it("returns defaults for a given version", () => {
    const s = setupPython({ version: "3.12" });
    expect(s._data.uses).toBe("actions/setup-python@v5");
    expect((s._data.with as Record<string, unknown>)["python-version"]).toBe("3.12");
  });

  it("overrides action version", () => {
    const s = setupPython({ version: "3.11", actionVersion: "actions/setup-python@v4" });
    expect(s._data.uses).toBe("actions/setup-python@v4");
  });
});
