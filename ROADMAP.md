# ghagen Roadmap

## What's Done

Steps 1-5 of the original plan are complete:

- **Project scaffolding** — uv + hatchling, src layout, ruff/pyright, pre-commit
- **YAML emitter** — ruamel.yaml with CommentedMap, canonical key ordering, comment attachment
- **Domain models** — Workflow, Job, Step, On/triggers, Permissions, Container, Strategy/Matrix, common types
- **Escape hatches** — `Raw[T]`, `extras`, `post_process` callback, `CommentedMap` passthrough
- **App class** — `synth()` and `check()` for multi-workflow synthesis
- **CLI** — `ghagen synth`, `ghagen check`, `ghagen init` via Typer
- **Tests** — 32 passing (models, emitter, CLI)

---

## Milestone 1: DRY Helpers

**Goal:** Ship reusable step factories and expression builders so users get immediate value from common patterns.

### 1.1 Step Factory Functions

**File:** `src/ghagen/helpers/steps.py`

Provide pre-built factory functions for the most common GitHub Actions steps. Each returns a typed `Step` instance.

```python
from ghagen.helpers.steps import checkout, setup_python, setup_uv, cache

# Usage
Job(steps=[
    checkout(),
    setup_python("3.12"),
    setup_uv(),
    cache("pip", path="~/.cache/pip", key="..."),
    Step(name="Test", run="pytest"),
])
```

Functions to implement:

| Function | Action | Key `with` params |
|---|---|---|
| `checkout(ref=None, fetch_depth=1)` | `actions/checkout@v4` | `ref`, `fetch-depth` |
| `setup_python(version, cache=None)` | `actions/setup-python@v5` | `python-version`, `cache` |
| `setup_node(version, cache=None)` | `actions/setup-node@v4` | `node-version`, `cache` |
| `setup_uv(version=None)` | `astral-sh/setup-uv@v4` | `version` |
| `cache(key, path, restore_keys=None)` | `actions/cache@v4` | `key`, `path`, `restore-keys` |
| `upload_artifact(name, path)` | `actions/upload-artifact@v4` | `name`, `path` |
| `download_artifact(name, path=None)` | `actions/download-artifact@v4` | `name`, `path` |

Each function should accept `**kwargs` and forward to `Step(...)` so users can override or add `comment`, `if_`, `env`, etc.

### 1.2 Expression Helpers

**File:** `src/ghagen/helpers/expressions.py`

Provide a safe builder for GitHub Actions `${{ }}` expressions, avoiding string typos.

```python
from ghagen.helpers.expressions import expr

# Attribute access builds dot-separated paths
expr.github.ref           # "${{ github.ref }}"
expr.github.event_name    # "${{ github.event_name }}"
expr.runner.os             # "${{ runner.os }}"
expr.matrix.python_version # "${{ matrix.python-version }}"

# Subscript access for secrets, env, etc.
expr.secrets["PYPI_TOKEN"]       # "${{ secrets.PYPI_TOKEN }}"
expr.env["CI"]                   # "${{ env.CI }}"
expr.steps["build"].outputs.dist # "${{ steps.build.outputs.dist }}"

# Functions
expr.contains(expr.github.ref, "refs/tags/")
# "${{ contains(github.ref, 'refs/tags/') }}"

expr.format("v{0}", expr.github.run_number)
# "${{ format('v{0}', github.run_number) }}"
```

Implementation: a `_ExprBuilder` class using `__getattr__` and `__getitem__` to accumulate path segments, with `__str__` wrapping in `${{ }}`. Common functions (`contains`, `startsWith`, `format`, `toJSON`, `fromJSON`, `hashFiles`) as methods.

### 1.3 Tests

- Unit tests for each step factory (correct `uses`, `with` values, kwarg forwarding)
- Unit tests for expression builder (attribute paths, subscripts, functions, string output)

---

## Milestone 2: Schema Pipeline (Maintainer-Only)

**Goal:** Automated detection of GitHub Actions schema changes so the library stays current.

### 2.1 Schema Fetcher

**File:** `src/ghagen/schema/fetch.py`

Download the latest workflow JSON Schema from SchemaStore.

```python
import httpx

SCHEMASTORE_URL = "https://json.schemastore.org/github-workflow.json"

def fetch_schema() -> dict:
    resp = httpx.get(SCHEMASTORE_URL, follow_redirects=True)
    resp.raise_for_status()
    return resp.json()

def save_schema(dest: Path) -> None:
    schema = fetch_schema()
    dest.write_text(json.dumps(schema, indent=2))
```

### 2.2 Code Generator

**File:** `src/ghagen/schema/codegen.py`

Run `datamodel-code-generator` to produce reference Pydantic v2 models from the JSON Schema.

