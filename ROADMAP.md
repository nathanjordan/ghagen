# ghagen Roadmap

## What's Done

Steps 1-5 of the original plan and Milestones 2-4 are complete:

- **Project scaffolding** — uv + hatchling, src layout, ruff/pyright, pre-commit
- **YAML emitter** — ruamel.yaml with CommentedMap, canonical key ordering, comment attachment
- **Domain models** — Workflow, Job, Step, On/triggers, Permissions, Container, Strategy/Matrix, common types
- **Escape hatches** — `Raw[T]`, `extras`, `post_process` callback, `CommentedMap` passthrough
- **App class** — `synth()` and `check()` for multi-workflow synthesis
- **CLI** — `ghagen synth`, `ghagen check`, `ghagen init` via Typer
- **Tests** — 128 passing (models, emitter, CLI, helpers, schema, integration, snapshots)
- **DRY helpers** — Step factories (`checkout`, `setup_python`, `setup_node`, `setup_uv`, `cache`, `upload_artifact`, `download_artifact`) and expression builder (`expr`)
- **Schema pipeline** — Schema fetcher (`fetch.py`), code generator (`codegen.py`), drift detection (`diff.py`), initial snapshots, weekly CI workflow for drift detection
- **Integration tests** — 7 end-to-end tests with JSON Schema validation and round-trip verification
- **Snapshot tests** — 5 snapshot files (`ci_basic`, `matrix_complex`, `comments`, `escape_hatches`, `full_featured`) via pytest-snapshot
- **Dogfooding** — ghagen's own CI/CD defined in `.github/ghagen_workflows.py` (CI, schema-drift, release, docs workflows)
- **Documentation site** — MkDocs-Material with mkdocstrings, 14 pages (guides, API reference, CLI), auto-deployed to GitHub Pages
- **README** — badges, install, example, feature highlights, doc links

### Known Issues (Deferred)

- **Comment formatting on sequence items** — EOL comments on map sequence items (e.g., Steps) render on a separate line instead of inline; block comments lack proper indentation. Root cause is ruamel.yaml's internal comment placement on `CommentedSeq` items that are `CommentedMap`s. Tests documenting the behavior are in `tests/test_emitter/test_yaml_writer.py`.

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
