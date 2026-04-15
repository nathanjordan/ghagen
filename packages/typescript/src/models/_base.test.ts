import { describe, it, expect } from "vitest";
import { raw, isRaw, createModel, isModel, extractMeta, mapFields } from "./_base.js";

// ---------------------------------------------------------------------------
// raw()
// ---------------------------------------------------------------------------
describe("raw()", () => {
  it("wraps a string value", () => {
    const r = raw("hello");
    expect(r.value).toBe("hello");
  });

  it("wraps a number value", () => {
    const r = raw(42);
    expect(r.value).toBe(42);
  });

  it("wraps an object value", () => {
    const obj = { nested: true };
    const r = raw(obj);
    expect(r.value).toBe(obj);
  });

  it("returns a frozen object", () => {
    const r = raw("frozen");
    expect(Object.isFrozen(r)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// isRaw()
// ---------------------------------------------------------------------------
describe("isRaw()", () => {
  it("returns true for a raw value", () => {
    expect(isRaw(raw("yes"))).toBe(true);
  });

  it("returns false for a plain object", () => {
    expect(isRaw({ value: "no" })).toBe(false);
  });

  it("returns false for null", () => {
    expect(isRaw(null)).toBe(false);
  });

  it("returns false for undefined", () => {
    expect(isRaw(undefined)).toBe(false);
  });

  it("returns false for a primitive", () => {
    expect(isRaw(42)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// createModel()
// ---------------------------------------------------------------------------
describe("createModel()", () => {
  it("returns an object with the correct _kind", () => {
    const m = createModel("workflow", {}, {}, []);
    expect(m._kind).toBe("workflow");
  });

  it("stores _data", () => {
    const data = { name: "ci" };
    const m = createModel("workflow", data, {}, []);
    expect(m._data).toEqual(data);
  });

  it("stores _meta", () => {
    const meta = { comment: "hello" };
    const m = createModel("workflow", {}, meta, []);
    expect(m._meta).toEqual(meta);
  });

  it("stores _keyOrder", () => {
    const order = ["name", "on", "jobs"] as const;
    const m = createModel("workflow", {}, {}, order);
    expect(m._keyOrder).toEqual(order);
  });

  it("returns a frozen object", () => {
    const m = createModel("step", {}, {}, []);
    expect(Object.isFrozen(m)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// isModel()
// ---------------------------------------------------------------------------
describe("isModel()", () => {
  it("returns true for a model", () => {
    const m = createModel("job", {}, {}, []);
    expect(isModel(m)).toBe(true);
  });

  it("returns false for a plain object", () => {
    expect(isModel({ _kind: "job", _data: {}, _meta: {}, _keyOrder: [] })).toBe(false);
  });

  it("returns false for null", () => {
    expect(isModel(null)).toBe(false);
  });

  it("returns false for undefined", () => {
    expect(isModel(undefined)).toBe(false);
  });

  it("returns false for an array", () => {
    expect(isModel([])).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// extractMeta()
// ---------------------------------------------------------------------------
describe("extractMeta()", () => {
  it("separates meta keys from data keys", () => {
    const input = {
      name: "ci",
      comment: "block comment",
      eolComment: "eol",
      fieldComments: { name: "before name" },
    };
    const [data, meta] = extractMeta(input);
    expect(data).toEqual({ name: "ci" });
    expect(meta).toEqual({
      comment: "block comment",
      eolComment: "eol",
      fieldComments: { name: "before name" },
    });
  });

  it("returns empty meta when no meta keys are present", () => {
    const input = { name: "ci", runsOn: "ubuntu-latest" };
    const [data, meta] = extractMeta(input);
    expect(data).toEqual({ name: "ci", runsOn: "ubuntu-latest" });
    expect(meta).toEqual({});
  });

  it("returns empty data when only meta keys are present", () => {
    const input = { comment: "only meta", extras: { foo: 1 } };
    const [data, meta] = extractMeta(input);
    expect(data).toEqual({});
    expect(meta).toEqual({ comment: "only meta", extras: { foo: 1 } });
  });
});

// ---------------------------------------------------------------------------
// mapFields()
// ---------------------------------------------------------------------------
describe("mapFields()", () => {
  it("maps camelCase keys to output keys via a field map", () => {
    const data = { runsOn: "ubuntu-latest", timeoutMinutes: 10 };
    const fieldMap = { runsOn: "runs-on", timeoutMinutes: "timeout-minutes" };
    expect(mapFields(data, fieldMap)).toEqual({
      "runs-on": "ubuntu-latest",
      "timeout-minutes": 10,
    });
  });

  it("skips undefined values", () => {
    const data = { runsOn: "ubuntu-latest", timeoutMinutes: undefined };
    const fieldMap = { runsOn: "runs-on", timeoutMinutes: "timeout-minutes" };
    expect(mapFields(data, fieldMap)).toEqual({ "runs-on": "ubuntu-latest" });
  });

  it("ignores data keys not in the field map", () => {
    const data = { runsOn: "ubuntu-latest", extra: "ignored" };
    const fieldMap = { runsOn: "runs-on" };
    expect(mapFields(data, fieldMap)).toEqual({ "runs-on": "ubuntu-latest" });
  });
});
