# 03. Inference Under the Hood

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

[§02](02-how-llms-work.md) ended with the catch: every generated token takes a full pass through the model, one after another. Serving that cheaply became its own discipline as LLMs became a mass product: continuous batching (Orca, 2022), PagedAttention and vLLM (2023), speculative decoding (2022–23), and prompt caching as a priced API feature (2024). This section covers what happens on the server between your request and the last token, at the depth an application engineer needs to predict cost and latency (P10). Running your own models is covered in [§31](31-open-weights-self-hosting.md).

## Why this exists

A 70B-parameter model at 16 bits per weight is 140 GB. To produce one token, the GPU must stream all of those weights from memory through its math units. Arithmetic is extremely fast and memory comparatively slow, so for one user generating one token at a time, the chip mostly waits. Done naively, serving recomputes the prompt at every step, leaves GPUs half-idle between requests, and fragments memory.

Inference engineering is the set of tricks that fix this. You don't run them when you call an API, but they explain your bill and your UI's pauses: why output costs more than input, why long prompts delay the first token, and why a cached prefix is cheap.

## How it works (under the hood)

### Two phases: prefill and decode

```text
Request: 2,000-token prompt → 300-token answer

PREFILL  [■■■■■■■■■■■■■■■■■■■■]  all 2,000 prompt tokens in ONE parallel pass
         builds the KV cache, emits output token 1        ← TTFT ends here
DECODE   [■] [■] [■] [■] ... 299 more passes, ONE new token each
         every pass re-reads all weights + the growing KV cache
```

- **Prefill** processes the whole prompt at once. Each weight loaded from memory is reused across thousands of tokens in large matrix-matrix multiplications, so the GPU's math units are the limit. Prefill is **compute-bound**.
- **Decode** generates one token per sequence per pass. Each weight loaded is used for only one token per sequence, so the speed of moving bytes is the limit. Decode is **memory-bandwidth-bound**.

A back-of-envelope estimate makes the gap concrete. It uses NVIDIA's H100 SXM figures: 3.35 TB/s of memory bandwidth and about 990 TFLOPS of dense FP16 math (NVIDIA lists 1,979 TFLOPS with sparsity). That chip can do roughly 300 arithmetic operations for every byte it reads. Decoding one sequence does about 2 operations (a multiply and an add) per 2-byte weight, roughly 1 per byte, so about 99% of the math capacity sits idle. Take a 70B model at 16 bits spread across two H100s:
- **Decode:** streaming 140 GB at 6.7 TB/s takes about 21 ms per step, so one sequence tops out near 48 tokens/s, however fast the math units are.
- **Prefill of 2,000 tokens:** about 2 × 70B × 2,000 = 2.8 × 10¹⁴ operations, about 0.14 s at full utilization.

These are idealized bounds that ignore attention, communication and imperfect utilization, but the shape is right: for a single sequence, an output token takes roughly 300× the GPU time of a prompt token (21 ms vs about 0.07 ms).

The fix for decode is **batching**. One pass over the weights can advance 64 sequences instead of one, at nearly the same cost per pass, until the batch becomes compute-bound or runs out of memory. Almost every other technique below exists to make bigger, fuller batches possible.

### The KV cache

At decode step t, the new token's query must attend to the keys and values of all t tokens before it. Because of the causal mask ([§02](02-how-llms-work.md)), those earlier keys and values never change once computed. Recomputing them at every step would make each step O(t) work and the whole generation O(n²). Instead, the server stores them: this store is the **KV cache**. It works like a materialized intermediate that you append to, rather than recomputing the whole table on every query.

