#!/usr/bin/env python3
"""PCP case runner — interprets `pcp-case/v0` cases (see JOURNAL.md §7).

usage: pcp_case.py [--checks-only] [--model MODEL]
                   <tests/case-NNN-name>

The model is a first-class run parameter: --model wins over the PCP_MODEL
env var (which remains for scripting/matrix use).

A case is a case.py file executed with the `pcp` DSL injected (SCHEMA, NAME,
DESCRIPTION, SETUP[], PROMPTS[], CHECKS[] built via pcp.checks.*).
pcp.checks.run(..., in_guest=True) runs its command inside a throwaway guest
container (for Linux-only artifacts).

Flow:
  1. load <case-dir>/case.py
  2. generate a guest script (workspace setup, pi invocation, artifact capture)
  3. delegate the VM run to `pcp_sandbox.py run --guest-script …`
  4. run the case's checks on the HOST against collected artifacts
  5. write results/checks.json + results/verdict.txt

--checks-only: skip steps 2-3, run checks against existing artifacts.

Results are kept per model under the repo-wide results root:
<repo>/results/<case-dir-name>/<MODEL>/ (_nomodel for agent-less cases). --checks-only needs PCP_MODEL set for agent cases.

Check contract: shell snippet run with cwd = case results dir.
Env: PCP_ARTIFACTS (…/results/artifacts), PCP_CASE_DIR, PCP_CASE,
     PCP_INGUEST (helper to run a command inside a throwaway guest container).
Exit 0 = pass. `human_review=True` checks are recorded but never fail the case.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

PCP_DIR = os.path.dirname(os.path.abspath(__file__))
SANDBOX_TOOL = os.path.join(PCP_DIR, "pcp_sandbox.py")

CASE_SCHEMA_V0 = "pcp-case/v0"
DEFAULT_CHECK_TIMEOUT = 600


# --- check classes (instances are created by the `pcp.checks` DSL) ---
class CheckResult:
    """Outcome of one check execution: status is pass, fail or human review."""

    def __init__(self, status: str, detail: str = ""):
        if status not in ("pass", "fail", "human review"):
            fail(f"invalid check status {status!r}")
        self.status = status
        self.detail = detail


class PcpCheck:
    """Base class for case checks. Subclasses implement execute(), which
    returns a CheckResult — the runner stays agnostic to how checks work."""

    def __init__(self, name: str, human_review: bool = False):
        if not name:
            fail("check: 'name' is required")
        self.name = name
        self.type = "human review" if human_review else "check"

    def execute(self, results: str, env: dict, timeout: int) -> CheckResult:
        raise NotImplementedError

    def provenance(self) -> str:
        """Human-readable description recorded in checks.json."""
        raise NotImplementedError


class RunCheck(PcpCheck):
    """Shell command, run on the host (or in a throwaway guest container
    when in_guest=True — for checks that must execute Linux binaries).
    Exit code 0 = pass, anything else = fail."""

    def __init__(self, name: str, cmd: str, human_review: bool = False,
                 in_guest: bool = False):
        super().__init__(name, human_review)
        if not cmd:
            fail(f"check {name!r}: 'cmd' is required")
        self.cmd = cmd
        self.in_guest = in_guest

    def execute(self, results: str, env: dict, timeout: int) -> CheckResult:
        if self.in_guest:
            tag = env.get("PCP_TAG") or "1.1"
            cmd = ["container", "run", "--rm",
                   "-v", f"{env['PCP_ARTIFACTS']}:/artifacts",
                   "-v", f"{env['PCP_CASE_DIR']}:/case:ro",
                   "-w", "/artifacts/workspace",
                   f"agent-sandbox:{tag}", "bash", "-c", self.cmd]
        else:
            cmd = ["bash", "-c", self.cmd]
        try:
            proc = subprocess.run(cmd, cwd=results, env=env,
                                  capture_output=True, text=True,
                                  timeout=timeout)
        except subprocess.TimeoutExpired as e:
            return CheckResult("fail", f"check timed out after {timeout}s\n"
                                       f"{(e.stdout or b'').decode(errors='replace')[-2000:] if isinstance(e.stdout, bytes) else (e.stdout or '')[-2000:]}")
        detail = (proc.stdout + ("\n" + proc.stderr if proc.stderr else "")).strip()
        if self.type == "human review":
            status = "human review"  # recorded, never scores
        else:
            status = "pass" if proc.returncode == 0 else "fail"
        return CheckResult(status, detail)

    def provenance(self) -> str:
        where = "in-guest" if self.in_guest else "host"
        return f"[{where}] {self.cmd}"


class TranscriptCheck(PcpCheck):
    """Built-in check over the captured session log: does the transcript
    include/exclude a pattern (over assistant text and/or tool commands)?"""

    def __init__(self, name: str, mode: str, pattern, scope: str = "any",
                 icase: bool = True):
        super().__init__(name)
        if mode not in (_TranscriptMode.includes, _TranscriptMode.excludes):
            fail(f"check {name!r}: mode must be includes or excludes")
        if scope not in (_TranscriptScope.tool, _TranscriptScope.assistant,
                         _TranscriptScope.any):
            fail(f"check {name!r}: scope must be tool, assistant or any")
        self.mode = mode
        self.regex = isinstance(pattern, re.Pattern)
        self.pattern = pattern.pattern if self.regex else pattern
        self.scope = scope
        self.case_sensitive = not icase

    def execute(self, results: str, env: dict, timeout: int) -> CheckResult:
        sessions = os.path.join(env["PCP_ARTIFACTS"], "sessions")
        rc, msg = transcript_match(
            self.mode, self.pattern, regex=self.regex, scope=self.scope,
            case_sensitive=self.case_sensitive, sessions=sessions)
        return CheckResult("pass" if rc == 0 else "fail", msg)

    def provenance(self) -> str:
        kind = "regex" if self.regex else "literal"
        return (f"[transcript] {self.mode} /{self.pattern}/ ({kind}, "
                f"scope={self.scope}, icase={not self.case_sensitive})")


# --- the `pcp` DSL injected into case.py files (see JOURNAL.md §7.3) ---
class _TranscriptMode:
    includes = "includes"
    excludes = "excludes"


class _TranscriptScope:
    tool = "tool"
    assistant = "assistant"
    any = "any"


class _checks:
    mode = _TranscriptMode
    scope = _TranscriptScope

    @staticmethod
    def run(name: str, cmd: str, human_review: bool = False,
            in_guest: bool = False) -> RunCheck:
        return RunCheck(name, cmd, human_review=human_review, in_guest=in_guest)

    @staticmethod
    def transcript(name: str, mode: str, pattern, scope: str = "any",
                   icase: bool = True) -> TranscriptCheck:
        return TranscriptCheck(name, mode, pattern, scope=scope, icase=icase)


pcp = SimpleNamespace(checks=_checks)

GUEST_TEMPLATE = """#!/bin/bash
# Generated by pcp/pcp_case.py from case.py — do not edit.
set -uo pipefail

