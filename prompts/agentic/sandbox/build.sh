#!/bin/bash
# Build the PCP guest image and print its digest.
# usage: build.sh <tag>
set -euo pipefail

TAG="${1:?usage: build.sh <tag>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

container build --progress plain -t "agent-sandbox:${TAG}" "${ROOT}/sandbox"

DIGEST="$(container image ls --format json | jq -r --arg ref "agent-sandbox:${TAG}" \
  'first(.[] | select((.configuration.name // "" | split("/")[-1]) == $ref) | .configuration.descriptor.digest)')"
printf 'built agent-sandbox:%s\n%s\n' "${TAG}" "${DIGEST}"
mkdir -p "${ROOT}/sandbox/.digests"
printf '%s\n' "${DIGEST}" > "${ROOT}/sandbox/.digests/${TAG}"
