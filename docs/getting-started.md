# Getting Started

This tutorial walks you through creating your first GitHub Actions workflow with ghagen.

## 1. Install

Install ghagen with pip or uv:

```bash
pip install ghagen
```

```bash
uv add ghagen --dev
```

## 2. Initialize

Run `ghagen init` to scaffold a starter configuration:

```bash
ghagen init
```

This creates `.github/ghagen_workflows.py` with a minimal CI workflow:

```python
"""GitHub Actions workflow definitions."""

from ghagen import Workflow, Job, Step, On
from ghagen.app import App
from ghagen.models.trigger import PushTrigger, PRTrigger

app = App(outdir=".github/workflows")

ci = Workflow(
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
                Step(name="Run tests", run="echo 'Add your test command here'"),
            ],
        ),
    },
)

app.add(ci, filename="ci.yml")
```

## 3. Customize

Edit the scaffold to match your project. Here are a few common modifications.

### Add a matrix strategy

```python
from ghagen import Strategy, Matrix

Job(
    runs_on="ubuntu-latest",
    strategy=Strategy(
        matrix=Matrix(
            include_extra={"python-version": ["3.11", "3.12", "3.13"]},
        ),
    ),
    steps=[
        checkout(),
        setup_python(python_version="${{ matrix.python-version }}"),
        Step(name="Test", run="pytest"),
    ],
)
```

### Use step helpers

ghagen provides factory functions for common actions so you don't have to remember exact action versions or input names:

```python
from ghagen.steps import checkout, setup_python, setup_node, cache

steps = [
    checkout(),
    setup_python(python_version="3.12"),
    cache(path="~/.cache/pip", key="pip-${{ hashFiles('requirements.txt') }}"),
    Step(name="Install", run="pip install -r requirements.txt"),
    Step(name="Test", run="pytest"),
]
```

## 4. Synthesize

Generate the YAML files:

```bash
ghagen synth
```

This reads your Python definitions and writes the corresponding YAML to `.github/workflows/`. The generated files include a header comment indicating they were produced by ghagen.

## 5. Keep in sync

Add a CI check to ensure your YAML files stay in sync with your Python definitions:

```bash
ghagen check
```

`ghagen check` exits with code 1 if any generated file differs from what the current definitions would produce. Add it to your CI workflow:

```python
Job(
    runs_on="ubuntu-latest",
    steps=[
        checkout(),
        setup_python(python_version="3.12"),
        Step(name="Install ghagen", run="pip install ghagen"),
        Step(name="Check workflows", run="ghagen check"),
    ],
)
```

## 6. Next steps

- [Concepts](concepts.md) -- Architecture and design principles
- [DRY Patterns](dry-patterns.md) -- Reuse techniques for workflows, jobs, and steps
- [Escape Hatches](escape-hatches.md) -- Handle anything the typed models don't cover
- [Comments](comments.md) -- Add comments to your generated YAML
- [CLI Reference](cli.md) -- Full command documentation
