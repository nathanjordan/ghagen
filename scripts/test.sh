#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

SCOPE="${1:-all}"
case "$SCOPE" in
  py | ts | all) ;;
  *)
    echo "Usage: $0 [py|ts|all]" >&2
    exit 1
    ;;
esac

if [[ "$SCOPE" == "py" || "$SCOPE" == "all" ]]; then
  echo "==> pytest"
  uv run pytest
fi

if [[ "$SCOPE" == "ts" || "$SCOPE" == "all" ]]; then
  echo "==> vitest"
  npm run test --prefix "$REPO_ROOT/packages/typescript"
fi
