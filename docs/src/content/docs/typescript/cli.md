---
title: CLI Reference
description: ghagen CLI command documentation for TypeScript
---

ghagen provides commands organized into top-level commands (`synth`, `check-synced`, `init`) and a `deps` subgroup (`deps pin`, `deps check-synced`, `deps upgrade`).

## Installation

```bash
npm install --save-dev @ghagen/ghagen
```

## ghagen synth

Generate YAML workflow files from your TypeScript/JavaScript definitions.

```bash
npx ghagen synth
```

### Options

| Option          | Description                                                 |
| --------------- | ----------------------------------------------------------- |
| `--config PATH` | Path to the configuration file. Defaults to auto-detection. |

### Config file resolution

If `--config` is not specified, ghagen locates the workflow file in this order:

1. The top-level `entrypoint` key in `.ghagen.yml`, if present
2. `.github/ghagen.workflows.ts`
3. `.github/ghagen.workflows.js`
4. `.github/ghagen.workflows.mjs`
5. `ghagen.workflows.ts`
6. `ghagen.workflows.js`
7. `ghagen.workflows.mjs`
8. `ghagen.config.ts`
9. `ghagen.config.js`
10. `ghagen.config.mjs`

The `entrypoint` value is a path (relative paths resolve against the
`.ghagen.yml` parent directory, i.e. the repo root, not the current working
directory). Use this when your workflow file lives outside the default
locations:

```yaml
# .ghagen.yml
entrypoint: scripts/workflows.ts
```

Within the workflow file, ghagen looks for:

1. A `createApp()` function that returns an `App` instance
2. An `app` variable that is an `App` instance

### Example

```bash
# Use default config detection
npx ghagen synth

# Specify a config file
npx ghagen synth --config workflows/generate.ts
```

## ghagen check-synced

