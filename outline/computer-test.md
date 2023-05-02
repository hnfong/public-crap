# Computer test

- Q1: Consider the following program.

```
// 1234.txt contains 4 bytes, "1234".
#include <stdio.h>
int main() {
    int val;
    fread(&val, sizeof(val), 1, fopen("1234.txt", "rb"));
    return printf("%x", val);
}
```

Which of the following are probable outputs of the program on a machine released after year 2000?

(i) 1234 (ii) 4321 (iii) 31323334 (iv) 34333231

* A - (i) only
* B - (i) and (ii) only
* C - (iii) only
* D - (iv) only
* E - Some other combination

- AK: E (Ref: https://en.wikipedia.org/wiki/Endianness https://en.wikipedia.org/wiki/ASCII)
