# 31. Open-Weight Models and Self-Hosting

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

The open-weight story starts with Meta's LLaMA (Feb 2023), released to researchers, whose weights leaked publicly within weeks. Llama 2 (Jul 2023) allowed commercial use, and Mistral 7B (Sep 2023) shipped under Apache 2.0. From 2024 the wave broadened: DeepSeek-V3 (Dec 2024) and R1 (Jan 2025), OpenAI's gpt-oss (Aug 2025), and, as of Oct 2026, active families from Qwen, DeepSeek, Mistral, Google's Gemma, Moonshot's Kimi, Z.ai's GLM, NVIDIA's Nemotron and IBM's Granite. Meta's newest Llama release on Hugging Face is still Llama 4 (Apr 2025). [§30](30-cost-latency-reliability.md) left a problem: past some scale, or under strict privacy rules, renting someone else's model stops making sense. This section is about running the model yourself. It leans on P10 (the serving economics), P5 (fine-tunes need weights), P11 (the interface that makes models swappable) and P12 (whatever you host will be superseded within months).

## Why this exists

A hosted API gives you a function you can call but never hold. Your prompts and data go to a third party. You accept its prices, rate limits, regions and retirement schedule, and you can fine-tune only if it offers that at all: as of Oct 2026 Anthropic's API has no self-serve fine-tuning and OpenAI is winding its own down ([§29](29-adapting-models.md)). Open weights hand you the function itself (P1): a file of parameters that runs anywhere you have enough memory.

Reasons to self-host:
- **Privacy and data residency.** Data never leaves your network, which may be the only option for some regulated, contractual or air-gapped workloads.
- **Cost at scale.** Once a GPU is busy most of the time, a token costs what the hardware and power cost, with no margin on top.
- **Control and latency.** You can pin an exact version forever, colocate the model with your data, set your own batch sizes and decoding, and you have no shared rate limit.
- **Fine-tunes.** LoRA adapters and full fine-tunes ([§29](29-adapting-models.md)) can be served cheaply, often many adapters on one base model. With closed providers mostly not offering or closing hosted fine-tuning, open weights (self-hosted or on a specialized provider) are where most fine-tuning now happens.
- **Offline and edge.** Laptops, factories, ships and phones.

Reasons not to:
- **Ops burden.** You now run a GPU service with on-call, capacity planning, upgrades and monitoring.
- **GPU cost at low utilization.** A rented GPU bills every hour whether or not anyone is calling it.
- **Capability gap.** The best open models trail the best closed ones on many hard tasks. Whether the gap matters for *your* task is an eval question, not a leaderboard question.
- **Security patching.** Serving engines have vulnerabilities, model files are a supply chain, and safety behavior is yours to verify.

## How it works (under the hood)

### "Open weights" is not "open source"

What you usually download: the weights (typically in the `safetensors` format), a config describing the architecture, the tokenizer, a chat template, a model card and a license. What you usually don't get: the training data, the full training code or the RL environments. You can run, fine-tune and inspect the model, but you can't rebuild it.

The Open Source Initiative's Open Source AI Definition 1.0 (Oct 2024) requires all three: "Data Information" detailed enough that "a skilled person can build a substantially equivalent system", the complete training and inference code, and the parameters. By that test most "open" LLMs are **open-weight**, not open source. AI2's OLMo family is a notable exception that publishes data and code too.

The license decides what you may do. Read the one on each checkpoint's model card, because terms vary within a single family:

| License type (examples, Oct 2026) | What it allows | Watch for |
|---|---|---|
| Apache 2.0 (most Qwen 3.x checkpoints, gpt-oss, Gemma 4, Mistral Small 4) | Commercial use, modification, redistribution | Attribution and notice files; patent terms |
| MIT (DeepSeek V4, GLM-5 to GLM-5.2, GLM-5.3-Flash) | Nearly anything | Attribution |
| Custom licenses (Llama 4, Kimi, GLM-5.3, Mistral Medium 3.5, Qwen3.8-2.4T and Qwen3.8-Flash-Next) | Varies, from broad commercial use with conditions to narrower terms | Llama 4: a separate license from Meta above 700 million monthly active users, "Built with Llama" display, derivative names must start with "Llama", plus an acceptable-use policy |

