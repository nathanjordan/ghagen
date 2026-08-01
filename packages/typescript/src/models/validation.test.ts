/**
 * Construction-time validation invariants shared by every factory.
 *
 * The TypeScript peer of `packages/python/tests/test_models/test_validation.py`.
 * Both ports promise the same thing: a model validates its input when it is
 * constructed. These tests pin the three ways that promise is kept —
 * unknown input keys are an error, declared value grammars are enforced, and
 * the `Raw` escape hatch is opt-in.
 *
 * The unknown-key cases are written through `as` casts and spreads on purpose:
 * TypeScript's excess-property check fires only on a *fresh object literal* in
 * the argument position, so four of the five ordinary authoring shapes reach
 * the factory with the compiler silent. Those four are exactly what the runtime
 * check exists for.
 */

import { describe, expect, it } from "vitest";
import { buildYamlData, ModelInputError, raw, type ModelSpec, type WithMeta } from "./_base.js";
import { imageSnapshot } from "./image-snapshot.js";
import { job, matrix, strategy } from "./job.js";
import { permissions } from "./permissions.js";
import { step, type StepInput } from "./step.js";
import { workflowCall, workflowDispatch } from "./trigger.js";
import { toData } from "../emitter/yaml-writer.js";

describe("unknown input keys are rejected", () => {
  it("rejects a misspelled field passed through a variable", () => {
    const input = { nmae: "Build", run: "echo hi" } as unknown as WithMeta<StepInput>;
    expect(() => step(input)).toThrow(ModelInputError);
    expect(() => step(input)).toThrow(/nmae/);
  });

  it("rejects a misspelled field arriving via a spread", () => {
    expect(() => step({ run: "echo hi", ...({ nmae: "Build" } as object) })).toThrow(
      ModelInputError,
    );
  });

  it("rejects a misspelled field behind an `as unknown as` cast", () => {
    expect(() => step({ nmae: "Build" } as unknown as WithMeta<StepInput>)).toThrow(
      ModelInputError,
    );
  });

  it("rejects a misspelled field on a `satisfies`-annotated constant", () => {
    const input = { run: "echo hi", nmae: "Build" } satisfies Record<string, unknown>;
    expect(() => step(input as unknown as WithMeta<StepInput>)).toThrow(ModelInputError);
  });

  it("rejects an unknown key on a nested model factory", () => {
    const input = { runsOnn: "ubuntu-latest", steps: [] } as unknown as Parameters<typeof job>[0];
    expect(() => job(input)).toThrow(/runsOnn/);
  });

  it("names extras as the sanctioned channel and the model kind", () => {
    let message = "";
    try {
      step({ nmae: "Build" } as unknown as WithMeta<StepInput>);
    } catch (err) {
      message = (err as Error).message;
    }
    expect(message).toContain("step");
    expect(message).toContain("extras");
  });

  it("carries a discriminated problem payload", () => {
    try {
      step({ nmae: "Build" } as unknown as WithMeta<StepInput>);
      expect.unreachable();
    } catch (err) {
      const e = err as ModelInputError;
      expect(e).toBeInstanceOf(ModelInputError);
      expect(e.name).toBe("ModelInputError");
      expect(e.kind).toBe("step");
      expect(e.problem).toEqual({ reason: "unknownKeys", keys: ["nmae"] });
    }
  });

  it("still accepts extras as the unmodeled-key channel", () => {
    const s = step({ name: "build", extras: { "x-custom": "value" } });
    expect(toData(s)).toEqual({ name: "build", "x-custom": "value" });
  });

  it("still accepts dynamic axes on matrix (declared dynamicKeys)", () => {
    const m = matrix({ "python-version": ["3.11", "3.12"] });
    expect(toData(m)).toEqual({ "python-version": ["3.11", "3.12"] });
  });

  it("rejects the Python spelling of StrategyInput.matrix_", () => {
    const input = { matrix: matrix({ include: [] }) } as unknown as Parameters<typeof strategy>[0];
    expect(() => strategy(input)).toThrow(ModelInputError);
  });
});

describe("declared value grammars are enforced", () => {
  it("rejects a version outside the snapshot grammar", () => {
    expect(() => imageSnapshot({ imageName: "img", version: "1.2.3" })).toThrow(ModelInputError);
  });

  it("carries a pattern problem payload naming the field and the grammar", () => {
    try {
      imageSnapshot({ imageName: "img", version: "latest" });
      expect.unreachable();
    } catch (err) {
      const e = err as ModelInputError;
      expect(e.kind).toBe("imageSnapshot");
      expect(e.problem).toEqual({
        reason: "pattern",
        field: "version",
        value: "latest",
        pattern: String.raw`^\d+(\.\d+|\*)?$`,
      });
    }
  });

  it("skips non-string values, so a Raw value never hits the grammar", () => {
    // Mirrors test_validation.py::TestDeclaredGrammars::
    // test_pattern_skips_a_raw_value — the check is a property of the spec
    // consumption, not of `imageSnapshot()`, whose declared `version` type is
    // `string` in both ports.
    const spec = {
      kind: "imageSnapshot",
      fieldMap: { version: "version" },
      order: [],
      patterns: { version: /^\d+(\.\d+|\*)?$/ },
    } as unknown as ModelSpec;
    expect(buildYamlData(spec, { version: raw("nightly") })).toEqual({
      version: raw("nightly"),
    });
  });
});

describe("Raw is available wherever a union constrains a value", () => {
  it("accepts raw() on a permission scope", () => {
    const p = permissions({ contents: raw("future-level") });
    expect(toData(p)).toEqual({ contents: "future-level" });
  });

  it("accepts raw() on a workflow_dispatch input type", () => {
    const t = workflowDispatch({
      inputs: { mode: { type: raw("future-type") } },
    });
    expect(toData(t)).toEqual({ inputs: { mode: { type: "future-type" } } });
  });

  it("accepts raw() on a workflow_call input type", () => {
    const t = workflowCall({
      inputs: { mode: { type: raw("future-type") } },
    });
    expect(toData(t)).toEqual({ inputs: { mode: { type: "future-type" } } });
  });
});
