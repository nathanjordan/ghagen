#!/usr/bin/env bash
set -euo pipefail
GATE_NAME=typecheck GATE_SCOPES="py ts docs"
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

if in_scope docs; then
  # There is no separate "typecheck" step for docs: `astro build` (which runs
  # TypeDoc over packages/typescript/src/_docs-api-*.ts) is the only thing that
  # actually builds the site, so it is the docs equivalent of a type check here.
  # It needs packages/typescript installed too -- TypeDoc documents that package.
  need_node packages/typescript
  need_node docs

  # The build writes generated output (TypeDoc markdown into
  # src/content/docs/typescript/api/, plus .astro/ and dist/) that oxfmt does not
  # honor .gitignore for: a `scripts/fmt.sh docs` run after this one would trip
  # over content this gate produced. Clean it up on the way out, pass or fail, so
  # this gate is read-only like the others.
  trap 'rm -rf "$REPO_ROOT/docs/.astro" "$REPO_ROOT/docs/dist" "$REPO_ROOT/docs/src/content/docs/typescript/api"' EXIT

  step "astro build (docs)"
  npm run build --prefix "$REPO_ROOT/docs"
fi
