# Find our models in the Downloads folder.
MODELS=$(shell cd ~/Downloads; ls *.gguf test_models/*.gguf; echo test_models/split_ggufs/*00001-of-*gguf )

LONG_CTX_MODELS=$(shell cd ~/Downloads/; ls *.gguf test_models/*.gguf | grep -iE 'SuperNova-Medius|Meta-Llama-3.1-8B-Instruct|Llama-3.2-3B-Instruct|gemma-3-4b-it|gemma-3-12b-it|gemma-3-27b-it|qwq')

# For each model
TARGETS=$(foreach model,$(MODELS),__DONE__.$(model))

all: $(TARGETS)

__DONE__.%.gguf: ~/Downloads/%.gguf
	./ask.py -c 2048 -M qwq,-c,8192 -v -p empty -n 1 -f '*/*.prompt' -o '{f}.{m}.{n}.out' -m $(shell basename $< .gguf)
	if echo $(LONG_CTX_MODELS) | grep -q `basename $<`; then ./ask.py -c 10000 -v -p empty -n 1 -f '*/*.c10000.longprompt' -o '{f}.{m}.{n}.out' -m $(shell basename $< .gguf); fi
	if echo $(LONG_CTX_MODELS) | grep -q `basename $<`; then ./ask.py -c 20000 -v -p empty -n 1 -f '*/*.c20000.longprompt' -o '{f}.{m}.{n}.out' -m $(shell basename $< .gguf); fi
	if echo $(LONG_CTX_MODELS) | grep -q `basename $<`; then ./ask.py -c 40000 -v -p empty -n 1 -f '*/*.c40000.longprompt' -o '{f}.{m}.{n}.out' -m $(shell basename $< .gguf); fi


__DONE__.split_ggufs/%.gguf: ~/Downloads/split_ggufs/%.gguf
	./ask.py -c 2048 -M qwq,-c,8192 -v -p empty -n 1 -f '*/*.prompt' -o '{f}.{m}.{n}.out' -m split_ggufs/$(shell basename $< .gguf)

targets:
	echo $(TARGETS)

clean:
	rm -vf *.out *.out.txt
