#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Ruff check"
uv run ruff check packages/python/src/ packages/python/tests/

echo "==> oxlint (typescript)"
npm run lint --prefix "$REPO_ROOT/packages/typescript"

echo "==> oxlint (docs)"
npm run lint --prefix "$REPO_ROOT/docs"
