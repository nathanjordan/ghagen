# Published-API divergences between the two ports

**Status:** closed — all three fixed in both ports, and a fourth divergence found while
fixing them is recorded as a constraint gap. From round 2. Found by the whole-branch
adversarial review (docs-vs-code)

Feature parity between the Python and TypeScript ports is a repo-level mandate, and round 2 bound a
great deal of it — `schema/conformance-scopes.yml`, `schema/conformance-values.yml`,
`schema/tag-grammar.yml`, `fixtures/expected/`, `fixtures/cli-exit-codes.yml`. What none of those
tables bind is the **shape of the published input types**. These three diverge today.

## 1. `PermissionsValue` is documented and does not exist

`docs/src/content/docs/python/api/permissions.md:58,63` publishes:

```
PermissionsValue = Permissions | Literal["read-all", "write-all"] | Raw[str] | dict[str, str]
```

`grep -rn PermissionsValue packages/` returns nothing. The name appears in the API reference and
nowhere in either port's source. A reader importing it gets an `ImportError`.

Decide whether the alias should exist (in which case export it in both ports, since the docs are
generated per-port and TypeScript has no peer either) or whether the docs page should describe the
union inline.

## 2. Job `permissions` accepts a string shorthand in one port only

The two ports disagree about whether `permissions` takes the `"read-all"` / `"write-all"` shorthand
directly, or only the structured form. This is the exact union item 1 documents, so the two findings
share a root cause: the union was written down before it was implemented on both sides.

## 3. Input `default` accepts different types

The workflow-input `default` field's accepted types differ between ports. A config that type-checks
in TypeScript is rejected by Python or vice versa.

## 4. Neither port binds `type` -> `default` (found while fixing 3)

Widening `default` to the union in item 3 raises the question the issue did not ask: the Snapshot
does not type `workflowDispatchInput.default` unconditionally at all. It leaves it untyped in
`properties` and constrains it from a five-branch `allOf` of `if`/`then` clauses keyed on the
sibling `type`. Both ports declare the _unconditional_ union of those branches and neither reads
`type` when validating `default`, so `type: "boolean"` with `default: "yes"` is accepted by both
ports and rejected by GitHub.

This is not implemented. See the Resolution.

## Why the conformance tables did not catch these

`schema/conformance-scopes.yml` binds the _set of scope names_. `conformance-values.yml` binds _value
grammars_ for the fields that declare `patterns`. Neither binds the _accepted type union_ of an input
field — that is the one axis of the model interface with no shared table.

That is the real finding. A `schema/conformance-inputs.yml` (kind → field → accepted type union, with
accept/reject vectors per port) is the peer these three want, and it would close the class rather than
the three instances. It is also the natural home for the reject vectors that
`docs/issues/22`'s grammar-message fix will need.

## Files

- `docs/src/content/docs/python/api/permissions.md:58,63`
- `packages/python/src/ghagen/models/job.py`, `packages/typescript/src/models/job.ts`
- `packages/python/src/ghagen/models/permissions.py`, `packages/typescript/src/models/permissions.ts`
- `schema/conformance-scopes.yml`, `schema/conformance-values.yml` — the pattern a new table follows
- `schema/conformance-inputs.yml` — the table this issue asked for (added)
- `schema/conformance-gaps.yml` — its new `constraints` section holds item 4
- `packages/typescript/src/models/conformance-inputs.ts` — the TypeScript bindings, compile-checked

## Resolution

All three divergences fixed, both ports; the class closed with the shared table the issue named;
item 4 recorded rather than built.

**1. `PermissionsValue` now exists and is exported from both ports.** The docs were the only place
the name lived, so the fix is the one the issue's first branch describes: make the published name
real. `PermissionsValue = OrRaw[Permissions | Literal["read-all", "write-all"] | Raw[str]]` in
`packages/python/src/ghagen/models/permissions.py`, exported from `ghagen`; the peer union in
`packages/typescript/src/models/permissions.ts`, exported from `src/index.ts`. The published
definition was wrong in one member -- it listed `dict[str, str]`, which neither port accepts -- and
wrong about scope: it said "the `Workflow.permissions` field," when the Snapshot gives the
workflow-level and job-level fields one `$ref` to the same `definitions.permissions` node. One
upstream node, one alias, both fields. That `$ref` is now itself asserted, by the `ref` key on both
`permissions` rows of the new table: if upstream ever inlines or splits the node, one alias stops
being the right shape and both suites say so.

