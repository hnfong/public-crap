#!/usr/bin/env python3

"""
This is a script to interact with llama.cpp models. It is a wrapper around the
llama.cpp binary that allows you to easily infer prompts and get responses. It
also allows you to use presets to make it easier to use.

Usage:

ask.py [OPTIONS] [PROMPT]

Options:

-h: Show this help message
-g: Set the no generation limit flag
-k: Keep the temporary prompt file

-P args:           Pass through arguments to llama.cpp
-C context:        Set the context for the prompt (not very useful)
-c size:           Set context size prompt (default: model default)
-d size:           Dynamic context size = prompt tokens+size (max is specified by -c)
-t temperature:    Set the temperature (default: 0.3)
-f file:           Input prompt file (can be a glob)
-o file:           Output file (can contain {n}, {m}, {f} for round, model, and file)
-p preset:         Set the preset to use (default: explain_this)
-m model:          Set the model to use. This can be a string in which case the first substring match in ~/Downloads or MODELS_PATH will be used.
-n rounds:         Set the number of rounds to run (default: 1)
-x ignore_prefix:  Set the prefix to ignore in the prompt file (default: #!)
-X extra_prompt:   Set the extra prompt to add to the assistant output (default: "")
-T template:       Set the template to use (default: chatml, but we hardcode some models to use different templates)
-M match,options.. If the model filename contains the match string, then append the specified options (comma separated).
-F match,options.. If the input filename contains the match string, then append the specified options (comma separated).

"""

import datetime
import getopt
import glob
import re
import os
import shutil
import subprocess
import sys
import tempfile

LLAMA_CPP_PATH = os.environ.get("LLAMA_CPP_PATH") or shutil.which('llama-completion') or os.path.expanduser("~/projects/llama.gguf/llama-completion")
MODELS_PATH = os.environ.get("MODELS_PATH") or os.path.expanduser("~/Downloads/")

def model_glob(abbr):
    return glob.glob(f"{MODELS_PATH}/*{abbr}*.gguf")

DEFAULT_MODEL = "gemma-3-12b-it"
DEFAULT_CODE_INSTRUCT_MODEL = "Qwen3-30B-A3B-Instruct"
DEFAULT_CODE_GENERATION_MODEL = "Qwen3-Coder-30B-A3B-Instruct"  # FIM

# Presets

class Preset:
    def __init__(self, user_prompt):
        self.user_prompt = user_prompt
        self._system_message = ""

    def prompt(self):
        raise NotImplementedError("Please implement this method in a subclass", self.__class__)

    def system_message(self):
        assert self._system_message is not None
        return self._system_message

    def set_system_message(self, message):
        assert message is not None
        self._system_message = message


    def templated_prompt(self):
        # Implemented by mixins if needed
        return self.prompt()

    def has_postprocess(self):
        return False

    def override_model(self):
        return None

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

class CliPreset(Preset):
    def __init__(self, user_prompt, context):
        super().__init__(user_prompt)
        self.context = context
        self._system_message = "You are a helpful AI assistant."

    name = "cli"

    def get_os(self):
        import platform
        override = {'Darwin': 'macOS'}
        ret = platform.system()
        return override.get(ret) or ret

    def prompt(self):
        return f"[Only give the command. Do not explain unless necessary, but if you explain, put it in the form of comments appropriate for the script/language you are using as output. IMPORTANT: Make sure the output is executable.]\n[Environment: {os.environ.get('SHELL')}; Operating System: {self.get_os()}\n\n{self.user_prompt}\n"

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

