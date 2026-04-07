# CLI Reference

ghagen provides three commands: `synth`, `check`, and `init`. All commands are invoked through the `ghagen` CLI, which is built with Typer.

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
