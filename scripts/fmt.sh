#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

FIX=0
SCOPE="all"
for arg in "$@"; do
  case "$arg" in
    --fix) FIX=1 ;;
    py | ts | all) SCOPE="$arg" ;;
    *)
      echo "Usage: $0 [py|ts|all] [--fix]" >&2
      exit 1
      ;;
  esac
done

if [[ "$FIX" -eq 1 ]]; then
  if [[ "$SCOPE" == "py" || "$SCOPE" == "all" ]]; then
    echo "==> Ruff format (fix)"
    uv run ruff format packages/python/src/ packages/python/tests/
  fi

  if [[ "$SCOPE" == "ts" || "$SCOPE" == "all" ]]; then
    echo "==> oxfmt (typescript, fix)"
    npm run fmt --prefix "$REPO_ROOT/packages/typescript"

    echo "==> oxfmt (docs, fix)"
    npm run fmt --prefix "$REPO_ROOT/docs"
  fi
else
  if [[ "$SCOPE" == "py" || "$SCOPE" == "all" ]]; then
    echo "==> Ruff format (check)"
    uv run ruff format --check packages/python/src/ packages/python/tests/
  fi

  if [[ "$SCOPE" == "ts" || "$SCOPE" == "all" ]]; then
    echo "==> oxfmt (typescript, check)"
    npm run fmt:check --prefix "$REPO_ROOT/packages/typescript"

    echo "==> oxfmt (docs, check)"
    npm run fmt:check --prefix "$REPO_ROOT/docs"
  fi
fi
