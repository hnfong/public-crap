#!/bin/bash
# Run one PCP test case: one ephemeral Linux VM (fresh `container run --rm`)
# per run. Run parameters (owner decision): (MODEL, TEST_CASE); all tunables
# are PCP_* env vars.
#
# usage: run-test.sh [--dry-run] <tests/case-NNN-name>
#
# Env overrides (defaults):
#   PCP_TAG            image tag                    (1.0)
#   PCP_MODEL          model name (run parameter)   (unset)
#   PCP_MODEL_PORT     host llama.cpp port          (9931; host binds 127.0.0.1)
#   PCP_CPUS           guest CPUs                   (2)
#   PCP_MEMORY         guest memory                 (4G)
#   PCP_NET            network: default=internet, internal=offline (default)
#   PCP_TIMEOUT_SECS   test timeout                 (1800)
#   PCP_CONTEXT_WINDOW model context window         (262144)
#   PCP_GUEST_SCRIPT   host path to a guest script to run instead of
#                      /work/run.sh (mounted ro at /pcp-run; used by
#                      harness/run-case.sh for case.toml-driven cases)
#
# Connectivity (no sudo, no DNS host-bridge — owner decision): the harness
# generates an ephemeral SSH keypair, mounts the public key into the guest,
# and opens a reverse tunnel host->guest so the guest reaches the host's
# loopback model server at http://127.0.0.1:$PCP_MODEL_PORT/v1.
set -euo pipefail

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
  shift
fi
[ $# -eq 1 ] || { echo "usage: run-test.sh [--dry-run] <tests/case-NNN-name>" >&2; exit 2; }

CASE_DIR="$(cd "$1" 2>/dev/null && pwd)" || { echo "case dir not found: $1" >&2; exit 2; }
# run.sh is required only for legacy (phase-1) cases; case.toml cases inject
# their guest script via PCP_GUEST_SCRIPT instead
if [ -z "${PCP_GUEST_SCRIPT:-}" ] && [ ! -f "${CASE_DIR}/run.sh" ]; then
  echo "no run.sh in ${CASE_DIR}" >&2; exit 2
fi
CASE_NAME="$(basename "${CASE_DIR}")"
# results dir: per model when driven by harness/run-case.sh (PCP_RESULTS_DIR),
# else the legacy shared dir for standalone run.sh cases
RESULTS_DIR="${PCP_RESULTS_DIR:-${CASE_DIR}/results}"
mkdir -p "${RESULTS_DIR}"

TAG="${PCP_TAG:-1.1}"
IMAGE="agent-sandbox:${TAG}"
MODEL="${PCP_MODEL:-}"
MODEL_PORT="${PCP_MODEL_PORT:-9931}"
CPUS="${PCP_CPUS:-2}"
MEMORY="${PCP_MEMORY:-4G}"
NET="${PCP_NET:-default}"
TIMEOUT_SECS="${PCP_TIMEOUT_SECS:-1800}"
CONTEXT_WINDOW="${PCP_CONTEXT_WINDOW:-262144}"
CNAME="pcp-test-${CASE_NAME}-$$"

TMP="$(mktemp -d)"
SSH_PID=""
RUN_PID=""
# shellcheck disable=SC2329  # invoked via trap below
cleanup() {
  set +e
  if [ -n "$SSH_PID" ]; then kill "$SSH_PID" 2>/dev/null; fi
  if [ -n "$RUN_PID" ]; then kill "$RUN_PID" 2>/dev/null; fi
  container rm -f "$CNAME" >/dev/null 2>&1
  rm -rf "$TMP"
  set -e
}
trap cleanup EXIT

image_digest() {
  container image ls --format json | jq -r --arg ref "$1" \
    'first(.[] | select((.configuration.name // "" | split("/")[-1]) == $ref) | .configuration.descriptor.digest)'
}

# --- per-run ephemeral ssh keypair (public half is mounted into the guest) ---
mkdir -p "${TMP}/ssh"
ssh-keygen -q -t ed25519 -N "" -f "${TMP}/pcp_id" -C "pcp-${CASE_NAME}"
cp "${TMP}/pcp_id.pub" "${TMP}/ssh/authorized_keys"
chmod 755 "${TMP}/ssh"
chmod 644 "${TMP}/ssh/authorized_keys"

# --- per-run pi config (model is a run parameter; no secrets in the image) ---
mkdir -p "${TMP}/pi/agent"
jq -n --arg m "${MODEL:-pcp-model}" \
  '{defaultProvider: "llama.cpp", defaultModel: $m}' \
  > "${TMP}/pi/agent/settings.json"
# Mirror the host pi setup exactly (see ~/.pi/agent + pi docs llama-cpp.md):
# - auth.json: the llama.cpp connection (a loopback URL, not a secret)
# - models-store.json: the provider catalog with the PCP_MODEL entry
# - settings.json: default provider/model
# NOTE: do NOT use <agent-dir>/models.json to override the built-in
# "llama.cpp" provider — it reports "Provider is not configured".
jq -n --arg url "http://127.0.0.1:${MODEL_PORT}" \
  '{"llama.cpp": {type: "api_key", env: {LLAMA_BASE_URL: $url}}}' \
  > "${TMP}/pi/agent/auth.json"

jq -n --arg id "${MODEL:-pcp-model}" \
      --arg url "http://127.0.0.1:${MODEL_PORT}/v1" \
      --argjson ctx "${CONTEXT_WINDOW}" \
  '{"llama.cpp": {
      checkedAt: (now | todateiso8601),
      models: [{
        id: $id, name: $id,
        api: "openai-completions", provider: "llama.cpp", baseUrl: $url,
        reasoning: true, input: ["text"],
        cost: {input: 0, output: 0, cacheRead: 0, cacheWrite: 0},
        contextWindow: $ctx, maxTokens: $ctx,
        compat: {
          supportsStore: false, supportsDeveloperRole: false,
          supportsReasoningEffort: false, supportsUsageInStreaming: true,
          supportsStrictMode: false, maxTokensField: "max_tokens"
        }
      }]
    }}' > "${TMP}/pi/agent/models-store.json"

