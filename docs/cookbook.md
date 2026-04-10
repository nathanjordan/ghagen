# Cookbook

Practical recipes for common workflow patterns. Every snippet is valid Python against the current ghagen API — copy, adapt, and run `ghagen synth`.

## Matrix build across Python versions

Run the same job against multiple Python versions. Dynamic matrix dimensions
go in `Matrix.extras`; `include` and `exclude` are typed fields.

```python
from ghagen import Job, Matrix, Step, Strategy, checkout, setup_python

test = Job(
    name="Test (Python ${{ matrix.python-version }})",
    runs_on="ubuntu-latest",
    timeout_minutes=15,
    strategy=Strategy(
        matrix=Matrix(
            extras={"python-version": ["3.11", "3.12", "3.13"]},
        ),
    ),
    steps=[
        checkout(),
        setup_python(version="${{ matrix.python-version }}"),
        Step(name="Install", run="pip install -e '.[dev]'"),
        Step(name="Test", run="pytest"),
    ],
)
```

## Matrix over multiple OSes

`runs_on` is typed as a string, so an expression needs `Raw` to get through.
`exclude` trims unwanted combinations.

```python
from ghagen import Job, Matrix, Raw, Step, Strategy, checkout, setup_python

Job(
    name="Cross-platform test",
    runs_on=Raw("${{ matrix.os }}"),
    timeout_minutes=20,
    strategy=Strategy(
        matrix=Matrix(
            extras={
                "os": ["ubuntu-latest", "macos-latest", "windows-latest"],
                "python-version": ["3.11", "3.12", "3.13"],
            },
            exclude=[
                {"os": "windows-latest", "python-version": "3.11"},
            ],
        ),
    ),
    steps=[
        checkout(),
        setup_python(version="${{ matrix.python-version }}"),
        Step(name="Test", run="pytest"),
    ],
)
```

## Cache dependencies

`cache()` takes `key` and `path` as positional-friendly kwargs. `restore_keys`
accepts a list and is joined with newlines on emission.

```python
from ghagen import Step, cache, checkout, setup_python

steps = [
    checkout(),
    setup_python(version="3.12"),
    cache(
        key="pip-${{ hashFiles('requirements.txt') }}",
        path="~/.cache/pip",
        restore_keys=["pip-"],
    ),
    Step(name="Install", run="pip install -r requirements.txt"),
    Step(name="Test", run="pytest"),
]
```

## Job dependencies with `needs`

A downstream job lists its upstream dependencies with `needs` (string or list
of strings) and can read their outputs via `needs.<job>.outputs.*`.

```python
from ghagen import Job, Step, checkout

jobs = {
    "build": Job(
        runs_on="ubuntu-latest",
        timeout_minutes=10,
        outputs={"version": "${{ steps.ver.outputs.value }}"},
        steps=[
            checkout(),
            Step(
                id="ver",
                name="Compute version",
                run="echo 'value=1.2.3' >> $GITHUB_OUTPUT",
            ),
        ],
    ),
    "release": Job(
        runs_on="ubuntu-latest",
        needs="build",
        if_="github.ref == 'refs/heads/main'",
        timeout_minutes=10,
        steps=[
            Step(run="echo Releasing ${{ needs.build.outputs.version }}"),
        ],
    ),
}
```

## Pass artifacts between jobs

Use `upload_artifact` in the producer and `download_artifact` in the
consumer. `needs` ensures the producer finishes first.

```python
from ghagen import Job, Step, checkout, download_artifact, upload_artifact

jobs = {
    "build": Job(
        runs_on="ubuntu-latest",
        timeout_minutes=15,
        steps=[
            checkout(),
            Step(name="Build wheel", run="python -m build"),
            upload_artifact(name="dist", path="dist/"),
        ],
    ),
    "publish": Job(
        runs_on="ubuntu-latest",
        needs="build",
        timeout_minutes=10,
        steps=[
            download_artifact(name="dist", path="dist/"),
            Step(name="Publish", run="twine upload dist/*"),
        ],
    ),
}
```

## Use secrets and environment variables

`expr.secrets["NAME"]` renders as `${{ secrets.NAME }}`. Wrap it in `str()`
when assigning to a typed `dict[str, str]` field like `env`.

