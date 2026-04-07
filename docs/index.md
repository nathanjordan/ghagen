# ghagen

**Generate GitHub Actions workflows from Python code.**

Get type safety, IDE autocomplete, DRY patterns, and version-controlled workflow generation.

## Quick Install

=== "pip"

    ```bash
    pip install ghagen
    ```

=== "uv"

    ```bash
    uv add ghagen
    ```

## Example

Define your workflow in Python:

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

ghagen generates clean, readable YAML:

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

- **Typed Pydantic models** for workflows, jobs, steps, triggers, and permissions
- **IDE autocomplete** and type checking for every field
- **YAML comment support** — block, end-of-line, and field-level comments
- **DRY helpers** — step factories (`checkout()`, `setup_python()`, etc.) and expression builder (`expr`)
- **Escape hatches** — `Raw[T]`, `extras`, `post_process`, and `CommentedMap` passthrough for edge cases
- **CLI** — `ghagen synth` to generate, `ghagen check` to verify freshness in CI

## Next Steps

- [Getting Started](getting-started.md) — step-by-step tutorial
- [Concepts](concepts.md) — architecture overview
- [API Reference](api/workflow.md) — full model documentation
