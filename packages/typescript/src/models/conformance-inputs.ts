/**
 * Input-type sweep bindings for `schema/conformance-inputs.yml`, plus the
 * counterexample bindings for that file's peer, the `constraints` section of
 * `schema/conformance-gaps.yml`.
 *
 * ## Why this is a plain `src/` module and not part of `conformance.test.ts`
 *
 * Because it is the only place in this port where the claims below are
 * checkable at all. `tsconfig.json` excludes `src/**\/*.test.ts` from
 * `tsc --noEmit` (the `typecheck` gate), and vitest (esbuild, transpile-only)
 * type-checks nothing either — so a `satisfies` written in a `.test.ts` is
 * decorative. Same reasoning as {@link ./conformance-values.ts}, for a
 * strictly stronger reason: that file needed the compiler for one invariant
 * (a pattern-carrying field must admit `Raw<string>`); this file needs it for
 * *every reject vector it declares*.
 *
 * ## The asymmetry with Python, stated plainly
 *
 * Python's half of this sweep executes both directions: Pydantic validates the
 * declared annotation on every construction, so `WorkflowDispatchInput(default=[])`
 * genuinely raises and the shared table's `reject` vectors are real runtime
 * assertions there.
 *
 * TypeScript has no runtime type system. `job({ permissions: 123 as never })`
 * throws nothing — `defineFactory` validates model *metadata* and value
 * *grammars*, never declared input types. So the reject direction is handed to
 * the compiler:
 *
 *   - `accept` is declared `satisfies readonly <FieldType>[]`. Narrow the
 *     field and this stops compiling.
 *   - each `reject` vector is a `satisfies <FieldType>` under an
 *     `@ts-expect-error`. Widen the field far enough to admit it and tsc
 *     reports an *unused* `@ts-expect-error` directive, which is an error.
 *     That is a compiler-executed reject vector — it fails in exactly the
 *     situation Python's `pytest.raises` fails in.
 *
 * `conformance.test.ts` then deep-equals these declared literals against the
 * shared YAML. That comparison is what binds the compiler's judgement back to
 * the shared table: edit a vector in `conformance-inputs.yml` and the Python
 * sweep fails the construction while this port fails the comparison. Both
 * suites go red off one shared byte, which is the whole point of the table.
 */
import type { WorkflowDispatchInputDef, WorkflowCallInputDef } from "./trigger.js";
import { workflowCall, workflowDispatch } from "./trigger.js";
import type { ModelSpec } from "./_base.js";
import { job, JOB_SPEC } from "./job.js";
import type { PermissionsValue } from "./permissions.js";
import { step, STEP_SPEC } from "./step.js";
import { workflow, WORKFLOW_SPEC } from "./workflow.js";
import { WORKFLOW_CALL_INPUT_SPEC, WORKFLOW_DISPATCH_INPUT_SPEC } from "./trigger.js";

/**
 * This port's binding for one `<kind>.<field>` key from
 * `schema/conformance-inputs.yml`. Type-erased on purpose: the compile-time
 * claim is made by the literals passed to {@link defineInputBinding}, and
 * survives erasure because `tsc` has already checked it by the time this shape
 * is produced.
 */
export interface InputBinding {
  readonly spec: ModelSpec;
  /**
   * This port's name for the field. The shared table keys on one spelling for
   * a field the two ports name differently (`continueOnError` here,
   * `continue_on_error` in Python); each port names its own and both assert
   * their spec maps it to the shared `yaml_key`.
   */
  readonly field: string;
  /** Construct the owning model with `value` in the bound field. */
  readonly construct: (value: unknown) => unknown;
  /** Re-declaration of the shared table's `accept`, compile-checked. */
  readonly accept: readonly unknown[];
  /** Re-declaration of the shared table's `reject`, compile-*rejected*. */
  readonly reject: readonly unknown[];
}

/**
 * Capture a typed binding and erase it to {@link InputBinding}.
 *
 * The single `value as A` is the whole cast surface of this file. It is safe
 * in the direction that matters: `accept` is `readonly A[]`, so the sweep only
 * ever feeds `construct` values the compiler has already accepted as `A`.
 */
function defineInputBinding<A>(binding: {
  readonly spec: ModelSpec;
  readonly field: string;
  readonly construct: (value: A) => unknown;
  readonly accept: readonly A[];
  readonly reject: readonly unknown[];
}): InputBinding {
  return {
    spec: binding.spec,
    field: binding.field,
    construct: (value) => binding.construct(value as A),
    accept: binding.accept,
    reject: binding.reject,
  };
}

