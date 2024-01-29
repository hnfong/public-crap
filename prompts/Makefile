# Find our models in the Downloads folder.
MODELS=$(shell cd ~/Downloads/; ls *.gguf | grep -E 'chat|instruct|dolphin')

# For each model
TARGETS=$(foreach model,$(MODELS),__DONE__.$(model))

all: $(TARGETS)
	echo $(TARGETS)

__DONE__.%.gguf: ~/Downloads/%.gguf
	./infer -m $< -t $@
