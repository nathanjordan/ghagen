# TypeScript has no multi-repo `upgrade()` test

**Status:** open — from round 2

Python covers `upgrade()` across more than one repository; TypeScript does not. The parity mandate in
`AGENTS.md` is about the shipped surface, and the surface is present in both ports — this is a
**coverage** gap, not a behaviour divergence, which is why it did not become a proposal.

It is the cheapest remaining item in this file: one test, mirroring the Python case, against the
canned transport that proposal 16 single-homed.
