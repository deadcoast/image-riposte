---
title: "Best Uncensored AI Models in 2026"
source: "Featherless.ai"
author:
published:
created: 2026-09-14
description: "Six uncensored open LLMs worth running in 2026, picked by use case: general reasoning, roleplay and fiction, security research, and small fast models. All live on Featherless, no logs, flat rate."
---
Every uncensored LLM here runs on Featherless through an OpenAI-compatible API, flat rate, nothing to download, so the only real question is which one fits the work you're doing.

## The picks, by use case

A great roleplay model is a mediocre red-team assistant, so pick by the job. Specs and dates are from each model's Featherless page, checked July 2026.

![The six uncensored model picks grouped by use case](https://cdn.prod.website-files.com/6998510a90d20a0dc26dabc5/6a6349ff5abd03b867f9d22e_6a63496e90f683f582b47941_uncensored-picks-by-use-case.png)

The picks at a glance, by use case.

### General and reasoning

- [**Huihui-Qwen3.5-27B-abliterated**](https://featherless.ai/models/huihui-ai/Huihui-Qwen3.5-27B-abliterated). The default for general uncensored work since it shipped in February. Qwen3.5 27B with the refusals stripped, Apache-2.0, and the strongest reasoning of the abliterated builds we host. The most popular sampler config for it runs temperature 0.78. Qwen3.6 abliterations are starting to appear, but this one has the track record.
- [**gemma-4-26B-A4B-it-uncensored**](https://featherless.ai/models/TrevorJS/gemma-4-26B-A4B-it-uncensored). Gemma 4's 26B mixture-of-experts with about 4B parameters active per token, so it's quick for its size. The uncensoring was done carefully, expert by expert, and the author published the results: 0.7% refusal rate across four test sets, quality effectively unchanged. The base model is one of the most-run models on Featherless. Supports tool calling.

### Creative writing and roleplay

The category that sends most people looking for uncensored models in the first place: long fiction, character roleplay, mature but legal writing, all the places a stock model breaks character to refuse.

- [**Huihui-Mistral-Small-3.2-24B-Instruct-2506-abliterated**](https://featherless.ai/models/huihui-ai/Huihui-Mistral-Small-3.2-24B-Instruct-2506-abliterated). Mistral Small 3.2 with refusals removed from the text path only, which keeps the prose clean. Coherent over long scenes, easy to steer with a system prompt, and if you used Dolphin-Mistral 24B for fiction, this is its replacement. Users mostly run it around temperature 0.3 and it writes best there.

### Security research and code

- [**Qwythos-9B-Claude-Mythos-5-1M**](https://featherless.ai/models/empero-ai/Qwythos-9B-Claude-Mythos-5-1M). The new one everyone is trying, and currently the top trending uncensored model in our catalog. A 9B on a Qwen3.5 base, post-trained on 500M tokens of Claude Mythos and Fable traces, with native function calling and self-correction when it has tools. Empero's matched-condition evals report +34 on MMLU and +30 on GSM8K-strict over the base, which is a lot for a fine-tune. Built for security research, red-teaming, and other technical work where hedging wastes your time.

### Small and fast

These cost one concurrent unit on the Chat plan instead of two, so you can run twice as many requests in parallel.

- [**Huihui-Qwen3.5-9B-abliterated**](https://featherless.ai/models/huihui-ai/Huihui-Qwen3.5-9B-abliterated). Qwen3.5 9B, abliterated in March. Solid general chat when you want speed over depth. Popular settings run it at temperature 0.5.
- [**Huihui-Qwen3-4B-Instruct-2507-abliterated**](https://featherless.ai/models/huihui-ai/Huihui-Qwen3-4B-Instruct-2507-abliterated). The smallest model on the list, good for drafting and quick chat, and a Featherless exclusive: nobody else serves it.

These four categories are the short version. The uncensored filter alone lists 781 models as I write this, so browse the full [uncensored](https://featherless.ai/models?training=uncensored) and [abliterated](https://featherless.ai/models?training=abliterated) catalogs if none of these fit.

## Uncensored AI models at a glance

| Model | Base | Size | Best for | Released |
| --- | --- | --- | --- | --- |
| Huihui-Qwen3.5-27B-abliterated | Qwen3.5 | 27B | General / reasoning | Feb 2026 |
| gemma-4-26B-A4B-it-uncensored | Gemma 4 (MoE) | 26B (~4B active) | General, fast | Apr 2026 |
| Huihui-Mistral-Small-3.2-24B-abliterated | Mistral Small 3.2 | 24B | Creative & roleplay | Jul 2025 |
| Qwythos-9B-Claude-Mythos-5-1M | Qwen3.5-9B | 9B | Security / code | Jun 2026 |
| Huihui-Qwen3.5-9B-abliterated | Qwen3.5 | 9B | Fast general chat | Mar 2026 |
| Huihui-Qwen3-4B-Instruct-2507-abliterated | Qwen3 | 4B | Drafting, quick chat | Aug 2025 |

## What it costs and what we log

Nothing gets logged. "Featherless does not log chats, prompts, or completions sent through our API" is the policy, written down [here](https://featherless.ai/docs/privacy-and-logging). Requests are processed in real time and never stored, which for uncensored use is usually the reason to pick a provider carefully in the first place.

Every model on this list runs on the [Chat plan](https://featherless.ai/#pricing): $25 a month, unlimited tokens, 32K context, four concurrent units, cancel anytime. That's the right plan for roleplay, writing, and most day-to-day use. If you're building something that bills by volume, the Developer plan starts at $50 a month in credits, billed per token, and unused credits roll over.

## FAQ

**What is the best uncensored AI model in 2026?** Depends on the job. [Huihui-Qwen3.5-27B-abliterated](https://featherless.ai/models/huihui-ai/Huihui-Qwen3.5-27B-abliterated) for general use, [gemma-4-26B-A4B-it-uncensored](https://featherless.ai/models/TrevorJS/gemma-4-26B-A4B-it-uncensored) when speed matters, [the Mistral Small 3.2 abliteration](https://featherless.ai/models/huihui-ai/Huihui-Mistral-Small-3.2-24B-Instruct-2506-abliterated) for fiction and roleplay, and [Qwythos-9B](https://featherless.ai/models/empero-ai/Qwythos-9B-Claude-Mythos-5-1M) for security work and code.

**Does Featherless log prompts?** No. Prompts and completions sent through the API are not logged or stored, and requests are processed in real time. The policy is published [here](https://featherless.ai/docs/privacy-and-logging).

**What's the difference between an uncensored and an abliterated model?** Uncensored is the outcome, abliterated is one method of getting there: suppressing the refusal behavior inside the model instead of retraining it on refusal-free data the way the Dolphin models were. Abliteration is faster and can cost a little quality, so compare against the base model.

---
