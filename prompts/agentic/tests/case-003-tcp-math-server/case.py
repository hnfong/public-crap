# PCP case: tcp-math-server
# Write a small TCP server in C; validation is empirical — checks connect to
# the running server and compare responses. Each check runs in its own
# throwaway container, so the server started there dies with it (no cleanup).

SCHEMA = PCP_CASE_V0

NAME = "tcp-math-server"
DESCRIPTION = ("Write a TCP server (mathd.c) that evaluates one arithmetic "
               "expression per connection; supports + - *, nested parentheses, "
               "answers NaN on invalid input.")

PROMPTS = [
  """Write a TCP server in C, in a file called mathd.c in the current directory.

- It listens on TCP port 6767.
- For every TCP connection, it takes the first line it receives, evaluates it
  as a simple arithmetic expression (e.g. 2+4), and responds with one line
  that contains the evaluated result.
- Must support addition, subtraction and multiplication. No division.
- Must support parentheses and nested parentheses.
- Invalid expressions must produce a line containing the string NaN.

It must compile with exactly: clang -o mathd mathd.c
""",
]

CHECKS = [
  # exact compile command from the requirements (pipefail: | tail masks rc)
  pcp.checks.run(name="builds", in_guest=True,
                 cmd="set -o pipefail && clang -o mathd mathd.c 2>&1 | tail -3"),

  # --- behavior: start the server, probe it over TCP -----------------------
  # (probe.py retries the connection briefly, so server startup race is fine;
  # word-boundary grep so a response of "16" does not count as "6")
  pcp.checks.run(name="add", in_guest=True,
                 cmd="./mathd >/dev/null 2>&1 & sleep 0.5; "
                     "python3 /case/checks/probe.py '2+4' | grep -qE '(^|[^0-9-])6([^0-9]|$)'"),
  pcp.checks.run(name="subtract", in_guest=True,
                 cmd="./mathd >/dev/null 2>&1 & sleep 0.5; "
                     "python3 /case/checks/probe.py '10-3' | grep -qE '(^|[^0-9-])7([^0-9]|$)'"),
  pcp.checks.run(name="subtract-negative-result", in_guest=True,
                 cmd="./mathd >/dev/null 2>&1 & sleep 0.5; "
                     "python3 /case/checks/probe.py '2-5' | grep -qE '(^|[^0-9])-3([^0-9]|$)'"),
  pcp.checks.run(name="multiply", in_guest=True,
                 cmd="./mathd >/dev/null 2>&1 & sleep 0.5; "
                     "python3 /case/checks/probe.py '6*7' | grep -qE '(^|[^0-9-])42([^0-9]|$)'"),
  pcp.checks.run(name="parentheses", in_guest=True,
                 cmd="./mathd >/dev/null 2>&1 & sleep 0.5; "
                     "python3 /case/checks/probe.py '(2+4)*3' | grep -qE '(^|[^0-9-])18([^0-9]|$)'"),
  pcp.checks.run(name="nested-parentheses", in_guest=True,
                 cmd="./mathd >/dev/null 2>&1 & sleep 0.5; "
                     "python3 /case/checks/probe.py '((1+2)*(3+4))' | grep -qE '(^|[^0-9-])21([^0-9]|$)'"),
  pcp.checks.run(name="invalid-expression", in_guest=True,
                 cmd="./mathd >/dev/null 2>&1 & sleep 0.5; "
                     "python3 /case/checks/probe.py '2+' | grep -q NaN"),
  pcp.checks.run(name="garbage-input", in_guest=True,
                 cmd="./mathd >/dev/null 2>&1 & sleep 0.5; "
                     "python3 /case/checks/probe.py 'abc' | grep -q NaN"),
  pcp.checks.run(name="division-unsupported", in_guest=True,
                 cmd="./mathd >/dev/null 2>&1 & sleep 0.5; "
                     "python3 /case/checks/probe.py '8/2' | grep -q NaN"),
  pcp.checks.run(name="multiple-connections", in_guest=True,
                 cmd="./mathd >/dev/null 2>&1 & sleep 0.5; "
                     "python3 /case/checks/probe.py '1+1' | grep -qE '(^|[^0-9-])2([^0-9]|$)' && "
                     "python3 /case/checks/probe.py '2+2' | grep -qE '(^|[^0-9-])4([^0-9]|$)'"),
]
