#!/usr/bin/env bash
set -euo pipefail
GATE_NAME=typecheck GATE_SCOPES="py ts"
source "$(dirname "$0")/_gate.sh"
gate_parse "$@"

if in_scope py; then
  step "Pyright (python)"
  uv run pyright packages/python/src/
fi

if in_scope ts; then
  need_node packages/typescript
  step "tsc (typescript)"
  npm run typecheck --prefix "$REPO_ROOT/packages/typescript"
fi
