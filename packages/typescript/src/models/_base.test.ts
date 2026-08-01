import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, it, expect } from "vitest";
import {
  raw,
  isRaw,
  isModel,
  isCommented,
  withComment,
  extractMeta,
  buildYamlData,
  defineFactory,
  Model,
  ModelInputError,
} from "./_base.js";
import type { ModelSpec } from "./_base.js";
import { WORKFLOW_SPEC } from "./workflow.js";
import { STEP_SPEC } from "./step.js";
import { JOB_SPEC, defaults } from "./job.js";
import type { DefaultsRunInput } from "./job.js";

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
    const m = new Model(WORKFLOW_SPEC, {}, {});
    expect(m.kind).toBe("workflow");
  });

  it("stores data", () => {
    const data = { name: "ci" };
    const m = new Model(WORKFLOW_SPEC, data, {});
    expect(m.data).toEqual(data);
  });

  it("stores meta", () => {
    const meta = { comment: "hello" };
    const m = new Model(WORKFLOW_SPEC, {}, meta);
    expect(m.meta).toEqual(meta);
  });

  it("carries its spec", () => {
    const m = new Model(WORKFLOW_SPEC, {}, {});
    expect(m.spec).toBe(WORKFLOW_SPEC);
  });

  it("returns a non-frozen object so transforms can mutate data", () => {
    const m = new Model(STEP_SPEC, {}, {});
    expect(Object.isFrozen(m)).toBe(false);
  });

  it("captures a source location at the call site", () => {
    const m = new Model(STEP_SPEC, {}, {});
    expect(m.sourceLocation).not.toBeNull();
    expect(m.sourceLocation?.file).toContain("_base.test");
    expect(typeof m.sourceLocation?.line).toBe("number");
  });

  it("is an instance of Model", () => {
    const m = new Model(STEP_SPEC, {}, {});
    expect(m).toBeInstanceOf(Model);
  });
});

