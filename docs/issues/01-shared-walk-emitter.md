# Shared-walk emitter: to_data as a projection of one recursion

**Status:** closed — the collection stage is shared in both ports and the one-document cross-check
is replaced by a sweep over every bound fixture. The premise was half true: Python already shared
its collection stage; TypeScript did not. The remaining duplication (value-rendering dispatch) is
deliberately deferred and named below

`to_data`/`toData` shipped as the proposal's sanctioned two-walk alternative: a second recursion
beside the YAML walk. The round-1 review found the model suite now rides the copy, not the walk
that writes files; the full-tree cross-check test (added post-review) is the mitigation. Real fix:
one shared emission walk with a swappable backend (YAML nodes vs plain data), per proposal 02's
recommended design. Both ports.

## Resolution

**"Both ports" was measured, and it was true of TypeScript only.** Python's
`packages/python/src/ghagen/emitter/data.py` already imported `emit_entries` from
`emitter/nodes.py`: `_model_to_data` and `_model_to_map` consumed one resolver, so membership
(`exclude_none`/`exclude_unset`), YAML-key mapping, canonical ordering, the extras merge, the Step
`run` dedent, comment harvesting and the `present_null_when_empty` decision were each already
resolved once, upstream of either rendering. TypeScript's `modelToData`
(`packages/typescript/src/emitter/yaml-writer.ts`) and `modelToYamlMap` each independently called
`orderedEntries`, each built their own `new Set(model.spec.presentNullWhenEmpty ?? [])`, each
re-derived `model.kind === "step"` and re-applied the `run` dedent, and each re-decided present-null
— `modelToYamlMap` inline and `modelToData` through a separate `presentNullComments` helper that
existed only because the second walk needed the comment-folding rule restated. Six decisions
duplicated, in two textually parallel copies of the same loop. That is the divergence surface the
issue describes, and it was one port's.

**TypeScript now has the `emitEntries` peer.** Python's design ported across rather than reinvented:
an `Entry` (`key`, `value`, `comment`, `eolComment`, `presentNull`) and one `emitEntries(model,
autoDedent)` that composes `orderedEntries` with the dedent, the comment harvest and the present-null
verdict — including the fold of a discarded sub-model's own comment onto the entry. Both
`modelToYamlMap` and `modelToData` are now loops over `emitEntries` that differ only in what they
_render_: a `Pair` with a `Scalar` key versus a `Record` slot; `nullScalar()` versus `null`;
`attachFieldComment` versus a `CommentNode`. Neither re-derives anything the entry already carries.
`presentNullComments` is deleted — its rationale moved into `emitEntries`' doc comment, where it now
governs both renderings instead of one.

**`postProcess` stayed where it was, deliberately.** It operates on the backend node, so it lives in
`modelToYamlMap` after the entry loop and does not move into the shared stage. `toData` does not run
it and did not gain it; that documented asymmetry is unchanged, and the sweep below subtracts it
explicitly rather than being written around it.

**No byte moved.** `fixtures/expected/` is unchanged (`git diff -- fixtures/` is empty, verified
against a pre-change checksum baseline). All 29 `.yml` fixtures compare identically in both ports,
and the docs build — which generates every guide's YAML from a live emitter run and pins it to the
same `docs_*.yml` files — is green. `toData`'s public output is unchanged: the same `Record`, the
same `CommentNode` placement.

**The one-document cross-check is now a sweep over every bound fixture, in both ports.**
`test_deep_structure_matches_emitted_yaml` (Python) and its TypeScript peer were each one
hand-built document — an existence proof over the shapes their author happened to remember. Both
are **kept**, because they deliberately pack shapes no fixture contains, and both now sit beside a
sweep that asserts `parse(to_yaml(doc)) == to_data(doc)` for every fixture document. Comments are
off (a YAML parse drops them) and `auto_dedent` is at its default, which is `to_yaml`'s.

