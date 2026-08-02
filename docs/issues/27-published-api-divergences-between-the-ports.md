# Published-API divergences between the two ports

**Status:** open — from round 2. Found by the whole-branch adversarial review (docs-vs-code)

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
