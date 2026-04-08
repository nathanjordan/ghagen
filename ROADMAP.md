# ghagen Roadmap

## What's Done

Steps 1-5 of the original plan and Milestones 2-5 are complete:

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
- **Release pipeline** — Release Please automation (`googleapis/release-please-action@v4`) with OIDC-based PyPI trusted publishing, CHANGELOG.md, version management via conventional commits
- **GitHub Action** — Composite action (`action.yml`) wrapping `ghagen check` for users to add workflow freshness checking to their CI (`uses: nathanjordan/ghagen@v0.2.0`)
- **Reusable workflows and composite/Docker/JS actions** — `Action`/`ActionInput`/`ActionOutput`/`Branding`/`CompositeRuns`/`DockerRuns`/`NodeRuns` models generate `action.yml` files alongside workflows; `App` redesigned with `add_workflow()`/`add_action()`/`add()`; reusable workflow producer side (`workflow_call` trigger) covered end-to-end; schema pipeline extended to fetch, codegen, diff, and validate the `github-action.json` schema; ghagen's own `action.yml` is now dogfooded from Python

### Known Issues (Deferred)

- **Comment formatting on sequence items** — EOL comments on map sequence items (e.g., Steps) render on a separate line instead of inline; block comments lack proper indentation. Root cause is ruamel.yaml's internal comment placement on `CommentedSeq` items that are `CommentedMap`s. Tests documenting the behavior are in `tests/test_emitter/test_yaml_writer.py`.

---

## Future Work (Post v0.1.0)

These items are not gated on the initial release but represent the longer-term vision.

### VSCode Extension

A language server / extension that provides:
- Stale file detection (indicator when generated YAML is out of sync with Python source)
- Action version resolution (convert `actions/checkout@v4` to `actions/checkout@<commit-sha>` with a preserving comment)
- Go-to-definition from generated YAML back to the Python source
- IntelliSense for ghagen Python files (model field completion, step factory signatures)

### Import from YAML (Migration Tool)

A `ghagen import` command that parses an existing `.github/workflows/*.yml` file and generates the equivalent ghagen Python code. Useful for migrating existing repos to ghagen.

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