```python
import math
import random

rng = random.Random(42)
D = 4                                                  # tiny hidden size
def rand_matrix():
    return [[rng.uniform(-1, 1) for _ in range(D)] for _ in range(D)]
WQ, WK, WV = rand_matrix(), rand_matrix(), rand_matrix()  # trained weights: fixed at inference
seq = [[rng.uniform(-1, 1) for _ in range(D)] for _ in range(50)]  # 50 token vectors
calls = {"proj": 0}                                    # counts matrix-vector products

def project(W, x):
    calls["proj"] += 1
    return [sum(w * xi for w, xi in zip(row, x)) for row in W]

def attend(q, keys, values):                           # softmax(q·k / sqrt(D)) weighted sum of v
    scores = [sum(a * b for a, b in zip(q, k)) / math.sqrt(D) for k in keys]
    w = [math.exp(s - max(scores)) for s in scores]
    return [sum(wi * v[j] for wi, v in zip(w, values)) / sum(w) for j in range(D)]

def decode_without_cache():
    outs = []
    for t in range(1, len(seq) + 1):                   # step t re-projects the whole prefix
        keys = [project(WK, x) for x in seq[:t]]
        vals = [project(WV, x) for x in seq[:t]]
        outs.append(attend(project(WQ, seq[t - 1]), keys, vals))
    return outs

def decode_with_cache():
    outs, k_cache, v_cache = [], [], []
    for x in seq:                                      # only the NEW token is projected
        k_cache.append(project(WK, x))                 # earlier K and V never change: keep them
        v_cache.append(project(WV, x))
        outs.append(attend(project(WQ, x), k_cache, v_cache))
    return outs

for fn in (decode_without_cache, decode_with_cache):
    calls["proj"] = 0
    last = fn()[-1]
    print(f"{fn.__name__:22s} projections={calls['proj']:5d}  last={[round(v, 4) for v in last]}")
```

```text
decode_without_cache   projections= 2600  last=[0.0214, -0.0059, -0.1033, -0.0217]
decode_with_cache      projections=  150  last=[0.0214, -0.0059, -0.1033, -0.0217]
```

Same outputs, 17× fewer projections, and the gap grows with the square of the length. The toy is a single layer and head fed a fixed sequence. A real model does this in every layer, and each new input vector comes from the token it just sampled.

**The price is memory.** The cache holds, for every token, 2 (K and V) × layers × KV heads × head size × bytes per number. For Llama 3 70B (80 layers, 8 KV heads of size 128, 16-bit) that is 2 × 80 × 8 × 128 × 2 bytes ≈ 320 KiB per token, or about 40 GiB for a single 128K-token context. Llama 3 already shrinks this with **grouped-query attention (GQA)**, where 8 key/value heads are shared by 64 query heads. With one KV head per query head, the cache would be eight times larger. The upshot is that KV memory, not compute, often caps how many requests a GPU can serve at once.

### Latency metrics

- **TTFT (time to first token):** request to first output token, covering network, queueing and prefill. It grows with the uncached prompt length.
- **TPOT (time per output token):** the average gap after the first token, (end-to-end latency − TTFT) / (output tokens − 1).
- **ITL (inter-token latency):** each individual gap. For one request, mean ITL equals TPOT. Across requests, benchmarks average differently, so check definitions before comparing.
- **End-to-end latency** ≈ TTFT + TPOT × (output tokens − 1).
- **Throughput:** tokens per second across all users of a server. **Goodput** counts only requests that meet their latency targets.

Throughput and per-user latency pull against each other. Bigger batches raise throughput and lower cost per token, but each decode step takes longer, so every user's TPOT rises. Which metric matters depends on the product:
- **Chat UIs** care about TTFT and TPOT. Streaming shows tokens as they arrive, which hides total time but doesn't reduce it.
- **Offline extraction** cares about throughput and price.
- **Agents** pay end-to-end latency on every step, multiplied by the number of steps.

### Batching: static vs continuous, and PagedAttention

```text
STATIC      req A ■■■■■■■■■■■■■■■■■■■■
            req B ■■■■······  done; slot idles until A finishes
            req C waits for the next batch ...
CONTINUOUS  req A ■■■■■■■■■■■■■■■■■■■■
            req B ■■■■ req C ■■■■■■■■ req D ■■■■■■   (joins/leaves every step)
```

**Static batching** groups requests and runs them until all finish. Short answers then wait on the longest one, and new arrivals wait for the next batch. **Continuous batching** (Orca, OSDI 2022, which calls it "iteration-level scheduling") rebuilds the batch after every decode step: finished sequences leave, and queued ones join immediately.

Continuous batching only pays off if memory can be packed tightly. Early servers reserved a contiguous KV region sized for each request's maximum length, which wasted memory through fragmentation and over-reservation. **PagedAttention** (Kwon et al., 2023), the core of the **vLLM** server, stores the KV cache in fixed-size blocks mapped through a per-sequence block table, like operating-system virtual memory pages. The paper reports near-zero KV waste, sharing of blocks across requests, and 2–4× higher throughput than FasterTransformer and Orca at the same latency. Some systems go further and run prefill and decode on separate GPU pools, since the two phases hit different bottlenecks (DistServe, 2024).

