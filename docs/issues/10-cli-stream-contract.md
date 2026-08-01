# 78 CLI assertions cannot detect a stdout/stderr regression

**Status:** open — from round 2, deferred out of proposal 19 with a measurement attached

`packages/python/tests/test_cli/` holds **78 `result.output` assertions, 3 `result.stdout`, and 1
`result.stderr`**. `result.output` is the merged stream, so 78 of the 82 cannot tell stdout from
stderr — exactly the class of bug hotfix H6 was (`deps upgrade --format json` printing a progress
note to stdout ahead of the JSON, making the output unparseable).

Proposal 19 recorded this rather than rewriting it mid-round, and **instructs implementers not to
"fix" these piecemeal**: a scattered half-conversion leaves it unclear which assertions are
stream-precise on purpose and which merely have not been converted yet.

This wants its own proposal — a single sweep, plus a rule about which stream each command's
machine-readable output belongs on.
