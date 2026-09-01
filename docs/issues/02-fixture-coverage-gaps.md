# Integration fixture coverage gaps

**Status:** closed — all five body-shape gaps closed by one fixture,
`fixtures/expected/body_shapes.yml`, proven load-bearing by a six-way single-byte corruption

`fixtures/expected/` exercises none of: a `defaults:` block, empty `workflow_dispatch`
(present-null), a dynamic extras interleave on an alphabetical spec, or SHA-pinned `uses:` refs. The
round's "snapshots are the byte oracle" claim is hollow for exactly the paths it changed; those are
unit-covered only. Add one workflow fixture covering all four.

The extras example used to be `merge_group`, which is a typed `On` field as of round 2 (proposal
11). `on:` now models every event the canonical Snapshot declares — asserted scope-wide by the
conformance sweep — so the extras half of that fixture needs a key the Snapshot does not carry
(an event GitHub ships ahead of the Snapshot), not a real-but-unmodelled event.

Also added in round 2: no file under `fixtures/expected/` contains `workflow_call` at all. Proposal
11 gave the three `workflow_call` sub-map defs their own TypeScript specs so both ports emit them in
the same canonical key order; that byte change has unit coverage in both ports and no shared
fixture oracle. A `workflow_call` block with inputs, outputs, and secrets belongs in the same
fixture.

**Amendment (proposal 13):** the inventory above was incomplete — **headers** were a gap of the
same kind, and a larger one. Every one of the ten emitter goldens passed `header=None`, so the byte
oracle contained zero header bytes and never saw a live five-way byte divergence between the ports.
Closed by `fixtures/expected/header_*.yml` (six files, read byte-for-byte by both suites). The gaps
listed above remain open; they are body-shape gaps and 13 adds no body coverage. Scheduling note:
the remedy above and the header goldens touch the same two test files (`test_snapshots.py`,
`snapshots.test.ts`) and the same directory, so a single pass over `fixtures/expected/` avoids a
second round of conflicts.

## Resolution

One fixture, `fixtures/expected/body_shapes.yml` (45 lines), read byte-for-byte by
`test_body_shapes` in `packages/python/tests/test_integration/test_snapshots.py` and by
`it("body_shapes.yml")` in `packages/typescript/src/integration/snapshots.test.ts`. One file rather
than five because the gaps are body shapes of a single workflow and a single document exercises the
interactions between them — an alphabetical `on:` whose extras key must sort _between_ two typed
keys is not expressible in a fixture that carries only extras.

The TypeScript half was written independently against the same bytes and passed byte-identical on
its first run, which is the only reason to have two ports assert one file.

### What each gap got

1. **`defaults:`** — at both levels, because they are different code paths: a workflow-level
   `defaults.run` with `shell` and `working-directory`, and a job-level `defaults.run` overriding
   `working-directory` alone. `working-directory` also pins the underscore-to-hyphen key mapping.
2. **Present-null** — a bare `workflow_dispatch:` (the case the issue named) _and_ a bare `create:`
   (an event that only present-nulls because of `docs/issues/04`'s widening). The second is the one
   that matters: it is the byte that would silently revert if the widened rule were narrowed back.
3. **Dynamic extras interleave on an alphabetical spec** — `pull_request_review_thread`, which
   sorts strictly between the typed keys `create` and `push`, so the emitted order is
   `create` → `pull_request_review_thread` → `push` → `workflow_call` → `workflow_dispatch` and a
   fixture that appended extras instead of interleaving them would differ in bytes.
4. **SHA-pinned `uses:`** — two refs, deliberately not one: `actions/checkout` pinned with a
   `# v4.2.2` end-of-line comment (pin plus comment geometry) and `actions/setup-python` pinned
   bare (pin with no comment). The two render through different paths.
5. **`workflow_call`** — `inputs`, `outputs` and `secrets` all three, each a sub-map def with its
   own spec, which is what proposal 11 changed and what had no shared oracle. The `outputs.value`
   carries a `${{ }}` expression and the secret key `deploy-token` carries a hyphen.

### The extras key, and why it is that one

The issue asks for "a key the canonical Snapshot does NOT carry (an event GitHub ships ahead of the
Snapshot) … A real-but-unmodelled event will not work." There is currently **no** genuinely-newer
upstream event to borrow: `origin/schema-drift/20260831` — the branch holding the newer Snapshot —
adds no new `on:` events, checked directly. `pull_request_review_thread` is the substitute: a real
GitHub event that the canonical Snapshot's `on:` map does not declare, so it behaves in this fixture
exactly as a genuinely-ahead event would (unmodelled, so it can only arrive through `extras`), and
its sort position makes the interleave load-bearing. If the Snapshot ever adds it, the conformance
sweep's scope assertion fails first and points here.

Checked before choosing it: snapshot fixtures are not schema-validated. Only
`schema-validation.test.ts` validates against the Snapshot and it builds its own workflows, so
`additionalProperties: false` on the `on:` map does not reject this fixture.

### Corruption proof

The repo's standard, run in full. Six single-byte corruptions of `body_shapes.yml`, one per gap
(two for present-null, one per event), each run against both suites:

```
present-null create:               python_fails=True  vitest_fails=True
present-null workflow_dispatch:    python_fails=True  vitest_fails=True
extras interleave                  python_fails=True  vitest_fails=True
defaults block                     python_fails=True  vitest_fails=True
SHA-pinned uses                    python_fails=True  vitest_fails=True
workflow_call block                python_fails=True  vitest_fails=True
restored, unchanged: True
```

Each replacement was asserted to be the same length as its needle and to differ by exactly one
byte, and the needle to occur exactly once, before it was written. The fixture was restored from
the original bytes in a `finally` and compared byte-for-byte afterwards. **Both** suites fail for
**every** corruption: the file is a shared oracle, not two independent assertions that happen to
agree.

### Suite counts

`pytest 1008 → 1011 passed`, `vitest 1069 → 1072 passed (46 files)` — three new tests per port
(`test_body_shapes` here, plus the two `docs/issues/04` tests). No fixture, test or golden was
removed.

### What was deliberately NOT done

**The `header=None` habit was not revisited.** `body_shapes.yml` passes `header=None`, like the ten
emitter goldens the round-2 amendment criticises. That is correct here and not a regression of what
proposal 13 fixed: the header goldens (`fixtures/expected/header_*.yml`) exist precisely so header
bytes have their own oracle, and stamping a header onto a body-shape fixture would make every byte
of it hostage to a header change.

**No fixture was added for a `null` that survives to emission.** `On(extras={"foo": None})` renders
`foo:` in Python and `foo: null` in TypeScript — a live cross-port byte divergence, found while
closing `docs/issues/04`, filed as `docs/issues/36`. Putting it into `body_shapes.yml` would have
required fixing it first (the ports disagree, so there are no shared bytes to write down), and that
fix is an emitter change that deserves its own red-green proof rather than riding this pass.

**`packages/python/tests/test_integration/test_snapshots.py` still imports `Defaults`,
`DefaultsRun` and the three `WorkflowCall*` sub-defs from `ghagen.models.*`** rather than from
`ghagen`, because the package does not export them while TypeScript exports its peers. Same family
as `docs/issues/27`; recorded there and in `docs/issues/04`, not fixed on the way past.
