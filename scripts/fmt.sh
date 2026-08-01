#!/usr/bin/env bash
set -euo pipefail
GATE_NAME=fmt GATE_SCOPES="py ts docs" GATE_ALLOW_FIX=1
source "$(dirname "$0")/_gate.sh"
gate_parse "$@"

if [[ "$FIX" -eq 1 ]]; then
  NPM_FMT=fmt
  MODE=fix
else
  NPM_FMT=fmt:check
  MODE=check
fi

if in_scope py; then
  step "Ruff format ($MODE)"
  if [[ "$FIX" -eq 1 ]]; then
    uv run ruff format packages/python/src/ packages/python/tests/
  else
    uv run ruff format --check packages/python/src/ packages/python/tests/
  fi
fi

if in_scope ts; then
  need_node packages/typescript
  step "oxfmt (typescript, $MODE)"
  npm run "$NPM_FMT" --prefix "$REPO_ROOT/packages/typescript"
fi

if in_scope docs; then
  need_node docs
  step "oxfmt (docs, $MODE)"
  npm run "$NPM_FMT" --prefix "$REPO_ROOT/docs"
fi