One consequence is easy to miss: the file you downloaded never changes underneath you. That is great for reproducibility, but it also means no safety fixes arrive unless you pull and re-evaluate a new release.

Many current open models are **mixture-of-experts (MoE)**: each token runs through only a few "expert" sub-networks. gpt-oss-120b has 117B parameters but 5.1B active per token. For serving, that splits the cost: *memory* scales with total parameters, because every expert must be loaded, while *compute per token* scales with active parameters.

### Serving engines: §03 as software

A serving engine is the server side of [§03](03-inference.md) packaged as a program. The mechanisms are the same, and now you configure them:

```text
HTTP (OpenAI- / Anthropic-compatible) ──► scheduler ─────────► model executor (GPUs)
   requests stream in                    │ continuous batching   │ tensor/expert parallel
                                         │ chunked prefill       │ quantized kernels
                                         ▼                       │ speculative decoding
                                   KV block manager ◄────────────┘
                                   │ PagedAttention: KV in fixed-size pages
                                   │ prefix cache: reuse pages for shared prefixes
```

- **vLLM** is the default choice for GPU serving. Its README lists PagedAttention, "continuous batching of incoming requests, chunked prefill, prefix caching", FP8, INT8, INT4, GPTQ/AWQ, GGUF and newer 4-bit formats, speculative decoding (including EAGLE), tensor, pipeline and expert parallelism, and an "OpenAI-compatible API server, plus Anthropic Messages API". At startup it reserves a fixed share of GPU memory (`gpu_memory_utilization`, default 0.92) and fills what the weights don't use with KV-cache pages.
- **SGLang** adds **RadixAttention**: it keeps KV caches of past requests in a radix tree (a prefix tree), so any new request that shares a prefix with *any* earlier one reuses it automatically. That suits agents, few-shot prompts and tree-of-thought style branching. The 2023 paper reports up to 6.4× higher throughput than prior systems on such workloads, and the project positions itself for "agentic workloads, large-scale serving, and RL rollouts."
- **TGI** (Hugging Face Text Generation Inference) "is now in maintenance mode." Hugging Face recommends vLLM, SGLang, llama.cpp or MLX instead.
- **llama.cpp** is a C/C++ engine that runs on CPUs, consumer GPUs and Apple silicon ("a first-class citizen"), with 1.5- to 8-bit integer quantization and the single-file **GGUF** format. `llama-server` exposes an HTTP API.
- **Ollama** wraps llama.cpp-style local serving in a model registry and one-line installs, and exposes subsets of the OpenAI and Anthropic APIs.
- **LM Studio** is a desktop app with a local server, OpenAI- and Anthropic-compatible endpoints, and a headless mode.

The split is GPU fleet serving (vLLM, SGLang) versus local single-user use (llama.cpp, Ollama, LM Studio). Local tools optimize for fitting one model on one machine. Fleet engines optimize for batching many users onto expensive GPUs.

```bash
# Serve an open-weight model with vLLM (needs a GPU with enough memory; see the estimator below)
vllm serve openai/gpt-oss-120b --api-key "$VLLM_API_KEY"

# Any OpenAI-style client can now call it...
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $VLLM_API_KEY" -H "Content-Type: application/json" \
  -d '{"model": "openai/gpt-oss-120b", "messages": [{"role": "user", "content": "Hi"}]}'

# ...and vLLM also serves the Anthropic Messages shape at /v1/messages
```

