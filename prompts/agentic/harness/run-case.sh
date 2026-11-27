#!/bin/bash
# Run one PCP case from its case.py (see JOURNAL.md §7.3).
# usage: run-case.sh [--checks-only] [--dry-run] [--model MODEL] <tests/case-NNN-name>
set -euo pipefail
exec python3 "$(cd "$(dirname "$0")" && pwd)/pcp_case.py" "$@"
