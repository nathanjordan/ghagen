import { describe, it, expect } from "vitest";
import {
  cloneModel,
  createModel,
  isModel,
  isRaw,
  isCommented,
  raw,
  withEolComment,
} from "./_base.js";
import { step } from "./step.js";

describe("cloneModel()", () => {
  it("returns a Model with the same kind and key order", () => {
    const original = createModel("step", { run: "echo hi" }, { eolComment: "x" }, ["run"]);
    const cloned = cloneModel(original);
    expect(isModel(cloned)).toBe(true);
    expect(cloned._kind).toBe(original._kind);
    expect(cloned._keyOrder).toBe(original._keyOrder);
  });

  it("performs a deep copy of _data", () => {
    const original = createModel("step", { with: { a: "1" } }, {}, []);
    const cloned = cloneModel(original);
    (cloned._data as Record<string, Record<string, string>>).with!.a = "2";
    expect((original._data as Record<string, Record<string, string>>).with!.a).toBe("1");
  });

  it("deep-copies Commented values inside _data", () => {
    const original = createModel(
      "step",
      { uses: withEolComment("actions/checkout@v4", "v4") },
      {},
      [],
    );
    const cloned = cloneModel(original);
    expect(isCommented(cloned._data["uses"])).toBe(true);
    const c = cloned._data["uses"] as { value: string; eolComment: string };
    expect(c.value).toBe("actions/checkout@v4");
    expect(c.eolComment).toBe("v4");
    // Mutating the clone's nested Commented doesn't affect the original.
    (cloned._data as Record<string, unknown>)["uses"] = "modified";
    expect(isCommented(original._data["uses"])).toBe(true);
  });

  it("preserves the postProcess function by reference", () => {
    const fn = () => {};
    const original = createModel("workflow", {}, { postProcess: fn }, []);
    const cloned = cloneModel(original);
    expect(cloned._meta.postProcess).toBe(fn);
  });

  it("preserves Raw values inside _data", () => {
    const r = raw("custom");
    const original = createModel("step", { shell: r }, {}, []);
    const cloned = cloneModel(original);
    expect(isRaw(cloned._data["shell"])).toBe(true);
    expect((cloned._data["shell"] as { value: string }).value).toBe("custom");
  });

  it("recursively clones nested Models inside _data arrays", () => {
    const inner = createModel("step", { run: "echo hi" }, {}, []);
    const outer = createModel("job", { steps: [inner] }, {}, []);
    const cloned = cloneModel(outer);
    const clonedInner = (cloned._data["steps"] as unknown[])[0] as ReturnType<typeof createModel>;
    expect(isModel(clonedInner)).toBe(true);
    expect(clonedInner._kind).toBe("step");
    // Mutating the clone's nested step doesn't affect the original.
    (clonedInner._data as Record<string, string>).run = "modified";
    expect((inner._data as Record<string, string>).run).toBe("echo hi");
  });

  it("preserves _sourceLocation by reference", () => {
    const original = step({ run: "echo hi" });
    const cloned = cloneModel(original);
    expect(cloned._sourceLocation).toBe(original._sourceLocation);
  });

  it("returns a non-frozen object so transforms can mutate it", () => {
    const original = step({ uses: "actions/checkout@v4" });
    const cloned = cloneModel(original);
    expect(Object.isFrozen(cloned)).toBe(false);
    expect(Object.isFrozen(cloned._data)).toBe(false);
  });
});
