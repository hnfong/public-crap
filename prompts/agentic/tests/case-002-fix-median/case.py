# PCP case: fix-median
# Fix-a-bug case: deterministic outcome check (tests pass) plus an anti-cheat
# behavioral check (tests unmodified). Guest has no pytest by design; the
# fixture uses the stdlib unittest so the same suite runs on host and guest.

SCHEMA = PCP_CASE_V0

NAME = "fix-median"
DESCRIPTION = "Fix the bug in median.py so the failing stdlib unittest passes; tests must stay unmodified."

PROMPTS = [
  """The test suite in this directory is failing.

Run it (`python3 -m unittest -v test_median`), find the bug in median.py,
and fix it so all tests pass. Do NOT modify test_median.py. Keep the fix
minimal.
""",
]

CHECKS = [
  # NOTE pipefail: a naive `| tail` masks the test exit code
  pcp.checks.run(name="tests-pass",
                 cmd='cd "$PCP_ARTIFACTS/workspace" && set -o pipefail && python3 -m unittest -v test_median 2>&1 | tail -3'),
  pcp.checks.run(name="tests-unmodified",
                 cmd='diff -u "$PCP_CASE_DIR/fixture/test_median.py" "$PCP_ARTIFACTS/workspace/test_median.py"'),
]
