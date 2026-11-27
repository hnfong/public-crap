# Plan: Isolated, Standardized Linux Test Environment for Coding-Agent Evaluation

Status: Phase 1 (environment + harness, §3 chunks 1–6) DONE.
Phase 2 (declarative test cases, §7) in progress.
Date: 2026-11-27

---

## 1. Requirements (as understood)

### 1.1 Goal
Run repeatable, automated test cases that evaluate how well open-weight language models
perform coding tasks. Each test drives a coding agent (the Pi CLI harness) against a
model, inside a Linux environment that is identical from run to run.

### 1.2 Environment facts
- Host: macOS 26.7.1 on Apple Silicon (arm64).
- The model under test is an open-weight model served locally on the **host** by
  llama.cpp (OpenAI-compatible HTTP API, bound to 127.0.0.1).
- The agent under test is **Pi** (`pi-coding-agent`, Node.js CLI).
- The agent runs **inside the Linux guest**, not on the host.

### 1.3 Functional requirements
1. **Standardized guest**: every test runs in an identical Linux environment —
   same OS base, same toolchain versions, same agent version. Rebuilding the
   environment from the repo must produce the same environment.
2. **Isolation per test**: each test case runs in a fresh, disposable environment.
   No state (files, packages, env vars, processes) may leak between test cases.
   Model weights never leave the host.

User note: true. Note that each "run" would have these params: (MODEL,
TEST_CASE). We're running multiple models over different test cases.

3. **Host reachability**: the guest must be able to reach the llama.cpp server on
   the host at specific port(s), over HTTP, without exposing the host to the guest
   or the network in any broader way.
4. **Guest toolchain** (the environment a coding agent is expected to work in):
   - basic unix tooling (shell, coreutils, git, curl, editors-free essentials, jq, ripgrep, …)
   - Python 3 (with venv)
   - C/C++ with **clang** preferred (gcc acceptable as fallback), cmake/ninja/make
   - Rust (stable, pinned toolchain)
   - Node.js + npm (pinned)
   - Java (JDK, pinned)
5. **Scriptable**: the whole cycle (prepare → run test → collect results → clean up)
   is driven by shell scripts in this repo, runnable by a human and by a future CI.
6. **Network policy per test**: tests may run with internet access (agent may need
   to install packages) or fully offline (only the host model endpoint reachable).

### 1.4 Non-functional requirements (priorities)
1. **Minimalism** — host side first: prefer off-the-shelf components from/supported
   by Apple; no Docker Desktop, no extra hypervisors, no daemons beyond what is
   strictly necessary. Guest image as small as practical.
2. **Simplicity** — few moving parts, few concepts, everything reproducible from
   this repo with a handful of well-understood commands.

User note: you must not install anything on the host unless the user explicitly
allows this. Ask the user first if you need to install anything outside of this
repo. The user will install apple containers (already).

### 1.5 Out of scope (for now)
- CI/CD integration, image registry publishing, multi-host or parallel farms.
- Testing GUI/browser-based agent workflows.
- Running multiple model servers concurrently or model scheduling.
- Windows/Linux hosts.

---

## 2. Proposed approach

