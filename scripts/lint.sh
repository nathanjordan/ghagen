#!/usr/bin/env bash
set -euo pipefail
GATE_NAME=lint GATE_SCOPES="py ts docs meta" GATE_ALLOW_FIX=1
source "$(dirname "$0")/_gate.sh"
gate_parse "$@"

if [[ "$FIX" -eq 1 ]]; then NPM_LINT=lint:fix; else NPM_LINT=lint; fi

if in_scope py; then
  step "Ruff check"
  if [[ "$FIX" -eq 1 ]]; then
    uv run ruff check --fix "${PY_PATHS[@]}"
  else
    uv run ruff check "${PY_PATHS[@]}"
  fi

  # click 8.3+'s Result.output interleaves stdout and stderr in write order,
  # so an assertion against it can never pin which stream a line landed on --
  # see schema/cli-streams.yml. A bare `result.output` in test_cli/ is only
  # legitimate for a genuine total-absence claim ("must appear on neither
  # stream"), and those are required to carry a comment saying so.
  step "result.output usage is marked deliberate (test_cli)"
  output_hits="$(grep -n 'result\.output' packages/python/tests/test_cli/*.py | grep -v '``' || true)"
  bad=0
  if [[ -n "$output_hits" ]]; then
    while IFS=: read -r file lineno _; do
      context="$(sed -n "$((lineno > 6 ? lineno - 6 : 1)),${lineno}p" "$file")"
      if ! grep -q "Deliberately spans both streams" <<<"$context"; then
        echo "error: $file:$lineno: bare 'result.output' use -- add a 'Deliberately spans both streams' comment if this is a genuine total-absence claim, otherwise assert against result.stdout/result.stderr" >&2
        bad=1
      fi
    done <<<"$output_hits"
  fi
  if [[ "$bad" -ne 0 ]]; then exit 1; fi
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
