# On formal verification for software systems -

In a software project with sufficiently complicated features/requirements, the "formal specification" is as complicated as the program itself. There are ways to make the specification language less error prone, but... that's what the software community has already been doing for decades, by inventing new high level programming languages that are easier to read/write and less prone to error.

The advances in high level languages in the past couple decades is in a sense equivalent to formal verification (at least verification of lower level languages like C). In fact, a lot of languages compile down into C as an intermediate form. Although we don't usually think of high level languages that way, I'd say they are as close as "a formal specification language for C/asm" as you can realistically hope for. And as an added bonus, those that compile down to C generate "provably equivalent" C code and thus saves you from writing it explicitly.

That said, there might be value in re-writing code again and proving that the two pieces of code are functionally equivalent. I'm not sure this would be an easy sell from a commercial standpoint though... If systems were important enough that that warrants approaches like this, one can always ask _three_ teams to implement a spec separately, and then take the result of the majority.

---

And this, my friends, might actually be the most important reason why programming (for most software projects) is not "maths", despite what all those math-leaning people in academia (mostly CS theorists) say. The concept of proofs is fundamental in mathematics, and the fact that software is often not amenable to "proofs" is evidence that the inherent structure of most problems that software projects encounter are not similar to the structure of the problems in the domain of mathematics at all.