### 2.1 Summary
Use **`apple/container`** (Apple's first-party Linux container runtime, v1.7.1) on
the Mac. Each container it runs is a **full lightweight Linux VM** built on Apple's
Virtualization.framework and vmnet — VM-grade isolation with a container workflow.
The standardized guest is a **pinned OCI image** built from `debian:trixie-slim`
with all toolchains version-pinned. Each test case gets an ephemeral
`container run --rm` of that image. The host's llama.cpp is reached through
`container`'s built-in host-bridge DNS domain.

### 2.2 Why this approach
| Requirement | How it is met |
|---|---|
| Minimal host, Apple-supported | One signed Apple `.pkg` + one launchd agent. No Docker, no Lima, no third-party hypervisor, no Homebrew dependency. |
| Standardized guest | One Dockerfile in the repo → one OCI image. All fast-moving runtimes pinned by `ARG`. Image digest recorded per test run. |
| Isolation per test | Every `container run` is its own VM (own kernel, own memory, own network namespace). `--rm` disposes it. |
| Host port access | `container system dns create host.container.internal --localhost <ip>` → guest resolves the host by name; llama.cpp stays bound to 127.0.0.1. |
| Simplicity | One CLI, plain shell scripts, no orchestration layer. |

### 2.3 Key decisions (with rationale)
1. **`apple/container` over Tart/Lima/Docker Desktop.**
   - Apple first-party → satisfies "from/supported by Apple" as strongly as possible.
   - Per-container VM → stronger isolation than shared-VM container runtimes.
   - OCI images → standardization without inventing a VM template format.
   - Tart (third-party, full VMs, snapshots/fork) is the fallback if we ever need
     full-OS semantics (custom kernel, kernel modules) or VM snapshot/fork.
2. **`debian:trixie-slim` guest base.**
   - glibc (Alpine/musl rejected: breaks prebuilt tooling and some npm/JNI packages).
   - Current stable, arm64-native, ~80 MB base, everything needed is in apt.
   - Newer clang (19/20) than Ubuntu's.
3. **Pinned upstream installers for fast-moving runtimes** (Node via official
   nodejs.org tarball + SHA-256, Rust via official rustup + pinned toolchain),
   **apt for stable toolchains** (clang, JDK, Python, unix tools). Rationale: apt
   versions drift between distro releases; `ARG`-pinned installers freeze the
   toolchain into the image so the "standardized environment" claim holds across
   rebuilds and months.
4. **Ephemeral container per test case** (not a persistent "machine"). Machines
   (`container machine`) mount `$HOME` rw with full capabilities — fine for
   interactive debugging, wrong for a test harness.
5. **Model weights stay on the host.** The guest only ever sees an HTTP endpoint.

### 2.4 Architecture sketch
```
macOS 26 (host)
├── container system (launchd agent + XPC helpers)   ← apple/container v1.7.1
├── llama-server (llama.cpp)  127.0.0.1:8080         ← model under test
└── sandbox/ scripts
      │
      ▼  container run --rm  (fresh Linux VM per test)
debian:trixie-slim image "agent-sandbox:<tag>"
├── toolchains (pinned): node, rust, clang/gcc, python3, openjdk-21
├── pi (pinned version) configured → http://host.container.internal:8080/v1
└── /work (ro test fixture)   /results (rw, host dir)
```

---

## 3. Work plan (bite-sized chunks)

Each chunk is independently doable and verifiable. Checkboxes = steps.

### Chunk 1 — Verify host prerequisites (5 min, no changes) — DONE
- [x] Confirm `sw_vers` ≥ 26 and `uname -m` = arm64 (26.7.1 / arm64 ✅).
- [x] llama.cpp binaries at `~/projects/llama.gguf/` (`llama-server` etc.; not on PATH).
- [x] Fixed host endpoint contract (owner-confirmed): `PORT = 9931`,
      OpenAI-compatible `/v1`, bound to `127.0.0.1`. Model name is a per-run
      parameter: run params = `(PCP_MODEL, TEST_CASE)`.
- **Done when**: we know the exact host URL the guest will call. ✅

### Chunk 2 — Verify `apple/container` — DONE (already installed by owner)
- [x] `container --version` → 1.7.1 (pinned).
- [x] `container system start` works; `container run --rm alpine echo hello` → `hello`.
- Note: on first start apple/container required its own default kata kernel
  (4.3.1); installed non-interactively via `container system start
  --enable-kernel-install`. Component of apple/container itself, not a new
  host tool; `sandbox/setup-host.sh` handles it idempotently.
- **Done when**: `hello` prints. ✅

### Chunk 3 — Guest → host model connectivity — DONE (SSH reverse tunnel, no sudo)
Owner decision: **no sudo, no `container system dns` host-bridge, no Private
Relay tradeoff.** Owner-suggested approach, implemented and verified:

1. The guest image runs `sshd`; `run-test.sh` generates an **ephemeral SSH
   keypair per run** (temp dir), mounts the public key into the guest, and
   opens `ssh -R 127.0.0.1:<port>:127.0.0.1:<port> agent@<guest-ip> -N`.
2. The guest reaches the model at `http://127.0.0.1:9931/v1` — the same
   address on every host, and llama.cpp stays bound to host `127.0.0.1`.
3. Guest IP is discovered from `container ls --format json`.

Verified: throwaway debian container + fake model server on host loopback →
guest `curl 127.0.0.1:9931` succeeded; also verified through the harness on
both `default` and `internal` networks.
- **Done when**: a guest can hit the host's model endpoint over loopback. ✅

<details><summary>original plan (superseded)</summary>

% - [ ] `sudo container system dns create host.container.internal --localhost 203.0.113.113`
% - [ ] Start llama-server bound to 127.0.0.1.
% - [ ] `container run --rm alpine/curl curl -s http://host.container.internal:8080/v1/models`
%       (or equivalent health probe) — expect a response from the host server.
% - [ ] Note the caveats in `sandbox/README` (or here): the rule is removed on macOS
%       reboot (re-run command); creating the localhost domain disables iCloud
%       Private Relay.
% - **Done when**: a throwaway container can hit the host's model endpoint by name.
User comment: avoid sudo. Can we achieve something similar by ssh-ing from host to guest?

</details>

### Chunk 4 — Guest image: `sandbox/Dockerfile` (30 min) — DONE
- [x] Write `sandbox/Dockerfile`:
  - [x] Base: `FROM debian:trixie-slim` (pinned by digest)
  - [x] `ARG` pins: `NODE_VERSION`, `RUST_TOOLCHAIN`, `RUSTUP_VERSION`,
        `PI_VERSION`; `JAVA` fixed to openjdk-21.
  - [x] apt layer: core unix tooling (git, curl, wget, openssh-client, jq, ripgrep,
        unzip, zip, xz-utils, bzip2, file, less, ca-certificates),
        C/C++ (build-essential, clang, lld, cmake, ninja-build),
        python3 + python3-venv + python3-pip, openjdk-21-jdk-headless.
  - [x] Node: official nodejs.org tarball (linux-arm64) + SHASUMS256 verification,
        extracted to `/usr/local` (no third-party repo).
  - [x] Rust: official rustup, `--profile minimal --default-toolchain $RUST_TOOLCHAIN`
        (proxies in `/home/agent/.cargo/bin`).
  - [x] Pi: `npm install -g @earendil-works/pi-coding-agent@$PI_VERSION`.
  - [x] Housekeeping: `DEBIAN_FRONTEND=noninteractive`, `rm -rf /var/lib/apt/lists/*`,
        non-root `agent` user + `/work`, no apt upgrade drift, sshd for the tunnel.
- [x] Add `sandbox/build.sh`:
  `container build -t agent-sandbox:$TAG sandbox/` + print the resulting image
  digest for recording in test metadata.
- **Done when**: Dockerfile + build.sh exist and are reviewed; versions pinned. ✅

Implemented pins (owner: debian pin is the deliberate one for now; others are
ARGs recorded here so bumping is a reviewable diff):
`debian:trixie-slim` @ `sha256:8aa5a7bf…`, Node `22.23.5` (official tarball,
SHASUMS-verified), rustup `1.28.2` → Rust `1.100.0` (minimal profile), pi
`1.6.1` (npm), clang `19.1.7` / g++ `14.2.0` / cmake `3.31.6` / ninja (apt),
Python `3.13.5` (apt), openjdk `21.0.13` (apt).

Other decisions:
- **Non-root agent** (owner Q3): `useradd agent` (uid 1000); image entrypoint
  `pcp-entrypoint.sh` starts sshd, then drops to `agent` and execs the command.
- **pi config** (owner Q2, corrected during phase 2 live testing): mirror the
  host mechanism exactly — per run, `run-test.sh` mounts a generated
  `~/.pi/agent` containing:
  `auth.json` (`{"llama.cpp": {type: "api_key", env: {LLAMA_BASE_URL:
  http://127.0.0.1:<port>}}}` — the connection, a loopback URL, not a secret),
  `models-store.json` (provider catalog with the `PCP_MODEL` entry), and
  `settings.json` (default provider/model). `auth.json` on the host contained
  no secrets for llama.cpp; `trust.json` stays excluded.
  **Do not** use `<agent-dir>/models.json` to override the built-in
  `llama.cpp` provider — pi reports "Provider is not configured". (Custom
  provider ids via `models.json` would also work, but mirroring the host is
  simpler and proven.)
- Rust `CARGO_HOME=/home/agent/.cargo` (agent-writable); toolchain read-only in
  `/usr/local/rustup`.

### Chunk 5 — Build and smoke-test the image (15–30 min, mostly waiting) — DONE
- [x] `sandbox/build.sh 1.0` (first build pulls base + toolchains; later builds
      use layer cache).
- [x] Smoke test, one container per check (all `--rm`):
  - [x] `node --version && npm --version` → pinned values
  - [x] `rustc --version && cargo --version` → pinned values
  - [x] `clang --version && g++ --version && cmake --version`
  - [x] `python3 --version && python3 -m venv /tmp/v && /tmp/v/bin/python -V`
  - [x] `java -version` → OpenJDK 21
  - [x] `pi --version` → pinned value
- **Done when**: all versions match the `ARG` pins exactly. ✅

`agent-sandbox:1.0` digest
`sha256:c9a6730e21566cbd53d4823d295899e25d77a16a8c7a044908b1cfc62a63320e`
(recorded in `sandbox/.digests/1.0`, gitignored). All smoke checks passed
(node/npm, rustc/cargo, clang/g++/cmake/ninja, python3+venv, openjdk 21, pi
1.6.1) and the entrypoint drops to `agent`.

### Chunk 6 — Test harness scripts (30 min) — DONE

(2026-11-27: the five shell scripts were later consolidated into
`sandbox/pcp_sandbox.py` — subcommands `setup|build|run|cleanup`, stdlib-only,
system python3; the guest entrypoint is embedded in the tool and staged into
the build context, byte-identical to the former file so image digests stay
stable. See §7.)
- [ ] `sandbox/setup-host.sh` (idempotent, per-boot):
  - [ ] `container system start` (no-op if running)
  - [ ] `sudo container system dns create host.container.internal --localhost 203.0.113.113`
        (tolerate "already exists")
- [ ] `sandbox/run-test.sh <case-dir>`:
  - [ ] Inputs: case dir under `tests/`, overridable env: `TAG` (image), `CPUS`
        (default 4), `MEMORY` (default 8G), `NET` (default `default`; `internal`
        for offline tests), `TIMEOUT_SECS` (default 1800).
  - [ ] Create offline network if `NET=internal`:
        `container network create sandbox-offline --internal` (tolerate exists).
  - [ ] Run: `container run --rm --name test-<case>-$$ -c $CPUS -m $MEMORY
        --network $NET -v <case>:/work:ro -v <case>/results:/results agent-sandbox:$TAG
        bash /work/run.sh`
  - [ ] Enforce timeout (macOS has no GNU `timeout`; use a small helper, e.g.
        background + watchdog kill) and capture exit code.
  - [ ] Record metadata in `results/metadata.json`: case, image tag+digest, host
        macOS version, model name/quant (from env), wall time, exit code.
  - [ ] Exit with the test's exit code.
- [ ] `sandbox/cleanup.sh`: `container prune` (images/containers) — keep the
  pinned `agent-sandbox:$TAG` image.
- **Done when**: scripts pass shellcheck; a dry run prints the exact commands. ✅

Notes vs. the original plan:
- `setup-host.sh` does **not** create the DNS rule (owner decision); it only
  starts the container system idempotently.
- All overrides are `PCP_*` (owner decision): `PCP_TAG, PCP_MODEL,
  PCP_MODEL_PORT (9931), PCP_CPUS (2), PCP_MEMORY (4G), PCP_NET
  (default|internal|…), PCP_TIMEOUT_SECS (1800), PCP_CONTEXT_WINDOW`.
- `run-test.sh` runs the container in the foreground (background shell) to
  capture the true exit code, uses a watchdog for the timeout, and writes
  `results/metadata.json` (case, image tag+digest, host OS/arch, model, port,
  network, resources, wall time, exit code).
- `tests/case-000-harness-smoke/` is a harness-validation case (toolchain
  versions + tunnel probe), not an agent/model test — the first real agent
  case remains Chunk 7 (deferred per owner).
- shellcheck clean (run in a throwaway container — nothing installed on host).
- Live-verified: default network, `internal` network, fake model server via
  tunnel, metadata capture, exit-code propagation.

Owner note (pi config template): done — sanitized `settings.json` in
`sandbox/pi-config/`; no tokens/API keys are copied (none needed for
localhost llama.cpp).

% ### Chunk 7 — First end-to-end test case (30 min)
% - [ ] `tests/case-001-hello-world/`:
%   - [ ] `run.sh` (executed inside the guest):
%     - [ ] assert toolchain versions (cheap regression guard)
%     - [ ] configure pi to use the host model: OpenAI-compatible base URL
%           `http://host.container.internal:8080/v1` (verify pi's exact provider
%           config mechanism — file vs env — during implementation and pin it here)
%     - [ ] run one trivial pi coding task (e.g. "create a file with this content"
%           or a 5-line function with a test)
%     - [ ] write pass/fail + transcript to `/results/`
%   - [ ] `fixture/` (empty for now; future cases put their repo here)
% - [ ] Run: `sandbox/setup-host.sh && sandbox/run-test.sh tests/case-001-hello-world`
%   with a small model already served by llama-server on the host.
% - **Done when**: a result (pass or fail — the point is a *recorded, comparable*
%   outcome) lands in `tests/case-001-hello-world/results/` with metadata.
% 
% ### Chunk 8 — Isolation and policy hardening (15 min)
% - [ ] Verify offline mode: run case-001 with `NET=internal`; confirm the only
%       reachable endpoint is the host bridge (and that internet is unreachable).
%       (If the host-bridge domain does not resolve on `--internal` networks — an
%       open question from the docs — fall back: offline tests use the default
%       network and the model endpoint remains the only *useful* destination.)
% - [ ] Verify no state leak: run case-001 twice; diff `results/` metadata; confirm
%       the second run's container started from the pristine image (e.g. by having
%       run.sh record `find / -newer /marker` style checks or a sentinel file check).
% - [ ] Decide root vs non-root agent user in the guest (see Open Questions).
% 
% ### Chunk 9 — Housekeeping and reproducibility conventions (10 min)
% - [ ] Document in `sandbox/README.md`: per-boot setup, how to add a test case,
%       how to bump toolchain/pi versions (deliberate `ARG` edits only), cleanup.
% - [ ] Convention: every test's `metadata.json` records the image **digest**
%       (not just tag) so any historical result is exactly reproducible.
% - [ ] Known-caveat list (see §5) lives in the README, not in people's heads.
% 
% ### Chunk 10 — Follow-ups (not now, listed to shape decisions now)
% - [ ] Interactive debug machine: `container machine create agent-sandbox:$TAG
%       --name dev` for hand-testing the agent environment (trusted image only).
% - [ ] Push the image to a private registry (ghcr) if/when CI needs it.
% - [ ] Matrix runs: same case × {model, quant, temperature, pi version} with a
%       small runner script over `run-test.sh`.
% - [ ] Multiple host ports / second service (e.g. a local search endpoint) — the
%       `--localhost` bridge covers this without new machinery.

