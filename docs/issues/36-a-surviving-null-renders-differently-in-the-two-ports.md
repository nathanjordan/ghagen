# A surviving `null` renders differently in the two ports

**Status:** open — found while closing `docs/issues/04`

Issue 04 settled what a `null`/`None` **field** means: _unset_, dropped at construction in both
ports. That closes the field case, and it closes it in the only place a spec rule can reach — the
model boundary. It says nothing about a `null` that is not a field: one nested inside plain data,
inside a list, or inside `extras`. Those never pass through `buildYamlData` / `collect_fields`, so
`exclude_none` and its TypeScript peer never see them. They reach the emitter intact, and the two
emitters render them differently.

Measured on this branch, both ports, `header=None`:

| construction                                         | Python         | TypeScript         |
| ---------------------------------------------------- | -------------- | ------------------ |
| `Step(with_={"a": None})` / `step({with_:{a:null}})` | `        a:\n` | `        ? a\n`    |
| `with_={"a": [1, None]}`                             | `        - \n` | `        - null\n` |
| `On(extras={"foo": None})`                           | `  foo:\n`     | `  foo: null\n`    |

Three shapes, three divergences, one root cause: Python's writer emits a bare-key null everywhere,
TypeScript's `toYamlValue` hands the underlying writer a plain JS `null`. Python's list form is
additionally wrong on its own terms — `- ` carries a **trailing space**, which no other line this
emitter produces does.

`docs/issues/23` is the closed home for exactly this class ("cross-port byte divergences the oracle
cannot see"), and it is closed because all six of _its_ items were fixed with a `fixtures/expected/`
oracle each. This is a seventh of the same kind, found after that issue closed, so it gets its own
number rather than reopening one.

## Why it was not closed with issue 04

It is a different defect at a different layer. Issue 04's fix is a construction-time rule about
_fields_, proven by reverting one line in `_base.ts` and watching a test go red. This one lives in
the two emitters' scalar writers and would want its own fixture — and the fixture is the work, not
the fix. The TypeScript half is plausibly one line (`toYamlValue` returning `nullScalar()`, the
helper `presentNullWhenEmpty` already uses); the Python half is a trailing-space bug in the list
branch. Neither is in scope for a pass over issues 02 and 04, and folding an unrelated byte change
into the fixture that proves 02 would have made that fixture's corruption proof ambiguous.

## What a fix must do

1. TypeScript: emit a bare-key null for a surviving `null` in every position — map value, list item,
   `extras` value — as Python already does in the first and third.
2. Python: drop the trailing space from the list-item form.
3. Add a `fixtures/expected/` golden carrying all three positions, read byte-for-byte by both
   suites, and prove it load-bearing by corrupting one byte per position.
4. Note that this is deliberately _not_ the same question as issue 04: here `null` is data the
   caller asked to emit, not a field they left unset.

## Files

- `packages/typescript/src/emitter/yaml-writer.ts` — `toYamlValue`, `nullScalar`
- `packages/python/src/ghagen/emitter/yaml_writer.py`, `emitter/nodes.py` — the peer writer
- `fixtures/expected/` — where the golden goes