**2. Python's `Job.permissions` accepts the shorthand, and emits it as a scalar.** TypeScript was
right; `packages/python/src/ghagen/models/job.py` now carries `PermissionsValue | None`, the same
type as `Workflow.permissions`. A type widening alone would have been a half-fix -- the emitter
walks models generically, so a shorthand that survives construction can still land as a one-key
mapping or a quoted scalar with no type error to show for it -- so both ports assert the bytes:
`test_blanket_permissions_emit_as_bare_scalars` in
`packages/python/tests/test_integration/test_full_workflow.py` and its peer in
`packages/typescript/src/integration/schema-validation.test.ts` pin `\npermissions: read-all\n` at
column 0 and `\n    permissions: write-all\n` under `jobs.test`, and assert the mapping form and
both quoted forms are absent.

**3. Both `default` fields widened, in both ports, at both sites.** `str | bool | int | float` in
`packages/python/src/ghagen/models/trigger.py`, for `WorkflowDispatchInput` and `WorkflowCallInput`
alike; TypeScript already had `string | boolean | number` at both. `int` is spelled alongside
`float` deliberately: pydantic's smart union would otherwise coerce `3` to `3.0`, which emits as
`3.0` -- a different document that the schema still accepts, so only a byte-level assertion catches
it. Both ports now have one.

**4. Recorded, not implemented.** A cross-field rule has no footprint a property gap has: both
fields are present and both are typed, so absence-from-the-spec cannot prove the limit still
exists. `schema/conformance-gaps.yml` therefore gained a reserved top-level `constraints` key with
its own row shape -- `requires` (upstream paths that must still hold), `requires_prose`,
`unenforced`, and a `counterexample` that both ports construct and watch succeed. That construction
is the proof: the day either port enforces the conditional, the counterexample throws, the row's
test fails, and the row must go. Binding the rule for real would mean a validator that reads a
sibling field, which is new capability in both `ModelSpec` and the emitter's construction-time
checks -- `patterns`, the one existing per-field grammar hook, sees a single value with no access
to the rest of the model. One rule does not justify the mechanism; an unrecorded one is how a known
limit becomes a bug report.

**The class: `schema/conformance-inputs.yml`.** Six rows (`job.permissions`,
`workflow.permissions`, `workflowDispatchInput.default`, `workflowCallInput.default`,
`job.continueOnError`, `step.continueOnError`), each binding a `yaml_key`, the `type_paths` into
the Snapshot whose union the declared type must equal, that union, an optional `ref`, and
accept/reject vectors. The type-union check is the peer of the value table's pattern-identity
check: an upstream narrowing, or a typo in `types`, fails both suites. `yaml_key` is what lets one
shared row cover a field the two ports name differently (`continueOnError` / `continue_on_error`):
each port names its own field in its own binding and both assert the field lands on the same
emitted key.

The reject direction is asymmetric, and the table's header says so rather than hiding it. Python
executes reject vectors at runtime under `pytest.raises(ValidationError)`. TypeScript has no
runtime type validation to execute, so its reject vectors are executed by the _compiler_: each
literal sits under an `@ts-expect-error` in `packages/typescript/src/models/conformance-inputs.ts`,
so widening a field to admit one turns the directive unused and `tsc` reports TS2578. That file is
a plain `src/` module rather than a `.test.ts` for the reason issue 09 documents: `tsconfig.json`
excludes `src/**/*.test.ts` from `tsc --noEmit`, and vitest's esbuild transform type-checks nothing,
so a compile-time claim written in a test file is not checked by any gate. The alias-identity
assertions (`Equals<Parameters<typeof job>[0]["permissions"], PermissionsValue>`) live there for
the same reason, and were verified to fail (TS2344) when `job.ts` widens its field.

Corruption proof, as the repo requires: changing one accept vector in
`schema/conformance-inputs.yml` fails both suites -- Python at construction, TypeScript at the
comparison between the compiler-checked literals and the shared file.

**Docs.** `docs/src/content/docs/python/api/permissions.md` now documents the alias that exists
(the `dict[str, str]` member removed, the `CommentedMap`/`OrRaw` arm added, and "Workflow-level
shorthand" retitled since it is not workflow-level any more); `job.md`, `workflow.md` and
`triggers.md` carry the new types, and `triggers.md` gained a caution stating item 4's limit where
a reader of `default` will hit it. TypeScript's API reference is not hand-written -- typedoc
generates it from the `_docs-api-*.ts` entry points -- so its peer edit is one line:
`_docs-api-permissions.ts` now re-exports the `PermissionsValue` type, whose TSDoc carries the same
definition, and `/typescript/api/permissions` publishes it. That is what the issue meant by
"TypeScript has no peer either."
