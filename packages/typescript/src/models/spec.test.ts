import { describe, it, expect } from "vitest";
import { ALL_SPECS, SPECS_BY_KIND } from "./registry.js";

describe("ModelSpec self-consistency", () => {
  // "every ModelKind has exactly one spec" is not a test any more: it is
  // `satisfies Record<ModelKind, ModelSpec>` in registry.ts, checked by
  // `tsc --noEmit -p tsconfig.json`. The two hand-maintained lists this file
  // used to carry both omitted `imageSnapshot`, so the assertion that replaced
  // it compared 26 against 26 and never consulted the union.
  it("every registry entry's kind equals its key", () => {
    // The one invariant `satisfies Record<ModelKind, ModelSpec>` cannot
    // express: binding `imageSnapshot: STEP_SPEC` compiles clean.
    for (const [key, spec] of Object.entries(SPECS_BY_KIND)) {
      expect(spec.kind, `registry key ${key} is bound to a ${spec.kind} spec`).toBe(key);
    }
  });

  it.each(ALL_SPECS)("$kind: explicit order has no duplicates", (spec) => {
    if (spec.order.kind !== "explicit") {
      return;
    }
    expect(new Set(spec.order.keys).size).toBe(spec.order.keys.length);
  });

  it.each(ALL_SPECS)("$kind: explicit order is complete (== fieldMap values)", (spec) => {
    if (spec.order.kind !== "explicit") {
      return; // alphabetical-emission opt-in (the `on:` section)
    }
    const emitted = new Set(Object.values(spec.fieldMap));
    expect(new Set(spec.order.keys)).toEqual(emitted);
  });

  it.each(ALL_SPECS)("$kind: every wrap key is a field in the map", (spec) => {
    for (const camelKey of Object.keys(spec.wrap ?? {})) {
      expect(spec.fieldMap).toHaveProperty(camelKey);
    }
  });

  it("only the `on` spec uses alphabetical order", () => {
    const alpha = ALL_SPECS.filter((s) => s.order.kind === "alphabetical").map((s) => s.kind);
    expect(alpha).toEqual(["on"]);
  });
});
