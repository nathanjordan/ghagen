# TypeScript has no multi-repo `upgrade()` test

**Status:** closed — the test exists; verified round 3

Python covers `upgrade()` across more than one repository; TypeScript does not. The parity mandate in
`AGENTS.md` is about the shipped surface, and the surface is present in both ports — this is a
**coverage** gap, not a behaviour divergence, which is why it did not become a proposal.

It is the cheapest remaining item in this file: one test, mirroring the Python case, against the
canned transport that proposal 16 single-homed.

## Resolution

The test was written and cites this issue by number.
`packages/typescript/src/pin/engine.test.ts`, `it("detects and applies version bumps across more
than one repository")`: two distinct repos (`actions/checkout`, `actions/setup-python`) in one
`upgrade()` call against the shared canned transport, asserting both `versionBumps` entries and both
rewritten `uses:` strings.

It is a deliberate improvement on the Python counterpart rather than a transcription of it, and its
comment says so: Python's multi-repo case drives the **CLI** with a mocked
`GitHubClient.list_tags`, while this one drives the **engine** directly against the shared canned
transport, one entry per repo, to prove a second loop iteration over a distinct repo is actually
exercised.
