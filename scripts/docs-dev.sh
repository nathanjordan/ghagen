#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Building docs"
npm run build --prefix "$REPO_ROOT/docs"

echo "==> Starting docs dev server"
exec npm run dev --prefix "$REPO_ROOT/docs"