class AskUserPreset(Preset):
    def __init__(self, user_prompt, context):
        super().__init__(user_prompt)
        self._system_message = "You are a helpful, thoughtful and creative AI assistant."
        self._user_question = None
        self._override_model = None
    name = "ask_user"

    example_ini = """
[code_review]
question = Review this code.

[fill_in]
question = Fill in the parts marked with "..." according to the comments. Keep the comments except "...".

[whatswrong]
question = Identify errors (if any) with this code and suggest replacements. Just write out the code that needs to be changed,.

[didwemiss]
question = Did we miss anything? Be creative and thoughtful. Do not point out mundane things just for the sake of answering though.
model = gemma-2-9b
"""

    def override_model(self):
        return self._override_model

    def prompt(self):
        import configparser
        if self._user_question is None:
            # Read user-defined preset questions from ~/.config/ask/presets.ini using configparser
            config = configparser.ConfigParser()
            ini_path = "~/.config/ask/presets.ini"
            config.read(os.path.expanduser(ini_path))
            presets = config.sections()
            choices = {}
            models = {}
            for i, preset in enumerate(presets, 1):
                if preset == "defaults":
                    if "model" in config[preset]:
                        self._override_model = config[preset]["model"]
                    continue

                try:
                    choices[i] = config[preset]['question']
                    print(f"{i}. \033[1m{preset}\033[0m: {choices[i][:100]}")
                    models[i] = config[preset].get('model') # OK to be None
                except KeyError:
                    print(f"Error in {ini_path} at section {preset}")

            cache_dir = os.path.expanduser("~/.cache/ask")
            os.makedirs(cache_dir, exist_ok=True)
            history_file = os.path.join(cache_dir, "history.txt")

            # In addition to presets, show the last 3 entries from ~/.cache/ask/history.txt . These history choices are to be named 'a', 'b', 'c' (to separate them from the numeric ones)
            with open(history_file, "r") as f:
                history = f.readlines()
                for i, entry in enumerate(history[-3:], 1):
                    abc = chr(i + ord('a') - 1)
                    qqq = entry.strip().split('\t', 1)[-1]
                    print(f"{abc}. " + qqq)
                    choices[abc] = qqq

            print(f"m. input custom model")

            while True:
                user_input = input("Choose a preset (or type a custom question): ")
                if user_input.isdigit() and 1 <= int(user_input) <= len(presets):
                    self._user_question = choices[int(user_input)]
                    self._override_model = models[int(user_input)]
                elif user_input.strip() == "m": # mode to choose model
                    self._override_model = input("Model: ")
                    if (temp_glob := model_glob(self._override_model)):
                        print(f"Selecting model: {temp_glob[0]}")
                    else:
                        print("Warning: Cannot find suitable model")
                    continue
                elif user_input.strip() in choices.keys():
                    self._user_question = choices[user_input.strip()]
                else:
                    self._user_question = user_input
                break # continue is for looping the model choice logic

            # If the user inputs a single number, replace it with the preset value instead
            if self._user_question.isdigit() and 1 <= int(self._user_question) <= len(presets):
                self._user_question = config[presets[int(self._user_question) - 1]]['question']

            # Remember the question in ~/.cache/ask/history.txt
            with open(history_file, "a") as f:
                f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t{self._user_question}\n")

        if len(self.user_prompt) < 4096:
            return f"{self._user_question}\n(Please be concise unless the answer requires in-depth analysis)\n--- Start of data ---\n\n{self.user_prompt}\n\n--- End of data ---\n"
        else:
            # For longer contexts, repeat the question/instruction at the end
            return f"{self._user_question}\n(Please be concise unless the answer requires in-depth analysis)\n--- Start of data ---\n\n{self.user_prompt}\n\n--- End of data ---\n\n{self._user_question}\n(Please be concise unless the answer requires in-depth analysis)\n"


class GitCommitSummarizePreset(Preset):
    def __init__(self, user_prompt, context):
        super().__init__(user_prompt)
        self.context = context
        self._system_message = "You are a helpful, thoughtful and creative AI assistant."

    name = "gitcommit"

    def postprocess(self, outs):
        outs = outs.replace('[end of text]', '').rstrip()
        return "\n".join(line.strip() if line.strip() == '' else '🤖 ' + line.rstrip() for line in outs.splitlines(keepends=False))

    def has_postprocess(self):
        return True

    def prompt(self):
        return f"""
Please write a summary of the changes as a git commit message. The first line must be very concise and short. Subsequent paragraph(s) should be concise, but make sure you mention all important and interesting points.

```
{self.user_prompt}
```

Please write a summary of the changes as a git commit message. The first line must be very concise and short. Subsequent paragraph(s) should be concise, but make sure you mention all important and interesting points.
"""


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

class ExplainSourceCodePreset(Preset):
    def __init__(self, user_prompt, context):
        super().__init__(user_prompt)
        self.context = context
        self._system_message = "You are a helpful AI assistant."

    name = "sourcefile"
    def prompt(self):
        return f"""
Explain what this source code file is doing on a very high level. Do not
discuss implementation details. Just explain what it does to somebody who is
not familiar with the codebase (and not familiar with the class names and their
interactions etc.)

----

{self.user_prompt}

----

Explain what this source code file is doing on a very high level. Do not
discuss implementation details. Just explain what it does to somebody who is
not familiar with the codebase (and not familiar with the class names and their
interactions etc.)
"""


class SummarizeLawCase(Preset):
    def __init__(self, user_prompt, context):
        super().__init__(user_prompt)
        self.context = context
        self._system_message = "You are a helpful AI assistant."

    name = "lawcase"
    def prompt(self):
        return f"""
### TASKS ###

1. Briefly summarize the facts of the following case.
1.1 After your summary, craft a catchy, memorable sentence to help the reader remember the case. (The sentence should be short and concise and reference distinctive elements of the case)
2. Then, briefly summarize the arguments of the two parties.
3. Summarize the legal principles (ratio decidendi) of the case. Be detailed and thorough. There is no word limit. Use multiple paragraphs. If applicable, focus on the points that might be novel or controversial.
4. Finally, is there anything striking, unusual or remarkable about the case? (It may or may not be about law, just anything you find extraordinary.)

----

{self.user_prompt}

----

### TASKS ###

1. Briefly summarize the facts of the above case.
1.1 After your summary, craft a catchy, memorable sentence to help the reader remember the case. (The sentence should be short and concise and reference distinctive elements of the case)
2. Then, briefly summarize the arguments of the two parties.
3. Summarize the legal principles (ratio decidendi) of the case. Be detailed and thorough. There is no word limit. Use multiple paragraphs. If applicable, focus on the points that might be novel or controversial.
4. Finally, is there anything striking, unusual or remarkable about the case? (It may or may not be about law, just anything you find extraordinary.)
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
        self.offset = int(offset)

        # assert file size is less than 10kb
        assert os.path.getsize(self.file_name) < 50000
        self.content_bytes = open(self.file_name, "rb").read()

        # while self.content_bytes[self.offset] != ord(b"\n"):
            # self.offset += 1

    def path(self):
        return self.file_name
    def code_language(self):
        # XXX: The CodeGeeX4 model wants the language. We may or may not be
        # using this model, but the code seems generally useful enough.
        GUESSES = {
            ".py": "python",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "cpp",
            ".hpp": "cpp",
            ".java": "java",
            ".js": "javascript",
            ".ts": "typescript",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sass": "sass",
            ".less": "less",
            ".php": "php",
            ".sql": "sql",
            ".rb": "ruby",
            ".rs": "rust",
            ".vim": "vimscript",
        }
        for x in range(1, 10):
            suffix = self.file_name[-x:]
            if suffix in GUESSES:
                return GUESSES[suffix]

        # Guess from shebang
        if self.content_bytes.startswith(b"#!"):
            shebang = self.content_bytes[:max(self.offset, 128)].split(b"\n")[0]
            if b"python" in shebang:
                return "python"
            if b"bash" in shebang:
                return "bash"
            if b"/sh" in shebang:
                return "bash"

    def prefix(self):
        return self.content_bytes[:self.offset].decode("utf-8")

    def suffix(self):
        return self.content_bytes[self.offset:].decode("utf-8")

class QwenFimMixin:
    def templated_prompt(self):
        return f"""
