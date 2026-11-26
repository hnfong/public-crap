# Plan: Isolated, Standardized Linux Test Environment for Coding-Agent Evaluation

Status: draft for review — not yet implemented.
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

### Chunk 1 — Verify host prerequisites (5 min, no changes)
- [ ] Confirm `sw_vers` ≥ 26 and `uname -m` = arm64 (known: 26.7.1 / arm64 ✅).
- [ ] Confirm llama.cpp is available on the host and identify its server binary
      (`llama-server`) and the port it listens on (default 8080).
- [ ] Decide the fixed host endpoint contract: `127.0.0.1:8080`, OpenAI-compatible
      path `/v1`. Record it here once confirmed: `PORT = ____`.
- **Done when**: we know the exact host URL the guest will call.

### Chunk 2 — Install `apple/container` (10 min)
- [ ] Download the signed installer `.pkg` for the latest release from
      https://github.com/apple/container/releases (pin: v1.7.1).
- [ ] Install via the package (installs to `/usr/local`), then:
      - [ ] `container system start`
      - [ ] `container --version`
      - [ ] `container run --rm alpine echo hello`
- **Done when**: `hello` prints. Host now has exactly one new component:
  the `container` service.

### Chunk 3 — Host bridge for llama.cpp (5 min, per-boot)
- [ ] `sudo container system dns create host.container.internal --localhost 203.0.113.113`
- [ ] Start llama-server bound to 127.0.0.1.
- [ ] `container run --rm alpine/curl curl -s http://host.container.internal:8080/v1/models`
      (or equivalent health probe) — expect a response from the host server.
- [ ] Note the caveats in `sandbox/README` (or here): the rule is removed on macOS
      reboot (re-run command); creating the localhost domain disables iCloud
      Private Relay.
- **Done when**: a throwaway container can hit the host's model endpoint by name.

### Chunk 4 — Guest image: `sandbox/Dockerfile` (30 min)
- [ ] Write `sandbox/Dockerfile`:
  - [ ] Base: `FROM debian:trixie-slim`
  - [ ] `ARG` pins: `NODE_VERSION` (exact, e.g. 22.x.y), `RUST_TOOLCHAIN` (e.g. 1.88.0),
        `PI_VERSION` (exact), `JAVA` fixed to openjdk-21.
  - [ ] apt layer: core unix tooling (git, curl, wget, openssh-client, jq, ripgrep,
        unzip, zip, xz-utils, bzip2, file, less, ca-certificates),
        C/C++ (build-essential, clang, lld, cmake, ninja-build),
        python3 + python3-venv + python3-pip, openjdk-21-jdk-headless.
  - [ ] Node: official nodejs.org tarball (linux-arm64) + SHASUMS256 verification,
        extracted to `/usr/local` (no third-party repo).
  - [ ] Rust: official rustup, `--profile minimal --default-toolchain $RUST_TOOLCHAIN`,
        symlinked into `/usr/local/bin`.
  - [ ] Pi: `npm install -g @earendil-works/pi-coding-agent@$PI_VERSION`.
  - [ ] Housekeeping: `DEBIAN_FRONTEND=noninteractive`, `rm -rf /var/lib/apt/lists/*`,
        non-root working dir note (see Open Questions), no apt upgrade drift.
- [ ] Add `sandbox/build.sh`:
  `container build -t agent-sandbox:$TAG sandbox/` + print the resulting image
  digest for recording in test metadata.
- **Done when**: Dockerfile + build.sh exist and are reviewed; versions pinned.

### Chunk 5 — Build and smoke-test the image (15–30 min, mostly waiting)
- [ ] `sandbox/build.sh 1.0` (first build pulls base + toolchains; later builds
      use layer cache).
- [ ] Smoke test, one container per check (all `--rm`):
  - [ ] `node --version && npm --version` → pinned values
  - [ ] `rustc --version && cargo --version` → pinned values
  - [ ] `clang --version && g++ --version && cmake --version`
  - [ ] `python3 --version && python3 -m venv /tmp/v && /tmp/v/bin/python -V`
  - [ ] `java -version` → OpenJDK 21
  - [ ] `pi --version` → pinned value
- **Done when**: all versions match the `ARG` pins exactly.

### Chunk 6 — Test harness scripts (30 min)
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
- **Done when**: scripts pass shellcheck; a dry run prints the exact commands.

