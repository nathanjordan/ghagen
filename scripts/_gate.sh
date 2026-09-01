#!/usr/bin/env bash
# The gate interface: usage, error mode, flag admissibility, prerequisites.
# Sourced by scripts/{lint,fmt,typecheck,test,docs-dev}.sh -- never executed.
#
# Each gate declares its own scope set, before sourcing:
#     GATE_NAME=lint GATE_SCOPES="py ts docs meta" GATE_ALLOW_FIX=1
# `all` is implicit and always means "every scope this gate declares".
#
# Every conditional below is an `if` block rather than an `&&` list: this file is
# sourced by callers running under `set -e`, where a bare `[[ ... ]] && ...` that
# evaluates false would abort the caller.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Every Python root in the repo, named once so the three `py` gates cannot
# disagree about what they cover. Each gate used to spell its own list out, and
# the three lists drifted apart -- see docs/issues/32 (and docs/issues/17, the
# half-fix it is residue from). `scripts/` and `.github/ghagen_workflows.py` are
# dev tooling rather than shipped package code (ADR-0003), but they are Python
# source and the gates must see them: the latter is the single source for every
# file under `.github/workflows/`.
#
# Paths are repo-root-relative because the gates are documented to run from the
# repo root, and relative paths keep ruff/pyright diagnostics short.
PY_PATHS=(
  packages/python/src/
  packages/python/tests/
  scripts/
  .github/ghagen_workflows.py
)

# Every gate now covers every root: pyright used to skip packages/python/tests/,
# which is where every Python test lives, so no Python test file was checked by
# anything (docs/issues/09). The subtraction that arranged that is gone, and
# PY_PATHS_TYPED is kept as a name only so the typecheck gate reads like its two
# siblings -- if a root ever has to be dropped from one gate again, this is the
# place, and the divergence is visible here rather than inside a gate script.
PY_PATHS_TYPED=("${PY_PATHS[@]}")

: "${GATE_NAME:?_gate.sh: set GATE_NAME before sourcing}"
: "${GATE_ALLOW_FIX:=0}" # gates that support --fix set this to 1

SCOPE="all"
FIX=0

# Print the usage string (optionally prefixed by an error) and exit 1.
gate_usage() { # reader 1 of GATE_SCOPES
  if [[ $# -gt 0 ]]; then
    echo "error: scripts/$GATE_NAME.sh: $1" >&2
  fi
  local flags=""
  if [[ "$GATE_ALLOW_FIX" -eq 1 ]]; then flags=" [--fix]"; fi
  local vals
  vals="$(echo "$GATE_SCOPES all" | tr ' ' '|')"
  echo "Usage: scripts/$GATE_NAME.sh [$vals]$flags   (default: all)" >&2
  exit 1
}

# True iff this gate declares the given scope value.
_gate_declares() { # reader 2 of GATE_SCOPES
  local s
  for s in $GATE_SCOPES all; do
    if [[ "$s" == "$1" ]]; then return 0; fi
  done
  return 1
}

# Parse the gate's argv into SCOPE and FIX. Exactly one scope per invocation.
gate_parse() {
  : "${GATE_SCOPES:?_gate.sh: set GATE_SCOPES before calling gate_parse}"
  local seen=0
  local arg
  for arg in "$@"; do
    if [[ "$arg" == "--fix" ]]; then
      if [[ "$GATE_ALLOW_FIX" -ne 1 ]]; then gate_usage "--fix is not accepted by this gate"; fi
      FIX=1
      continue
    fi
    if ! _gate_declares "$arg"; then gate_usage "no '$arg' scope"; fi
    if [[ "$seen" -ne 0 ]]; then gate_usage "one scope per invocation"; fi
    SCOPE="$arg"
    seen=1
  done
}

# True when the requested scope selects the named one (or is the `all` union).
in_scope() { [[ "$SCOPE" == "$1" || "$SCOPE" == "all" ]]; }

step() { echo "==> $1"; }

# Declared prerequisite. Turns `oxlint: command not found` into a diagnosis.
need_node() {
  if [[ -d "$REPO_ROOT/$1/node_modules" ]]; then return 0; fi
  echo "error: scripts/$GATE_NAME.sh needs the '$1' toolchain, which is not installed." >&2
  echo "       run: npm ci --prefix $1" >&2
  exit 1
}