```python
from ghagen import Job, Step, checkout, expr

Job(
    name="Publish release notes",
    runs_on="ubuntu-latest",
    timeout_minutes=10,
    env={
        "GH_TOKEN": str(expr.secrets["GITHUB_TOKEN"]),
        "RELEASE_CHANNEL": "stable",
    },
    steps=[
        checkout(),
        Step(
            name="Comment on release",
            run="gh release edit ${{ github.ref_name }} --notes-file NOTES.md",
        ),
    ],
)
```

Prefer `expr.secrets[...]` over hand-written `"${{ secrets.FOO }}"` strings —
it keeps typos in secret names out of your workflows and renames ripple
through your Python.

## Scheduled (cron) workflows

`ScheduleTrigger(cron=...)` entries go into `On.schedule` as a list. You can
combine them with a `WorkflowDispatchTrigger` to allow manual runs too.

```python
from ghagen import (
    Job,
    On,
    ScheduleTrigger,
    Step,
    Workflow,
    WorkflowDispatchTrigger,
    checkout,
)

nightly = Workflow(
    name="Nightly Build",
    on=On(
        schedule=[ScheduleTrigger(cron="0 9 * * *")],
        workflow_dispatch=WorkflowDispatchTrigger(),
    ),
    jobs={
        "build": Job(
            runs_on="ubuntu-latest",
            timeout_minutes=30,
            steps=[
                checkout(),
                Step(name="Nightly build", run="make nightly"),
            ],
        ),
    },
)
```

## Reusable workflows with `workflow_call`

Define a workflow that accepts `workflow_call` inputs and reference it from
another workflow by passing `uses:` on a job.

**Callee** (`.github/workflows/deploy.yml`):

```python
from ghagen import (
    Job,
    On,
    Permissions,
    Step,
    Workflow,
    WorkflowCallTrigger,
    checkout,
)
from ghagen.models.trigger import WorkflowCallInput

deploy = Workflow(
    name="Deploy",
    on=On(
        workflow_call=WorkflowCallTrigger(
            inputs={
                "environment": WorkflowCallInput(
                    description="Target environment",
                    required=True,
                    type="string",
                ),
            },
        ),
    ),
    permissions=Permissions(contents="read", id_token="write"),
    jobs={
        "deploy": Job(
            runs_on="ubuntu-latest",
            environment="${{ inputs.environment }}",
            timeout_minutes=15,
            steps=[
                checkout(),
                Step(name="Deploy", run="./deploy.sh"),
            ],
        ),
    },
)
```

**Caller** — a job that references the reusable workflow via `uses`:

```python
from ghagen import Job, expr

release = Job(
    name="Deploy to production",
    uses="./.github/workflows/deploy.yml",
    with_={"environment": "production"},
    secrets={"DEPLOY_KEY": str(expr.secrets["DEPLOY_KEY"])},
)
```

`uses` on a `Job` is the reusable-workflow shorthand; such a job has no
`steps` of its own and inherits its runner from the callee.

## Conditional jobs and steps

`if_` (Python-safe alias for `if`) works on both `Job` and `Step`.

```python
from ghagen import Job, Step, checkout

Job(
    name="Deploy",
    runs_on="ubuntu-latest",
    timeout_minutes=15,
    if_="github.event_name == 'push' && github.ref == 'refs/heads/main'",
    steps=[
        checkout(),
        Step(name="Build", run="make build"),
        Step(
            name="Smoke test (main only)",
            run="./smoke-test.sh",
            if_="github.ref == 'refs/heads/main'",
        ),
    ],
)
```

## Composite action alongside your workflows

`App` can emit composite actions as well as workflows. Use `app.add_action()`
and the action is written to `action.yml` (or `<dir>/action.yml`) next to
your repo root.

```python
from ghagen import (
    Action,
    ActionInput,
    App,
    Branding,
    CompositeRuns,
    Step,
)

check_action = Action(
    name="My Check",
    description="Run the project's canonical checks",
    branding=Branding(icon="check-circle", color="green"),
    inputs={
        "config": ActionInput(
            description="Path to config file",
            required=False,
            default="config.toml",
        ),
    },
    runs=CompositeRuns(
        steps=[
            Step(
                name="Run checks",
                run='mycheck --config "${{ inputs.config }}"',
                shell="bash",
            ),
        ],
    ),
)

app = App()
app.add_action(check_action)   # -> ./action.yml
```

Use this pattern when you want one file to be the source of truth for both
your CI workflows *and* the composite action other repos consume.
