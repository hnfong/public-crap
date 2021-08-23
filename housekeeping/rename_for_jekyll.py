#!/usr/bin/env python
"""
# So apparently, Jekyll (as implemented in Github) even recognizes unicode "？"
# (65311) and somehow processes the character in the links differently enough
# to fail translating the link (the page gets processed correctly though). So,
# a "？" becomes "%3F" (which is the ASCII question mark) and the ASCII
# question mark becomes a literal "?".

# I have no idea how f**ked up a system could be to mess up these characters
# like this. That said, Ruby.

# Anyway, the workaround seems to be "escaping" question marks and other
# dubious characters with some format that they like.
"""

import os


for root, directories, files in os.walk("."):
    for fn in files:
        if "/." in root: continue

        if fn.endswith(".md"):
            nfn = fn.replace("?", "_qm_").replace("？", "_qm_").replace("﹖", "_qm_")
            if nfn != fn:
                print(root + os.path.sep + fn, root + os.path.sep + nfn)
                os.rename(root + os.path.sep + fn, root + os.path.sep + nfn)