**The binding is the existing one, extracted — not a parallel registry.** The models were written
inline inside the snapshot tests, so the sweep could only have reached them by copying them. They
were instead lifted into one module per port —
`packages/python/tests/test_integration/fixture_models.py` and
`packages/typescript/src/integration/fixture-models.ts` — which the byte oracle
(`test_snapshots.py` / `snapshots.test.ts`), the docs pin (`test_docs_snippets.py`) and the walk
sweep all read. There is one list, so the sweep runs over exactly the documents the oracle covers
and cannot silently cover less. `build` is a factory rather than a value so no two readers share a
model; `header` is stated explicitly per entry (no fixture wants ghagen's default header);
`post_process_root_keys` declares the keys a document's `post_process` adds, and the sweep asserts
each is present in the parsed YAML before deleting it — so the subtraction cannot hide a real
difference.

**What is swept, and what is not.** `fixtures/expected/` holds 29 `.yml` files. Three
(`lockfile_golden.yml`, `lockfile_key_quoting.yml`, `lockfile_space_separator_rejected.yml`) are not
emitter documents at all — the pin lockfile serializer writes them, no model produces them.
`init_scaffold.yml` has no static source model: it is whatever the config `ghagen init` scaffolds
emits, so it is swept where that model exists, in `test_init_scaffold.py` /
`init-scaffold.test.ts`, alongside the byte assertion already there. That leaves 25 documents
swept from the registry in Python and 17 in TypeScript. The eight `docs_*.yml` are the difference:
their TypeScript source models live in `docs/src/snippets/emitted.ts`, a Vite module in the `docs/`
package that uses `?raw` imports and is not loadable from the TypeScript suite, so TypeScript lists
them in `UNBOUND_DOC_FIXTURES` with that reason while Python sweeps them. Nothing is dropped
silently: both ports carry an `accounts for every .yml fixture` test that reads the directory and
fails on any file that is neither swept, nor a declared non-document, nor unbound-with-a-reason. A
new fixture lands in none of the three and fails there.

**Both halves were proved load-bearing, by mutation.**

_The sweep catches a divergence between the two walks._ In each port, `toData` was made to disagree
with the YAML walk on one decision the shared stage owns — rendering a present-null entry as `{}`
instead of `null`, leaving `emitEntries` and the YAML rendering untouched. Python: **2 failed, 24
passed** in `test_to_data_sweep.py` (`comments.yml`, `body_shapes.yml`). TypeScript: **2 failed, 16
passed** in `to-data-sweep.test.ts`, the same two documents. Reverted.

Measured honestly, the retained hand-built document catches this particular mutation too — it
contains both present-null spellings, which is why it was worth keeping. It was also checked
against a narrower mutation (`present_null` honoured only when the discarded value is a
`GhagenModel`, so a bare `create: {}` is not nulled): that fails the hand-built document _and_
`body_shapes.yml`, and no other fixture has the shape to notice. The sweep's claim is therefore
breadth, not that the old test was blind — one curated document is one author's memory of the
shapes that matter, and the fixtures are the shapes the ports actually agreed to emit. Whichever
decision the shared stage owns diverges next, the document that has it is now in the set.

_The shared stage feeds both consumers._ In each port, one rule inside `emitEntries` was changed
once — `present_null` / `presentNull` forced to `false` — and both renderings moved. Python: **6
failed** — 2 in `test_snapshots.py` (the YAML consumer: `comments.yml`, `body_shapes.yml`) and 4 in
`test_emitter/test_to_data.py` (the data consumer), from a single edited line. TypeScript: **5
failed** — 2 in `snapshots.test.ts` and 3 in `to-data.test.ts`, likewise from one line. The sweep
itself stayed green in both, which is the point: the two renderings moved _together_, because they
read one rule. Reverted.

**What was deliberately not done.** Proposal 02's recommended design — one plain emission tree with
a swappable ruamel/`yaml` backend — is not built, and the value-rendering dispatch is still
duplicated per port: `_value_to_data` beside `_to_node` in Python, `valueToData` beside
`toYamlValue` in TypeScript, roughly 25 lines each. That duplication is a different shape from the
one this issue was about. The collection stage decided _what_ is emitted — the answers the two
walks could disagree on with both suites green — and it is now shared. The value dispatch decides
_how_ each already-agreed value is rendered into a backend the two do not share, so collapsing it
means introducing the intermediate tree and the backend interface, in both ports, with no bytes to
show for it. It was considered and deferred rather than smuggled in behind a structural change that
had to move zero bytes. Python's `emit_entries` was left alone beyond what TypeScript parity
required — which was nothing.

**Counts.** pytest **1019 → 1045** (+26: 25 registry sweeps, 1 accounting test; the init-scaffold
round-trip is an assertion inside an existing test). vitest **1074 → 1092** across **46 → 47 files**
(+18: 17 registry sweeps, 1 accounting test). Both suites green, and again under `CI=true` for
Python. `./scripts/typecheck.sh all`, `./scripts/lint.sh all`, `./scripts/fmt.sh all`,
`ghagen check-synced`, `ghagen deps check-synced` and `ghagen_schema check` all pass; the docs build
runs as part of the typecheck gate and is green, which is the independent confirmation that no
emitted byte moved.

## Files

- `packages/typescript/src/emitter/yaml-writer.ts` — `Entry`, `emitEntries`, both consumers
- `packages/python/src/ghagen/emitter/nodes.py` — the design ported across (unmodified)
- `packages/python/tests/test_integration/fixture_models.py`,
  `packages/typescript/src/integration/fixture-models.ts` — the one fixture → model binding
- `packages/python/tests/test_integration/test_to_data_sweep.py`,
  `packages/typescript/src/integration/to-data-sweep.test.ts` — the sweep
- `packages/python/tests/test_cli/test_init_scaffold.py`,
  `packages/typescript/src/cli/init-scaffold.test.ts` — the one document swept where it is built
