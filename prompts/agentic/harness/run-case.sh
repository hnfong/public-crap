#!/bin/bash
# Run one PCP case from its case.toml (see JOURNAL.md §7).
# usage: run-case.sh [--checks-only] [--dry-run] <tests/case-NNN-name>
set -euo pipefail

# needs tomllib (python >= 3.11); macOS default python3 may be older
PY=""
for c in python3.14 python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import tomllib' 2>/dev/null; then
    PY="$c"; break
  fi
done
[ -n "$PY" ] || { echo "run-case: need python >= 3.11 (tomllib) on PATH" >&2; exit 1; }

exec "$PY" "$(cd "$(dirname "$0")" && pwd)/pcp_case.py" "$@"