<|fim_prefix|>{self.prefix()}<|fim_suffix|>{self.suffix()}<|fim_middle|>
""".strip() + "\n"

    def postprocess(self, outs):
        ends = (' [end of text]', '[end of text]', )
        for end in ends:
            if end in outs:
                return outs.split(end)[0]
        return outs

    def has_postprocess(self):
        return True

class SeedTemplateMixin:
    def templated_prompt(self):
        return f"""
<seed:bos>system
{self.system_message()}<seed:eos><seed:bos>user
{self.prompt()}<seed:eos><seed:bos>assistant
        """.strip() + "\n"

class KimiTemplateMixin:
    def templated_prompt(self):
        return f"""
<|im_system|>system<|im_middle|>{self.system_message()}<|im_end|><|im_user|>user<|im_middle|>{self.prompt()}<|im_end|><|im_assistant|>assistant<|im_middle|>
        """.strip() + "\n"

    def extra_gguf_options(self):
        return ["-r", "<|im_end|>"]

class ErnieTemplateMixin:
    def templated_prompt(self):
        return f"""
<|begin_of_sentence|>{self.system_message()}
User: {self.prompt()}
Assistant:
        """.strip() + " "

    def extra_gguf_options(self):
        return ["-r", "<|im_end|>"]


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

    def extra_gguf_options(self):
        return ["-r", "<|im_end|>"]

class NoThinkingChatMLTemplateMixin:
    def templated_prompt(self):
        if self.system_message():
            return f"""
<|im_start|>system
{self.system_message()}<|im_end|>
<|im_start|>user
{self.prompt()}<|im_end|>
<|im_start|>assistant
<think>

</think>
            """.strip() + "\n"
        else:
            return f"""
<|im_start|>system
You are a helpful assistant.<|im_end|>
<|im_start|>user
{self.prompt()}<|im_end|>
<|im_start|>assistant
<think>

</think>
            """.strip() + "\n"

    def extra_gguf_options(self):
        return ["-r", "<|im_end|>"]

class HomunculusNothinkTemplateMixin:
    def templated_prompt(self):
        if self.system_message():
            return f"""
<|im_start|>system
{self.system_message()}<|im_end|>
<|im_start|>user
{self.prompt()} /nothink<|im_end|>
<|im_start|>assistant
            """.strip() + "\n"
        else:
            return f"""
<|im_start|>user
{self.prompt()} /nothink<|im_end|>
<|im_start|>assistant
            """.strip() + "\n"


class LongContextChatMLTemplateMixin(ChatMLTemplateMixin):
    def extra_gguf_options(self):
        return ["-r", "<|im_end|>", "-c", "9216"]

class QwenTemplateMixin(ChatMLTemplateMixin):
    def system_message(self):
        # https://www.reddit.com/r/LocalLLaMA/comments/1gpwrq1/how_to_use_qwen25coderinstruct_without/
        return "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."

class Qwen3InstructTemplateMixin:
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
    def system_message(self):
        # https://www.reddit.com/r/LocalLLaMA/comments/1gpwrq1/how_to_use_qwen25coderinstruct_without/
        return "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."

class Qwen3ThinkingTemplateMixin(Qwen3InstructTemplateMixin):
    def extra_gguf_options(self):
        return ["-r", "<|im_end|>", "-c", "9216"]

class Qwen3TemplateMixin:
    # XXX: added /nothink to disable thinking by default
    def templated_prompt(self):
        if self.system_message():
            return f"""
<|im_start|>system
{self.system_message()}<|im_end|>
<|im_start|>user
{self.prompt()} /nothink<|im_end|>
<|im_start|>assistant
            """.strip() + "\n"
        else:
            return f"""
<|im_start|>user
{self.prompt()} /nothink<|im_end|>
<|im_start|>assistant
            """.strip() + "\n"
    def system_message(self):
        # https://www.reddit.com/r/LocalLLaMA/comments/1gpwrq1/how_to_use_qwen25coderinstruct_without/
        return "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."

class NemotronQwen3Reasoning:
    def templated_prompt(self):
        return f"""<｜User｜>{self.prompt()}<｜Assistant｜><think>"""

class InstructionTemplateMixin:
    def templated_prompt(self):
        return f"""

