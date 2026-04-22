# ghagen

ghagen is a Github Actions code generator. It facilitates writing actions in Python or
Typescript/Javascript which are then transformed into YAML files in the .github/ directory
(configurable).

Think of this kind of like AWS CDK for Github Actions.

## Philosophy

- Don't try to make YAML into a programming language. Use a real programming language to generate
  YAML.
- Use opinionated defaults/conventions but allow for customization with escape hatches
- balance simplicity with developer convenience of using the tool
- treat actions like code dependencies

## Functionality

- Specify Github Actions as structured Python/Typescript/Javascript, allows for:
  - Type checking
  - Code reuse
  - DRY
  - Abstractions
- Ensure Python/Javascript/Typescript and generated YAML specs are in sync
  - Check functionality that can run as git hook and/or github action in CI
- Action dependency version management (eg. `uses: org/tool@v2`)
  - github actions are versioned code (essentially packages)
  - they should be managed like other dependencies (with a package manager)
  - Use a lockfile to pin semver specs to a specific action SHA/digest.
    - the same action is run every time unless you upgrade
    - Prevents unexpected breakage and security risks by pinning the action to a static commit
  - support upgrading (both major versions and lockfile maintenance)
  - Custom ghagen github action to handle this automatically like dependabot or renovate
    - Generate PRs or issues (configurable)

## Agent Instructions

- The ghagen.toml and pyproject.toml/package.json config structures should stay in sync and support
  the same functionality.
- The ghagen tool is used in supporting github actions that are defined in this repo, so actions
will need to be considered when making changes to the tool.
- Update documentation when making any user-facing changes.
- **ALWAYS** make sure lint/format/type/test checks pass before completing a task.

## Common Commands

```sh
scripts/lint.sh # lint
scripts/fmt.sh # format
scripts/typecheck.sh # check types
scripts/test.sh # tests
uv run ghagen check-synced # check GHA workflow files synced
```

## Docs

The documentation site is an [Astro Starlight](https://starlight.astro.build/) project in `docs/`.

```sh
scripts/docs-dev.sh # serve docs locally (http://localhost:4321/ghagen/)
cd docs && npm run build # production build (also regenerates TypeScript API docs)
```