# --- network policy ---
NETARGS=()
if [ "$NET" != "default" ]; then
  container network inspect "$NET" >/dev/null 2>&1 || container network create "$NET" --internal
  NETARGS=(--network "$NET")
fi

GUEST_SCRIPT="${PCP_GUEST_SCRIPT:-}"
if [ -n "$GUEST_SCRIPT" ]; then
  GUEST_DIR="$(cd "$(dirname "$GUEST_SCRIPT")" && pwd)"
  GUEST_NAME="$(basename "$GUEST_SCRIPT")"
  GUEST_MOUNT=(-v "${GUEST_DIR}:/pcp-run:ro")
  GUEST_CMD=(bash "/pcp-run/${GUEST_NAME}")
else
  GUEST_MOUNT=()
  GUEST_CMD=(bash /work/run.sh)
fi

RUN_CMD=(container run --rm --name "$CNAME" -c "$CPUS" -m "$MEMORY"
  "${NETARGS[@]+"${NETARGS[@]}"}"
  "${GUEST_MOUNT[@]+"${GUEST_MOUNT[@]}"}"
  -v "${CASE_DIR}:/work:ro"
  -v "${RESULTS_DIR}:/results"
  -v "${TMP}/pi:/home/agent/.pi"
  -v "${TMP}/ssh:/home/agent/.ssh"
  -e "PCP_CASE=${CASE_NAME}"
  -e "PCP_MODEL=${MODEL}"
  -e "PCP_MODEL_PORT=${MODEL_PORT}"
  -w /work
  "$IMAGE"
  "${GUEST_CMD[@]}")

if [ "$DRY_RUN" = 1 ]; then
  echo "-- dry run --"
  echo "case:        ${CASE_NAME}"
  echo "image:       ${IMAGE} ($(image_digest "$IMAGE" 2>/dev/null || echo 'not built'))"
  echo "model:       ${MODEL:-<unset>} @ host 127.0.0.1:${MODEL_PORT}"
  echo "resources:   ${CPUS} cpus / ${MEMORY}"
  echo "network:     ${NET}"
  echo "timeout:     ${TIMEOUT_SECS}s"
  echo "command:     ${RUN_CMD[*]}"
  exit 0
fi

DIGEST="$(image_digest "$IMAGE")"
START_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_SECS="$(date +%s)"

# --- run the test in the foreground (background shell) so we get its exit code ---
"${RUN_CMD[@]}" &
RUN_PID=$!

# --- timeout watchdog (macOS has no GNU timeout) ---
( sleep "$TIMEOUT_SECS"; kill "$RUN_PID" 2>/dev/null; true ) &
WATCHDOG_PID=$!

# --- wait for the guest IP, then open the reverse tunnel to host loopback ---
IP=""
for _ in $(seq 1 120); do
  IP="$(container ls --format json 2>/dev/null | jq -r --arg n "$CNAME" \
        'first(.[] | select(.id == $n and .status.state == "running")
               | .status.networks[0].ipv4Address)' | cut -d/ -f1)"
  [ -n "$IP" ] && break
  kill -0 "$RUN_PID" 2>/dev/null || break
  sleep 0.5
done

if [ -n "$IP" ]; then
  echo "guest ${CNAME} at ${IP}; tunneling 127.0.0.1:${MODEL_PORT} (host loopback) into guest"
  ssh -i "${TMP}/pcp_id" \
      -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      -o LogLevel=ERROR -o ExitOnForwardFailure=yes \
      -R "127.0.0.1:${MODEL_PORT}:127.0.0.1:${MODEL_PORT}" \
      -N agent@"$IP" &
  SSH_PID=$!
else
  echo "warning: guest IP not found; no tunnel (model endpoint unreachable in guest)" >&2
fi

set +e
wait "$RUN_PID"
RC=$?
set -e
kill "$WATCHDOG_PID" 2>/dev/null || true
[ $RC -gt 128 ] && echo "test timed out or was killed (exit ${RC})" >&2

# --- record metadata ---
END_SECS="$(date +%s)"
END_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
jq -n --arg case "$CASE_NAME" \
      --arg image "$IMAGE" --arg digest "$DIGEST" \
      --arg hostOs "$(sw_vers -productVersion) ($(sw_vers -buildVersion))" \
      --arg hostArch "$(uname -m)" \
      --arg model "$MODEL" --argjson modelPort "$MODEL_PORT" \
      --arg network "$NET" \
      --argjson cpus "$CPUS" --arg memory "$MEMORY" \
      --argjson timeoutSecs "$TIMEOUT_SECS" \
      --arg started "$START_ISO" --arg finished "$END_ISO" \
      --argjson wallSecs "$((END_SECS - START_SECS))" \
      --argjson exitCode "$RC" \
  '{case: $case, image: $image, imageDigest: $digest,
    hostOs: $hostOs, hostArch: $hostArch,
    model: $model, modelPort: $modelPort, network: $network,
    cpus: $cpus, memory: $memory, timeoutSecs: $timeoutSecs,
    startedAt: $started, finishedAt: $finished,
    wallTimeSecs: $wallSecs, exitCode: $exitCode}' \
  > "${RESULTS_DIR}/metadata.json"

echo "done: ${CASE_NAME} exit=${RC} (${RESULTS_DIR}/metadata.json)"
exit "$RC"
