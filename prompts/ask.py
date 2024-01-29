#!/usr/bin/env python3

# Ask an AI a question

# Use llama.cpp

import getopt
import glob
import os
import random
import re
import subprocess
import sys
import time
import tempfile

LLAMA_CPP_PATH = os.path.expanduser("~/projects/llama.gguf/patched_main")
MODELS_PATH = os.path.expanduser("~/Downloads/")

# DEFAULT_MODEL = "dolphin-2_6-phi-2"
DEFAULT_MODEL = "phi-2-orange"
# DEFAULT_CODE_GENERATION_MODEL = "stable-code-3b" # Sucks
DEFAULT_CODE_GENERATION_MODEL = "codellama-34b-instruct"

# Patch used to avoid outputting the prompt
"""
diff --git a/examples/main/main.cpp b/examples/main/main.cpp
index 5668b011..0acacd2e 100644
--- a/examples/main/main.cpp
+++ b/examples/main/main.cpp
@@ -733,13 +733,15 @@ int main(int argc, char ** argv) {
         if (input_echo && display) {
             for (auto id : embd) {
                 const std::string token_str = llama_token_to_piece(ctx, id);
-                printf("%s", token_str.c_str());
+                // printf("%s", token_str.c_str());

                 if (embd.size() > 1) {
                     input_tokens.push_back(id);
                 } else {
                     output_tokens.push_back(id);
                     output_ss << token_str;
+                    printf("%s", token_str.c_str());
+
                 }
             }
             fflush(stdout);
"""

# Presets

class Preset:
    def __init__(self, user_prompt):
        self.user_prompt = user_prompt

    def prompt(self):
        raise NotImplementedError("Please implement this method in a subclass")

    def system_message(self):
        return "You are a helpful assistant. You will answer questions in a helpful and concise manner."

    def templated_prompt(self):
        # Implemented by mixins if needed
        return self.prompt()

class ExplainPreset(Preset):
    def __init__(self, user_prompt, context):
        super().__init__(user_prompt)
        self.context = context

    name = "explain_this"

    def prompt(self):
        if self.context:
            return f"In the context of " + self.context + ", please explain the following. Be concise in your answer.\n```{self.user_prompt}```\n"
        else:
            return f"Please explain the following. Be concise in your answer.\n```{self.user_prompt}```\n"

class CodeReviewPreset(Preset):
    def __init__(self, user_prompt, context):
        super().__init__(user_prompt)
    name = "code_review"

    def prompt(self):
        return f"Please assume this is a code snippet in a github pull request. Please review the following code. Focus on potential problems. Because it is a snippet, do not be concerned with undefined or unknown references as long as they seem to be reasonable. Be concise in your answer.\n```{self.user_prompt}```\n"

class CodeGenerationPreset(Preset):
    name = "code_generation"
    def __init__(self, file_name, offset):
        super().__init__("")
        self.file_name = file_name
        self.offset = offset

        # assert file size is less than 10kb
        assert os.path.getsize(self.file_name) < 10000
        self.content_bytes = open(self.file_name, "rb").read()

        while self.content_bytes[self.offset] != ord(b"\n"):
            print(repr(self.content_bytes[self.offset]))
            self.offset += 1

    def prefix(self):
        return self.content_bytes[:self.offset].decode("utf-8")

    def suffix(self):
        return self.content_bytes[self.offset:].decode("utf-8")

class ChatMLTemplateMixin:
    def templated_prompt(self):
        return f"""
<|im_start|>system
{self.system_message()}<|im_end|>
<|im_start|>user
{self.prompt()}<|im_end|>
<|im_start|>assistant
        """.strip() + "\n"

class InstructionTemplateMixin:
    def templated_prompt(self):
        return f"""

### Instruction:

{self.prompt()}

### Response:

"""

class StableCodeCompletionTemplateMixin:
    def templated_prompt(self):
        return f"""<fim_prefix>{self.prefix()}<fim_suffix>{self.suffix()}<fim_middle>"""

class CodeLlamaCompletionTemplateMixin:
    def templated_prompt(self):
        return f"""▁<PRE> {self.prefix()}▁<SUF> {self.suffix()}▁<MID>"""

class LlamaTemplateMixin:
    def templated_prompt(self):
        return f"""<s>[INST] <<SYS>>\n{self.system_message()}\n<</SYS>>\n\n{self.prompt()} [/INST]"""

if __name__ == "__main__":
    PRESETS = {}
    # loop through all classes in this file and add them to the presets
    import inspect
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            if issubclass(obj, Preset) and obj != Preset:
                PRESETS[obj.name] = obj
    opt_list, args = getopt.getopt(sys.argv[1:], "hc:t:f:p:m:g")
    opts = dict(opt_list)

    preset = PRESETS.get(opts.get("-p") or "explain_this")
    assert preset is not None




    template = opts.get("-t") or "chatml"
    context = opts.get("-c") or ""
    model_name = opts.get("-m") or DEFAULT_MODEL
    if preset is CodeGenerationPreset:
        model_name = DEFAULT_CODE_GENERATION_MODEL
    cmd_args = []
    is_mac = "Darwin" in subprocess.run(["uname"], capture_output=True).stdout.decode("utf-8").strip()
    if opts.get("-g") or is_mac:
        cmd_args.append("-ngl")
        cmd_args.append("99")

    templateMixIn = None
    if template == "chatml":
        templateMixIn = ChatMLTemplateMixin
    elif template == "llama":
        templateMixIn = LlamaTemplateMixin
    else:
        templateMixIn = InstructionTemplateMixin

    # Note: need to add the prompt after
    cmd = [LLAMA_CPP_PATH,] + cmd_args + ["-m", glob.glob(f"{MODELS_PATH}/*{model_name}*.gguf")[0]]
    if preset is not CodeGenerationPreset:
        class CurrentPrompt(templateMixIn, preset):
            pass

        user_prompt = None
        if args:
            user_prompt = " ".join(args)  # join all args into one string for easy use
        elif opts.get("-f"):
            user_prompt = open(opts.get("-f")).read()
        else:
            print("What is your question?")
            user_prompt = sys.stdin.read()

        prompt = CurrentPrompt(user_prompt, context).templated_prompt()
        cmd += ["-p", prompt, "-c", "1024"]
    else: # is CodeGenerationPreset
        assert opts.get("-f") is not None
        # Force template to be code completion
        class CodeGenerationPrompt(CodeLlamaCompletionTemplateMixin, preset):
            pass

        prompt = CodeGenerationPrompt(opts.get("-f"), int(args[0] or 0)).templated_prompt()

        # Create a temporary file for storing the prompt
        temp_prompt_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        temp_prompt_file.write(prompt)
        temp_prompt_file.close()
        print(temp_prompt_file.name)
        cmd += ["-f", temp_prompt_file.name, "-c", "4096"]
        print(cmd)

    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    while dat := p.stdout.read(1):
        sys.stdout.buffer.write(dat)
        sys.stdout.flush()

    outs = p.communicate()

    # Check exit code
    if p.returncode != 0:
        print("Error: " + outs[1].decode("utf-8"))
        sys.exit(1)
    else:
        outs_s = outs[0].decode("utf-8")
        if outs_s.startswith(prompt):
            outs_s = outs_s[len(prompt):]
            # This doesn't work at least in some models because <|im_end|>
            # seems to be tokenized and stringified back to an empty string.
            # Instead I just modified the llama.cpp code to just output the
            # results.

        print(outs_s)
