# ghagen Roadmap

## What's Done

Steps 1-5 of the original plan and Milestones 2-5 are complete:

- **Project scaffolding** — uv + hatchling, src layout, ruff/pyright, pre-commit
- **YAML emitter** — ruamel.yaml with CommentedMap, canonical key ordering, comment attachment
- **Domain models** — Workflow, Job, Step, On/triggers, Permissions, Container, Strategy/Matrix, common types
- **Escape hatches** — `Raw[T]`, `extras`, `post_process` callback, `CommentedMap` passthrough
- **App class** — `synth()` and `check_synced()` for multi-workflow synthesis
- **CLI** — `ghagen synth`, `ghagen check-synced`, `ghagen init` via Typer
- **Tests** — 128 passing (models, emitter, CLI, helpers, schema, integration, snapshots)
- **DRY helpers** — Step factories (`checkout`, `setup_python`, `setup_node`, `setup_uv`, `cache`, `upload_artifact`, `download_artifact`) and expression builder (`expr`)
- **Schema pipeline** — Schema fetcher (`fetch.py`), code generator (`codegen.py`), drift detection (`diff.py`), initial snapshots, weekly CI workflow for drift detection
- **Integration tests** — 7 end-to-end tests with JSON Schema validation and round-trip verification
- **Snapshot tests** — 5 snapshot files (`ci_basic`, `matrix_complex`, `comments`, `escape_hatches`, `full_featured`) via pytest-snapshot
- **Dogfooding** — ghagen's own CI/CD defined in `.github/ghagen_workflows.py` (CI, schema-drift, release, docs workflows)
- **Documentation site** — MkDocs-Material with mkdocstrings, 14 pages (guides, API reference, CLI), auto-deployed to GitHub Pages
- **README** — badges, install, example, feature highlights, doc links
- **Release pipeline** — Release Please automation (`googleapis/release-please-action@v4`) with OIDC-based PyPI trusted publishing, CHANGELOG.md, version management via conventional commits
- **GitHub Action** — Composite action (`action.yml`) wrapping `ghagen check-synced` for users to add workflow freshness checking to their CI (`uses: nathanjordan/ghagen@v0.2.0`)
- **Reusable workflows and composite/Docker/JS actions** — `Action`/`ActionInput`/`ActionOutput`/`Branding`/`CompositeRuns`/`DockerRuns`/`NodeRuns` models generate `action.yml` files alongside workflows; `App` redesigned with `add_workflow()`/`add_action()`/`add()`; reusable workflow producer side (`workflow_call` trigger) covered end-to-end; schema pipeline extended to fetch, codegen, diff, and validate the `github-action.json` schema; ghagen's own `action.yml` is now dogfooded from Python
- **Linting** — `ghagen lint` command with rule engine, Python source-line capture via frame inspection, `.github/ghagen.toml` + `pyproject.toml` config loading, human/JSON/GitHub annotation output formats. Built-in rules: `missing-permissions`, `unpinned-actions`, `missing-timeout`, `duplicate-step-ids`.
- **Action pinning** — `ghagen deps pin` command resolves action version refs (e.g. `@v4`) to immutable commit SHAs stored in a lockfile at `.github/ghagen.lock.toml` (Cargo.lock / package-lock.json-style; machine-managed, auto-sorted). Clean version tags stay in Python source. Flags: `--update`, `--prune`, `--token`. `ghagen deps check-synced` verifies the lockfile is in sync (CI-friendly). Built on a model transform pipeline (`SynthContext`, `Transform` protocol) applied between Pydantic models and YAML emission; `App.synth()`/`check_synced()` auto-apply the lockfile when present. GitHub API resolver (urllib) handles lightweight and annotated tags. Emitted YAML uses the industry-standard inline comment format: `actions/checkout@<sha>  # v4`. The `unpinned-actions` lint rule is lockfile-aware.
- **YAML output formatting** — EOL comments on map sequence items now render inline with the first key (e.g. `- name: Ruff  # fast Python linter`); block comments on sequence items and on regular map fields are indented to align with their containing item rather than sticking to column 0; multiline `str` values automatically render as `|` literal block scalars (`|-` strip-chomping when no trailing newline). `Raw[str]` values bypass the auto-conversion via a `PlainScalarString` sentinel, preserving the escape-hatch contract. Implemented via two post-passes in `dump_yaml`: a tree walker that promotes plain multiline strings to `LiteralScalarString` (skipping `ScalarString` subclasses) and a walker that rewrites every pre-comment `CommentToken.start_mark.column` to match the emit indent.

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