Treat that server as an internal service, not an internet endpoint. vLLM's own docs warn that `--api-key` only protects some path prefixes, and that other endpoints such as `/invocations` are not authenticated, so put it behind a gateway or reverse proxy ([§30](30-cost-latency-reliability.md)).

### Quantization formats and their tradeoffs

[§03](03-inference.md) explains why fewer bits per weight speeds up memory-bound decode. In practice you meet the method and the file format together:

- **FP8** (8-bit floating point, weights and often activations): uses the FP8 math units on H100-class and newer GPUs, so it speeds up prefill as well as decode.
- **GPTQ** rounds weights to INT4 (or INT3) layer by layer, using a small calibration set to minimize each layer's output error.
- **AWQ** (activation-aware weight quantization) starts from the observation that "protecting only 1% salient weights can greatly reduce quantization error". It finds those channels from activation statistics and scales them up before rounding, so everything can still be stored in INT4 without mixed precision. Both GPTQ and AWQ are mostly *weight-only*: weights are stored in 4 bits and expanded to 16 bits for the math, which saves memory and bandwidth.
- **GGUF** is a container format, not a single method: a single file with metadata and memory-mappable tensors, designed for llama.cpp. It carries llama.cpp's own quantization types, such as `Q8_0` or `Q4_K_M`, optionally tuned with an "importance matrix" from calibration data.
- **MXFP4 / NVFP4** are newer 4-bit floating-point formats with hardware support on recent GPUs; gpt-oss ships with its MoE weights in MXFP4.

How much quality do you lose? A study that calls itself the most comprehensive to date (Kurtic et al., more than 500,000 evaluations on the Llama 3.1 family) found FP8 "effectively lossless across all model scales", well-tuned INT8 at "1-3%" degradation, and INT4 weight-only "more competitive than expected, rivaling 8-bit". It recommended W4A16 for latency-bound serving and W8A8 for high-throughput continuous batching. Treat that as a prior, not a guarantee. Losses vary by model and method, tend to show first on long reasoning, math and long contexts, and only your eval on your task settles it ([§26](26-evals.md)). Quantizing the KV cache to 8 bits is a separate dial that halves cache memory.

### GPU memory math: weights plus KV cache

What must fit in GPU memory is the weights, plus the KV cache for every token of every sequence in flight, plus working overhead. The KV formula is from [§03](03-inference.md): 2 (K and V) × layers × KV heads × head size × bytes per value, per token.

```python
import math

GIB = 2**30
WEIGHT_BYTES = {"bf16": 2.0, "fp8": 1.0, "int4": 0.5}   # per parameter; INT4 scales add a few % more

def kv_bytes_per_token(layers, kv_heads, head_dim, kv_bytes):
    return 2 * layers * kv_heads * head_dim * kv_bytes   # K and V, in every layer (see §03)

def estimate(params_b, wfmt, layers, kv_heads, head_dim, ctx, batch,
             kv_bytes=2, gpu_gib=80, mem_util=0.92, overhead=0.10):
    weights = params_b * 1e9 * WEIGHT_BYTES[wfmt]
    kv = kv_bytes_per_token(layers, kv_heads, head_dim, kv_bytes) * ctx * batch
    need = (weights + kv) * (1 + overhead)    # activations, CUDA graphs, fragmentation: an ASSUMPTION
    usable = gpu_gib * GIB * mem_util         # vLLM's default gpu_memory_utilization is 0.92
    return weights / GIB, kv / GIB, math.ceil(need / usable)

# Llama-3-70B-shaped dense model: 80 layers, 8 KV heads (GQA), head size 128
SHAPE = dict(params_b=70, layers=80, kv_heads=8, head_dim=128)
for wfmt, kvb, ctx, batch in [("bf16", 2, 8_192, 1), ("bf16", 2, 32_768, 16),
                              ("fp8", 2, 32_768, 16), ("int4", 2, 32_768, 16),
                              ("int4", 1, 32_768, 16)]:
    w, kv, gpus = estimate(wfmt=wfmt, kv_bytes=kvb, ctx=ctx, batch=batch, **SHAPE)
    print(f"weights {wfmt:4s} KV {kvb}B  ctx {ctx:>6,} x batch {batch:>2}: "
          f"weights {w:5.1f} GiB + KV {kv:5.1f} GiB -> {gpus} x 80 GB GPU")
```

