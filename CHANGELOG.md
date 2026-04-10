# Changelog

## [1.0.0](https://github.com/nathanjordan/ghagen/compare/ghagen-v0.2.1...ghagen-v1.0.0) (2026-04-10)


### ⚠ BREAKING CHANGES

* **emitter:** configurable header with source-file templating
* add action.yml generation and redesign App API ([#4](https://github.com/nathanjordan/ghagen/issues/4))

### feat\

* add action.yml generation and redesign App API ([#4](https://github.com/nathanjordan/ghagen/issues/4)) ([10914bb](https://github.com/nathanjordan/ghagen/commit/10914bb8768d2a4fc390a3c86dca6f80c80c5805))


### Features

* add `ghagen pin` command with SHA lockfile ([#7](https://github.com/nathanjordan/ghagen/issues/7)) ([a138ee0](https://github.com/nathanjordan/ghagen/commit/a138ee06b858e376ed4948bf893dc5b2937510b9))
* add CI job to test composite action via uses: ./ ([f02a3ed](https://github.com/nathanjordan/ghagen/commit/f02a3ed27b9d930fab150fac3ba19daef6df82bb))
* add ghagen lint command with rule engine ([#5](https://github.com/nathanjordan/ghagen/issues/5)) ([3e7d3da](https://github.com/nathanjordan/ghagen/commit/3e7d3da76db019d83da87a7c56be976fa625b557))
* **cli:** add `entrypoint` key to .github/ghagen.toml ([16f5156](https://github.com/nathanjordan/ghagen/commit/16f5156ff68ff0e3aa9788b2af504b1104e0be2f))
* **emitter:** configurable header with source-file templating ([64bb6d9](https://github.com/nathanjordan/ghagen/commit/64bb6d9141c05f52c0510f3260c1966bdd81f06b))
* **emitter:** fix seq-item comments and auto-wrap multiline strings ([#9](https://github.com/nathanjordan/ghagen/issues/9)) ([5fd0bda](https://github.com/nathanjordan/ghagen/commit/5fd0bdaf380cdcd16800fddec5688f0aecbef378))
* **lint:** add duplicate-step-ids rule and drop mutable-defaults ([#6](https://github.com/nathanjordan/ghagen/issues/6)) ([1d5874d](https://github.com/nathanjordan/ghagen/commit/1d5874d952b377536c23e5ff49e5db75ce5497cd))
* **pin:** pin composite action steps alongside workflows ([dbd9aa4](https://github.com/nathanjordan/ghagen/commit/dbd9aa400357a75702eec03aa73b1382701108d1))


### Bug Fixes

* **pin:** skip token warning in --check mode ([4c09391](https://github.com/nathanjordan/ghagen/commit/4c09391cb34ab771d6bf2634eb04d584c4e98d1e))


### Documentation

* **roadmap:** mark action pinning as done ([#8](https://github.com/nathanjordan/ghagen/issues/8)) ([1149723](https://github.com/nathanjordan/ghagen/commit/114972386a2d0931b5c7a580d33f1b5e1394e49d))

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
