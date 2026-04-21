#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "${1:-}" == "--fix" ]]; then
  echo "==> Ruff format (fix)"
  uv run ruff format packages/python/src/ packages/python/tests/

  echo "==> oxfmt (typescript, fix)"
  npm run fmt --prefix "$REPO_ROOT/packages/typescript"

  echo "==> oxfmt (docs, fix)"
  npm run fmt --prefix "$REPO_ROOT/docs"
else
  echo "==> Ruff format (check)"
  uv run ruff format --check packages/python/src/ packages/python/tests/

  echo "==> oxfmt (typescript, check)"
  npm run fmt:check --prefix "$REPO_ROOT/packages/typescript"

  echo "==> oxfmt (docs, check)"
  npm run fmt:check --prefix "$REPO_ROOT/docs"
fi
