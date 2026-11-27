# PCP case: harness smoke (see JOURNAL.md §7.3 for the schema)
# End-to-end smoke: harness plumbing (workspace, artifact capture, checks)
# plus a trivial LLM round-trip through the tunnel. Requires a model server.

SCHEMA = PCP_CASE_V0

NAME = "harness-smoke"
DESCRIPTION = "Smoke test that uses the LLM minimally to ensure the VM, harness and LLM are correctly set up and functional."

SETUP = ["""{
  echo "user: $(id)"
  echo "cwd:  $(pwd)"
  echo "node: $(node --version)"
  echo "npm:  $(npm --version)"
  echo "rust: $(rustc --version)"
  echo "cargo: $(cargo --version)"
  echo "clang: $(clang --version | head -1)"
  echo "python: $(python3 --version)"
  echo "java:  $(java -version 2>&1 | head -1)"
  echo "pi:    $(pi --version)"
  echo "git:   $(git --version)"
  echo "strace: $(strace -V 2>&1 | head -1)"
} > toolchain.txt 2>&1
         """,]

PROMPTS = [
  """Who was the famous King of England who had six wives, two of whom he had executed? Answer with just the name, nothing else.""",
]

CHECKS = [
  pcp.checks.run(name="toolchain-versions", cmd="""
test -f "$PCP_ARTIFACTS/workspace/toolchain.txt" \\
  && grep -q '^node: v'    "$PCP_ARTIFACTS/workspace/toolchain.txt" \\
  && grep -q '^pi: '       "$PCP_ARTIFACTS/workspace/toolchain.txt" \\
  && grep -q '^strace: '   "$PCP_ARTIFACTS/workspace/toolchain.txt"
  """),
  pcp.checks.transcript(name="llm-says-henry", mode=pcp.checks.mode.includes, icase=True, scope=pcp.checks.scope.assistant, pattern="henry"),
  pcp.checks.transcript(name="llm-says-viii", mode=pcp.checks.mode.includes, icase=True, scope=pcp.checks.scope.assistant, pattern=re.compile(r'viii|8th|eighth'))
]
