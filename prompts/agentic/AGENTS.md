# AGENTS.md

This project is called PCP (no meaning), just an identifier.

Working instructions for coding agents (and humans) in this repository.
**Draft v1 — review and edit.** Derived from the project owner's stated
priorities and working style during planning (2026-11-27).

## What this repo is

A test harness for evaluating **open-weight language models** on coding tasks.
A coding agent (the **Pi** CLI) runs inside a standardized, disposable **Linux
container** and is pointed at a local model server (**llama.cpp**) running on
the **macOS host**. Each test case produces a recorded, comparable result.

The environment is the product as much as the tests: standardization and
isolation of the guest are first-class goals.

## Key facts

- Host: macOS 26+, Apple Silicon (arm64).
- Guest runtime: **`apple/container`** (Apple first-party, per-container VMs).
  No Docker, no Lima, no other container tooling on the host.
- Guest image: pinned OCI image (`agent-sandbox:<tag>`) built from
  `debian:trixie-slim`, built from `sandbox/Dockerfile` in this repo.
- Model serving: llama.cpp on the host, bound to 127.0.0.1. The guest reaches
  it via the host-bridge DNS name `host.container.internal` (see
  `sandbox/setup-host.sh`). **Model weights never enter the guest.**
- Agent under test: Pi, installed and version-pinned in the guest image.

## Priorities (in order)

1. **Minimalism** — host side above all: prefer off-the-shelf components from
   or supported by Apple; no extra daemons, no Docker Desktop, no Homebrew
   dependencies unless unavoidable. Guest image as small as practical.
2. **Simplicity** — few moving parts, few concepts, everything reproducible
   from this repo with a handful of well-understood commands.
3. **Reproducibility / standardization** — same environment, every run.

When a change improves one priority at the cost of another, prefer in the
order above and call out the tradeoff.

## How to work in this repo

### Plan before building
- Non-trivial work gets a written plan first (`PLAN.md` or a section in it),
  broken into **bite-sized, independently verifiable chunks** with explicit
  "done when" criteria.
- Do not start implementing a chunk until its prerequisites are done.

### Ask, don't assume
- Open questions, decisions needing owner input, and anything ambiguous go to
  **`QUESTIONS_FOR_USER.md`** — each with context and a proposed default, so
  the owner can answer by confirming or overriding.
- Never invent answers to blocking questions; implement against the stated
  default only if the owner has confirmed it.

### Pin everything that can drift
- Fast-moving runtimes (Node, Rust, pi, apple/container) are pinned by exact
  version in the Dockerfile `ARG`s / scripts. Bumping a pin is a deliberate,
  reviewable change — never an implicit side effect of a rebuild.
- apt is for stable toolchains (clang, JDK, Python, unix tools); pinned
  upstream installers are for fast-moving runtimes.
- Test results record the image **digest**, not just the tag.
- Verify downloaded artifacts where possible (e.g. Node tarball SHA-256).

### Protect the invariants
- **No state leakage between test runs.** Every test runs in a fresh ephemeral
  container (`--rm`); anything persistent must be explicit and documented.
- **No new host components** without owner sign-off (host minimalism).
- **No model weights or host filesystem beyond explicit test fixtures** in the
  guest. Test fixtures are mounted read-only; only `results/` is writable.
- Keep the host's llama.cpp bound to 127.0.0.1.

## Conventions

- Layout (target):
  ```
  agentic/
  ├── PLAN.md              ← living plan: decisions, chunks, status
  ├── QUESTIONS_FOR_USER.md
  ├── sandbox/             ← Dockerfile, build.sh, setup-host.sh, run-test.sh,
  │                          cleanup.sh, README.md
  └── tests/case-NNN-name/ ← run.sh (executed in guest), fixture/, results/
  ```
- Test case naming: `case-NNN-short-slug` (zero-padded number, kebab-case).
- `results/` directories are gitignored; `metadata.json` (case, image digest,
  host OS, model, wall time, exit code) is written by the harness.
- Shell scripts: `set -euo pipefail`, pass shellcheck, idempotent where they
  touch host state (especially `setup-host.sh` — it must survive being run
  twice, and re-run after every macOS reboot).
- Decisions and their rationale land in `PLAN.md` §2.3; caveats/risks in §5.

## Commands (once implemented)

```bash
sandbox/setup-host.sh                     # per-boot: start container system + host bridge
sandbox/build.sh <tag>                    # build agent-sandbox:<tag>, print digest
sandbox/run-test.sh tests/case-NNN-...    # one test case = one ephemeral VM
sandbox/cleanup.sh                        # prune containers/images (keep pinned image)
```

## Do not

- Do not add Docker, OrbStack, Colima, Lima, or any other runtime to the host.
- Do not run the agent as a host process "for convenience" — that invalidates
  the environment.
- Do not let test cases share containers, networks, or writable mounts.
- Do not silently change version pins, resource defaults, or the network
  policy; change them in the plan and the Dockerfile together.
- Do not fetch or install anything in the guest at test time unless the test
  case explicitly needs internet (see `NET=` policy in `run-test.sh`).
