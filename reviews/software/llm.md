# LLM reviews

Subjective LLM reviews. Mostly on open weight models.

## Llama series

- Llama1 lacked fine tune. I didn't have hardware to run the Llama1 finetunes (vicuna etc.)
- Llama2 was reasonably decent for the time (early days of locally run open weight models). I didn't use it for much though.
- Llama3 was pretty good. Llama3 70B was basically the best local model one could run at the time, and most models that claimed to be better than it were fine tunes.
  - The long context llama3 models weren't that great. They seemed to have improved quite a bit in llama3.3
- Llama4 was a disaster (in a winner takes all environment). Not sure whether it was caused by switch to MOE architecture or just them getting out-competed by Chinese companies. Not that Meta had the leading edge models anyway, theirs was always slightly behind OpenAI and Google. The special-fine-tuned-for-lmsys-leaderboard thing was pretty dodgy NGL.

## Gemma series

- Gemma2 27B used to be my most beloved local model. It felt intelligent beyond its size, and its local performance was fast enough that I could just use it as a real time chatbot (the 70B llama models were too slow during inference on my Mac Studio). 10/10 rating.
- Gemma3 27B felt a bit "too creative" sometimes, and could go off in unpredictable directions and sometimes you just can't make it come back. That said I still use it as my go-to model. Long context was fine up to a point. Same for the smaller models on the long context front. I think they're probably the best models for English-based tasks with long contexts. (Don't have objective benchmarks to back up that claim though)

## Qwen series

- Don't remember a lot about Qwen1/2
- Qwen2.5 was hailed as the best open weights model by r/LocalLlama/ . I didn't really see a big difference between Qwen2.5 and Llama3. That does mean Qwen2.5 70B was up there with Llama3 70B as potentially one of the best open weights model at the time.
- Qwen3 had too many models, it wasn't easy to evaluate them all (and I haven't)
  - I haven't run the larger models much. Since I default to gemma-3 for the ~30B size use cases, I generally run the smaller models
  - I've tried Qwen3-8B and Qwen3-4B as coding assistances. They're reasonably good for the job for simple cases. For complex tasks probably need to use a much larger LLM anyway. I haven't seen a very noticable difference between the 4-8B and the 30B models (except speed, which is usually the deciding factor in most cases, so I stick with the smaller models).
    - Note that I don't use reasoning mode for coding. For some reason they just keep reasoning non-stop. I have no idea how to coax good results from reasoning mode from Qwen3.

- QwQ was an interesting model. Obsoleted by Qwen3 for sure, but the reasoning it had was pretty fun especially when you can't run R1 locally (and the R1 distills kinda sucked)

## Arcee

- Before Qwen3 came out, I used SuperNova-Medius as a coding model. It was small enough, and somehow still reasonably powerful for coding tasks. I don't have objective benchmarks (there are a couple people in r/LocalLlama/ who had high praise for SuperNova-Medius too, so I hope I wasn't hallucinating) but I used it religiously for a couple months until the smaller Qwen3 models came out. As mentioned, speed was the deciding factor. The Qwen3 small models were faster and were not obviously worse.
- The later Arcee models didn't impress me enough to continue using them. As I commented on a post in r/LocalLlama/: "after trying Homunculus with some of my personal prompts, it seems Homunculus underperforms SuperNova Medius by a significant margin. Damn. I had high hopes.."

## Starling-LM-7B-alpha

This is a lesser known, older (released in late 2023) model that I included for review because it consistently performs well on a very specific problem: given a title of a youtube video (which is often long, spammy, clickbaity and could contain Chinese characters (for my use case)), shorten it. (This is the high level idea not the prompt) At the time I wrote the script, only Starling-LM-7B-alpha actually followed the instructions and did what I wanted... Llama3 (7B) just didn't like the Chinese input.

This shows how regardless of fancy benchmarks, the best model is the one that performs well in your use case (and why having lots of open weight models to choose from is great!)

## DeepSeek

- DeepSeek v1 was unremarkable.
- I forgot what I thought of DeepSeek v2. I probably didn't have the vRAM to run it...
- DeepSeek v2.5 was one of the best models at the time for Cantonese. It wasn't perfect, but it was better than basically all models except Gemini for dealing with Cantonese especially Cantonese writing. It was also unfortunately a huge model. I found a UD GGUF quant by somebody on r/LocalLLama/. Unfortunately the author seems to have unlisted/deleted the huggingface repo. Sadge.
- DeepSeek v3 could basically generate perfect Cantonese. Also it was huge.
- DeepSeek R1 was all the hype. And for good reason. It was up there as one of the best leading models including proprietary ones. As of mid 2025, I think this is still the best model for Cantonese writing.
  - Bought the maxxed out M3 Ultra with 512GB RAM for R1. In retrospect, the Chinese models kept rolling out, so I guess it was a good buy.
- DeepSeek's coder and lite (circa v2.5) models were unremarkable.

## Phi

- The phi series of models simply didn't quite click with me. Apparently Phi-4 models are pretty good? I never found a good use case for them nor particularly good reviews from other online commenters

## Kimi

- Kimi-K2 is *very* promising. It feels at least as good as R1 without having to reason. Maybe if it gets the R1 distill treatment it will become a monster. It's definitely the highest performing open weights model in my (limited) tests. It's noticably worse than R1 for writing Cantonese though unfortunately.

## dots.llm1

I haven't had the chance to thoroughly review this yet unfortunately.

## Mistral series

- Mixtral 8x7B was the OG MoE model. It was pretty good for the time (late 2023)
- Mistral 7B was also pretty good for the time (late 2023).
  - The dolphin finetunes were quite good. I used them quite a bit when they were still fresh.
- Miqu was pretty interesting, but obviously it couldn't be used in any serious manner.
- Mistral's later models weren't really that remarkable after that.
  - I haven't had particularly good results with Codestral and Devstral. At best they felt like on par with the other ~30B models (Gemma,Qwen).

## qwen2.5-7b-ins-v3

This isn't a qwen model per-se. It was uploaded by somebody, without a model card, to huggingface, and the only real info about the model was in a r/LocalLLaMA/ post: https://www.reddit.com/r/LocalLLaMA/comments/1g03rdn/hidden_gem_happzy2633qwen257binsv3_is_an/

The model is nothing special these days, but at the time of its upload (I hesitate to call it "release") in around Sep 2024, it was basically one of the first reasoning models to exist. Reasoning models were still a new thing, and the only other offering out there was OpenAI's o1 preview model (which did not give you the reasoning tokens). DeepSeek R1 had not been released yet, neither had Qwen's qwq.

Of course its actual performance (quality) was pretty meh, given that it probably was fine-tuned from qwen2.5 7b base (per the name), but it was definitely doing the reasoning just like all the other models we know in 2025.

It's interesting how glimpse of "real" history like this is often lost to popular narrative. Anyways.
