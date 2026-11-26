#!/bin/bash
# PCP guest entrypoint. Runs as root: starts sshd (for the harness reverse
# tunnel), then drops to the non-root 'agent' user and execs the command.
set -euo pipefail

# Host keys are generated per container filesystem (not baked into the image).
ssh-keygen -A >/dev/null 2>&1
mkdir -p /run/sshd
/usr/sbin/sshd

if [ "$#" -eq 0 ]; then
  # no command: idle (interactive debugging via harness ssh)
  exec sleep infinity
fi

exec runuser -u agent -- env HOME=/home/agent USER=agent LOGNAME=agent "$@"