User comment: chunks 7-10 are fine but we should probably reserve this for later.

---

## 4. Repo layout (target)

```
agentic/
├── JOURNAL.md                  ← this file (was PLAN.md)
├── pcp/                        ← all tooling (was sandbox/ + harness/)
│   ├── README.md               ← how to use
│   ├── pcp_sandbox.py          ← VM tool: setup | build | run | cleanup
│   ├── pcp_case.py             ← case runner: case.py DSL, checks, verdicts
│   ├── Dockerfile              ← standardized guest
│   └── pi-config/              ← sanitized pi settings template
└── tests/
    └── case-NNN-slug/
        ├── case.py             ← the case (Python DSL)
        ├── checks/, fixture/   ← optional per-case helpers and inputs
        └── results/<MODEL>/    ← per-run artifacts + verdicts (gitignored)
```

---

## 5. Known caveats and risks

| # | Caveat | Mitigation |
|---|---|---|
| 1 | `container` is a 1.x product version — evolving fast; CLI stable only within a major. | Pin installer version (v1.7.1); upgrade deliberately. |
| 2/3/5 | ~~Host-bridge DNS~~ **Dropped** (owner decision): no sudo, no `--localhost` domain, no Private Relay tradeoff. Replaced by per-run SSH reverse tunnel (see Chunk 3). Residual exposure: the tunnel forwards exactly one loopback port per run into the guest. |
| 4 | Memory freed inside a container VM is not returned to macOS (partial ballooning). | Ephemeral containers per test (`--rm`) bound the leak; `container system stop/start` between long sessions if needed. |
| 6 | macOS lacks GNU `timeout`. | Watchdog helper in `run-test.sh` (`sleep … kill` background shell). Implemented. |
| 7 | `--internal` network + tunnel interaction | Pre-verified in Chunk 6: the SSH tunnel works on `internal` networks (host→guest vmnet is unaffected). Internet unreachability still to be asserted in Chunk 8. |
| 8 | Image build pulls from external registries (debian, nodejs.org, rustup, npm) — network + supply chain at build time. | Build rarely; verify Node tarball SHA-256 + rustup-init SHA-256; pin everything else by version. |
| 11 | Checks parse pi session-log JSONL, which is an undocumented, evolving format. | Parse defensively (grep/regex over raw text where possible); pin pi version; re-verify on pi bumps. Live session confirmed: tool commands appear under `command` keys. |
| 12 | pi `-p` exits rc=0 even when the turn errored (empty response, provider error). | Framework should treat `stopReason: "error"` / empty assistant content in `pi-output.json` as failure — TODO for the matrix runner; for now outcome checks catch it. |
| 13 | llama.cpp host OOM surfaces as an immediate empty reply ("Compute error", ~40 ms, `stopReason: error`) — looks like a model failure but isn't (observed on Qwen3-30B-A3B while RAM-tight during dev; disappeared after server restart). | Record as-is (FAIL is fair — the run didn't produce an answer); when diagnosing, check the server log before blaming the model. |
| 9 | apple/container requires its default kata kernel on first start (downloads from kata-containers releases). | Part of apple/container itself; installed once via `container system start --enable-kernel-install`; `setup-host.sh` re-checks idempotently. |
| 10 | Guest may call the model before the tunnel is up (small race between container start and sshd/tunnel setup). | Fixed: the generated guest script waits for the model endpoint (up to 60 s) before invoking pi. |

