# Changelog

## [0.6.0](https://github.com/nathanjordan/ghagen/compare/v0.5.0...v0.6.0) (2026-04-23)


### ⚠ BREAKING CHANGES

* Model field names drop underscore prefixes (_kind -> kind, _data -> data, _meta -> meta, _keyOrder -> keyOrder, _sourceLocation -> sourceLocation). createModel() and modelToYamlMap() are removed. Model classes are now exported as values for instanceof.
* GhagenOptions.autoDedent renamed to auto_dedent to match the YAML key name.
* remove ghagen lint feature
* Configuration files must be migrated from .github/ghagen.toml to .ghagen.yml at the repo root. Lockfiles must be migrated from .github/ghagen.lock.toml to .ghagen.lock.yml. Entrypoint paths are now relative to the repo root instead of .github/.

### refactor\

* replace Symbol-branded model objects with class hierarchy ([2550b87](https://github.com/nathanjordan/ghagen/commit/2550b879b95b308787e7f2e68c98c36213de438c))


### feat\

* migrate configuration from TOML to .ghagen.yml ([cd2629c](https://github.com/nathanjordan/ghagen/commit/cd2629c2e34d21349ad6d570bc41bd088d3d13e3))
* remove ghagen lint feature ([0e05e34](https://github.com/nathanjordan/ghagen/commit/0e05e34757753a45a54c14a71cc90fa520057bee))


### Features

* add ModelKind union type for model kind discriminants ([35a56b4](https://github.com/nathanjordan/ghagen/commit/35a56b43a4ceda924dc81f9c7eca5d34ed2d074a))
* **docs:** add build step to dev script and update AGENTS.md ([a6f33ee](https://github.com/nathanjordan/ghagen/commit/a6f33ee30891e967f11846d7a67fb5ed2e4830ed))
* **docs:** generate LLM-friendly documentation with starlight-llms-txt ([f4c5376](https://github.com/nathanjordan/ghagen/commit/f4c5376d1638109ac5d8253c3eb7af7b05a28919))
* **docs:** group TypeScript API docs into 9 module sidebar sections ([e4143fe](https://github.com/nathanjordan/ghagen/commit/e4143febc2aefe74eb9fd2bac18a7a9d51d2cdcf))
* **release:** switch npm publish to OIDC trusted publishing ([9871653](https://github.com/nathanjordan/ghagen/commit/9871653409995a56ed637a04c7c52174fae35e6c))
* **scripts:** add docs dev server script ([ff5fc09](https://github.com/nathanjordan/ghagen/commit/ff5fc09e0aec0ae9da7229e44498813702f8c5f9))


### Bug Fixes

* remove unused imports and useless string concatenation ([a02bbc2](https://github.com/nathanjordan/ghagen/commit/a02bbc2f81e8509a4541db73caabb9081b5f433f))


### Code Refactoring

* replace manual config validation with Zod 4 schema ([d881e01](https://github.com/nathanjordan/ghagen/commit/d881e01aa1ae8a341e5bfedc6b941a995fefb4f4))

## [0.5.0](https://github.com/nathanjordan/ghagen/compare/v0.4.0...v0.5.0) (2026-04-21)

### Features

- add CI/local parity for lint, format, and type checks ([eb40f1b](https://github.com/nathanjordan/ghagen/commit/eb40f1b4e35491e8805c75948bd30eceb570b179))
- add top-level lint/fmt/test scripts and simplify pre-commit hooks ([f07bc1a](https://github.com/nathanjordan/ghagen/commit/f07bc1a91529451dc8d4d2dbf5d6794219da9b80))
- **docs:** render TypeScript API members as HTML tables ([b986b5a](https://github.com/nathanjordan/ghagen/commit/b986b5a8818f8e1f25caf8e6b7f1e97fbdc7ae67))
- replace field_comments/field_eol_comments with withComment/withEolComment wrappers ([6eb57bb](https://github.com/nathanjordan/ghagen/commit/6eb57bbb067fe1e816e92695a8cb470b32cdfdfe))
- **typescript:** add App, CLI, pin, lint, and config subsystems ([9553551](https://github.com/nathanjordan/ghagen/commit/95535511ecc3a0b2f5c9f2a5e65ed90f75bb54e9))

### Bug Fixes

- **ci:** resolve pyright, ruff, and oxfmt failures ([66d8a8e](https://github.com/nathanjordan/ghagen/commit/66d8a8e22232c3de760d265225051ccb59b69171))
- **deps:** prune stale lockfile entries by default and fix oxlint errors ([752cd22](https://github.com/nathanjordan/ghagen/commit/752cd224140c9fc94e1c69fabb68f86006807f25))
- **docs:** apply oxfmt formatting to docs content files ([8b133ae](https://github.com/nathanjordan/ghagen/commit/8b133ae4eb8da0c22e1effeed696842dc2367906))
- **docs:** install TypeScript package deps before docs build ([35c429b](https://github.com/nathanjordan/ghagen/commit/35c429bb3e8959eb7d2cf3dcec5076d9d04db99f))
- **docs:** skip TypeDoc error checking during build ([a8207e4](https://github.com/nathanjordan/ghagen/commit/a8207e41e9e50401797f3e5373d9d17183f19036))
- **release:** single approval gate, clean up tags and changelogs ([1bb0b4e](https://github.com/nathanjordan/ghagen/commit/1bb0b4e461c6e75e75f7b43fcda4d563a51b8ed6))

### Documentation

- add local docs server instructions to AGENTS.md ([7487e50](https://github.com/nathanjordan/ghagen/commit/7487e5075ca49fed49926c8b7e2bc258875f46ff))
- add Why section and expand Features list in README ([8d84fc9](https://github.com/nathanjordan/ghagen/commit/8d84fc9f5eeae6d84760a195d5b0e8af467f9ab2))
- bring TypeScript documentation to parity with Python ([bda81e4](https://github.com/nathanjordan/ghagen/commit/bda81e458ba3a4ee0a334f97334c3b69e63b43ab))
- clean up documentation for developer audience ([e32768c](https://github.com/nathanjordan/ghagen/commit/e32768c9d82f730bdc1d2ed3d7b5f68d0c3fc4cf))
- clean up TypeScript API pages with concise formatting ([09fa292](https://github.com/nathanjordan/ghagen/commit/09fa2926b934e313ba175628c29a292a64e7aa81))
- fix typos and improve README clarity ([2b92acb](https://github.com/nathanjordan/ghagen/commit/2b92acbe4addb0ce3f77b3cbb330e453149cd2b6))
- flatten TypeScript API sidebar into a single list ([e12c722](https://github.com/nathanjordan/ghagen/commit/e12c722fa5f8a3fb0ab0be97a4c7208b843d0ec3))
- improve examples, navigation, and add raw YAML passthrough ([224fa75](https://github.com/nathanjordan/ghagen/commit/224fa7508c5f480c233e2604bce3b11d70f6b16e))
- move "Why" section from README to docs home page ([893b5a8](https://github.com/nathanjordan/ghagen/commit/893b5a83106346992dae919844d4c22bfde2ca70))
- move "you probably don't need this" note below features ([39461f5](https://github.com/nathanjordan/ghagen/commit/39461f5da7e1b8c212f873310e08c2b6a8615b59))
- remove dependency update action design spec ([6e4f632](https://github.com/nathanjordan/ghagen/commit/6e4f632b5fabd9dacbfbcc610b63fa4d7959ff1e))
- remove getting-started, FAQ, and unpinned-actions references ([2b062f4](https://github.com/nathanjordan/ghagen/commit/2b062f4e804ece7d56f687563bd8ad04c652e637))
- restructure README with per-tool quickstarts and inline FAQ ([1dba769](https://github.com/nathanjordan/ghagen/commit/1dba769875aea916141774018a0ba56c0640936f))
- switch Starlight theme to rapide ([0e8a58b](https://github.com/nathanjordan/ghagen/commit/0e8a58b092bd8261ed98e08c9126d7473495ca72))
- trim completed items from ROADMAP and reformat ([a42bf61](https://github.com/nathanjordan/ghagen/commit/a42bf61b9c80d73a4115b6135492041947c3b304))
- update README to reflect TypeScript App/synth parity ([5f89560](https://github.com/nathanjordan/ghagen/commit/5f895606d7eb1e237944bda4755517ae7481f567))

## [0.4.0](https://github.com/nathanjordan/ghagen/compare/v0.3.2...v0.4.0) (2026-04-15)

### ⚠ BREAKING CHANGES

- checkout(), setup_python(), setup_uv(), setup_node(), cache(), upload_artifact(), download_artifact() helpers removed. Use Step(uses=...) directly.

### Features

- add oxlint and oxfmt for TypeScript and docs packages ([688c77e](https://github.com/nathanjordan/ghagen/commit/688c77eb0e01e831b66b5f788fd262e285ba444d))
- remove predefined step helpers in favor of direct Step() usage ([869ff2f](https://github.com/nathanjordan/ghagen/commit/869ff2f6235e027cbf6776df114ae4159ee807a4))

### Bug Fixes

- **release:** switch to v0.X.Y tags and add rolling major version tag ([696c723](https://github.com/nathanjordan/ghagen/commit/696c7236f6ab2bb9fb01bb42d697a94c55f35ddb))

## [0.3.2](https://github.com/nathanjordan/ghagen/compare/v0.3.1...v0.3.2) (2026-04-15)

### Bug Fixes

- **release:** rename npm package to @ghagen/ghagen for scoped publishing ([a60cc87](https://github.com/nathanjordan/ghagen/commit/a60cc87fcf36230c2f5a12a72a284b67ffa5912f))

### Documentation

- migrate from MkDocs to Astro Starlight with TypeScript support ([580dda1](https://github.com/nathanjordan/ghagen/commit/580dda175c5e7d4791d6ef1cc8e5ffd6e54b686e))

## [0.3.1](https://github.com/nathanjordan/ghagen/compare/v0.3.0...v0.3.1) (2026-04-14)

### Bug Fixes

- **release:** correct release-please output key for TypeScript package ([2967da0](https://github.com/nathanjordan/ghagen/commit/2967da0489daed0f95e266321df074ce02cff9f4))
- **release:** reset TypeScript manifest to 0.1.0 for re-release ([ab1f20a](https://github.com/nathanjordan/ghagen/commit/ab1f20aff62cc54fb1ec026a1b8986923c6ffce4))

## [0.3.0](https://github.com/nathanjordan/ghagen/compare/v0.2.1...v0.3.0) (2026-04-14)

### ⚠ BREAKING CHANGES

- **emitter:** configurable header with source-file templating
- add action.yml generation and redesign App API ([#4](https://github.com/nathanjordan/ghagen/issues/4))

### Features

- add action.yml generation and redesign App API ([#4](https://github.com/nathanjordan/ghagen/issues/4)) ([10914bb](https://github.com/nathanjordan/ghagen/commit/10914bb8768d2a4fc390a3c86dca6f80c80c5805))
- add `ghagen pin` command with SHA lockfile ([#7](https://github.com/nathanjordan/ghagen/issues/7)) ([a138ee0](https://github.com/nathanjordan/ghagen/commit/a138ee06b858e376ed4948bf893dc5b2937510b9))
- add CI job to test composite action via uses: ./ ([f02a3ed](https://github.com/nathanjordan/ghagen/commit/f02a3ed27b9d930fab150fac3ba19daef6df82bb))
- add ghagen lint command with rule engine ([#5](https://github.com/nathanjordan/ghagen/issues/5)) ([3e7d3da](https://github.com/nathanjordan/ghagen/commit/3e7d3da76db019d83da87a7c56be976fa625b557))
- add ghagen update action for automated dependency updates ([78d19b4](https://github.com/nathanjordan/ghagen/commit/78d19b476fa945c2d26042865cb2852f8177cc35))
- add Homebrew tap automation and install docs ([60dd99c](https://github.com/nathanjordan/ghagen/commit/60dd99cc828d594db0784f37ac435e8694530c40))
- **cli:** add `entrypoint` key to .github/ghagen.toml ([16f5156](https://github.com/nathanjordan/ghagen/commit/16f5156ff68ff0e3aa9788b2af504b1104e0be2f))
- **cli:** add `ghagen outdated` command for update detection ([f1a1dff](https://github.com/nathanjordan/ghagen/commit/f1a1dff8166a3d85029e501e178fcf97e74452ba))
- **emitter:** configurable header with source-file templating ([64bb6d9](https://github.com/nathanjordan/ghagen/commit/64bb6d9141c05f52c0510f3260c1966bdd81f06b))
- **emitter:** fix seq-item comments and auto-wrap multiline strings ([#9](https://github.com/nathanjordan/ghagen/issues/9)) ([5fd0bda](https://github.com/nathanjordan/ghagen/commit/5fd0bdaf380cdcd16800fddec5688f0aecbef378))
- **lint:** add duplicate-step-ids rule and drop mutable-defaults ([#6](https://github.com/nathanjordan/ghagen/issues/6)) ([1d5874d](https://github.com/nathanjordan/ghagen/commit/1d5874d952b377536c23e5ff49e5db75ce5497cd))
- **pin:** add list_tags() for paginated tag listing via GitHub API ([483589b](https://github.com/nathanjordan/ghagen/commit/483589bc7b32fb0fa1188659b3bd9bd64f034fa4))
- **pin:** add source tracking module for uses ref location ([189e3db](https://github.com/nathanjordan/ghagen/commit/189e3dbcae78dc8b2ab17e3e4c8e14b0e7268be7))
- **pin:** add source update module for applying version bumps ([1838832](https://github.com/nathanjordan/ghagen/commit/18388323463539b94cdc8c872d39417038a72943))
- **pin:** add version comparison module for action tags ([a416844](https://github.com/nathanjordan/ghagen/commit/a416844054cc878e8386b21b24179d9c27385a53))
- **pin:** pin composite action steps alongside workflows ([dbd9aa4](https://github.com/nathanjordan/ghagen/commit/dbd9aa400357a75702eec03aa73b1382701108d1))
- **release:** add npm publishing for TypeScript package ([1a50b45](https://github.com/nathanjordan/ghagen/commit/1a50b454f31de02dd106604133c27a359f6d38ac))
- restructure into monorepo with TypeScript package skeleton ([#20](https://github.com/nathanjordan/ghagen/issues/20)) ([e997f15](https://github.com/nathanjordan/ghagen/commit/e997f15acec46136d57386498e60ce644d89967e))
- **step:** auto-dedent triple-quoted strings in Step.run ([0dac976](https://github.com/nathanjordan/ghagen/commit/0dac97625f778fcbd34129c391942c1653773efd))
- **typescript:** implement model layer with factory functions and YAML serializer ([0ca3e2d](https://github.com/nathanjordan/ghagen/commit/0ca3e2d389cf4639d175053f419a5a6fe5fd9925))

### Bug Fixes

- add release environment to homebrew-bump job ([5f80ca1](https://github.com/nathanjordan/ghagen/commit/5f80ca10606ed0d8b7da61b079f5ad0500f985a3))
- address code review findings for outdated command ([b808e64](https://github.com/nathanjordan/ghagen/commit/b808e64f684b8a13ff3fab47c885014a79dda079))
- **pin:** skip token warning in --check mode ([4c09391](https://github.com/nathanjordan/ghagen/commit/4c09391cb34ab771d6bf2634eb04d584c4e98d1e))
- **release:** bump minor (not major) for breaking changes pre-1.0 ([#11](https://github.com/nathanjordan/ghagen/issues/11)) ([687fd3e](https://github.com/nathanjordan/ghagen/commit/687fd3ecea704007b665d2d1e2c58843f08cd395))

### Documentation

- add AGENTS.md with project overview and agent instructions ([1e862a8](https://github.com/nathanjordan/ghagen/commit/1e862a866952acfe1f60b0f4466410a5f75b4e8d))
- **mkdocs:** switch theme to amber accent with factory logo ([7d2ab9a](https://github.com/nathanjordan/ghagen/commit/7d2ab9a5f852e8a2fe698f83aabcd62705f003e8))
- note that ghagen supports actions defined in this repo ([f41e240](https://github.com/nathanjordan/ghagen/commit/f41e2409d1a4f1b8dd24ec90f26e821be710af18))
- require documentation updates for user-facing changes ([e7b96e1](https://github.com/nathanjordan/ghagen/commit/e7b96e145a7a27f6a6d458e13efea456510717ea))
- **roadmap:** mark action pinning as done ([#8](https://github.com/nathanjordan/ghagen/issues/8)) ([1149723](https://github.com/nathanjordan/ghagen/commit/114972386a2d0931b5c7a580d33f1b5e1394e49d))
- update AGENTS.md to reflect TypeScript/JavaScript support ([78de75b](https://github.com/nathanjordan/ghagen/commit/78de75b764330faad363c7c2b5d6bc71f3ecfd17))

## [0.2.1](https://github.com/nathanjordan/ghagen/compare/v0.2.0...v0.2.1) (2026-04-07)

### Bug Fixes

- add contents:read permission to publish job ([a7cb3fb](https://github.com/nathanjordan/ghagen/commit/a7cb3fb283239dc2b40735d2cde063648b85fd83))

## [0.2.0](https://github.com/nathanjordan/ghagen/compare/v0.1.0...v0.2.0) (2026-04-07)

### Features

- add actionlint to pre-commit and CI lint job ([59198c2](https://github.com/nathanjordan/ghagen/commit/59198c20824e3bc4a5fc693d3d5bf82dc72c2ff7))
- add composite GitHub Action for workflow freshness checking ([178728b](https://github.com/nathanjordan/ghagen/commit/178728b9981cf237cd2db75309dd32d1748d0c03))
- add DRY helpers — step factories and expression builder ([3b1fabf](https://github.com/nathanjordan/ghagen/commit/3b1fabf651308ca019cb0b977e360fada9d35545))
- add Release Please automation for PyPI publishing (Milestone 5) ([6f48ab3](https://github.com/nathanjordan/ghagen/commit/6f48ab39f465ed423bd1b508490a74dd7fbcd7a0))
- add schema pipeline for drift detection ([637fafc](https://github.com/nathanjordan/ghagen/commit/637fafc13027ee5f57cb1f4037ac1d309fa21d11))
- dogfood ghagen for own CI/CD workflows ([949acf9](https://github.com/nathanjordan/ghagen/commit/949acf9858bdff5414e7d2e6c482abf85b1fe3be))
- initial implementation of ghagen core library ([8651ab0](https://github.com/nathanjordan/ghagen/commit/8651ab03893ff80b83a8fb03890a82d23180efa0))

### Bug Fixes

- resolve ruff lint errors in new test files ([9b409a1](https://github.com/nathanjordan/ghagen/commit/9b409a1a61dde62ee81df40537bd2829a0927b3d))

### Documentation

- add detailed ROADMAP.md for remaining work ([17e249c](https://github.com/nathanjordan/ghagen/commit/17e249c07dcf469b295a2f886f629c90f87f1196))
- add MkDocs-Material documentation site and README (Milestone 4) ([1885543](https://github.com/nathanjordan/ghagen/commit/1885543804ca0b70f0fe500042a8b86ecfd37186))
- update ROADMAP.md — mark Milestone 3 complete ([203c9b5](https://github.com/nathanjordan/ghagen/commit/203c9b55a8f212c02a6378c0cd2c05f1444af0c3))

## [0.1.0](https://github.com/nathanjordan/ghagen/releases/tag/v0.1.0) (2026-04-07)

Initial release — generate GitHub Actions workflow YAML from Python code.
