#!/usr/bin/env python3
"""PCP sandbox tool — build, run, and clean up the standardized guest VM.

Replaces the former build.sh / setup-host.sh / run-test.sh / cleanup.sh /
pcp-entrypoint.sh (one tool, subcommands; stdlib only, runs on the system
python3). See JOURNAL.md for design and decisions.

Subcommands:
  setup                per-boot host preparation (idempotent, no sudo)
  build [--tag T]      build agent-sandbox:<T>, print + record its digest
  run <case> [opts]    one test case = one ephemeral VM (tunnel, watchdog,
                       metadata.json)
  cleanup [--images]   prune stopped containers (--images: also remove
                       non-pinned images)

Run parameter precedence: --flag > PCP_* env var > documented default.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

PCP_DIR = os.path.dirname(os.path.abspath(__file__))

# The guest entrypoint, staged into the build context by `build`.
# Runs as root: starts sshd (for the harness reverse tunnel), then drops to
# the non-root 'agent' user and execs the command.
# NOTE: keep byte-identical to the former sandbox/pcp-entrypoint.sh so
# rebuilds of the same Dockerfile produce the same image digest.
ENTRYPOINT = """#!/bin/bash
# PCP guest entrypoint. Runs as root: starts sshd (for the harness reverse
# tunnel), then drops to the non-root 'agent' user and execs the command.
set -euo pipefail

# Host keys are generated per container filesystem (not baked into the image).
ssh-keygen -A >/dev/null 2>&1
mkdir -p /run/sshd
/usr/sbin/sshd

if [ "$#" -eq 0 ]; then
  # no command: idle (interactive debugging via harness ssh)
  exec sleep infinity
fi

exec runuser -u agent -- env HOME=/home/agent USER=agent LOGNAME=agent "$@"
"""


def fail(msg: str, code: int = 2) -> None:
    print(f"pcp_sandbox: {msg}", file=sys.stderr)
    sys.exit(code)


def sh(cmd: list, **kw) -> subprocess.CompletedProcess:
    kw.setdefault("text", True)
    return subprocess.run(cmd, **kw)


def image_digest(image_ref: str) -> str:
    """Digest of a locally stored image (ref like 'agent-sandbox:1.1')."""
    proc = sh(["container", "image", "ls", "--format", "json"],
              capture_output=True)
    for entry in json.loads(proc.stdout):
        name = (entry.get("configuration") or {}).get("name") or ""
        if name.split("/")[-1] == image_ref:
            return ((entry.get("configuration") or {})
                    .get("descriptor", {}).get("digest", ""))
    return ""


def container_running() -> bool:
    proc = sh(["container", "system", "status"], capture_output=True)
    return bool(re.search(r"^status\s+running", proc.stdout or "", re.M))


def env_or(args_val, env_key, default):
    if args_val is not None:
        return args_val
    return os.environ.get(env_key) or default


# ---------------------------------------------------------------- setup
def cmd_setup(args) -> int:
    if container_running():
        print("container system: already running")
    else:
        print("container system: starting...")
        # --enable-kernel-install: install apple/container's default kernel
        # non-interactively if missing (component of apple/container itself).
        sh(["container", "system", "start", "--enable-kernel-install"])
    print("PCP host setup complete.")
    return 0


# ---------------------------------------------------------------- build
def cmd_build(args) -> int:
    tag = env_or(args.tag, "PCP_TAG", "1.1")
    image = f"agent-sandbox:{tag}"

    # stage a clean build context: Dockerfile + pi-config + generated entrypoint
    staging = tempfile.mkdtemp(prefix="pcp-build-")
    try:
        shutil.copy(os.path.join(PCP_DIR, "Dockerfile"), staging)
        shutil.copytree(os.path.join(PCP_DIR, "pi-config"),
                        os.path.join(staging, "pi-config"))
        entry = os.path.join(staging, "pcp-entrypoint.sh")
        with open(entry, "w") as f:
            f.write(ENTRYPOINT)
        os.chmod(entry, 0o755)

        proc = sh(["container", "build", "--progress", "plain",
                   "-t", image, staging])
        if proc.returncode != 0:
            fail(f"build failed (rc={proc.returncode})")
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    digest = image_digest(image)
    if not digest:
        fail(f"built {image} but could not read its digest")
    print(f"built {image}\n{digest}")
    return 0


# ---------------------------------------------------------------- run
class RunOpts:
    """Resolved options for one `run` invocation."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


