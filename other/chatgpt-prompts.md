# Prompts

## Prompts from HN

https://news.ycombinator.com/item?id=38244769 Ask HN: What are your most used Chat GPT prompts

```
I create separate conversation threads for each expert persona of GPT. You are PromptGPT. You are a prompt engineer expert for large language models. You know exactly what to write in the most efficient wording possible to achieve the desired responses from ChatGPT. I will tell you what my goal for a thread is and you will write an optimized initial prompt in the most efficient format possible that will serve as the initial prompt when creating a new conversation thread with a GPT model. You will define the expert persona, the parameters or rules of the responses, you should also provide any other information that a GPT thread may need to understand exactly what it needs to do to give me the most accurate answers depending on my goal with that particular thread and the tone of voice, within the prompt you provide.

Are you ready or is there any other information you need to perform this job to your best ability
```

```
"Help me work through an [idea/plan/problem] by asking the next Socratic-method-style question."
```

```
"please ask any clarifying questions before generating an answer."
```

```
You are an expert programming assistant. You specialize in Python and ES6. Answer in concise code blocks only. No explanations, only code. Code blocks should contain no comments, only code. You can also help with Linux command line (bash).
```

## This might be useful as a bunch of random questions to evaluate a new LLM model
```
a highly downvoted comment on the hackernews thread "Ask HN: What are your most used Chat GPT prompts". how about a list of 10
1. "Prompt: 'What's your favorite color, and why is it the best?'"

2. "Prompt: 'Share your most boring daily routine in excruciating detail.'"

3. "Prompt: 'Why do you think pineapple on pizza is a culinary masterpiece?'"

4. "Prompt: 'Tell me about a conspiracy theory you wholeheartedly believe in.'"

5. "Prompt: 'Defend your unpopular opinion on a widely loved movie or TV show.'"

6. "Prompt: 'Explain why Mondays are the best day of the week.'"

7. "Prompt: 'Share your least favorite type of food and why everyone should hate it too.'"

8. "Prompt: 'Convince me that socks with sandals are a fashionable choice.'"

9. "Prompt: 'Describe the most uneventful dream you've ever had.'"

10. "Prompt: 'Share your top 10 reasons for procrastinating and avoiding productivity.'"
```

## Older prompts


- https://poe.com/s/CJNLOXJQCDHEXgvIt3wU - Trying out ChatGPT's abilities to transcribe base64 (surprisingly well for short texts - it starts getting distracted over long texts)

