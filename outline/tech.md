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


## Programming Languages

### C
- De-facto standard for low level systems programming
- Standard library tries hard to make you commit programming mistakes
- Superceded by C++, Objective C, and Rust, among others

### C++

- Most commonly used in higher level apps where speed is important but memory allocations aren't expected to fail.
- Tries to fix problems in C, but many issues linger, especially memory management problems
- Generally slow to compile
- Standard library rather limited in scope

### Rust

- Relatively new comer, but is gaining traction quickly as C and C++ replacement
- Promises memory safety as long as you don't use unsafe constructs

### Go

- ?

### Java

- One of the first popular high level languages
- JVM, JIT, GC
- Found its place in enterprise server technology stacks
- Tend to have a lot of boilerplate, software written tend to be very verbose
- Extensive standard library. Lots of third party open source libraries.

### C# / .NET

- Microsoft's clone of Java (in spirit, not in implementation)
- Arguably better in design and implementation, but no widespread adoption outside Microsoft platforms

### Javascript

- Standard language for web browsers
- Language is considered by some to be nice enough that people start using it on the backend too
- Not remotely close to Java (although in these 25 years they seem to have converged a bit)

### Perl

- Pretty much dead language by now
- Superceded by: PHP, python and ruby
- Used to be a great scripting language that is everything that PHP, python and ruby was

### Python

- Great language as long as speed and type checking is not important
- Python devs generally have good "taste" in terms of code cleaniness
- One obvious way to do things
- One of the few general programming languages favored by both software engineers and non-software engineers (eg. data scientists, statisticians, etc.)

### PHP

- Used to be popular web programming language before the days of Ruby on Rails and Django.
- No self-respectable programmer admits to coding primarily on PHP these days


### Ruby

- Whenever you are considering using ruby, it is wise to choose Python instead
- The language is fine. However, the dev community tries its best to encourage people to write unmaintable code:
  - Encouraging many valid alternative ways of doing the same thing, making it easy for people to write code, but forces readers to learn all the possible ways the language can work to understand the code.
  - Monkey patching encouraged (via Ruby on Rails probably), as a reader you can only guess what the code is doing after a couple of `require`s
  - Generally attracts devs who can tolerate this status quo, leading to vicious cycles

### Haskell

- It's pure!
- Haskell programmers figured out how to represent state change with `monads` and thereafter acted as if they invented imperative programming

### Lisp

- ?
- Mother of all functional-ish languages
- Powerful macros
- Many dialects (Logo is a lisp dialect)

### Objective-C

- Relatively simple dynamic OOP language grafted on top of C
- Usually only used when working on Apple platforms

### Swift

- Modern language by Apple
- Usually only used when working on Apple platforms


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