/** True only when `A` and `B` are the same type, not merely mutually assignable. */
type Equals<A, B> =
  (<T>() => T extends A ? 1 : 2) extends <T>() => T extends B ? 1 : 2 ? true : false;

/** Compiles only for `true`; the vehicle for a compile-time claim. */
type Assert<T extends true> = T;

/**
 * `PermissionsValue` is the declared type of BOTH `permissions` fields.
 *
 * The alias exists because the Snapshot defines `permissions` exactly once and
 * both fields are a bare `$ref` to it (asserted from the shared table by the
 * `ref` rows). This is the other half, and the peer of Python's
 * `test_permissions_value_alias_is_both_permissions_fields`: the alias is not
 * merely exported, it is what the two fields are annotated with — so
 * re-inlining the union at one site, which is exactly how the two ports
 * drifted apart, stops this file compiling.
 */
export type JobPermissionsIsPermissionsValue = Assert<
  Equals<NonNullable<Parameters<typeof job>[0]["permissions"]>, PermissionsValue>
>;
export type WorkflowPermissionsIsPermissionsValue = Assert<
  Equals<NonNullable<Parameters<typeof workflow>[0]["permissions"]>, PermissionsValue>
>;

/** The unconditional union `workflow_dispatch` inputs accept for `default`. */
type DispatchDefault = NonNullable<WorkflowDispatchInputDef["default"]>;
/** The unconditional union `workflow_call` inputs accept for `default`. */
type CallDefault = NonNullable<WorkflowCallInputDef["default"]>;
/** What `continue-on-error` accepts, at either level. */
type ContinueOnError = NonNullable<Parameters<typeof job>[0]["continueOnError"]>;

