import { describe, it, expect } from "vitest";
import {
  raw,
  isRaw,
  isModel,
  extractMeta,
  mapFields,
  WorkflowModel,
  StepModel,
  JobModel,
  Model,
} from "./_base.js";
import { WORKFLOW_KEY_ORDER } from "../emitter/key-order.js";

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
// Model class constructors
// ---------------------------------------------------------------------------
describe("Model class", () => {
  it("returns an object with the correct kind", () => {
    const m = new WorkflowModel({}, {});
    expect(m.kind).toBe("workflow");
  });

  it("stores data", () => {
    const data = { name: "ci" };
    const m = new WorkflowModel(data, {});
    expect(m.data).toEqual(data);
  });

  it("stores meta", () => {
    const meta = { comment: "hello" };
    const m = new WorkflowModel({}, meta);
    expect(m.meta).toEqual(meta);
  });

  it("has correct keyOrder from the subclass", () => {
    const m = new WorkflowModel({}, {});
    expect(m.keyOrder).toEqual(WORKFLOW_KEY_ORDER);
  });

  it("returns a non-frozen object so transforms can mutate data", () => {
    const m = new StepModel({}, {});
    expect(Object.isFrozen(m)).toBe(false);
  });

  it("captures a source location at the call site", () => {
    const m = new StepModel({}, {});
    expect(m.sourceLocation).not.toBeNull();
    expect(m.sourceLocation?.file).toContain("_base.test");
    expect(typeof m.sourceLocation?.line).toBe("number");
  });

  it("is an instance of Model", () => {
    const m = new StepModel({}, {});
    expect(m).toBeInstanceOf(Model);
    expect(m).toBeInstanceOf(StepModel);
  });
});

// ---------------------------------------------------------------------------
// isModel()
// ---------------------------------------------------------------------------
describe("isModel()", () => {
  it("returns true for a model", () => {
    const m = new JobModel({}, {});
    expect(isModel(m)).toBe(true);
  });

  it("returns false for a plain object", () => {
    expect(isModel({ kind: "job", data: {}, meta: {}, keyOrder: [] })).toBe(false);
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
    };
    const [data, meta] = extractMeta(input);
    expect(data).toEqual({ name: "ci" });
    expect(meta).toEqual({
      comment: "block comment",
      eolComment: "eol",
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
