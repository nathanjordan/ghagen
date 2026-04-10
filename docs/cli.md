# CLI Reference

ghagen provides five commands: `synth`, `check`, `lint`, `pin`, and `init`. All commands are invoked through the `ghagen` CLI, which is built with Typer.

## ghagen synth

Generate YAML workflow files from your Python definitions.

```bash
ghagen synth
```

### Options

| Option | Description |
|---|---|
| `--config PATH` | Path to the configuration file. Defaults to auto-detection. |

### Config file resolution

If `--config` is not specified, ghagen locates the workflow file in this order:

1. The top-level `entrypoint` key in `.github/ghagen.toml`, if present
2. `.github/ghagen_workflows.py`
3. `ghagen_config.py`

The `entrypoint` value is a path (relative paths resolve against the
directory containing `ghagen.toml`, not the current working directory). Use
this when your workflow file lives outside the two default locations:

```toml
# .github/ghagen.toml
entrypoint = "../scripts/workflows.py"

[lint]
# existing lint config continues to live here
```

Within the workflow file, ghagen looks for:

1. A `create_app()` function that returns an `App` instance
2. An `app` variable that is an `App` instance

### Example

```bash
# Use default config detection
ghagen synth

# Specify a config file
ghagen synth --config workflows/generate.py
```

## ghagen check

Verify that generated YAML files match the current Python definitions. Exits with code 0 if all files are up to date, or code 1 if any file is stale.

```bash
ghagen check
```

### Options

| Option | Description |
|---|---|
| `--config PATH` | Path to the configuration file. Defaults to auto-detection. |

This command follows the same config file resolution as `synth`.

### Example

```bash
# Run in CI to catch stale workflows
ghagen check

# Check with explicit config
ghagen check --config .github/ghagen_workflows.py
```

### CI usage

Add `ghagen check` to your CI pipeline to ensure that generated YAML files are never out of sync with their Python definitions:

```yaml
- name: Check workflow freshness
  run: ghagen check
```

If someone edits a generated YAML file directly instead of updating the Python source, `ghagen check` will fail and the CI run will report the mismatch.

## ghagen lint

Run rule-based checks against your workflow definitions. See the
[Linting guide](linting.md) for rule descriptions and configuration.

```bash
ghagen lint
```

### Options

| Option | Description |
|---|---|
| `--config PATH`, `-c` | Path to the `ghagen_workflows.py` config file. |
| `--format {human,json,github}`, `-f` | Output format. Defaults to `human`. |
| `--disable RULE_ID` | Disable a rule by ID. Can be repeated. |
| `--list-rules` | Print all available rules with their descriptions and exit. |

### Exit codes

| Code | Meaning |
|------|---------|
| `0`  | No error-severity violations (warnings may still be present) |
| `1`  | At least one error-severity violation found |
| `2`  | Configuration error (malformed TOML, unknown severity, etc.) |

### Example

```bash
# Human-readable output (default)
ghagen lint

# JSON for scripts
ghagen lint --format=json

# GitHub annotations for CI
ghagen lint --format=github

# List all rules
ghagen lint --list-rules

# Disable specific rules
ghagen lint --disable missing-timeout --disable unpinned-actions
```

## ghagen pin

Pin every `uses:` reference in your workflows to an exact commit SHA, recorded
in `.github/ghagen.lock.toml`. When a lockfile is present, `ghagen synth`
automatically rewrites `uses:` entries to the pinned SHA on emission, so your
generated YAML is reproducible without hand-editing.

```bash
ghagen pin           # Resolve any refs missing from the lockfile
ghagen pin --update  # Re-resolve every entry to the latest SHA
ghagen pin --check   # Fail if the lockfile is out of sync (CI-friendly)
ghagen pin --prune   # Drop lockfile entries no longer referenced
```

### Options

| Option | Description |
|---|---|
| `--config PATH`, `-c` | Path to the configuration file. Defaults to auto-detection. |
| `--update` | Re-resolve every entry to its current SHA, not just the missing ones. |
| `--check` | Verify the lockfile is in sync with the current code; exit 1 if stale. No network calls. |
| `--prune` | Remove lockfile entries that are no longer referenced by any workflow. |
| `--token TOKEN` | GitHub token used to resolve refs. Defaults to `$GITHUB_TOKEN`, then `$GH_TOKEN`. Unauthenticated requests are limited to 60/hour. |

### Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Lockfile is in sync (or was updated successfully) |
| `1`  | Lockfile is stale (`--check`) or one or more refs failed to resolve |

### CI usage

Run `ghagen pin --check --prune` in CI to catch PRs that introduce a new
`uses:` without updating the lockfile:

```python
Step(
    name="ghagen pin --check",
    run="ghagen pin --check --prune",
)
```

`--check` does not make network calls, so it doesn't need a GitHub token.

## ghagen init

Scaffold a starter configuration file with a minimal CI workflow.

```bash
ghagen init
```

### Options

| Option | Description |
|---|---|
| `--outdir PATH` | Directory to create the config file in. Defaults to `.github`. |

### Example

```bash
# Create .github/ghagen_workflows.py
ghagen init

# Create in a custom directory
ghagen init --outdir workflows
```

The generated file contains an `App` instance with a single CI workflow that checks out code and runs a placeholder test command. See [Getting Started](getting-started.md) for the full scaffold content.
