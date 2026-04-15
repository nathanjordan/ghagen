---
title: Helpers
description: Step factory functions, the expression builder, and utility types for building workflows.
---

ghagen provides helper functions and types that simplify common workflow patterns. These include pre-built step factories for popular actions, a fluent expression builder, and escape-hatch types.

## Step factory functions

Factory functions that create pre-configured `Step` objects for commonly used GitHub Actions. All functions accept `**kwargs` which are forwarded to the `Step` constructor, allowing you to set `name`, `if_`, `env`, and other step parameters. A `with_` dict in kwargs is merged with the built-in parameters.

Import from `ghagen.helpers.steps`:

```python
from ghagen.helpers.steps import checkout, setup_python, setup_node
```

### `checkout(**kwargs) -> Step`

Creates a checkout step using `actions/checkout@v4`.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `ref` | `str \| None` | `None` | Git reference to check out (branch, tag, or SHA). Defaults to the triggering ref. |
| `fetch_depth` | `int \| None` | `1` | Number of commits to fetch. Set to `0` for a full clone. |
| `**kwargs` | | | Additional `Step` parameters (e.g., `name`, `if_`, `env`). |

```python
from ghagen.helpers.steps import checkout

step = checkout()                          # shallow clone
step = checkout(ref="develop")             # specific branch
step = checkout(fetch_depth=0)             # full clone
step = checkout(name="Checkout code")      # custom name
```

### `setup_python(version, **kwargs) -> Step`

Creates a Python setup step using `actions/setup-python@v5`.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `version` | `str` | required | Python version string (e.g., `"3.12"`). |
| `cache` | `str \| None` | `None` | Package manager to cache (e.g., `"pip"`, `"uv"`). |
| `**kwargs` | | | Additional `Step` parameters. |

```python
from ghagen.helpers.steps import setup_python

step = setup_python("3.12")
step = setup_python("3.12", cache="pip")
step = setup_python("${{ matrix.python-version }}")
```

### `setup_node(version, **kwargs) -> Step`

Creates a Node.js setup step using `actions/setup-node@v4`.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `version` | `str` | required | Node.js version string (e.g., `"20"`). |
| `cache` | `str \| None` | `None` | Package manager to cache (e.g., `"npm"`, `"yarn"`, `"pnpm"`). |
| `**kwargs` | | | Additional `Step` parameters. |

```python
from ghagen.helpers.steps import setup_node

step = setup_node("20")
step = setup_node("20", cache="npm")
```

### `setup_uv(**kwargs) -> Step`

Creates a uv setup step using `astral-sh/setup-uv@v4`.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `version` | `str \| None` | `None` | Specific uv version to install. If `None`, uses the latest release. |
| `**kwargs` | | | Additional `Step` parameters. |

```python
from ghagen.helpers.steps import setup_uv

step = setup_uv()
step = setup_uv(version="0.6.0")
```

### `cache(key, path, **kwargs) -> Step`

Creates a cache step using `actions/cache@v4`.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `key` | `str` | required | Cache key (e.g., `"${{ runner.os }}-pip-${{ hashFiles('...') }}"`). |
| `path` | `str` | required | Path(s) to cache. |
| `restore_keys` | `str \| list[str] \| None` | `None` | Fallback key(s) for partial cache matches. A list is joined with newlines. |
| `**kwargs` | | | Additional `Step` parameters. |

```python
from ghagen.helpers.steps import cache

step = cache(
    key="${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}",
    path="~/.cache/pip",
    restore_keys=["${{ runner.os }}-pip-"],
)
```

### `upload_artifact(name, path, **kwargs) -> Step`

Creates an upload step using `actions/upload-artifact@v4`.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `name` | `str` | required | Name for the artifact. |
| `path` | `str` | required | File or directory path to upload. |
| `**kwargs` | | | Additional `Step` parameters. |

```python
from ghagen.helpers.steps import upload_artifact

step = upload_artifact("coverage", "coverage/")
```

