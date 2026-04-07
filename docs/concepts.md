# Concepts

This page covers the architecture and design principles behind ghagen.

## Layer model

ghagen transforms your workflow definitions through three layers:

```
Python Models  -->  CommentedMap (ruamel.yaml)  -->  YAML string
```

1. **Python Models** -- Pydantic models (`Workflow`, `Job`, `Step`, etc.) that provide type checking, validation, and IDE autocompletion.
2. **CommentedMap** -- An intermediate representation from ruamel.yaml that preserves comments and key ordering. Each model's `to_commented_map()` method produces this structure.
3. **YAML string** -- The final output written to disk. ruamel.yaml emits YAML that retains comments and avoids unnecessary quoting.

This layered approach means you get full type safety in Python while still producing clean, human-readable YAML with comments.

## GhagenModel base class

All ghagen models inherit from `GhagenModel`, a Pydantic `BaseModel` subclass that adds YAML-specific capabilities:

- **`extras`** -- A dictionary of arbitrary key-value pairs injected into the YAML output. Use this when a model doesn't have a typed field for a key you need.
- **`post_process`** -- A callback that receives the `CommentedMap` before it is emitted, letting you make final modifications.
- **`comment`** -- A block comment rendered above the node in YAML.
- **`eol_comment`** -- An end-of-line comment rendered after the node's value.
- **`field_comments`** -- A dictionary mapping field names (by their YAML alias) to block comments rendered above that field.
- **`field_eol_comments`** -- A dictionary mapping field names (by their YAML alias) to EOL comments rendered after that field's value.

### Canonical key ordering

Each model defines a `_get_key_order()` class method that returns the preferred order of keys in the YAML output. This ensures generated files follow GitHub Actions conventions (e.g., `name` before `on`, `on` before `jobs`) regardless of the order you define fields in Python.

## App class

The `App` class follows a CDK-inspired synthesize pattern:

```python
from ghagen.app import App

app = App(outdir=".github/workflows")

app.add(ci_workflow, filename="ci.yml")
app.add(deploy_workflow, filename="deploy.yml")

app.synth()   # Write all YAML files to outdir
app.check()   # Verify files on disk match current definitions
```

- **`add(workflow, filename)`** -- Register a workflow with the app. The filename determines the output path within `outdir`.
- **`synth()`** -- Write all registered workflows to disk as YAML files.
- **`check()`** -- Compare the current definitions against the files on disk. Returns whether they match. Used in CI to detect when someone edits the YAML directly instead of updating the Python source.

## Escape hatches

ghagen provides four graduated escape hatches for situations where the typed models don't cover what you need. Each trades increasing flexibility for decreasing type safety:

| Mechanism | Type safety | Use case |
|---|---|---|
| `Raw[T]` | Bypasses constraints on a single field | Expression strings, custom enum values |
| `extras` | Untyped dict merged into output | Extra YAML keys not in the model |
| `post_process` | Callback on CommentedMap | Conditional logic, complex mutations |
| CommentedMap passthrough | No type checking | Fully custom YAML structures |

See the [Escape Hatches](escape-hatches.md) guide for detailed examples.

## Expression builder

ghagen includes an expression builder that generates GitHub Actions `${{ }}` expressions with Python syntax:

```python
from ghagen.expr import expr

expr.github.ref           # "${{ github.ref }}"
expr.github.event_name    # "${{ github.event_name }}"
expr.secrets.DEPLOY_TOKEN # "${{ secrets.DEPLOY_TOKEN }}"
expr.matrix.os            # "${{ matrix.os }}"
```

The builder supports function calls and operators, letting you construct expressions without manual string interpolation.

## Comment system

ghagen propagates comments through the entire layer model so they appear in the final YAML output. Comments are useful for documenting workflow intent, explaining non-obvious configuration, and adding context for maintainers who read the generated files.

Four types of comments are supported:

- **Block comments** -- Rendered on the line above a node.
- **End-of-line comments** -- Rendered after a node's value on the same line.
- **Field-level block comments** -- Rendered above a specific field within a model.
- **Field-level EOL comments** -- Rendered after a specific field's value.

Additionally, every generated file includes an auto-generated header comment indicating it was produced by ghagen.

See the [Comments](comments.md) guide for examples and known limitations.
