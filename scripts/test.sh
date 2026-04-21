#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> pytest"
uv run pytest

echo "==> vitest"
npm run test --prefix "$REPO_ROOT/packages/typescript"
