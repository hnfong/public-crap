# Questions for the user

Context: planning the isolated Linux test environment for coding-agent evaluation
(see `PLAN.md`). These block (or shape) the implementation. Each has a proposed
default — just confirm or override.

---

## Q1. llama.cpp endpoint details (blocks Chunk 1 & 3)

What exactly is running the model on the host?

1. Which binary/server: `llama-server` (llama.cpp's built-in HTTP server)?
2. Which port? (default is `8080`)
3. Does it expose the **OpenAI-compatible API** (`/v1/chat/completions`,
   `/v1/models`)? We plan to point pi at `<endpoint>/v1`. If it's a different
   API surface (raw `/completion`, custom), the guest-side config changes.
4. Is the model path / name fixed for now, or do you expect to swap models
   frequently? (Affects how we parameterize the harness.)

> Proposed default: `llama-server` on `127.0.0.1:8080`, OpenAI-compatible `/v1`,
> model name passed to the harness as an env var per run.

User answer:

- either on $PATH, or ~/projects/llama.gguf/llama-{server|cli|completions} etc. (this thing should run on multiple hosts, there are some diff setups)
- port is 9931 (llama.cpp server default [as of writing at least])
- I suppose so.
- models will be frequently swapped. it should be a parameter for a "run" (eg. run parameters would be at least (MODEL, TEST_CASE))


## Q2. How should pi be pointed at the host model? (blocks Chunk 7)

pi supports custom model providers (config file vs. environment variables).
Do you have a preferred/existing way you configure pi's providers, or should I
check pi's docs and pick the cleanest mechanism during implementation?

Related: should the **model name/params** (temperature etc.) be part of each
test case's `run.sh`, or global harness env vars?

> Proposed default: I'll verify pi's provider config mechanism during
> implementation and record it in `PLAN.md`; model name + endpoint as harness
> env vars, per-case overrides allowed in `run.sh`.

User answer: You can take a "copy" of the current Pi harness' config in hosts' ~/.pi (don't
modify the host's config though)

## Q3. Agent user inside the guest (shapes Chunks 4 & 8)

Should the agent run as **root** or as a **dedicated non-root user** in the
container?

- root: simplest, matches many CI defaults; agent has full control.
- non-root: more realistic of a normal dev box; may surface permission issues
  that root would hide (arguably a feature for agent testing).

> Proposed default: **root** to start; revisit in Chunk 8 if behavior looks
> root-sensitive.

User answer: Dedicated non-root. There may be complications if we run root as some apps/envs
will behave differently.

## Q4. Default per-test resource limits (blocks Chunk 6)

Proposed defaults: **4 CPUs / 8 GB RAM** per test container.

How much headroom does the host have while llama.cpp is holding the model in
RAM? (M-series unified memory is shared, so an 8 GB VM + a large model can
squeeze things.)

> Proposed default: `CPUS=4`, `MEMORY=8G`, overridable per run via env vars.

User answer: I'd say CPU=2, MEMORY=4G.
There should be much more room but this is basically how much I'd rather give to the linux env.
Also, let's call this project PCP, so any override vars should have this prefix.

## Q5. Internet access policy (shapes Chunk 6 default)

Should tests run **with internet by default** (agent may `pip install` /
`npm install` during a task) or **offline by default** (only the host model
endpoint reachable), with internet as the opt-in?

> Proposed default: internet by default (matches realistic agent usage);
> `NET=internal` for the offline variant.

User answer: Internet by default. Should be tune-able per test.

## Q6. Version pins — confirm the starting pins (blocks Chunk 4)

Proposed initial pins for the guest image:

| Component | Proposed pin |
|---|---|
| Base | `debian:trixie-slim` |
| Node.js | latest 22.x LTS (exact version filled in at build time) |
| Rust | 1.88.0 (or current stable — your call) |
| Java | OpenJDK 21 (headless) |
| Python | distro 3.13 |
| pi | latest release, pinned at image-build time |
| apple/container | 1.7.1 |

Any of these should be different (e.g. Node 24, a specific pi version you're
standardizing on)?

User answer: Pin of debian version is probably enough for now.

## Q7. Scope check — anything I got wrong?

Quick sanity check on my reading of the setup (PLAN.md §1):

- The **agent (pi) runs inside the guest**; the model never does.

User answer: Correct

- Tests are **CLI-based coding tasks** (no browser/GUI).

User answer: Generally correct.

- "Specific ports" = just the llama.cpp server for now.

User answer: Correct

- You want results collected per case in the repo (`results/`), gitignored.

User answer: Not entirely. I think each test would have to have some way to interpret the results. The final results would be saved also, but of course we'd have to figure out what to capture from the VM.

Flag anything that doesn't match your intent.
