# FAQ

Quick answers to questions that come up when using ghagen.

## Why use ghagen instead of writing YAML directly?

Three reasons, in rough order of impact:

1. **Type safety and IDE autocomplete.** Typing `Job(` in an editor gives you
   every field with the right type. Typos in action input names fail at
   `ghagen synth` rather than at workflow runtime.
2. **DRY.** Plain Python loops, functions, and constants work for free.
   Stamping out ten similar jobs is a list comprehension, not ten YAML
   blocks.
3. **Linting and pinning.** `ghagen lint` flags missing permissions,
   unpinned actions, missing timeouts, and duplicate step ids at the exact
   line that constructed the offending model. `ghagen pin` locks every
   action to a commit SHA.

If your workflows are short and static, plain YAML is fine. If they grow,
ghagen pays for itself quickly.

## Why are my keys reordered in the generated YAML?

ghagen emits the canonical GitHub Actions key order (`name` → `on` →
`permissions` → `jobs`, and so on) regardless of how you order fields in
Python. Your field order in a model doesn't matter for output — pick
whichever order reads best in your source.

## `ghagen check` is failing in CI. How do I fix it?

Run `ghagen synth` locally, commit the regenerated YAML, and push. `ghagen
check` just compares the current Python definitions against the committed
YAML and reports any drift. The usual cause is someone hand-editing a file
under `.github/workflows/` or forgetting to re-synth after changing
`ghagen_workflows.py`.

## How do I add a GitHub Actions key the model doesn't cover?

Use the `extras` dict on the model. Keys and values are passed through to
the YAML output:

```python
Job(
    runs_on="ubuntu-latest",
    extras={"continue-on-error": True, "timeout-minutes": 30},
)
```

See [Escape Hatches](escape-hatches.md) for the full hierarchy.

## How do I use an expression where a literal value is expected?

Wrap the value in `Raw`. This bypasses validation on that single field
without affecting the rest of the model:

```python
from ghagen import Job, Raw

Job(runs_on=Raw("${{ matrix.os }}"))
```

This is the lightest escape hatch — everything else on the job stays fully
typed.

## How do I pin actions to commit SHAs?

Run `ghagen pin` to populate `.github/ghagen.lock.toml`. On subsequent
`ghagen synth` calls, every `uses:` is rewritten to its pinned SHA. Wire
`ghagen pin --check --prune` into CI to catch unpinned additions.

```bash
ghagen pin          # First-time population
ghagen pin --check  # Verify in CI (no network calls)
ghagen pin --update # Periodically refresh to latest SHAs
```

See the [CLI Reference](cli.md#ghagen-pin).

## Can I use ghagen for composite actions?

Yes. Define an `Action` with `CompositeRuns` and register it with
`app.add_action()`:

```python
from ghagen import Action, CompositeRuns, Step, App

my_action = Action(
    name="My Action",
    description="Do the thing",
    runs=CompositeRuns(steps=[Step(run="./do-it.sh", shell="bash")]),
)

app = App()
app.add_action(my_action)   # writes ./action.yml
```

Actions and workflows can share the same `App`. See the "Composite action
alongside your workflows" recipe in the [Cookbook](cookbook.md).

## How do I debug the YAML a workflow will produce?

Call `to_yaml()` directly on the model from a Python REPL:

```python
>>> from my_workflows import ci
>>> print(ci.to_yaml())
```

Or just `ghagen synth` and inspect the file under `.github/workflows/`.

## Can I mix ghagen-generated workflows with hand-written YAML?

Yes. ghagen only touches files you register with `app.add_workflow()` or
`app.add_action()`. Any other file in `.github/workflows/` is left alone —
add a hand-written `weekly-report.yml` next to a ghagen-generated `ci.yml`
and nothing breaks. `ghagen check` and `ghagen lint` similarly only reason
about workflows defined in your Python source.

## Why does `ghagen lint` warn about missing permissions by default?

GitHub's default `GITHUB_TOKEN` is granted broad write scopes. Setting an
explicit `permissions` block on your workflow (or on each job) restricts
the token to what you actually need, which is the hardening posture OWASP
recommends. Set a top-level `permissions=Permissions(contents="read")`
and grant more only where needed:

```python
from ghagen import Permissions, Workflow

Workflow(
    name="CI",
    permissions=Permissions(contents="read"),
    # ...
)
```

## Why is my `eol_comment` on a step rendering on its own line?

This is a known ruamel.yaml limitation for EOL comments on mapping items
inside sequences. The comment is still attached to the right step — it
just appears on its own line instead of at the end of the first line. See
the Known Limitations section of [Comments](comments.md#known-limitations).
