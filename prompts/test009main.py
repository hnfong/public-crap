import sys

CASES = [
            {  # 0
                "args": ("code/009-code2.test.1.in", b"0"),
                "expect": 0,
            },
            {  # 1
                "args": ("code/009-code2.test.1.in", b"9"),
                "expect": 127,
            },
            {  # 2
                "args": ("code/009-code2.test.1.in", b"2 by"),
                "expect": 17,
            },
            {  # 3
                "args": ("code/009-code2.test.1.in", b"1 Z"),
                "expect": 17,
            },
        ]

import test009

case = CASES[int(sys.argv[1])]
result = test009.binary_search_file(*case["args"])
print(repr(result), " vs ", repr(case["expect"]))
assert result == case["expect"]