// snapshot filename -> `<kind>.<field>` -> this port's binding.
// See schema/conformance-inputs.yml for the shared vectors this binds to.
export const INPUT_BINDINGS: Record<string, Record<string, InputBinding>> = {
  "workflow_schema.json": {
    "job.permissions": defineInputBinding<PermissionsValue>({
      spec: JOB_SPEC,
      field: "permissions",
      construct: (permissions) => job({ runsOn: "ubuntu-latest", permissions }),
      accept: [
        "read-all",
        "write-all",
        { contents: "read" },
        { contents: "write", issues: "none" },
      ] satisfies readonly PermissionsValue[],
      reject: [
        // @ts-expect-error — the blanket enum has exactly two members.
        "read-only" satisfies PermissionsValue,
        // @ts-expect-error — `write` is a per-scope level, not a blanket one.
        "write" satisfies PermissionsValue,
        // @ts-expect-error — the empty string is not a blanket keyword.
        "" satisfies PermissionsValue,
        // @ts-expect-error — a permission is a string or a mapping.
        123 satisfies PermissionsValue,
        // @ts-expect-error — a permission is a string or a mapping.
        true satisfies PermissionsValue,
        // @ts-expect-error — never a sequence.
        ["read-all"] satisfies PermissionsValue,
      ],
    }),
    "workflow.permissions": defineInputBinding<PermissionsValue>({
      spec: WORKFLOW_SPEC,
      field: "permissions",
      construct: (permissions) => workflow({ name: "CI", permissions, jobs: {} }),
      accept: [
        "read-all",
        "write-all",
        { contents: "read" },
        { contents: "write", issues: "none" },
      ] satisfies readonly PermissionsValue[],
      reject: [
        // @ts-expect-error — the blanket enum has exactly two members.
        "read-only" satisfies PermissionsValue,
        // @ts-expect-error — `write` is a per-scope level, not a blanket one.
        "write" satisfies PermissionsValue,
        // @ts-expect-error — the empty string is not a blanket keyword.
        "" satisfies PermissionsValue,
        // @ts-expect-error — a permission is a string or a mapping.
        123 satisfies PermissionsValue,
        // @ts-expect-error — a permission is a string or a mapping.
        true satisfies PermissionsValue,
        // @ts-expect-error — never a sequence.
        ["read-all"] satisfies PermissionsValue,
      ],
    }),
    "workflowDispatchInput.default": defineInputBinding<DispatchDefault>({
      spec: WORKFLOW_DISPATCH_INPUT_SPEC,
      field: "default",
      // Constructed WITHOUT `type`: every `if` in the Snapshot's conditional
      // block is guarded by `required: [type]`, so with no `type` present the
      // unconditional union is exactly what applies.
      construct: (value) => workflowDispatch({ inputs: { input: { default: value } } }),
      accept: ["a-string", "", true, false, 3, 3.5] satisfies readonly DispatchDefault[],
      reject: [
        // @ts-expect-error — not a scalar of any admitted type.
        [] satisfies DispatchDefault,
        // @ts-expect-error — not a scalar of any admitted type.
        {} satisfies DispatchDefault,
        // @ts-expect-error — not a scalar of any admitted type.
        ["a", "b"] satisfies DispatchDefault,
      ],
    }),
    "workflowCallInput.default": defineInputBinding<CallDefault>({
      spec: WORKFLOW_CALL_INPUT_SPEC,
      field: "default",
      // `type` is required here, and unlike workflow_dispatch it does not
      // constrain `default` -- the Snapshot types that field directly.
      construct: (value) => workflowCall({ inputs: { input: { type: "string", default: value } } }),
      accept: ["a-string", "", true, false, 3, 3.5] satisfies readonly CallDefault[],
      reject: [
        // @ts-expect-error — not a scalar of any admitted type.
        [] satisfies CallDefault,
        // @ts-expect-error — not a scalar of any admitted type.
        {} satisfies CallDefault,
        // @ts-expect-error — not a scalar of any admitted type.
        ["a", "b"] satisfies CallDefault,
      ],
    }),
    "job.continueOnError": defineInputBinding<ContinueOnError>({
      spec: JOB_SPEC,
      field: "continueOnError",
      construct: (continueOnError) => job({ runsOn: "ubuntu-latest", continueOnError }),
      accept: [
        true,
        false,
        "${{ github.event_name == 'push' }}",
        "",
      ] satisfies readonly ContinueOnError[],
      reject: [
        // @ts-expect-error — boolean or an expression string, never a number.
        123 satisfies ContinueOnError,
        // @ts-expect-error — never a sequence.
        [] satisfies ContinueOnError,
        // @ts-expect-error — never a mapping.
        {} satisfies ContinueOnError,
      ],
    }),
    "step.continueOnError": defineInputBinding<ContinueOnError>({
      spec: STEP_SPEC,
      field: "continueOnError",
      construct: (continueOnError) => step({ run: "echo hi", continueOnError }),
      accept: [
        true,
        false,
        "${{ github.event_name == 'push' }}",
        "",
      ] satisfies readonly ContinueOnError[],
      reject: [
        // @ts-expect-error — boolean or an expression string, never a number.
        123 satisfies ContinueOnError,
        // @ts-expect-error — never a sequence.
        [] satisfies ContinueOnError,
        // @ts-expect-error — never a mapping.
        {} satisfies ContinueOnError,
      ],
    }),
  },
};

/**
 * This port's binding for one row of the `constraints` section of
 * `schema/conformance-gaps.yml`.
 *
 * The row records a cross-field rule the Snapshot imposes and neither port
 * enforces. Python proves the gap is still open by constructing the
 * schema-invalid combination and observing no `ValidationError`. This port
 * does the same at runtime — and adds the claim that is actually meaningful
 * here: {@link counterexample} is a typed literal that *compiles* against the
 * model's input type. TypeScript could enforce this rule at compile time with
 * a discriminated union; if someone ever does, the literal stops compiling and
 * the row must go. That is the same forcing function Python's construction
 * gives, at the moment this port would actually close the gap.
 */
export interface ConstraintBinding {
  /** The schema-invalid input, re-declared as a compiling typed literal. */
  readonly counterexample: unknown;
  /** Construct with the counterexample. Must not throw — the gap is real. */
  readonly construct: () => unknown;
}

// snapshot -> `<kind>.<field>` -> binding. See the `constraints` section of
// schema/conformance-gaps.yml for the rows this binds to.
export const CONSTRAINT_BINDINGS: Record<string, Record<string, ConstraintBinding>> = {
  workflow_schema: {
    "workflowDispatchInput.default": {
      // A string `default` on a `type: "boolean"` input. The Snapshot's
      // `allOf`/`if`/`then` block rejects this; `WorkflowDispatchInputDef`
      // types the two fields independently, so it compiles.
      counterexample: {
        type: "boolean",
        default: "yes",
      } satisfies WorkflowDispatchInputDef,
      construct: () => workflowDispatch({ inputs: { input: { type: "boolean", default: "yes" } } }),
    },
  },
};