For you as an API caller, three things follow:
- Your request shares a GPU with strangers' requests, so latency depends on provider load.
- Batch size changes the floating-point arithmetic, which is one reason `temperature = 0` isn't reproducible.
- If you don't need an answer now, the **Batch API (GA)** gives a 50% discount on input and output, because the provider can schedule your work into gaps.

### Quantization

**Quantization** stores weights (and sometimes the KV cache) in fewer bits than the 16-bit FP16/BF16 standard: **FP8** or **INT8** (8 bits), or **INT4** (4 bits) with methods such as GPTQ and AWQ that choose how to round weights so each layer's output changes as little as possible. LLM.int8() showed that a few large "outlier" values need special handling to keep 8-bit accuracy.

The mechanism ties straight back to decode being memory-bound: half the bytes means roughly half the time per decode step, and half the memory means bigger batches or fewer GPUs. A 70B model drops from 140 GB at 16 bits to about 70 GB at 8 bits and about 35 GB at 4 bits, plus overhead for the scales. Newer GPUs such as the H100 add FP8 math units, so FP8 also speeds up compute-bound prefill. Weight-only INT4 mostly saves bandwidth, because the weights are typically converted back to 16-bit for the actual math.

The tradeoff is precision. Losses are usually small at 8 bits and more noticeable at 4 bits, especially on long reasoning chains, math and long contexts. Damage varies by model and method, so the only reliable check is your own evals ([§26](26-evals.md)). Hosted APIs don't let you choose, and providers don't always disclose what they run.

### Speculative decoding

Decode leaves math units idle, and **speculative decoding** puts them to work:
1. A small, fast **draft model** guesses the next k tokens.
2. The large model scores all k guesses in one parallel pass, at roughly the cost of generating one token, because the weights are read once.
3. A modified rejection-sampling rule accepts the longest run of guesses consistent with the large model's distribution, then the large model supplies one corrected token.

The output distribution is mathematically the same as the large model's alone. Leviathan et al. (2022) report 2–3× faster decoding on T5-XXL with identical outputs. Chen et al. (DeepMind, 2023) report 2–2.5× on the 70B Chinchilla. The speedup depends on the acceptance rate: predictable text such as boilerplate, code edits and quoted input accepts more guesses. Under heavy load, when batches are already compute-bound, the gain shrinks.

A related product dial: Anthropic's fast mode **(Preview)**, a research preview as of Oct 2026, runs Claude Opus 5.5 at up to 2.5× higher output tokens per second for $8/$40 per MTok versus the standard $4/$20. Anthropic describes it as the same model with a faster inference configuration and doesn't say which techniques it uses.

### Why output tokens cost more than input tokens

Prefill amortizes each weight read over thousands of prompt tokens. Decode gets one token per sequence per weight read, has to run sequentially, and holds a KV slot for the whole request. So an output token uses far more GPU time than an input token. As of Oct 2026, every current Claude model prices output at 5× input. Claude Sonnet 5.5, for example, costs $2 per million input tokens and $10 per million output tokens.

Consequences:
- Ask for concise outputs and use structured formats ([§06](06-structured-outputs.md)).
- Set `max_tokens` deliberately.
- Remember that reasoning tokens are billed as output ([§04](04-reasoning-models.md)).

### Why long contexts cost more

1. **Linear billing, repeated.** Every input token is billed on every call, and because the model is stateless (P2), a chat re-sends its history each turn. An N-turn conversation that adds m tokens per turn sends about m × N²/2 input tokens in total.
2. **Prefill attention grows with n²**, so TTFT climbs faster than linearly at long lengths.
3. **Every decode step reads the whole KV cache**, so TPOT rises as the context grows.
4. **KV memory per request grows with n**, so fewer requests fit on a GPU and each token costs the provider more. Some prices reflect this. Claude Haiku 5.5 charges $0.10 per million input tokens for prompts up to 100K tokens and $0.50 beyond. Current Opus and Sonnet charge one rate across the full 1M window.
5. **Quality degrades too** (P3), so a long context costs you in accuracy as well as money.

