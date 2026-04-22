#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Starting docs dev server"
exec npm run dev --prefix "$REPO_ROOT/docs"
