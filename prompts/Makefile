# Find our models in the Downloads folder.
MODELS=$(shell cd ~/Downloads/; ls *.gguf | grep -E 'chat|dolphin|orange|mixtral')

# For each model
TARGETS=$(foreach model,$(MODELS),__DONE__.$(model))

all: $(TARGETS)
	echo $(TARGETS)

__DONE__.%.gguf: ~/Downloads/%.gguf
	./ask.py -p empty -n 4 -f '*.prompt' -o '{f}.{m}.{n}.out' -m $(shell basename $< .gguf)

clean:
	rm -vf *.out *.out.txt
