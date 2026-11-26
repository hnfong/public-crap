#!/bin/bash
# Run a command inside a throwaway guest container with the case artifacts
# mounted. Used by checks that must execute Linux artifacts (build, run,
# strace). cwd inside the container = /artifacts/workspace; case dir at
# /case (read-only). Nothing installed on the host.
# usage: in-guest.sh '<shell command>'
set -euo pipefail
TAG="${PCP_TAG:-1.1}"
: "${PCP_ARTIFACTS:?must be set}"
: "${PCP_CASE_DIR:?must be set}"
exec container run --rm \
  -v "${PCP_ARTIFACTS}:/artifacts" \
  -v "${PCP_CASE_DIR}:/case:ro" \
  -w /artifacts/workspace \
  "agent-sandbox:${TAG}" bash -c "$1"