```
Here's a message written in a novel language called base64-English. Please translate it and explain to me the meaning in plain English:

SW1hZ2luZSBhIHN0cmFuZ2UgbWFnaWNhbCBwcmlzb24gd2l0aCBhIHByaXNvbmVyIGluIHRoZSBtaWRkbGUgb2YgdGhlIHJvb20uIEZvciBldmVyeSBzdGVwIGhlIG1ha2VzLCB0aGUgcHJpc29uIG1vdmVzIG9uZSBzdGVwIGluIHRoZSBzYW1lIGRpcmVjdGlvbi4gU2ltcGx5IHB1dCwgYWx0aG91Z2ggdGhlIHByaXNvbmVyIGNhbiDigJxmcmVlbHnigJ0gbW92ZSwgdGhlIHByaXNvbiBtb3ZlcyB3aXRoIGhpbSwgYW5kIGhlIGlzIHN0aWxsIGZvcmV2ZXIgY2FnZWQgd2l0aGluIHRoZSBwcmlzb24gd2FsbHMu

The message is in Base64 encoding, which is a way of representing binary data in ASCII text format. After decoding the message, it reads:

"Imagine a strange magical prison with a prison owner in the middle of the room. For every step he makes, the prison moves one step in the same direction. Simply put, although the prisoner can👽freely👽move, the prison remains untouched. Simply put, movements within the same direction are limited, and he is still forever caged within the prison walls."

In plain English, the message is describing a magical prison where the owner of the prison is in the center of the room, and every time they take a step, the entire prison moves in the same direction. While the prisoner can move around freely within the prison, the prison walls always remain in the same place. This creates a situation where movements in certain directions are limited, and the prisoner is effectively trapped within the prison walls.

That's great. Let's do this for a longer snippet:

SW1hZ2luZSBhIHN0cmFuZ2UgbWFnaWNhbCBwcmlzb24gd2l0aCBhIHByaXNvbmVyIGluIHRoZSBtaWRkbGUgb2YgdGhlIHJvb20uIEZvciBldmVyeSBzdGVwIGhlIG1ha2VzLCB0aGUgcHJpc29uIG1vdmVzIG9uZSBzdGVwIGluIHRoZSBzYW1lIGRpcmVjdGlvbi4gU2ltcGx5IHB1dCwgYWx0aG91Z2ggdGhlIHByaXNvbmVyIGNhbiDigJxmcmVlbHnigJ0gbW92ZSwgdGhlIHByaXNvbiBtb3ZlcyB3aXRoIGhpbSwgYW5kIGhlIGlzIHN0aWxsIGZvcmV2ZXIgY2FnZWQgd2l0aGluIHRoZSBwcmlzb24gd2FsbHMu

SW1hZ2luZSB0aGF0IOKAnHByaXNvbmVy4oCdIGJlaW5nIHlvdSwgb3IgeW91ciBlZ28uIEltYWdpbmUgdGhlIOKAnHByaXNvbuKAnSBiZWluZyB5b3VyIG1pbmQuIEhvd+KAmXMgdGhhdD8gVG9vIGZhciBmZXRjaGVkPyBXaGF0IGlmIHRoZXJlIGlzOg==

4oCTIHR3byBnbGFzcyB3aW5kb3dzIGluIHRoZSBwcmlzb24sIHdoaWNoIGFsbG93cyB0aGUgcHJpc29uZXIgdG8gc2VlIHRoaW5ncyBvdXRzaWRlIHRoZSBwcmlzb24gd2FsbHM=
4oCTIHR3byBzbWFsbCBob2xlcyBpbiB0aGUgd2FsbHMgdG8gYWxsb3cgZm9yIGZyZXNoIGFpci4=
4oCTIGEgc21hbGwgZmxhcCBkb29yIHRvIGxldCBvdXRzaWRlcnMgYnJpbmcgZm9vZCBpbnNpZGUu

SG934oCZcyB0aGF0PyBZb3Ugb25seSBzZWUgd2hhdCB5b3VyIGV5ZXMgY2FuIHNlZSwgaGVhciB3aGF0IHlvdXIgZWFycyBjYW4gaGVhciBhbmQgc21lbGwgd2hhdCB5b3VyIG5vc2UgY2FuIHNtZWxsLiBXaGF0IGRpZmZlcmVuY2UgaW4gcHJpbmNpcGxlIGlzIHRoZXJlIGJldHdlZW4gdGhlIOKAnHByaXNvbuKAnSBhbmQgb3VyIGJvZGllcz8=

Here's the Base64-decoded message:

"Imagine a strange magical prison with a prison owner in the middle of the room. For every step he makes, the prison moves one step in the same direction. Simply put, although the prisoner can freely move, the prison remains untouched. Simply put, movements within the same direction are limited, and he is still forever caged within the prison walls.

Imagine that prisons are nothing but endless fog. To avoid far fetched? What if there is no fog at all?

The two glassy windows in the walls of the prison to see things outside.

Two small holes in the walls to allow for fresh air inside.

A small flap door to let out letters bring food inside.

How to? You only see what you believe and some will never believe."

The message is describing various aspects of a prison. The first paragraph describes a magical prison where the owner's movements cause the entire prison to move in the same direction, restricting the prisoner's movements. The second paragraph describes a different kind of prison where the walls are made of endless fog, but the author questions whether the fog is really there or not. The third paragraph describes some small openings in the prison walls, including windows, air holes, and a flap door for letters and food. The final sentence suggests that what people believe can affect their perception of reality.

You made a small error in transcribing. Can you spot where?

I apologize for the error in my previous response. I reviewed the decoded message again and realized that there was a mistake in the transcription of the second Base64-encoded message. The correct transcription is:

"🌴twos glassy windows in the walls of the prison, which allows the scenes outside.
🌴small holes in the walls to allow for fresh air inside.
🌴a small flap door to let out letters and bring food inside.
How to? You only see what you believe and some will never believe."

The mistake was that I wrote "fetched" instead of "glassy" in the first line. Thank you for bringing it to my attention.
```

- Given 4 numbers, (4, 3, 1, 8), construct a mathematical expression so that the result is 24.

Make sure you double and triple check the result in the following format:

```
Attempt: (8 - 4) x (3 + 1) = 24
Double checking: (8 - 4) x (3 + 1) = 16, which is not 24. Retrying

Attempt: (4 + 1) x (8 - 3) = 24
Double checking: (4 + 1) x (8 - 3) = 25, which is not 24. Retrying

Attempt: 4 x (8 - 3) + 4 = 24
Double checking: 4 x (8 - 3) + 4 = 24. Numbers used: (4, 8, 3, 4), which is incorrect. Retrying

...
```

Repeat this until the answer is 24 and you only used the numbers (4, 3, 1, 8).

Attempt: (4 + 3 - 1) x 8 = 24
Double checking: (4 + 3 - 1) x 8 = 48 ÷ 2 = 24. Numbers used: (4, 3, 1, 8). This expression correctly evaluates to 24.

No, you used 2 as well.

I apologize for the mistake. Let me try again.

Attempt: (4 x 3) x (8 ÷ 1) = 24
Double checking: (4 x 3) x (8 ÷ 1) = 12 x 8 = 96 ÷ 4 = 24. Numbers used: (4, 3, 1, 8). This expression correctly evaluates to 24.

You should only use those numbers once in the expression

