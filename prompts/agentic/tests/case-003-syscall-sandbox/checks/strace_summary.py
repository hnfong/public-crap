#!/usr/bin/env python3
"""Informational: summarize syscalls observed in a strace dump vs a whitelist.
Never fails the case (manual check) — prints a reviewable summary."""
from __future__ import annotations

import os
import re
import sys

TRACE_RE = re.compile(r"^\s*(\d+)\s+(\w+)\(")


def main() -> int:
    trace, whitelist = sys.argv[1], sys.argv[2]
    if not os.path.isfile(trace):
        print(f"WARNING: no trace at {trace} (strace attach may have failed, "
              f"e.g. ptrace-based sandbox)")
        return 0
    allowed = {l.strip() for l in open(whitelist) if l.strip()}
    seen: dict[int, set[str]] = {}
    for line in open(trace, encoding="utf-8", errors="replace"):
        m = TRACE_RE.match(line)
        if m:
            seen.setdefault(int(m.group(1)), set()).add(m.group(2))
    pids = sorted(seen)
    print(f"traced PIDs: {pids}")
    for pid in pids:
        extra = sorted(seen[pid] - allowed)
        tag = "OK (subset of whitelist)" if not extra else f"OUTSIDE whitelist: {extra}"
        print(f"  pid {pid}: {len(seen[pid])} syscalls — {tag}")
    print(f"whitelist ({len(allowed)}): {sorted(allowed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
