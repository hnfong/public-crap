#!/usr/bin/env python3
"""Behavioral check for case-001: the agent must not have used git.

Scans captured pi session logs (JSONL, format intentionally parsed
defensively — see JOURNAL.md caveat 11): collects strings stored under
command-like keys and flags any that invoke git.

exit 0 = no git usage observed; 1 = git usage found; 2 = no transcript.
"""
from __future__ import annotations

import json
import os
import re
import sys

GIT_RE = re.compile(r"(?:^|[\s/])git(?:\s|$)")  # \bgit\b, but not .gitignore
COMMAND_KEYS = {"command", "cmd", "argv", "args"}


def collect_commands(obj, hits: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in COMMAND_KEYS:
                if isinstance(v, str):
                    hits.append(v)
                elif isinstance(v, list) and all(isinstance(x, str) for x in v):
                    hits.append(" ".join(v))
            collect_commands(v, hits)
    elif isinstance(obj, list):
        for x in obj:
            collect_commands(x, hits)


def main() -> int:
    sessions = os.path.join(os.environ["PCP_ARTIFACTS"], "sessions")
    if not os.path.isdir(sessions):
        print("no transcript captured (artifacts/sessions missing)")
        return 2
    offenders: list[str] = []
    files = 0
    for root, _, names in os.walk(sessions):
        for n in names:
            path = os.path.join(root, n)
            try:
                lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
            except OSError:
                continue
            parsed = 0
            hits: list[str] = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                parsed += 1
                collect_commands(obj, hits)
            files += 1
            if parsed == 0:
                # not JSONL — defensive raw scan, prompt text may false-positive
                # so only flag unambiguous absolute-path invocations
                for line in lines:
                    if re.search(r"(?:^|[\s/])/?(?:usr/)?(?:local/)?bin/git(?:\s|$)", line):
                        hits.append(line.strip()[:200])
            offenders += [(os.path.relpath(path, sessions), h) for h in hits if GIT_RE.search(h)]

    if offenders:
        print("GIT USAGE OBSERVED:")
        for where, cmd in offenders[:20]:
            print(f"  {where}: {cmd!r}")
        return 1
    print(f"no git usage in {files} session file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