### Instruction:

{self.prompt()}

### Response:

"""

class CodeGeeX4TemplateMixin:
    def templated_prompt(self):
        return f"""

###PATH:{self.path()}
###LANGUAGE:{self.code_language()}
###MODE:LINE
<|code_suffix|>{self.suffix()}<|code_prefix|>{self.prefix()}<|code_middle|>
""".strip() + "\n"

    def postprocess(self, outs):
        # Remove '<|code_middle|>' (somehow llama.cpp emits this, not sure why)
        PREFIX = "<|code_middle|>\n"
        splitter = outs.split(PREFIX)
        return splitter[-1]

    def has_postprocess(self):
        return True

class LlamaTemplateMixin:
    def templated_prompt(self):
        return f"""<s>[INST] <<SYS>>\n{self.system_message()}\n<</SYS>>\n\n{self.prompt()} [/INST]"""

class DevstralTemplateMixin:
    def templated_prompt(self):
        return f"""[SYSTEM_PROMPT]{self.system_message()}[/SYSTEM_PROMPT][INST]{self.prompt()}[/INST]""".strip()

class Phi3TemplateMixin:
    def templated_prompt(self):
        return f"""<|user|>\n{self.prompt()}<|end|>\n<|assistant|>\n"""

class Phi4TemplateMixin:
    def templated_prompt(self):
        return f"""<|im_start|>system<|im_sep|>{self.system_message()}<|im_end|><|im_start|>user<|im_sep|>{self.prompt()}<|im_end|><|im_start|>assistant<|im_sep|>"""

    def extra_gguf_options(self):
        return ["-r", "<|im_end|>"]

class Phi4ReasoningTemplateMixin:
    def templated_prompt(self):
        return f"""<|im_start|>system<|im_sep|>You are Phi, a language model trained by Microsoft to help users. Your role as an assistant involves thoroughly exploring questions through a systematic thinking process before providing the final precise and accurate solutions. This requires engaging in a comprehensive cycle of analysis, summarizing, exploration, reassessment, reflection, backtracing, and iteration to develop well-considered thinking process. Please structure your response into two main sections: Thought and Solution using the specified format: <think> {{Thought section}} </think> {{Solution section}}. In the Thought section, detail your reasoning process in steps. Each step should include detailed considerations such as analysing questions, summarizing relevant findings, brainstorming new ideas, verifying the accuracy of the current steps, refining any errors, and revisiting previous steps. In the Solution section, based on various attempts, explorations, and reflections from the Thought section, systematically present the final solution that you deem correct. The Solution section should be logical, accurate, and concise and detail necessary steps needed to reach the conclusion. Now, try to solve the following question through the above guidelines:<|im_end|><|im_start|>user<|im_sep|>{self.prompt()}<|im_end|><|im_start|>assistant<|im_sep|>"""

    def extra_gguf_options(self):
        return ["-r", "<|im_end|>", "-c", "9216"]

class ZephyrTemplateMixin:
    def templated_prompt(self):
        return f"""<|user|>\n{self.prompt()}</s>\n<|assistant|>\n"""

class Gemma2Mixin:
    def templated_prompt(self):
        return f"""<start_of_turn>user\n{self.prompt()}<end_of_turn>\n<start_of_turn>model\n"""

Gemma3Mixin = Gemma2Mixin
class GLMTemplateMixin:
    def templated_prompt(self):
        return f"""[gMASK]<sop><|system|>
{self.system_message()}<|user|>
{self.prompt()}<|assistant|>"""


class MiniMaxTemplateMixin:
    # Yes this isn't messed up terminal escape codes. It's really like this.
    # The thinking part is because if we allow it to think, it would just get stuck in a loop at temp=0
    def templated_prompt(self):
        return f"""
]~b]system
{self.system_message()}[e~[
]~b]user
{self.prompt()}[e~[
]~b]ai
<think>
OK, I understand this. Let's reply.
</think>
""".strip() + "\n"

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
    def extra_gguf_options(self):
        return ["-b", "256"] # https://github.com/ggerganov/llama.cpp/issues/7652#issuecomment-2140568771

class DeepSeekR1DistillMixin:
    def templated_prompt(self):
        if self.system_message():
            return f"""<｜begin▁of▁sentence｜>{self.system_message()}<｜User｜>{self.prompt()}<｜Assistant｜>"""
        else:
            return f"""<｜begin▁of▁sentence｜><｜User｜>{self.prompt()}<｜Assistant｜>"""

    def extra_gguf_options(self):
        return ["-c", "8192"]

class DeepSeekV25Mixin:
    def templated_prompt(self):
        if self.system_message():
            return f"""<｜begin▁of▁sentence｜>{self.system_message()}<｜User｜>{self.prompt()}<｜Assistant｜>"""
        else:
            return f"""<｜begin▁of▁sentence｜><｜User｜>{self.prompt()}<｜Assistant｜>"""

    def extra_gguf_options(self):
        return ["-c", "2048"] # We don't have enough RAM for 4096

class DeepSeekV3Mixin:
    def templated_prompt(self):
        if self.system_message():
            return f"""{self.system_message()}<｜User｜>{self.prompt()}<｜Assistant｜>"""
        else:
            return f"""<｜User｜>{self.prompt()}<｜Assistant｜>"""

class Mistral3InstructTemplate:
    def templated_prompt(self):
        # wtf? If we really believe the chat_template above, this is the result. But it doesn't work.
        # return f"""\n    \n\n\n<s>\n\n    \n    \n        \n            [INST] {self.prompt()}[/INST]\n        \n    \n        """
        return f"""[SYSTEM_PROMPT]{self.system_message()}[/SYSTEM_PROMPT]\n[INST]{self.prompt()}[/INST]"""

class DotsLLMTemplate:
    def templated_prompt(self):
        return f"""<|system|>{self.system_message()}<|endofsystem|><|userprompt|>{self.prompt()}<|endofuserprompt|><|response|>"""
    def extra_gguf_options(self):
        return ["-r", "<|endofresponse|>"]

class OpenBuddyTemplate:
    def templated_prompt(self):
        return f"""
