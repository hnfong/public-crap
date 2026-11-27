#!/bin/sh

set -eu

# run from the repo dir regardless of where the script is invoked from
cd "$(dirname "$0")" || exit 1

if [ $# -lt 1 ]; then
    echo "usage: test_model.sh <path/to/model.gguf>" >&2
    exit 1
fi

LLAMA_SERVER=`which llama-server || echo "$HOME/projects/llama.gguf/llama-server"`
if [ ! -x "$LLAMA_SERVER" ]; then
    echo "Cannot find llama.cpp server binary." >&2
    exit 1
fi

MODEL=$1
shift

MODELS_DIR=`dirname "$MODEL"`
MODEL_NAME=`basename "$MODEL" ".gguf"`

# per-boot container-system preparation (idempotent)
python3 pcp/pcp_sandbox.py setup

# server log: the diagnostic for llama.cpp "Compute error"/OOM failures
mkdir -p results
SERVER_LOG=results/llama-server.log

set -x
killall -9 llama-server || true
nohup "$LLAMA_SERVER" -np 1 --models-dir "$MODELS_DIR" -c 0 --cache-ram 10000 \
    > "$SERVER_LOG" 2>&1 &

# always clean up the server on exit (including Ctrl-C / mid-sweep failure)
trap 'killall -9 llama-server || true' EXIT

# warmup: router mode loads the GGUF on first request, which can take minutes
# for a large model — do it here so it does not eat into the first case's
# case-defined TIMEOUT. Retry until the model answers.
i=0
until curl -s -m 300 http://127.0.0.1:9931/v1/chat/completions \
        -H 'Content-Type: application/json' \
        -d "{\"model\": \"$MODEL_NAME\", \"messages\": [{\"role\": \"user\", \"content\": \"hi\"}], \"max_tokens\": 1}" \
        | grep -q '"content"'; do
    i=$((i + 1))
    if [ "$i" -gt 120 ]; then
        echo "Model failed to load after 10 minutes; see $SERVER_LOG" >&2
        exit 1
    fi
    sleep 5
done
echo "model $MODEL_NAME loaded"

FAILED=""
for test_case in tests/*.py; do
    EXPECTED_OUTFILE="results/`basename $test_case .py`.$MODEL_NAME.out"
    if [ -f "$EXPECTED_OUTFILE" ]; then
        echo "$EXPECTED_OUTFILE exists, skipping"
        continue
    fi
    # continue on failure: one bad case must not abort the sweep
    if python3 pcp/pcp_case.py --model "$MODEL_NAME" "$test_case"; then
        :
    else
        FAILED="$FAILED $test_case"
    fi
done

killall -9 llama-server || true

if [ -n "$FAILED" ]; then
    echo "cases that did not fully pass:$FAILED" >&2
    exit 1
fi
