# Changelog

## [0.3.0](https://github.com/nathanjordan/ghagen/compare/ghagen-js-v0.2.1...ghagen-js-v0.3.0) (2026-04-15)


### ⚠ BREAKING CHANGES

* checkout(), setup_python(), setup_uv(), setup_node(), cache(), upload_artifact(), download_artifact() helpers removed. Use Step(uses=...) directly.

### feat\

* remove predefined step helpers in favor of direct Step() usage ([869ff2f](https://github.com/nathanjordan/ghagen/commit/869ff2f6235e027cbf6776df114ae4159ee807a4))


### Features

* add oxlint and oxfmt for TypeScript and docs packages ([688c77e](https://github.com/nathanjordan/ghagen/commit/688c77eb0e01e831b66b5f788fd262e285ba444d))

## [0.2.1](https://github.com/nathanjordan/ghagen/compare/ghagen-js-v0.2.0...ghagen-js-v0.2.1) (2026-04-15)

### Bug Fixes

- **release:** rename npm package to @ghagen/ghagen for scoped publishing ([a60cc87](https://github.com/nathanjordan/ghagen/commit/a60cc87fcf36230c2f5a12a72a284b67ffa5912f))

## [0.2.0](https://github.com/nathanjordan/ghagen/compare/ghagen-js-v0.1.0...ghagen-js-v0.2.0) (2026-04-14)

### Features

- **release:** add npm publishing for TypeScript package ([1a50b45](https://github.com/nathanjordan/ghagen/commit/1a50b454f31de02dd106604133c27a359f6d38ac))
- restructure into monorepo with TypeScript package skeleton ([#20](https://github.com/nathanjordan/ghagen/issues/20)) ([e997f15](https://github.com/nathanjordan/ghagen/commit/e997f15acec46136d57386498e60ce644d89967e))
- **typescript:** implement model layer with factory functions and YAML serializer ([0ca3e2d](https://github.com/nathanjordan/ghagen/commit/0ca3e2d389cf4639d175053f419a5a6fe5fd9925))

### Bug Fixes

- **release:** reset TypeScript manifest to 0.1.0 for re-release ([ab1f20a](https://github.com/nathanjordan/ghagen/commit/ab1f20aff62cc54fb1ec026a1b8986923c6ffce4))

## [0.2.0](https://github.com/nathanjordan/ghagen/compare/ghagen-js-v0.1.0...ghagen-js-v0.2.0) (2026-04-14)

### Features

- **release:** add npm publishing for TypeScript package ([1a50b45](https://github.com/nathanjordan/ghagen/commit/1a50b454f31de02dd106604133c27a359f6d38ac))
- restructure into monorepo with TypeScript package skeleton ([#20](https://github.com/nathanjordan/ghagen/issues/20)) ([e997f15](https://github.com/nathanjordan/ghagen/commit/e997f15acec46136d57386498e60ce644d89967e))
- **typescript:** implement model layer with factory functions and YAML serializer ([0ca3e2d](https://github.com/nathanjordan/ghagen/commit/0ca3e2d389cf4639d175053f419a5a6fe5fd9925))
