/**
 * Value-grammar sweep bindings for `schema/conformance-values.yml`.
 *
 * Pulled out of `conformance.test.ts` on purpose: `tsconfig.json` excludes
 * `src/**\/*.test.ts` from `tsc --noEmit` (the `typecheck` gate), and vitest
 * itself (esbuild, transpile-only) never type-checks anything either. Python's
 * half of the raw-hatch invariant ("a field carrying a spec pattern must admit
 * Raw[str]") is enforced at *runtime* — Pydantic validates a model's declared
 * annotation on every construction, so a narrowed field genuinely raises.
 * TypeScript has no such runtime type system: an object branded `Raw<string>`
 * sails straight through a plain-`string`-typed field with zero runtime
 * signal. The only place "this field's input type admits `Raw<string>`" is a
 * checkable fact in this port is the compiler. So `construct` below has to
 * live in a normal `src/` module, where `tsc --noEmit` actually visits it, or
 * the invariant is decorative.
 *
 * `conformance.test.ts` imports {@link VALUE_BINDINGS} and, for the raw-hatch
 * check, calls `construct` with a `raw(...)`-wrapped value — so the binding is
 * both compile-time checked (this file) and runtime executed (the test),
 * which is stronger than either alone and is what makes the invariant
 * load-bearing in both suites for this port.
 */
import { withComment, type ModelSpec, type Raw } from "./_base.js";
import { imageSnapshot } from "./image-snapshot.js";
import { SPECS_BY_KIND } from "./registry.js";

/**
 * This port's binding for one `<kind>.<field>` key from
 * `schema/conformance-values.yml`: the field's spec plus two constructors.
 */
export interface ValueBinding {
  readonly spec: ModelSpec;
  /**
   * Construct the model with `value` in the bound field. Throws on reject.
   * Also called with a `raw(...)`-wrapped value by the raw-hatch check in
   * `conformance.test.ts` — the parameter type admits both on purpose, so a
   * future field whose input type narrows away `Raw<string>` fails to
   * type-check here rather than only being discoverable by a caller acting on
   * the grammar-violation message.
   */
  readonly construct: (value: string | Raw<string>) => unknown;
  /** Construct with `withComment(value, …)` in the bound field. */
  readonly constructCommented: (value: string) => unknown;
}

// snapshot filename -> `<kind>.<field>` -> this port's spec + constructors.
// See schema/conformance-values.yml for the shared vectors this binds to.
export const VALUE_BINDINGS: Record<string, Record<string, ValueBinding>> = {
  "workflow_schema.json": {
    "imageSnapshot.version": {
      spec: SPECS_BY_KIND.imageSnapshot,
      construct: (version) => imageSnapshot({ imageName: "img", version }),
      constructCommented: (version) =>
        imageSnapshot({ imageName: "img", version: withComment(version, "note") }),
    },
  },
};