<|role|>system<|says|>{self.system_message()}<|end|>
<|role|>user<|says|>{self.prompt()}<|end|>
<|role|>assistant<|says|>
""".strip()

class OlmoTemplate:
    def templated_prompt(self):
        return f"""
<|system|>
{self.system_message()}
<|user|>
{self.prompt()}
<|assistant|>
""".strip() + "\n"

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

class MlxArgumentConverter:

    @staticmethod
    def _extract_argument(haystack, needle, subsequent):
        ret = []
        keep = 0
        for arg in haystack:
            if arg == needle or keep > 0:
                ret.append(arg)
                if keep == 0:
                    keep = subsequent
                else:
                    keep -= 1
                    if keep <= 0:
                        break
        return ret

    # Hackish way to convert llama-cli arguments to mlx_lm.generate arguments
    def mlx_generate_arguments_from_llama_args(self, args):
        # We might need to manually add the start of whatever token though!
        mlx_args = ["mlx_lm.generate", "--ignore-chat-template"]
        mlx_args += MlxArgumentConverter._extract_argument(args, "--temp", 1)

        # It's unclear whether we should be using --max-tokens or --max-kv-size, the latter seems to imply rotating whatever, so maybe don't do that.
        mlx_args += ["--max-tokens", MlxArgumentConverter._extract_argument(args, "-c", 1)[-1]]

        mlx_args += ["--model", MlxArgumentConverter._extract_argument(args, "-m", 1)[-1].replace("--", "/").split(".mlx")[0]]

        mlx_args += ["--prompt", "-"]  # Feed it through stdin, hopefully it works.

        return mlx_args

class HuanyuanTemplateMixin:
    def templated_prompt(self):
        return f"""
<|startoftext|>{self.system_message()}<|extra_4|>{self.prompt()}<|extra_0|>
""".strip()

class HuanyuanNoThinkTemplateMixin:
    def templated_prompt(self):
        return f"""
<|startoftext|>{self.system_message()}<|extra_4|>/no_think {self.prompt()}<|extra_0|>
""".strip()

class GPTOSSTemplateMixin:
    def templated_prompt(self):
        return f"""
<|start|>system<|message|>{self.system_message()}<|end|><|start|>user<|message|>{self.prompt()}<|end|><|start|>assistant
""".strip()

    def system_message(self):
        return "You are ChatGPT, a large language model trained by OpenAI. Knowledge cutoff: 2024-06. Current date: 2025-08-07. Reasoning: low"

    def extra_gguf_options(self):
        return ["-c", "8192"]

class GLM45TemplateMixin(MlxArgumentConverter):
    def templated_prompt(self):
        return f"""
[gMASK]<sop>
<|system|>
{self.system_message()}
<|user|>
{self.prompt()}
/nothink
<|assistant|>
<think></think>
""".strip()

class GLM47TemplateMixin:
    def templated_prompt(self):
        return f"""
[gMASK]<sop>
<|system|>
{self.system_message()}
<|user|>
{self.prompt()}
<|assistant|>
</think>
""".strip()

class LingTemplateMixin:
    def templated_prompt(self):
        return f"""