// ---------------------------------------------------------------------------
// isModel()
// ---------------------------------------------------------------------------
describe("isModel()", () => {
  it("returns true for a model", () => {
    const m = new Model(JOB_SPEC, {}, {});
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
// buildYamlData() — field mapping + wrap application
// ---------------------------------------------------------------------------
describe("buildYamlData()", () => {
  it("maps camelCase keys to YAML keys via the spec fieldMap", () => {
    const spec = {
      kind: "job",
      fieldMap: { runsOn: "runs-on", timeoutMinutes: "timeout-minutes" },
    } as unknown as ModelSpec;
    const data = { runsOn: "ubuntu-latest", timeoutMinutes: 10 };
    expect(buildYamlData(spec, data)).toEqual({
      "runs-on": "ubuntu-latest",
      "timeout-minutes": 10,
    });
  });

  it("skips undefined values", () => {
    const spec = {
      kind: "job",
      fieldMap: { runsOn: "runs-on", timeoutMinutes: "timeout-minutes" },
    } as unknown as ModelSpec;
    const data = { runsOn: "ubuntu-latest", timeoutMinutes: undefined };
    expect(buildYamlData(spec, data)).toEqual({ "runs-on": "ubuntu-latest" });
  });

  it("rejects keys not in the field map", () => {
    // Was "skips ... keys not in the field map": the drop was silent, so a
    // misspelled input key produced a model missing that YAML key with no
    // signal. `meta.extras` is the sanctioned channel for unmodeled keys.
    const spec = {
      kind: "job",
      fieldMap: { runsOn: "runs-on", timeoutMinutes: "timeout-minutes" },
    } as unknown as ModelSpec;
    const data = { runsOn: "ubuntu-latest", extra: "ignored" };
    expect(() => buildYamlData(spec, data)).toThrow(ModelInputError);
    expect(() => buildYamlData(spec, data)).toThrow(/extra/);
  });

  it("passes unknown keys through when the spec declares dynamicKeys", () => {
    const spec = {
      kind: "matrix",
      fieldMap: { include: "include" },
      dynamicKeys: true,
    } as unknown as ModelSpec;
    expect(buildYamlData(spec, { "node-version": [20, 22] })).toEqual({
      "node-version": [20, 22],
    });
  });

  it("rejects a string value outside the spec's declared grammar", () => {
    const spec = {
      kind: "imageSnapshot",
      fieldMap: { version: "version" },
      patterns: { version: /^\d+$/ },
    } as unknown as ModelSpec;
    expect(() => buildYamlData(spec, { version: "v1" })).toThrow(ModelInputError);
    expect(buildYamlData(spec, { version: "12" })).toEqual({ version: "12" });
  });

  it("peels and re-applies a Commented wrapper around a wrapped field", () => {
    const spec = {
      kind: "job",
      fieldMap: { env: "env" },
    } as unknown as ModelSpec;
    const data = { env: withComment({ CI: "true" }, "environment") };
    const out = buildYamlData(spec, data);
    expect(isCommented(out["env"])).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// defineFactory()
// ---------------------------------------------------------------------------

describe("defineFactory()", () => {
  interface DemoInput {
    runsOn?: string;
    timeoutMinutes?: number;
  }

  const DEMO_SPEC = {
    kind: "job",
    fieldMap: { runsOn: "runs-on", timeoutMinutes: "timeout-minutes" },
  } as unknown as ModelSpec;

  it("splits meta off the input and maps the rest through the spec fieldMap", () => {
    const demo = defineFactory<Model, DemoInput>(DEMO_SPEC);
    const model = demo({ runsOn: "ubuntu-latest", timeoutMinutes: 10, comment: "hi" });
    expect(model.data).toEqual({ "runs-on": "ubuntu-latest", "timeout-minutes": 10 });
    expect(model.meta.comment).toBe("hi");
  });

  it("takes the model kind from the passed spec", () => {
    const demo = defineFactory<Model, DemoInput>(DEMO_SPEC);
    expect(demo({ runsOn: "ubuntu-latest" }).kind).toBe("job");
    expect(demo({ runsOn: "ubuntu-latest" })).toBeInstanceOf(Model);
  });

  it("applies the spec's wrap rules", () => {
    const inner = defineFactory<Model, DemoInput>(DEMO_SPEC);
    const outerSpec = {
      kind: "workflow",
      fieldMap: { nested: "nested" },
      wrap: { nested: { mode: "model", factory: inner } },
    } as unknown as ModelSpec;
    const outer = defineFactory<Model, { nested?: DemoInput }>(outerSpec);
    const model = outer({ nested: { runsOn: "ubuntu-latest" } });
    expect(isModel(model.data["nested"])).toBe(true);
  });

  it("honours dynamicKeys", () => {
    const dynSpec = {
      kind: "matrix",
      fieldMap: { include: "include" },
      dynamicKeys: true,
    } as unknown as ModelSpec;
    const dyn = defineFactory<Model, Record<string, unknown>>(dynSpec);
    expect(dyn({ "node-version": [20, 22] }).data).toEqual({ "node-version": [20, 22] });
  });

  // The two 09 behaviours every collapsed factory must keep. `defineFactory`
  // wraps nothing in try/catch, so both propagate with the caller's frame.
  it("propagates ModelInputError for an unknown input key", () => {
    const demo = defineFactory<Model, DemoInput>(DEMO_SPEC);
    expect(() => demo({ nope: 1 } as unknown as DemoInput)).toThrow(ModelInputError);
    expect(() => demo({ nope: 1 } as unknown as DemoInput)).toThrow(/nope/);
  });

  it("propagates ModelInputError for a value outside the spec's declared grammar", () => {
    const patSpec = {
      kind: "imageSnapshot",
      fieldMap: { version: "version" },
      patterns: { version: /^\d+$/ },
    } as unknown as ModelSpec;
    const snap = defineFactory<Model, { version?: string }>(patSpec);
    expect(() => snap({ version: "v1" })).toThrow(ModelInputError);
    expect(snap({ version: "12" }).data).toEqual({ version: "12" });
  });

  // `captureSourceLocation` skips internal frames by predicate, not by a fixed
  // count, so the extra closure frame `defineFactory` introduces must stay
  // invisible. A regression here silently degrades every PinTransform
  // diagnostic, so pin it rather than reason about it.
  it("keeps sourceLocation pointing at the caller, not at the closure", () => {
    const demo = defineFactory<Model, DemoInput>(DEMO_SPEC);
    const model = demo({ runsOn: "ubuntu-latest" });
    const here = fileURLToPath(import.meta.url);
    expect(model.sourceLocation).not.toBeNull();
    expect(model.sourceLocation?.file).toBe(here);
  });
});

// ---------------------------------------------------------------------------
// defaultsRun meta promotion
// ---------------------------------------------------------------------------

// The sweep's ONLY behavioural change. `defaultsRun` was the one factory body
// that skipped `extractMeta` and hard-coded `{}` as meta, so a meta key
// reaching the `run` shorthand was passed to `buildYamlData` as a *data* key
// -- which post-09 makes it a hard ModelInputError. Routing it through
// `defineFactory` promotes the key to meta like every other factory.
describe("defaults({ run }) meta promotion", () => {
  it("promotes a meta key on the run shorthand instead of rejecting it", () => {
    const model = defaults({
      run: { shell: "bash", comment: "default shell" } as DefaultsRunInput,
    });
    const runModel = model.data["run"];
    expect(isModel(runModel)).toBe(true);
    expect((runModel as Model).data).toEqual({ shell: "bash" });
    expect((runModel as Model).meta.comment).toBe("default shell");
  });
});

// ---------------------------------------------------------------------------
// `@function` tag guard
// ---------------------------------------------------------------------------

// TypeDoc reflects a function-typed `const` as a Variable unless the doc block
// carries `@function`. Without the tag every collapsed factory's page moves
// from `functions/` to `variables/`, breaking published deep links -- and
// nothing else in CI notices: tsc, oxlint and the docs build are all silent.
// The identical failure mode (a doc block that does not attach) is already
// live in six factories, so the sweep brings its own detector.
describe("exported defineFactory bindings carry @function", () => {
  const MODULES = [
    "action.ts",
    "container.ts",
    "image-snapshot.ts",
    "job.ts",
    "permissions.ts",
    "step.ts",
    "trigger.ts",
    "workflow.ts",
  ];
  const dir = fileURLToPath(new URL(".", import.meta.url));

  it.each(MODULES)("%s", (name) => {
    const source = readFileSync(`${dir}${name}`, "utf8");
    const bindings = [...source.matchAll(/^export const (\w+) = defineFactory</gm)];
    expect(bindings.length).toBeGreaterThan(0);
    for (const match of bindings) {
      const preceding = source.slice(0, match.index);
      const block = preceding.slice(preceding.lastIndexOf("/**"));
      expect(block, `${name}: ${match[1]} is missing @function`).toContain("@function");
    }
  });
});
