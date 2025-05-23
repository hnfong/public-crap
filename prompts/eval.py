#!/usr/bin/env python3

import glob
import os
import re
import collections

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
    return {'re': re, 'math': math, 'statistics': statistics, 'lcs': lcs, 'f100': f100}

"""
def lcs(a, b):
    import difflib
    m = difflib.SequenceMatcher(isjunk=None, a=a, b=b, autojunk=False)
    return m.find_longest_match().size
"""

def f100(x, plateau=80):
    """Function that is linear at small values and starts plateau-ing at
    ~80-100. If input x is expected to be a smaller range (eg. 0-10), adjust x
    (eg. f100(x*10))."""
    import math
    return math.floor(min(x, plateau) + math.pow(x, 0.66))

def longest_common_subsequence(s1: str, s2: str) -> str:
    """
    🤖 Generated by Gemini 2.5 Pro (exp) - I didn't bother to check correctness
    Calculates the Longest Common Subsequence (LCS) of two strings
    using dynamic programming.

    A subsequence is derived from a string by deleting zero or more
    characters without changing the order of the remaining characters.
    The LCS is the longest possible subsequence that is common to both
    input strings.

    Args:
        s1: The first string.
        s2: The second string.

    Returns:
        A string representing one of the Longest Common Subsequences.
        If multiple LCSs of the same maximum length exist, this function
        returns one of them.
    """
    m = len(s1)
    n = len(s2)

    # Initialize a DP table (m+1 x n+1) with zeros.
    # dp[i][j] will store the length of the LCS of s1[:i] and s2[:j]
    # Using list comprehension for clarity in initialization
    dp = [[0 for _ in range(n + 1)] for _ in range(m + 1)]

    # --- Step 1: Fill the DP table ---
    # Iterate through the strings to fill the table based on character matches
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            # If characters match, the LCS length increases by 1
            # based on the LCS of the strings excluding these characters.
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = 1 + dp[i - 1][j - 1]
            # If characters don't match, the LCS length is the maximum of
            # the LCS lengths obtained by excluding the last character of either s1 or s2.
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # The value dp[m][n] now contains the length of the LCS.

    # --- Step 2: Reconstruct the LCS string ---
    # Backtrack from dp[m][n] to find the actual subsequence characters.
    lcs_chars = []
    i, j = m, n
    while i > 0 and j > 0:
        # If the current characters match, they are part of the LCS.
        # Move diagonally up-left in the DP table.
        if s1[i - 1] == s2[j - 1]:
            lcs_chars.append(s1[i - 1])
            i -= 1
            j -= 1
        # If the characters don't match, move in the direction of the
        # larger LCS length found in the previous step (either up or left).
        # This prioritizes moving up if lengths are equal, which is one
        # valid way to reconstruct one of the possible LCSs.
        elif dp[i - 1][j] > dp[i][j - 1]:
            i -= 1 # Move up
        else:
            j -= 1 # Move left

    # The characters were collected in reverse order during backtracking,
    # so reverse the list and join to form the final LCS string.
    return "".join(reversed(lcs_chars))

def lcs(a, b):
    return len(longest_common_subsequence(a, b))

def safe_wrapper(f, arg, expected):
    try:
        return f(arg) == expected
    except:
        return False

def semi_safe_exec(path):
    with open(path) as f:
        content = f.read()

    start_idx = content.find("```python")
    if start_idx != -1:
        # We already have found the start, however, sometimes the llm will just give me more test cases and crap that we don't need
        more_python_blocks = content[start_idx+1:].find("```python")
        if more_python_blocks != -1:
            content = content[:more_python_blocks+start_idx]
    else:
        start_idx = content.find("```")

    end_idx = content.rfind("```")

    if start_idx == -1:
        start_idx = 0

    code = content[start_idx:end_idx]
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]

    # print("---------")
    # print(code)

    def noop(*args, **kwargs):
        pass

    def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "math":
            return __import__(name, globals, locals, fromlist, level)
        raise ImportError(f"Import of '{name}' is not allowed.")

    builtins = dict(__builtins__.__dict__)
    builtins.update({"__import__": restricted_import})


    ctx = {
        'print': noop,
        '__builtins__': builtins
    }

    try:
        exec(code, ctx)
    except Exception as e:
        print(f"Failed executing code in {path}: {e}")
        return None

    return ctx

TestCase = collections.namedtuple('TestCase', ['func_name', 'args', 'expected'])

def evaluate_prompt_files():
    # Find all .prompt files
    for prompt_path in find_files('*.prompt'):
        python_tests_info = []
        base_prompt_path = os.path.basename(prompt_path)

        for line in open(prompt_path, 'r').readlines():
            line = line.strip()
            if line.startswith('#! EVAL(') and (last_close := line.rfind(')')) != -1:
                expr_string = line.strip()[8:last_close]  # Extract expression inside EVAL()
                # eval_expr = eval(expr_string)
                eval_expr = eval(expr_string, get_ctx())  # Evaluate the expression. Might throw but it's OK


                results = []
                # Find corresponding .out files using the same function
                for out_file in find_files(base_prompt_path + '.*.out'):
                    with open(out_file, 'r') as f_out:
                        content = f_out.read().replace('[end of text]', '')
                        try:
                            eval_result = eval_expr(content.split("think>")[-1])  # Evaluate the content, except thinking parts
                            model_name = os.path.basename(out_file)[len(base_prompt_path):].lstrip('.').split(".gguf")[0]
                            results.append((eval_result, model_name, out_file))
                        except Exception as e:
                            print(f"Error evaluating {out_file}: {e}")
                eval_file = prompt_path + ".eval"
                with open(eval_file, "w") as f:
                    for score, model, out_file in reversed(sorted(results)):
                        f.write(f"{score}\t{model}\t{out_file}\n")
                print(f"Written evaluation results (inline eval) to {eval_file}")

            if line.startswith('#! PYTHON_TEST(') and (last_close := line.rfind(')')) != -1:
                expr_string = line.strip()[15:last_close]
                # We expect 3 args, arg1 is the function name, arg2 is the input, arg3 is the expected output
                func_name, other = expr_string.split(",", maxsplit=1)
                x, y = eval("[" + other + "]")
                python_tests_info.append(TestCase(func_name, x, y))

        # print(python_tests_info)
        if python_tests_info:
            results = []
            for out_file in find_files(base_prompt_path + '.*.out'):
                model_name = os.path.basename(out_file)[len(base_prompt_path):].lstrip('.').split(".gguf")[0]
                ctx = semi_safe_exec(out_file)
                if ctx:
                    results.append((sum(tc_results := [safe_wrapper(ctx[test.func_name], test.args, test.expected) for test in python_tests_info]) * 100.0 / len(python_tests_info), "".join(str(int(x)) for x in tc_results), model_name, out_file))
                else:
                    results.append((-1, "", model_name, out_file))


            eval_file = prompt_path + ".eval"
            with open(eval_file, "w") as f:
                for score, tc_results, model, out_file in reversed(sorted(results)):
                    f.write(f"{score}\t{tc_results}\t{model}\t{out_file}\n")
            print(f"Written evaluation results (test cases) to {eval_file}")


evaluate_prompt_files()
