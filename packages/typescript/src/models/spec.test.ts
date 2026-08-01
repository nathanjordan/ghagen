import { describe, it, expect } from "vitest";
import { ALL_SPECS, SPECS_BY_KIND } from "./registry.js";
import { Model, buildModel } from "./_base.js";
import type { ModelSpec } from "./_base.js";
import { toData } from "../emitter/yaml-writer.js";

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

  // The two assertions that used to sit here — "explicit order has no
  // duplicates" and "explicit order is complete (== fieldMap values)" — both
  // compared `order` against `fieldMap` as *sets*. Every explicit spec restated
  // `Object.values(fieldMap)` verbatim, so what they actually pinned was that
  // the copy had not lost or gained an entry; permuting one against the other
  // changed the emitted YAML with the whole suite green. `order`'s payload is
  // gone, so there is no second list to compare. What replaces them guards the
  // one list that remains, as a *sequence*.

  it.each(ALL_SPECS)("$kind: fieldMap values are unique", (spec) => {
    // `buildYamlData` writes into a record keyed by YAML key, so two fields
    // mapping to one key silently drop the earlier one. A set comparison
    // accepted that; this does not.
    const values = Object.values(spec.fieldMap);
    expect(new Set(values).size, `duplicate YAML keys in ${spec.kind} fieldMap`).toBe(
      values.length,
    );
  });

  it.each(ALL_SPECS)("$kind: no fieldMap value is an integer-like key", (spec) => {
    // JS `OrdinaryOwnPropertyKeys` lists array-index keys first, ahead of
    // string keys in creation order, so a decimal-integer YAML key would jump
    // to the front of `data` regardless of where `fieldMap` declares it — and
    // the Python port, whose `dict` has no such rule, would not follow. The
    // constraint is documented on `buildYamlData`; this is where it is checked.
    for (const value of Object.values(spec.fieldMap)) {
      expect(String(Number.parseInt(value, 10)), `${spec.kind}.${value}`).not.toBe(value);
    }
  });

  it.each(ALL_SPECS)("$kind: emitted key sequence equals fieldMap declaration order", (spec) => {
    // The guard the port never had. Built constructively — one fully populated
    // model per spec, with the input keys supplied in **reverse** fieldMap
    // order — so a pass means `buildYamlData` normalised them, not that the
    // input happened to arrive already sorted. The golden fixtures do not
    // back-stop this: most specs never emit enough keys at once for any
    // ordering to be observable, and eight have no fixture coverage at all.
    const expected = Object.values(spec.fieldMap);
    const emitted = Object.keys(toData(populate(spec)) as Record<string, unknown>);
    expect(emitted).toEqual(spec.order === "alphabetical" ? [...expected].sort() : expected);
  });

  it.each(ALL_SPECS)("$kind: every wrap key is a field in the map", (spec) => {
    for (const camelKey of Object.keys(spec.wrap ?? {})) {
      expect(spec.fieldMap).toHaveProperty(camelKey);
    }
  });

  it("only the `on` spec uses alphabetical order", () => {
    const alpha = ALL_SPECS.filter((s) => s.order === "alphabetical").map((s) => s.kind);
    expect(alpha).toEqual(["on"]);
  });
});

/**
 * Build a Model from *spec* with every `fieldMap` field set, supplied in
 * reverse declaration order.
 *
 * The values only have to survive `buildYamlData` and reach `toData` as
 * distinct keys, so they are chosen to make every construction-time rule a
 * pass-through rather than to be realistic:
 *
 * - a wrap-ruled field gets `rule.factory({})`, already a `Model`, which every
 *   {@link WrapRule} mode returns untouched;
 * - every other field gets `1`, a non-string, which `spec.patterns` skips for
 *   the same reason it skips `raw()`.
 *
 * `presentNullWhenEmpty` only rewrites values, never keys, so it does not
 * affect the sequence under test.
 */
function populate(spec: ModelSpec): Model {
  const input: Record<string, unknown> = {};
  for (const camelKey of Object.keys(spec.fieldMap).reverse()) {
    const rule = spec.wrap?.[camelKey];
    input[camelKey] = rule === undefined ? 1 : (rule.factory as (i: unknown) => Model)({});
  }
  return buildModel(spec, input, {});
}
