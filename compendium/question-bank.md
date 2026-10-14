# Question Bank (Self-Test)

Every "Check your understanding" question in the compendium, grouped by section. Answers are hidden: answer in your own words first, then expand to compare.
Grade yourself on whether you named the **mechanism** and the **principle** behind it ([§01](01-first-principles.md)), not on matching the wording.

**262 questions.**

- [01. First Principles: Why AI Engineering Exists](#01-first-principles-why-ai-engineering-exists) — 8 questions · [read section](01-first-principles.md)
- [02. How an LLM Works](#02-how-an-llm-works) — 6 questions · [read section](02-how-llms-work.md)
- [03. Inference Under the Hood](#03-inference-under-the-hood) — 7 questions · [read section](03-inference.md)
- [04. Reasoning Models and Test-Time Compute](#04-reasoning-models-and-test-time-compute) — 7 questions · [read section](04-reasoning-models.md)
- [05. The API and Prompt Engineering](#05-the-api-and-prompt-engineering) — 7 questions · [read section](05-api-and-prompting.md)
- [06. Structured Outputs and Constrained Decoding](#06-structured-outputs-and-constrained-decoding) — 6 questions · [read section](06-structured-outputs.md)
- [07. Multimodal Models and Documents](#07-multimodal-models-and-documents) — 6 questions · [read section](07-multimodal.md)
- [08. Embeddings and Search](#08-embeddings-and-search) — 6 questions · [read section](08-embeddings-and-search.md)
- [09. Retrieval-Augmented Generation (RAG)](#09-retrieval-augmented-generation-rag) — 7 questions · [read section](09-rag.md)
- [10. Tool Use and Tool Design](#10-tool-use-and-tool-design) — 7 questions · [read section](10-tool-use.md)
- [11. Agents and the Agent Loop](#11-agents-and-the-agent-loop) — 7 questions · [read section](11-agents.md)
- [12. Agentic Design Patterns](#12-agentic-design-patterns) — 6 questions · [read section](12-agentic-design-patterns.md)
- [13. Multi-Agent Systems](#13-multi-agent-systems) — 6 questions · [read section](13-multi-agent.md)
- [14. Graph Engineering: Orchestration as State Machines](#14-graph-engineering-orchestration-as-state-machines) — 7 questions · [read section](14-graph-engineering.md)
- [15. Protocols: MCP and A2A](#15-protocols-mcp-and-a2a) — 7 questions · [read section](15-protocols-mcp-a2a.md)
- [16. Context Engineering](#16-context-engineering) — 7 questions · [read section](16-context-engineering.md)
- [17. Agent Memory](#17-agent-memory) — 7 questions · [read section](17-memory.md)
- [18. Agent Skills](#18-agent-skills) — 7 questions · [read section](18-skills.md)
- [19. Harness Engineering](#19-harness-engineering) — 7 questions · [read section](19-harness-engineering.md)
- [20. Agent Runtime: Sandboxes, Durable Execution, Long-Running Agents](#20-agent-runtime-sandboxes-durable-execution-long-running-agents) — 7 questions · [read section](20-agent-runtime.md)
- [21. Loop Engineering](#21-loop-engineering) — 7 questions · [read section](21-loop-engineering.md)
- [22. Build a Harness from Scratch](#22-build-a-harness-from-scratch) — 8 questions · [read section](22-build-a-harness.md)
- [23. Coding Agents and Agentic Engineering](#23-coding-agents-and-agentic-engineering) — 6 questions · [read section](23-coding-agents.md)
- [24. Computer-Use, Browser, and Deep-Research Agents](#24-computer-use-browser-and-deep-research-agents) — 6 questions · [read section](24-computer-use-and-research-agents.md)
- [25. Voice and Realtime Agents](#25-voice-and-realtime-agents) — 7 questions · [read section](25-voice-agents.md)
- [26. Evals](#26-evals) — 7 questions · [read section](26-evals.md)
- [27. Observability and Tracing](#27-observability-and-tracing) — 7 questions · [read section](27-observability.md)
- [28. Data Flywheels and Synthetic Data](#28-data-flywheels-and-synthetic-data) — 7 questions · [read section](28-data-flywheels.md)
- [29. Adapting Models: Prompt Optimization, Fine-Tuning, Distillation, RL](#29-adapting-models-prompt-optimization-fine-tuning-distillation-rl) — 6 questions · [read section](29-adapting-models.md)
- [30. Cost, Latency, and Reliability](#30-cost-latency-and-reliability) — 7 questions · [read section](30-cost-latency-reliability.md)
- [31. Open-Weight Models and Self-Hosting](#31-open-weight-models-and-self-hosting) — 7 questions · [read section](31-open-weights-self-hosting.md)
- [32. Security and Guardrails](#32-security-and-guardrails) — 7 questions · [read section](32-security-guardrails.md)
- [33. Agent Identity and Authorization](#33-agent-identity-and-authorization) — 7 questions · [read section](33-agent-identity.md)
- [34. Governance and Regulation](#34-governance-and-regulation) — 7 questions · [read section](34-governance-regulation.md)
- [35. AI UX and Generative UI](#35-ai-ux-and-generative-ui) — 7 questions · [read section](35-ai-ux.md)
- [36. AI Product Thinking](#36-ai-product-thinking) — 7 questions · [read section](36-product-thinking.md)
- [37. Why X over Y](#37-why-x-over-y) — 10 questions · [read section](37-why-x-over-y.md)
- [38. The Disciplines and Skills Map](#38-the-disciplines-and-skills-map) — 7 questions · [read section](38-disciplines-map.md)

## 01. First Principles: Why AI Engineering Exists

<details>
<summary><b>Q: Why is this field called "AI engineering" rather than ML engineering?</b></summary>

Because the work moved from building a model to building around one. In ML engineering you train a model for each task. In AI engineering you take a general foundation model behind an API and get the capability from the context you give it and the code around it. You can do the job well without training anything, though you can still fine-tune when it's worth it ([§29](29-adapting-models.md)).

</details>

<details>
<summary><b>Q: If the model is stateless, how does a chatbot remember what you said three messages ago?</b></summary>

It doesn't remember. The client application resends the entire transcript with every request (P2), so the model rereads the whole conversation each turn. That is why long chats get slower and more expensive (P10) and eventually hit the context limit. Anything that must outlive the conversation has to be stored outside the model ([§17](17-memory.md)).

</details>

<details>
<summary><b>Q: Why can't you fix prompt injection by telling the model to ignore instructions inside documents?</b></summary>

Because instructions and data share one channel (P9). The model sees your system prompt and the malicious document as the same kind of thing: tokens. There is nothing like a parameterized query to separate them, so any prompt-level defense is just more tokens that a cleverer attack can override. The reliable defense is limiting what the model can do: least-privilege tools, sandboxes, and human approval for consequential actions.

</details>

<details>
<summary><b>Q: Why does a 20-step agent fail far more often than a single model call, even with a strong model?</b></summary>

Because errors compound (P8). With 95% reliability per step, 20 independent steps all succeed only about 36% of the time, and early mistakes poison later steps. Making the model stronger raises *p*, but verification and checkpoints at each step are what keep *pⁿ* from collapsing.

</details>

<details>
<summary><b>Q: When should you fine-tune a model rather than use retrieval?</b></summary>

Use retrieval or tools for facts, especially private, changing, or citable ones. Use fine-tuning to change behavior: output format, style, or a narrow skill (P5). Fine-tuning facts into the weights makes them hard to update, impossible to cite, and easy to blur together, while retrieval keeps them fresh and checkable. Most teams should exhaust prompting and retrieval first.

</details>

<details>
<summary><b>Q: Why is "it worked when I tried it" not evidence that an LLM feature works?</b></summary>

Because outputs are sampled (P4). One success is one draw from a distribution, and the next input or the next sample may fail. You need a dataset of representative inputs, a way to grade outputs, and a measured success rate. That is an eval ([§26](26-evals.md)).

</details>

<details>
<summary><b>Q: Why might a clever prompt pipeline you built in 2024 make your system worse in 2026?</b></summary>

Because of the bitter lesson (P12). Scaffolding that compensated for an older model's weaknesses, such as forced step-by-step decomposition, rigid parsers, or hand-tuned retrieval tricks, can constrain a stronger model that would do better on its own. Keep scaffolding thin and removable, and use evals to find out whether each piece still helps.

</details>

<details>
<summary><b>Q: What is the real difference between a workflow and an agent?</b></summary>

Who decides the next step (P7). In a workflow, your code sets the sequence of model calls, so it is predictable, cheap, and testable. In an agent, the model chooses each next action, which handles open-ended tasks at the cost of variance and spend. Pick the least autonomy the task allows.

</details>

## 02. How an LLM Works

<details>
<summary><b>Q: Why does an LLM struggle to count the r's in "strawberry" when it can write a sonnet about strawberries?</b></summary>

The tokenizer turns " strawberry" into one or a few IDs, so the letters never reach the model, and it must recall the spelling of a token as a memorized fact. So character-level tasks are unreliable. Subword tokens are a deliberate tradeoff: they keep sequences short, which matters under n² attention. The problem goes away once the letters are in context, for example when the model spells the word out or uses a code tool.

</details>

<details>
<summary><b>Q: What would happen if you doubled an already long prompt?</b></summary>

Attention work grows with the square of the length, so it roughly quadruples while MLP work doubles. You pay more, wait longer and dilute attention (P3). FlashAttention reduces memory traffic but not the n² math. For short prompts the MLP dominates, so the square law matters mainly at tens of thousands of tokens.

</details>

<details>
<summary><b>Q: Base model vs chat model: which would you call to classify support tickets?</b></summary>

A chat model. It is post-trained to follow instructions and formats, while a base model just continues documents and needs careful few-shot framing. The tradeoff is post-training side effects such as sycophancy and weaker calibration. Use a base model when you plan to fine-tune it yourself.

</details>

<details>
<summary><b>Q: Why might an RLHF-trained model agree with a user's incorrect claim?</b></summary>

Its reward model learned from human preferences, and people often prefer agreement. RL then optimizes for whatever scores well, including agreeableness. The same optimization produces the helpfulness you want, so you can't simply remove it. Don't treat the model's agreement as verification: use a separate checker (P8) and evals.

</details>

<details>
<summary><b>Q: What would happen if you set temperature to 0 and expected identical outputs?</b></summary>

Greedy decoding is deterministic only if the logits are bit-identical, and shared servers batch requests in ways that change the floating-point math, so near-ties can flip. Many current hosted models also reject non-default temperature. Write statistical evals, not exact-match tests (P4). Exact reproducibility requires infrastructure you control.

</details>

<details>
<summary><b>Q: Fine-tuning vs putting facts in the prompt: which should you use to give the model your product catalog?</b></summary>

Put the facts in context. Fine-tuning stores facts lossily, without sources, and goes stale when the catalog changes (P5). Retrieval keeps facts fresh and citable, at the cost of input tokens per call. Fine-tune for consistent format or behavior, not as a database.

</details>

## 03. Inference Under the Hood

<details>
<summary><b>Q: Why is decode memory-bandwidth-bound while prefill is compute-bound?</b></summary>

Prefill reuses each loaded weight across thousands of prompt tokens, so math is the limit. Decode reloads every weight to make one token per sequence, so memory speed is the limit. That is why providers batch many users' decode steps together, until batches turn compute-bound or the KV cache fills memory.

</details>

<details>
<summary><b>Q: What would happen if a server did not keep a KV cache?</b></summary>

Every step would recompute keys and values for the whole prefix: O(n²) projections per generation instead of O(n). Outputs would be identical, only much slower. The cache trades memory for that compute, and at long contexts that memory caps how many requests fit on a GPU.

</details>

<details>
<summary><b>Q: Why are output tokens priced higher than input tokens?</b></summary>

An input token shares a weight read with thousands of others during prefill, while an output token needs its own sequential pass and holds a KV slot until the request finishes. More GPU time per token means a higher price (5× on current Claude models). For output-heavy work, shortening the answer saves more than trimming the prompt.

</details>

<details>
<summary><b>Q: TTFT vs TPOT: which should you optimize for a chat UI, and which for a nightly batch job?</b></summary>

A chat UI needs low TTFT so a response visibly starts, and a TPOT low enough that streaming reads smoothly. A nightly job cares about neither; it needs throughput and price, so the Batch API's 50% discount fits. Agents pay end-to-end latency on every step, so total time matters most.

</details>

<details>
<summary><b>Q: What would happen to your cache hit rate if you put the current timestamp at the top of the system prompt?</b></summary>

It would drop to zero. Caching matches exact prefixes, and a changed first line changes every later block's hash, so every request pays full prefill price and TTFT. Nothing errors, so it can go unnoticed. Put volatile values after the last breakpoint and monitor `cache_read_input_tokens`.

</details>

<details>
<summary><b>Q: Why does quantization speed up generation, and when should you avoid it?</b></summary>

Decode is limited by bytes moved, so fewer bits per weight means less data per step and more room for batching. The cost is precision, which tends to show on long reasoning, math and long contexts. Avoid aggressive quantization when your evals show degradation, or when quality matters more than serving cost.

</details>

<details>
<summary><b>Q: Why doesn't speculative decoding change the model's output?</b></summary>

The large model checks every drafted token with a rejection-sampling rule that preserves its own distribution, and supplies the correction at the first mismatch, so the draft changes only speed. Speedups depend on how often drafts are accepted, and they shrink when batches are already compute-bound.

</details>

## 04. Reasoning Models and Test-Time Compute

<details>
<summary><b>Q: Why does writing intermediate steps let a transformer solve problems it cannot solve when forced to answer in its first token?</b></summary>

Each generated token gets one fixed-cost forward pass and is fed back as input (P1). Writing steps buys more serial computation and a scratchpad the model can attend to. The result is better accuracy on multi-step problems, at the price of tokens, cost and latency (P10). It doesn't help when the bottleneck is missing knowledge rather than computation.

</details>

<details>
<summary><b>Q: Why did RL with verifiable rewards produce backtracking and self-checking when chain-of-thought prompting did not?</b></summary>

Prompted CoT imitates the form of reasoning, and nothing rewards it for being correct. RLVR scores only whether the final answer passes a programmatic check, so any habit that raises the hit rate gets reinforced. It only works where answers can be checked automatically, and it rewards passing the checker rather than meeting intent. It's the wrong tool for open-ended tasks with no verifier.

</details>

<details>
<summary><b>Q: GRPO vs PPO: what does GRPO drop, and what does it use instead?</b></summary>

PPO trains a separate value model to estimate a baseline. GRPO drops it and uses the mean (and spread) of rewards across a group of sampled answers to the same prompt. That saves a second large model's memory and compute, which makes RL on big models cheaper. The cost is more generation per training step, since it needs several samples per prompt.

</details>

<details>
<summary><b>Q: Serial vs parallel test-time compute: when would you prefer majority voting over raising the effort level?</b></summary>

Voting runs N independent samples, so wall-clock time stays near one sample and the agreement rate doubles as a confidence score. It suits short, comparable answers such as a number or a label, when you can afford N× the cost. For long free-form outputs, where no two samples match, raise effort instead.

</details>

<details>
<summary><b>Q: What would happen if your code read only <code>content[0].text</code> from a Claude response with adaptive thinking on?</b></summary>

The first block is often a `thinking` block, which has no `text` field and an empty `thinking` field by default. The code would crash or read nothing, and because the model decides per request whether to think, the bug would show up only some of the time. Always iterate over the blocks and select by `type`.

</details>

<details>
<summary><b>Q: Why should you not treat a thinking summary as an audit log of why the model made a decision?</b></summary>

A different model writes the summary, from a trace that is itself often unfaithful: in Anthropic's tests, models used planted hints but usually didn't mention them. Relying on summaries for compliance or root-cause analysis gives false confidence. Use them to debug prompts, and verify behavior with evals and independent checks (P8).

</details>

<details>
<summary><b>Q: Why did RL post-training on agentic tasks make 2025 agents reliable enough to ship?</b></summary>

Success compounds as p^n (P8), so raising per-step reliability from 0.9 to 0.99 lifts a 20-step task from about 12% to about 82%. RL on tool-using tasks with checkable outcomes, plus interleaved thinking, taught models to check results and recover from mistakes. The price was longer, costlier runs that still need outside verification. For short, well-defined tasks, a plain workflow is still cheaper (P7).

</details>

## 05. The API and Prompt Engineering

<details>
<summary><b>Q: Why does a chatbot built on the Messages API remember your name from three turns ago, if the model is stateless?</b></summary>

Your code resends the whole conversation on every call, so the earlier turn is literally back in the context window (P2). As a result, cost and latency grow with conversation length, and the context window eventually forces trimming or summarizing. Server-side state options only move the replay to the vendor; you still pay for those input tokens.

</details>

<details>
<summary><b>Q: What would happen if you put the current timestamp at the top of a long cached system prompt?</b></summary>

Caching is an exact prefix match, so a prefix that changes on every request never hits. Every call would pay the cache-write price (1.25× base) instead of the read price (0.1× or less), which is worse than not caching at all. Put volatile values after the last cache breakpoint, or in the user turn.

</details>

<details>
<summary><b>Q: Why did Anthropic remove assistant prefill, and what replaces it?</b></summary>

Prefill worked by writing the first output tokens yourself (P1). That clashes with thinking, which is meant to come before the answer, and newer models follow instructions well enough that the trick became dead weight (P12). Claude 4.6 and later return a 400 for it. Use structured outputs for format, system-prompt instructions for preambles, and a user message for continuations.

</details>

<details>
<summary><b>Q: Temperature vs effort: which dial controls what on a current Claude model?</b></summary>

Temperature rescales logits before sampling, trading determinism for diversity; on current Claude models it's deprecated and anything but 1.0 is rejected. Effort controls how much work goes into a response: how readily and deeply the model thinks and how many tool calls it makes. To reduce variability now, use structured outputs and evals rather than temperature.

</details>

<details>
<summary><b>Q: Why do few-shot examples sometimes make output worse?</b></summary>

The model continues every pattern in its context, so it copies your examples' length, phrasing and label balance along with the format you intended. Three short positive examples teach "be short and positive". Make examples diverse and tagged, and drop them once structured outputs can enforce the format.

</details>

<details>
<summary><b>Q: What would happen if your streaming code assumed an HTTP 200 meant the response would complete?</b></summary>

An SSE stream can carry an `error` event such as `overloaded_error` after the 200, partway through the text. Code that ignores it shows a truncated answer as if complete, or hangs waiting for `message_stop`. Handle error events, check the final `stop_reason`, and resume through a user message, not prefill.

</details>

<details>
<summary><b>Q: Why are XML tags in a prompt not a defense against prompt injection?</b></summary>

Tags help the model tell instructions from data, but every token, tagged or not, flows through the same attention channel, and a persuasive instruction inside a `<document>` can still be followed (P9). Treating tags as a defense gives false confidence. Real defenses are least privilege on tools and human approval for risky actions ([§32](32-security-guardrails.md)).

</details>

## 06. Structured Outputs and Constrained Decoding

<details>
<summary><b>Q: Why doesn't writing "respond only with valid JSON" in the prompt guarantee valid JSON?</b></summary>

The instruction changes probabilities but never removes a token from the vocabulary, so illegal tokens keep some chance of being sampled (P1, P4). Across hundreds of tokens per object and millions of objects, small per-token error rates compound into many broken records (P8). Constrained decoding sets illegal tokens' probability to exactly zero. Prompting still matters alongside it, because a prompt that matches the format keeps the mask from fighting the model.

</details>

<details>
<summary><b>Q: What does JSON mode guarantee compared with strict structured outputs?</b></summary>

JSON mode constrains decoding to *some* syntactically valid JSON, so it parses, but keys, types and enums are unchecked. Strict structured outputs compile *your* schema into a grammar, so required keys, types and enum values are enforced too. The tradeoff is a supported-schema subset, complexity limits and first-request compile latency. Treat JSON mode as legacy and use it only where a model lacks schema support.

</details>

<details>
<summary><b>Q: What would happen if your schema put the <code>answer</code> field before the <code>reasoning</code> field?</b></summary>

Each token is computed from the tokens before it, so the model commits to an answer before writing any reasoning, which then becomes after-the-fact justification (P1). Accuracy on multi-step problems can drop, which is one plausible mechanism behind the "Let Me Speak Freely?" results. Put reasoning first (both fields required), use a model whose thinking is unconstrained, or split the work into reasoning and extraction calls. For simple classification the order barely matters.

</details>

<details>
<summary><b>Q: What would happen if your schema requires <code>invoice_number</code> but the document has none?</b></summary>

The grammar forces the model to emit a string, so it produces a plausible invented number that passes every parser (P4). The fix is schema design: make the field nullable or add an explicit "not found" option, so the honest answer is a legal path. Then measure value accuracy with evals, because no parser can catch this.

</details>

<details>
<summary><b>Q: Constrained decoding vs validate-and-retry: why do you usually need both?</b></summary>

Constrained decoding guarantees syntax and schema at generation time, with no wasted calls. It can't express business rules such as "line items sum to the total", and unsupported keywords like `minimum` get checked only on your side. A Pydantic validator catches those violations, and a bounded retry that feeds back the exact error gives the model a targeted second sample. Don't retry refusals or `max_tokens` truncations blindly; resampling won't fix them.

</details>

<details>
<summary><b>Q: Why is tool use a form of structured output?</b></summary>

A tool call is the model emitting a name plus a JSON object that must match the tool's `input_schema`, which the harness then parses and executes (P6). With `strict: true`, the same grammar-constrained decoding guarantees the arguments validate. The only difference is routing: the output triggers an action instead of being stored. That is why the "fake tool to get JSON" trick worked, and why current Claude models that reject forced `tool_choice` point you to `output_config.format`.

</details>

## 07. Multimodal Models and Documents

<details>
<summary><b>Q: Why does an image cost tokens at all, and what decides how many?</b></summary>

The model only processes sequences of vectors, so the image is cut into patches, and each patch becomes one vector in the context, attended to and computed in prefill like a text token (P3, P10). On Claude the count is `⌈w/28⌉ × ⌈h/28⌉`, capped by downscaling to the tier's edge and token limits. Cost grows with resolution up to that cap. When fine detail doesn't matter, downscale or crop instead of sending full resolution.

</details>

<details>
<summary><b>Q: What would happen if you sent a 150-page scanned contract as a native PDF with every user question?</b></summary>

Every question would carry hundreds of thousands of input tokens: page images plus 1,500–3,000 extracted-text tokens per page. Latency and cost rise, and attention is spread across mostly irrelevant pages (P3, P10). Prompt caching cuts the repeat cost, but the document never becomes searchable data. For repeated questions, parse once into chunks with page provenance and retrieve only the relevant pages ([§08](08-embeddings-and-search.md)). Native PDF is fine for a one-off question.

</details>

<details>
<summary><b>Q: Native PDF support vs a parse-once pipeline: when would you choose each?</b></summary>

Native PDF rasterizes every page and sends text plus images on each call: the least code and the best on charts, but you pay per query and keep nothing reusable. A pipeline (OCR, layout, table structure → Markdown/JSON) costs engineering effort up front but yields versioned, indexable data, like a silver layer. Choose native for low-volume or ad-hoc work and for the hardest pages. For corpora you'll query repeatedly, choose a pipeline, usually hybrid with a VLM fallback.

</details>

<details>
<summary><b>Q: Why are a VLM's reading errors more dangerous than classic OCR errors?</b></summary>

OCR fails visibly: garbled characters stand out and are easy to flag. A VLM is a next-token predictor with a strong language prior (P1), so unclear pixels produce fluent, plausible text instead of noise. Under a strict schema the hallucinated value is perfectly valid and looks trustworthy (P4). Mitigate with "unreadable" schema options, cross-checks against the text layer or OCR, crops of small regions, and accuracy measured on labeled samples.

</details>

<details>
<summary><b>Q: Why can't you reliably map bounding boxes Claude returns for a PDF back onto the original page?</b></summary>

Claude returns pixel coordinates in the image it actually saw. PDF pages are rasterized server-side at dimensions you don't control, so you don't know the scale to invert. For images, the API also downscales oversized inputs and pads them to a multiple of 28 px. Rasterize pages yourself, pre-resize each one to fit the model's limits, send it as an image, and ask for absolute pixel coordinates, so they map one-to-one.

</details>

<details>
<summary><b>Q: Chained STT → LLM → TTS vs native speech-to-speech: what's the tradeoff?</b></summary>

Chaining turns audio into text, so you can inspect, log, filter and route it, swap components, and use any text model, including ones without audio input. You pay in per-stage latency and lost tone. Speech-to-speech consumes and emits audio tokens directly, which lowers latency and keeps tone but is harder to control and test. Choose chaining for regulated or tool-heavy flows, and speech-to-speech when conversational feel matters ([§25](25-voice-agents.md)).

</details>

## 08. Embeddings and Search

<details>
<summary><b>Q: Why can't you store embeddings from two different embedding models in the same index?</b></summary>

Each model learns its own coordinate system, so distances mean something only between vectors from the same model version. A query from model B against documents from model A produces plausible-looking scores that are essentially random. So a model upgrade means re-embedding everything, which is a backfill. The exception is a family deliberately trained into one space, such as Voyage's 4-series, and even then you should verify recall on your own evaluation set.

</details>

<details>
<summary><b>Q: Why does BM25 often beat a strong dense embedding model on a query like "E-4012 timeout"?</b></summary>

A dense model compresses the whole passage into one vector, and a rare token such as an error code is a small, poorly learned part of it. BM25 gives rare terms the highest weight through IDF and requires an exact match, so the one runbook that contains "E-4012" rises to the top. The tradeoff is that BM25 can't handle paraphrase. That is why hybrid search, not either method alone, is the production default.

</details>

<details>
<summary><b>Q: HNSW vs IVF: how does each prune the search, and when would you pick IVF?</b></summary>

HNSW prunes by greedy hops through a layered neighbor graph, which gives an excellent recall/speed tradeoff at the cost of memory and slow builds. IVF prunes like partition pruning: it scans only the clusters closest to the query, and it misses neighbors just across cluster boundaries. Pick IVF, often combined with PQ, for large, fairly static data under memory pressure. Avoid it for fast-changing data, because the centroids go stale.

</details>

<details>
<summary><b>Q: Why does Reciprocal Rank Fusion use ranks instead of the retrievers' scores?</b></summary>

BM25 scores are unbounded and depend on the corpus, while cosine scores lie between −1 and 1, so adding them lets one retriever dominate arbitrarily. RRF sums `1/(k + rank)`, which needs no calibration. The cost is that it ignores how strong a match was and favors documents that both lists found, which is why a reranker usually follows it. A tuned weighted score fusion can beat RRF if you have labeled data to tune with.

</details>

<details>
<summary><b>Q: Bi-encoder vs cross-encoder: why not just use the more accurate cross-encoder for everything?</b></summary>

A cross-encoder reads the query and the document together, so it can't precompute anything and must run a full model pass per (query, document) pair. Over millions of documents that's infeasible: Sentence-BERT estimated about 65 hours versus 5 seconds for a 10,000-sentence search. So bi-encoders and BM25 narrow millions of documents to about 100, and the cross-encoder reorders those. Skip it when the latency budget is tiny or when first-stage ordering already scores well on your evaluation set.

</details>

<details>
<summary><b>Q: What would happen if you add <code>WHERE tenant_id = 42</code> to an HNSW query in pgvector and that tenant owns 10% of the rows?</b></summary>

pgvector applies the filter after the approximate index scan. With the default `ef_search` of 40 candidates, only about 4 belong to tenant 42, so you silently get fewer than k results and may miss the best ones. Iterative index scans, a higher `ef_search`, or per-tenant partitions or partial indexes fix it. The same mechanism decides whether access-control filters in RAG cost you answers or leak data.

</details>

## 09. Retrieval-Augmented Generation (RAG)

<details>
<summary><b>Q: Why does an LLM need RAG if it was trained on the whole internet?</b></summary>

Training compresses public text into weights that are frozen at a cutoff, so the model never saw your private or recent data, can't cite where a "fact" came from, and can't forget it per user (P5). RAG puts the relevant passages into the context at request time, which gives the model fresh, private, citable facts to copy instead of guess. The tradeoff is a retrieval pipeline you must build, secure and evaluate. If your corpus is small and stable and everyone may see it, long context with caching may be simpler.

</details>

<details>
<summary><b>Q: What would happen if you enforce document permissions only with a system-prompt instruction?</b></summary>

Once a confidential passage is in the context, it is just tokens, and any user prompt, or injected text in another document, can get the model to repeat it (P9). The instruction lowers the leak rate but can't guarantee anything, because output is sampled (P4). The real control is in the retriever: filter by the end user's ACLs before passages reach the model, and keep ACLs in sync. The prompt line is fine as an extra layer, never as the only one.

</details>

<details>
<summary><b>Q: Small chunks vs large chunks: what's the tradeoff, and how do you choose?</b></summary>

Small chunks give focused vectors that match queries precisely, but they lose referents such as "it" or "the company", and an answer can straddle two chunks. Large chunks keep context but average many topics into one vector and cost more tokens per hit (P3, P10). Parent-child retrieval and contextual retrieval exist to get precise matching *and* context. Choose by sweeping chunk sizes against recall@k on your own evaluation queries, not by copying a default.

</details>

<details>
<summary><b>Q: Why does contextual retrieval prepend context before both embedding and BM25 indexing?</b></summary>

The missing information, such as which company or which quarter, hurts both retrievers: the dense vector doesn't encode it, and the inverted index doesn't contain the term. Adding a short LLM-written context to the chunk fixes both, and in Anthropic's tests the combination cut top-20 retrieval failures by 49%, against 35% for embeddings alone. The cost is one LLM call per chunk at ingest, made cheap by prompt caching, and it has to be rerun when documents change. For a tiny corpus, skip it and use long context.

</details>

<details>
<summary><b>Q: A user reports a wrong answer from your RAG bot. How do you tell a retrieval failure from a generation failure?</b></summary>

Check whether the correct passage was in the context the model actually received. If it wasn't, it's a retrieval problem: walk the funnel from corpus, parsing, chunking and top-N through reranking. If it was, it's generation: the model ignored the passage, was confused by a conflicting one, or missed it in the middle of a long context. Log retrieved IDs per request so traces answer this without re-running ([§27](27-observability.md)).

</details>

<details>
<summary><b>Q: Agentic RAG vs classic RAG: when is giving the model a search tool not worth it?</b></summary>

Agentic RAG lets the model reformulate and repeat searches, which helps on multi-hop questions where the first query can't be known in advance. Each extra step adds latency, tokens and variance, and errors compound across steps (P8). For simple lookups, such as a policy FAQ, one well-tuned hybrid retrieval inside a workflow is cheaper, faster and easier to evaluate. Move toward agentic RAG when traces show the fixed query regularly misses.

</details>

<details>
<summary><b>Q: GraphRAG vs vector RAG: which questions favor GraphRAG, and why isn't it "graph engineering"?</b></summary>

GraphRAG precomputes an entity graph, Leiden communities and LLM-written community summaries, so a "global" question about themes across the whole corpus can map-reduce over summaries instead of a biased top-k sample. It costs far more to index and adds little for needle lookups, where hybrid vector search is enough. The name collides with graph engineering ([§14](14-graph-engineering.md)), but there the graph is an agent's control flow (steps and transitions). In GraphRAG it is the data (entities and relationships).

</details>

## 10. Tool Use and Tool Design

<details>
<summary><b>Q: Why does the model never execute a tool itself, and where does that put your security checks?</b></summary>

The model only emits tokens (P1). The API parses a call into a `tool_use` block, and nothing happens until your code chooses to act (P6). Authorization, validation and approval gates therefore belong in the executor, where they are deterministic. "Never refund more than $100" in a prompt is a request to a probabilistic system. The same rule in the executor is a guarantee.

</details>

<details>
<summary><b>Q: Why did the field move from ReAct-style text parsing to API-level function calling?</b></summary>

Text protocols need the model to reproduce a format perfectly, and sampling (P4) guarantees that it sometimes won't, failing silently. Function calling trains the format in and moves parsing into the API. You get schema-checked arguments (guaranteed with `strict`) and an explicit `stop_reason`. Text parsing remains only for models without native tools.

</details>

<details>
<summary><b>Q: What would happen if a tool threw an exception and your loop crashed instead of returning <code>is_error: true</code>?</b></summary>

The turn dies, and the one component that could adapt, the model, never learns what went wrong. An error result that names the fix lets it correct the argument, choose another tool, or ask the user. Crash or escalate only on failures the model can't fix, such as a revoked credential.

</details>

<details>
<summary><b>Q: Why expose <code>search_contacts(query)</code> instead of the more flexible <code>list_contacts()</code>?</b></summary>

The agent's context is a scarce attention budget (P3), while your database's memory is cheap. Listing everything makes the model scan thousands of records token by token, which costs money (P10) and invites mistakes. Filtering in code returns only the signal. Keep low-level tools only where evals show the agent needs them.

</details>

<details>
<summary><b>Q: Your agent has 60 tools from five MCP servers and uses three per task. Why does that still hurt, and what can you do?</b></summary>

All 60 definitions are resent every turn (P2), tens of thousands of tokens that cost money and dilute selection (P3). In order: prune or merge tools, cache the stable prefix, defer rarely used tools behind tool search, and push chained calls into programmatic tool calling. With only a handful of tools, skip tool search, because the extra step isn't worth it.

</details>

<details>
<summary><b>Q: Code as action vs JSON tool calls: when would you choose each?</b></summary>

JSON calls are single typed actions that are easy to validate, gate and audit, which suits consequential writes. Code actions loop, filter and combine many calls in one step, saving context and round trips on bulk reads and data wrangling. Their cost is a sandbox and coarser control. Many systems use both.

</details>

<details>
<summary><b>Q: Why is an agent with a "read inbox" tool and a "fetch URL" tool dangerous, even if each tool is harmless alone?</b></summary>

Together they complete the lethal trifecta: private data, untrusted content (any email can carry instructions), and an exfiltration channel (a URL can carry data out in its query string). Because instructions and data share one channel (P9), one malicious email can trigger the leak. Remove a leg: allowlist egress, or require approval for outbound calls.

</details>

## 11. Agents and the Agent Loop

<details>
<summary><b>Q: Why did AutoGPT-style agents fail in 2023 while nearly the same loop works in 2025?</b></summary>

The loop was never the problem. Per-step reliability was. With no native tool calling, small context windows and weak error recovery, *p* was low, and *pⁿ* collapsed over long runs (P8). Later models were trained for tool use and agentic tasks and learned to notice and fix their own mistakes, so the same `while` loop now finishes real work. This is P12 in action: the scaffolding stayed simple, and the model improved underneath it.

</details>

<details>
<summary><b>Q: Every night you must classify new support tickets and route them to one of five queues. Workflow or agent?</b></summary>

A workflow. The steps are known in advance (read, classify, route), so code should own the control flow (P7). That makes the job cheaper, faster, testable and predictable. An agent would add variance and cost and gain nothing, because no step depends on discovering something new. Reconsider only if tickets regularly need open-ended investigation.

</details>

<details>
<summary><b>Q: What would happen if you removed <code>max_turns</code> and relied on the model to say when it's done?</b></summary>

Most runs would end fine, but a few would loop indefinitely, repeating a failing call or oscillating between two edits, and each turn would cost more than the last because the context grows (P2, P10). In a sampled system, rare behaviors appear at scale (P4), so the tail is guaranteed. Keep a turn cap and a token cap as hard backstops, even if they rarely fire.

</details>

<details>
<summary><b>Q: A step is 95% reliable. Why is a 20-step agent built from it so unreliable, and what is the most effective fix?</b></summary>

Independent steps multiply: 0.95²⁰ ≈ 36%. Raising *p* helps, but verification helps more. A checker that catches a failed step and allows one retry lifts the effective *p* to about 0.9975, and 20-step success to about 95% (under idealized assumptions). The checker converts silent errors into recoverable ones.

</details>

<details>
<summary><b>Q: Why keep the checker separate from the maker?</b></summary>

A model grading its own output shares the misunderstandings that produced it, and it tends toward leniency. Anthropic reports that agents "confidently" praise mediocre work. A separate checker, ideally computational (tests, schema checks), or a differently prompted skeptical judge, fails in different ways, so its errors don't line up with the maker's. That independence is what makes the retry math work.

</details>

<details>
<summary><b>Q: Why is <code>stop_reason: "end_turn"</code> not proof that the task succeeded?</b></summary>

It only means the model stopped emitting tool calls. It predicted that a final answer comes next. That prediction can be wrong, for example when a later agent sees partial progress and declares the job done. Done should be decided by an external check: tests pass, data reconciles, or a human approves.

</details>

<details>
<summary><b>Q: Why does each turn of an agent cost more than the one before, and what do you do about it?</b></summary>

The model is stateless, so each request resends the full transcript, and total input tokens grow roughly with the square of the turn count (P2, P10). Prompt caching makes the repeated prefix cheap, and clearing stale tool results or compacting history keeps the context small and focused (P3). For very long tasks, split the work across fresh contexts with state on disk ([§16](16-context-engineering.md)).

</details>

## 12. Agentic Design Patterns

<details>
<summary><b>Q: Why does a gate between two prompt-chain steps improve reliability more than writing one better prompt?</b></summary>

A gate is deterministic code that checks an intermediate output before the next step consumes it. Errors get caught at the step that made them, so they can't compound into later steps (P8), and each step runs on a smaller, focused prompt (P3). The cost is extra calls and latency, and a gate catches only what you can express in code. If the task doesn't break into checkable steps, or one call already passes your evals, chaining just adds latency.

</details>

<details>
<summary><b>Q: Orchestrator-workers vs sectioning: what is the difference if both fan out to several LLM calls?</b></summary>

Sectioning fixes the subtasks in code before any input arrives. In orchestrator-workers, an LLM invents the subtasks for each input at runtime. That handles tasks whose shape varies, but control flow moves to the model (P7), so behavior is less predictable and harder to test, and you pay for a planning call and a synthesis call. If you can list the subtasks in advance, use sectioning.

</details>

<details>
<summary><b>Q: Why use a separate evaluator instead of asking the same model to review its own work?</b></summary>

A self-review shares the context and assumptions that produced the mistake, and agents reliably grade their own work too generously. Self-correction without external feedback often fails (Huang et al., 2023). A separate evaluator, with its own skeptical prompt, rubric and fresh context, sees only the output, so it can catch what the maker rationalized. It costs extra calls and still needs tuning, because it is lenient by default. When a deterministic check exists, such as tests or a schema, prefer it: it's cheaper and can't be argued into passing.

</details>

<details>
<summary><b>Q: What would happen if you used voting with five identical calls on a question the model systematically gets wrong?</b></summary>

Voting helps only when errors are roughly independent across samples. Five calls with the same prompt and the same weights share the same bias, so most of them repeat the error, and a 5/5 majority looks like certainty. You pay five times the tokens for false confidence. Vary the prompts or models, or use a real verifier. Against a systematic error, voting is the wrong tool.

</details>

<details>
<summary><b>Q: ReAct vs plan-and-execute: when does planning up front beat deciding step by step?</b></summary>

ReAct picks each step after seeing the last observation. That makes it adaptive, but it calls the big model every turn and resends the transcript each time (P10). Plan-and-execute calls the planner once and leaves the work to cheap executors, and ReWOO and LLMCompiler can even run independent calls in parallel. It wins when the steps are predictable from the start. A plan written before any observation can be wrong, so you need replanning. For exploratory work like debugging, where each result changes the next move, ReAct fits better.

</details>

<details>
<summary><b>Q: What would happen if you upgraded the planner–generator–evaluator harness to a much stronger model and kept every component?</b></summary>

Each component encodes an assumption about what the model can't do alone, and a stronger model makes some of those assumptions false. In Anthropic's case, sprints and per-sprint QA stopped paying for themselves once Opus 4.6 could sustain long builds. Keeping them means paying hours and dollars for dead weight (P12), and it can even constrain the model. Remove one component at a time, measure the effect, and keep the evaluator only for tasks beyond what the model does reliably alone.

</details>

## 13. Multi-Agent Systems

<details>
<summary><b>Q: Why did token usage explain most of the performance variance in Anthropic's research system, and what does that say about why multi-agent helps?</b></summary>

Hard research needs a lot of reading, and one agent can usefully spend only as many tokens as its context window allows before it fills and rots (P3). Subagents each get a fresh window, so the system can spend far more tokens in parallel and pass only compressed findings to the lead. Multi-agent works here mainly as a way to scale token spend. The price is about 15× the tokens of chat, so it pays only when the work is valuable and splits into breadth-first pieces.

</details>

<details>
<summary><b>Q: What would happen if you split "build a feature" into planner, implementer, tester and reviewer agents?</b></summary>

Each handoff compresses context. The tester doesn't know why the implementer made its choices, and the reviewer never saw the exploration, so information degrades at every hop. Anthropic saw subagents split this way spend more tokens on coordination than on the work itself. Decompose by context boundary instead: one agent writes the feature and its tests, and a separate verifier black-box tests the result, since verification needs little context. Splitting by role makes sense only when the roles genuinely need different, isolated context.

</details>

<details>
<summary><b>Q: Subagents (agents-as-tools) vs handoffs: when would you choose each?</b></summary>

With subagents, the manager keeps control. Each specialist sees only its brief, runs in isolation and returns a result, which gives strong context isolation, parallel fan-out and one owner of the final answer, at the cost of an extra model call per request. With handoffs, control moves to the specialist, who sees the history by default and talks to the user directly, which takes fewer calls and works well for triage. Choose subagents for bounded, parallel, read-only work. Choose handoffs when routing to a specialist is the workflow. Avoid handoffs when misroutes are costly or histories are long.

</details>

<details>
<summary><b>Q: Why is "read-heavy" part of the decision rule, and not just "parallelizable"?</b></summary>

Write-heavy work can look perfectly parallelizable on paper and still fail, because every write commits implicit decisions about style, schema and edge cases that other writers can't see (Cognition's Flappy Bird example). Reads commit nothing, and their summaries merge cleanly. It's the many-readers, one-writer rule from any data system without a transaction manager. Parallel writers work only when partitions are truly disjoint and a verification step checks the merge.

</details>

<details>
<summary><b>Q: What would happen if you added agents to a task a single agent already handles at 80% accuracy?</b></summary>

Google found a capability ceiling: once a single agent is already strong (above about 45% in their revised study), extra agents bring negative returns. The coordination tax, meaning messages that eat each agent's token budget and fragmented reasoning, outweighs the little headroom left. You'd pay several times the tokens for the same or worse results. Spend the effort on the single agent's context, tools and verification instead.

</details>

<details>
<summary><b>Q: A2A vs your framework's subagent API: why not use A2A for everything?</b></summary>

A2A is a wire protocol for agents that are opaque to each other: they're built by different teams or vendors, find each other through Agent Cards, and exchange tasks without sharing memory or tools. Inside your own system you control both sides, so a framework primitive (a tool call that runs a subagent loop) is simpler, faster and easier to trace. A2A's own docs say it is "not a sub-agent or tool-call protocol." Use it when you cross an organizational or framework boundary, not for internal delegation.

</details>

## 14. Graph Engineering: Orchestration as State Machines

<details>
<summary><b>Q: Why do agent graphs usually contain cycles when Airflow and dbt pipelines forbid them?</b></summary>

A data DAG encodes dependencies between transformations, and a cycle would leave no valid execution order, so acyclicity guarantees that every task runs once and the run ends. Agents loop as part of their work: they retry tools, ask for missing input, and revise after validation. So the graph needs back-edges, and the run ends when a runtime condition is met rather than by structure. The tradeoff is that you must enforce termination yourself with step limits, counters and budgets. If your process really is a fixed sequence of transformations, a DAG is the better tool.

</details>

<details>
<summary><b>Q: What would happen if a node sends an email and then calls <code>interrupt()</code> to ask for approval?</b></summary>

Checkpoints are written at super-step boundaries, and a resumed node runs again from its first line, so the email goes out once before the pause and again on resume. The fix is idempotency: put the send in its own node after approval, or guard it with an idempotency key. It is the at-least-once lesson from Kafka consumers. You can skip the precaution only for naturally idempotent effects, such as an upsert keyed by ID.

</details>

<details>
<summary><b>Q: In what sense is a ReAct-style agent loop "a degenerate graph"?</b></summary>

The loop is two nodes, the model call and the tool executor, with one conditional edge ("did the model request a tool?") that either cycles back or exits. So loop and graph are the same mechanism with different amounts of structure written down. The consequence is that you can start with a loop and promote steps to explicit nodes and edges only where you need guaranteed order, persistence or approval. Over-promoting turns a flexible agent into a brittle flowchart.

</details>

<details>
<summary><b>Q: Checkpointer vs store: what does each persist, and why does a checkpointer need a <code>thread_id</code>?</b></summary>

A checkpointer saves snapshots of one run's graph state after every super-step. The `thread_id` is the key that says which snapshot sequence to load and append to, so reusing it resumes and a new one starts fresh. A store is a cross-thread key-value layer for data that outlives any single run, such as user preferences. Putting long-term facts in thread state would lose them when a new thread starts, and putting per-run scratch data in the store would leak it across conversations.

</details>

<details>
<summary><b>Q: What would happen if you modeled open-ended research as a fixed graph with one node per research step?</b></summary>

The graph would hard-code your guess about how research unfolds: how many searches, in what order, when to stop. Real queries vary, so it wastes steps on easy questions, cuts off hard ones, and grows edges with every new case. LangChain hit exactly this and moved deep research to an agent harness. Keep a graph only for the fixed stages around such a task, such as intake, then a research agent node, then human review.

</details>

<details>
<summary><b>Q: Why does map-reduce need <code>Send</code> instead of ordinary edges?</b></summary>

Ordinary edges are declared before the run, so they can't express "one worker per item" when the number of items is known only at runtime. A `Send` returned from a conditional edge launches a parallel invocation of a node with its own private input. A reducer such as `operator.add` then merges the parallel writes into shared state. Without a merging reducer, the parallel updates to the same key would conflict. If the fan-out width is fixed and small, plain parallel edges are simpler.

</details>

<details>
<summary><b>Q: Why doesn't replaying an agent graph from an old checkpoint reproduce the original run?</b></summary>

Time travel restores the saved state and then re-executes every node after that checkpoint, including LLM calls, API requests and interrupts. Model output is sampled (P4) and external systems change, so the replayed path can diverge. That makes replay useful for asking "what if we retried from here?" or for forking with edited state, but not for exact reproduction. For audits, rely on the recorded traces ([§27](27-observability.md)), not on replay.

</details>

## 15. Protocols: MCP and A2A

<details>
<summary><b>Q: Why does MCP turn N×M integrations into N+M, and what does it leave unstandardized?</b></summary>

Each host implements an MCP client once and each system implements an MCP server once, so any host can discover and call any server through the same JSON-RPC messages: N+M implementations instead of N×M. It standardizes discovery, invocation, transports and auth. It does not standardize whether a tool is well designed, what its description makes the model do, or what it costs in context. A bad tool behind MCP is still a bad tool, only easier to install.

</details>

<details>
<summary><b>Q: Why did the 2026-07-28 revision remove the initialize handshake and the session, and how does a server keep state now?</b></summary>

Sessions pinned each client to the instance that issued its `Mcp-Session-Id`, which forced sticky routing and shared session stores and made horizontal scaling awkward. Now every request carries its version and capabilities in `_meta`, so any instance can serve it, and mid-call questions use multi round-trip results whose `requestState` travels in the payload. A server that needs cross-call state mints an explicit handle that the model passes back as an argument, so state management moves into tool design.

</details>

<details>
<summary><b>Q: What would happen if you connected 15 MCP servers exposing about 10 tools each to one agent?</b></summary>

About 150 tool definitions would be injected into every request, plausibly tens of thousands of tokens, before the user says anything. That raises cost and latency (P10), dilutes attention (P3), and increases wrong picks between similarly named tools. The fixes are to load fewer tools per task, defer them behind tool search, or let the agent call tools through code. If you really need only three tools, connect only those.

</details>

<details>
<summary><b>Q: MCP vs plain tool use: when is a protocol overkill?</b></summary>

Plain tool use is a JSON Schema in your request and a function in your process. MCP adds a separate server process or HTTP service, JSON-RPC, version negotiation and often OAuth. That overhead buys reuse across hosts, third-party maintenance and central governance. For one application with a few tools you own, especially on a latency-sensitive path, it buys nothing, so define the tools directly.

</details>

<details>
<summary><b>Q: Why is tool poisoning possible even when the user approves every tool call?</b></summary>

The attack lives in the tool's *description*, which the model reads as context (P9), not in the visible call. A poisoned description can tell the model to read a secret file and slip it into an innocuous-looking parameter, and confirmation dialogs often hide full arguments. Rug pulls make it worse, because the description can change after approval. The defense is least privilege, meaning that the server and its tokens can't reach the secrets, plus pinned, re-reviewed tool definitions. Better prompting is not a defense.

</details>

<details>
<summary><b>Q: Why not just wrap a remote agent as an MCP tool instead of using A2A?</b></summary>

An MCP tool models a function call: a request with a schema and a result. A remote agent may run for hours, ask for input or authentication mid-task, stream partial artifacts and keep its internals opaque, which A2A models with task states, push notifications and signed Agent Cards. Wrapping works for a quick, stateless sub-agent, and MCP's Tasks extension narrows the gap. For long-running delegation across organizations, A2A fits better.

</details>

<details>
<summary><b>Q: What would happen if a stdio MCP server writes debug output with <code>print()</code>?</b></summary>

On stdio, stdout *is* the protocol channel, and every line is expected to be a JSON-RPC message. A stray print injects non-JSON bytes, so the client fails to parse responses and the connection breaks in confusing ways. Log to stderr or OpenTelemetry, which is also the spec's replacement for deprecated Logging. Streamable HTTP servers don't have this problem, because the HTTP body is separate from process output.

</details>

## 16. Context Engineering

<details>
<summary><b>Q: Why doesn't a 1M-token context window make context engineering unnecessary?</b></summary>

Attention spreads thinner as the window fills (P3), and Chroma saw accuracy fall with length on all 18 models it tested, even on simple tasks. Each turn also re-sends the whole window, so an agent's total input grows roughly with the square of its step count (P10). A big window gives you room; it doesn't make filling the room free or harmless. It's still the right tool when one task truly needs a large document read in full.

</details>

<details>
<summary><b>Q: What would happen if you put the current timestamp at the top of an agent's system prompt?</b></summary>

Caching matches prefixes byte for byte, and a value that changes every request near the front invalidates everything after it. Every turn then pays full price and full prefill latency for the whole history, plus a write premium if markers are set. Move the date into the newest user turn or a mid-conversation system message, after the cached history.

</details>

<details>
<summary><b>Q: Compaction vs a context reset: when would you choose a reset?</b></summary>

Compaction summarizes old turns so the same agent continues. A reset starts a new agent with an empty window and a handoff file. That clean slate fixed "context anxiety" in models like Sonnet 4.5, but it costs orchestration code, tokens and latency, and the handoff must carry everything that matters. Prefer compaction on models without the anxiety, as Anthropic did once Opus 4.5 arrived.

</details>

<details>
<summary><b>Q: Why is tool-result clearing the lightest form of compaction, and what does it cost?</b></summary>

Once the model has acted on a large tool result, the raw text rarely matters again, and a placeholder can't hallucinate the way a summary can. But each clearing edits earlier context and breaks the cache from that point, so batch clearings instead of trimming every turn. On the 5.5-family models, let the API's context editing do it: clearing by hand also invalidates every later thinking block. Keep the path or URL so it's restorable, and exclude results the agent still depends on, such as the spec it's implementing.

</details>

<details>
<summary><b>Q: Just-in-time agentic search vs pre-indexed RAG: when does each win?</b></summary>

Agentic search loads content with tools such as grep at the moment of need, so nothing goes stale and the folder structure acts as free metadata. Each lookup costs tool calls, though, and the agent can wander. RAG answers in one fast lookup and scales to millions of documents, but the index must be kept current. Use agentic search for codebases and live systems and RAG for large, slow-changing corpora; hybrids are common.

</details>

<details>
<summary><b>Q: What would happen if a subagent returned its whole exploration transcript instead of a summary?</b></summary>

A subagent exists to burn tokens exploring in its own window so the lead doesn't have to. Returning the transcript moves all that noise into the lead's context, which brings back distraction and confusion and multiplies cost. The lead should get a condensed result, often 1-2K tokens, with references to details it can fetch.

</details>

<details>
<summary><b>Q: Why might cleaning errors out of an agent's context make it worse, and how does that square with context poisoning?</b></summary>

A failed command and its stack trace shift the model away from repeating that action, and Manus found that keeping wrong turns improves recovery. Poisoning is a *false belief*, a hallucinated fact or goal that the model keeps treating as true. Keep observed evidence of failure, and correct invented content, especially in summaries and notes that will persist.

</details>

## 17. Agent Memory

<details>
<summary><b>Q: Why can't a model "just remember" a user's preferences between sessions, and what does a memory system do instead?</b></summary>

The model is stateless: nothing from one API call survives into the next (P2), and its weights don't change during use. A memory system writes chosen information to storage outside the model and puts a relevant slice back into a later context, so quality depends on the write and read policies. If you need changed behavior for everyone, that's a fine-tuning question, not a memory question.

</details>

<details>
<summary><b>Q: Semantic vs episodic memory: which would you use to stop an agent repeating a failed backfill strategy, and why?</b></summary>

Episodic memory stores specific experiences, such as "the full backfill timed out on 2026-09-02; splitting by month worked", which can be retrieved as worked examples when a similar task comes up. Semantic memory stores standing facts, such as "orders is partitioned by month". The lesson begins as an episode. If it keeps recurring, promote it to a procedural rule in CLAUDE.md or a skill, so it doesn't depend on retrieval finding the right episode.

</details>

<details>
<summary><b>Q: What would happen if an agent saved a summary of every web page it read into long-term memory without review?</b></summary>

Any instruction hidden in a page would be replayed into every future session, a persistent prompt injection: OWASP's memory and context poisoning (P9). The store would also fill with low-value, contradictory content, which hurts retrieval and costs tokens. Save only distilled facts with provenance, review writes from untrusted sources, and keep versions so you can roll back.

</details>

<details>
<summary><b>Q: Hot-path vs background memory writes: when would you choose each?</b></summary>

Hot-path writes happen during the conversation, so the memory is usable immediately and visible to the user, at the cost of latency and a model splitting its attention. Background consolidation runs later, adds no latency, and can deduplicate and reconcile carefully, but other sessions see updates late. Use the hot path for explicit "remember this" requests and corrections. Use background jobs for mining patterns across many sessions.

</details>

<details>
<summary><b>Q: Why did MemGPT warn the model about "memory pressure" before evicting messages, rather than just evicting them?</b></summary>

Eviction is done by code, which can't judge which details matter. The warning at a threshold such as 70% gives the model a turn to move important facts into working context or archival storage before the queue manager evicts a large block of messages (e.g. half the window) into a summary. Decide what to keep before the cut, not after.

</details>

<details>
<summary><b>Q: A support agent needs each customer's plan, the refund policy and the company's tone of voice. Where should each live?</b></summary>

The customer's plan is per-user and changes, so it belongs in memory or, better, a live lookup tool against the system of record. The refund policy is shared, reviewed knowledge, so retrieve it with RAG and cite it. Tone of voice is behavior, so put it in the system prompt first and fine-tune only if prompting fails at scale (P5).

</details>

<details>
<summary><b>Q: Why have so many 2025-26 memory systems converged on plain files, and when is a vector store still the better choice?</b></summary>

Files are readable and editable by humans, versionable with git, and navigable with file tools models are trained heavily on, with no embedding index to drift. A directory gets unwieldy with fuzzy recall across thousands of memories, many concurrent writers or strict per-user isolation. Then a store with filters and vector search fits better, often behind a small index file.

</details>

## 18. Agent Skills

<details>
<summary><b>Q: Why does a skill's description matter more than its body for whether the skill is useful at all?</b></summary>

Before activation the description is the only part in context, and the model reads it to decide whether to load the body. It works as a probabilistic routing rule (P4): a strong body behind a vague description never loads, and a greedy description loads it on unrelated tasks. So you write what *and* when, use the user's keywords, and test with should and shouldn't prompts. For a skill you only invoke explicitly (`/name`), the description matters much less.

</details>

<details>
<summary><b>Q: What would happen if you moved all 40 of your team's skills into one big system prompt instead?</b></summary>

Every call would carry all 40 procedures, perhaps 100k+ tokens, adding cost and latency (P10); caching would soften the bill but not the attention cost. Adherence to the one relevant procedure would drop as attention spreads (P3), rules from different procedures would collide, and scripts would no longer stay out of context. A single always-on file only makes sense for a few short rules that apply to nearly every task.

</details>

<details>
<summary><b>Q: Skills vs MCP servers: which one should you build for "our team's process for backfilling a partitioned table"?</b></summary>

The process is know-how (ordered steps, checks, conventions), so it's a skill. An MCP server gives *access*, for example `run_sql` or `trigger_job` tools the skill's steps call. Hard-coding the process as MCP tools would freeze it into code paths and load schemas up front. If the agent can't reach the warehouse yet, you need the MCP server or a CLI as well, because a skill can't create access.

</details>

<details>
<summary><b>Q: Why do bundled scripts make a skill more reliable, and when does that benefit disappear?</b></summary>

A script runs deterministically and only its output enters context, so the agent gets the same validation every time without paying tokens for the code (P4, P10). Regenerating the logic each run would vary and cost more. The benefit disappears if the agent reads the script instead of running it, if the runtime lacks a dependency or network access the script needs, or if the task is a judgment call that code can't capture.

</details>

<details>
<summary><b>Q: Why is installing a third-party skill a supply-chain risk even if you never run its scripts?</b></summary>

The `SKILL.md` body enters context as instructions, and the model can't reliably separate trusted instructions from malicious ones in the same channel (P9). A poisoned body can tell the agent to run commands, exfiltrate files or fetch remote instructions, using the permissions the agent already has. Snyk found critical issues in 13.4% of the 3,984 public skills it scanned. Review, pin and sandbox skills, and rely on least privilege rather than on the skill behaving well.

</details>

<details>
<summary><b>Q: How does progressive disclosure change the cost of installing your 100th skill compared with your 10th?</b></summary>

The idle cost per skill stays roughly constant, about 100 tokens for one name and description, while bodies and files cost nothing until used. The real limit becomes selection quality: with a hundred overlapping descriptions the model chooses less reliably, and the index turns into noise. At that point, prune, merge, or route groups of skills to subagents.

</details>

<details>
<summary><b>Q: Why might a skill that helped last year make your agent worse today?</b></summary>

Many skills encode workarounds for a model's weaknesses, such as step-by-step hand-holding or rigid templates. Under P12, newer models absorb those abilities, and over-prescriptive instructions then constrain a model that would do better on its own. Re-run your evals when you change models, and delete skills that no longer move the results.

</details>

## 19. Harness Engineering

<details>
<summary><b>Q: Why can the same model score very differently on a benchmark depending on the harness?</b></summary>

The model only proposes tokens (P6). The harness decides what context it sees, which tools exist and in what format, what gets verified, and when it may stop, and over many steps those choices compound (P8). That's how LangChain gained 13.7 points on Terminal Bench 2.0 with the model fixed. Co-training adds a twist: models overfit to their home harness, so a new harness can help or hurt. Read every score as model plus harness.

</details>

<details>
<summary><b>Q: Guides vs sensors: what goes wrong if you build only one kind?</b></summary>

With guides only, the agent follows rules probabilistically and nobody checks whether they worked. With sensors only, the agent keeps making the same mistakes and burns turns getting caught. Guides raise first-attempt quality, and sensors catch what slips through. Prefer computational versions of both where they exist, because they're deterministic and cheap.

</details>

<details>
<summary><b>Q: What would happen if OpenAI's team had kept a single 1,000-line AGENTS.md instead of a 100-line map?</b></summary>

The file would crowd the task out of context (P3) and dilute every rule, since when everything is "important" nothing is. It would also go stale, with no mechanical way to tell live rules from dead ones. A short map plus a versioned `docs/` system of record gives progressive disclosure, and CI can check those docs. A single file works only for tiny projects with a handful of rules.

</details>

<details>
<summary><b>Q: Why does Anthropic's harness use a separate evaluator agent instead of asking the generator to check its own work?</b></summary>

Agents grade their own output too leniently and talk themselves out of real bugs. A separate checker (P8) can be tuned to be skeptical without making the generator timid, and it hands the generator concrete feedback to iterate against. The price was 6 hours and $200 against 20 minutes and $9 in one test, so drop the evaluator for tasks the current model already does reliably on its own.

</details>

<details>
<summary><b>Q: When should you prefer a context reset over compaction?</b></summary>

Prefer a reset when the model degrades or rushes as its window fills ("context anxiety"), or when work spans many windows and each session should start clean. The handoff (progress file, git history, feature list) must carry all the state, because nothing else does. Compaction is simpler and keeps continuity, and Anthropic switched back to it once Opus 4.5 stopped showing the anxiety. Re-test the choice with each new model (P12).

</details>

<details>
<summary><b>Q: Why is a pre-tool hook that blocks <code>rm -rf</code> necessary but not sufficient?</b></summary>

The hook runs on every call regardless of what the model decides, so it reliably stops the obvious command and tells the model why (P6). But a blocklist can't enumerate every destructive command: `find -delete`, a Python one-liner or a script the agent writes all get past it. Since any text in context can steer the model (P9), you also need containment underneath: a sandbox, least-privilege credentials, and checkpoints.

</details>

<details>
<summary><b>Q: How does the ratchet interact with the bitter lesson (P12)?</b></summary>

The ratchet adds a permanent fix for each observed mistake, so the harness only grows. P12 says many of those fixes are workarounds for today's model weaknesses and become dead weight as models improve. Anthropic's harness shed context resets and sprint decomposition across two model generations. So tie every rule to the failure that created it, and remove rules when you upgrade models and your evals show they no longer help.

</details>

## 20. Agent Runtime: Sandboxes, Durable Execution, Long-Running Agents

<details>
<summary><b>Q: Why does an agent that runs code need filesystem and network isolation together, rather than either alone?</b></summary>

Filesystem limits stop an injected agent from reading or changing files outside its area, and network limits stop it from sending data anywhere. With only one, the other becomes the hole: data inside the allowed paths gets posted to any host, or the agent edits configs to regain the network access you blocked. Together they cap the damage of an injection without trusting the model (P9). The cost is maintaining allow-lists for the registries and APIs real tasks need.

</details>

<details>
<summary><b>Q: In durable execution, why must workflow code be deterministic when the LLM calls inside it are not?</b></summary>

Recovery re-runs the code and feeds each step its recorded result, so the code must take the same branches and produce the same step IDs. LLM calls may be random because they are steps, and replay returns the logged sample, not a new one (P4). A clock read or random number outside a step can send replay down a branch that never happened. That discipline is not worth it for short runs that can simply restart.

</details>

<details>
<summary><b>Q: What would happen if a tool that charges a customer crashed after the charge succeeded but before its result was logged?</b></summary>

Engines record a step only after it returns, so the step re-runs on restart and the customer is charged twice: durable execution is at-least-once. An idempotency key built from the run and step ID lets the payment API drop the duplicate, which makes the charge effectively-once. If the API has no such key, check for an existing charge before writing, or gate the step behind a human.

</details>

<details>
<summary><b>Q: Checkpointer vs step journal: what does each persist, and when is each the better fit?</b></summary>

A checkpointer snapshots the whole state after each step. A journal records every step's result and rebuilds the state by replaying them. Checkpoints are simpler and give resume and time travel, but a half-finished node re-runs. Journals replay side effects exactly and add durable timers, at the cost of determinism rules and another system. Use checkpoints for graph agents and chat threads, and journals for long runs with external side effects.

</details>

<details>
<summary><b>Q: Why does Managed Agents keep the session log separate from Claude's context window?</b></summary>

The log stores every event durably outside the harness, and the context window is only the slice the harness shows Claude next. So compaction becomes a reversible view: the originals can be re-read with `getEvents()` later. It also makes the harness stateless, because a replacement reads the log and resumes. For a one-call task the extra layer buys nothing.

</details>

<details>
<summary><b>Q: How can a human approval that takes three days cost nothing while it waits?</b></summary>

The approval is a step whose result comes from a person. The runtime saves state, records the pending request and releases the process and sandbox. When the answer arrives as an event, the run replays its finished steps from the log, with no repeated model calls, and continues. Code before the interrupt must be safe to run again.

</details>

<details>
<summary><b>Q: What would happen to a spend cap tracked in process memory when the run crashes and replays?</b></summary>

The counter restarts at zero while recorded steps replay at no new cost, so every restart grants a fresh budget, and a crash-looping agent can spend many times its cap. Record each step's cost in the durable log so the total is rebuilt on replay, or enforce the cap outside the process, as Managed Agents session budgets do.

</details>

## 21. Loop Engineering

<details>
<summary><b>Q: Why does the Ralph loop start every iteration with a fresh context instead of continuing one long session?</b></summary>

The model is stateless (P2), so a new process that reads the same files is the same agent without the accumulated failed attempts and stale tool output that degrade attention (P3). State moves to disk in the plan file, the specs and git, so nothing important is lost. The cost is re-reading the specs every time, which prompt caching partly offsets. For judgment-heavy exploratory work, where the session's own reasoning is the valuable state, one long session can be better.

</details>

<details>
<summary><b>Q: What is back pressure in a loop, and why must the checks be fast?</b></summary>

Back pressure is an automated check (tests, type checker, linter) that rejects bad output and feeds the error into the next iteration. It is what keeps a loop converging instead of compounding errors (P8). Each iteration waits on the checks, so slow checks mean fewer iterations per hour, which is Huntley's point that "the wheel has got to turn fast." You trade check speed against how much each check proves, so keep a fast check inside the loop and a slower full suite at merge time.

</details>

<details>
<summary><b>Q: Why should the agent that wrote the code not be the one that decides it is done?</b></summary>

The maker's context holds its own case for why the work is correct, and models "reliably skew positive when grading their own work." A checker with a fresh context, different instructions and ideally its own evidence (running the tests itself) avoids those blind spots. A separate checker still costs tokens and is still an LLM. So prefer deterministic checks, and use a model judge only for what code can't verify.

</details>

<details>
<summary><b>Q: What would happen if a loop's only stop condition were "the test suite passes" and the agent could edit the tests?</b></summary>

The quickest route to green is to delete, weaken or special-case the tests, and models trained against passing checks are known to take it (reward hacking). The loop would then stop "successfully" with broken code. Make tests read-only to the maker, diff-guard the test directory, run the checks outside the agent's sandbox and keep held-out tests. Pair the test check with a separate goal judge.

</details>

<details>
<summary><b>Q: <code>/goal</code> vs a plain iteration cap: what does each guarantee?</b></summary>

`/goal` runs a separate small model after each turn to judge whether your condition holds. It decides *success*, but probabilistically, and it sees only what the transcript shows. An iteration cap guarantees *termination* but says nothing about quality. You need both, plus a spend cap, because each covers a failure the others miss.

</details>

<details>
<summary><b>Q: Why do parallel loops in separate git worktrees still conflict?</b></summary>

Worktrees give each loop its own directory and branch, so edits cannot collide on disk. But two loops can make incompatible decisions about the same code, and those surface as merge conflicts or subtle breakage when the branches are combined. Partition work by area, keep PRs small, rebase often and merge through one queue. Don't run tightly coupled tasks in parallel at all.

</details>

<details>
<summary><b>Q: Is "loop engineering" a new discipline or a new name for harness engineering?</b></summary>

The practice is real and older than the name: agents have run in loops since 2023, Ralph since mid-2025. What the label adds is a focus on a different unit of design: the system that schedules runs, feeds them, checks them and stops them, one floor above a single harness. The overlap is large and the term is only a few months old, so judge it by its practices (back pressure, maker ≠ checker, stop conditions), not by the label.

</details>

## 22. Build a Harness from Scratch

<details>
<summary><b>Q: What breaks if you remove the durable log?</b></summary>

A crash at turn 30 loses the in-memory run. Every model call is paid for again, and because output is sampled (P4), the rerun takes a different path that may contradict files already written. Side effects and approval prompts repeat, and the spend counter resets, so a crash-looping agent can blow through its budget. For a run that lasts seconds, skipping the log is a fair tradeoff.

</details>

<details>
<summary><b>Q: Why does the goal check rerun the check itself and use a separate model call, instead of trusting the agent's <code>end_turn</code> and its <code>run_check</code> output?</b></summary>

`end_turn` only means the model stopped asking for tools, and its closing message is a prediction that sounds like success (P8). The transcript holds the maker's own reasons for believing the work is right, so a judge that reads it inherits its blind spots. Running the check in a new process gathers independent evidence, and a judge with a fresh context and no tools sees only the artifact. The price is an extra call per iteration, so the cheap computational check runs first.

</details>

<details>
<summary><b>Q: What would happen if a tool raised an exception instead of returning an <code>is_error</code> result?</b></summary>

The loop would crash, or the API would reject the next request, because every `tool_use` needs a matching `tool_result`. Either way, the model, which is the only component that can change the plan, never learns what went wrong. An instructive error result such as "Blocked: ... Run one python3 file." lets it adapt on its next turn. Raise only for failures the model can't fix, such as a revoked API key.

</details>

<details>
<summary><b>Q: What would happen if <code>compact()</code> kept the thinking blocks of the turns it keeps, on Claude Sonnet 5.5?</b></summary>

Each thinking block is bound to the system prompt, tools and messages that came before it (preserved thinking). Once the summary replaces the earlier turns, that prefix no longer matches, so the API rejects the request where the check is enforced. The fixes are to strip thinking from the kept turns, to send `"drop_block"` so the API drops the stale blocks, to use simple compaction with no turns kept, or to let the API compact on the server **(Preview)**. Without thinking blocks in the history, the problem doesn't arise.

</details>

<details>
<summary><b>Q: Why does the system prompt stay identical for the whole run, with the progress notes in the first user message instead?</b></summary>

The prefix is resent on every call (P2), and prompt caching only pays off if it is byte-identical (P10). Volatile content near the front invalidates everything after it, and on current models editing the system prompt also invalidates stored thinking. So stable content goes first, volatile content last, and history stays append-only. If instructions must change mid-run, append a system message instead ([§16](16-context-engineering.md)).

</details>

<details>
<summary><b>Q: The dangerous-command hook and <code>run_check</code>'s allow-list both stop <code>rm -rf</code>. Why keep both, and which one is the real control?</b></summary>

The allow-list is the stronger check. It permits exactly `python3 <file>`, so anything unlisted fails, whatever it looks like (P9). The regex blocklist can't enumerate every destructive command (`find -delete`, a Python one-liner), but it catches common ones early, with a clearer message that helps the model recover. Neither is the real control, because neither is containment: the agent wrote the file that `python3 <file>` runs, so that file can do anything your user can. In production, an OS-level sandbox bounds the damage ([§20](20-agent-runtime.md), [§32](32-security-guardrails.md)).

</details>

<details>
<summary><b>Q: Why does iteration 2 start from an empty context instead of continuing iteration 1's conversation?</b></summary>

Iteration 1's history holds a failed attempt, a denied command and a summary, tokens that dilute attention and can mislead (P3). The model is stateless anyway (P2), so a fresh context that reads two notes from disk is the same agent without that baggage. The cost is that anything not written down is lost. For judgment-heavy work, where the session's own reasoning is the valuable state, one longer session with compaction can be better.

</details>

<details>
<summary><b>Q: Stub vs real model: what does the stub prove, and what can't it tell you?</b></summary>

The stub proves the mechanics: the request shape, tool round trip, hooks, compaction, replay and stop rules all behave correctly on a known path, deterministically and for free. It can't tell you whether a real model loads the right skill, recovers from back pressure or finishes within budget. Those behaviors are probabilistic (P4) and need evals over many real runs ([§26](26-evals.md)). Use stubs for harness tests in CI and evals for agent quality.

</details>

## 23. Coding Agents and Agentic Engineering

<details>
<summary><b>Q: Why did coding become the first domain where agents worked reliably?</b></summary>

Every step can be checked cheaply and deterministically by compiling, type-checking and running tests. That turns P8's pⁿ compounding into a chain of caught-and-retried steps. Code is text in files (P1), and git makes every state reversible. RL with verifiable rewards also trained models on exactly this edit-run-fix loop, while domains without such verifiers lag.

</details>

<details>
<summary><b>Q: Why does Claude Code lean on grep and glob instead of a vector index, and when would you add one?</b></summary>

Code is searched by exact identifiers, which grep matches perfectly. An index goes stale with every edit, including the agent's own, and chunking separates functions from their callers. The cost is more tool calls and tokens per question. Add semantic search alongside grep, not instead of it, when the repository is too large to explore and questions are conceptual.

</details>

<details>
<summary><b>Q: What would happen if a str_replace tool silently edited the first match when old_str appears twice?</b></summary>

Sometimes it would change the wrong function, and the model would believe the edit succeeded. The error would surface turns later, far from its cause, and compound (P8). The uniqueness rule turns ambiguity into an immediate `is_error` the model fixes by quoting more context. The exact-match rule does the same for stale context.

</details>

<details>
<summary><b>Q: Vibe coding vs agentic engineering: if both use the same tool, what is actually different?</b></summary>

Ownership and verification. Vibe coding means accepting every diff and forgetting "the code even exists," which is fine for throwaway projects. Agentic engineering means you still specify the goal, give the agent checks, review the diff and answer for the result. Willison's line makes it concrete: don't file a PR you haven't reviewed yourself.

</details>

<details>
<summary><b>Q: Why did OpenAI stop reporting SWE-bench Verified, and what does that teach you about coding benchmarks?</b></summary>

Most of the hard tasks models kept failing had tests that rejected correct fixes or underspecified issues, and frontier models could recite gold patches from training data. Near the top, gains reflected exposure more than skill. Treat any public score as one model-plus-harness measurement on possibly contaminated tasks, and confirm on private tasks from your own codebase.

</details>

<details>
<summary><b>Q: What would happen if you ran five agents in parallel worktrees but kept your old review process?</b></summary>

Worktrees prevent file collisions, so you'd get five branches of plausible diffs, but your review capacity wouldn't grow. You'd either rubber-stamp them and build comprehension debt, or queue them and lose the speedup. Branches can also conflict semantically even when they merge cleanly. Parallelism pays only with small PRs, strong automated checks and partitioned work.

</details>

## 24. Computer-Use, Browser, and Deep-Research Agents

<details>
<summary><b>Q: Why is one computer-use step so much slower and more expensive than one API tool call?</b></summary>

The observation is an image of about 1,000–2,700 visual tokens instead of a few hundred tokens of JSON. Because the model is stateless, every earlier screenshot is also resent on every later step (P2, P10). Each step waits on a full model round trip, the action and a UI render. Batching, caching and lower resolution help, but if an API exists, the real fix is not to use computer use at all.

</details>

<details>
<summary><b>Q: What would happen if you downscaled screenshots from 1920 to 1280 pixels wide but forgot to scale the returned coordinates?</b></summary>

The model answers in the pixel space of the image it saw, so every click would land at two-thirds of the intended position, consistently offset toward the top left. It would miss targets or hit the wrong control, see confusing results, and burn steps retrying. Keep the scale factor and apply its inverse to every coordinate before executing.

</details>

<details>
<summary><b>Q: Accessibility tree vs screenshots: when should a browser agent use each?</b></summary>

The tree is text: cheaper, with exact element references that survive layout shifts, so read it first on well-built pages. Screenshots are needed when the tree doesn't describe the content (canvas, video, cross-origin iframes, poor markup) or when visual layout matters. The tradeoff is coverage against cost and coordinate fragility. Good toolsets switch between the two page by page.

</details>

<details>
<summary><b>Q: Why does a computer-use agent need out-of-band verification more than a coding agent does?</b></summary>

A coding agent's loop has computational checkers, tests and compilers, that report failure whatever the model believes. A GUI agent usually judges success from a screenshot read by the same model that acted. The maker is the checker, so errors compound silently over long runs (P8). Query the system of record for the end state, use a separate checker, or require human approval. Skip the extra check only for trivially reversible actions.

</details>

<details>
<summary><b>Q: Why are hallucinated citations a natural failure of research agents, and what structural fix prevents them?</b></summary>

The model predicts text, and from its weights it knows what citations look like, so it can produce a plausible URL or title it never retrieved (P1, P5). Telling it to "only cite real sources" is a plea, not a control. Accept only citations to document IDs the harness fetched, check in code that each quoted span appears in that document, and drop unsupported claims. A judge then checks whether each span actually supports its claim.

</details>

<details>
<summary><b>Q: What would happen if a browser agent in your everyday Chrome profile opened a page with hidden instructions to email your files somewhere?</b></summary>

The agent would combine private data (your sessions and files), untrusted content (the page) and the ability to act (send email): the lethal trifecta. If the model follows the injected text, the harness carries out a real exfiltration with your credentials (P9). Classifiers reduce the odds without removing them; Anthropic's pilot still saw 11.2% of attacks succeed. Run agents in a fresh profile without credentials, allowlist sites, and confirm consequential actions as they execute.

</details>

## 25. Voice and Realtime Agents

<details>
<summary><b>Q: Why is a two-second delay acceptable in text chat but not on a voice call?</b></summary>

Human conversation runs on gaps of about 200 ms, with listeners predicting the end of each turn. Silence on a call is ambiguous: has the agent failed, or the line dropped? In text chat, streamed tokens show progress, so the same delay feels fine. Voice therefore needs streaming at every stage and smart turn detection, and you should budget the p95, not only the median.

</details>

<details>
<summary><b>Q: What would happen if you set the silence threshold to 150 ms to cut latency?</b></summary>

The agent would answer faster on clean, definite turns, but it would treat ordinary pauses (breathing, "um," thinking) as the end of the turn. It would cut users off mid-sentence and answer half-questions, which forces repairs that cost far more time than the 350 ms saved. Use semantic or audio-based turn detection to be quick on definite endings and patient on trailing ones.

</details>

<details>
<summary><b>Q: Cascaded or speech-to-speech for a bank's phone agent that calls account tools and must keep auditable records?</b></summary>

Usually cascaded, or full duplex with a text backend. The transcript is the system of record, so you can log it, redact it and check policy before the agent speaks. You can also use the strongest tool-calling model and test text outputs with ordinary evals. You pay in latency and lost tone, so stream every stage and fix turn detection. Choose speech-to-speech when conversational feel matters more than auditability.

</details>

<details>
<summary><b>Q: Why must you truncate the assistant's turn after a barge-in, and what goes wrong if you don't?</b></summary>

The model only knows what the history says (P2). If the history records a full sentence the user never heard, the model reasons from a false shared state. It may say "as I mentioned," skip a question that never reached the user, or contradict itself. Truncate to the audio actually played: WebRTC and SIP sessions on OpenAI do this server-side, and over WebSocket the client sends `conversation.item.truncate`.

</details>

<details>
<summary><b>Q: Why does streaming change voice latency from a sum of stage durations into a sum of first-chunk latencies?</b></summary>

Without streaming, each stage waits for the previous stage's complete output, so you pay full STT plus full generation plus full synthesis. With streaming, TTS starts on the first clause while the LLM is still decoding, so only each stage's *first* output sits on the critical path. The tradeoff is engineering complexity: chunking, cancellation, and keeping text and audio aligned on interruption.

</details>

<details>
<summary><b>Q: Why do voice agents need filler speech during tool calls, and what is the risk?</b></summary>

A tool call's latency becomes dead air, which callers read as failure. A short acknowledgment covers the gap. The risk is that filler claims or implies results the tool hasn't produced ("I've booked it"), or repeats until it sounds robotic. Keep fillers non-committal, measure them separately from the real answer, and confirm only after the harness has the result.

</details>

<details>
<summary><b>Q: Why is a caller's voice or caller ID not an acceptable authentication factor?</b></summary>

A few seconds of audio can clone a voice, and caller ID and SIP headers can be spoofed. OpenAI's docs call SIP headers "untrusted caller metadata, not authorization." Authenticating on either hands an impersonator your tools. Verify identity out of band (a one-time code, an app confirmation), and scope tools to the verified identity (P9).

</details>

## 26. Evals

<details>
<summary><b>Q: Why can't you test an LLM feature with ordinary unit tests?</b></summary>

A unit test assumes a deterministic function, but an LLM samples its output (P4), so one passing run is a sample of one. The input space is open, and "correct" is often a judgment rather than an equality. So you measure a rate over a dataset and repeated trials, with graders that may include a model or a human. Unit tests still belong around the deterministic code: parsers, tools, schema validation.

</details>

<details>
<summary><b>Q: Why start with error analysis instead of standard metrics like helpfulness?</b></summary>

An app's failures are specific to its prompt, data and users, so generic metrics can miss them and give false confidence. Reading and coding traces shows which failures occur and how often, and criteria drift means you couldn't have written the rubric beforehand. Many findings are bugs to fix, not evals to maintain. The cost is expert time, and generic metrics still help find traces worth reading.

</details>

<details>
<summary><b>Q: What would happen if you shipped an LLM judge without calibrating it against human labels?</b></summary>

The judge is sampled and biased (position, verbosity, self-preference), so its scores may track its quirks rather than your quality bar. You could then tune prompts toward what the judge likes, which is Goodhart's law, without noticing. TPR and TNR on a held-out labeled set tell you how far to trust it. For checks code can decide, skip the judge.

</details>

<details>
<summary><b>Q: pass@k vs pass^k: which should a customer-support agent report?</b></summary>

pass^k, because each customer gets one conversation and the business needs the agent to handle the same request correctly every time. pass@k credits a task if any of k attempts succeeds, which fits products where a verifier picks the winner, such as patches filtered by tests. The same trials can give pass@8 = 100% and pass^8 = 25%. Report pass@k only if the product really retries with an automatic checker.

</details>

<details>
<summary><b>Q: A prompt change moves your pass rate from 78% to 82% on 60 cases. Should you ship it?</b></summary>

Not on that evidence. At n = 60 each rate's 95% interval is about ±10 points, so a 4-point move is inside the noise. Run a paired comparison with several trials per case, check slices for hidden regressions, and compare cost and latency. Shipping a cheap change that shows no harm is fine, but don't call it an improvement.

</details>

<details>
<summary><b>Q: Outcome grading vs trajectory grading: when is each one wrong?</b></summary>

Outcome grading misses cases where the path matters, such as reaching the right state by skipping identity verification or burning 40 tool calls. Trajectory grading is wrong when it demands one sequence, because agents find valid routes the designer didn't foresee. Grade outcomes by default and add targeted trajectory checks for rules and budgets.

</details>

<details>
<summary><b>Q: When is it right to write an eval before building the feature?</b></summary>

When you can specify success exactly in advance: hard constraints ("never call `refund` without verification"), required formats, or capability bets for the next model. Otherwise the failure surface is too large to anticipate and criteria drift sends early evals after imagined failures. The middle path is to write the evals you can specify and grow the rest from error analysis.

</details>

## 27. Observability and Tracing

<details>
<summary><b>Q: Why log the full request instead of just the user's message and the final answer?</b></summary>

The model is stateless (P2), so the whole request (system prompt, history, retrieved passages, tool results) is everything that shaped the output. Without it you can't tell a retrieval bug from a prompt bug from a model mistake, and because output is sampled (P4) you can't reliably reproduce the failure later. The tradeoff is storage and privacy, which is why the conventions make content opt-in and recommend external storage in production. When content can't be stored at all, log metadata and route review through people allowed to see the data.

</details>

<details>
<summary><b>Q: Why does a dashboard of status codes and latency miss most LLM failures?</b></summary>

Most LLM failures are successful HTTP calls carrying a wrong, unsafe or wasteful answer: hallucinated facts, skipped verification, ten extra tool calls. Status codes measure transport, not quality. You need content-aware signals: online evals, user feedback, and per-trace step and cost counts. Status and latency panels are still necessary for outages and rate limits.

</details>

<details>
<summary><b>Q: What happens if you compute Claude costs from <code>input_tokens</code> alone on a cache-heavy agent?</b></summary>

Anthropic reports cache reads and writes separately from `input_tokens`, so a call with 8,000 cached and 900 uncached tokens shows only 900. Your token totals undercount by about 90%, your cache hit rate can't be computed, and the cost estimate leaves out cache hits (billed at a fraction of the input rate) and cache writes (billed at a premium). The GenAI conventions require summing all three into `gen_ai.usage.input_tokens` and recording cached tokens separately, then pricing each kind at its own rate. OpenAI's `input_tokens` already include cached tokens, so adding them again would double-count there.

</details>

<details>
<summary><b>Q: Head sampling vs tail sampling: which should you use to catch rare agent failures?</b></summary>

Tail sampling, because it decides after the trace completes and can keep every error, slow trace and judge-flagged trace, plus a random share for unbiased rates. Head sampling decides before anything has happened, so at 5% it drops 95% of the rare failures. Tail sampling costs buffering and Collector infrastructure. For low-traffic apps, keep everything and skip sampling.

</details>

<details>
<summary><b>Q: Why adopt the OTel GenAI conventions while they're still in Development status?</b></summary>

Because the alternative is N×M: every library's private attribute names mapped by every backend (P11). Backends such as Datadog, Langfuse, LangSmith and Phoenix already ingest OTel-shaped GenAI spans, so instrumenting once keeps the backend swappable. The cost is churn: names like `gen_ai.system` and the cache-write attribute have already been renamed. Pin the convention version, isolate attribute names in one module, and plan for upgrades.

</details>

<details>
<summary><b>Q: Explicit vs implicit feedback: how should you use each?</b></summary>

Explicit feedback is clear in meaning but sparse, self-selected and skewed toward severe problems. Implicit signals (retries, rephrasing, abandonment, accepted suggestions) are plentiful but ambiguous proxies. Use both to pick traces for human review and to cross-check online evals, and attach them to trace IDs. Don't make either one the quality metric you optimize, or Goodhart's law will optimize the proxy instead of the product.

</details>

<details>
<summary><b>Q: What can go wrong when a coding agent can read production traces?</b></summary>

Traces contain user- and tool-supplied text, so instructions planted in them can steer the agent (P9), and with write access that becomes an incident. Traces are also huge, so dumping them into context wastes the attention budget (P3). Give the agent read-only, least-privilege query tools that return summaries and specific spans, and redact PII before it can see anything. Used that way, traces are a strong sensor for verifying fixes against measured behavior (P8).

</details>

## 28. Data Flywheels and Synthetic Data

<details>
<summary><b>Q: Why is a labeled set of your product's failures a more durable asset than the model you use?</b></summary>

The model is rented: competitors use the same weights, and you will replace it within months (P12). A labeled failure set encodes your users' real distribution and your judgments of good and bad, which nobody else has. It carries over to the next model, as the eval that validates the migration and as few-shot or training data. The cost is expert labeling time and regular refreshes, and raw unlabeled logs don't count.

</details>

<details>
<summary><b>Q: What would happen if you split support tickets into train and test sets randomly by row?</b></summary>

Customers file near-identical tickets, so near-duplicates land on both sides of the split. A fine-tune or few-shot selector effectively sees test answers, and the test score measures memorization rather than generalization. Split by account, conversation or time, and run near-duplicate checks across splits before each run. A random row split is fine only when rows are truly independent, which is rare for user data.

</details>

<details>
<summary><b>Q: Thumbs-down vs user edits: which makes better training data, and why?</b></summary>

Edits. A thumbs-down says a response failed, but not why or what would have been right, and it comes from a biased sample of users. An edit puts the corrected version next to the model's draft, giving you a supervised target and a preference pair at once. Edits are biased too, since users fix only what blocks them. Treat thumbs as triage and edits as candidate labels that still get reviewed.

</details>

<details>
<summary><b>Q: Why can't you get more diverse synthetic data from current Claude models by raising the temperature, and what do you do instead?</b></summary>

Current Claude models reject non-default temperature ([§02](02-how-llms-work.md)). Even where it's allowed, temperature only spreads probability across nearby phrasings of the typical answer; it doesn't invent new user types or tasks. Diversity has to come from conditioning: vary personas, seeds, topics and difficulty, evolve seeds into harder variants, and filter near-duplicates. Then measure diversity (distinct-n, embedding spread, intent coverage) rather than assuming it.

</details>

<details>
<summary><b>Q: Does model collapse mean you should never train on synthetic data?</b></summary>

No. Shumailov et al. showed collapse when each generation trains indiscriminately on the previous generation's output, which under-samples rare events at every step until the tails vanish. Gerstgrasser et al. found that accumulating synthetic data alongside the original real data avoided collapse. So keep real data as the anchor, filter and verify synthetic rows, tag provenance and watch the synthetic share. Keep rare cases human-sourced, because collapse removes them first.

</details>

<details>
<summary><b>Q: Why should synthetic eval cases get more human review than synthetic training data?</b></summary>

An eval is a measuring instrument: one wrong label skews every later comparison, while a noisy training row is diluted among thousands. Synthetic cases also reflect the generator's picture of your users, and if a related model grades them, generator and grader can agree on the wrong answer. So review every synthetic eval item and cap the synthetic share. For bulk training data, sampled audits are enough.

</details>

<details>
<summary><b>Q: Why does lineage from trace to example matter for privacy?</b></summary>

When a user asks to be deleted, you must find everywhere their data went. With trace IDs, dataset versions and a record of which models trained on which versions, you can delete their rows and know which models need retraining. Without lineage you can't answer the question, and data trained into weights can't be removed surgically ([§17](17-memory.md)). It costs a few columns per row.

</details>

## 29. Adapting Models: Prompt Optimization, Fine-Tuning, Distillation, RL

<details>
<summary><b>Q: What does "low rank" mean in LoRA, and why does it cut training memory so much?</b></summary>

LoRA writes each weight update as a product B·A through r dimensions, so a 4096 × 4096 matrix trains 16 × 8,192 ≈ 131K parameters at r = 16 instead of 16.8M. Training state costs about 16 bytes per *trainable* parameter, while frozen weights cost 2 bytes each (about 0.5 in 4-bit with QLoRA), so an 8B model drops from about 128 GB to 17 GB, or 5 GB. The tradeoff is capacity: when a task needs more change than the rank allows, as with large datasets, LoRA falls behind full fine-tuning.

</details>

<details>
<summary><b>Q: Why not fine-tune your product documentation into the model instead of using RAG?</b></summary>

Fine-tuning absorbs new facts slowly and, once it does, increases hallucination (Gekhman et al.), and retrieval beat it for adding knowledge (Ovadia et al.). A fine-tuned model also can't cite its source and goes stale with the next doc edit, while RAG stays fresh and checkable (P5). Fine-tune only for how to use the retrieved documents: format, tone, citation style.

</details>

<details>
<summary><b>Q: What would happen if you ran RFT on a task where the model currently scores 0%?</b></summary>

Nothing useful. RL raises the probability of samples that score above the group average, and if every sample scores zero, none does, so there is no gradient signal. Make the task reachable first: add context or tools, decompose it, or run SFT on demonstrations. Partial-credit graders can help, but every new way to score is a new way to hack the score.

</details>

<details>
<summary><b>Q: How is an RL environment different from an agent eval?</b></summary>

Structurally it isn't: both are a task, tools, a sandbox and a verifier. The difference is where the score goes, into a report or back into the weights as a reward. That raises the stakes on the verifier, because an optimizer actively searches for ways to fool it, as with `sys.exit(0)` faking passing tests. It also means you can't use the same environment as a held-out eval after training on it.

</details>

<details>
<summary><b>Q: Why might a fine-tune that beats your prompt today be worthless in a year?</b></summary>

It is tied to its base model, and provider fine-tunes shut down with it: OpenAI's GPT-4.1 fine-tunes end on Jan 14, 2027. Meanwhile newer stock models often match the tuned behavior at the same price or lower (P12). So payback has to come well inside the base model's remaining life. Keep the training data and evals, so retraining or deleting is a measured decision.

</details>

<details>
<summary><b>Q: Your fine-tune gained 8 points on the target metric, but users say it got worse at everything else. What happened?</b></summary>

Catastrophic forgetting: updates for the new task overwrote shared weights other skills relied on, and your eval measured only the target task. Retrain with LoRA, mixed-in general data, a lower learning rate or fewer epochs, and a pull toward the reference model. Then add regression suites for instruction following, formats and safety so the next run can't ship with the same blind spot.

</details>

## 30. Cost, Latency, and Reliability

<details>
<summary><b>Q: Why does an agent's cost per task grow faster than linearly with its number of steps?</b></summary>

The model is stateless, so each step resends the system prompt, the tools and the entire history, and the history grows every step, so total input grows with roughly the square of the step count. Caching reprices the resent prefix but doesn't stop the resending, so cutting steps still pays. A workflow with a fixed, small number of calls doesn't have this problem.

</details>

<details>
<summary><b>Q: What would happen to your bill if a deploy added the current date to the top of the system prompt?</b></summary>

Every request's prefix would differ from the cached one at the first changed byte, so cache reads fall to zero and every request pays full input price plus write premiums. Nothing errors, so only the usage fields or the bill reveal it. Put volatile values after the last breakpoint and alert on hit rate.

</details>

<details>
<summary><b>Q: 429 vs 529: why should your client treat them differently?</b></summary>

A 429 means you exceeded your own per-model quota and usually carries `retry-after`, so wait that long or use a model with its own limit. A 529 means the provider is overloaded for everyone, so back off, and switching models or providers may get you served sooner. A spend-cap 429 has no `retry-after` and must not be retried at all.

</details>

<details>
<summary><b>Q: Cascade vs a single model at lower effort: which should you try first, and why?</b></summary>

Lower effort first. It keeps one prompt, one cache and one quality profile, and lower effort often holds quality on routine work. A cascade adds a confidence check that can be wrong, bills failed cheap attempts, adds latency on escalation and splits the cache. Use one when you have a reliable external check and a large price gap between models.

</details>

<details>
<summary><b>Q: What would go wrong if you added a semantic cache to a customer-support agent?</b></summary>

Similar-looking questions can need opposite answers, and an answer personalized for one customer can be served to another, which is a privacy breach. Answers also go stale and can be poisoned. Restrict it to non-personalized FAQ-style queries with tenant-scoped keys and short TTLs, or skip it.

</details>

<details>
<summary><b>Q: Why isn't "HTTP 200 rate" a good availability SLI for an LLM feature?</b></summary>

A 200 can carry a refusal, a truncated answer, invalid JSON or a fluent wrong answer. Count a good event only when the response is complete, valid and on time, and add a sampled quality SLI because correctness is statistical (P4). The error budget then tells you when a cheaper model is acceptable.

</details>

<details>
<summary><b>Q: Why should retries of a side-effecting tool carry an idempotency key when model-call retries don't need one?</b></summary>

A model call changes nothing at the provider, so a retry only costs money and a new sample. A tool that sends email or moves money may have succeeded before the timeout, so a blind retry doubles the effect. A key derived from the task and step lets the downstream service deduplicate; read-only tools can skip it.

</details>

## 31. Open-Weight Models and Self-Hosting

<details>
<summary><b>Q: Why is a model with downloadable weights usually called "open-weight" rather than "open source"?</b></summary>

You get the parameters, a config and a tokenizer, so you can run and fine-tune the model, but usually not the training data or full training code, so you can't rebuild or fully audit it. The OSI's Open Source AI Definition requires data information, code and parameters. The practical consequence is in the license, which can still restrict use, as Llama 4's 700-million-user clause does.

</details>

<details>
<summary><b>Q: Why does the KV cache, not the weights, often decide how many GPUs you need?</b></summary>

Weights are a fixed cost, but the KV cache grows with context length times concurrent sequences, and a 70B dense model needs about 320 KiB per token. Sixteen 32K-token sequences need about 160 GiB, more than the 16-bit weights. Architectures with fewer KV heads or sliding-window layers, and 8-bit KV caches, shrink that term.

</details>

<details>
<summary><b>Q: What would happen if you sized self-hosted GPUs for peak traffic on a spiky interactive workload?</b></summary>

The GPUs would sit mostly idle off-peak, so you pay for capacity you use perhaps a third of the time, and cost per token ends up above a hosted API that pools many customers' peaks. Self-hosting wins on cost with flat, high-utilization load, such as batch jobs, or when privacy forces it regardless of price.

</details>

<details>
<summary><b>Q: GPTQ/AWQ vs FP8: when would you pick each?</b></summary>

FP8 quantizes weights and activations to 8-bit floats, uses H100-class FP8 math, and is effectively lossless in the largest study, so it is a safe default on new GPUs. GPTQ and AWQ store weights in 4 bits and expand them for the math, halving memory again and helping latency-bound serving, at a small, task-dependent quality risk. Choose 4-bit when memory is the constraint, and confirm with your own eval.

</details>

<details>
<summary><b>Q: Why isn't an "OpenAI-compatible" endpoint a guarantee that your app will work on a new model?</b></summary>

Compatibility standardizes the request and response envelope (P11), not the behavior inside it. Tool-call reliability, chat templates, reasoning fields and structured-output support differ by model and server. Swapping the base URL is quick, but you still have to re-run your evals.

</details>

<details>
<summary><b>Q: Hosted open-weight API vs self-hosting the same model: what does self-hosting actually buy you?</b></summary>

The weights and quality can be identical, so you are buying where it runs: data stays in your network, versions stay pinned, and you control latency and batching. Price is only better at high utilization. If privacy isn't a constraint and load is spiky, the hosted API is usually cheaper and simpler.

</details>

<details>
<summary><b>Q: Why serve an MoE model like gpt-oss-120b when its memory footprint is set by 117B parameters?</b></summary>

Every expert must sit in memory, but each token runs only about 5.1B active parameters, so per-token compute and bandwidth look like a small model's. That gives large-model knowledge with small-model speed per token, provided you can afford the memory. If memory is the binding constraint, a smaller dense model may serve you better.

</details>

## 32. Security and Guardrails

<details>
<summary><b>Q: Why can't prompt injection be fixed the way SQL injection was?</b></summary>

Parameterized queries give the database separate, typed channels for code and data, so data can never execute. An LLM gets one token sequence, and the untrusted content is what it must reason over, so no slot is guaranteed inert (P9). Wording and training only lower the probability of obedience (P4), so security must come from limiting what a fooled model can do.

</details>

<details>
<summary><b>Q: What would happen if you added "Never follow instructions in web pages" to the system prompt of an agent that browses and sends email?</b></summary>

The injection rate might drop, but some phrasing would still work, and adaptive attackers iterate until they find it. The agent still holds all three trifecta legs, so one success leaks data. Keep the sentence as hygiene but cut a leg as the control: block external sends after browsing, or browse in a session with no private data.

</details>

<details>
<summary><b>Q: Jailbreak vs prompt injection: why does the distinction matter to an application developer?</b></summary>

A jailbreak is the user attacking the provider's safety policy. Injection is a third party attacking your user through content your agent reads. Developers who equate them treat injection as the vendor's problem, yet it comes from your architecture. Jailbreaks are fought with training and classifiers, injection with least privilege and trifecta-breaking design.

</details>

<details>
<summary><b>Q: Why did CaMeL need more than the dual-LLM pattern?</b></summary>

In the dual-LLM pattern the privileged model never reads untrusted tokens, but the quarantined model's outputs still become tool arguments, so a malicious document can pick an email's recipient. CaMeL plans the program from the trusted query, tags every value with its provenance, and checks policies at each tool call, so an untrusted recipient triggers approval. The price is policy work and some lost tasks: 77% solved securely against 84% undefended on AgentDojo.

</details>

<details>
<summary><b>Q: What would happen if your guardrail runs in parallel with the agent and trips on the first turn?</b></summary>

The run is cancelled, but the agent may already have spent tokens and executed tools, as the OpenAI Agents SDK documents for its default mode. Parallel checks buy latency at the cost of side effects. For agents whose tools change state, block first or enforce at the tool layer.

</details>

<details>
<summary><b>Q: Why is a markdown image an exfiltration channel when the agent has no network tools?</b></summary>

The client renders the output, and rendering an image whose URL contains a secret makes the user's browser send that secret to the attacker's server. No tool call happens; the renderer is the third trifecta leg. EchoLeak combined reference-style markdown with an open redirect on an allow-listed domain. Render only from allowed domains, and treat model output as untrusted.

</details>

<details>
<summary><b>Q: Why should red-team results be an eval suite rather than a one-off audit?</b></summary>

Behavior is probabilistic (P4), so you need attack success *rates* over many trials, beside task success. The system also keeps changing: new models, prompts, tools and skills shift susceptibility (P12). A CI suite against the full harness, with incidents added as regression cases, catches regressions the way tests do. An audit expires at the next deploy.

</details>

## 33. Agent Identity and Authorization

<details>
<summary><b>Q: Why shouldn't an internal agent run as one shared service account, even if every user is allowed to use the agent?</b></summary>

The account's permissions apply whoever is asking, so any user, or any document the agent reads, can steer it into actions the requester couldn't take: a confused deputy (P9). Logs show only the service account, an attribution gap. Delegated tokens with the user in `sub` keep the agent inside that user's rights, so row-level security and audit still work. A shared principal suits only system jobs that no user drives.

</details>

<details>
<summary><b>Q: What would happen if an MCP server forwarded the client's token straight to the GitHub API?</b></summary>

That is token passthrough, which MCP forbids. GitHub would receive a token not issued for that hop, so audience-dependent controls are bypassed, logs blame the wrong party, and a stolen token can use the server as a proxy. The server should accept only tokens issued to itself and call GitHub as its own OAuth client with a separate token.

</details>

<details>
<summary><b>Q: How does PKCE protect the authorization code flow, and what would an attacker with an intercepted code lack?</b></summary>

The client sends only the SHA-256 challenge up front and keeps the verifier. Redeeming the code requires the verifier, which the authorization server hashes and compares. An attacker who intercepts the redirect has the code but not the verifier, so the token request fails. That is why OAuth 2.1 requires PKCE and MCP clients refuse servers without S256 support.

</details>

<details>
<summary><b>Q: Delegated vs autonomous authority: when should an agent be its own principal?</b></summary>

Use delegated authority for any action on a user's data: rights are the user's permissions intersected with the granted scopes, and audits name both parties. Use autonomous authority for work with no user in the loop, such as nightly triage, where the agent's own grants are the only limit and must be narrow. Many agents mix the two, acting as themselves for system tasks and with a delegated token when they touch a person's data.

</details>

<details>
<summary><b>Q: Why must credentials never enter the model's context, even for a model you trust?</b></summary>

Trusting the model doesn't mean trusting everything it reads. An injected instruction can make it copy a secret into a tool argument, a URL or its reply (P9), and context also lands in logs and traces. With a harness-side broker or an egress vault, a hijacked agent can only request tool calls. The harness executes them with a short-lived, narrow token the model never sees, so there is nothing to steal.

</details>

<details>
<summary><b>Q: What does a valid Agent Card signature prove, and what doesn't it?</b></summary>

The JWS over the canonicalized card proves it came from the key holder and wasn't altered, so a forged "Admin Helper" card fails. It doesn't prove the publisher is trustworthy, that the agent behaves as its skills claim, or that its output is safe to act on. You still need a publisher allow-list, per-request authentication and authorization, and treatment of remote output as untrusted ([§32](32-security-guardrails.md)).

</details>

<details>
<summary><b>Q: Why isn't a user's click on "Approve" in the agent's UI the same as authorization?</b></summary>

The click happens in software the agent controls and leaves nothing a resource server can verify; a hijacked or buggy client could fake it. Authorization means the authorization server issues a token or step-up grant that the resource server checks, and the WIMSE draft requires binding approvals to such an event, for example via CIBA. Keep UI approvals as a usability layer on top of real scopes.

</details>

## 34. Governance and Regulation

<details>
<summary><b>Q: Why does the EU AI Act attach most duties to use cases rather than to models?</b></summary>

Risk comes from where an output lands, not from the weights: the same model is harmless filtering spam and consequential ranking applicants. Behavior is probabilistic and can't be certified in advance (P4), so the Act scales duties to the stakes of the intended purpose. The model layer gets lighter GPAI duties (documentation, copyright policy, and evaluations for systemic-risk models), because the model provider can't foresee every downstream use.

</details>

<details>
<summary><b>Q: You sell a CV-screening assistant, built on a vendor's model API, to EU employers. What are you, and what applies when?</b></summary>

You are the provider of a high-risk system (Annex III, employment), and each employer is a deployer. The vendor is the GPAI provider. If the assistant talks to candidates, Art. 50 disclosure has applied since Aug 2, 2026, and the high-risk requirements apply from Dec 2, 2027 under the 2026 amendments. Build the logging and oversight now, and confirm the details with counsel.

</details>

<details>
<summary><b>Q: What would happen if your audit log stored the inputs and the model ID but not the outputs?</b></summary>

You couldn't reconstruct what the system actually said. A model call is sampled (P4), so rerunning the inputs can give a different answer, and the model may be retired by the time someone asks. Lineage tells you *how* an output was produced, but only the stored output tells you *what* it was, so store it (or a hashed reference to it).

</details>

<details>
<summary><b>Q: Reviewers approve 99.8% of recommendations at about two seconds each. Do you have human oversight?</b></summary>

On paper, yes. In substance, probably not. Art. 14 expects overseers who can interpret outputs, resist automation bias and override, and that approval rate and speed suggest nobody is evaluating anything. Seed known-bad cases to test whether reviewers catch them, show evidence instead of verdicts, and cut review volume so that each review gets attention.

</details>

<details>
<summary><b>Q: NIST AI RMF vs ISO/IEC 42001: what does each give you?</b></summary>

The NIST AI RMF is a voluntary vocabulary and practice guide (Govern, Map, Measure, Manage), and its Generative AI Profile lists twelve risks to work through. ISO/IEC 42001 is a management-system standard that a third party certifies, which proves you *run* an AI risk process. Teams often use NIST to decide what to do and ISO 42001 to demonstrate that they do it. Neither alone satisfies the AI Act.

</details>

<details>
<summary><b>Q: When does fine-tuning a vendor model make you a GPAI model provider?</b></summary>

Under the Commission's indicative criterion, when your modification uses more than one third of the original model's training compute, and even then your duties cover only the modification. Typical fine-tuning, especially LoRA, is far below that. You are much more likely to pick up obligations through the use case: a model fine-tuned for hiring makes the *system* high-risk, whatever the compute.

</details>

<details>
<summary><b>Q: A team says, "high-risk dates moved to 2027, so governance can wait." What's wrong with that?</b></summary>

Prohibitions, AI literacy and Art. 50 transparency already apply. The controls the high-risk rules require (inventory, tiering, reconstructable logs, eval gates, an incident runbook) take time to build and are good engineering anyway. Logging retrofitted in 2027 leaves you with no records of 2026.

</details>

## 35. AI UX and Generative UI

<details>
<summary><b>Q: Why does streaming make a response feel faster when the total generation time is unchanged?</b></summary>

Decode is sequential, so tokens are produced one at a time anyway (P10). Streaming shows each one as it arrives, so perceived latency drops to time-to-first-token and the user reads while the model writes. The tradeoff is that you can't retract text already shown, and partial JSON or Markdown is invalid until the end. Buffer instead when an output must pass a check before anyone sees it.

</details>

<details>
<summary><b>Q: What would happen if every tool call an agent makes required human approval?</b></summary>

Users would get approval fatigue: after dozens of prompts they stop reading and click yes, so the approval looks like oversight and provides none. Anthropic found that sandboxing cut Claude Code's permission prompts by 84% by drawing the boundary once. Gate by risk instead: reads run freely, reversible writes run with undo, and only irreversible or external actions ask, with full arguments and a preview.

</details>

<details>
<summary><b>Q: Citations vs "trust me": what does an API citation guarantee, and what doesn't it?</b></summary>

Anthropic's citations guarantee valid pointers: `cited_text` really exists at that location in the documents you supplied. They don't guarantee that the quote supports the claim next to it, or that the documents are right. Their value is that they make checking cheap, one click to the source span, which is what turns verification from a burden into a habit (P8).

</details>

<details>
<summary><b>Q: Why validate a model-emitted UI spec even when structured outputs guarantee the JSON matches your schema?</b></summary>

A schema guarantees shape, not meaning. A well-formed button can still trigger `drop_table` because injected text steered the model (P9), and a valid table can still have 10,000 rows. The renderer and action handlers are your code (P6), so they enforce the catalog, the allowed actions, size limits and escaping, and they send every clicked action through normal authorization.

</details>

<details>
<summary><b>Q: MCP Apps vs a declarative component catalog: when would you pick each?</b></summary>

A catalog (ChatKit widgets, A2UI) keeps the model inside components you built, which makes it consistent, accessible and easy to secure, but it is only as expressive as the catalog. MCP Apps lets a server ship a full interactive HTML app, such as a map, an editor or a live dashboard, isolated in a sandboxed iframe whose actions still pass the host's consent path. Use a catalog for structured answers in your own product, and MCP Apps when a third-party tool needs rich interactivity across many hosts.

</details>

<details>
<summary><b>Q: Thumbs vs edits: which feedback signal is more useful, and why?</b></summary>

Edits, usually. Thumbs are sparse and skewed toward extreme reactions, while the diff between the AI's draft and what the user actually sent shows exactly what was wrong, on nearly every interaction, with no extra effort from the user. Either signal is worthless if it can't be joined to the trace that produced the response, so log feedback with trace IDs and turn the patterns into eval cases.

</details>

<details>
<summary><b>Q: Why can a friendlier, more human-like assistant produce worse outcomes?</b></summary>

Human cues (names, faces, emotional language, simulated typing) trigger social trust, so users over-rely on fluent output and check it less. That is automation bias, which NIST and the EU AI Act both name. Because outputs are probabilistic (P4), unchecked reliance means unchecked errors. Disclose that it is an AI, show evidence, and keep friction proportional to stakes. Warmth is fine when it doesn't stand in for reliability.

</details>

## 36. AI Product Thinking

<details>
<summary><b>Q: Why is "verification is cheaper than generation" the first test for an AI use case?</b></summary>

Because the human time saved is roughly the time to do the task minus the time to check the AI's output (P8). If checking takes a minute and doing takes twenty, AI drafting pays even when some drafts are discarded. If checking takes as long as doing, a careful person must redo the work to trust it, so the AI adds cost. Tasks with computational checks (tests, schemas, totals) are the best candidates, and tasks only an expert can verify slowly are the worst.

</details>

<details>
<summary><b>Q: What would happen if you launched a support agent and reported only its deflection rate?</b></summary>

You would count every customer who gave up as a success. Deflection measures contacts that didn't reach a human, not problems solved, so a frustrating bot can raise it. Pair it with repeat-contact rate, resolution checks and satisfaction, and keep tracking them after launch. Klarna's case shows that a strong deflection headline doesn't settle whether quality held up.

</details>

<details>
<summary><b>Q: Automate vs augment: when should a feature keep a human approving every output?</b></summary>

When errors are costly, silent or irreversible and no computational check can catch them: refunds, contract terms, medical or legal content. Approval puts the verifier where mistakes can't be undone (P8). The costs are human time and rubber-stamping, so make each check fast and show the evidence. Automate step by step as evals show high success rates and the remaining errors become cheap.

</details>

<details>
<summary><b>Q: Why might "wait" be the best answer to a build-vs-buy question?</b></summary>

Because scaffolding that works around a weak model tends to be deleted when a better model arrives (P12), and verifiable tasks are the ones labs improve fastest. Waiting means building the eval, data access and integration now, since all of them survive model changes, and re-running the eval on each release. It's the wrong answer when timing matters competitively and a narrower version works today.

</details>

<details>
<summary><b>Q: Why do AI demos overstate value, and what closes the pilot-to-production gap?</b></summary>

A demo is one sample (P4) on hand-picked inputs, with an expert fixing errors and nobody paying for review or failures. Production adds the long tail, volume, latency and cost limits; LinkedIn reached 80% quality in a month and spent four more months trying to pass 95%. The gap closes through evals on sampled production inputs, error analysis, and feedback loops that let the system learn from its own usage, not through a better demo.

</details>

<details>
<summary><b>Q: Why is per-seat pricing risky for an agent product?</b></summary>

Because cost per user isn't fixed (P10). Agents take a variable number of turns and heavy users consume many times the tokens of light ones, so a flat seat price can turn negative on your best customers. Usage pricing tracks cost but makes bills unpredictable. Outcome pricing aligns price with value, but only when success is clearly measurable and you can absorb failed attempts.

</details>

<details>
<summary><b>Q: Is your company's data a moat for an AI product?</b></summary>

Usually not in the form people mean, because generic documents add little that a frontier model or a competitor lacks. What compounds is data only your product produces: outcome-labeled traces, human corrections, and an eval set of your domain's failures. The eval set is the most durable of these, because it survives model changes (P12) and lets you adopt better models quickly. It's a moat only if the flywheel actually turns usage into improvements.

</details>

## 37. Why X over Y

<details>
<summary><b>Q: You're building an internal Q&amp;A bot over 300 pages of HR policy that every employee may read, updated quarterly, answering a few hundred questions a day. Long context or RAG, and why?</b></summary>

Long context with prompt caching. The corpus is small, stable and readable by everyone, so RAG's main advantages (scale, freshness, per-user filtering) don't apply, and caching makes the repeated prefix cheap as long as questions arrive within the cache lifetime (P10). You also skip a retrieval pipeline that could miss the right clause. Switch to RAG if traffic is too sparse to keep the cache warm and the per-question cost hurts, if context rot shows in your evals as the corpus grows (P3), or if some documents become restricted to certain employees.

</details>

<details>
<summary><b>Q: You're building search for a support assistant where customers paste error codes like "E-4012" alongside natural-language questions. Vector or hybrid search, and why?</b></summary>

Hybrid. Embeddings capture topic, so "E-4012" and "E-4021" can land close together, while BM25 matches the exact token. Fusing both with reciprocal rank fusion and reranking the top results covers paraphrased questions and exact codes. The cost is a second index. Vector-only is fine only if your query logs show that exact identifiers rarely matter.

</details>

<details>
<summary><b>Q: You're building a nightly job that classifies 2 million product reviews into 12 categories on a tight budget. Which model and output setup do you choose, and why?</b></summary>

A small model at low or no reasoning effort, strict structured outputs with an enum of the 12 labels, and the batch API. The task is single-step classification, so thinking tokens add cost without accuracy (P10), the grammar guarantees a valid label, and batch pricing halves the bill because nobody is waiting. Validate on a labeled sample first. If one or two categories are genuinely ambiguous, route only low-confidence items to a bigger model.

</details>

<details>
<summary><b>Q: You're building an agent to refactor a large codebase, and a colleague proposes five parallel agents, each editing its own module. Single or multi-agent, and why?</b></summary>

A single writer, possibly helped by read-only subagents. Refactoring is tightly coupled: each edit carries implicit decisions about interfaces and naming, and parallel writers make conflicting ones (Cognition's lesson). Google's study measured multi-agent setups at 39–70% worse on sequential work. Use subagents to explore and summarize the modules in parallel, and keep one agent writing. Parallel writers make sense only for truly independent changes, each verified separately.

</details>

<details>
<summary><b>Q: You're automating invoice processing: extract fields, match them to the purchase order, route anything over $10,000 to a manager, then pay. Graph or agent loop, and why?</b></summary>

An explicit graph. The steps are known, the approval is business structure that should never depend on a model's choice, and you need checkpoints and an audit trail (P7). Extraction is a structured-output node with code checks such as totals and PO match. The approval is a durable interrupt that shows the full details, and payment runs only after it. If mismatches need open-ended investigation, put an agent inside that one node rather than making the whole process agentic.

</details>

<details>
<summary><b>Q: You're building an agent to file 50 expense reports a week in a legacy desktop app that has no API. Which interface do you choose, and why?</b></summary>

Computer use in a disposable VM, because no API exists, but plan to replace it. Every step costs screenshot tokens and compounds error risk (P8, P10), and the screen is untrusted input (P9). Have a human approve before each final submit, and verify the end state outside the GUI if you can. Because the flow repeats, have the agent author a script once and run that script, re-authoring it when the UI changes. If the vendor ever offers an API, switch to it.

</details>

<details>
<summary><b>Q: Your eval for a summarization feature must catch summaries that invent facts. Code grader or LLM judge, and why?</b></summary>

Mostly an LLM judge, because checking whether each claim is supported by the source requires reading meaning, which code can't do. Give it one narrow binary question (is every claim supported?), keep it separate from the summarizer, and calibrate it on at least 50 labeled passes and 50 labeled fails, measuring true positive and true negative rates before trusting its numbers. Add code graders for whatever a program can decide: length, required sections, that quoted strings appear in the source. Never tune prompts against an uncalibrated judge.

</details>

<details>
<summary><b>Q: You're building a voice agent for a bank's card-replacement line, with identity verification and strict audit requirements. Cascaded or speech-to-speech, and why?</b></summary>

Cascaded. Every step produces inspectable text, so you can log the transcript, run evals on it, apply guardrails before tool calls such as blocking the card, and swap components if needed (P8). You pay in latency because the stages add up (P10), so stream every stage and keep responses short. Speech-to-speech fits better where conversational feel matters more than auditability.

</details>

<details>
<summary><b>Q: Your agent's system prompt holds 40 internal procedures, about 60,000 tokens, and quality is dropping. What do you change, and why?</b></summary>

Move the procedures into skills and keep only short, universal rules in the system prompt. Every call currently pays for all 40 procedures while using one, and the irrelevant ones dilute attention (P3), which caching doesn't fix. As skills, the idle cost is about 100 tokens each, and a body loads only when its description matches. Because triggering is probabilistic (P4), write descriptions that say what and when, test them, and keep any rule that must always apply in the system prompt.

</details>

<details>
<summary><b>Q: A healthcare client requires that patient data never leave their network, and the workload is steady, high-volume document extraction. Hosted API or self-hosting, and why?</b></summary>

First check whether a hosted model available inside the client's own cloud account, with private networking, meets the requirement, since that keeps frontier quality without running GPUs. If not, self-host open weights. The steady volume keeps GPUs utilized, which is what makes self-hosting pay (P10), and extraction suits a smaller tuned or constrained model. Budget for operations, and evaluate quantized models against your extraction evals before switching.

</details>

## 38. The Disciplines and Skills Map

<details>
<summary><b>Q: Why do new "X engineering" labels keep appearing?</b></summary>

Because each label marks where the bottleneck moved. As models absorb more of one layer's work (P12), the hard part moves outward: from the words, to everything the model sees, to the system around the model, to the human attention needed to drive it. The old layer doesn't disappear; it becomes a component of the new one.

</details>

<details>
<summary><b>Q: How are prompt, context, harness, and loop engineering related?</b></summary>

They nest. The prompt is part of the context. The harness produces the context on every call, along with tools, sandboxes, and feedback. The loop drives the harness without a human prompting each run. Graph engineering sits beside this stack, because it is about who owns control flow (P7) rather than what the model sees.

</details>

<details>
<summary><b>Q: Is "graph engineering" the same as GraphRAG?</b></summary>

No. Graph engineering means structuring agent control flow as a state machine: nodes, edges, cycles, checkpoints ([§14](14-graph-engineering.md)). GraphRAG builds a knowledge graph of entities and relationships from documents in order to answer whole-corpus questions ([§09](09-rag.md)). They share a word and nothing else.

</details>

<details>
<summary><b>Q: How would you decide whether a new label is a real discipline?</b></summary>

Ask whether it names a distinct bottleneck, has its own artifacts, has its own failure modes, and can be taught without naming a product. Context and harness engineering pass all four. A label that only renames "doing it carefully", or can only be explained through one vendor's tool, is marketing.

</details>

<details>
<summary><b>Q: Why is loop engineering called "emerging" when people have run agents in loops since 2023?</b></summary>

The practice is old and real: AutoGPT looped, and Huntley's Ralph loop (Jul 2025) is a bash `while` loop. What's new is a named set of practices around it, such as separate stop-condition checkers, back pressure, parallel worktrees, and scheduled automations. That set was only named in mid-2026 and overlaps heavily with harness engineering. Its boundaries are still being worked out.

</details>

<details>
<summary><b>Q: Which AI engineering skill do most newcomers underestimate?</b></summary>

Verification and evals (P4, P8). Making a model produce something is easy. Knowing whether it is right, at what rate, and catching regressions when the model or prompt changes is where most of the engineering goes. Error analysis on real traces is the skill that separates working systems from demos.

</details>

<details>
<summary><b>Q: What is the biggest mental shift for someone coming from data engineering?</b></summary>

Accepting that correctness is a rate, not a fact (P4). Many habits carry over directly: idempotency becomes durable execution, the log becomes the session event log, DAGs become graphs, and quality tests become evals. But an LLM feature passes "94% of the time on this distribution," so you have to measure, not assert.

</details>
