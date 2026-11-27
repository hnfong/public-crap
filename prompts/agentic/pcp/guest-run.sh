#!/bin/bash
# PCP guest runner — the one static wrapper executed inside the guest.
# Per-case inputs are staged by pcp_case.py into /pcp-run (mounted ro):
#   /pcp-run/setup.sh    optional per-case setup snippet (cwd = workspace)
#   /pcp-run/prompt.txt  the agent prompt
#   /pcp-run/timeout     inner watchdog seconds for the agent run
# The host-side outer watchdog (pcp_sandbox.py run) is that + 30s, so the
# artifact-capture step below always runs even when the agent times out.
set -uo pipefail

WS=/tmp/workspace
mkdir -p "$WS" /results/artifacts
if [ -d /work/fixture ]; then cp -a /work/fixture/. "$WS"/; fi
cd "$WS"

# per-case setup (always executed; may be absent/empty)
if [ -f /pcp-run/setup.sh ]; then
  bash /pcp-run/setup.sh
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "pcp: setup failed (rc=$rc)"
    exit "$rc"
  fi
fi

RC=0
if [ -f /pcp-run/prompt.txt ]; then
  # wait for the reverse tunnel / model endpoint
  for _ in $(seq 1 120); do
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 2 \
      "http://127.0.0.1:${PCP_MODEL_PORT:-9931}/v1/models" || true)
    [ "$code" = "200" ] && break
    sleep 0.5
  done
  if [ "$code" != "200" ]; then
    echo "pcp: model endpoint never became reachable (last code=$code)" >&2
    RC=1
  else
    # inner watchdog: the agent gets exactly the case-defined timeout
    INNER_TIMEOUT=$(cat /pcp-run/timeout 2>/dev/null || echo 600)
    timeout "$INNER_TIMEOUT" pi --mode json -p "$(cat /pcp-run/prompt.txt)" \
      > /results/artifacts/pi-output.json 2> /results/artifacts/pi-stderr.log
    RC=$?
    echo "pcp: pi exited rc=$RC"
  fi
else
  echo "pcp: no prompt (case misconfigured?)" >&2
  RC=1
fi

# ---- artifact capture (generous + fixed; see JOURNAL.md §7.2) ----
mkdir -p /results/artifacts/workspace
cp -a "$WS"/. /results/artifacts/workspace/ 2>/dev/null
# keep artifacts lean; heavy build dirs are re-creatable by checks
rm -rf /results/artifacts/workspace/target /results/artifacts/workspace/node_modules
find /results/artifacts/workspace -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
if [ -d /home/agent/.pi/agent/sessions ]; then
  cp -a /home/agent/.pi/agent/sessions /results/artifacts/sessions
fi
exit $RC
