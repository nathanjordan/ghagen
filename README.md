# ghagen

Generate GitHub Actions workflows from Python or TypeScript code.

[![CI](https://github.com/nathanjordan/ghagen/actions/workflows/ci.yml/badge.svg)](https://github.com/nathanjordan/ghagen/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/ghagen)](https://pypi.org/project/ghagen/)
[![Python](https://img.shields.io/pypi/pyversions/ghagen)](https://pypi.org/project/ghagen/)
[![License](https://img.shields.io/github/license/nathanjordan/ghagen)](LICENSE)

## Features

- **Dual language support** - The tool comes in two flavors depending on your
   constraints/preferences: Python and Javascript/Typescript.
- **Typed models** — type checking and IDE autocomplete which prevents typos or unsupported values.
- **YAML comments** — Add comments to the generated yaml for additional documentation/clarity
- **Helpers** — expression builder (`expr`) ensures you are using supported template variables
- **Escape hatches** — Break out of the type system when you want to. You're not stuck with the
schema if new features come out or you need to override something.
- **Freshness checking** — ensure your generated yaml files are in sync with your defined ghagen
  models
- **Version pinning** — Prevent surprises and security risks by ensuring the same actions run every
  time.

> [!NOTE] **You might not need this** if your GitHub Actions setup is relatively simple, ghagen
> might not be worth the added complexity — [actionlint][actionlint]
> [renovate][renovate]/[dependabot][dependabot] and [ratchet][ratchet] can cover a lot of common
> issues. Reach for ghagen when keeping track of workflows by hand becomes painful, or when you want
> the extra assurances a real programming language provides (types, tests, refactoring tools).

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
import { App, workflow, job, step, on, pushTrigger } from "@ghagen/ghagen";

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

const app = new App();
app.addWorkflow(ci, "ci.yml");
await app.synth();
```

```bash
npx ghagen synth
```

### GitHub Action

Run `ghagen check-synced` in CI so a PR fails if the generated YAML drifts from the Python config:

```yaml
jobs:
  check-workflows:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: nathanjordan/ghagen/check-synth@v0
        with:
          config: .github/ghagen_workflows.py  # optional; default shown
          python-version: "3.13"               # optional; default shown
          ghagen-version: ""                   # optional; empty = latest
```

`v0` is a rolling major tag. The Action is a drift check for the Python path; TypeScript users can
run `npx ghagen check-synced` instead.

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

**Python or TypeScript — which should I pick?** Pick whatever you're comfortable with or fits with
your project. Both Python and Typescript/Javscript implementations have feature parity and are
interchangeable.

**Can I mix ghagen-generated workflows with hand-written YAML?** Yes. ghagen only touches files you
explicitly register. Any other file in `.github/workflows/` is left alone — drop a hand-written
`weekly-report.yml` next to a ghagen-generated `ci.yml` and nothing breaks.

**What does the GitHub Action do?** It runs `ghagen check-synced` against your Python config and
fails the build if the generated YAML doesn't match what the current definitions would produce. It
prevents changes made to the Python/JS code from not making it into the YAML spec.

**How do I handle something ghagen's models don't cover?** Use `extras` on any model for arbitrary
keys, or `Raw` / `raw()` to drop an expression into a field that expects a literal. Both leave the
rest of the model fully typed.

**How do I pin actions to commit SHAs?** Run `ghagen deps pin` to populate
`.github/ghagen.lock.toml`; subsequent `ghagen synth` calls rewrite every `uses:` to its pinned SHA.
Wire `ghagen deps check-synced` into CI to catch unpinned additions.

_More questions? See the [full FAQ](https://nathanjordan.github.io/ghagen/faq/)._

## Documentation

Full documentation: [nathanjordan.github.io/ghagen](https://nathanjordan.github.io/ghagen/)

## License

MIT

[actionlint]: https://github.com/rhysd/actionlint
[renovate]: https://docs.renovatebot.com/
[dependabot]: https://docs.github.com/en/code-security/dependabot
[ratchet]: https://github.com/sethvargo/ratchet
