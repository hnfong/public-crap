#!/usr/bin/env python3

"""
Script to generate the README.md
"""

import os
import re
from urllib.parse import quote as url_quote

def insert(node, key_path, value):
    if len(key_path) == 1:
        if key_path[0] not in node:
            node[key_path[0]] = []

        node[key_path[0]].append(value)
        return

    if key_path[0] not in node:
        node[key_path[0]] = {}

    return insert(node[key_path[0]], key_path[1:], value)

def capitalize_if_necessary(s):
    if re.match(r'^[a-zA-Z]+', s):
        return s[0].upper() + s[1:]
    return s

def preorder_dfs(node, f, d = []):
    # print("debug", repr(node))

    if hasattr(node, "append"):
        for item in sorted(node, reverse=True):
            preorder_dfs(item, f, d + [item,])
    elif hasattr(node, "keys"):
        for k in sorted(node.keys(), reverse=True):
            f(k, d)
            preorder_dfs(node[k], f, d + [k,])
    else:
        f(node, d + [None,])

def transformback(s):
    if s.endswith('.md'):
        s = s[:-3]
    return (s
        .replace('_qm_', '?')
        .replace("_ex_", "!").replace("_EX_", "！")
        .replace('_cl_', ':').replace('_CL_', '：')
        .replace("_lp_", "(").replace("_rp_", ")")
        .replace("_LP_", "（").replace("_RP_", "）")
        .replace('_cm_', ',').replace('_CM_', '，')

        .replace('_', ' ') # keep this last
        )

def p(s, d):
    if len(d) > 0 and d[-1] is None:
        # Leaf node

        # Do nothing for the readme file.
        if s == "README.md":
            return

        url = '/'.join(dd for dd in d[:-1])
        print(f"- [{transformback(s)}]({url})")
    else:
        if s == "":
            return

        print("")
        print(("#" * (len(d)+2) ) + " " + capitalize_if_necessary(s))
        print("")

root_node = {}

for root, directories, files in os.walk("."):
    for fn in files:
        if "/." in root: continue
        if fn.endswith(".md"):
            insert(root_node, root.lstrip("./").split("/"), fn)

print("# 散彈一號公廁 (shotgun1 public crap)")
print("")
print("Github Pages link [https://hnfong.github.io/public-crap/](https://hnfong.github.io/public-crap/)")



preorder_dfs(root_node, p)
