# PCP case: syscall-sandbox
# Agent writes a Rust sandbox utility; validation is empirical (does a
# non-whitelisted operation actually get blocked?), not trace parsing.
# strace is captured for human review only (manual check).

SCHEMA = PCP_CASE_V0

NAME = "syscall-sandbox"
DESCRIPTION = "Write a Rust sandbox utility (pcp_sandbox) enforcing a syscall whitelist; validated empirically via blocked operations."

SETUP = [
  # compile the fixture probe programs into the workspace (they land in the
  # artifacts and are reused by the checks)
  "gcc -o writer writer.c && gcc -o reader reader.c",
]

PROMPTS = [
  """Write a Linux utility in Rust called `pcp_sandbox`.

Usage: pcp_sandbox [-l syscall_whitelist_file] <program> [args...]

It execs <program> with the given args, allowing the child process only the
syscalls listed in the whitelist file (one syscall name per line, e.g.
`openat`, `write`). With no -l option, pick and document a default policy.

Put a cargo project named pcp_sandbox in the current directory; it must
build with `cargo build`. It will run as root in a minimal Linux container.
""",
]

CHECKS = [
  # FIXME: we need a in_guest option in checks.run, or run_in_guest()

  # Linux ELF can't run on the macOS host: build/run checks use in_guest=True
  # (throwaway container; artifacts at /artifacts, case dir read-only at /case)
  pcp.checks.run(name="builds", in_guest=True,
                 # NOTE pipefail: a naive `| tail` masks cargo's exit code
                 cmd="set -o pipefail && cargo build 2>&1 | tail -3"),
  pcp.checks.run(name="echo-ok-with-whitelist", in_guest=True,
                 cmd="target/debug/pcp_sandbox -l /case/fixture/whitelist-echo.txt /bin/echo HONK | grep -qx HONK"),
  # whitelist-tight.txt has NO openat: a passthrough sandbox lets writer
  # succeed -> this check fails. Catches do-nothing sandboxes.
  pcp.checks.run(name="write-blocked-without-openat", in_guest=True, cmd="""
if target/debug/pcp_sandbox -l /case/fixture/whitelist-tight.txt ./writer >/dev/null 2>&1; then
  echo "writer was NOT blocked (passthrough sandbox?)"
  exit 1
else
  echo "writer blocked"
fi
"""),
  # informational only: dump the trace + per-PID syscall summary
  pcp.checks.run(name="strace-observed-syscalls", manual=True, in_guest=True, cmd="""
strace -f -o /artifacts/strace-echo.txt target/debug/pcp_sandbox -l /case/fixture/whitelist-echo.txt /bin/echo HONK >/dev/null 2>&1
python3 /case/checks/strace_summary.py /artifacts/strace-echo.txt /case/fixture/whitelist-echo.txt
"""),
]
