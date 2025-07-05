# Find our models in the Downloads folder.
MODELS=$(shell cd ~/Downloads; ls *.gguf test_models/*.gguf; echo test_models/split_ggufs/*00001-of-*gguf )

# Replace / with ---
VMODELS=mlx-community---Qwen2.5-VL-7B-Instruct-4bit mlx-community---InternVL3-8B-6bit mlx-community---Qwen2.5-VL-32B-Instruct-4bit mlx-community---gemma-3-12b-it-qat-6bit

LONG_CTX_MODELS=$(shell cd ~/Downloads/; ls *.gguf test_models/*.gguf | grep -iE 'SuperNova-Medius|Meta-Llama-3.1-8B-Instruct|Llama-3.2-3B-Instruct|gemma-3-4b-it|gemma-3-12b-it|gemma-3-27b-it|qwq|Qwen3-8B|jan-nano-128k')

# For each model
TARGETS=$(foreach model,$(MODELS),__DONE__.$(model))

VTARGETS=$(foreach vmodel,$(VMODELS),__VDONE__/$(vmodel))

all: $(TARGETS) $(VTARGETS)
	python3 eval.py

__DONE__.%.gguf: ~/Downloads/%.gguf
	./ask.py -t 0 -T REQUIRED -c 2048 -M qwq,-c,8192 -M Qwen3,-c,8192 -v -p empty -n 1 -f '*/*.prompt' -o '{f}.{m}.{n}.out' -m $(shell basename $< .gguf)
	if echo $(LONG_CTX_MODELS) | grep -q `basename $<`; then ./ask.py -t 0 -M \*,-c,10000 -v -p empty -n 1 -f '*/*.c10000.longprompt' -o '{f}.{m}.{n}.out' -m $(shell basename $< .gguf); fi
	if echo $(LONG_CTX_MODELS) | grep -q `basename $<`; then ./ask.py -t 0 -M \*,-c,20000 -v -p empty -n 1 -f '*/*.c20000.longprompt' -o '{f}.{m}.{n}.out' -m $(shell basename $< .gguf); fi
	if echo $(LONG_CTX_MODELS) | grep -q `basename $<`; then ./ask.py -t 0 -M \*,-c,40000 -v -p empty -n 1 -f '*/*.c40000.longprompt' -o '{f}.{m}.{n}.out' -m $(shell basename $< .gguf); fi

__DONE__.test_models/split_ggufs/%.gguf: ~/Downloads/test_models/split_ggufs/%.gguf
	./ask.py -t 0 -T REQUIRED -c 2048 -M qwq,-c,8192 -v -p empty -n 1 -f '*/*.prompt' -o '{f}.{m}.{n}.out' -m test_models/split_ggufs/$(shell basename $< .gguf)

__DONE__.test_models/%.gguf: ~/Downloads/test_models/%.gguf
	./ask.py -t 0 -T REQUIRED -c 2048 -M qwq,-c,8192 -v -p empty -n 1 -f '*/*.prompt' -o '{f}.{m}.{n}.out' -m test_models/$(shell basename $< .gguf)


__VDONE__/%:
	./vlm_helper "$@"

targets:
	echo $(TARGETS)
	echo $(VTARGETS)

clean:
	rm -vf *.out *.out.txt
