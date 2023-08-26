# Miraculous Healing and Bayes Rule

A refresher for the Bayes rule:

```
         P(B|A) * P(A)
P(A|B) = -------------
             P(B)

        P(B) * P(A|B)
P(A) = --------------
           P(B|A)
```

Now, suppose:

- A: "I" get cured of a supposedly incurable disease
- B: miracles exist

Also, assume that P(A) is mostly low, but empirically not zero. Sometimes people do suddenly get cured without a good reason.

Let us investigate the **subjective probabilities** of:

1. The devout believer,
2. the denialist, and
3. the "rational experimentalist"

![image](./images/healing-the-sick.jpg)

# The Devout Believer

Obviously, P(B) ~= 1

```
          1 * P(A|B) <- [Jesus factor, or am I worthy of salvation?]
P(A) ~= --------------
          P(B|A) ~= P(B) =~ 1
```

Basically the subjective probability of A depends on whether you think you will be saved. "Jesus" helps quite a bit in boosting the probability here. For those who object to the subjective probability here, don't fret -- a subjective probability of 99.999% still doesn't mean anything in the frequentist world. It just means they have messed up priors.

However, for those who believe not only in subjective truth but also in subjective probability, this might ring a bell.

# The Denialist


The denialist just pretends B isn't a thing. So,

- P(B) is very low
- P(B|A) is very low (won't believe the evidence even if something apparently miraculous happened)
- P(A) ~= P(A|B) -- basically, B is not a real thing, P(A|B) is just P(A) because B is irrelevant.


# The Rational Experimentalist


"*I'll believe it when I see it*" -- your local Rational Experimentalist

- P(B) is very low (denote it as 'e')
- P(B|A) is very high, i.e. "I will believe in miracles if I get cured"

So,

```
        e * P(A|B)       e
P(A) = -------------- < --- ~= 0
           1             1
```

Here, the math is straightforward, but the interpretation is funny. On the surface, the rational experimentalist is just tautologically applying the formula, since in order to be able to say "I will believe in miracles if I get cured" given a low P(B) prior, P(A) must have had been very very low (i.e. virtually no possibility of a non-miraculous cure). Then the math is just as expected.

But if we take a subjective reality world view, that whatever we do not know is truly not yet settled, then "discovering" or "deciding" that P(B|A) is high is logically the same act as "discovering" or "deciding" that P(A) is low.

i.e. **If** you have a rational choice to decide that P(B|A) is high, in making that choice you have also decided that P(A) is very very low. (It gets even lower if you believe you're not worthy).

I wanted to say "that's why frequentist approaches to miracle finding doesn't work", but I suppose that doesn't really follow.

# Further reading

[Subjective Truth](../2022/09-Subjective_Truth.md)
