# sandbox/

PCP guest image and test harness. See `../PLAN.md` for design and decisions.

## Per boot

```bash
sandbox/setup-host.sh     # idempotent; starts apple/container if not running
```

No sudo, no DNS host-bridge (owner decision). The guest reaches host
**loopback** services (llama.cpp on `127.0.0.1:9931`) through a per-run SSH
reverse tunnel created by `run-test.sh`.

## Build the guest image

```bash
sandbox/build.sh 1.0      # prints + records the image digest
```

## Run a test case

Preferred (declarative cases, `case.toml` — see JOURNAL.md §7):

```bash
harness/run-case.sh --model Qwen3.8-27B-Q6_K tests/case-001-git-no-git
harness/run-case.sh --checks-only --model Qwen3.8-27B-Q6_K tests/case-001-git-no-git  # re-score
harness/run-case.sh --dry-run tests/case-001-git-no-git
```

`--model` overrides the `PCP_MODEL` env var; results are stored per model
(`results/<MODEL>/`).

One run = one ephemeral VM. The case's checks run on the host against
collected artifacts (`results/artifacts/workspace`, `results/artifacts/sessions`);
checks that must execute Linux binaries go through `harness/in-guest.sh`
(throwaway container). Output: `results/checks.json`, `results/verdict.txt`.

Legacy phase-1 style (`run.sh` in the case dir) still works:

```bash
PCP_MODEL=Qwen3.8-27B sandbox/run-test.sh tests/case-000-harness-smoke
PCP_NET=internal sandbox/run-test.sh tests/case-000-harness-smoke   # offline
sandbox/run-test.sh --dry-run tests/case-000-harness-smoke
```

One run = one ephemeral VM (`container run --rm`). Run parameters:
`(PCP_MODEL, TEST_CASE)`. Overrides: `--model` flag (or `PCP_MODEL`), `PCP_TAG (1.1),
PCP_MODEL_PORT, PCP_CPUS (2), PCP_MEMORY (4G), PCP_NET,
PCP_TIMEOUT_SECS (1800), PCP_CONTEXT_WINDOW`. Results land in
`tests/<case>/results/<MODEL>/` (`metadata.json` records the image digest).

## Clean up

```bash
sandbox/cleanup.sh          # stopped containers
sandbox/cleanup.sh --images # also remove images except agent-sandbox:$PCP_TAG
```

## Adding a test case

`tests/case-NNN-short-slug/` with `run.sh` (executed **inside the guest** as
the non-root `agent` user; the case dir is mounted read-only at `/work`,
`results/` is writable at `/results`). `run.sh` reaches the model at
`http://127.0.0.1:${PCP_MODEL_PORT}/v1` (OpenAI-compatible). Poll the
endpoint briefly if the tunnel may not be up yet.

## Caveats

- `apple/container` v1.7.1; its default kernel is installed non-interactively
  by `setup-host.sh` if missing.
- The guest IP is on the host-only vmnet network (192.168.64.0/24); the SSH
  tunnel is the only sanctioned path to host services.
- Memory freed inside a guest VM is not returned to macOS; ephemeral runs
  bound the leak.
