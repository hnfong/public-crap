#!/bin/bash
# Prune PCP leftovers. Default: remove stopped containers only.
# `--images` also removes images EXCEPT the pinned agent-sandbox:<tag>.
# usage: cleanup.sh [--images]
set -euo pipefail

TAG="${PCP_TAG:-1.0}"
KEEP="agent-sandbox:${TAG}"

echo "pruning stopped containers..."
container prune

if [ "${1:-}" = "--images" ]; then
  echo "removing images except ${KEEP}..."
  container image ls --format json | jq -r '.[] | .configuration.name // empty' \
    | grep -v -- "^${KEEP}$" \
    | while read -r img; do
        # skip digest-only rows; keep the base image (needed for cached rebuilds)
        case "$img" in
          sha256:*|"docker.io/library/debian"*|"ghcr.io/apple/container"*) continue ;;
        esac
        container image rm "$img" || true
      done
fi

echo "images kept:"
container image ls
