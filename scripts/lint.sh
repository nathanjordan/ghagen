#!/usr/bin/env bash
set -euo pipefail
GATE_NAME=lint GATE_SCOPES="py ts docs meta" GATE_ALLOW_FIX=1
source "$(dirname "$0")/_gate.sh"
gate_parse "$@"

if [[ "$FIX" -eq 1 ]]; then NPM_LINT=lint:fix; else NPM_LINT=lint; fi

if in_scope py; then
  step "Ruff check"
  if [[ "$FIX" -eq 1 ]]; then
    uv run ruff check --fix packages/python/src/ packages/python/tests/
  else
    uv run ruff check packages/python/src/ packages/python/tests/
  fi
fi

if in_scope ts; then
  need_node packages/typescript
  step "oxlint (typescript)"
  npm run "$NPM_LINT" --prefix "$REPO_ROOT/packages/typescript"
fi

if in_scope docs; then
  need_node docs
  step "oxlint (docs)"
  npm run "$NPM_LINT" --prefix "$REPO_ROOT/docs"
fi

if in_scope meta; then
  step "ghagen deps check-synced"
  uv run ghagen deps check-synced

  # ghagen_schema/generate.py shells `npm run generate-types` in the TS package.
  need_node packages/typescript
  step "Schema types up to date"
  PYTHONPATH=scripts uv run python -m ghagen_schema check
fi
