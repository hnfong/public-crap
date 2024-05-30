#!/usr/bin/env python3

"""
This is a script to interact with llama.cpp models. It is a wrapper around the
llama.cpp binary that allows you to easily infer prompts and get responses. It
also allows you to use presets to make it easier to use.
"""

import getopt
import glob
import os
import subprocess
import sys
import tempfile

LLAMA_CPP_PATH = os.environ.get("LLAMA_CPP_PATH") or os.path.expanduser("~/projects/llama.gguf/main")
MODELS_PATH = os.environ.get("MODELS_PATH") or os.path.expanduser("~/Downloads/")

# DEFAULT_MODEL = "dolphin-2_6-phi-2"
DEFAULT_MODEL = "Meta-Llama-3-8B"
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
        self._system_message = ""

    def prompt(self):
        raise NotImplementedError("Please implement this method in a subclass")

    def system_message(self):
        assert self._system_message is not None
        return self._system_message

    def set_system_message(self, message):
        assert message is not None
        self._system_message = message


    def templated_prompt(self):
        # Implemented by mixins if needed
        return self.prompt()

class EmptyPreset(Preset):
    def __init__(self, user_prompt, context):
        super().__init__(user_prompt)
        self.context = context
    def prompt(self):
        return self.user_prompt
    name = "empty"

class DefaultPreset(Preset):
    def __init__(self, user_prompt, context):
        super().__init__(user_prompt)
        self.context = context
        self._system_message = "You are a helpful, thoughtful and creative AI assistant. Give concise answers unless the answer would be better with more detail."

    name = "default"
    def prompt(self):
        return self.user_prompt

class ExplainPreset(Preset):
    def __init__(self, user_prompt, context):
        super().__init__(user_prompt)
        self.context = context
        self._system_message = "You are a helpful, thoughtful and creative AI assistant. Give concise answers unless the answer would be better with more detail."

    name = "explain_this"

    def prompt(self):
        if self.context:
            return f"In the context of {self.context}, please explain the following. Be concise in your answer.\n```{self.user_prompt}```\n"
        else:
            return f"Please explain the following.\n```{self.user_prompt}```\n"

class SummarizePreset(Preset):
    def __init__(self, user_prompt, context):
        super().__init__(user_prompt)
        self.context = context
        self._system_message = "You are a helpful, thoughtful and creative AI assistant."

    name = "summarize"

    def prompt(self):
        return f"""
Please summarize the following text. Be concise (i.e. avoid superfluous writing), but make sure you mention all important and interesting points.

```
{self.user_prompt}
```

Please summarize the above text. Be concise (i.e. avoid superfluous writing), but make sure you mention all important and interesting points.
"""


class ReviewPreset(Preset):
    def __init__(self, user_prompt, context):
        super().__init__(user_prompt)
        self.context = context
        self._system_message = "You are a helpful, thoughtful and creative AI assistant. Give concise answers unless the answer would be better with more detail."

    name = "review"

    def prompt(self):
        return f"Please review the following text. Point out (a) mistakes (if any), (b) suggestions for improvements, and (c) other comments that may be relevant. Be thoughtful and creative. Don't just make trivial comments on low hanging fruit. Be engaging. \n```{self.user_prompt}```\n"

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
        if self.system_message():
            return f"""
<|im_start|>system
{self.system_message()}<|im_end|>
<|im_start|>user
{self.prompt()}<|im_end|>
<|im_start|>assistant
            """.strip() + "\n"
        else:
            return f"""
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

class CodeLlama70bTemplateMixin:
    def templated_prompt(self):
        return f""" <step> Source: system

  {self.system_message()} <step> Source: user

  {self.prompt()} <step> Source: assistant""" + "\n\n"

class LlamaTemplateMixin:
    def templated_prompt(self):
        return f"""<s>[INST] <<SYS>>\n{self.system_message()}\n<</SYS>>\n\n{self.prompt()} [/INST]"""

class Phi3TemplateMixin:
    def templated_prompt(self):
        return f"""<|user|>\n{self.prompt()}<|end|>\n<|assistant|>\n"""


class ZephyrTemplateMixin:
    def templated_prompt(self):
        return f"""<|user|>\n{self.prompt()}</s>\n<|assistant|>\n"""

class MiniCPMTemplateMixin:
    def templated_prompt(self):
        return f"""<用户>{self.prompt()}\n<AI>"""

class DeepSeekV2LiteMixin:
    def templated_prompt(self):
        #   "chat_template": "{% if not add_generation_prompt is defined %}{% set add_generation_prompt = false %}{% endif %}{{ bos_token }}{% for message in messages %}{% if message['role'] == 'user' %}{{ 'User: ' + message['content'] + '\n\n' }}{% elif message['role'] == 'assistant' %}{{ 'Assistant: ' + message['content'] + eos_token }}{% elif message['role'] == 'system' %}{{ message['content'] + '\n\n' }}{% endif %}{% endfor %}{% if add_generation_prompt %}{{ 'Assistant:' }}{% endif %}"
        if self.system_message():
            return f"""{self.system_message()}\n\nUser: {self.prompt()}\n\nAssistant: """
        else:
            return f"""User: {self.prompt()}\n\nAssistant: """

class Llama3TemplateMixin:
    def templated_prompt(self):
        return f"""