### Prompt caching: reusing the prefix (P10)

Because of the causal mask, the KV cache for a prefix depends only on the tokens in that prefix. If a new request starts with exactly the same tokens as a recent one, the server can load the stored keys and values and skip that part of prefill. vLLM's design hashes each KV block by its own tokens plus all the tokens before it. That is a hash chain, so changing one early token changes every later block's hash and nothing after it matches. OpenAI's docs add a physical detail: a request hits the cache only if it is routed to a machine that still holds the entry, and routing uses a hash of the prompt's first tokens.

Anthropic's version **(GA)** caches the prefix in the order `tools` → `system` → `messages`, up to a `cache_control` breakpoint:

```json
{
  "model": "claude-sonnet-5-5",
  "max_tokens": 1024,
  "system": [
    {"type": "text", "text": "<5,000 tokens of stable instructions and reference docs>",
     "cache_control": {"type": "ephemeral"}}
  ],
  "messages": [{"role": "user", "content": "<the part that changes every request>"}]
}
```

```json
{"usage": {"input_tokens": 42, "cache_creation_input_tokens": 0,
           "cache_read_input_tokens": 5012, "output_tokens": 230}}
```

The total prompt is `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. Here the 5,012-token prefix was read from cache, and only the last 42 tokens were processed fresh (the numbers are illustrative). Pricing as of Oct 2026:
- Writing to the cache costs 1.25× the base input price for the default 5-minute lifetime, or 2× for a 1-hour lifetime.
- Each hit refreshes the 5-minute timer.
- Reads cost 0.1× base input on most models, 0.05× on Claude Opus 5.5 and Sonnet 5.5, and 0.025× on Claude Fable 5.1.

OpenAI's shape is now similar on GPT-5.6 and later: a 1,024-token minimum, breakpoints you place or let OpenAI choose, writes at 1.25× and most reads at 0.1×. Gemini caches implicitly (4,096-token minimum on current models) and also offers explicit caches.

Design rules follow from the mechanism. Put stable content first (tools, system prompt, documents) and volatile content last (timestamps, user IDs, the question itself). Keep tool lists and JSON serialization deterministic. Caching doesn't help when prompts differ from the very first tokens, when traffic gaps exceed the cache lifetime, or when the prefix is below the provider's minimum length, which on Anthropic fails silently with no error. Check `cache_read_input_tokens` to confirm it is working.

### Putting numbers on it

```python
# USD per million tokens: Claude Sonnet 5.5 list prices, as of Oct 2026 (check the pricing page).
PRICE = {"input": 2.00, "cache_write": 2.50, "cache_read": 0.10, "output": 10.00}

# Speeds are ASSUMPTIONS for illustration. Measure your own: they vary by model, load and provider.
PREFILL_TOK_S = 10_000   # uncached input tokens processed per second (parallel, fast)
DECODE_TOK_S = 60        # output tokens generated per second (one forward pass each, slow)
OVERHEAD_S = 0.3         # network, queueing, tokenization

def estimate(input_tokens, output_tokens, cache_read=0, cache_write=0):
    """Return (cost_usd, ttft_s, total_s) for one request."""
    uncached = input_tokens - cache_read - cache_write        # billed at the full input rate
    cost = (uncached * PRICE["input"] + cache_write * PRICE["cache_write"]
            + cache_read * PRICE["cache_read"] + output_tokens * PRICE["output"]) / 1e6
    ttft = OVERHEAD_S + (input_tokens - cache_read) / PREFILL_TOK_S  # cached prefix skips prefill
    total = ttft + output_tokens / DECODE_TOK_S                      # decode dominates long outputs
    return cost, ttft, total

cases = {
    "classify: 20k in, 10 out":       dict(input_tokens=20_000, output_tokens=10),
    "draft: 500 in, 2k out":          dict(input_tokens=500, output_tokens=2_000),
    "agent turn, cold: 80k in":       dict(input_tokens=80_000, output_tokens=400,
                                           cache_write=78_000),
    "agent turn, warm: 80k in":       dict(input_tokens=80_000, output_tokens=400,
                                           cache_read=78_000, cache_write=1_500),
}
for name, kw in cases.items():
    cost, ttft, total = estimate(**kw)
    print(f"{name:28s} ${cost:.4f}  TTFT {ttft:5.2f}s  total {total:6.2f}s")