```python
import subprocess

def generate_models(schema_path: Path, output_path: Path) -> None:
    subprocess.run([
        "datamodel-codegen",
        "--input", str(schema_path),
        "--input-file-type", "jsonschema",
        "--output-model-type", "pydantic_v2.BaseModel",
        "--output", str(output_path),
    ], check=True)
```

### 2.3 Drift Detection

**File:** `src/ghagen/schema/diff.py`

Compare current snapshot files against freshly generated ones and report differences.

```python
def check_drift(snapshot_dir: Path) -> tuple[bool, str]:
    """Returns (has_drift, diff_output)."""
    # Fetch fresh schema, generate fresh models to temp dir
    # Compare against snapshot_dir contents
    # Return unified diff if different
```

### 2.4 Snapshot Files

Commit initial snapshots to `src/ghagen/schema/snapshot/`:

- `workflow_schema.json` — the raw JSON Schema from SchemaStore
- `_generated_models.py` — auto-generated Pydantic v2 models (reference only, not imported at runtime)

### 2.5 CI Workflow for Drift Detection

A weekly cron GitHub Actions workflow in the ghagen repo:

```yaml
name: Schema Drift Check
on:
  schedule:
    - cron: "0 9 * * 1"  # Every Monday at 9am UTC
  workflow_dispatch:

jobs:
  check-drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync
      - run: |
          uv run python -m ghagen.schema.fetch
          uv run python -m ghagen.schema.codegen
      - name: Check for drift
        run: |
          if ! git diff --exit-code src/ghagen/schema/snapshot/; then
            echo "::warning::Schema drift detected"
            gh issue create \
              --title "GitHub Actions schema drift detected" \
              --body "$(git diff src/ghagen/schema/snapshot/)" \
              --label schema-drift
          fi
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

This workflow should eventually be dogfooded (generated by ghagen itself).

### 2.6 Tests

- Test `fetch_schema()` with a mocked HTTP response
- Test `generate_models()` with a small test schema
- Test `check_drift()` with matching and divergent snapshots

---

## Milestone 3: Expanded Test Coverage and Dogfooding

**Goal:** Comprehensive tests, integration validation, and self-hosting ghagen's own CI.

### 3.1 Integration Tests

**File:** `tests/test_integration/test_full_workflow.py`

End-to-end tests that:
1. Define a workflow in Python using all model types
2. Generate YAML via `to_yaml()`
3. Validate the generated YAML against the SchemaStore JSON Schema using the `jsonschema` library
4. Parse the YAML back with `ruamel.yaml` and verify round-trip correctness

Cover these scenarios:
- Simple CI workflow (push + PR triggers, single job, checkout + test steps)
- Matrix build (multi-version Python, multi-OS, with exclude)
- Reusable workflow call (`uses` job)
- Workflow with containers and services
- Workflow with all permission scopes set
- Complex triggers (schedule, workflow_dispatch with inputs, workflow_call with inputs/outputs/secrets)
- Escape hatches: `Raw`, `extras`, `post_process`, `CommentedMap` passthrough

### 3.2 Snapshot Tests

**Directory:** `tests/snapshots/`

Store expected YAML output as `.yml` files. Use `pytest-snapshot` to compare generated output against stored snapshots. Snapshots should cover:

- `ci_basic.yml` — minimal CI workflow
- `matrix_complex.yml` — multi-axis matrix with exclude
- `comments.yml` — workflow with block, end-of-line, and field-level comments
- `escape_hatches.yml` — all four escape hatches in one workflow
- `full_featured.yml` — comprehensive workflow exercising all model types

### 3.3 Dogfooding

**File:** `.github/ghagen_workflows.py`

Define ghagen's own CI/CD workflows using ghagen:

1. **CI workflow** (`ci.yml`): lint (ruff), type check (pyright), test (pytest) across Python 3.11-3.13
2. **Schema drift workflow** (`schema-drift.yml`): weekly cron from Milestone 2
3. **Release workflow** (`release.yml`): build + publish to PyPI on tag push (placeholder until Milestone 5)

After generating, run `ghagen check` in CI to verify the YAML stays in sync with the Python definitions.

### 3.4 Comment Formatting Polish

Known issues from the initial implementation:
- End-of-line comments on sequence items render on a separate line instead of inline
- Block comments on sequence items have inconsistent indentation

Investigate ruamel.yaml's `yaml_set_comment_before_after_key` and `yaml_add_eol_comment` behavior at different nesting depths. Add targeted tests and fix the emitter wrapper if needed.

---

## Milestone 4: Documentation

**Goal:** Comprehensive docs site and polished README for open-source launch.

### 4.1 MkDocs-Material Site

**Config:** `mkdocs.yml` at repo root

```yaml
site_name: ghagen
site_description: Generate GitHub Actions workflows from Python
theme:
  name: material
  palette:
    primary: deep-purple
plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          options:
            show_source: false
            heading_level: 3
```

**Pages:**

| Page | Content |
|---|---|
| `docs/index.md` | Overview, quick example, install instructions |
| `docs/getting-started.md` | Step-by-step tutorial: install, init, define workflow, synth |
| `docs/concepts.md` | Architecture overview: layers, models, emitter, app |
| `docs/escape-hatches.md` | Detailed guide to Raw, extras, post_process, CommentedMap |
| `docs/dry-patterns.md` | Reuse patterns: step factories, job templates, shared constants, loops |
| `docs/comments.md` | How to add comments: block, end-of-line, field-level, header |
| `docs/cli.md` | CLI reference: synth, check, init (with examples) |
| `docs/api/workflow.md` | API reference for Workflow model |
| `docs/api/job.md` | API reference for Job, Strategy, Matrix, Environment |
| `docs/api/step.md` | API reference for Step model |
| `docs/api/triggers.md` | API reference for On, all trigger types |
| `docs/api/permissions.md` | API reference for Permissions |
| `docs/api/helpers.md` | API reference for step factories and expression builder |

### 4.2 README

Polish `README.md` with:
- Project tagline and badges (CI status, PyPI version, Python versions, license)
- Quick install: `pip install ghagen`
- Minimal example showing Python → YAML
- Feature highlights (typed models, comments, DRY, escape hatches, CLI)
- Links to full documentation

### 4.3 Dev Dependencies

Add to dev dependency group:
```
"mkdocs-material",
"mkdocstrings[python]",
```

---

## Milestone 5: Release Preparation

**Goal:** Ship v0.1.0 to PyPI and set up automated release pipeline.

### 5.1 Version Management

Options (choose one):
- **python-semantic-release**: auto-bump version from conventional commit messages, generate changelog
- **Manual**: bump version in `pyproject.toml`, tag, push

Recommendation: start with manual releases, add semantic-release later when commit discipline is established.

### 5.2 PyPI Trusted Publishing

Set up OIDC-based publishing so GitHub Actions can publish to PyPI without storing API tokens:

1. Create the `ghagen` project on PyPI
2. Configure Trusted Publisher in PyPI settings (link to GitHub repo + workflow)
3. Create a release workflow:

```yaml
name: Release
on:
  push:
    tags: ["v*"]

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: release
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

### 5.3 Changelog

Maintain a `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/) format. Automate generation from git tags/commits if using semantic-release.

### 5.4 Pre-release Checklist

Before tagging v0.1.0:
- [ ] All milestones 1-4 complete
- [ ] `uv run pytest` passes
- [ ] `uv run ruff check src/ tests/` clean
- [ ] `uv run pyright src/` clean
- [ ] `ghagen check` passes (dogfooding)
- [ ] README has install/usage instructions
- [ ] Documentation site builds and deploys
- [ ] License file present (MIT)
- [ ] `py.typed` marker present
- [ ] `pyproject.toml` metadata complete (description, keywords, classifiers, URLs)

---

## Future Work (Post v0.1.0)

These items are not gated on the initial release but represent the longer-term vision.

### GitHub Action for Users

A composite action that wraps `ghagen check` so users can add freshness checking to their own CI:

```yaml
# In user's workflow
- uses: nathanjordan/ghagen-action@v1
  with:
    config: .github/ghagen_workflows.py
```

Implementation: a small `action.yml` that installs ghagen and runs `ghagen check`. Eventually dogfooded with ghagen itself.

### VSCode Extension

A language server / extension that provides:
- Stale file detection (indicator when generated YAML is out of sync with Python source)
- Action version resolution (convert `actions/checkout@v4` to `actions/checkout@<commit-sha>` with a preserving comment)
- Go-to-definition from generated YAML back to the Python source
- IntelliSense for ghagen Python files (model field completion, step factory signatures)

### Import from YAML (Migration Tool)

A `ghagen import` command that parses an existing `.github/workflows/*.yml` file and generates the equivalent ghagen Python code. Useful for migrating existing repos to ghagen.

### Reusable Workflow and Composite Action Generation

Extend beyond workflow files to generate:
- Reusable workflow files (the `workflow_call` trigger side)
- `action.yml` files for composite actions
- `action.yml` files for Docker/JavaScript actions (metadata only)

### Linting Rules

Built-in linting for generated workflows:
- Missing `permissions` (default is overly broad)
- Unpinned action versions (`@main` instead of `@v4` or `@sha`)
- Missing `timeout-minutes` on jobs
- Mutable default values in workflow definitions
- Duplicate step IDs within a job

### Action Version Pinning

A `ghagen pin` command that resolves action version tags to their commit SHAs:

```
actions/checkout@v4 → actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4
```

Preserves the tag as a comment for readability. Uses the GitHub API to resolve tags.
