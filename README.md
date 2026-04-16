# ghagen

Generate GitHub Actions workflows from Python or TypeScript code.

[![CI](https://github.com/nathanjordan/ghagen/actions/workflows/ci.yml/badge.svg)](https://github.com/nathanjordan/ghagen/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/ghagen)](https://pypi.org/project/ghagen/)
[![Python](https://img.shields.io/pypi/pyversions/ghagen)](https://pypi.org/project/ghagen/)
[![License](https://img.shields.io/github/license/nathanjordan/ghagen)](LICENSE)

> [!NOTE]
> **You probably don't need this.** If your GitHub Actions setup is relatively
> simple, ghagen is not worth the added complexity — [actionlint][actionlint]
> and [Renovate][renovate]/[Dependabot][dependabot] will serve you well. Reach
> for ghagen when keeping track of workflows by hand becomes painful, or when
> you want the extra assurances a real programming language provides (types,
> tests, refactoring tools).

## Features

- **Typed models** — Pydantic (Python) and factory functions (TypeScript) with full IDE autocomplete
- **YAML comments** — block, end-of-line, and field-level comments preserved in output
- **DRY helpers** — expression builder (`expr`) and step factories (`checkout()`, `setup_python()`, …) for common actions
- **Escape hatches** — `Raw`/`raw()`, `extras`, and passthrough for anything the typed API doesn't cover
- **Linting** _(Python)_ — catches missing `permissions`, unpinned actions, missing `timeout-minutes`, and duplicate step ids with source-line precision
- **CLI** _(Python)_ — `ghagen synth` generates YAML, `ghagen check-synced` verifies freshness in CI, `ghagen lint` runs rule-based checks, `ghagen deps pin` locks actions to commit SHAs

## Quickstart

### Python

```bash
pip install ghagen        # or: uv tool install ghagen
```

```python
from ghagen import App, Job, On, PushTrigger, Step, Workflow

ci = Workflow(
    name="CI",
    on=On(push=PushTrigger(branches=["main"])),
    jobs={
        "test": Job(
            runs_on="ubuntu-latest",
            steps=[Step(uses="actions/checkout@v4"), Step(run="pytest")],
        ),
    },
)

app = App()
app.add_workflow(ci, "ci.yml")
app.synth()
```

```bash
ghagen synth
```

### TypeScript

```bash
npm install --save-dev @ghagen/ghagen
```

```typescript
import { workflow, job, step, on, pushTrigger, toYamlFile } from "@ghagen/ghagen";

const ci = workflow({
  name: "CI",
  on: on({ push: pushTrigger({ branches: ["main"] }) }),
  jobs: {
    test: job({
      runsOn: "ubuntu-latest",
      steps: [step({ uses: "actions/checkout@v4" }), step({ run: "pytest" })],
    }),
  },
});

toYamlFile(ci, ".github/workflows/ci.yml");
```

```bash
npx tsx .github/workflows.ts
```

### GitHub Action

Run `ghagen check-synced` in CI so a PR fails if the generated YAML drifts
from the Python config:

```yaml
jobs:
  check-workflows:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: nathanjordan/ghagen@v0
        with:
          config: .github/ghagen_workflows.py  # optional; default shown
          python-version: "3.13"               # optional; default shown
          ghagen-version: ""                   # optional; empty = latest
```

`v0` is a rolling major tag. The Action is a drift check for the Python
path; TypeScript users should run their script and `git diff --exit-code
.github/workflows/` instead.

## Example output

Both snippets above generate:

```yaml
name: CI
on:
  push:
    branches:
    - main
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - run: pytest
```

## FAQ

**Python or TypeScript — which should I pick?**
Match your repo's primary language. The Python package is more featureful
today (CLI, `ghagen lint`, `ghagen deps pin` for SHA pinning); the
TypeScript package covers the core modeling and YAML emission.

**Can I mix ghagen-generated workflows with hand-written YAML?**
Yes. ghagen only touches files you explicitly register. Any other file in
`.github/workflows/` is left alone — drop a hand-written `weekly-report.yml`
next to a ghagen-generated `ci.yml` and nothing breaks.

**What does the GitHub Action do?**
It runs `ghagen check-synced` against your Python config and fails the
build if the generated YAML doesn't match what the current definitions
would produce. It's a drift check, not a code generator.

**How do I handle something ghagen's models don't cover?**
Use `extras` on any model for arbitrary keys, or `Raw` / `raw()` to drop
an expression into a field that expects a literal. Both leave the rest of
the model fully typed.

**How do I pin actions to commit SHAs?**
Run `ghagen deps pin` to populate `.github/ghagen.lock.toml`; subsequent
`ghagen synth` calls rewrite every `uses:` to its pinned SHA. Wire
`ghagen deps check-synced` into CI to catch unpinned additions.
_(Python CLI only.)_

_More questions? See the [full FAQ](https://nathanjordan.github.io/ghagen/faq/)._

## Documentation

Full documentation: [nathanjordan.github.io/ghagen](https://nathanjordan.github.io/ghagen/)

## License

MIT

[actionlint]: https://github.com/rhysd/actionlint
[renovate]: https://docs.renovatebot.com/
[dependabot]: https://docs.github.com/en/code-security/dependabot
