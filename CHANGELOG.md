# Changelog

## [0.3.0](https://github.com/nathanjordan/ghagen/compare/ghagen-v0.2.1...ghagen-v0.3.0) (2026-04-14)


### ⚠ BREAKING CHANGES

* **emitter:** configurable header with source-file templating
* add action.yml generation and redesign App API ([#4](https://github.com/nathanjordan/ghagen/issues/4))

### feat\

* add action.yml generation and redesign App API ([#4](https://github.com/nathanjordan/ghagen/issues/4)) ([10914bb](https://github.com/nathanjordan/ghagen/commit/10914bb8768d2a4fc390a3c86dca6f80c80c5805))


### Features

* add `ghagen pin` command with SHA lockfile ([#7](https://github.com/nathanjordan/ghagen/issues/7)) ([a138ee0](https://github.com/nathanjordan/ghagen/commit/a138ee06b858e376ed4948bf893dc5b2937510b9))
* add CI job to test composite action via uses: ./ ([f02a3ed](https://github.com/nathanjordan/ghagen/commit/f02a3ed27b9d930fab150fac3ba19daef6df82bb))
* add ghagen lint command with rule engine ([#5](https://github.com/nathanjordan/ghagen/issues/5)) ([3e7d3da](https://github.com/nathanjordan/ghagen/commit/3e7d3da76db019d83da87a7c56be976fa625b557))
* add ghagen update action for automated dependency updates ([78d19b4](https://github.com/nathanjordan/ghagen/commit/78d19b476fa945c2d26042865cb2852f8177cc35))
* add Homebrew tap automation and install docs ([60dd99c](https://github.com/nathanjordan/ghagen/commit/60dd99cc828d594db0784f37ac435e8694530c40))
* **cli:** add `entrypoint` key to .github/ghagen.toml ([16f5156](https://github.com/nathanjordan/ghagen/commit/16f5156ff68ff0e3aa9788b2af504b1104e0be2f))
* **cli:** add `ghagen outdated` command for update detection ([f1a1dff](https://github.com/nathanjordan/ghagen/commit/f1a1dff8166a3d85029e501e178fcf97e74452ba))
* **emitter:** configurable header with source-file templating ([64bb6d9](https://github.com/nathanjordan/ghagen/commit/64bb6d9141c05f52c0510f3260c1966bdd81f06b))
* **emitter:** fix seq-item comments and auto-wrap multiline strings ([#9](https://github.com/nathanjordan/ghagen/issues/9)) ([5fd0bda](https://github.com/nathanjordan/ghagen/commit/5fd0bdaf380cdcd16800fddec5688f0aecbef378))
* **lint:** add duplicate-step-ids rule and drop mutable-defaults ([#6](https://github.com/nathanjordan/ghagen/issues/6)) ([1d5874d](https://github.com/nathanjordan/ghagen/commit/1d5874d952b377536c23e5ff49e5db75ce5497cd))
* **pin:** add list_tags() for paginated tag listing via GitHub API ([483589b](https://github.com/nathanjordan/ghagen/commit/483589bc7b32fb0fa1188659b3bd9bd64f034fa4))
* **pin:** add source tracking module for uses ref location ([189e3db](https://github.com/nathanjordan/ghagen/commit/189e3dbcae78dc8b2ab17e3e4c8e14b0e7268be7))
* **pin:** add source update module for applying version bumps ([1838832](https://github.com/nathanjordan/ghagen/commit/18388323463539b94cdc8c872d39417038a72943))
* **pin:** add version comparison module for action tags ([a416844](https://github.com/nathanjordan/ghagen/commit/a416844054cc878e8386b21b24179d9c27385a53))
* **pin:** pin composite action steps alongside workflows ([dbd9aa4](https://github.com/nathanjordan/ghagen/commit/dbd9aa400357a75702eec03aa73b1382701108d1))
* **release:** add npm publishing for TypeScript package ([1a50b45](https://github.com/nathanjordan/ghagen/commit/1a50b454f31de02dd106604133c27a359f6d38ac))
* restructure into monorepo with TypeScript package skeleton ([#20](https://github.com/nathanjordan/ghagen/issues/20)) ([e997f15](https://github.com/nathanjordan/ghagen/commit/e997f15acec46136d57386498e60ce644d89967e))
* **step:** auto-dedent triple-quoted strings in Step.run ([0dac976](https://github.com/nathanjordan/ghagen/commit/0dac97625f778fcbd34129c391942c1653773efd))
* **typescript:** implement model layer with factory functions and YAML serializer ([0ca3e2d](https://github.com/nathanjordan/ghagen/commit/0ca3e2d389cf4639d175053f419a5a6fe5fd9925))


### Bug Fixes

* add release environment to homebrew-bump job ([5f80ca1](https://github.com/nathanjordan/ghagen/commit/5f80ca10606ed0d8b7da61b079f5ad0500f985a3))
* address code review findings for outdated command ([b808e64](https://github.com/nathanjordan/ghagen/commit/b808e64f684b8a13ff3fab47c885014a79dda079))
* **pin:** skip token warning in --check mode ([4c09391](https://github.com/nathanjordan/ghagen/commit/4c09391cb34ab771d6bf2634eb04d584c4e98d1e))
* **release:** bump minor (not major) for breaking changes pre-1.0 ([#11](https://github.com/nathanjordan/ghagen/issues/11)) ([687fd3e](https://github.com/nathanjordan/ghagen/commit/687fd3ecea704007b665d2d1e2c58843f08cd395))


### Documentation

* add AGENTS.md with project overview and agent instructions ([1e862a8](https://github.com/nathanjordan/ghagen/commit/1e862a866952acfe1f60b0f4466410a5f75b4e8d))
* **mkdocs:** switch theme to amber accent with factory logo ([7d2ab9a](https://github.com/nathanjordan/ghagen/commit/7d2ab9a5f852e8a2fe698f83aabcd62705f003e8))
* note that ghagen supports actions defined in this repo ([f41e240](https://github.com/nathanjordan/ghagen/commit/f41e2409d1a4f1b8dd24ec90f26e821be710af18))
* require documentation updates for user-facing changes ([e7b96e1](https://github.com/nathanjordan/ghagen/commit/e7b96e145a7a27f6a6d458e13efea456510717ea))
* **roadmap:** mark action pinning as done ([#8](https://github.com/nathanjordan/ghagen/issues/8)) ([1149723](https://github.com/nathanjordan/ghagen/commit/114972386a2d0931b5c7a580d33f1b5e1394e49d))
* update AGENTS.md to reflect TypeScript/JavaScript support ([78de75b](https://github.com/nathanjordan/ghagen/commit/78de75b764330faad363c7c2b5d6bc71f3ecfd17))

## [0.2.1](https://github.com/nathanjordan/ghagen/compare/ghagen-v0.2.0...ghagen-v0.2.1) (2026-04-07)


### Bug Fixes

* add contents:read permission to publish job ([a7cb3fb](https://github.com/nathanjordan/ghagen/commit/a7cb3fb283239dc2b40735d2cde063648b85fd83))

## [0.2.0](https://github.com/nathanjordan/ghagen/compare/ghagen-v0.1.0...ghagen-v0.2.0) (2026-04-07)


### Features

* add actionlint to pre-commit and CI lint job ([59198c2](https://github.com/nathanjordan/ghagen/commit/59198c20824e3bc4a5fc693d3d5bf82dc72c2ff7))
* add composite GitHub Action for workflow freshness checking ([178728b](https://github.com/nathanjordan/ghagen/commit/178728b9981cf237cd2db75309dd32d1748d0c03))
* add DRY helpers — step factories and expression builder ([3b1fabf](https://github.com/nathanjordan/ghagen/commit/3b1fabf651308ca019cb0b977e360fada9d35545))
* add Release Please automation for PyPI publishing (Milestone 5) ([6f48ab3](https://github.com/nathanjordan/ghagen/commit/6f48ab39f465ed423bd1b508490a74dd7fbcd7a0))
* add schema pipeline for drift detection ([637fafc](https://github.com/nathanjordan/ghagen/commit/637fafc13027ee5f57cb1f4037ac1d309fa21d11))
* dogfood ghagen for own CI/CD workflows ([949acf9](https://github.com/nathanjordan/ghagen/commit/949acf9858bdff5414e7d2e6c482abf85b1fe3be))
* initial implementation of ghagen core library ([8651ab0](https://github.com/nathanjordan/ghagen/commit/8651ab03893ff80b83a8fb03890a82d23180efa0))


### Bug Fixes

* resolve ruff lint errors in new test files ([9b409a1](https://github.com/nathanjordan/ghagen/commit/9b409a1a61dde62ee81df40537bd2829a0927b3d))


### Documentation

* add detailed ROADMAP.md for remaining work ([17e249c](https://github.com/nathanjordan/ghagen/commit/17e249c07dcf469b295a2f886f629c90f87f1196))
* add MkDocs-Material documentation site and README (Milestone 4) ([1885543](https://github.com/nathanjordan/ghagen/commit/1885543804ca0b70f0fe500042a8b86ecfd37186))
* update ROADMAP.md — mark Milestone 3 complete ([203c9b5](https://github.com/nathanjordan/ghagen/commit/203c9b55a8f212c02a6378c0cd2c05f1444af0c3))

## [0.1.0](https://github.com/nathanjordan/ghagen/releases/tag/v0.1.0) (2026-04-07)

Initial release — generate GitHub Actions workflow YAML from Python code.