### Chunk 7 — First end-to-end test case (30 min)
- [ ] `tests/case-001-hello-world/`:
  - [ ] `run.sh` (executed inside the guest):
    - [ ] assert toolchain versions (cheap regression guard)
    - [ ] configure pi to use the host model: OpenAI-compatible base URL
          `http://host.container.internal:8080/v1` (verify pi's exact provider
          config mechanism — file vs env — during implementation and pin it here)
    - [ ] run one trivial pi coding task (e.g. "create a file with this content"
          or a 5-line function with a test)
    - [ ] write pass/fail + transcript to `/results/`
  - [ ] `fixture/` (empty for now; future cases put their repo here)
- [ ] Run: `sandbox/setup-host.sh && sandbox/run-test.sh tests/case-001-hello-world`
  with a small model already served by llama-server on the host.
- **Done when**: a result (pass or fail — the point is a *recorded, comparable*
  outcome) lands in `tests/case-001-hello-world/results/` with metadata.

### Chunk 8 — Isolation and policy hardening (15 min)
- [ ] Verify offline mode: run case-001 with `NET=internal`; confirm the only
      reachable endpoint is the host bridge (and that internet is unreachable).
      (If the host-bridge domain does not resolve on `--internal` networks — an
      open question from the docs — fall back: offline tests use the default
      network and the model endpoint remains the only *useful* destination.)
- [ ] Verify no state leak: run case-001 twice; diff `results/` metadata; confirm
      the second run's container started from the pristine image (e.g. by having
      run.sh record `find / -newer /marker` style checks or a sentinel file check).
- [ ] Decide root vs non-root agent user in the guest (see Open Questions).

### Chunk 9 — Housekeeping and reproducibility conventions (10 min)
- [ ] Document in `sandbox/README.md`: per-boot setup, how to add a test case,
      how to bump toolchain/pi versions (deliberate `ARG` edits only), cleanup.
- [ ] Convention: every test's `metadata.json` records the image **digest**
      (not just tag) so any historical result is exactly reproducible.
- [ ] Known-caveat list (see §5) lives in the README, not in people's heads.

### Chunk 10 — Follow-ups (not now, listed to shape decisions now)
- [ ] Interactive debug machine: `container machine create agent-sandbox:$TAG
      --name dev` for hand-testing the agent environment (trusted image only).
- [ ] Push the image to a private registry (ghcr) if/when CI needs it.
- [ ] Matrix runs: same case × {model, quant, temperature, pi version} with a
      small runner script over `run-test.sh`.
- [ ] Multiple host ports / second service (e.g. a local search endpoint) — the
      `--localhost` bridge covers this without new machinery.

---

## 4. Repo layout (target)

```
agentic/
├── PLAN.md                     ← this file
├── sandbox/
│   ├── README.md               ← how to use (Chunk 9)
│   ├── Dockerfile              ← standardized guest (Chunk 4)
│   ├── build.sh                ← build + print digest (Chunk 4)
│   ├── setup-host.sh           ← idempotent per-boot host prep (Chunk 6)
│   ├── run-test.sh             ← one test case = one ephemeral VM (Chunk 6)
│   └── cleanup.sh              ← prune (Chunk 6)
└── tests/
    └── case-001-hello-world/
        ├── run.sh              ← executed inside the guest (Chunk 7)
        ├── fixture/            ← optional repo for the agent to work in
        └── results/            ← written by run.sh + harness (gitignored)
```

---

## 5. Known caveats and risks

| # | Caveat | Mitigation |
|---|---|---|
| 1 | `container` is a 1.x product version — evolving fast; CLI stable only within a major. | Pin installer version (v1.7.1); upgrade deliberately. |
| 2 | Host-bridge DNS rule (`--localhost`) is removed on macOS reboot. | `setup-host.sh` re-creates it idempotently; document it. |
| 3 | Creating the localhost domain disables iCloud Private Relay. | Accept (document); it only lasts while the rule exists. |
| 4 | Memory freed inside a container VM is not returned to macOS (partial ballooning). | Ephemeral containers per test (`--rm`) bound the leak; `container system stop/start` between long sessions if needed. |
| 5 | Host bridge reaches the whole host (all 127.0.0.1 services), not just one port. | Keep llama.cpp bound to 127.0.0.1; don't run other local services during tests (or accept them as reachable). |
| 6 | macOS lacks GNU `timeout`. | Small watchdog helper in `run-test.sh`. |
| 7 | `--internal` network + host-bridge DNS interaction unverified. | Chunk 8 verifies; documented fallback exists. |
| 8 | Image build pulls from external registries (debian, nodejs.org, rustup, npm) — network + supply chain at build time. | Build rarely; verify Node tarball SHA-256; pin everything else by version. |

## 6. Open questions

See QUESTIONS_FOR_USER.md