```text
weights bf16 KV 2B  ctx  8,192 x batch  1: weights 130.4 GiB + KV   2.5 GiB -> 2 x 80 GB GPU
weights bf16 KV 2B  ctx 32,768 x batch 16: weights 130.4 GiB + KV 160.0 GiB -> 5 x 80 GB GPU
weights fp8  KV 2B  ctx 32,768 x batch 16: weights  65.2 GiB + KV 160.0 GiB -> 4 x 80 GB GPU
weights int4 KV 2B  ctx 32,768 x batch 16: weights  32.6 GiB + KV 160.0 GiB -> 3 x 80 GB GPU
weights int4 KV 1B  ctx 32,768 x batch 16: weights  32.6 GiB + KV  80.0 GiB -> 2 x 80 GB GPU
```

Three lessons follow:
1. **At serving scale the KV cache, not the weights, dominates.** Sixteen concurrent 32K-token sequences need more memory than the 16-bit weights. Quantizing weights alone gets you from 5 GPUs to 3; quantizing the KV cache too gets you to 2.
2. **The worst case is pessimistic.** PagedAttention allocates pages as sequences grow, so real traffic with shorter contexts fits more. The engine preempts or queues requests when pages run out, which shows up as latency spikes rather than crashes.
3. **Round up to what parallelism allows.** Tensor parallelism splits each layer across GPUs, and the split usually has to divide the attention heads evenly, so "5 GPUs" becomes 8 in practice.

Architecture changes the KV term a lot. gpt-oss-120b's config has 36 layers with 8 KV heads of size 64, and every other layer uses a 128-token sliding window. Only the 18 full-attention layers grow with context, so its KV cost is about 36 KiB per token against about 320 KiB for Llama 3 70B. That, plus MXFP4 MoE weights, is how a 117B-parameter model fits "into a single 80GB GPU", in OpenAI's words.

### Hosted open-weight models: the middle path

You can get open weights without running GPUs:
- **Cloud platforms.** Amazon Bedrock added 18 fully managed open-weight models in Dec 2025 and more in Feb 2026. Google Cloud's Model Garden serves open models such as DeepSeek, GLM and Llama as managed APIs. Microsoft Foundry's catalog also sells open-weight models such as gpt-oss, DeepSeek V4 and Qwen 3.x.
- **Inference APIs** such as Together, Fireworks, Groq, Cerebras, Baseten, DeepInfra and Hugging Face Inference Providers, often reached through OpenRouter.
- **Dedicated endpoints**, where a provider runs your chosen checkpoint (or fine-tune) on reserved GPUs, sit between serverless and self-hosting.

You get per-token pricing, no ops, and an exit: the same weights can later move in-house. Your data still leaves your network, so read each provider's retention terms. Also check *which* build the provider serves. OpenRouter lets you filter providers by quantization level, a reminder that two providers of "the same model" may run different precisions, context limits and chat templates, and can score differently on your eval.

### OpenAI-compatible APIs as the de facto interface (P11)

Without a common interface, N applications × M serving stacks means N×M integrations. The OpenAI Chat Completions request shape became the shared envelope: vLLM, SGLang, llama.cpp's server, Ollama, LM Studio, gateways like LiteLLM and OpenRouter, and most hosted providers accept it. Anthropic and Google offer OpenAI-compatible endpoints too, though Anthropic describes its layer as "primarily intended to test and compare model capabilities", not a long-term production path. By 2026 the Anthropic Messages shape is a second common envelope (vLLM, Ollama and LM Studio serve it), so tools built for Claude, such as coding agents, can point at a local model by changing a base URL.