<role>SYSTEM</role>{self.system_message()}<|role_end|><role>HUMAN</role>{self.prompt()}<|role_end|><role>ASSISTANT</role>
""".strip()

NAME_MATCH_OVERRIDE = [
    # More specific first
    ("Nemotron-Research-Reasoning-Qwen", NemotronQwen3Reasoning),
    ("Qwen3-4B-Instruct", Qwen3InstructTemplateMixin),
    ("Qwen3-30B-A3B-Instruct", Qwen3InstructTemplateMixin),
    ("Qwen3-30B-A3B-Thinking-2507", Qwen3ThinkingTemplateMixin),
    ("Qwen3-235B-A22B-Instruct", Qwen3InstructTemplateMixin),
    ("Qwen3-235B-A22B-Thinking", Qwen3ThinkingTemplateMixin),
    ("Qwen3-Coder-480B-A35B-Instruct", Qwen3InstructTemplateMixin),
    ("Qwen3-Coder-30B-A3B-Instruct", Qwen3InstructTemplateMixin),
    ("phi-4-reasoning", Phi4ReasoningTemplateMixin),
    ("OpenBuddy-", OpenBuddyTemplate),
    ("Arcee-SuperNova-v1-", Llama3TemplateMixin),
    ("dots.llm", DotsLLMTemplate),
    ("jan-nano-", LongContextChatMLTemplateMixin),
    ("Kimi-K2-", KimiTemplateMixin),
    ("ERNIE-4.5", ErnieTemplateMixin),
    ("MiniMax", MiniMaxTemplateMixin),
    ("SmolLM3-", ChatMLTemplateMixin),
    ("Seed-", SeedTemplateMixin),
    ("Olmo-", ChatMLTemplateMixin),

    ("GLM-4.5", GLM45TemplateMixin),
    ("GLM-4.7", GLM47TemplateMixin),
    ("gpt-oss", GPTOSSTemplateMixin),
    ("QwenLong-L1.5", Qwen3ThinkingTemplateMixin),

    ("Light-IF", NoThinkingChatMLTemplateMixin),
    ("Ling-", LingTemplateMixin),
    ("Hunyuan-MT", HuanyuanTemplateMixin),
    ("Hunyuan-", HuanyuanNoThinkTemplateMixin),
    ("SmallThinker-", ChatMLTemplateMixin),
    ("OLMo-2-", OlmoTemplate),
    ("Athene-V2", ChatMLTemplateMixin),
    ("DeepSeek-V2-Lite", DeepSeekV2LiteMixin),
    ("DeepSeek-V2.5", DeepSeekV25Mixin),
    ("DeepSeek-V3-", DeepSeekV3Mixin),
    ("DeepSeek-V3-", DeepSeekV3Mixin),
    ("DeepSeek-V3.1", DeepSeekV3Mixin),
    ("DeepSeek-R1", DeepSeekR1DistillMixin),  # Distills, basically
    ("Mimo", LongContextChatMLTemplateMixin),
    ("Mistral-Large-Instruct", Mistral3InstructTemplate),
    ("Mistral-Small", Mistral3InstructTemplate),
    ("Ministral-3", Mistral3InstructTemplate),
    ("miqu-", Mistral3InstructTemplate),
    ("OpenCoder-8B", ChatMLTemplateMixin),
    ("SuperNova-Medius", ChatMLTemplateMixin),
    ("Virtuoso-", ChatMLTemplateMixin),
    ("Qwen2", QwenTemplateMixin),
    ("Qwen3", Qwen3TemplateMixin),
    ("command-r-plus", CommandRPlusTemplateMixin),
    ("calme-3.2-instruct", ChatMLTemplateMixin),
    ("dolphin", ChatMLTemplateMixin),
    ("gemma-2", Gemma2Mixin),
    ("gemma-3", Gemma3Mixin),
    ("glm-4", GLMTemplateMixin),
    ("llama-2", LlamaTemplateMixin),
    ("llama-3", Llama3TemplateMixin),
    ("minicpm", MiniCPMTemplateMixin),
    ("mixtral-8x7b-instruct", LlamaTemplateMixin),
    ("orange", ChatMLTemplateMixin),
    ("phi-3", Phi3TemplateMixin),
    ("phi-4", Phi4TemplateMixin),
    ("qwen2", QwenTemplateMixin),
    ("qwq-32b", QwenTemplateMixin),
    ("starling", ChatMLTemplateMixin),  # Officially it's not ChatML, but it works. Officially, the prompt template looks like this: single_turn_prompt = f"GPT4 Correct User: {prompt}<|end_of_turn|>GPT4 Correct Assistant:"
    ("tinyllama_v1.1", ChatMLTemplateMixin),
    ("wizardlm", WizardLmMixin),
    ("zephyr", ZephyrTemplateMixin),
    ("TheDrummer_Valkyrie", Llama3TemplateMixin),
    ("Devstral-", DevstralTemplateMixin),
    ("Falcon3-Mamba-7B", ChatMLTemplateMixin),
    ("Homunculus-", HomunculusNothinkTemplateMixin),
]

FIM_MATCH_OVERRIDE = [
    ("Qwen2", QwenFimMixin),
    ("Qwen3", QwenFimMixin),
    ("codegeex4", CodeGeeX4TemplateMixin),
]


def read_prompt_file(prompt_file, ignore_prefix="#!", system_prefix="SYSTEM:", extra_args_prefix=" ARGS:", user_prompt=None):
    lines = []
    system = []
    extra_args = []
    with open(prompt_file, "r") as f:
        while line := f.readline():
            if line.startswith(ignore_prefix):
                if line.startswith(ignore_prefix + system_prefix):
                    system.append(line[len(ignore_prefix) + len(system_prefix):])
                if line.startswith(ignore_prefix + extra_args_prefix):
                    extra_args += line[len(ignore_prefix) + len(extra_args_prefix):].split()

                continue
            lines.append(line)

    content = "".join(lines)
    if user_prompt:
        if len(content) < 1024 * 8:
            user_final = user_prompt + "\n```\n" + content + "\n```\n"
        else:
            user_final = user_prompt + "\n```\n" + content + "\n```\n" + user_prompt
    else:
        user_final = content

    return {
        "user": user_final,
        "system": "".join(system).strip(),
        "extra_args": extra_args
        }


if __name__ == "__main__":
    PRESETS = {}
    # loop through all classes in this file and add them to the presets
    import inspect
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            if issubclass(obj, Preset) and obj != Preset:
                PRESETS[obj.name] = obj
    opt_list, args = getopt.getopt(sys.argv[1:], "DqhkP:C:c:d:t:f:o:p:m:n:x:gX:T:M:F:v")
    verbosity = opt_list.count(('-v', ''))
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
        if preset is CodeGenerationPreset:
            user_prompt = opts.get("-f")
        else:
            prompt_globs = sorted(glob.glob(opts.get("-f")))
            if args:
                user_prompt = " ".join(args)
    elif args:
        user_prompt = " ".join(args)
    else:
        # if it's a terminal print the prompt
        if sys.stdin.isatty():
            print("What is your question?")
        user_prompt = sys.stdin.read()

    template = opts.get("-T") or "chatml"

    if opts.get("-t") is not None:
        temperature = float(opts.get("-t"))
    elif int(opts.get("-n") or 1) == 1 and user_prompt is None:
        # Use 0 if we only run once on a file
        temperature = 0.0
    else:
        # Default to 0.3
        temperature = 0.3

    context = opts.get("-C") or ""
    gguf_context_size = opts.get("-c", "0")
    model_name = opts.get("-m") or DEFAULT_MODEL
    if preset in (AskUserPreset, CodeReviewPreset):
        model_name = DEFAULT_CODE_INSTRUCT_MODEL
    if preset in (CodeGenerationPreset,):
        model_name = DEFAULT_CODE_GENERATION_MODEL
    cmd_args = []
    cmd_args.append("--no-escape")  # llama.cpp just doesn't do sane defaults...
    cmd_args.append("--no-conversation")  # llama.cpp just doesn't do sane defaults...
    cmd_args.append("--no-display-prompt")  # llama.cpp just doesn't do sane defaults...
    assert temperature >= 0
    cmd_args.append("--temp")
    cmd_args.append(str(temperature))

    is_mac = "Darwin" in subprocess.run(["uname"], capture_output=True).stdout.decode("utf-8").strip()
    if opts.get("-g") or is_mac:
        cmd_args.append("-ngl")
        cmd_args.append("99")

    if "-q" not in opts:
        # If not quiet mode, verbose prompt
        cmd_args.append("--verbose-prompt")

    templateMixIn = None
    overrideTemplateMixIn = None
    if template == "chatml":
        templateMixIn = ChatMLTemplateMixin
    elif template == "llama":
        templateMixIn = LlamaTemplateMixin
    else:
        templateMixIn = InstructionTemplateMixin

    if preset is CodeGenerationPreset:
        # Force template to be code completion
        model = model_glob(model_name)[0]
        for model_substring, tm in FIM_MATCH_OVERRIDE:
            if model_substring.lower() in model.lower():
                overrideTemplateMixIn = tm
                break
        else:
            if overrideTemplateMixIn is None:
                sys.stderr.write(f"Warning: No template found for {model}, using QwenFimMixin as a fallback\n")
                overrideTemplateMixIn = QwenFimMixin

        context = args[0]
        # We need a file for code generation
        assert opts.get("-f") is not None

        cmd_args.append("-c")
        cmd_args.append(gguf_context_size)

        cmd_args.append("--n-predict")
        cmd_args.append("200")
    else:
        cmd_args.append("-c")
        cmd_args.append(gguf_context_size)

    # Passthrough arguments
    if opts.get("-P"):
        cmd_args += opts.get("-P").strip().split()

    # If -n or --n-predict is not in the args, we add "--n-predict", "-2"
    if '-n' not in cmd_args and '--n-predict' not in cmd_args:
        cmd_args += ["--n-predict", "-2"] # -2 means fill context


    class ModelPlaceholder:
        pass

    cmd = [LLAMA_CPP_PATH,] + cmd_args + ["-m", ModelPlaceholder]

    assert_count = 0
    ggg = model_glob(model_name)
    for model in ggg or [model_name]:
        if '-of-000' in model and '01-of-000' not in model:
            # Only use the first shard
            continue
        assert_count += 1
        assert assert_count == 1, "We need to refactor this so that we don't iterate on the model since we actually don't need to"

        if overrideTemplateMixIn is None:
            for model_substring, tm in NAME_MATCH_OVERRIDE:
                if model_substring.lower() in model.lower():
                    overrideTemplateMixIn = tm
                    break
            else:
                if overrideTemplateMixIn is None:
                    if opts.get('-T') == 'REQUIRED':
                        print(f"No appropriate template found for {model}, exiting with error")
                        sys.exit(1)
                    else:
                        print(f"Warning: No template found for {model}, using ChatMLTemplateMixin as a fallback")
                        overrideTemplateMixIn = ChatMLTemplateMixin

        class CurrentPromptTemplate(overrideTemplateMixIn, preset):
            pass
        for prompt_file in prompt_globs or [None,]:
            if prompt_file is None:
                prompt = {"user":user_prompt}
            else:
                prompt = read_prompt_file(prompt_file, ignore_prefix=opts.get("-x") or "#!", user_prompt=user_prompt)

            if prompt.get("user") is None:
                continue

            # Create a temporary file for storing the prompt
            with tempfile.NamedTemporaryFile(mode="w", delete=('-k' not in opts)) as temp_prompt_file:
                cp = CurrentPromptTemplate(prompt.get("user"), context)
                sys_prompt = prompt.get("system")
                if sys_prompt:
                    cp.set_system_message(sys_prompt)
                templated_prompt = cp.templated_prompt()
                if verbosity >= 2:
                    print(templated_prompt)
                temp_prompt_file.write(templated_prompt)
                # Try to fix an apparent llama.cpp bug where it chops off the last newline
                if templated_prompt[-1] == "\n":
                    temp_prompt_file.write("\n")
                if extra := opts.get("-X"):
                    # Extra prompt as prefix of assistant output
                    temp_prompt_file.write(extra)
                    if extra[-1] != "\n":
                        temp_prompt_file.write("\n")
                temp_prompt_file.flush()

                for infer_round in range(int(opts.get("-n") or 1)):
                    out_file = opts.get("-o")
                    if '-m' not in opts: # allow overriding the model if the user did not specify it.
                        if cp.override_model() is not None:
                            try:
                                try_model = model_glob(cp.override_model())[0]
                                if not os.path.isfile(try_model):
                                    raise Exception(try_model + " exists but is not a file?!")
                                model = try_model
                            except Exception as e:
                                sys.stderr.write(f"Error using {cp.override_model()} as model: {e}")
                                sys.stderr.write("\n")
                                sys.stderr.flush()
                    if out_file is not None:
                        out_file = (out_file.
                            replace('{n}', str(infer_round)).
                            replace('{m}', os.path.basename(model)).
                            replace('{f}', prompt_file))
                        if os.path.exists(out_file):
                            print(f"Skipping {out_file} as it already exists")
                            continue

                    this_cmd = cmd.copy()
                    if hasattr(cp, "extra_gguf_options"):
                        this_cmd.extend(cp.extra_gguf_options())

                    this_cmd[this_cmd.index(ModelPlaceholder)] = model
                    this_cmd += ["-f", temp_prompt_file.name]

                    if (prompt_extra_args := prompt.get("extra_args")):
                        this_cmd += prompt_extra_args


                    if prompt_file and "-F" in opts:  # if filename matches a string, add more options
                        conditional_options = opts.get("-F").split(",")
                        if conditional_options[0] in prompt_file:
                            this_cmd += conditional_options[1:]
                            if '--skip--' in this_cmd:
                                continue
                    if "-M" in opts:  # if model matches a string, add more options
                        m_params = [opt[1] for opt in opt_list if opt[0] == '-M']
                        for m_param in m_params:
                            conditional_options = m_param.split(",")
                            if conditional_options[0] in model or conditional_options[0] == '*':
                                this_cmd += conditional_options[1:]

                    if opts.get("-d"):
                        with tempfile.TemporaryFile() as tok_stderr:
                            # Dynamically set the context size. But we need the user context size as a maximum value
                            LLAMA_TOKENIZER = os.path.dirname(LLAMA_CPP_PATH) + os.path.sep + "llama-tokenize"
                            tokenize_cmd = [LLAMA_TOKENIZER, "-m", model, "-f", temp_prompt_file.name, "--show-count", "--log-disable", "--ids"]
                            tok_p = subprocess.Popen(tokenize_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=tok_stderr)
                            tok_stdout, _ = tok_p.communicate()
                            tok_stderr.seek(0)
                            tok_stderr = tok_stderr.read()
                            tok_success = False
                            if tok_p.returncode == 0:
                                tok_m = re.search(r"Total number of tokens: (\d+)", tok_stdout.decode("utf-8", errors="replace"))
                                if tok_m:
                                    this_cmd += ["-c", "%d" % min(int(opts.get("-c") or 2147483647), int(tok_m.group(1)) + int(opts.get("-d")))]
                                    tok_success = True

                            if not tok_success:
                                sys.stderr.write("Error: cannot determine number of tokens in prompt!\n")
                                sys.stderr.write("Command: %s\n" % str(tokenize_cmd))
                                sys.stderr.write("Exit code: %d\n" % tok_p.returncode)
                                sys.stderr.write("Output: %s\n" % tok_stdout.decode("utf-8", errors="replace"))
                                sys.stderr.write("Stderr: %s\n" % tok_stderr.decode("utf-8", errors="replace"))
                                sys.exit(1)


                    if verbosity > 0:
                        print("Original prompt file: ", prompt_file)

                    if "-D" in opts:
                        # Dry run only
                        continue

                    with tempfile.TemporaryFile() as temp_stderr:
                        stderr_output = b""
                        if isinstance(cp, MlxArgumentConverter):
                            mlx_cmd = cp.mlx_generate_arguments_from_llama_args(this_cmd)
                            if verbosity > 0:
                                print(mlx_cmd)
                            temp_prompt_file.seek(0) # Reset to zero hopefully it can be read.
                            p = subprocess.Popen(mlx_cmd, stdin=temp_prompt_file, stdout=subprocess.PIPE, stderr=temp_stderr)

                        else:
                            if verbosity > 0:
                                print(this_cmd)
                            p = subprocess.Popen(this_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=temp_stderr)

                        if '-o' not in opts and not cp.has_postprocess():
                            while dat := p.stdout.read(1):
                                sys.stdout.buffer.write(dat)
                                sys.stdout.flush()

                        outs = p.communicate()
                        temp_stderr.seek(0)
                        stderr_output = temp_stderr.read()

                    # Check exit code
                    if p.returncode != 0:
                        sys.stderr.write("Error: " + stderr_output.decode("utf-8", errors="replace"))
                        sys.stderr.write("\n")
                        sys.stderr.flush()
                        sys.exit(1)
                    else:
                        outs_s = outs[0].decode("utf-8", errors="replace")
                        if cp.has_postprocess():
                            outs_s = cp.postprocess(outs_s)

                        if out_file is not None:
                            print(f"Writing result to: {out_file}")
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
else:
    print(__name__)

