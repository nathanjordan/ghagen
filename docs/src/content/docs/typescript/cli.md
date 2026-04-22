---
title: CLI Reference
description: ghagen CLI command documentation for TypeScript
---

ghagen provides commands organized into top-level commands (`synth`, `check-synced`, `lint`, `init`) and a `deps` subgroup (`deps pin`, `deps check-synced`, `deps upgrade`).

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

lint:
  # existing lint config continues to live here
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

Verify that generated YAML files match the current TypeScript/JavaScript definitions. Exits with code 0 if all files are up to date, or code 1 if any file is stale.

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

## ghagen lint

Run rule-based checks against your workflow definitions. See the
[Linting guide](../linting/) for rule descriptions and configuration.

```bash
npx ghagen lint
```

### Options

| Option                               | Description                                                 |
| ------------------------------------ | ----------------------------------------------------------- |
| `--config PATH`, `-c`                | Path to the config file.                                    |
| `--format {human,json,github}`, `-f` | Output format. Defaults to `human`.                         |
| `--disable RULE_ID`                  | Disable a rule by ID. Can be repeated.                      |
| `--list-rules`                       | Print all available rules with their descriptions and exit. |

### Exit codes

| Code | Meaning                                                      |
| ---- | ------------------------------------------------------------ |
| `0`  | No error-severity violations (warnings may still be present) |
| `1`  | At least one error-severity violation found                  |
| `2`  | Configuration error (malformed YAML, unknown severity, etc.) |

### Example

```bash
# Human-readable output (default)
npx ghagen lint

# JSON for scripts
npx ghagen lint --format=json

# GitHub annotations for CI
npx ghagen lint --format=github

# List all rules
npx ghagen lint --list-rules

# Disable specific rules
npx ghagen lint --disable missing-timeout
```

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

### Exit codes

| Code | Meaning                                           |
| ---- | ------------------------------------------------- |
| `0`  | Lockfile is in sync (or was updated successfully) |
| `1`  | One or more refs failed to resolve                |

## ghagen deps check-synced

Verify the lockfile is in sync with the current code. Exits with code 1 if the lockfile is stale. Does not make network calls.

```bash
npx ghagen deps check-synced
```

### Options

| Option                | Description                                                                    |
| --------------------- | ------------------------------------------------------------------------------ |
| `--config PATH`, `-c` | Path to the configuration file. Defaults to auto-detection.                    |
| `--prune`             | Also check for lockfile entries that are no longer referenced by any workflow. |

### Exit codes

| Code | Meaning             |
| ---- | ------------------- |
| `0`  | Lockfile is in sync |
| `1`  | Lockfile is stale   |

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
npx ghagen deps upgrade              # Apply available updates to source files
npx ghagen deps upgrade --check      # Report available updates without applying
npx ghagen deps upgrade --check --json  # Machine-readable JSON report
```

### Options

| Option                | Description                                                                     |
| --------------------- | ------------------------------------------------------------------------------- |
| `--config PATH`, `-c` | Path to the configuration file. Defaults to auto-detection.                     |
| `--check`             | Report available updates without applying changes (dry-run mode).               |
| `--json`              | Output results as JSON (only valid with `--check`).                             |
| `--token TOKEN`       | GitHub token used to query tags. Defaults to `$GITHUB_TOKEN`, then `$GH_TOKEN`. |

### Exit codes

| Code | Meaning                                                              |
| ---- | -------------------------------------------------------------------- |
| `0`  | No updates available, or updates applied successfully                |
| `1`  | Updates available (`--check`) or one or more updates failed to apply |

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
