# Tech

## "Moore's Law"
- "number of transistors per silicon chip doubles every 18-24 months"
- Exponential increase in computational power counteracts difficulty of solving asymptotically hard computational problems
- Main driver of economy between 1980-2020

## Asymptotic complexity
- "Analysis of complexity when problem size grows large."
- Smaller components of the complexity function and constants become irrelevant.

## Programming
- "Writing software to make computers do what people want."
- Traditionally the first half was emphasized, people studied how to make computers work.
- Given that computers are relatively simple things, we have for the most part figured out how to deal with computers. However, "what people want" is a much harder problem.

## Software Engineering
- "Programming with other people"
- Understanding of software is a given, and relatively easy; the key is to also understand how people understand software. (eg. Linus Torvalds on "taste")

## Software eating the world

## Open Source Software

### Licenses - GPLv2
- "Software license that requires reciprocal sharing of source code"
- Drafting considered somewhat problematic by lawyers but pragmatically acceptable given it is a defacto standard
  * Problems include - legal status of preamble, contractual nature despite assertion that it is not a contract, fuzzy definition of derivative work, etc.

### Licenses - GPLv3
- "Software license that requires licensee to have compatible views with the FSF"
- Contents considered rather draconian by most lawyers; non-OSS focused companies generally try to avoid touching GPLv3 code
- Not as widely adopted as GPLv2

### Licenses - MIT/BSD
- "Permissive licenses that basically allow licensee to do whatever they want with the code as long as some formalities are observed"
- BSD has different versions, 2,3,4 clauses. 4-clause is considered problematic and should be avoided.

### Licenses - Apache v2
- "Mostly Permissive license; used extensively by the Java OSS ecosystem"

### Licenses - Creative Commons
- "A diverse set of licenses ranging from somewhat restrictive to extremely permissive"
- people have confused the different types of CC licenses with funny consequences

### CVS
- "a clumsy tool for keeping different versions of files"
- defacto standard before SVN came along
- centralized repository that made forking technically difficult
- projects stagnated due to arguments over commit rights and forks were a bitter business because merging was difficult

### SVN
- "a better CVS"
- the next defacto standard before Git came along

### Git
- "distributed revision control"
- forking (cloning) was made easy, it is also the first interaction with any repository
- democratized OSS software development by decentralizing control, making all peers equal in function