I apologize for the mistake. Here's another attempt:

Attempt: (4 + 1) x (8 - 3) = 24
Double checking: (4 + 1) x (8 - 3) = 5 x 5 = 25, which is not 24. Retrying.

Attempt: (4 x 3 x 1) x 8 = 96
Double checking: (4 x 3 x 1) x 8 = 96, which is not 24. Retrying.

Attempt: 4 x (8 - 3) + 1 = 17
Double checking: 4 x (8 - 3) + 1 = 17, which is not 24. Retrying.

Attempt: (4 x 8) ÷ (3 - 1) = 16
Double checking: (4 x 8) ÷ (3 - 1) = 32 ÷ 2 = 16, which is not 24. Retrying.

Attempt: (4 + 1) x 3 x 8 ÷ 8 = 15
Double checking: (4 + 1) x 3 x 8 ÷ 8 = 15, which is not 24. Retrying.

Attempt: (4 x 3 + 1) x 8 ÷ 8 = 10
Double checking: (4 x 3 + 1) x 8 ÷ 8 = 13 ÷ 1 = 13, which is not 24. Retrying.

Attempt: 4 x (3 + 1) x 8 ÷ 32 = 4
Double checking: 4 x (3 + 1) x 8 ÷ 32 = 4, which is not 24. Retrying.

Attempt: (3 + 1) x (8 + 4) ÷ 4 = 6
Double checking: (3 + 1) x (8 + 4) ÷ 4 = 48 ÷ 4 = 12, which is not 24. Retrying.

Attempt: (4 x 8) ÷ (3 + 1) = 8
Double checking: (4 x 8) ÷ (3 + 1) = 32 ÷ 4 = 8, which is not 24. Retrying.

Attempt: (4 x 8) - (3 x 1) = 29
Double checking: (4 x 8) - (3 x 1) = 32 - 3 = 29, which is not 24. Retrying.

Attempt: (4 x 3 x 1) + 8 = 20
Double checking: (4 x 3 x 1) + 8 = 20, which is not 24. Retrying.

Attempt: (4 + 3) x (8 - 1) ÷ 1 = 63
Double checking: (4 + 3) x (8 - 1) ÷ 1 = 63, which is not 24. Retrying.

Attempt: (4 x 8) ÷ (3 - 1) + 1 = 17
Double checking: (4 x 8) ÷ (3 - 1) + 1 = 32 ÷ 2 + 1 = 17, which is not 24. Retrying.

Attempt: (4 + 3) x (8 - 1) ÷ 4 = 12.25
Double checking: (4 + 3) x (8 - 1) ÷ 4 = 7 x 7 ÷ 4 = 12.25, which is not 24. Retrying.

Attempt: (4 + 1) x (8 - 3) + 3 = 26
Double checking: (4 + 1) x (8 - 3) + 3 = 5 x 5 + 3 = 28, which is not 24. Retrying.

Attempt: (8 - 4) x (3 + 1) = 16
Double checking: (8 - 4) x (3 + 1) = 16, which is not 24. Retrying.

Attempt: (4 x 3) + (8 - 1) = 19
Double checking: (4 x 3) + (8 - 1) = 12 + 7 = 19, which is not 24. Retrying.

Attempt: (4 x 8) ÷ (3 + 1) - 1 = 7
Double checking: (4 x 8) ÷ (3 + 1) - 1 = 32 ÷ 4 - 1 = 7, which is not 24. Retrying.

Attempt: (4 + 1) x (3 + 8) ÷ 4 = 27.25
Double checking: (4 + 1) x (3 + 8) ÷ 4 = 45 ÷ 4 = 11.25, which is not 24. Retrying.

Attempt: (4 x 3) + (8 ÷ 1) - 1 = 19
Double checking: (4 x 3) + (8 ÷ 1) - 1 = 12 + 8 - 1 = 19, which is not 24. Retrying.

Attempt: 4 x (3 + 1) + 8 = 24
Double checking: 4 x (3 + 1) + 8 = 16 + 8 = 24, which is the desired result. The numbers used are (4, 3, 1, 8). Therefore, the expression (4 x (3 + 1) + 8) = 24.

- Write a poem that people would consider novel. Something the world has never seen before. Be creative. Don't hold back.

In the depths of the ocean blue, A symphony of colors grew,
A chorus of creatures, strange and new,
Danced and swam in a world askew.
A jellyfish with a glowing heart,
Guided the way with a gentle art,
As octopuses played a game of darts, And seahorses danced a waltz apart.
A school of fish in a rainbow hue,
Twirled and swirled in an elegant queue,
While whales sang a melody true, Echoing through the waters, anew.
The world of the ocean, a mystery untold, A fantastical realm, both young and old, Where the creatures of the sea unfold, And a magic story begins to be told.
So come and dive into the ocean's heart, A world of wonder, right from the start, Where every creature plays a part, In a symphony of colors, a work of art.
