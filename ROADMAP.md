# ghagen Roadmap

## What's Done

Steps 1-5 of the original plan and Milestone 2 are complete:

- **Project scaffolding** — uv + hatchling, src layout, ruff/pyright, pre-commit
- **YAML emitter** — ruamel.yaml with CommentedMap, canonical key ordering, comment attachment
- **Domain models** — Workflow, Job, Step, On/triggers, Permissions, Container, Strategy/Matrix, common types
- **Escape hatches** — `Raw[T]`, `extras`, `post_process` callback, `CommentedMap` passthrough
- **App class** — `synth()` and `check()` for multi-workflow synthesis
- **CLI** — `ghagen synth`, `ghagen check`, `ghagen init` via Typer
- **Tests** — 112 passing (models, emitter, CLI, helpers, schema)
- **DRY helpers** — Step factories (`checkout`, `setup_python`, `setup_node`, `setup_uv`, `cache`, `upload_artifact`, `download_artifact`) and expression builder (`expr`)
- **Schema pipeline** — Schema fetcher (`fetch.py`), code generator (`codegen.py`), drift detection (`diff.py`), initial snapshots, weekly CI workflow for drift detection

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