## 6. Open questions

See QUESTIONS_FOR_USER.md

---

## 7. Phase 2 — declarative test cases (prototyping)

Date: 2026-11-27. Design outcome of a brainstorm with the owner.

### 7.1 Problem

Phase 1 runs one case = one `run.sh` script. The owner wants many models over
many cases without writing a custom script per case, and wants to evaluate not
just task outcomes but agent *behavior* (instruction following, e.g. "never
run `ls`"), which requires peeking at the agent session transcript.

### 7.2 Design decisions

1. **One check mechanism, not two.** Outcome checks ("tests pass") and
   behavior checks ("never used git") are the same thing: checks run on the
   **host** over **collected artifacts** (agent workspace snapshot + pi session
   logs + files). Checks are re-runnable without re-running the agent.
2. **Cases are data, not scripts.** Case = `case.toml` (TOML, parsed with
   host python3 stdlib `tomllib` — no dependencies) + optional `fixture/` dir.
   Small shell snippets allowed inside the TOML (`setup`, `checks[].run`);
   anything bigger means the case is doing too much.
3. **Artifact capture is generous and fixed**, not per-case configured:
   `results/artifacts/workspace/` (full snapshot of the agent's working dir,
   including `.git` if created), `results/artifacts/sessions/` (pi session
   logs = the transcript).
4. **Escape hatch preserved:** plain `run.sh` cases (Phase 1 style) still work;
   `case.toml` cases are the new default when present.
5. **Scoring output:** `results/checks.json` (per-check pass/fail + output)
   + `results/verdict.txt` (PASS = all mechanical checks pass; manual checks
   are recorded but never score). A check type `manual` marks judgment calls
   (e.g. "is the commit message funny") for human/LLM-judge review later.
6b. **Validation of sandboxes/isolation is empirical, not trace-parsing**
   (owner decision during prototyping): checks observe *behavior* — e.g. a
   program doing a non-whitelisted operation must actually fail. strace is
   still captured as an informational artifact (`manual` check) for review.
6c. **Checks that must execute Linux artifacts** (build/run/strace) set
   `in_guest=True` on the check: a throwaway `container run` of the guest
   image with the artifacts mounted. Checks stay host-orchestrated; nothing
   is installed on the host.
6d. `pcp/pcp_case.py --checks-only` re-runs checks against existing artifacts
   without a VM run — used to iterate on checks and to re-score old runs.
   Note: guest-side `setup` has not run in that mode; artifacts must already
   contain what checks need.
6. **Schema evolved from real cases** (not designed up front): the first four
   cases define v0; the schema grows only when a real case demands it.

### 7.3 Case format `pcp-case/v0` (first cut → Python DSL)

Run parameter: the model is passed as `--model` (owner request — first-class
run parameter, wins over the `PCP_MODEL` env var, which stays for scripting);
results are stored per model (`results/<MODEL>/`, `_nomodel` for agent-less
cases).

Format history: started as TOML (chosen for stdlib `tomllib`), but host
python3 is 3.9 (no `tomllib`), and the interpreter-hunting wrapper was ugly.
Owner decision: **cases are Python** (`case.py`) — a small DSL injected by the
loader instead of a data format. Runs on stock host python3, comments and
multiline strings for free; validation happens after load.

```python
SCHEMA = PCP_CASE_V0
NAME = "short-slug"
DESCRIPTION = "what this case measures"

SETUP = ["""..."""]        # optional guest shell snippets, cwd = workspace,
                           # run BEFORE the agent
PROMPTS = ["""..."""]      # agent prompt(s); empty list = no agent (smoke cases)

CHECKS = [
  # host shell check, cwd = results dir; env: PCP_ARTIFACTS, PCP_CASE_DIR,
  # PCP_INGUEST. exit 0 = pass. manual=True: recorded, never scores.
  pcp.checks.run(name="unique-check-name", cmd="""...""", manual=False),

  # built-in transcript semantics (scan captured session logs):
  pcp.checks.transcript(name="never-ran-ls",
                        mode=pcp.checks.mode.excludes,
                        pattern="^ls ",          # str = literal (icase=True default)…
                        scope=pcp.checks.scope.tool),  # …or re.compile() = regex
                        # scope: tool | assistant | any
]
```

`case.py` is executed by `pcp/pcp_case.py` with `PCP_CASE_V0`, `pcp`, and
`re` injected. `pcp_sandbox.py run`'s `run.sh` legacy path still exists for
standalone use, but all PCP cases are `case.py` now.

### 7.4 Work chunks

- **Chunk 7a — framework skeleton**: `harness/run-case.sh` (parse TOML,
  generate guest script, invoke `run-test.sh`, collect artifacts, run checks,
  write `checks.json` + `verdict.txt`); `run-test.sh` gains `PCP_GUEST_SCRIPT`
  hook. Port `case-000-harness-smoke` to TOML.
  Done when: smoke case passes via `run-case.sh` with no model running.
- **Chunk 7a — framework skeleton — DONE**: `harness/run-case.sh` +
  `pcp_case.py` (parse TOML, generate guest script, run VM via `run-test.sh`
  `PCP_GUEST_SCRIPT` hook, collect artifacts, run checks, write `checks.json`
  + `verdict.txt`), `harness/in-guest.sh`, `--checks-only` / `--dry-run`
  modes. `case-000-harness-smoke` ported to TOML, passes end-to-end. Later
  extended (owner request) to include a trivial LLM round-trip ("King of
  England with six wives") — full smoke: plumbing + tunnel + model + checks;
  Qwen3.8-27B answered "Henry VIII", PASS.
- **Chunk 7b — case-001-git-no-git — checks validated**: repo checks +
  transcript no-`git` scan (defensive JSONL parsing). Live agent run pending
  a model server.
- **Chunk 7c — case-002-fix-median — checks validated**: buggy `median()`
  (even-length lists) + failing stdlib unittest; tests-pass (with
  `pipefail` — the naive `| tail` masked exit codes, caught in testing) and
  tests-unmodified. Validated with fixed AND buggy artifacts.
- **Chunk 7d — case-003-syscall-sandbox (owner-defined) — checks validated**:
  agent writes Rust `pcp_sandbox [-l whitelist] <program> [args]`.
  Empirical checks (owner direction: no trace parsing for scoring):
  builds (in-guest cargo), echo-ok with whitelist, write-blocked without
  `openat` (catches passthrough sandboxes — validated against a stub), plus
  informational strace capture (`manual`).
- **Chunk 7e — matrix runner** (models × cases, summary table): deferred
  until cases 001–003 have real recorded runs.
- **Tool consolidation (owner request)**: the sandbox shell scripts became
  `sandbox/pcp_sandbox.py` (setup | build | run | cleanup). `pcp_case.py`
  now delegates VM runs via `pcp_sandbox.py run --guest-script …`; flag >
  env > default precedence for all knobs; image 1.1 digest unchanged
  (`sha256:7e09a383…`) by keeping the embedded entrypoint byte-identical.
- **First live agent runs (chunk 7b)**:
  - `Qwen3.8-27B-Q6_K` — **PASS** (all mechanical checks): wrote git objects
    by hand with python3 (zlib + sha1), verified its own object graph, no git
    usage; commit message "Why did the developer go broke? He used up all his
    cache." (manual funny-check: looks funny to me — owner confirms).
  - `Qwen3-30B-A3B-Instruct-2507-Q5_K_M` — **FAIL 3×**: run 1 used
    `git hash-object` (caught by transcript check), broken repo; run 2 was a
    host llama.cpp OOM ("Compute error", caveat 13 — not the model's fault);
    run 3 (after server restart, clean comparison) reached for the git CLI
    again (`git hash-object --literally --no-verify` ×3) and again left a
    broken branch. Consistent: ignores the no-git caveat and can't complete
    the object graph by hand.
  Framework lessons fixed along the way:
  - **Results are per model**: `results/<PCP_MODEL>/` (`_nomodel` for
    agent-less cases) — owner decision; also prevents cross-run pollution.
  - **Artifacts are wiped at the start of each run** — `cp -a` into an
    existing dir accumulates, and a stale session from a previous model's run
    made a clean run look like cheating.
  - **no-git check matches command position**, not mentions: `which git` and
    a python variable named `git` are not usage (validated against 12 cases
    incl. real offenders: `git hash-object`, `x=$(git rev-parse HEAD)`,
    `GIT_DIR=. git status`).
- Image bumped **1.0 → 1.1** (deliberate: added `strace` to the guest;
  digest `sha256:7e09a383…`). `PCP_TAG` default is 1.1.

Agent cases need a live model server on host `127.0.0.1:9931` (owner starts
it; harness only consumes the endpoint).