cost, _, _ = estimate(**cases["agent turn, warm: 80k in"])
print(f"100k warm agent turns per day for 30 days: ${cost * 100_000 * 30:,.0f}")
```

```text
classify: 20k in, 10 out     $0.0401  TTFT  2.30s  total   2.47s
draft: 500 in, 2k out        $0.0210  TTFT  0.35s  total  33.68s
agent turn, cold: 80k in     $0.2030  TTFT  8.30s  total  14.97s
agent turn, warm: 80k in     $0.0165  TTFT  0.50s  total   7.17s
100k warm agent turns per day for 30 days: $49,650
```

Read the shape, not the exact numbers. The classifier pays for input, while the draft pays for output and waits on decode. The warm cache cuts the agent turn's cost by about 12× and its TTFT by about 16×. The cold turn costs about 24% more than not caching at all, because of the write premium, so caching pays only when the prefix is reused.

### Failure modes

- **Silent cache misses.** A timestamp or a reordered tool list early in the prompt means every request pays full price, and nothing errors.
- **TTFT spikes under load.** Queueing at the provider adds latency that you can't fix with prompt changes, so budget for p95 and p99, not the average.
- **Truncation.** Output stops at `max_tokens` (`stop_reason: "max_tokens"`) mid-answer. Long outputs also need streaming to avoid HTTP timeouts.
- **Non-reproducibility** from batching, even with greedy decoding.

## Comparison

| Phase | What runs | Bottleneck | Drives | Your lever |
|---|---|---|---|---|
| Prefill | All uncached prompt tokens in one parallel pass | Compute (FLOPs) | TTFT, input price | Shorter prompts; prompt caching |
| Decode | One pass per output token | Memory bandwidth (weights + KV cache) | TPOT, output price | Shorter outputs; faster tier or model |

| Technique | Mechanism | Saves | Tradeoff | Who controls it |
|---|---|---|---|---|
| KV cache | Store earlier tokens' keys/values | Recomputation (O(n²) → O(n)) | GPU memory per token | Every server |
| Continuous batching | Rebuild the batch every step | Idle GPU slots | Your latency depends on others' load | Provider / your server |
| PagedAttention | KV cache in fixed-size pages | Memory waste → bigger batches | Engine complexity | Provider / vLLM |
| Quantization | Fewer bits per weight | Memory, bandwidth, GPUs | Possible quality loss; eval it | Provider / you if self-hosting |
| Speculative decoding | Draft guesses, big model verifies | Decode latency | Extra compute; gains vary with text | Provider / your server |
| Prompt caching | Reuse a prefix's KV cache | Prefill cost and TTFT | Write premium; strict prefix match | You (prompt layout) |
| Batch API | Async, provider-scheduled | 50% of the price | No immediate answer | You |

## What it didn't solve

Inference engineering made each token cheaper and faster, but it didn't change what a token can do. Each token gets one forward pass, a fixed amount of computation however hard the question is. A multi-step problem that needs more thought than one pass provides still fails, unless the model can spend more tokens working it out before answering. That idea, test-time compute, produced reasoning models.

→ Next: [§04 Reasoning Models and Test-Time Compute](04-reasoning-models.md)

## Check your understanding

**Q: Why is decode memory-bandwidth-bound while prefill is compute-bound?**

Prefill reuses each loaded weight across thousands of prompt tokens, so math is the limit. Decode reloads every weight to make one token per sequence, so memory speed is the limit. That is why providers batch many users' decode steps together, until batches turn compute-bound or the KV cache fills memory.

**Q: What would happen if a server did not keep a KV cache?**

Every step would recompute keys and values for the whole prefix: O(n²) projections per generation instead of O(n). Outputs would be identical, only much slower. The cache trades memory for that compute, and at long contexts that memory caps how many requests fit on a GPU.

**Q: Why are output tokens priced higher than input tokens?**

An input token shares a weight read with thousands of others during prefill, while an output token needs its own sequential pass and holds a KV slot until the request finishes. More GPU time per token means a higher price (5× on current Claude models). For output-heavy work, shortening the answer saves more than trimming the prompt.

**Q: TTFT vs TPOT: which should you optimize for a chat UI, and which for a nightly batch job?**

A chat UI needs low TTFT so a response visibly starts, and a TPOT low enough that streaming reads smoothly. A nightly job cares about neither; it needs throughput and price, so the Batch API's 50% discount fits. Agents pay end-to-end latency on every step, so total time matters most.

**Q: What would happen to your cache hit rate if you put the current timestamp at the top of the system prompt?**

It would drop to zero. Caching matches exact prefixes, and a changed first line changes every later block's hash, so every request pays full prefill price and TTFT. Nothing errors, so it can go unnoticed. Put volatile values after the last breakpoint and monitor `cache_read_input_tokens`.

**Q: Why does quantization speed up generation, and when should you avoid it?**

Decode is limited by bytes moved, so fewer bits per weight means less data per step and more room for batching. The cost is precision, which tends to show on long reasoning, math and long contexts. Avoid aggressive quantization when your evals show degradation, or when quality matters more than serving cost.

**Q: Why doesn't speculative decoding change the model's output?**

The large model checks every drafted token with a rejection-sampling rule that preserves its own distribution, and supplies the correction at the first mismatch, so the draft changes only speed. Speedups depend on how often drafts are accepted, and they shrink when batches are already compute-bound.

## Takeaways

- Prefill is parallel and compute-bound; decode is sequential and memory-bandwidth-bound (P10).
- The KV cache trades memory for compute, and KV memory often limits how many requests a GPU can serve.
- Batching is the core economic lever; continuous batching and PagedAttention keep batches full.
- Output tokens cost more because each one needs its own sequential pass (5× input on current Claude models).
- Long contexts cost more four ways: billing, n² prefill, slower decode steps, and fewer requests per GPU.
- Prompt caching reuses a prefix's KV cache, so put stable content first and volatile content last.
- Quantization and speculative decoding buy speed; quantization can cost quality, speculative decoding cannot.
- Measure TTFT, TPOT and cost per request, and estimate before you build.

## Sources

- Kwon et al., "Efficient Memory Management for LLM Serving with PagedAttention" (2023): https://arxiv.org/abs/2309.06180
- Yu et al., "Orca: A Distributed Serving System for Transformer-Based Generative Models" (OSDI 2022): https://www.usenix.org/conference/osdi22/presentation/yu
- Zhong et al., "DistServe: Disaggregating Prefill and Decoding" (2024): https://arxiv.org/abs/2401.09670
- Leviathan et al., "Fast Inference from Transformers via Speculative Decoding" (2022): https://arxiv.org/abs/2211.17192
- Chen et al., "Accelerating LLM Decoding with Speculative Sampling" (2023): https://arxiv.org/abs/2302.01318
- Ainslie et al., "GQA" (2023): https://arxiv.org/abs/2305.13245
- Shazeer, "Fast Transformer Decoding: One Write-Head is All You Need" (MQA, 2019): https://arxiv.org/abs/1911.02150
- Dettmers et al., "LLM.int8()" (2022): https://arxiv.org/abs/2208.07339
- Frantar et al., "GPTQ" (2022): https://arxiv.org/abs/2210.17323
- Lin et al., "AWQ" (2023): https://arxiv.org/abs/2306.00978
- Micikevicius et al., "FP8 Formats for Deep Learning" (2022): https://arxiv.org/abs/2209.05433
- Llama Team, "The Llama 3 Herd of Models" (2024), architecture table: https://arxiv.org/abs/2407.21783
- vLLM, prefix caching design doc: https://github.com/vllm-project/vllm/blob/main/docs/design/prefix_caching.md
- vLLM documentation: https://docs.vllm.ai
- BentoML LLM Inference Handbook (metrics, batching, prefill/decode): https://bentoml.com/llm/
- NVIDIA H100 specifications: https://www.nvidia.com/en-us/data-center/h100/
- Anthropic, Prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Anthropic, Pricing (output, cache, batch, long-context rates): https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic, Fast mode: https://platform.claude.com/docs/en/build-with-claude/fast-mode
- OpenAI, Prompt caching: https://developers.openai.com/api/docs/guides/prompt-caching
- Google, Gemini context caching: https://ai.google.dev/gemini-api/docs/caching
- Thinking Machines Lab, "Defeating Nondeterminism in LLM Inference" (2025): https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
