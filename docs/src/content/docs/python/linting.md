---
title: Linting
description: Rule-based checks for ghagen workflow definitions
---

`ghagen lint` runs rule-based checks against your workflow definitions
**at the Python source level**. Violations point at the exact line in
your `ghagen_workflows.py` that constructed the offending model -- not a
line number in a generated file -- so you can jump straight to the fix.

This is complementary to tools like
[actionlint](https://github.com/rhysd/actionlint), which lints the
generated `.yml` files. Use actionlint for YAML-level concerns (shell
syntax, action input types) and `ghagen lint` for ghagen-idiomatic
concerns.

## Running

```bash
# Lint using your .github/ghagen_workflows.py
ghagen lint

# List all available rules and exit
ghagen lint --list-rules

# JSON output for scripts and CI
ghagen lint --format=json

# GitHub Actions annotations (for use inside CI)
ghagen lint --format=github

# Disable a rule from the command line
ghagen lint --disable missing-timeout
```

Exit codes:

| Code | Meaning                                                      |
| ---- | ------------------------------------------------------------ |
| `0`  | No error-severity violations (warnings may still be present) |
| `1`  | At least one error-severity violation found                  |
| `2`  | Configuration error (malformed YAML, unknown severity, etc.) |

## Built-in rules

### `missing-permissions` (warning)

Flags workflows with no top-level `permissions` set and no per-job
`permissions` either. GitHub's default `GITHUB_TOKEN` has broad write
access; setting an explicit `permissions` block is the OWASP-recommended
hardening.

```python
# Triggers the rule
Workflow(
    name="ci",
    jobs={"build": Job(runs_on="ubuntu-latest", steps=[...])},
)

# Passes
Workflow(
    name="ci",
    permissions=Permissions(contents="read"),
    jobs={"build": Job(runs_on="ubuntu-latest", steps=[...])},
)
```

### `missing-timeout` (warning)

Flags jobs without `timeout_minutes`. GitHub's default job timeout is 6
hours; setting an explicit shorter timeout bounds runaway builds. Jobs
that reference a reusable workflow via `uses` are skipped (their timeout
is owned by the reusable workflow).

```python
# Triggers the rule
Job(runs_on="ubuntu-latest", steps=[...])

# Passes
Job(runs_on="ubuntu-latest", timeout_minutes=10, steps=[...])
```

### `duplicate-step-ids` (error)

Flags two or more steps within a single job that share the same `id`.
GitHub Actions requires step ids to be unique within a job; duplicates
break `steps.<id>.outputs` references because the expression silently
resolves to just one of the matching steps. Step ids are scoped per-job,
so the same id in two different jobs is fine.

Severity is `error` (not warning) because this is a correctness bug, not
a hardening concern -- `ghagen lint` exits with code 1 when any
duplicates are found.

```python
# Triggers the rule
Job(
    runs_on="ubuntu-latest",
    steps=[
        Step(id="build", run="make"),
        Step(id="build", run="make test"),  # duplicate!
    ],
)

# Passes
Job(
    runs_on="ubuntu-latest",
    steps=[
        Step(id="build", run="make"),
        Step(id="test", run="make test"),
    ],
)
```

## Configuration

Lint behavior is configured via a YAML file at the repo root:

**`.ghagen.yml`**

```yaml
# .ghagen.yml
lint:
  disable:
    - missing-timeout
  severity:
    missing-permissions: error
```

CLI flags layer on top of the config file:

```bash
# Union with any disables in the config file
ghagen lint --disable missing-permissions
```

## CI integration

Add `ghagen lint` to your pipeline with `--format=github` to get inline
PR annotations:

```python
from ghagen import Job, Step

Job(
    name="Lint",
    runs_on="ubuntu-latest",
    timeout_minutes=10,
    steps=[
        Step(name="Checkout", uses="actions/checkout@v6"),
        Step(name="Set up uv", uses="astral-sh/setup-uv@v7"),
        Step(name="Sync", run="uv sync"),
        Step(
            name="ghagen lint",
            run="uv run ghagen lint --format=github",
        ),
    ],
)
```

## What's not covered

The following are intentionally out of scope for v1:

- **YAML-level linting** -- use `actionlint` for that.
- **User-defined rules** -- all rules are built-in. A public rule API may
  come later once the built-in rule shape is proven.
