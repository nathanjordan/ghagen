# Config discovery returns typed results, not framework exceptions

**Status:** accepted (2026-07-28)

The config module (`config.py` / `config.ts`) solely owns `.ghagen.yml`: discovery, a single
parse, validation, and App resolution (`resolve_app` / `resolveApp`). It returns a typed
`ProjectConfig` (root, config path, entrypoint, options, errors) with **errors as values**
(`ConfigError` kinds: `parse`, `not-a-mapping`, `bad-entrypoint-type`, `entrypoint-missing`,
`bad-option-type`, `app-resolution`); it never raises on user input. The CLI renders errors and
owns exit codes; `CliError` is CLI-local. An explicit `--config` flag short-circuits discovery —
a malformed `.ghagen.yml` must not block an explicit override.

## Why

`.ghagen.yml` was parsed twice per CLI invocation by two schemas of different strictness, and
discovery/load errors were only expressible (and testable) as `typer.Exit` / thrown `CliError` —
in contrast to the pin engine's typed-report style. Parallel to that decision: pure result types
at the seam, presentation at the edge.

## Consequences

- `DEFAULT_LOCKFILE_PATH` is single-homed in the config module; `pin/lockfile` re-exports it.
- Spec 0004 unified root discovery and the TS config file layout; this decision unifies the file
  parse it left split.
- The exit-code contract is `fixtures/cli-exit-codes.yml`, driven through `main()` by both ports:
  `0` success, `1` expected failure, `2` usage error. The CLI frameworks render text; `main()`
  decides the number.