Compatible doesn't mean identical. The envelope is standard, but the behavior inside it isn't:
- Tool-calling reliability differs by model.
- Chat templates differ: gpt-oss "should only be used with the harmony format."
- Reasoning fields, structured-output support and caching semantics vary by server.

Swapping a base URL takes a minute. Proving the new model still does the job takes an eval.

### Break-even analysis: API vs self-hosting

The fair comparison is the *same* open model on a hosted API vs on your GPUs. Comparing a self-hosted open model with a frontier API compares price and capability at once.

```python
import math

HOURS = 730                                  # hours in a month
# ASSUMPTIONS for illustration only. Replace every number with your own quotes and benchmarks.
HOSTED_OPEN = {"in": 0.15, "out": 0.60}      # $/MTok: same open model on a hosted inference API
FRONTIER = {"in": 2.00, "out": 10.00}        # $/MTok: Claude Sonnet 5.5 list price, Oct 2026
GPU_HOUR = 3.00                              # $/hour for one rented 80 GB-class GPU
TOK_S_PER_GPU = 2_500                        # output tok/s one GPU sustains at your latency target
OPS_MONTH = 15_000                           # $/month of engineer time: on-call, upgrades, patching
MIN_GPUS = 2                                 # one replica is not high availability

def api(price, m_in, m_out):                 # m_* = millions of tokens per month
    return m_in * price["in"] + m_out * price["out"]

def self_host(m_out, peak_to_avg):
    avg_tok_s = m_out * 1e6 / (HOURS * 3600)
    gpus = max(MIN_GPUS, math.ceil(avg_tok_s * peak_to_avg / TOK_S_PER_GPU))  # size for the peak
    return gpus * GPU_HOUR * HOURS + OPS_MONTH, gpus, avg_tok_s / (gpus * TOK_S_PER_GPU)

print(f"{'out MTok/mo':>11} {'hosted open':>12} {'frontier':>10} {'self (spiky)':>13} "
      f"{'self (flat)':>12}  GPUs/util spiky")
for m_out in (100, 1_000, 10_000, 50_000, 200_000):
    m_in = 3 * m_out                          # assume 3 input tokens per output token
    spiky, gpus, util = self_host(m_out, peak_to_avg=3.0)   # interactive traffic
    flat, _, _ = self_host(m_out, peak_to_avg=1.2)           # batch-like, steady traffic
    print(f"{m_out:>11,} {api(HOSTED_OPEN, m_in, m_out):>12,.0f} {api(FRONTIER, m_in, m_out):>10,.0f}"
          f" {spiky:>13,.0f} {flat:>12,.0f}  {gpus:>4} / {util:.0%}")
```

```text
out MTok/mo  hosted open   frontier  self (spiky)  self (flat)  GPUs/util spiky
        100          105      1,600        19,380       19,380     2 / 1%
      1,000        1,050     16,000        19,380       19,380     2 / 8%
     10,000       10,500    160,000        25,950       19,380     5 / 30%
     50,000       52,500    800,000        65,370       36,900    23 / 33%
    200,000      210,000  3,200,000       216,480       96,030    92 / 33%
```

Read the shape, not the dollars:
- **Utilization is the dial.** A GPU sized for peak traffic idles the rest of the time, so spiky interactive load runs at about a third utilization and never beats the hosted API in this toy. Hosted providers pool many customers' peaks, which is how they run busy GPUs and still make a margin. Flat, batch-like load beats the hosted API somewhere past roughly 20 billion output tokens a month here.
- **Fixed costs dominate small deployments.** Two GPUs for redundancy plus engineer time cost about $19k a month before the first token.
- **Against the frontier API, self-hosting looks cheap early,** at around 1–2 billion output tokens a month here. But that compares different models, so it only counts if your eval says the open model is good enough.
- **Hidden costs** the toy ignores: GPU availability and quotas, slow scale-up (loading 100+ GB of weights takes minutes, so you keep warm spare capacity), evals for every model upgrade, and the security work below.

