# Explicit-null trigger fields diverge across ports

**Status:** closed — one semantic in both ports (`null`/`None` means _unset_), and the
present-null rule widened from one event to every event. Both changes proven load-bearing by
reverting them to red

`On(create=None)` (Python) is dropped by `exclude_none` → `on: {}`; TS `on({ create: null })`
keeps the key and a plain-null map value renders in the ugly `? create` explicit-key form. No
fixture exercises it. Decide one semantic (probably: drop in both), implement via spec rule.

## Resolution

Two decisions, both implemented in both ports, both proven by reverting them and watching a test go
red.

### What was measured first

The divergence the issue names is real, and it is worse than "ugly": before this change the two
ports emitted **semantically different workflows** from the same input. Measured on `f9eb712`,
`header=None`:

| construction                                      | Python before        | TypeScript before            | both after |
| ------------------------------------------------- | -------------------- | ---------------------------- | ---------- |
| `On(create=None)` / `on({ create: null })`        | `on: {}`             | `on:\n  ? create`            | `on: {}`   |
| `On(workflow_dispatch=None)`                      | `on: {}`             | `on:\n  ? workflow_dispatch` | `on: {}`   |
| `On(create={})` / `on({ create: {} })`            | `create: {}`         | `create: {}`                 | `create:`  |
| `On(push=PushTrigger())` / `on({ push: {} })`     | `push: {}`           | `push: {}`                   | `push:`    |
| `On(workflow_dispatch=WorkflowDispatchTrigger())` | `workflow_dispatch:` | `workflow_dispatch:`         | unchanged  |

`on: {}` fires on nothing. `on:\n  ? create` fires on `create`. That is not a formatting
difference between the ports; it is two different workflows from one config, which is the parity
mandate broken at its most load-bearing point.

### Decision 1 — `null`/`None` means _unset_, in both ports

TypeScript changed, Python did not. `buildYamlData` (`packages/typescript/src/models/_base.ts`) now
drops a `null` field exactly as it drops an `undefined` one, the peer of Python's `exclude_none` in
`emitter/nodes.py:collect_fields`. One word, one meaning, for every field of every model in both
ports — not a rule about `on:`.

The check sits on the **raw** value, before the `Commented` peel, for the same reason Python's sits
on the raw wrapper: `raw(null)` and `withComment(null, ...)` are objects, not `null`, so a caller
who deliberately asks to emit a null still gets one. The `null` branch of `applyWrapRule`'s
`dispatch` mode became dead code and was deleted rather than left as a second, unreachable answer
to the same question.

This is a **breaking change** to the TypeScript API, taken freely per the pre-1.0 rule: a caller
using `on({ create: null })` to mean "fire on `create`" must now write `on({ create: {} })`. The
eleven `Pass \`null\` for an event with no configuration`TSDoc lines that taught the old spelling
now say`{}`, and `OnInput`'s interface doc states the rule outright.

**Red proof.** Reverting only `if (value === undefined || value === null)` back to
`if (value === undefined)` in `_base.ts`: vitest exits 1 with
`× treats a null event as unset, not as a bare key`, `Tests 1 failed | 1071 passed (1072)`.
Restored.

### Decision 2 — every event key present-nulls an empty map

`present_null_when_empty` / `presentNullWhenEmpty` used to name `workflow_dispatch` alone. That was
never a decision about `workflow_dispatch`; it was the one key somebody needed. It now covers every
key in `ON_SPEC`.

**How "every filterless event" is expressed: derived, not listed, and widened past "filterless" on
purpose.** The set is `frozenset(_ON_YAML_KEYS.values())` in Python and
`Object.values(ON_FIELD_MAP)` in TypeScript — the same map the spec's `yaml_keys` / `fieldMap`
already reads. Two reasons:

1. A derived set cannot fall out of date. Adding an event to `_ON_YAML_KEYS` adds it here in the
   same edit, and there is no second list for a guard test to compare against the first. The issue
   allowed an explicit list plus a guard test; deriving is strictly better, because the failure mode
   the guard test exists to catch cannot occur. (`schema/key-order.yml` already binds this key set
   across the two ports, so the derivation inherits that cross-port binding for free.)
2. An empty map is never the right emission for an `on:` key. GitHub's documented spelling for
   "this event, no filters" is the bare key — `create:` for an event that takes no filters at all,
   and equally `push:` or `workflow_call:` for one whose filters were simply left empty.

Reason 2 is a **deliberate widening beyond strictly-filterless events**, and it is observable:
`On(push=PushTrigger())`, `On(pull_request=PRTrigger())`, `On(pull_request_target=PRTrigger())` and
`On(workflow_call=WorkflowCallTrigger())` now emit a bare key where they emitted `{}`. Both forms
are accepted by GitHub and by the canonical Snapshot; the bare key is the documented one.
`schedule` is unaffected — a list is not an empty map, in either port's `resolves_to_empty_map` /
`isEmptyMapValue`.

**Red proof.** Reverting both ports to the one-element allowlist: Python `6 failed, 1005 passed`
(`test_body_shapes`, `test_every_on_event_present_nulls_an_empty_map`, and the four
`test_on_event_is_accepted[branch_protection_rule|discussion|discussion_comment|gollum]` cases that
pass `{}`); TypeScript `2 failed | 1070 passed` (`present-nulls an empty map on every event key`,
`body_shapes.yml`). Restored.

### Coverage

The issue's "no fixture exercises it" is closed twice over. `fixtures/expected/body_shapes.yml`
(see `docs/issues/02`) carries both a bare `workflow_dispatch:` and a bare `create:` as shared
bytes; on top of that each port has a loop asserting the bare form for **every** key in
`ON_SPEC.yaml_keys` / `ON_SPEC.fieldMap`, so a new event added to the map is covered the day it is
added, and a null-field test asserting `On(create=None)` emits `on: {}` with no `create` anywhere.

### What was deliberately NOT done

**A surviving `null` still renders differently in the two ports.** Decision 1 is a rule about
_fields_, applied at construction. A `null` nested in plain data, in a list, or in `extras` never
reaches that rule, and the two emitters disagree about it — `a:` vs `? a`, `- ` vs `- null`,
`foo:` vs `foo: null`. That is a defect in the emitters' scalar writers, not in the spec, it wants
its own fixture and its own corruption proof, and folding it into this pass would have muddied the
`body_shapes.yml` proof. Filed as `docs/issues/36`.

**Python's published API was not widened.** The new fixture test imports `Defaults`, `DefaultsRun`,
`WorkflowCallInput`, `WorkflowCallOutput` and `WorkflowCallSecret` from `ghagen.models.*` because
the `ghagen` package does not export them, while TypeScript exports `workflowCall` with all three
sub-def types. That asymmetry is real and is the same family as `docs/issues/27`; it is not what
this issue asked about, and the test follows the existing `Concurrency` precedent rather than
changing the published surface on the way past.

### Files

- `packages/typescript/src/models/_base.ts` — `buildYamlData`, the Decision 1 change
- `packages/typescript/src/models/trigger.ts` — `ON_FIELD_MAP` extracted, `ON_SPEC` derives from it
- `packages/python/src/ghagen/models/trigger.py` — `_ON_YAML_KEYS`, the peer derivation
- `packages/python/src/ghagen/models/spec.py`, `packages/typescript/src/models/spec.ts` — both
  `present_null_when_empty` docs now state that a null field never reaches the rule
- `fixtures/expected/body_shapes.yml` — the shared bytes
- `docs/src/content/docs/python/api/triggers.md` — "`{}` is the event, `None` is no event"
