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
  echo "==> Ruff check"
  uv run ruff check packages/python/src/ packages/python/tests/
fi

if [[ "$SCOPE" == "ts" || "$SCOPE" == "all" ]]; then
  echo "==> oxlint (typescript)"
  npm run lint --prefix "$REPO_ROOT/packages/typescript"

  echo "==> oxlint (docs)"
  npm run lint --prefix "$REPO_ROOT/docs"
fi

# actionlint and `ghagen deps check-synced` are language-neutral (they don't belong to
# either the Python or TypeScript surface), so they only run under the default `all`
# scope -- a `py` or `ts` scoped call is meant to gate just that language's checks.
# CI's per-language lint jobs therefore call this script with `py`/`ts` and never see
# these two; a separate CI job runs them directly instead (see `.github/ghagen_workflows.py`).
if [[ "$SCOPE" == "all" ]]; then
  echo "==> actionlint"
  actionlint

  echo "==> ghagen deps check-synced"
  uv run ghagen deps check-synced
fi
