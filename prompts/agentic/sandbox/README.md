# sandbox/

PCP guest image and VM tooling. See `../JOURNAL.md` for design and decisions.

Everything is driven by **`pcp_sandbox.py`** (stdlib-only, runs on the system
python3) — one tool, four subcommands:

## Per boot

```bash
sandbox/pcp_sandbox.py setup     # idempotent; starts apple/container if needed
```

No sudo, no DNS host-bridge (owner decision). The guest reaches host
**loopback** services (llama.cpp on `127.0.0.1:9931`) through a per-run SSH
reverse tunnel created by `run`.

## Build the guest image

```bash
sandbox/pcp_sandbox.py build --tag 1.1   # prints + records the image digest
```

The guest entrypoint is embedded in the tool and staged into the build
context (keep it byte-stable: same Dockerfile ⇒ same digest).

## Run a test case

Cases are `tests/case-*/case.py` (Python DSL — see JOURNAL.md §7.3), run via
the harness:

```bash
harness/run-case.sh --model Qwen3.8-27B-Q6_K tests/case-001-git-no-git
harness/run-case.sh --checks-only --model Qwen3.8-27B-Q6_K tests/case-001-git-no-git
harness/run-case.sh --dry-run tests/case-001-git-no-git
```

`harness/run-case.sh` delegates the VM run to `pcp_sandbox.py run`. One run =
one ephemeral VM. The case's checks run on the host against collected
artifacts (`results/<MODEL>/artifacts/…`); checks that must execute Linux
binaries go through `harness/in-guest.sh` (throwaway container). Output:
`results/<MODEL>/metadata.json`, `checks.json`, `verdict.txt`.

Legacy phase-1 style (`run.sh` in the case dir) still works:

```bash
sandbox/pcp_sandbox.py run --model <model> tests/case-000-harness-smoke
sandbox/pcp_sandbox.py run --net internal tests/case-000-harness-smoke  # offline
```

## Clean up

```bash
sandbox/pcp_sandbox.py cleanup          # stopped containers
sandbox/pcp_sandbox.py cleanup --images # also remove images except the pinned tag
```

## Run parameter precedence

`--flag` > `PCP_*` env var > default. Knobs: `PCP_TAG (1.1), PCP_MODEL,
PCP_MODEL_PORT (9931), PCP_CPUS (2), PCP_MEMORY (4G), PCP_NET,
PCP_TIMEOUT_SECS (1800), PCP_CONTEXT_WINDOW (262144)`.

## Adding a test case

`tests/case-NNN-short-slug/case.py` (see JOURNAL.md §7.3 for the DSL). The
case dir is mounted read-only at `/work`, `results/<MODEL>/` is writable at
`/results`. `run.py`-style guest code reaches the model at
`http://127.0.0.1:${PCP_MODEL_PORT}/v1` (OpenAI-compatible); the generated
guest script waits for the endpoint before invoking pi.

## Caveats

- `apple/container` v1.7.1; its default kernel is installed non-interactively
  by `setup` if missing.
- The guest IP is on the host-only vmnet network (192.168.64.0/24); the SSH
  tunnel is the only sanctioned path to host services.
- Memory freed inside a guest VM is not returned to macOS; ephemeral runs
  bound the leak.