def do_run(o: RunOpts) -> int:
    tmp, ssh_proc, watchdog = o.tmp, None, None
    forced = {"flag": False}

    def cleanup():
        if ssh_proc and ssh_proc.poll() is None:
            ssh_proc.terminate()
        if watchdog:
            watchdog.cancel()
        # quiesce + remove the container (fs is copied out by now)
        sh(["container", "stop", o.cname], capture_output=True)
        sh(["container", "rm", "-f", o.cname], capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)

    try:
        # --- per-run ephemeral ssh keypair (pub half mounted into the guest)
        os.makedirs(os.path.join(tmp, "ssh"), exist_ok=True)
        sh(["ssh-keygen", "-q", "-t", "ed25519", "-N", "",
            "-f", f"{tmp}/pcp_id", "-C", f"pcp-{o.case_name}"], check=True)
        shutil.copy(f"{tmp}/pcp_id.pub", f"{tmp}/ssh/authorized_keys")
        os.chmod(f"{tmp}/ssh", 0o755)
        os.chmod(f"{tmp}/ssh/authorized_keys", 0o644)

        # --- per-run pi config (mirrors the host setup; no secrets)
        # - auth.json: the llama.cpp connection (a loopback URL, not a secret)
        # - models-store.json: provider catalog with the PCP_MODEL entry
        # - settings.json: default provider/model
        # NOTE: do NOT use <agent-dir>/models.json to override the built-in
        # "llama.cpp" provider — pi reports "Provider is not configured".
        pi_dir = os.path.join(tmp, "pi", "agent")
        os.makedirs(pi_dir, exist_ok=True)
        model_id = o.model or "pcp-model"
        base_url = f"http://127.0.0.1:{o.model_port}"
        json.dump({"llama.cpp": {"type": "api_key",
                                 "env": {"LLAMA_BASE_URL": base_url}}},
                  open(os.path.join(pi_dir, "auth.json"), "w"), indent=1)
        json.dump({"llama.cpp": {
            "checkedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "models": [{
                "id": model_id, "name": model_id,
                "api": "openai-completions", "provider": "llama.cpp",
                "baseUrl": f"{base_url}/v1",
                "reasoning": True, "input": ["text"],
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                "contextWindow": int(o.context_window),
                "maxTokens": int(o.context_window),
                "compat": {
                    "supportsStore": False, "supportsDeveloperRole": False,
                    "supportsReasoningEffort": False,
                    "supportsUsageInStreaming": True,
                    "supportsStrictMode": False, "maxTokensField": "max_tokens",
                },
            }]}},
            open(os.path.join(pi_dir, "models-store.json"), "w"), indent=1)
        json.dump({"defaultProvider": "llama.cpp", "defaultModel": model_id},
                  open(os.path.join(pi_dir, "settings.json"), "w"), indent=1)

        # --- network policy
        netargs = []
        if o.net != "default":
            if sh(["container", "network", "inspect", o.net],
                  capture_output=True).returncode != 0:
                sh(["container", "network", "create", o.net, "--internal"],
                   check=True)
            netargs = ["--network", o.net]

        # --- guest command for the exec phase
        if o.guest_script:
            gdir = os.path.dirname(os.path.abspath(o.guest_script))
            gname = os.path.basename(o.guest_script)
            guest_mount = ["-v", f"{gdir}:/pcp-run:ro"]
            guest_cmd = ["bash", f"/pcp-run/{gname}"]
        else:
            guest_mount = []
            guest_cmd = ["bash", "/work/run.sh"]

        # --- start an IDLE container (no --rm): the fs persists after stops,
        # and the init (sleep infinity) is safe to "restart". The guest script
        # runs later via `container exec` and writes to container-local
        # /artifacts (root-owned 750 — invisible to the agent user). There is
        # deliberately NO results mount into the guest.
        run_cmd = (["container", "run", "-d", "--name", o.cname,
                    "-c", o.cpus, "-m", o.memory] + netargs + guest_mount +
                   ["-v", f"{o.case_dir}:/work:ro",
                    "-v", f"{tmp}/pi:/home/agent/.pi",
                    "-v", f"{tmp}/ssh:/home/agent/.ssh",
                    "-e", f"PCP_CASE={o.case_name}",
                    "-e", f"PCP_MODEL={o.model}",
                    "-e", f"PCP_MODEL_PORT={o.model_port}",
                    o.image, "sleep", "infinity"])
        proc = sh(run_cmd, capture_output=True)
        if proc.returncode != 0:
            fail(f"failed to start container: {proc.stderr.strip()}")
        start_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        start = time.monotonic()
        digest = image_digest(o.image)

        # --- outer watchdog: force shutdown if the exec phase overruns
        def force_stop():
            forced["flag"] = True
            sh(["container", "stop", o.cname], capture_output=True)
        watchdog = threading.Timer(o.timeout_secs, force_stop)
        watchdog.daemon = True
        watchdog.start()

        # --- tunnel: wait for the guest IP, reverse-tunnel host loopback in
        ip = ""
        for _ in range(120):
            listing = sh(["container", "ls", "--format", "json"],
                         capture_output=True)
            try:
                for entry in json.loads(listing.stdout or "[]"):
                    if entry.get("id") != o.cname:
                        continue
                    status = entry.get("status") or {}
                    if status.get("state") != "running":
                        continue
                    nets = status.get("networks") or []
                    if nets:
                        ip = (nets[0].get("ipv4Address") or "").split("/")[0]
                        break
            except json.JSONDecodeError:
                pass
            if ip:
                break
            time.sleep(0.5)
        if ip:
            print(f"guest {o.cname} at {ip}; "
                  f"tunneling 127.0.0.1:{o.model_port} (host loopback) into guest")
            ssh_proc = subprocess.Popen(
                ["ssh", "-i", f"{tmp}/pcp_id",
                 "-o", "StrictHostKeyChecking=no",
                 "-o", "UserKnownHostsFile=/dev/null",
                 "-o", "LogLevel=ERROR", "-o", "ExitOnForwardFailure=yes",
                 "-R", f"127.0.0.1:{o.model_port}:127.0.0.1:{o.model_port}",
                 "-N", f"agent@{ip}"])
        else:
            print("warning: guest IP not found; no tunnel "
                  "(model endpoint unreachable in guest)", file=sys.stderr)

        # --- agent run: exec the guest script (as root, in the container)
        print(f"pcp_sandbox: exec {guest_cmd[-1]} …")
        exec_proc = subprocess.Popen(["container", "exec", o.cname] + guest_cmd)
        exec_rc = exec_proc.wait()

        # --- force shutdown, then restart: quiesces everything (lingering
        # servers, hung agents) and gives a running container to copy from
        sh(["container", "stop", o.cname], capture_output=True)
        sh(["container", "start", o.cname], capture_output=True)

        # --- copy /artifacts out (tar over exec)
        artifacts_host = os.path.join(o.results_dir, "artifacts")
        os.makedirs(artifacts_host, exist_ok=True)
        p1 = subprocess.Popen(["container", "exec", o.cname,
                               "tar", "-C", "/artifacts", "-cf", "-", "."],
                              stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["tar", "-xf", "-", "-C", artifacts_host],
                              stdin=p1.stdout)
        p2.wait()
        p1.wait()

        # --- exit code: the guest script records its own rc in /artifacts/rc
        rc_file = os.path.join(artifacts_host, "rc")
        if os.path.isfile(rc_file):
            rc = int(open(rc_file).read().strip() or 1)
        elif forced["flag"]:
            rc = 124  # outer watchdog fired before the guest could record rc
        else:
            rc = exec_rc if exec_rc != 0 else 1

        # --- record metadata
        wall = int(time.monotonic() - start)
        end_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        host_os = sh(["sw_vers", "-productVersion"], capture_output=True).stdout.strip()
        host_build = sh(["sw_vers", "-buildVersion"], capture_output=True).stdout.strip()
        metadata = {
            "case": o.case_name, "image": o.image, "imageDigest": digest,
            "hostOs": f"{host_os} ({host_build})",
            "hostArch": os.uname().machine,
            "model": o.model, "modelPort": int(o.model_port),
            "network": o.net, "cpus": int(o.cpus), "memory": o.memory,
            "timeoutSecs": o.timeout_secs,
            "startedAt": start_iso, "finishedAt": end_iso,
            "wallTimeSecs": wall, "exitCode": rc,
        }
        meta_path = os.path.join(o.results_dir, "metadata.json")
        json.dump(metadata, open(meta_path, "w"), indent=2)
        print(f"done: {o.case_name} exit={rc} ({meta_path})")
        return rc
    finally:
        cleanup()


