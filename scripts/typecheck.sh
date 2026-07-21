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
  echo "==> Pyright (python)"
  uv run pyright packages/python/src/
fi

if [[ "$SCOPE" == "ts" || "$SCOPE" == "all" ]]; then
  echo "==> tsc (typescript)"
  npm run typecheck --prefix "$REPO_ROOT/packages/typescript"
fi
