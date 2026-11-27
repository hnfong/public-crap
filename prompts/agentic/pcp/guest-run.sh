#!/bin/bash
# PCP guest runner — executed via `container exec` (as root) in an idle
# container started by pcp_sandbox.py. Writes everything to container-local
# /artifacts, which is root-owned mode 750: the agent user (pi) cannot read
# or write it. There is NO mount for results; pcp_sandbox.py copies
# /artifacts out after the run (force shutdown → restart → tar over exec).
#
# /pcp-run (mounted ro by pcp_sandbox.py) carries the per-case inputs:
#   /pcp-run/setup.sh    optional per-case setup snippet (cwd = workspace)
#   /pcp-run/prompt.txt  the agent prompt
#   /pcp-run/timeout     inner watchdog seconds for the agent run
set -uo pipefail

INNER_TIMEOUT=$(cat /pcp-run/timeout 2>/dev/null || echo 600)

# artifacts: root-owned, invisible to the agent user
mkdir -p /artifacts
chown root:root /artifacts
chmod 750 /artifacts

# workspace: the agent's working dir, seeded from the case fixture
WS=/workspace
mkdir -p "$WS"
if [ -d /work/fixture ]; then cp -a /work/fixture/. "$WS"/; fi
chown -R agent:agent "$WS"

# per-case setup (as agent, cwd = workspace)
if [ -f /pcp-run/setup.sh ]; then
  if ! (cd "$WS" && runuser -u agent -- bash /pcp-run/setup.sh); then
    echo "pcp: setup failed"
    echo 1 > /artifacts/rc
    exit 1
  fi
fi

# wait for the reverse tunnel / model endpoint
for _ in $(seq 1 120); do
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 2 \
    "http://127.0.0.1:${PCP_MODEL_PORT:-9931}/v1/models" || true)
  [ "$code" = "200" ] && break
  sleep 0.5
done
if [ "$code" != "200" ]; then
  echo "pcp: model endpoint never became reachable (last code=$code)" >&2
  echo 1 > /artifacts/rc
  exit 1
fi

# the agent: as agent user, under the inner watchdog (case-defined timeout)
timeout "$INNER_TIMEOUT" runuser -u agent -- \
  env HOME=/home/agent USER=agent LOGNAME=agent \
  pi --mode json -p "$(cat /pcp-run/prompt.txt)" \
  > /artifacts/pi-output.json 2> /artifacts/pi-stderr.log
RC=$?
echo "pcp: pi exited rc=$RC"

# capture (root; the agent cannot touch /artifacts): workspace snapshot +
# session logs. Heavy build dirs are re-creatable by checks.
mkdir -p /artifacts/workspace
cp -a "$WS"/. /artifacts/workspace/ 2>/dev/null
rm -rf /artifacts/workspace/target /artifacts/workspace/node_modules
find /artifacts/workspace -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
if [ -d /home/agent/.pi/agent/sessions ]; then
  cp -a /home/agent/.pi/agent/sessions /artifacts/sessions
fi

echo "$RC" > /artifacts/rc
exit "$RC"