### `download_artifact(name, **kwargs) -> Step`

Creates a download step using `actions/download-artifact@v4`.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `name` | `str` | required | Name of the artifact to download. |
| `path` | `str \| None` | `None` | Destination path. Defaults to the workspace directory. |
| `**kwargs` | | | Additional `Step` parameters. |

```python
from ghagen.helpers.steps import download_artifact

step = download_artifact("coverage", path="./coverage")
```

---

## Expression builder

The `expr` singleton provides a fluent API for building GitHub Actions `${{ }}` expressions with Python syntax.

```python
from ghagen import expr
```

### Property access

Dot notation builds expression paths. Convert to string with `str()` or use directly in fields that accept strings.

```python
str(expr.github.ref)              # "${{ github.ref }}"
str(expr.github.event.action)     # "${{ github.event.action }}"
str(expr.runner.os)               # "${{ runner.os }}"
```

### Indexing

Bracket notation accesses dynamic keys, useful for contexts like `secrets` and `matrix`.

```python
str(expr.secrets["PYPI_TOKEN"])   # "${{ secrets.PYPI_TOKEN }}"
str(expr.matrix["python-version"])# "${{ matrix.python-version }}"
```

### Function calls

Call expressions as functions to produce GitHub Actions function syntax.

```python
str(expr.contains(expr.github.ref, "refs/tags/"))
# "${{ contains(github.ref, 'refs/tags/') }}"

str(expr.hashFiles("**/requirements.txt"))
# "${{ hashFiles('**/requirements.txt') }}"

str(expr.success())               # "${{ success() }}"
str(expr.failure())               # "${{ failure() }}"
str(expr.always())                # "${{ always() }}"
```

### Comparison operators

Standard Python comparison operators produce expression syntax.

```python
str(expr.github.ref == "refs/heads/main")
# "${{ github.ref == 'refs/heads/main' }}"

str(expr.github.event_name != "pull_request")
# "${{ github.event_name != 'pull_request' }}"
```

### Boolean operators

Use `&` (and), `|` (or), and `~` (not) for boolean logic. Note: these are bitwise operators in Python, not `and`/`or`/`not`.

```python
str(expr.github.ref & expr.github.event)
# "${{ github.ref && github.event }}"

str(expr.github.ref | expr.github.event)
# "${{ github.ref || github.event }}"

str(~expr.github.event.pull_request)
# "${{ !github.event.pull_request }}"
```

---

## Raw\[T\]

An escape hatch that bypasses type constraints, emitting the inner value as-is into the YAML output. Use this to pass values that aren't covered by the library's typed enums or Literal constraints.

```python
from ghagen import Raw
```

### Constructor

```python
Raw(value: T)
```

| Argument | Type | Description |
|----------|------|-------------|
| `value` | `T` | The value to emit verbatim. |

### Usage

```python
from ghagen import Step, Job, Raw

# Use a shell type not in the ShellType enum
step = Step(run="echo hello", shell=Raw("future-shell"))

# Use a custom runner label
job = Job(runs_on=Raw("self-hosted"))

# Use with permissions
from ghagen.models.permissions import Permissions
perm = Permissions(actions=Raw("admin"))
```

`Raw[T]` wraps any value and passes it through Pydantic validation unchanged. During serialization, `Raw[str]` values are emitted as plain YAML scalars (not block scalars), preserving the exact string.

---

## ExpressionStr

A `str` subclass that marks a value as a GitHub Actions expression (`${{ ... }}`). This is used internally by the expression builder.

```python
from ghagen.models.common import ExpressionStr
```

### Class method

#### `ExpressionStr.wrap(expr: str) -> ExpressionStr`

Wraps a bare expression in `${{ }}` delimiters. If the string is already wrapped, returns it unchanged.

```python
ExpressionStr.wrap("github.ref")          # "${{ github.ref }}"
ExpressionStr.wrap("${{ github.ref }}")   # "${{ github.ref }}" (unchanged)
```
