#!/usr/bin/env python3

import glob
import os
import re

# Use os.walk to find all *.prompt files here. For each such file $prompt_file

# Extract the lines that start with `#! EVAL(`

# Read the expression in EVAL(...) and evaluate it as a python3 expression (it is safe to do so, no need to sanitize or sandbox)

# Find all files named "$prompt_file.*.out" using os.walk, for each file

# read file contents and put it into the evaluation function, get the score from the function (assumed 0 to 100), print the filename and the evaluation results to stdout.
import glob
import os
import fnmatch

def find_files(pattern, root='.'):
    """Find all files matching the pattern using os.walk."""
    matched_paths = []
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if fnmatch.fnmatch(filename, pattern):
                matched_paths.append(os.path.join(dirpath, filename))
    return matched_paths

def get_ctx():
    import math
    import statistics
    import re
    return {'re': re, 'math': math, 'statistics': statistics}

def evaluate_prompt_files():
    # Find all .prompt files
    for prompt_path in find_files('*.prompt'):
        for line in open(prompt_path, 'r').readlines():
            line = line.strip()
            if line.startswith('#! EVAL(') and (last_close := line.rfind(')')) != -1:
                expr_string = line.strip()[8:last_close]  # Extract expression inside EVAL()
                # eval_expr = eval(expr_string)
                eval_expr = eval(expr_string, get_ctx())  # Evaluate the expression. Might throw but it's OK

                base_prompt_path = os.path.basename(prompt_path)

                results = []
                # Find corresponding .out files using the same function
                for out_file in find_files(base_prompt_path + '.*.out'):
                    with open(out_file, 'r') as f_out:
                        content = f_out.read().replace('[end of text]', '')
                        try:
                            eval_result = eval_expr(content)  # Evaluate the content
                            model_name = os.path.basename(out_file)[len(base_prompt_path):].lstrip('.').split(".gguf")[0]
                            results.append((eval_result, model_name, out_file))
                        except Exception as e:
                            print(f"Error evaluating {out_file}: {e}")
                eval_file = prompt_path + ".eval"
                with open(eval_file, "w") as f:
                    for score, model, out_file in reversed(sorted(results)):
                        f.write(f"{score}\t{model}\t{out_file}\n")
                print(f"Written evaluation results to {eval_file}")

evaluate_prompt_files()
