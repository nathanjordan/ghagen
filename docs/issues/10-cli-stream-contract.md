# 78 CLI assertions cannot detect a stdout/stderr regression

**Status:** closed — swept, see Resolution. From round 2, deferred out of proposal 19 with a
measurement attached

`packages/python/tests/test_cli/` holds **78 `result.output` assertions, 3 `result.stdout`, and 1
`result.stderr`**. `result.output` is the merged stream, so 78 of the 82 cannot tell stdout from
stderr — exactly the class of bug hotfix H6 was (`deps upgrade --format json` printing a progress
note to stdout ahead of the JSON, making the output unparseable).

Proposal 19 recorded this rather than rewriting it mid-round, and **instructs implementers not to
"fix" these piecemeal**: a scattered half-conversion leaves it unclear which assertions are
stream-precise on purpose and which merely have not been converted yet.

This wants its own proposal — a single sweep, plus a rule about which stream each command's
machine-readable output belongs on.

_(The 78/3/1 figures above are as they stood at filing, kept for the historical record — they were
never re-measured before now and had drifted; see Resolution for the swept, current count.)_

## Resolution

Swept `test_deps.py` and `test_main.py` — the two files the original count came from — assertion by
assertion, deciding each one's stream from the actual `typer.echo(..., err=?)` call it exercises
(`packages/python/src/ghagen/cli/deps.py`, `main.py`, `_common.py`), not by guessing. **54
assertions converted** (32 in `test_deps.py`, 22 in `test_main.py`) from `result.output` to
`result.stdout` or `result.stderr`. **3 were deliberately left on `result.output`**, all in
`test_deps.py` — each a genuine total-absence claim ("this string must appear on neither stream"),
not a which-stream claim, so the merged stream is the right tool: the `helper_provided` key must
never leak onto either stream from an empty `--format json` report, the H7 `"lockfile is disabled"`
message must never fire on a `lockfile: null` project, and a bare `assert` must never produce a
`Traceback` on either stream. Each carries a `# Deliberately spans both streams: ...` comment
explaining why, so a reader can tell "deliberate" from "not yet converted" at a glance. The
remaining files under `test_cli/` (`test_exit_codes.py`, `test_common.py`, `test_init_scaffold.py`)
had no `result.output` usage needing conversion.

The stream rule itself was not invented here — it already existed in both ports (Python's
`deps.py`: `progress_to_stderr = output_format is not None`; TypeScript's `deps.ts`: `format !==
undefined ? process.stderr : process.stdout`), and TypeScript already had a test for it. What was
missing was a name for the rule, a place both ports assert it from together, and a floor under it
so it cannot rot back into a single-port fact. Four pieces close that gap:

1. **`schema/cli-streams.yml`** — a 17-row shared oracle, peer of `fixtures/cli-exit-codes.yml`,
   naming the single stream (`stdout` or `stderr`) each `(command, condition)` pair's output belongs
   on, plus a `note` explaining why.
2. **Both suites are driven from it directly**: `packages/python/tests/test_cli/test_streams.py`
   (17 tests, new) and `packages/typescript/src/cli/streams.test.ts` (17 tests, new) each load the
   table at collection time and invoke the exact command/condition each row describes.
3. **Proved load-bearing, not just present**: mutating a single row's stream value
   (`deps-upgrade-progress-note-with-format`, `stdout` → `stderr`) failed the corresponding test in
   **both** suites — Python raised an `AssertionError` because the stray "Applied version bumps"
   progress note was no longer found on the row's asserted stream, and TypeScript's vitest run
   failed the mirrored assertion the same way. Reverting the row restored both suites to green.
4. **A lint gate**, `scripts/lint.sh`'s `py` scope: rejects a bare `result.output` anywhere under
   `packages/python/tests/test_cli/*.py` unless one of the three lines above it carries a
   "Deliberately spans both streams" comment. Proved load-bearing the same way as the table: with
   the comment stripped from the `Traceback` assertion in `test_deps.py`, the gate failed with
   `error: packages/python/tests/test_cli/test_deps.py:792: bare 'result.output' use -- add a
'Deliberately spans both streams' comment...`; restoring the comment passed it again.
5. **Documented CLI-wide, not just under `deps update`**: a new "Output streams" section in both
   `docs/src/content/docs/python/cli.md` and its TypeScript peer, giving the general rule (whichever
   stream carries a command's machine-readable payload carries _only_ that payload) plus a per-command
   table, and calling out the `deps upgrade`/`deps update` progress-note asymmetry — conditional on
   `--format` for `upgrade`, unconditional for `update` — as precisely the class of bug this
   contract exists to catch.
