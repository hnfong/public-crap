#!/bin/sh

set -e

LLAMA_SERVER=`which llama-server || echo $HOME/projects/llama.gguf/llama-server`
if [ ! -x "$LLAMA_SERVER" ]; then
    echo "Cannot find llama.cpp server binary." >&2
    exit 1
fi

MODEL=$1
shift

MODELS_DIR=`dirname "$MODEL"`
MODEL_NAME=`basename "$MODEL" ".gguf"`

set -x
killall -9 llama-server || true
nohup "$LLAMA_SERVER" -np 1 --models-dir "$MODELS_DIR" -c 0 --cache-ram 10000 &

for test_case in tests/*.py; do
    EXPECTED_OUTFILE="results/`basename $test_case .py`.$MODEL_NAME.out"
    if [ -f "$EXPECTED_OUTFILE" ]; then
        echo "$EXPECTED_OUTFILE exists, skipping"
        continue
    fi
    python3 pcp/pcp_case.py --model "$MODEL_NAME" "$test_case"
done

killall -9 llama-server || true
