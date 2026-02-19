# Find our models in the Downloads folder.
MODELS=$(shell cd ~/Downloads; ls *.gguf test_models/*.gguf; ls split_ggufs/*00001-of-*gguf; ls test_models/split_ggufs/*00001-of-*gguf )

# Replace / with ---
VMODELS=mlx-community---gemma-3-12b-it-qat-6bit mlx-community---GLM-4.5V-5bit

MLXLM_MODELS=mlx-community--GLM-4.5-4bit mlx-community--GLM-4.5-Air-4bit

LONG_CTX_MODELS=$(shell cd ~/Downloads/; ls *.gguf test_models/*.gguf split_ggufs/*00001-of-*gguf test_models/split_ggufs/*00001-of-*gguf | grep -iE 'SuperNova-Medius|Meta-Llama-3.1-8B-Instruct|Llama-3.2-3B-Instruct|gemma-3-4b-it|gemma-3-12b-it|gemma-3-27b-it|qwq|Qwen3-8B|jan-nano-128k|DeepSeek-R1-0528|Qwen3-30B-A3B-Instruct|QwenLong|Kimi-Linear')

# For each model
TARGETS=$(foreach model,$(MODELS),__DONE__.$(model))

VTARGETS=$(foreach vmodel,$(VMODELS),__VDONE__/$(vmodel))

MLX_TARGETS=$(foreach model,$(MLXLM_MODELS),$(model).mlx)

all: $(MLX_TARGETS) $(TARGETS) $(VTARGETS)
	python3 eval.py

%.mlx:
	if [[ -d ~/.cache/huggingface/hub/models--`basename $@ .mlx` ]]; then ./ask.py -t 0 -T REQUIRED -c 4096 -v -p empty -n 1 -f '*/*.prompt' -o '{f}.{m}.{n}.out' -m $@; fi

__DONE__.%.gguf: ~/Downloads/%.gguf
	./ask.py -t 0 -T REQUIRED -c 8192 -d 4096 -v -p empty -n 1 -f '*/*.prompt' -o '{f}.{m}.{n}.out' -m $<
	if echo $(LONG_CTX_MODELS) | grep -q `basename $<`; then ./ask.py -t 0 -d 10000 -v -p empty -n 1 -f '*/*.longprompt' -o '{f}.{m}.{n}.out' -m $<; fi

__DONE__.test_models/split_ggufs/%.gguf: ~/Downloads/test_models/split_ggufs/%.gguf
	./ask.py -t 0 -T REQUIRED -c 8192 -d 4096 -v -p empty -n 1 -f '*/*.prompt' -o '{f}.{m}.{n}.out' -m $<

__DONE__.split_ggufs/%.gguf: ~/Downloads/split_ggufs/%.gguf
	./ask.py -t 0 -T REQUIRED -c 8192 -d 4096 -v -p empty -n 1 -f '*/*.prompt' -o '{f}.{m}.{n}.out' -m $<

	# Max 40k context for long models since we're memory starved >:-)
	if echo $(LONG_CTX_MODELS) | grep -q `basename $<`; then ./ask.py -t 0 -d 10000 -v -p empty -n 1 -f '*/*.longprompt' -o '{f}.{m}.{n}.out' -m $<; fi

__DONE__.test_models/%.gguf: ~/Downloads/test_models/%.gguf
	./ask.py -t 0 -T REQUIRED -c 8192 -d 4096 -v -p empty -n 1 -f '*/*.prompt' -o '{f}.{m}.{n}.out' -m $<


__VDONE__/%:
	./vlm_helper "$@"

targets:
	echo $(MLX_TARGETS)
	echo $(TARGETS)
	echo $(VTARGETS)

clean:
	rm -vf *.out *.out.txt
