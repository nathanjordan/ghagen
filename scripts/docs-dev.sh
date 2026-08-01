#!/usr/bin/env bash
set -euo pipefail
# Not a scoped gate: sources _gate.sh for need_node/step only, never gate_parse.
GATE_NAME=docs-dev
source "$(dirname "$0")/_gate.sh"

need_node docs

step "Building docs"
npm run build --prefix "$REPO_ROOT/docs"

step "Starting docs dev server"
exec npm run dev --prefix "$REPO_ROOT/docs"