<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{self.system_message()}<|eot_id|><|start_header_id|>user<|end_header_id|>
{self.prompt()}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
""".strip() + "\n"

class WizardLmMixin:
    def templated_prompt(self):
        return f"""
USER: {self.prompt()}
ASSISTANT:
""".strip() + " "

class CommandRPlusTemplateMixin:
    # <BOS_TOKEN><|START_OF_TURN_TOKEN|><|SYSTEM_TOKEN|>{system_prompt}<|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|USER_TOKEN|>{prompt}<|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|><|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|>

    def templated_prompt(self):
        return f"""<|START_OF_TURN_TOKEN|><|SYSTEM_TOKEN|>{self.system_message()}<|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|USER_TOKEN|>{self.prompt()}<|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|><|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|>"""


NAME_MATCH_OVERRIDE = [
    ("command-r-plus", CommandRPlusTemplateMixin),
    ("codellama-70b-instruct", CodeLlama70bTemplateMixin),
    ("wizardlm", WizardLmMixin),
    ("phi-3-", Phi3TemplateMixin),
    ("zephyr", ZephyrTemplateMixin),
    ("llama-2", LlamaTemplateMixin),
    ("mixtral-8x7b-instruct", LlamaTemplateMixin),
    ("dolphin", ChatMLTemplateMixin),
    ("orange", ChatMLTemplateMixin),
    ("llama-3", Llama3TemplateMixin),
    ("minicpm", MiniCPMTemplateMixin),
    ("DeepSeek-V2-Lite", DeepSeekV2LiteMixin),
]


def read_prompt_file(prompt_file, ignore_prefix="#!", system_prefix="SYSTEM:"):
    lines = []
    system = []
    with open(prompt_file, "r") as f:
        while line := f.readline():
            if line.startswith(ignore_prefix):
                if line.startswith(ignore_prefix + system_prefix):
                    system.append(line[len(ignore_prefix) + len(system_prefix):])
                continue
            lines.append(line)
    return {
        "user": "".join(lines),
        "system": "".join(system).strip()
        }


if __name__ == "__main__":
    PRESETS = {}
    # loop through all classes in this file and add them to the presets
    import inspect
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            if issubclass(obj, Preset) and obj != Preset:
                PRESETS[obj.name] = obj
    opt_list, args = getopt.getopt(sys.argv[1:], "hc:t:f:o:p:m:n:x:g")
    opts = dict(opt_list)

    # Default to explain_this if we don't have a file. If we have a file it's better to assume the file contains a full prompt
    if opts.get("-p") is None:
        preset = ExplainPreset if "explain" in sys.argv[0] else DefaultPreset
    else:
        preset = PRESETS.get(opts.get("-p"))
    assert preset is not None

    user_prompt = None
    prompt_globs = []
    if opts.get("-f"):
        prompt_globs = sorted(glob.glob(opts.get("-f")))
    elif args:
        user_prompt = " ".join(args)
    else:
        print("What is your question?")
        user_prompt = sys.stdin.read()

    template = opts.get("-T") or "chatml"
    temperature = float(opts.get("-t", 0)) or (0.0 if (int(opts.get("-n", 1)) == 1 and user_prompt is None) else 0.3) # Use 0 if we only run once on a file
    context = opts.get("-c") or ""
    model_name = opts.get("-m") or DEFAULT_MODEL
    if preset is CodeGenerationPreset:
        model_name = DEFAULT_CODE_GENERATION_MODEL
    cmd_args = []
    assert temperature >= 0
    cmd_args.append("-t")
    cmd_args.append(str(temperature))

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

    if preset is CodeGenerationPreset:
        # Force template to be code completion
        templateMixIn = CodeLlamaCompletionTemplateMixin

        # We need a file for code generation
        assert opts.get("-f") is not None

        cmd_args.append("-c")
        cmd_args.append("4096")
    else:
        cmd_args.append("-c")
        cmd_args.append("4096")

    class ModelPlaceholder: pass

    cmd = [LLAMA_CPP_PATH,] + cmd_args + ["-m", ModelPlaceholder, "--n-predict", "-2"]  # -2 means fill context

    for model in glob.glob(f"{MODELS_PATH}/*{model_name}*.gguf") or [model_name]:

        overrideTemplateMixIn = templateMixIn
        for model_substring, tm in NAME_MATCH_OVERRIDE:
            if model_substring.lower() in model.lower():
                overrideTemplateMixIn = tm
                break
        else:
            print(f"Warning: No template found for {model}, using ChatMLTemplateMixin as a fallback")
            overrideTemplateMixIn = ChatMLTemplateMixin

        class CurrentPrompt(overrideTemplateMixIn, preset): pass
        for prompt_file, prompt in zip([None,] + prompt_globs, [{"user":user_prompt},] + [read_prompt_file(prompt_file, ignore_prefix=opts.get("-x") or "#!") for prompt_file in prompt_globs]):
            if prompt.get("user") is None:
                continue

            print(prompt_file)

            # Create a temporary file for storing the prompt
            with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_prompt_file:
                cp = CurrentPrompt(prompt.get("user"), context)
                sys_prompt = prompt.get("system")
                if sys_prompt:
                    cp.set_system_message(sys_prompt)
                templated_prompt = cp.templated_prompt()
                print(templated_prompt)
                temp_prompt_file.write(templated_prompt)
                # Try to fix an apparent llama.cpp bug where it chops off the last newline
                if templated_prompt[-1] == "\n":
                    temp_prompt_file.write("\n")
                temp_prompt_file.flush()

                for infer_round in range(int(opts.get("-n") or 1)):
                    out_file = opts.get("-o")
                    if out_file is not None:
                        out_file = (out_file.
                            replace('{n}', str(infer_round)).
                            replace('{m}', os.path.basename(model)).
                            replace('{f}', prompt_file))
                        if os.path.exists(out_file):
                            print(f"Skipping {out_file} as it already exists")
                            continue

                    this_cmd = cmd.copy()
                    if 'codellama-70b' in model: # XXX: Temp hack
                        this_cmd.append("-r")
                        this_cmd.append("EOT: true")
                    if 'yi-34b' in model: # XXX: Temp hack
                        this_cmd.append("-r")
                        this_cmd.append("<|im_end|>")
                    if overrideTemplateMixIn == DeepSeekV2LiteMixin:
                        this_cmd.append("-b")
                        this_cmd.append("256") # https://github.com/ggerganov/llama.cpp/issues/7652#issuecomment-2140568771

                    this_cmd[this_cmd.index(ModelPlaceholder)] = model
                    this_cmd += ["-f", temp_prompt_file.name]
                    print(this_cmd)
                    p = subprocess.Popen(this_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                    if '-o' not in opts:
                        while dat := p.stdout.read(1):
                            sys.stdout.buffer.write(dat)
                            sys.stdout.flush()

                    outs = p.communicate()

                    # Check exit code
                    if p.returncode != 0:
                        print("Error: " + outs[1].decode("utf-8", errors="replace"))
                        sys.exit(1)
                    else:
                        outs_s = outs[0].decode("utf-8", errors="replace")
                        if out_file is not None:
                            with open(out_file, "w") as f:
                                f.write(outs_s)
                        else:
                            prompt_user = prompt.get("user")
                            if outs_s.startswith(prompt_user):
                                outs_s = outs_s[len(prompt_user):]
                                # This doesn't work at least in some models because <|im_end|>
                                # seems to be tokenized and stringified back to an empty string.
                                # Instead I just modified the llama.cpp code to just output the
                                # results.

                            print(outs_s)
