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

from ghagen import App, Job, On, PRTrigger, PushTrigger, Step, Workflow

app = App()

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

app.add_workflow(ci, "ci.yml")
```

`App()` defaults to the current directory as the repository root, and `add_workflow` writes to `.github/workflows/<filename>` relative to it.

## 3. Customize

Edit the scaffold to match your project. Here are a few common modifications.

### Use step helpers

ghagen provides factory functions for common actions so you don't have to remember exact action versions or input names:

```python
from ghagen import Step, cache, checkout, setup_python

steps = [
    checkout(),
    setup_python(version="3.12"),
    cache(
        key="pip-${{ hashFiles('requirements.txt') }}",
        path="~/.cache/pip",
    ),
    Step(name="Install", run="pip install -r requirements.txt"),
    Step(name="Test", run="pytest"),
]
```

### Add a matrix strategy

```python
from ghagen import Job, Matrix, Step, Strategy, checkout, setup_python

Job(
    runs_on="ubuntu-latest",
    strategy=Strategy(
        matrix=Matrix(
            extras={"python-version": ["3.11", "3.12", "3.13"]},
        ),
    ),
    steps=[
        checkout(),
        setup_python(version="${{ matrix.python-version }}"),
        Step(name="Test", run="pytest"),
    ],
)
```

`Matrix.extras` holds the dynamic dimensions (anything that isn't `include` or `exclude`). See the [Cookbook](cookbook.md) for more matrix recipes.

## 4. Synthesize

Generate the YAML files:

```bash
ghagen synth
```

This reads your Python definitions and writes the corresponding YAML to `.github/workflows/`. Each generated file starts with a header comment indicating it was produced by ghagen.

## 5. Keep in sync

Add a CI check to ensure your YAML files stay in sync with your Python definitions:

```bash
ghagen check-synced
```

`ghagen check-synced` exits with code 1 if any generated file differs from what the current definitions would produce. Add it to your CI workflow:

```python
from ghagen import Job, Step, checkout, setup_python

Job(
    runs_on="ubuntu-latest",
    steps=[
        checkout(),
        setup_python(version="3.12"),
        Step(name="Install ghagen", run="pip install ghagen"),
        Step(name="Check workflows", run="ghagen check-synced"),
    ],
)
```

## 6. Next steps

- [Cookbook](cookbook.md) -- Recipes for matrix builds, caching, secrets, reusable workflows, and more
- [DRY Patterns](dry-patterns.md) -- Reuse techniques for workflows, jobs, and steps
- [Escape Hatches](escape-hatches.md) -- Handle anything the typed models don't cover
- [Comments](comments.md) -- Add comments to your generated YAML
- [Linting](linting.md) -- Catch common mistakes in your Python definitions
- [CLI Reference](cli.md) -- Full command documentation
- [FAQ](faq.md) -- Common questions
