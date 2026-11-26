#!/bin/bash
# PCP per-boot host preparation. Idempotent; safe to run any number of times,
# and after every macOS reboot. Requires NO sudo (owner decision: no
# host-bridge DNS rule, no Privata Relay tradeoff — the guest reaches host
# loopback services through a per-run SSH reverse tunnel instead).
set -euo pipefail

if container system status 2>/dev/null | grep -Eq '^status\s+running'; then
  echo "container system: already running"
else
  echo "container system: starting..."
  # --enable-kernel-install: install apple/container's default kernel
  # non-interactively if missing (component of apple/container itself).
  container system start --enable-kernel-install
fi

echo "PCP host setup complete."
