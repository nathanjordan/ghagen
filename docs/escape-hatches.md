# Escape Hatches

ghagen's typed models cover the most common GitHub Actions features, but the GitHub Actions schema is large and evolving. When you need something the models don't provide, ghagen offers four graduated escape hatches -- each trading increasing flexibility for decreasing type safety.

## 1. Raw[T] -- Bypass type constraints

`Raw[T]` wraps a value to bypass validation on a single field. The value is emitted as-is into the YAML output. Use this when a field has a constrained type (e.g., a `Literal` or `Enum`) but you need to pass an expression or a value outside the allowed set.

```python
from ghagen import Step, Job
from ghagen.models.raw import Raw

# Use an expression where a literal string is expected
Job(runs_on=Raw("${{ matrix.os }}"))

# Use a custom shell not in the predefined set
Step(name="Custom shell", run="echo hello", shell=Raw("custom-shell"))

# Pass a dynamic value
Step(uses=Raw("actions/checkout@${{ inputs.checkout-version }}"))
```

`Raw[T]` is the lightest escape hatch. It preserves type safety on all other fields and only bypasses the constraint on the specific field you wrap.

## 2. extras -- Inject arbitrary YAML keys

The `extras` dictionary lets you add key-value pairs that are merged into the model's YAML output. Use this when a model doesn't have a typed field for a key you need.

```python
from ghagen import Job

Job(
    runs_on="ubuntu-latest",
    extras={
        "timeout-minutes": 30,
        "continue-on-error": True,
    },
)
```

This produces:

```yaml
runs-on: ubuntu-latest
timeout-minutes: 30
continue-on-error: true
```

`extras` keys are added after the model's own fields. Values can be any type that ruamel.yaml can serialize -- strings, numbers, booleans, lists, or nested dicts.

## 3. post_process -- Modify the CommentedMap

The `post_process` callback receives the model's `CommentedMap` representation just before it is emitted. You can mutate it freely -- add keys, remove keys, reorder entries, or modify values.

```python
from ghagen import Workflow

def add_annotation(cm):
    cm["x-generated-by"] = "ghagen"

Workflow(
    name="Annotated",
    on=On(push=PushTrigger(branches=["main"])),
    jobs={"test": test_job},
    post_process=add_annotation,
)
```

`post_process` is powerful because you have full access to the intermediate representation. Use it for conditional logic, complex mutations, or anything that doesn't fit the declarative model:

```python
import os

def add_debug_step(cm):
    if os.environ.get("CI_DEBUG"):
        cm["jobs"]["test"]["steps"].insert(
            0, {"name": "Debug info", "run": "env | sort"}
        )

Workflow(..., post_process=add_debug_step)
```

## 4. CommentedMap passthrough -- Raw YAML structure

For maximum flexibility, you can pass a `CommentedMap` directly anywhere a model is expected. This bypasses the type system entirely and gives you full control over the YAML structure.

```python
from ruamel.yaml.comments import CommentedMap

cm_job = CommentedMap()
cm_job["runs-on"] = "ubuntu-latest"
cm_job["steps"] = [{"run": "echo 'raw job'"}]

Workflow(
    name="Mixed",
    on=On(push=PushTrigger(branches=["main"])),
    jobs={
        "raw": cm_job,
        "typed": Job(
            runs_on="ubuntu-latest",
            steps=[Step(uses="actions/checkout@v4")],
        ),
    },
)
```

You can mix typed models and raw `CommentedMap` objects in the same workflow. The typed models are converted to `CommentedMap` during synthesis, so they coexist seamlessly.

## When to use which

Use this decision guide to pick the right escape hatch:

| Situation | Escape hatch |
|---|---|
| A field rejects your value (expression, custom enum) | `Raw[T]` |
| You need a YAML key that has no corresponding model field | `extras` |
| You need conditional logic or complex mutations at synthesis time | `post_process` |
| You need full control over a section of YAML | CommentedMap passthrough |

**Start with `Raw[T]`** and escalate only if it doesn't solve your problem. The lighter the escape hatch, the more type safety and IDE support you retain.
