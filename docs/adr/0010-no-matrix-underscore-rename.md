# `Strategy.matrix` is not renamed to `matrix_`

**Status:** accepted (2026-07-31)

The Python `Strategy` model keeps a field named `matrix`. It is **not** renamed to `matrix_` to
mirror the `with_` / `if_` convention, and TypeScript's `strategy({ matrix: … })` keeps its plain
`matrix` key.

## Why this keeps coming up

`with_` and `if_` carry trailing underscores because `with` and `if` are Python **keywords** — the
field could not be spelled otherwise. `matrix` is not a keyword. The trailing underscore on those
two is forced; on `matrix` it would be decorative, adopted only to make the three look alike.

The recurring argument for renaming is not aesthetic, though: the two ports could diverge on this
field and nothing would catch it. That is a real concern, and it is the reason this was raised twice
in round 2 (proposals 09 and 11 both considered it and both declined).

## Why the rename does not answer that concern

**A rename does not detect divergence; it only makes one shape look like the other.** Two ports can
agree on a field's spelling and still disagree about its accepted values, its emission order, or
whether it is emitted at all — and every one of those has actually happened in this repo. Round 2
found the `workflow_call` sub-map defs emitting in three different orders across ports while their
key names matched exactly (proposal 11).

**The silent half of the failure is already closed.** Before round 2, `strategy({matrix: …})` in a
port that did not model the field would drop it without a word. Proposal 09 made unknown input keys
raise `ModelInputError` in both ports, so a misspelling or a port-only field is now a construction
error rather than a silent omission. The weaker half of the case for renaming went away with it.

**The cost lands on the port with no reason to pay it.** A Python-side `matrix_` would have to be
mirrored into TypeScript, where `matrix` is not reserved and the underscore reads as a typo, buying
cross-port cosmetic symmetry at the price of an ergonomic wart in the port that has no keyword
problem. Pre-1.0 breaking changes are cheap here, so this is not an argument from compatibility —
it is that the change makes the published surface worse in exchange for no detection.

## What actually catches the divergence

A shared table both ports bind and both suites read. That is the mechanism round 2 built:
`schema/conformance-scopes.yml` (28 scopes as of round 2, with an empty
`schema/conformance-gaps.yml` — every declared property is covered in both ports),
`schema/conformance-values.yml` for declared value grammars, and `fixtures/expected/` as the
byte oracle.

If a future round wants `strategy`/`matrix` divergence caught specifically, the mechanism is a
conformance **scope** covering `jobs.<id>.strategy`, or a cross-port shape assertion — not a rename.

## Consequences

**Do not re-suggest the rename on symmetry grounds.** Reopen this only with a concrete divergence
that a rename would have caught and a scope would not. No such case has been produced in two rounds.

**The `with_` / `if_` underscores stay** — they are keyword-forced and carry no implication that
non-keyword fields should follow suit.
