# Software Engineering

- You don’t write the code for the machines, you write it for your colleagues and your future self. Write it for the junior ones as a reference. (Copied from https://alexewerlof.medium.com/my-guiding-principles-after-20-years-of-programming-a087dc55596c )

- K.I.S.S.
  - Managing complexity is the most challenging part of software engineering.
  - Once complexity increases, it is hard to reduce it. Any increased complexity implies long term maintenance costs.
  - A complete graph has n(n-1)/2 edges. Complexity usually increases quadratically as opposed to linearly.
  - Compartmentalize complexity. Try to minimize interaction of new code with existing code and subsystems.
  - Don't add features to a non-trivial project unless you have to
  - Don’t solve a problem that doesn’t exist. Don’t do speculative programming. (Copied from https://alexewerlof.medium.com/my-guiding-principles-after-20-years-of-programming-a087dc55596c )
  - Always delete code when opportunity arises
  - Always try to remove unused features if you can
  - When (and how) to import dependencies is one of the most important decisions for a software architect. The decision usually cannot be undone, so invest the time to evaluate options, and consider carefully whether the benefit is greater than the cost.

- Don't reinvent the wheel
  - Common difficult problems have usually already been solved by somebody more clever than you.
  - But it is good to learn and practice through example of others

- Stay away from hype
  - Stay clear from hype-driven development. But learn all you can. Always have pet projects. (Copied from https://alexewerlof.medium.com/my-guiding-principles-after-20-years-of-programming-a087dc55596c )
  - Most testimonies for some technology don't give sufficient context. The solution that works for them may not be the right one for you.
    - Corollary: Most famous solutions work well for big tech and unicorns. You are not a unicorn.
    - Corollary: if you don't have an urgent scaling problem, you don't need to scale (cf. Don't do speculative programming)
  - Always be on the lookout for hype. The reason you hear about a technology is because it is hyped up. Presume everything is hype until proven otherwise.
  - The antidote of hype is diverse knowledge in software development tools
    - If all you have is a hammer, all problems look like a nail. Know lots of tools, or at least, enough of several tools to know when to pull out which tool ( https://news.ycombinator.com/item?id=30766376 )
