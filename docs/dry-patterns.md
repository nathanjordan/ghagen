# DRY Patterns

ghagen definitions are plain Python, so standard techniques for reducing duplication work naturally. This guide covers common patterns for keeping your workflow code concise and maintainable.

## Step factories

ghagen ships with factory functions for frequently used GitHub Actions. Each returns a `Step` instance and accepts `**kwargs` that are passed through to the `Step` constructor, so you can add `if` conditions, environment variables, or any other field.

```python
from ghagen import (
    cache,
    checkout,
    download_artifact,
    setup_node,
    setup_python,
    setup_uv,
    upload_artifact,
)
```

### Usage

```python
steps = [
    checkout(),
    setup_python(version="3.12"),
    cache(key="pip-${{ hashFiles('requirements.txt') }}", path="~/.cache/pip"),
    Step(name="Install deps", run="pip install -r requirements.txt"),
    Step(name="Test", run="pytest"),
    upload_artifact(name="coverage", path="htmlcov/"),
]
```

### Passing extra fields

Since factories forward `**kwargs` to `Step`, you can add any supported field:

```python
checkout(name="Checkout with submodules", with_={"submodules": "recursive"})
setup_python(version="3.12", if_="github.event_name == 'push'")
```

## Job template functions

Define a function that returns a `Job` to create reusable job templates:

```python
from ghagen import Job, Step, checkout

def lint_job(tool: str, cmd: str) -> Job:
    return Job(
        name=f"Lint ({tool})",
        runs_on="ubuntu-latest",
        steps=[
            checkout(),
            Step(name=tool, run=cmd),
        ],
    )
```

Use it to stamp out multiple jobs without repeating the structure:

```python
jobs = {
    "ruff": lint_job("Ruff", "ruff check ."),
    "mypy": lint_job("Mypy", "mypy src/"),
    "black": lint_job("Black", "black --check ."),
}
```

You can parameterize anything -- runner labels, Python versions, dependency install commands, or entire step lists.

## Shared constants

Extract repeated values into Python variables to ensure consistency and simplify updates:

```python
RUNNER = "ubuntu-latest"
PYTHON_VERSION = "3.12"
CHECKOUT_ACTION = "actions/checkout@v4"
SETUP_PYTHON_ACTION = "actions/setup-python@v5"

Job(
    runs_on=RUNNER,
    steps=[
        Step(uses=CHECKOUT_ACTION),
        Step(uses=SETUP_PYTHON_ACTION, with_={"python-version": PYTHON_VERSION}),
    ],
)
```

When a new action version is released, update the constant in one place.

## Loops

Use list comprehensions to generate repetitive structures:

```python
services = ["api", "web", "worker"]

jobs = {
    f"build-{svc}": Job(
        name=f"Build {svc}",
        runs_on="ubuntu-latest",
        steps=[
            checkout(),
            Step(name="Build", run=f"docker build -t {svc} ./services/{svc}"),
        ],
    )
    for svc in services
}
```

This works equally well for generating step lists:

```python
linters = [("ruff", "ruff check ."), ("mypy", "mypy src/")]

steps = [checkout()] + [
    Step(name=name, run=cmd) for name, cmd in linters
]
```

## Composable workflows

You are not limited to a single file. Split workflow definitions across modules and register them all with the same `App`:

```python
# .github/ghagen_workflows.py
from ghagen import App
from .ci import ci_workflow
from .deploy import deploy_workflow
from .release import release_workflow

app = App()

app.add_workflow(ci_workflow, "ci.yml")
app.add_workflow(deploy_workflow, "deploy.yml")
app.add_workflow(release_workflow, "release.yml")
```

Each module defines and exports its own `Workflow` object. This keeps individual files focused and easy to navigate, while the top-level file serves as the manifest of all generated workflows.

You can also share helper functions, step lists, and job templates across modules by importing from a common utilities module:

```python
# .github/common.py
from ghagen import Step, checkout, setup_python

RUNNER = "ubuntu-latest"

def python_setup_steps(version: str = "3.12"):
    return [
        checkout(),
        setup_python(version=version),
        Step(name="Install deps", run="pip install -e '.[dev]'"),
    ]
```