WS=/tmp/workspace
mkdir -p "$WS" /results/artifacts
if [ -d /work/fixture ]; then cp -a /work/fixture/. "$WS"/; fi
cd "$WS"
{setup}
SETUP_RC=$?
if [ "$SETUP_RC" -ne 0 ]; then
  echo "pcp: setup failed (rc=$SETUP_RC)"
  exit "$SETUP_RC"
fi
RC=0
{agent_block}
# ---- artifact capture (generous + fixed; see JOURNAL.md §7.2) ----
mkdir -p /results/artifacts/workspace
cp -a "$WS"/. /results/artifacts/workspace/ 2>/dev/null
# keep artifacts lean; heavy build dirs are re-creatable by checks
rm -rf /results/artifacts/workspace/target /results/artifacts/workspace/node_modules
find /results/artifacts/workspace -name __pycache__ -type d -exec rm -rf {{}} + 2>/dev/null
if [ -d /home/agent/.pi/agent/sessions ]; then
  cp -a /home/agent/.pi/agent/sessions /results/artifacts/sessions
fi
exit $RC
"""

AGENT_BLOCK = """if [ -f /pcp-run/prompt.txt ]; then
  # wait for the reverse tunnel / model endpoint (run-test.sh sets it up
  # asynchronously after boot — see JOURNAL.md caveat 10)
  for _ in $(seq 1 120); do
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 2 \\
      "http://127.0.0.1:${PCP_MODEL_PORT:-9931}/v1/models" || true)
    [ "$code" = "200" ] && break
    sleep 0.5
  done
  if [ "$code" != "200" ]; then
    echo "pcp: model endpoint never became reachable (last code=$code)" >&2
    RC=1
  else
    pi --mode json -p "$(cat /pcp-run/prompt.txt)" \\
       > /results/artifacts/pi-output.json 2> /results/artifacts/pi-stderr.log
    RC=$?
    echo "pcp: pi exited rc=$RC"
  fi
