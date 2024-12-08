# Find our models in the Downloads folder.
MODELS=$(shell cd ~/Downloads/; ls *.gguf | grep -iE 'WizardLm|chat|dolphin|orange|mixtral|miqu|yi-34b-chat|llama-2-7b|Meta-Llama-3|Llama-3.2-|Llama-3.3-|starling|Qwen1.5|qwen1_5|Qwen2.5|Phi-3|minicpm|qwen2-0_5b|tinyllama_v1.1|gemma-2|glm-4-|mistral-nemo|Mistral-Large-.*00001|Nemotron|granite|SmolLM|codegeex4|SuperNova-Medius' | grep -v Phi-3; echo split_ggufs/*00001-of-*gguf )

# For each model
TARGETS=$(foreach model,$(MODELS),__DONE__.$(model))

all: $(TARGETS)

__DONE__.%.gguf: ~/Downloads/%.gguf
	./ask.py -c 2048 -v -p empty -n 1 -f '*/*.prompt' -o '{f}.{m}.{n}.out' -m $(shell basename $< .gguf)
__DONE__.split_ggufs/%.gguf: ~/Downloads/split_ggufs/%.gguf
	./ask.py -c 2048 -v -p empty -n 1 -f '*/*.prompt' -o '{f}.{m}.{n}.out' -m split_ggufs/$(shell basename $< .gguf)

targets:
	echo $(TARGETS)

clean:
	rm -vf *.out *.out.txt
