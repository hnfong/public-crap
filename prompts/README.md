# Prompts

Prompts I've come to use to gauge LLM performance, and their results for future reference (and comparison).

(As of writing) Run on M2 Max Mac Studio with 96GB RAM

## Subjective comments

Selected comments. Very subjective.

| Model Name | Comments |
|------------|----------|
| TheDrummer_Valkyrie-49B-v1-Q6_K_L.gguf | Some good comments on [https://www.reddit.com/r/LocalLLaMA/comments/1kqgwh2/drummers_valkyrie_49 b_v1_a_strong_creative/](/localllama/), but in my (these) tests, the model performs really poorly for its class |
| Qwen3-4B | Apparently punches above its weight for coding and some tasks. Currently using this for simple coding tasks |
| gemma-3-12b-it | Works pretty well on long contexts. |
| gemma-3-27b-it | Generally a great model, and is curiously capable of writing passable Classical Chinese poetry, but in some conversations it tends to be a bit too flattering. |
| qwq-32b-q8_0 | An early reasoning model. On my (Mac) hardware, thinking is slow and in most cases isn't really worth the extra tokens. The cost/benefit ratio might change if you're using Nvidia where inference is fast but vRAM is expensive. |
| DeepSeek-v2.5-1210-UD | Dynamic quant of DeepSeek v2.5. One of the few models that can be feasibly run on consumer hardware that writes passable Cantonese. |
| SuperNova-Medius-Q5_K_M | Was my go-to coding model before Qwen3-4B came out. I don't actually have an opinion whether this is better or worse than Qwen3-4B yet, but the 4B model is much smaller (faster)... |
| qwen2.5-72b-instruct | One of the best 72B dense models. Use when raw power is needed. |
| gemma-2-27b-it | Best model local for general purpose use (a balance of speed/quality). Secretly thinking this might still be better than Gemma 3 given the latter's tendency to flatter excessively. |
| starling-lm-7b-alpha | I tried to write a shell script to shorten youtube video titles into a short and concise filename (<~20chars) and curiously this model was the only sub-8B model at the time that actually followed the instructions. Sometimes you just have to test things out instead of relying on reputation and benchmarks. |