else
  echo "pcp: no prompt (case misconfigured?)" >&2
  RC=1
fi"""


def fail(msg: str, code: int = 2) -> None:
    print(f"pcp_case: {msg}", file=sys.stderr)
    sys.exit(code)


def indent(text: str, pad: str = "") -> str:
    return "\n".join(pad + line if line else "" for line in text.splitlines())


def load_case(case_dir: str) -> dict:
    """Execute case.py with the `pcp` DSL injected and normalize its constants."""
    path = os.path.join(case_dir, "case.py")
    if not os.path.isfile(path):
        fail(f"no case.py in {case_dir}")
    namespace = {"PCP_CASE_V0": CASE_SCHEMA_V0, "pcp": pcp, "re": re,
                 "__name__": "pcp-case"}
    with open(path, encoding="utf-8") as f:
        code = compile(f.read(), path, "exec")
    exec(code, namespace)  # cases are trusted repo content
    try:
        schema, name = namespace["SCHEMA"], namespace["NAME"]
        prompts = namespace.get("PROMPTS", [])
        setup = namespace.get("SETUP", [])
        checks = namespace.get("CHECKS", [])
    except KeyError as e:
        fail(f"{path}: missing required constant {e}")
    if schema != CASE_SCHEMA_V0:
        fail(f"{path}: unknown SCHEMA {schema!r}")
    if not name:
        fail(f"{path}: NAME is empty")
    for i, chk in enumerate(checks):
        if not isinstance(chk, PcpCheck):
            fail(f"{path}: CHECKS[{i}] must come from a pcp.checks.* constructor")
    return {
        "schema": schema,
        "name": name,
        "description": namespace.get("DESCRIPTION", ""),
        # multiple prompts run as one concatenated prompt (none today)
        "prompt": "\n\n".join(prompts),
        "setup": "\n".join(setup),
        "no_agent": not prompts,
        "checks": list(checks),
        # per-case VM timeout (seconds); owner decision: driven by the case
        "timeout": int(namespace.get("TIMEOUT", 600)),
    }


def make_guest_script(case: dict) -> str:
    setup = indent(case.get("setup", "true"))
    agent_block = "" if case.get("no_agent") else indent(AGENT_BLOCK)
    return GUEST_TEMPLATE.format(setup=setup, agent_block=agent_block)


def model_dir_name() -> str:
    """Results are kept per model (owner decision): results/<MODEL>/.
    Agent-less cases land in results/_nomodel."""
    model = os.environ.get("PCP_MODEL", "").strip()
    if not model:
        return "_nomodel"
    return re.sub(r"[^A-Za-z0-9._-]", "_", model)


def run_vm(case: dict, case_dir: str, results: str) -> int:
    rundir = tempfile.mkdtemp(prefix="pcp-run-")
    with open(os.path.join(rundir, "guest-run.sh"), "w") as f:
        f.write(make_guest_script(case))
    os.chmod(os.path.join(rundir, "guest-run.sh"), 0o755)
    if case.get("prompt"):
        with open(os.path.join(rundir, "prompt.txt"), "w") as f:
            f.write(case["prompt"])
    # per-case timeout wins; PCP_TIMEOUT_SECS env is the fallback for cases
    # that don't define TIMEOUT
    timeout = case.get("timeout") or int(os.environ.get("PCP_TIMEOUT_SECS") or 600)
    cmd = [sys.executable, SANDBOX_TOOL, "run", case_dir,
           "--guest-script", os.path.join(rundir, "guest-run.sh"),
           "--results-dir", results,
           "--timeout-secs", str(timeout)]
    if os.environ.get("PCP_MODEL"):
        cmd += ["--model", os.environ["PCP_MODEL"]]
    print(f"pcp_case: running VM for {case['name']} …")
    # PCP_* knobs (tag/memory/net/timeout/…) flow through the environment
    proc = subprocess.run(cmd, env=dict(os.environ))
    return proc.returncode


def transcript_match(op: str, pattern: str, *, regex: bool = False,
                     scope: str = "any", case_sensitive: bool = False,
                     sessions: str) -> tuple[int, str]:
    """Built-in transcript check: does the captured session log include or
    exclude a pattern (over assistant text and/or tool-call commands)?
    Returns (exit_code, message); 0 = pass, 1 = fail, 2 = no transcript."""
    if not os.path.isdir(sessions):
        return 2, "no transcript captured (artifacts/sessions missing)"
    if regex:
        pat = re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)
        match = lambda text: pat.search(text) is not None
    else:
        needle = pattern if case_sensitive else pattern.lower()
        match = lambda text: needle in (text if case_sensitive else text.lower())

    command_keys = {"command", "cmd", "argv", "args"}

    def collect(obj, role, out):
        if isinstance(obj, dict):
            new_role = obj.get("role", role)
            if isinstance(new_role, str):
                role = new_role
            for k, v in obj.items():
                if k in command_keys:
                    if isinstance(v, str):
                        out.append(("tool", v))
                    elif isinstance(v, list) and all(isinstance(x, str) for x in v):
                        out.append(("tool", " ".join(v)))
                elif k == "text" and isinstance(v, str) and role == "assistant":
                    out.append(("assistant", v))
                collect(v, role, out)
        elif isinstance(obj, list):
            for x in obj:
                collect(x, role, out)

    found, files = [], 0
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
                pairs = []
                collect(obj, None, pairs)
                found += [(s, t) for s, t in pairs
                          if scope in ("any", s) and match(t)]

    if op == "includes":
        if found:
            return 0, f"includes: found in {found[0][0]}: {found[0][1][:200]!r}"
        return 1, "includes: pattern not found in transcript"
    if found:
        return 1, f"excludes: pattern FOUND in {found[0][0]}: {found[0][1][:200]!r}"
    return 0, f"excludes: pattern absent from {files} session file(s)"


def run_checks(case: dict, case_dir: str, results: str, artifacts: str) -> list[dict]:
    os.makedirs(artifacts, exist_ok=True)
    env_common = dict(
        os.environ,
        PCP_ARTIFACTS=artifacts,
        PCP_CASE_DIR=case_dir,
        PCP_CASE=case["name"],
    )
    out = []
    for chk in case.get("checks", []):
        t0 = time.monotonic()
        try:
            result = chk.execute(results, env_common, DEFAULT_CHECK_TIMEOUT)
        except Exception as e:  # a broken check must not break the run
            result = CheckResult("fail", f"check crashed: {e!r}")
        dt = int((time.monotonic() - t0) * 1000)
        entry = {
            "name": chk.name, "type": chk.type, "status": result.status,
            "check": chk.provenance(), "detail": result.detail[-4000:],
            "durationMs": dt,
        }
        out.append(entry)
        print(f"pcp_case: check {chk.name:<28} {result.status:<7} ({dt} ms)")
    return out


def write_results(case: dict, results: str, checks: list[dict]) -> int:
    with open(os.path.join(results, "checks.json"), "w") as f:
        json.dump(
            {"schema": case["schema"], "case": case["name"],
             "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "checks": checks},
            f, indent=2,
        )
    mechanical = [c for c in checks if c["type"] != "human review"]
    if any(c["status"] == "fail" for c in mechanical):
        verdict = "FAIL"
    elif mechanical and all(c["status"] == "pass" for c in mechanical):
        verdict = "PASS"
    else:
        verdict = "HUMAN REVIEW"  # nothing mechanical to score (or checks-only, empty)
    print(f"pcp_case: verdict {verdict} ({len(checks)} checks) → {results}")
    return 0 if verdict in ("PASS", "HUMAN REVIEW") else 1


# ---------------------------------------------------------------- output.txt
def _hr(title: str = "", width: int = 80, ch: str = "=") -> str:
    if title:
        pad = max(1, width - len(title) - 4)
        return f"{ch * 2} {title} " + ch * pad
    return ch * width


def _clip(text: str, head: int = 4000, tail: int = 4000) -> str:
    """Clip long text for human reading, keeping head and tail."""
    if len(text) <= head + tail:
        return text
    return (text[:head] + f"\n… [{len(text) - head - tail} chars truncated] …\n"
            + text[-tail:])


def _render_message(msg: dict) -> list[str]:
    """Render one pi message (role + content items) as text lines."""
    out = []
    role = msg.get("role", "?")
    content = msg.get("content")
    if role == "system":
        out.append(f"[system prompt omitted, {len(json.dumps(content))} chars]")
        return out
    if not isinstance(content, list):
        out.append(f"[{role}] {_clip(str(content), 500, 0)}")
        return out
    for item in content:
        if not isinstance(item, dict):
            out.append(f"[{role}] {_clip(str(item), 500, 0)}")
            continue
        itype = item.get("type")
        if itype == "text":
            out.append(f"[{role}]\n{_clip(item.get('text', ''))}")
        elif itype == "thinking":
            t = item.get("thinking", "")
            out.append(f"[thinking]\n{_clip(t, 800, 800)}")
        elif itype == "toolCall":
            name = item.get("name", "?")
            args = item.get("arguments") or {}
            if name == "bash" and isinstance(args, dict):
                out.append(f"[tool call: bash]\n$ {_clip(args.get('command', ''))}")
            else:
                out.append(f"[tool call: {name}]\n{_clip(json.dumps(args), 500, 0)}")
        else:
            out.append(f"[{role}: {itype}] {_clip(json.dumps(item), 300, 0)}")
    return out


def _render_session_file(path: str) -> str:
    """Render one pi session JSONL as readable text."""
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            out.append(f"[unparsed line: {line[:120]}]")
            continue
        etype = obj.get("type")
        if etype == "session":
            out.append(f"[session {obj.get('id')} cwd={obj.get('cwd')}]")
        elif etype == "model_change":
            out.append(f"[model] {obj.get('modelId')} "
                       f"(provider {obj.get('provider')})")
        elif etype == "thinking_level_change":
            out.append(f"[thinking level] {obj.get('thinkingLevel')}")
        elif etype == "message":
            out.extend(_render_message(obj.get("message") or {}))
        elif etype in ("agent_start", "agent_end", "agent_settled",
                       "turn_start", "turn_end"):
            pass  # structural noise
        else:
            out.append(f"[{etype}]")
    return "\n".join(out)


def _render_stream_file(path: str) -> str:
    """Render a pi --mode json event stream (pi-output.json). Used when the
    session log was not captured (e.g. the run was killed mid-turn):
    message_end events are complete; for turns that never ended, the last
    message_update carries the accumulated partial text."""
    out = []
    ended_roles = set()
    partial_text = {}  # role -> text of last message_update
    streaming_calls = {}  # toolCall contentIndex -> {name, args}
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = obj.get("type")
        if etype == "session":
            out.append(f"[session {obj.get('id')} cwd={obj.get('cwd')}]")
        elif etype == "model_change":
            out.append(f"[model] {obj.get('modelId')} "
                       f"(provider {obj.get('provider')})")
        elif etype == "thinking_level_change":
            out.append(f"[thinking level] {obj.get('thinkingLevel')}")
        elif etype == "message_end":
            msg = obj.get("message") or {}
            ended_roles.add(msg.get("role"))
            out.extend(_render_message(msg))
        elif etype == "message_update":
            ev = obj.get("assistantMessageEvent") or {}
            ekind = ev.get("type")
            if ekind == "toolcall_start":
                streaming_calls[ev.get("contentIndex")] = {
                    "name": ev.get("toolName", "?"), "args": ""}
            elif ekind == "toolcall_delta":
                call = streaming_calls.setdefault(
                    ev.get("contentIndex"), {"name": "?", "args": ""})
                call["args"] += ev.get("delta") or ""
            else:
                msg = obj.get("message") or {}
                role = msg.get("role", "?")
                text = "".join(c.get("text", "") for c in msg.get("content", [])
                               if isinstance(c, dict) and c.get("type") == "text")
                if text:
                    partial_text[role] = text
        # message_start / agent_* / turn_* : structural noise
    for idx in sorted(streaming_calls):
        call = streaming_calls[idx]
        out.append(f"[tool call: {call['name']} — INCOMPLETE, run killed while "
                   f"streaming {len(call['args'])} chars of arguments]\n"
                   f"args: {_clip(call['args'], 600, 600)}")
    for role, text in partial_text.items():
        if role not in ended_roles:
            out.append(f"[{role} — turn incomplete, run killed]\n"
                       f"{_clip(text, 2000, 4000)}")
    return "\n".join(out)


def _render_artifacts_listing(artifacts: str, limit: int = 300) -> str:
    if not os.path.isdir(artifacts):
        return "  (no artifacts captured)"
    entries = []
    for root, dirs, names in os.walk(artifacts):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "target")]
        for n in names:
            p = os.path.join(root, n)
            try:
                size = os.path.getsize(p)
            except OSError:
                size = -1
            entries.append((os.path.relpath(p, artifacts), size))
    entries.sort()
    lines = [f"  {size:>10}  {rel}" for rel, size in entries[:limit]]
    if len(entries) > limit:
        lines.append(f"  … [{len(entries) - limit} more files]")
    if not lines:
        lines.append("  (empty)")
    return "\n".join(lines)


def render_output(case: dict, results: str, artifacts: str,
                  checks: list[dict], run_rc) -> None:
    """Write results/output.txt — a human-readable run transcript."""
    meta_path = os.path.join(results, "metadata.json")
    meta = {}
    if os.path.isfile(meta_path):
        meta = json.load(open(meta_path))
    verdict = ""
    vpath = os.path.join(results, "verdict.txt")
    if os.path.isfile(vpath):
        verdict = open(vpath).read().strip()

    out = [_hr("PCP RUN TRANSCRIPT")]
    out.append(f"case:    {case['name']} ({case['schema']})")
    if case.get("description"):
        out.append(f"about:   {case['description']}")
    out.append(f"model:   {meta.get('model') or os.environ.get('PCP_MODEL') or '<unset>'}")
    if meta:
        out.append(f"image:   {meta.get('image')} ({meta.get('imageDigest')})")
        out.append(f"host:    {meta.get('hostOs')} / {meta.get('hostArch')}")
        out.append(f"run:     {meta.get('startedAt')} → {meta.get('finishedAt')} "
                       f"(wall {meta.get('wallTimeSecs')}s, VM exit "
                       f"{meta.get('exitCode')})")
    elif run_rc is not None:
        out.append(f"run:     VM exit {run_rc} (no metadata — run failed early)")
    if verdict:
        out.append(f"verdict: {verdict}")
    out.append(_hr())

    out.append("")
    out.append(_hr("CHECKS"))
    out.append("")
    if not checks:
        out.append("  (no checks defined)")
    for c in checks:
        out.append(f"  [{c['status']}] {c['name']}  ({c['durationMs']} ms)")
        out.append(f"      {c.get('check', '')}")
        if c.get("detail", "").strip():
            for ln in c["detail"].rstrip().splitlines()[:20]:
                out.append(f"      | {ln}")

    out.append("")
    out.append(_hr("ARTIFACTS"))
    out.append("")
    out.append(_render_artifacts_listing(artifacts))

    out.append("")
    out.append(_hr("PI SESSION"))
    sessions_dir = os.path.join(artifacts, "sessions")
    files = []
    if os.path.isdir(sessions_dir):
        for root, _, names in os.walk(sessions_dir):
            for n in names:
                if n.endswith(".jsonl"):
                    files.append(os.path.join(root, n))
    out.append("")
    if files:
        for path in sorted(files):
            rel = os.path.relpath(path, artifacts)
            out.append(_hr(f"session: {rel}", ch="-"))
            out.append("")
            try:
                out.append(_render_session_file(path))
            except Exception as e:  # renderer must never break the run
                out.append(f"  [failed to render session: {e}]")
    elif os.path.isfile(os.path.join(artifacts, "pi-output.json")):
        # session log not captured (e.g. the run was killed mid-turn) — fall
        # back to the --mode json event stream, which survives on /results
        out.append(_hr("from pi-output.json (session log not captured — "
                       "run likely killed mid-turn)", ch="-"))
        out.append("")
        try:
            out.append(_render_stream_file(os.path.join(artifacts,
                                                        "pi-output.json")))
        except Exception as e:
            out.append(f"  [failed to render stream: {e}]")
    else:
        out.append("  (no pi session transcript captured)")
    out.append("")

    with open(os.path.join(results, "output.txt"), "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"pcp_case: transcript written → {os.path.join(results, 'output.txt')}")


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(add_help=True, description="PCP case runner")
    ap.add_argument("--checks-only", action="store_true",
                    help="run checks against existing artifacts, no VM run")
    ap.add_argument("--model", default=None,
                    help="model name (overrides PCP_MODEL env; results are "
                         "stored per model)")
    ap.add_argument("case", help="tests/case-NNN-name")
    args = ap.parse_args()

    if args.model is not None:
        os.environ["PCP_MODEL"] = args.model
    checks_only = args.checks_only
    case_dir = os.path.abspath(args.case)
    case = load_case(case_dir)
    # repo-wide results root: <repo>/results/<case-dir-name>/<MODEL>/
    repo_root = os.path.dirname(PCP_DIR)
    results_root = os.environ.get("PCP_RESULTS_ROOT") or os.path.join(repo_root, "results")
    results = os.path.join(results_root, os.path.basename(case_dir),
                           model_dir_name())
    artifacts = os.path.join(results, "artifacts")

    run_rc = None
    if not checks_only:
        # clean slate per run: remove everything from previous runs of this
        # (model, case) combo — no stale metadata/transcripts may survive
        shutil.rmtree(results, ignore_errors=True)
        os.makedirs(results, exist_ok=True)
        run_rc = run_vm(case, case_dir, results)
        print(f"pcp_case: VM run exit={run_rc}")
    else:
        os.makedirs(results, exist_ok=True)

    checks = run_checks(case, case_dir, results, artifacts)
    rc = write_results(case, results, checks)
    render_output(case, results, artifacts, checks, run_rc)
    if run_rc is not None and run_rc != 0:
        print(f"pcp_case: note — VM run exited nonzero ({run_rc}); "
              f"see results/metadata.json", file=sys.stderr)
    sys.exit(rc)


if __name__ == "__main__":
    main()
