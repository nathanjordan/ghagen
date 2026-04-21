#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Pyright (python)"
uv run pyright packages/python/src/

echo "==> tsc (typescript)"
npm run typecheck --prefix "$REPO_ROOT/packages/typescript"