Verify that generated YAML files match the current TypeScript/JavaScript definitions. Fails if any file is stale (see [Exit codes](#exit-codes)).

```bash
npx ghagen check-synced
```

### Options

| Option          | Description                                                 |
| --------------- | ----------------------------------------------------------- |
| `--config PATH` | Path to the configuration file. Defaults to auto-detection. |

This command follows the same config file resolution as `synth`.

### Example

```bash
# Run in CI to catch stale workflows
npx ghagen check-synced

# Check with explicit config
npx ghagen check-synced --config .github/ghagen.workflows.ts
```

### CI usage

Add `ghagen check-synced` to your CI pipeline to ensure that generated YAML files are never out of sync with their TypeScript definitions:

```yaml
- name: Check workflow freshness
  run: npx ghagen check-synced
```

If someone edits a generated YAML file directly instead of updating the TypeScript source, `ghagen check-synced` will fail and the CI run will report the mismatch.

## ghagen deps pin

Pin every `uses:` reference in your workflows to an exact commit SHA, recorded
in `.ghagen.lock.yml`. When a lockfile is present, `ghagen synth`
automatically rewrites `uses:` entries to the pinned SHA on emission, so your
generated YAML is reproducible without hand-editing.

```bash
npx ghagen deps pin           # Resolve any refs missing from the lockfile
npx ghagen deps pin --update  # Re-resolve every entry to the latest SHA
npx ghagen deps pin --prune   # Drop lockfile entries no longer referenced
```

### Options

| Option                | Description                                                                                                                        |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `--config PATH`, `-c` | Path to the configuration file. Defaults to auto-detection.                                                                        |
| `--update`            | Re-resolve every entry to its current SHA, not just the missing ones.                                                              |
| `--prune`             | Remove lockfile entries that are no longer referenced by any workflow.                                                             |
| `--token TOKEN`       | GitHub token used to resolve refs. Defaults to `$GITHUB_TOKEN`, then `$GH_TOKEN`. Unauthenticated requests are limited to 60/hour. |

## ghagen deps check-synced

Verify the lockfile is in sync with the current code. Fails if the lockfile is stale (see [Exit codes](#exit-codes)). Does not make network calls.

```bash
npx ghagen deps check-synced
```

### Options

| Option                | Description                                                                    |
| --------------------- | ------------------------------------------------------------------------------ |
| `--config PATH`, `-c` | Path to the configuration file. Defaults to auto-detection.                    |
| `--prune`             | Also check for lockfile entries that are no longer referenced by any workflow. |

### CI usage

Run `ghagen deps check-synced --prune` in CI to catch PRs that introduce a new
`uses:` without updating the lockfile:

```typescript
step({
  name: "Check lockfile sync",
  run: "npx ghagen deps check-synced --prune",
});
```

`ghagen deps check-synced` does not make network calls, so it doesn't need a GitHub token.

## ghagen deps upgrade

Detect and apply updates to action dependencies in your workflows. By default,
applies updates to source files (version bumps). Use `--check` for a
dry-run report without modifying files.

```bash
npx ghagen deps upgrade                     # Apply available updates to source files
npx ghagen deps upgrade --check             # Report available updates without applying
npx ghagen deps upgrade --check --format json  # Machine-readable JSON report
```

### Options

| Option                | Description                                                                      |
| --------------------- | -------------------------------------------------------------------------------- |
| `--config PATH`, `-c` | Path to the configuration file. Defaults to auto-detection.                      |
| `--check`             | Report available updates without applying changes (dry-run mode).                |
| `--format FORMAT`     | Output format: `json`, `pr-body`, or `issue-body`. Omit for human-readable text. |
| `--mode MODE`         | Detection mode: `versions`, `lockfile`, or `all` (default).                      |
| `--token TOKEN`       | GitHub token used to query tags. Defaults to `$GITHUB_TOKEN`, then `$GH_TOKEN`.  |

### Which refs count as version tags

Only refs that match ghagen's version-tag grammar are upgrade candidates. A ref
is a version tag when it is an optional prefix (`prefix-` or `prefix/`), an
optional `v`, and dot-separated integers — and every segment's value is at most
`999999999999999`. When a prefix is present the numeric part needs at least two
segments, so `release/v1` stays a branch ref.

| Ref              | Version tag? | Why                                         |
| ---------------- | ------------ | ------------------------------------------- |
| `v4`             | yes          | release `4.0.0` — short forms are padded    |
| `v4.1`           | yes          | release `4.1.0`                             |
| `v1.2.3.4`       | yes          | more than three segments is allowed         |
| `v2.04`          | yes          | release `2.4.0` — leading zeros are numeric |
| `prefix/v1.0.0`  | yes          | prefixed, two or more segments              |
| `release/v1`     | no           | prefixed with one segment — a branch ref    |
| `main`, `latest` | no           | not numeric                                 |
| `v1.2.3-rc1`     | no           | prereleases and build metadata are not tags |

The **canonical release** of a tag is its segments as integers, padded to three
and stripped of trailing zeros beyond the third — so `v1.2.3.0` and `v1.2.3` are
the same version. Two tags are compared by that release, element-wise and then
by length, and only tags sharing the current ref's prefix are considered. The
severity reported for a bump is `major` when the first element changes, `minor`
when the second does, and `patch` otherwise.

The grammar is identical in the Python port — it is the shared contract in
`schema/tag-grammar.yml`, which both ports' suites are driven against.

## ghagen init

Scaffold a starter configuration file with a minimal CI workflow.

```bash
npx ghagen init
```

### Options

| Option          | Description                                                    |
| --------------- | -------------------------------------------------------------- |
| `--outdir PATH` | Directory to create the config file in. Defaults to `.github`. |

### Example

```bash
# Create .github/ghagen.workflows.ts
npx ghagen init

# Create in a custom directory
npx ghagen init --outdir workflows
```

The generated file contains an `App` instance with a single CI workflow that checks out code and runs a placeholder test command.

## Exit codes

Every command exits with one of three codes. The table is identical in the
Python port — it is the shared contract in `fixtures/cli-exit-codes.yml`,
which both ports' `main()` is tested against.

| Code | Meaning                                                                                                                                                                                                    |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `0`  | The command did what it was asked. Includes both "no updates available" and "updates available" under `deps upgrade --check` — a report is not a failure.                                                  |
| `1`  | Expected failure: generated files are stale, the lockfile is stale, refs failed to resolve, no config file was found, or the config module raised.                                                         |
| `2`  | Usage error: unknown command, unknown option, missing option argument, invalid option value, or no arguments at all. Framework-detected and hand-validated usage errors are indistinguishable to a caller. |