# ---------------------------------------------------------------- cleanup
def cmd_cleanup(args) -> int:
    tag = env_or(args.tag, "PCP_TAG", "1.1")
    keep = f"agent-sandbox:{tag}"
    print("pruning stopped containers...")
    sh(["container", "prune"])
    if args.images:
        print(f"removing images except {keep}...")
        listing = sh(["container", "image", "ls", "--format", "json"],
                     capture_output=True)
        for entry in json.loads(listing.stdout or "[]"):
            ref = (entry.get("configuration") or {}).get("name") or ""
            if not ref or ref.split("/")[-1] == keep:
                continue
            # keep the base image (needed for cached rebuilds) and internals
            if ref.startswith(("docker.io/library/debian",
                               "ghcr.io/apple/container")):
                continue
            sh(["container", "image", "rm", ref], capture_output=True)
    print("images kept:")
    sh(["container", "image", "ls"])
    return 0


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(
        prog="pcp_sandbox.py",
        description="PCP sandbox tool (build/run/cleanup the guest VM)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("setup", help="per-boot host preparation (idempotent)")

    p = sub.add_parser("build", help="build the guest image")
    p.add_argument("--tag", help="image tag (default PCP_TAG or 1.1)")

    p = sub.add_parser("run", help="run one test case in an ephemeral VM")
    p.add_argument("case", help="tests/case-NNN-name (legacy run.sh cases)")
    p.add_argument("--guest-script",
                   help="host script to run instead of /work/run.sh "
                        "(mounted ro at /pcp-run; used by pcp/pcp_case.py)")
    p.add_argument("--results-dir", help="override results dir")
    p.add_argument("--model", help="model name (default PCP_MODEL or unset)")
    p.add_argument("--tag", help="image tag (default PCP_TAG or 1.1)")
    p.add_argument("--model-port", help="host model port (default PCP_MODEL_PORT or 9931)")
    p.add_argument("--cpus", help="guest CPUs (default PCP_CPUS or 2)")
    p.add_argument("--memory", help="guest memory (default PCP_MEMORY or 4G)")
    p.add_argument("--net", help="network: default=internet, internal=offline "
                                 "(default PCP_NET or default)")
    p.add_argument("--timeout-secs", help="test timeout (default PCP_TIMEOUT_SECS or 1800)")
    p.add_argument("--context-window", help="model context window "
                                            "(default PCP_CONTEXT_WINDOW or 262144)")

    p = sub.add_parser("cleanup", help="prune stopped containers / images")
    p.add_argument("--images", action="store_true",
                   help="also remove images except agent-sandbox:<tag>")
    p.add_argument("--tag", help="image tag to keep (default PCP_TAG or 1.1)")

    args = ap.parse_args()
    if args.cmd == "setup":
        return cmd_setup(args)
    if args.cmd == "build":
        return cmd_build(args)
    if args.cmd == "run":
        opts = RunOpts(
            case_dir=os.path.abspath(args.case),
            case_name=os.path.basename(os.path.abspath(args.case)),
            results_dir=os.path.abspath(args.results_dir)
            if args.results_dir else os.path.join(
                ROOT, "results", os.path.basename(os.path.abspath(args.case))),
            tmp=tempfile.mkdtemp(prefix="pcp-run-"),
            cname=f"pcp-test-{os.path.basename(os.path.abspath(args.case))}"
                  f"-{os.getpid()}",
            image=f"agent-sandbox:{env_or(args.tag, 'PCP_TAG', '1.1')}",
            tag=env_or(args.tag, "PCP_TAG", "1.1"),
            model=env_or(args.model, "PCP_MODEL", ""),
            model_port=env_or(args.model_port, "PCP_MODEL_PORT", "9931"),
            cpus=env_or(args.cpus, "PCP_CPUS", "2"),
            memory=env_or(args.memory, "PCP_MEMORY", "4G"),
            net=env_or(args.net, "PCP_NET", "default"),
            timeout_secs=int(env_or(args.timeout_secs,
                                    "PCP_TIMEOUT_SECS", "1800")),
            context_window=env_or(args.context_window,
                                  "PCP_CONTEXT_WINDOW", "262144"),
            guest_script=args.guest_script,
            run_pid=None,
        )
        if not os.path.isfile(os.path.join(opts.case_dir, "run.sh")) \
                and not opts.guest_script:
            fail(f"no run.sh in {opts.case_dir} (and no --guest-script)")
        os.makedirs(opts.results_dir, exist_ok=True)
        return do_run(opts)
    if args.cmd == "cleanup":
        return cmd_cleanup(args)
    fail(f"unknown command {args.cmd}")


if __name__ == "__main__":
    sys.exit(main())
