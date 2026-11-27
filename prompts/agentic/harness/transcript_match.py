#!/usr/bin/env python3
"""Transcript check helper for PCP cases (see JOURNAL.md §7.3).

Scans the captured pi session logs (artifacts/sessions) and reports whether a
pattern is present (includes) or absent (excludes).

usage: transcript_match.py --op includes|excludes --pattern PATTERN
                           [--regex] [--scope tool|assistant|any]
                           [--case-sensitive]

Scope:
  tool      tool-call command strings (bash commands etc.)
  assistant assistant text content
  any       both (default)

Matching: literal substring, case-insensitive by default; --regex switches to
regular-expression matching. Exit 0 = check passes, 1 = fails, 2 = no
transcript captured.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

COMMAND_KEYS = {"command", "cmd", "argv", "args"}


def texts_from(obj, role: str | None, out: list[tuple[str, str]]) -> None:
    """Collect (scope, text) pairs from a session JSON object."""
    if isinstance(obj, dict):
        new_role = obj.get("role", role)
        if isinstance(new_role, str):
            role = new_role
        for k, v in obj.items():
            if k in COMMAND_KEYS:
                if isinstance(v, str):
                    out.append(("tool", v))
                elif isinstance(v, list) and all(isinstance(x, str) for x in v):
                    out.append(("tool", " ".join(v)))
            elif k == "text" and isinstance(v, str) and role == "assistant":
                out.append(("assistant", v))
            texts_from(v, role, out)
    elif isinstance(obj, list):
        for x in obj:
            texts_from(x, role, out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--op", choices=["includes", "excludes"], required=True)
    ap.add_argument("--pattern", required=True)
    ap.add_argument("--regex", action="store_true")
    ap.add_argument("--scope", choices=["tool", "assistant", "any"], default="any")
    ap.add_argument("--case-sensitive", action="store_true")
    args = ap.parse_args()

    sessions = os.path.join(os.environ["PCP_ARTIFACTS"], "sessions")
    if not os.path.isdir(sessions) or not any(
        os.scandir(sessions) and [e for e in os.scandir(sessions)]):
        print("no transcript captured (artifacts/sessions missing)")
        return 2

    if args.regex:
        pat = re.compile(args.pattern, 0 if args.case_sensitive else re.IGNORECASE)
        match = lambda text: pat.search(text) is not None
    else:
        needle = args.pattern if args.case_sensitive else args.pattern.lower()
        match = lambda text: needle in (text if args.case_sensitive else text.lower())

    found: list[tuple[str, str]] = []
    files = 0
    for root, _, names in os.walk(sessions):
        for n in names:
            path = os.path.join(root, n)
            try:
                lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
            except OSError:
                continue
            files += 1
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pairs: list[tuple[str, str]] = []
                texts_from(obj, None, pairs)
                for scope, text in pairs:
                    if args.scope in ("any", scope) and match(text):
                        found.append((scope, text))

    hit = found[0] if found else None
    if args.op == "includes":
        if hit:
            print(f"includes: found in {hit[0]}: {hit[1][:200]!r}")
            return 0
        print("includes: pattern not found in transcript")
        return 1
    if hit:
        print(f"excludes: pattern FOUND in {hit[0]}: {hit[1][:200]!r}")
        return 1
    print(f"excludes: pattern absent from {files} session file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