A data engineer will recognize the choice between owning a cluster and paying for serverless. Owned capacity wins only when you keep it busy.

### Evaluating open models on your tasks

Public leaderboards measure someone else's tasks, sometimes with contaminated test sets. Evaluate the exact thing you will run:
1. **Fix the full stack:** checkpoint, revision, quantization, engine version, chat template and sampling settings. Any one of them can move scores.
2. **Use your eval set** ([§26](26-evals.md)), built from real traffic and failure cases, and compare against your current API model on cost per completed task.
3. **Test the agent-critical behaviors separately:** tool-call validity, structured-output conformance, instruction following at long context, and refusal and jailbreak behavior. Open weights can be fine-tuned to remove safety training, so verify what you deploy ([§32](32-security-guardrails.md)).
4. **Load-test at your concurrency.** Measure TTFT and TPOT at p95 and goodput, not single-request speed ([§03](03-inference.md)).
5. **Re-run on every upgrade.** New open models arrive every few months (P12), and a pipeline that makes swapping cheap is worth more than any single choice.

### Failure modes

- **Chat template mismatch:** the model runs but answers badly, because the prompt isn't in the format it was trained on.
- **Quantization surprise:** benchmarks look fine, but your long-reasoning task degrades.
- **KV exhaustion under load:** preemptions and queueing push p99 latency far above the demo's.
- **Unpinned revisions:** a model repo updates, and behavior changes underneath you.
- **Supply-chain risk:** pickle-based checkpoints can execute code on load (prefer `safetensors`), and "trust remote code" options run code from the model repository.
- **Exposed endpoints:** an unauthenticated inference port on the internet is free compute for someone else.
- **License drift:** a derivative model shipped under the wrong terms.

## Comparison

| Option | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Frontier API | Provider's closed model, per token | Best capability, zero ops | Data leaves; prices, limits and retirements are theirs | Capability matters most, or volume is modest |
| Hosted open-weight API | Provider serves an open model | Cheap tokens, no ops, can exit to self-hosting | Data still leaves; builds vary by provider | You want open models without GPUs |
| Dedicated endpoint | Provider runs your checkpoint on reserved GPUs | Your fine-tune, isolation | Pay for idle time | Custom models at steady volume |
| Self-host (vLLM/SGLang) | Your GPUs, your engine | Privacy, control, lowest cost at high utilization | Ops, security, capacity planning | Strict data rules, or large flat volume |
| Local (llama.cpp/Ollama/LM Studio) | One machine, quantized GGUF | Offline, private, free per token | Small models, one user | Development, edge, personal use |

| Engine | Core mechanism | Best at | Note |
|---|---|---|---|
| vLLM | PagedAttention, continuous batching, prefix caching | General GPU serving at scale | OpenAI and Anthropic-compatible APIs |
| SGLang | RadixAttention prefix tree for KV reuse | Agentic, branching and shared-prefix workloads; RL rollouts | Also OpenAI-compatible |
| TGI | Continuous batching server | Existing deployments | Maintenance mode; HF recommends vLLM/SGLang |
| llama.cpp / Ollama / LM Studio | CPU/GPU/Apple-silicon kernels, GGUF | Local and edge | Single-user throughput |

| Format | Bits | Kind | Quality (Llama 3.1 study) | Typical use |
|---|---|---|---|---|
| FP8 | 8 | Weights + activations | Effectively lossless | H100-class GPU serving |
| INT8 (W8A8) | 8 | Weights + activations | 1–3% degradation | High-throughput batching |
| GPTQ / AWQ (W4A16) | 4 | Weight-only | Competitive with 8-bit | Latency-bound or memory-tight serving |
| GGUF `Q4_K_M`, `Q8_0`, ... | 1.5–8 | Weight-only, block-wise | Not covered by the study; eval it | llama.cpp, Ollama, local |

