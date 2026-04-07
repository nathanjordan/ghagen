# Comments

ghagen propagates comments through the entire generation pipeline so they appear in the final YAML output. This is useful for documenting intent, explaining non-obvious configuration, and adding context for anyone reading the generated files.

## Comment types

### Block comments

Set the `comment` field on any model to render a comment above that node in the YAML output:

```python
Job(
    name="Test",
    runs_on="ubuntu-latest",
    comment="Run the full test suite against all supported Python versions",
    steps=[...],
)
```

### End-of-line comments

Set the `eol_comment` field to render a comment after the node's value on the same line:

```python
Step(
    name="Ruff",
    run="ruff check .",
    eol_comment="fast Python linter",
)
```

### Field-level block comments

Use `field_comments` to add a comment above a specific field. Keys are the field's YAML alias (the key as it appears in the output):

```python
Workflow(
    name="CI",
    on=On(push=PushTrigger(branches=["main"])),
    field_comments={"name": "The name shown in the GitHub UI"},
    jobs={...},
)
```

### Field-level EOL comments

Use `field_eol_comments` to add an end-of-line comment after a specific field's value:

```python
Workflow(
    name="CI",
    on=On(push=PushTrigger(branches=["main"])),
    field_eol_comments={"on": "trigger configuration"},
    jobs={...},
)
```

## Full example

Here is a workflow that uses all four comment types:

```python
Workflow(
    name="Commented Workflow",
    on=On(push=PushTrigger(branches=["main"])),
    field_comments={"name": "The name shown in the GitHub UI"},
    field_eol_comments={"on": "trigger configuration"},
    jobs={
        "lint": Job(
            name="Lint",
            runs_on="ubuntu-latest",
            comment="Run linters before tests",
            steps=[
                Step(uses="actions/checkout@v4"),
                Step(
                    name="Ruff",
                    run="ruff check .",
                    eol_comment="fast Python linter",
                ),
            ],
        ),
    },
)
```

This produces the following YAML:

```yaml
# The name shown in the GitHub UI
name: Commented Workflow
on: # trigger configuration
  push:
    branches:
    - main
jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    -  # fast Python linter
      name: Ruff
      run: ruff check .
```

## Header comments

Every generated file includes an auto-generated header comment at the top indicating it was produced by ghagen. This helps maintainers understand that the file should not be edited directly.

## Known limitations

**EOL comments on map sequence items**: When a step (or other map item in a sequence) has an `eol_comment`, it renders on a separate line rather than truly at the end of the first line. This is due to how ruamel.yaml handles comments on mapping nodes within sequences. The comment still appears in the output and is associated with the correct node, but its visual placement is slightly different from a true end-of-line comment.
