# ghagen

Generate GitHub Actions workflows from Python or TypeScript code.

[![CI](https://github.com/nathanjordan/ghagen/actions/workflows/ci.yml/badge.svg)](https://github.com/nathanjordan/ghagen/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/ghagen)](https://pypi.org/project/ghagen/)
[![Python](https://img.shields.io/pypi/pyversions/ghagen)](https://pypi.org/project/ghagen/)
[![License](https://img.shields.io/github/license/nathanjordan/ghagen)](LICENSE)

## Why

Github actions are configuration defined as YAML files. This means they are usually simple and easy
to read. As projects grow and get more complex, their Github actions often do as well. YAML
configuration doesn't scale well however. Different workflows/actions often have shared concerns and
common behavior that leads to maintenance issues where you will find yourself changing the same
value or logic in multiple places. This can lead to bugs and configuration drift between
actions/workflows that are supposed to behave the same (eg. separate versions of the "setup-node"
action). Programming languages can solve this problem with code reuse, but yaml doesn't really have
this functionality. Github has tried to solve this with composite actions and [YAML
anchors](https://github.blog/changelog/2025-09-18-actions-yaml-anchors-and-non-public-workflow-templates/).
This is the wrong approach: instead of trying to turn YAML, a configuration language, into a
programming language, we should instead realize that configuration is indeed a programming language
problem. AWS CDK took the correct approach here: use a programming language to define configuration.
This is the problem `ghagen` is supposed to solve but for Github actions.

Another problem is that Github actions have package dependencies (ie. `uses: "setup-node@v2"`)
without a lockfile to pin to specific versions. This means you'll have potentially different action
versions running anytime you run your workflow, which makes the build process non-hermetic and opens
an avenue for security risks in the event of package takeovers. Fortunately some tools have been
created to address this problem like [Ratchet][ratchet]. `ghagen` also supports version pinning but
does so using a lockfile that you can update when you want via a cli command.

## Features

- **Dual language support** - The tool comes in two flavors depending on your
   constraints/preferences: Python and Javascript/Typescript.
- **Typed models** — type checking and IDE autocomplete which prevents typos or unsupported values.
- **YAML comments** — Add comments to the generated yaml for additional documentation/clarity
- **Helpers** — expression builder (`expr`) ensures you are using supported template variables
- **Escape hatches** — Break out of the type system when you want to. You're not stuck with the
schema if new features come out or you need to override something.
- **Linting** — catch gotchas like invalid permissions and more. `timeout-minutes`, and duplicate
  step ids with source-line precision
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