## What it didn't solve

Self-hosting decides where the model runs and who sees the data, but it doesn't make the model trustworthy. Instructions and data still share one channel (P9). An agent with tools can read a poisoned web page or document and be steered into leaking data or taking actions you never intended, whether the weights sit in your basement or a provider's cloud. With self-hosting, the guardrails the provider used to supply become your job too.

→ Next: [§32 Security and Guardrails](32-security-guardrails.md)

## Check your understanding

**Q: Why is a model with downloadable weights usually called "open-weight" rather than "open source"?**

You get the parameters, a config and a tokenizer, so you can run and fine-tune the model, but usually not the training data or full training code, so you can't rebuild or fully audit it. The OSI's Open Source AI Definition requires data information, code and parameters. The practical consequence is in the license, which can still restrict use, as Llama 4's 700-million-user clause does.

**Q: Why does the KV cache, not the weights, often decide how many GPUs you need?**

Weights are a fixed cost, but the KV cache grows with context length times concurrent sequences, and a 70B dense model needs about 320 KiB per token. Sixteen 32K-token sequences need about 160 GiB, more than the 16-bit weights. Architectures with fewer KV heads or sliding-window layers, and 8-bit KV caches, shrink that term.

**Q: What would happen if you sized self-hosted GPUs for peak traffic on a spiky interactive workload?**

The GPUs would sit mostly idle off-peak, so you pay for capacity you use perhaps a third of the time, and cost per token ends up above a hosted API that pools many customers' peaks. Self-hosting wins on cost with flat, high-utilization load, such as batch jobs, or when privacy forces it regardless of price.

**Q: GPTQ/AWQ vs FP8: when would you pick each?**

FP8 quantizes weights and activations to 8-bit floats, uses H100-class FP8 math, and is effectively lossless in the largest study, so it is a safe default on new GPUs. GPTQ and AWQ store weights in 4 bits and expand them for the math, halving memory again and helping latency-bound serving, at a small, task-dependent quality risk. Choose 4-bit when memory is the constraint, and confirm with your own eval.

**Q: Why isn't an "OpenAI-compatible" endpoint a guarantee that your app will work on a new model?**

Compatibility standardizes the request and response envelope (P11), not the behavior inside it. Tool-call reliability, chat templates, reasoning fields and structured-output support differ by model and server. Swapping the base URL is quick, but you still have to re-run your evals.

**Q: Hosted open-weight API vs self-hosting the same model: what does self-hosting actually buy you?**

The weights and quality can be identical, so you are buying where it runs: data stays in your network, versions stay pinned, and you control latency and batching. Price is only better at high utilization. If privacy isn't a constraint and load is spiky, the hosted API is usually cheaper and simpler.

**Q: Why serve an MoE model like gpt-oss-120b when its memory footprint is set by 117B parameters?**

Every expert must sit in memory, but each token runs only about 5.1B active parameters, so per-token compute and bandwidth look like a small model's. That gives large-model knowledge with small-model speed per token, provided you can afford the memory. If memory is the binding constraint, a smaller dense model may serve you better.

## Takeaways

- Open weights give you the function itself; open source would also give you the data and code. Read each checkpoint's license.
- Self-host for privacy, control, fine-tunes and offline use. Cost wins only at high, steady utilization.
- A serving engine is §03 as software: continuous batching, paged KV cache, prefix caching, quantized kernels.
- GPU memory = weights + KV cache (context × concurrency) + overhead; at scale the KV cache dominates.
- FP8 is nearly free in quality; 4-bit is often fine but must be checked on your task.
- Hosted open-weight APIs are the middle path, with an exit to self-hosting.
- OpenAI- and Anthropic-compatible endpoints make models swappable (P11); evals make swaps safe.
- Compare self-hosting against the same model hosted, not against a different frontier model.

