import { describe, it, expect } from "vitest";
import {
  cloneModel,
  isModel,
  isRaw,
  isCommented,
  raw,
  withEolComment,
  StepModel,
  JobModel,
  WorkflowModel,
} from "./_base.js";
import type { Model } from "./_base.js";
import { step } from "./step.js";

describe("cloneModel()", () => {
  it("returns a Model with the same kind and key order", () => {
    const original = new StepModel({ run: "echo hi" }, { eolComment: "x" });
    const cloned = cloneModel(original);
    expect(isModel(cloned)).toBe(true);
    expect(cloned.kind).toBe(original.kind);
    expect(cloned.keyOrder).toBe(original.keyOrder);
  });

  it("performs a deep copy of data", () => {
    const original = new StepModel({ with: { a: "1" } }, {});
    const cloned = cloneModel(original);
    (cloned.data as Record<string, Record<string, string>>).with!.a = "2";
    expect((original.data as Record<string, Record<string, string>>).with!.a).toBe("1");
  });

  it("deep-copies Commented values inside data", () => {
    const original = new StepModel({ uses: withEolComment("actions/checkout@v4", "v4") }, {});
    const cloned = cloneModel(original);
    expect(isCommented(cloned.data["uses"])).toBe(true);
    const c = cloned.data["uses"] as { value: string; eolComment: string };
    expect(c.value).toBe("actions/checkout@v4");
    expect(c.eolComment).toBe("v4");
    // Mutating the clone's nested Commented doesn't affect the original.
    (cloned.data as Record<string, unknown>)["uses"] = "modified";
    expect(isCommented(original.data["uses"])).toBe(true);
  });

  it("preserves the postProcess function by reference", () => {
    const fn = () => {};
    const original = new WorkflowModel({}, { postProcess: fn });
    const cloned = cloneModel(original);
    expect(cloned.meta.postProcess).toBe(fn);
  });

  it("preserves Raw values inside data", () => {
    const r = raw("custom");
    const original = new StepModel({ shell: r }, {});
    const cloned = cloneModel(original);
    expect(isRaw(cloned.data["shell"])).toBe(true);
    expect((cloned.data["shell"] as { value: string }).value).toBe("custom");
  });

  it("recursively clones nested Models inside data arrays", () => {
    const inner = new StepModel({ run: "echo hi" }, {});
    const outer = new JobModel({ steps: [inner] }, {});
    const cloned = cloneModel(outer);
    const clonedInner = (cloned.data["steps"] as unknown[])[0] as Model;
    expect(isModel(clonedInner)).toBe(true);
    expect(clonedInner.kind).toBe("step");
    // Mutating the clone's nested step doesn't affect the original.
    (clonedInner.data as Record<string, string>).run = "modified";
    expect((inner.data as Record<string, string>).run).toBe("echo hi");
  });

  it("preserves sourceLocation by reference", () => {
    const original = step({ run: "echo hi" });
    const cloned = cloneModel(original);
    expect(cloned.sourceLocation).toBe(original.sourceLocation);
  });

  it("returns a non-frozen object so transforms can mutate it", () => {
    const original = step({ uses: "actions/checkout@v4" });
    const cloned = cloneModel(original);
    expect(Object.isFrozen(cloned)).toBe(false);
    expect(Object.isFrozen(cloned.data)).toBe(false);
  });
});
