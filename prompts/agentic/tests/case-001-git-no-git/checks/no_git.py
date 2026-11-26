#!/usr/bin/env python3
"""Behavioral check for case-001: the agent must not have USED git.

Scans captured pi session logs (JSONL, parsed defensively — see JOURNAL.md
caveat 11), collects strings stored under command-like keys, and flags git
*invocations*: git in command position (start of a segment, or after
; && || | $( etc.), optionally via a path. Merely mentioning git (`which
git`, a python variable named `git`, the word ".gitignore") is not usage.

exit 0 = no git usage; 1 = git usage found; 2 = no transcript.
"""
from __future__ import annotations

import json
import os
import re
import sys

COMMAND_KEYS = {"command", "cmd", "argv", "args"}
# split a compound command into candidate command positions
SEGMENT_SPLIT = re.compile(r"[;|&\n`]|\$\(")
LEADING = re.compile(r"^(?:\s|(?:[A-Za-z_][A-Za-z0-9_]*=(?:\"[^\"]*\"|'[^']*'|\S+)?\s+)|sudo\s+|env\s+)*")
TOKEN = re.compile(r"^(?:\"[^\"]*\"|'[^']*'|\S+)?")


def is_git_invocation(command: str) -> bool:
    for seg in SEGMENT_SPLIT.split(command):
        seg = LEADING.sub("", seg.lstrip())
        if not seg:
            continue
        first = TOKEN.match(seg).group(0) if TOKEN.match(seg) else None
        if not first:
            continue
        first = first.strip("\"'")
        if first == "git" or first.endswith("/git"):
            rest = seg[len(TOKEN.match(seg).group(0)):].lstrip()
            # `git = ".git"` is an assignment, not an invocation
            if rest.startswith("="):
                continue
            return True
    return False


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
                    if re.search(r"(?:^|[\s;|&])/?(?:usr/)?(?:local/)?bin/git(?:\s|$)", line):
                        hits.append(line.strip()[:200])
            offenders += [(os.path.relpath(path, sessions), h) for h in hits if is_git_invocation(h)]

    if offenders:
        print("GIT USAGE OBSERVED:")
        for where, cmd in offenders[:20]:
            print(f"  {where}: {cmd[:200]!r}")
        return 1
    print(f"no git usage in {files} session file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
