#!/bin/bash
# PCP harness smoke test (chunk 6 validation; NOT an agent/model test).
# Runs in the guest as the non-root 'agent' user. Verifies the harness
# plumbing: mounts, per-run pi config, sshd/tunnel, results capture.
set -uo pipefail

OUT=/results
mkdir -p "$OUT"

{
  echo "== PCP harness smoke =="
  echo "user: $(id)"
  echo "cwd:  $(pwd)"
  echo "node: $(node --version)"
  echo "npm:  $(npm --version)"
  echo "rust: $(rustc --version)"
  echo "cargo: $(cargo --version)"
  echo "clang: $(clang --version | head -1)"
  echo "python: $(python3 --version)"
  echo "java:  $(java -version 2>&1 | head -1)"
  echo "pi:    $(pi --version)"
  echo "git:   $(git --version)"
} > "${OUT}/toolchain.txt" 2>&1

# pi config visible as expected? (mounted per run; no secrets)
cp /home/agent/.pi/agent/settings.json "${OUT}/pi-settings.json" 2>&1

# informational probe of the model endpoint through the ssh tunnel.
# 000 / empty just means no model was served during this run.
CODE="$(curl -s -m 5 -o "${OUT}/model-probe.json" \
  -w '%{http_code}' "http://127.0.0.1:${PCP_MODEL_PORT:-9931}/v1/models" \
  || echo 000)"
echo "$CODE" > "${OUT}/model-probe.http"

# verdict: toolchain versions present
if grep -q "^node: v" "${OUT}/toolchain.txt" \
   && grep -q "^pi: " "${OUT}/toolchain.txt"; then
  echo PASS > "${OUT}/verdict.txt"
  exit 0
else
  echo FAIL > "${OUT}/verdict.txt"
  exit 1
fi
