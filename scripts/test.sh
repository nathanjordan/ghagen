#!/usr/bin/env bash
set -euo pipefail
GATE_NAME=test GATE_SCOPES="py ts"
source "$(dirname "$0")/_gate.sh"
gate_parse "$@"

if in_scope py; then
  step "pytest"
  uv run pytest
fi

if in_scope ts; then
  need_node packages/typescript
  step "vitest"
  npm run test --prefix "$REPO_ROOT/packages/typescript"
fi
