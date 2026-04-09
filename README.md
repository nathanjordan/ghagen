# ghagen

Generate GitHub Actions workflows from Python code.

[![CI](https://github.com/nathanjordan/ghagen/actions/workflows/ci.yml/badge.svg)](https://github.com/nathanjordan/ghagen/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/ghagen)](https://pypi.org/project/ghagen/)
[![Python](https://img.shields.io/pypi/pyversions/ghagen)](https://pypi.org/project/ghagen/)
[![License](https://img.shields.io/github/license/nathanjordan/ghagen)](LICENSE)

## Install

```bash
pip install ghagen
```

## Example

```python
from ghagen import Workflow, Job, Step, On, App
from ghagen.models.trigger import PushTrigger, PRTrigger

workflow = Workflow(
    name="CI",
    on=On(
        push=PushTrigger(branches=["main"]),
        pull_request=PRTrigger(branches=["main"]),
    ),
    jobs={
        "test": Job(
            runs_on="ubuntu-latest",
            steps=[
                Step(uses="actions/checkout@v4"),
                Step(name="Run tests", run="python -m pytest"),
            ],
        ),
    },
)

app = App(outdir=".github/workflows")
app.add(workflow, filename="ci.yml")
app.synth()
```

This generates:

```yaml
name: CI
on:
  pull_request:
    branches:
    - main
  push:
    branches:
    - main
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Run tests
      run: python -m pytest
```

## Features

- **Typed models** — Pydantic models for workflows, jobs, steps, triggers, and permissions with full IDE autocomplete
- **YAML comments** — block, end-of-line, and field-level comments preserved in output
- **DRY helpers** — step factories (`checkout()`, `setup_python()`, `setup_uv()`) and expression builder (`expr`)
- **Escape hatches** — `Raw[T]`, `extras`, `post_process`, and `CommentedMap` passthrough for anything the typed API doesn't cover
- **Linting** — `ghagen lint` catches common problems (missing `permissions`, unpinned actions, missing `timeout-minutes`, duplicate step ids) at the Python level with source-line precision
- **CLI** — `ghagen synth` generates YAML, `ghagen check` verifies freshness in CI, `ghagen lint` runs rule-based checks, `ghagen init` scaffolds a starter config

## Quick Start

```bash
# Scaffold a config file
ghagen init

# Generate workflow YAML
ghagen synth

# Verify workflows match Python definitions (for CI)
ghagen check

# Lint workflow definitions
ghagen lint
```

## Documentation

Full documentation: [nathanjordan.github.io/ghagen](https://nathanjordan.github.io/ghagen/)

## License

MIT