## Sources

- Touvron et al., "LLaMA" (Feb 2023): https://arxiv.org/abs/2302.13971
- Touvron et al., "Llama 2" (Jul 2023): https://arxiv.org/abs/2307.09288
- Jiang et al., "Mistral 7B" (2023): https://arxiv.org/abs/2310.06825
- DeepSeek-AI, "DeepSeek-V3 Technical Report" (Dec 2024): https://arxiv.org/abs/2412.19437
- OpenAI, gpt-oss-120b model card and config: https://huggingface.co/openai/gpt-oss-120b
- Meta, Llama 4 Community License: https://www.llama.com/llama4/license/
- Google, Gemma 4 license (Apache 2.0): https://ai.google.dev/gemma/docs/gemma_4_license
- Publisher model listings on Hugging Face (release dates and license tags, checked Oct 2026): https://huggingface.co/meta-llama , https://huggingface.co/Qwen , https://huggingface.co/deepseek-ai , https://huggingface.co/mistralai , https://huggingface.co/google , https://huggingface.co/moonshotai , https://huggingface.co/zai-org , https://huggingface.co/allenai
- Open Source Initiative, Open Source AI Definition 1.0: https://opensource.org/ai/open-source-ai-definition
- Kwon et al., "Efficient Memory Management for LLM Serving with PagedAttention" (2023): https://arxiv.org/abs/2309.06180
- vLLM README: https://github.com/vllm-project/vllm ; OpenAI-compatible server docs (endpoints, Anthropic Messages API, `--api-key` limits): https://github.com/vllm-project/vllm/blob/main/docs/serving/online_serving/openai_compatible_server.md ; `gpu_memory_utilization` default: https://github.com/vllm-project/vllm/blob/main/vllm/config/cache.py
- Zheng et al., "SGLang: Efficient Execution of Structured Language Model Programs" (2023): https://arxiv.org/abs/2312.07104 ; https://github.com/sgl-project/sglang
- Hugging Face, Text Generation Inference (maintenance mode notice): https://huggingface.co/docs/text-generation-inference/index
- llama.cpp: https://github.com/ggml-org/llama.cpp ; GGUF specification: https://github.com/ggml-org/ggml/blob/master/docs/gguf.md
- Ollama, OpenAI compatibility: https://docs.ollama.com/api/openai-compatibility ; Anthropic compatibility: https://docs.ollama.com/api/anthropic-compatibility
- LM Studio developer docs: https://lmstudio.ai/docs/developer
- Frantar et al., "GPTQ" (2022): https://arxiv.org/abs/2210.17323
- Lin et al., "AWQ" (2023): https://arxiv.org/abs/2306.00978
- Kurtic et al., "'Give Me BF16 or Give Me Death'? Accuracy-Performance Trade-Offs in LLM Quantization" (2024): https://arxiv.org/abs/2411.02355
- AWS, "Amazon Bedrock adds 18 fully managed open weight models" (Dec 2025): https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-bedrock-fully-managed-open-weight-models/
- AWS, "Amazon Bedrock adds support for six fully-managed open weights models" (Feb 10, 2026): https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-bedrock-adds-support-six-open-weights-models/
- Google Cloud, open models as managed APIs (Model Garden MaaS): https://cloud.google.com/vertex-ai/generative-ai/docs/maas/use-open-models
- Microsoft, Foundry Models sold by Azure (gpt-oss, DeepSeek, Qwen and other open-weight models): https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure
- Hugging Face, Inference Providers: https://huggingface.co/docs/inference-providers/index
- OpenRouter, Provider selection (including quantization filters): https://openrouter.ai/docs/guides/routing/provider-selection
- Anthropic, OpenAI SDK compatibility: https://platform.claude.com/docs/en/api/openai-sdk
- Google, Gemini OpenAI compatibility: https://ai.google.dev/gemini-api/docs/openai
