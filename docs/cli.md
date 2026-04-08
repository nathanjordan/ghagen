# CLI Reference

ghagen provides four commands: `synth`, `check`, `lint`, and `init`. All commands are invoked through the `ghagen` CLI, which is built with Typer.

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

If `--config` is not specified, ghagen searches for config files in this order:

1. `.github/ghagen_workflows.py`
2. `ghagen_config.py`

Within the config file, ghagen looks for:

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
