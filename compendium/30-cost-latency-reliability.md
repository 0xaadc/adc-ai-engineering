# 30. Cost, Latency, and Reliability

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This is Part 8, production, and it applies to every era: a single classification call from 2022 and a 2026 multi-agent research system both pay per token, wait on decode and depend on a shared remote service. [§29](29-adapting-models.md) ended with a better-adapted model, but that model still has to answer within a budget, within a latency target and through the provider's outages. The driving principle is P10 (every token costs compute and time). P4 (sampled output) changes what "reliable" means, P8 (errors compound) explains why agents amplify every failure, and P11 (standard interfaces) is why gateways exist. The inference mechanics behind the numbers are in [§03](03-inference.md); this section covers the engineering built on top of them.

## Why this exists

A prototype makes a few hundred calls and nobody looks at the bill. Production makes millions, and three properties that were invisible in the demo start to dominate.

1. **Cost is linear in tokens, and agents resend everything.** The model is stateless (P2), so every turn resends the system prompt, the tool schemas and the whole history. Anthropic's cost guide puts it plainly: "A 40-turn task sends its first turn 40 times, so task cost grows with roughly the square of turn count."
2. **Latency is serial.** One response costs time to first token plus one decode step per output token ([§03](03-inference.md)). An agent pays that once per step, in sequence.
3. **The dependency is remote, shared, rate-limited and probabilistic.** A database call either succeeds or throws. A model call can return a 429, a 529, a timeout, an error halfway through a stream, a refusal with HTTP 200, a truncated answer, or a well-formed answer that is simply wrong (P4).

It is the familiar move from a notebook query to a scheduled pipeline with SLAs, except that "correct" can only be measured statistically.

## How it works (under the hood)

### Unit economics: cost per request, per task, per user

Every Anthropic `usage` object has four meters: uncached `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens` and `output_tokens` ([§03](03-inference.md)). Everything else is arithmetic over three units:

- **Cost per request** is what the price list describes, and it is the least useful number.
- **Cost per completed task** is what you actually buy. A cheaper model that needs more turns, retries or a human cleanup is not cheaper. Anthropic's guide says to compare models "on cost per completed task, not per token."
- **Cost per user per month** is what the business sees. Five agent tasks a day at $0.42 each comes to about $46 per user over 22 working days. Against a $20 subscription that is a negative gross margin, whatever the per-token price.

Agents multiply tokens. Anthropic measured agents at about 4× the tokens of chat and multi-agent systems at about 15× ([§13](13-multi-agent.md)). Those are averages; a deep loop sits far above them because input grows with the square of the turn count. A cost model makes this concrete:

```python
# USD per million tokens, Claude API list prices as of Oct 2026 (check the pricing page).
PRICES = {  # base input, 5-min cache write, cache read, output
    "claude-haiku-5-5":  {"in": 0.10, "write": 0.125, "read": 0.01, "out": 0.50},
    "claude-sonnet-5-5": {"in": 2.00, "write": 2.50,  "read": 0.10, "out": 10.00},
    "claude-opus-5-5":   {"in": 4.00, "write": 5.00,  "read": 0.20, "out": 20.00},
}

def task_cost(model, turns, prefix, in_per_turn, out_per_turn, hit_rate=None):
    """Cost of one task. Each turn resends everything so far (P2) plus new input."""
    p, usd, total_in = PRICES[model], 0.0, 0
    history = prefix                                   # system prompt + tool schemas
    for _ in range(turns):
        total_in += history + in_per_turn
        if hit_rate is None:                           # caching off: all input at base price
            usd += (history + in_per_turn) * p["in"]
        else:                                          # resent part hits or misses; new part is written
            usd += history * (hit_rate * p["read"] + (1 - hit_rate) * p["write"])
            usd += in_per_turn * p["write"]
        usd += out_per_turn * p["out"]
        history += in_per_turn + out_per_turn          # the context grows every turn
    return usd / 1e6, total_in + turns * out_per_turn

WORKLOADS = {  # ASSUMED shapes: replace with numbers from your own logs
    "chat (6 turns)":   dict(turns=6,  prefix=2_000, in_per_turn=150,   out_per_turn=400),
    "agent (25 steps)": dict(turns=25, prefix=8_000, in_per_turn=1_500, out_per_turn=300),
}
for name, w in WORKLOADS.items():
    for hit in (None, 0.5, 0.9):
        usd, tokens = task_cost("claude-sonnet-5-5", hit_rate=hit, **w)
        label = "no cache" if hit is None else f"hit {hit:.0%}"
        print(f"{name:17s} {label:9s} {tokens:>9,} tok  ${usd:.4f}/task"
              f"  ${usd * 10_000 * 30:>9,.0f}/mo at 10k tasks/day")
usd, _ = task_cost("claude-haiku-5-5", hit_rate=0.9, **WORKLOADS["agent (25 steps)"])
print(f"agent on Haiku 5.5, hit 90%: ${usd:.4f}/task (only if it still completes the task)")
```

```text
chat (6 turns)    no cache     23,550 tok  $0.0663/task  $   19,890/mo at 10k tasks/day
chat (6 turns)    hit 50%      23,550 tok  $0.0526/task  $   15,772/mo at 10k tasks/day
chat (6 turns)    hit 90%      23,550 tok  $0.0331/task  $    9,940/mo at 10k tasks/day
agent (25 steps)  no cache    785,000 tok  $1.6300/task  $  489,000/mo at 10k tasks/day
agent (25 steps)  hit 50%     785,000 tok  $1.1307/task  $  339,225/mo at 10k tasks/day
agent (25 steps)  hit 90%     785,000 tok  $0.4204/task  $  126,105/mo at 10k tasks/day
agent on Haiku 5.5, hit 90%: $0.0243/task (only if it still completes the task)
```

Read the shape. This 25-step agent uses 33× the tokens of the chat session, far above the 4× average, because of the quadratic resend. Caching cuts the agent's cost almost 4×, more than most model choices would. The Haiku line is 17× cheaper, but it means nothing until an eval shows Haiku finishes the task ([§26](26-evals.md)).

### The levers, in order

Anthropic's cost guide splits levers into **free wins**, which cut spend without touching quality (caching, token hygiene, batch, spend limits), and **tradeoffs**, which exchange capability for cost (effort, output caps, model choice). Apply the free wins first, and the tradeoffs only against an eval.

#### Prompt caching and cache-aware layout

[§03](03-inference.md) covers the mechanism: the server keeps the KV cache of a prompt prefix and reuses it when a request starts with byte-identical tokens. These operational details decide whether you get the discount **(GA)**:

- **Pricing (Oct 2026).** A write costs 1.25× base input for the default 5-minute lifetime, or 2× for 1 hour. A read costs 0.1× on most models, 0.05× on Claude Opus 5.5 and Sonnet 5.5, and 0.025× on Claude Fable 5.1. A 5-minute write pays for itself after one read, and the discounts stack with the Batch API.
- **Lifetimes.** Each read refreshes the timer for free, but the lifetime counts from the *start* of a request, so generation time uses it up. The 1-hour TTL pays only when gaps between requests sharing a prefix fall between 5 and 60 minutes.
- **Concurrency.** An entry becomes readable only once the first response begins. Fan out 20 parallel requests over one prefix and all 20 pay to write it. Send one, wait for its first token, then send the rest.
- **Scope.** Caches are per organization (per workspace on the Claude API) and per model, because a KV cache is computed from one model's weights. A model switch always starts cold.
- **Throughput.** On most Claude models, cache reads don't count toward the input-tokens-per-minute rate limit, so a high hit rate also raises your effective limit.

Cache-aware layout is a stability ordering, like partitioning a table by the column you filter on most:

```text
[tools: sorted, fixed] [system: frozen, no timestamps] [docs/few-shot] ◆ [history ...] ◆ [new turn]
 └──────────── changes never ─────────────┘└ per deploy ┘   └── grows append-only ──┘
◆ = cache breakpoint. Any byte change at position N invalidates everything after N.
```

Silent breakers include a timestamp in the system prompt, unordered JSON keys, a per-user tool list, a model switch, a change of top-level effort, and every context-editing pass. Anthropic treats a loop hit rate below about 80% as a sign of a breaker, and says a well-built loop deep in a task "pays full price on under 1% of its input." Monitor `cache_read_input_tokens` continuously, because regressions arrive with later prompt changes.

#### Batch APIs and flex tiers

Batching ([§03](03-inference.md)) is the provider's core economic lever. A batch API lets it schedule your work into idle capacity, and it passes on part of the saving.

- **Anthropic Message Batches (GA):** 50% off input and output, stacking with cache discounts; up to 100,000 requests or 256 MB per batch. Most finish within an hour, anything unfinished at 24 hours expires, and results are kept for 29 days. Each request is single-shot, so no tool loop runs inside a batch.
- **OpenAI Batch API (GA):** 50% off, a 24-hour completion window, and a separate rate-limit pool.
- **OpenAI flex processing (Preview, beta, limited models):** set `service_tier: "flex"` on an ordinary synchronous call and pay Batch rates, in exchange for slower responses and occasional uncharged `429 Resource Unavailable` errors. OpenAI suggests backing off, or retrying on the standard tier when finishing matters more than price.

Evals, backfills, enrichment and nightly jobs all qualify.

#### Model choice, routing and cascades

**Routing** classifies a request up front and sends it to the cheapest adequate handler. Chip Huyen notes that a router "typically consists of an intent classifier", which can also answer out-of-scope queries with a canned reply "without wasting an API call". Anthropic lists routing as a basic workflow ([§12](12-agentic-design-patterns.md)). A **cascade** tries a small model first and escalates on low confidence:

```text
request → small model → confidence check ─ok──→ answer
                              └─low──→ large model → answer
cost = small + P(escalate) × large        latency = small + P(escalate) × large
```

FrugalGPT (2023) learned cascades that matched GPT-4 "with up to 98% cost reduction" on its benchmarks, and RouteLLM (2024) cut costs "by over 2 times in certain cases" without losing quality. The hard part is the confidence check. Good signals are external, such as schema validation ([§06](06-structured-outputs.md)), tests or a verifier; a model's own claim of confidence is weak evidence (P8).

Cascades also bill the failed cheap attempt, add latency on escalation and split your prefix across caches. Measure the simpler option first: one model at a lower **effort** level ([§04](04-reasoning-models.md)). Anthropic reports that running a coding benchmark at low effort and re-running only the failures (detected by tests) at `high` held the pass rate at about half the cost.

#### Output length, context trimming and thinking budgets

- **Output** costs 5× input on every current Claude model. Specify the output shape, with an example, or use structured outputs. `max_tokens` is a backstop the model never sees, and a truncated answer is a failed attempt you paid for. Anthropic found 64,000 covered all but 2 of 14,000 measured turns at default effort.
- **Context trimming** ([§16](16-context-engineering.md)) reduces what each turn resends, but every edit invalidates the cache from that point. In Anthropic's measured run, context editing "cost more than it saved." Trim to fit the window and fight context rot (P3), in a few large passes rather than every turn.
- **Thinking** is billed as output. Control it with the `effort` level **(GA)** and, for whole loops, task budgets **(Preview)** ([§04](04-reasoning-models.md)). Pin effort per route, because changing it between requests invalidates the cache.

#### Semantic caching, and why it is risky

Three caches are often confused:

| Cache | Key | What it skips | Correctness risk |
|---|---|---|---|
| Prompt (KV) cache | Exact token prefix | Prefill only; the model still answers | None: same output distribution |
| Exact response cache | Hash of the full request | The whole call | Stale or personalized answers replayed |
| Semantic cache | Embedding similarity above a threshold | The whole call | Wrong answer to a different question |

A semantic cache embeds each query ([§08](08-embeddings-and-search.md)) and returns the nearest cached query's answer if similarity clears a threshold. Huyen calls its value "more dubious because many of its components are prone to failure." "Cancel my order" and "don't cancel my order" embed close together; a personalized answer can reach another user, a privacy incident; answers go stale; an attacker can seed a poisoned entry (P9). Cloudflare's AI Gateway caches only identical requests (as of Sep 2026), while Azure API Management offers semantic caching. If you use one, scope keys by tenant, cache only non-personalized requests, keep TTLs short and measure false hits (P4).

### The data engineering analogy: warehouse sizing as a cost dial

Snowflake doubles the credit rate with each warehouse size and bills per second, so a query that parallelizes well costs about the same on a bigger warehouse and finishes sooner, yet "Larger is not necessarily faster for small, basic queries." Model tiers behave the same way: a larger model costs more per token but may finish in fewer turns, while a simple classifier gains nothing from a frontier model. Cache TTL plays the role of auto-suspend, and spend caps are resource monitors. Size per workload and measure cost per finished job.

### Latency: actual vs perceived

Total time for one call is roughly TTFT plus output tokens × TPOT ([§03](03-inference.md)). Users perceive something else: how soon something useful appears, and whether progress is visible.

- **Streaming** doesn't cut total time, but it turns a 20-second wait into a 1-second wait followed by reading. For agents, stream progress and tool activity too ([§35](35-ai-ux.md)).
- **TTFT levers:** a warm prefix cache skips most prefill. For interactive apps, pre-warm with a `max_tokens: 0` request at startup so the first real request isn't cold.
- **Total-time levers:** fewer output tokens, lower effort, a smaller model, or a faster tier (fast mode **(Preview)**, [§03](03-inference.md)).
- **Agent latency is a sum of serial hops**, so cut the hops:

```text
serial:    [LLM]→[tool A]→[LLM]→[tool B]→[LLM]→[tool C]→[LLM]      7 hops
parallel:  [LLM]→[tool A | tool B | tool C]→[LLM]                  3 hops
```

  Claude can emit several `tool_use` blocks in one turn; run them concurrently and return all results in one message ([§10](10-tool-use.md)). Subagent fan-out does the same at a larger scale ([§13](13-multi-agent.md)).
- **Speculative execution** starts work the model will probably ask for, such as retrieving documents while the model plans. **Hedged requests** (Dean and Barroso, "The Tail at Scale", 2013) send a backup request only when the first is running slow; with LLMs each hedge duplicates the token bill, and only side-effect-free calls are safe to hedge.
- **Regional endpoints** matter mostly for data residency, since network round trips are small next to generation, except in voice ([§25](25-voice-agents.md)). On Anthropic, `inference_geo: "us"` keeps inference in the US at 1.1× token prices.

Budget for p95 and p99, not the mean: provider queueing under load adds latency no prompt change can fix.

### Reliability

#### Know your failure types

| Signal | Meaning | Retry? |
|---|---|---|
| 429 `rate_limit_error` + `retry-after` | You exceeded RPM, ITPM or OTPM (token-bucket limits, per model), or ramped up too fast ("acceleration limits") | Yes, after `retry-after` |
| 429 with `enforced_spend_limit_reached`, no `retry-after` | Your org hit its monthly tier spend cap | No: it fails until access resumes |
| 529 `overloaded_error` | Anthropic is overloaded across all users | Yes, with backoff; consider another model or provider |
| 500 / 504 | Internal error / processing timeout | Yes; stream long requests |
| 400 / 401 / 403 / 404 / 413 | Your request or credentials are wrong | No: fix it |
| Error event after HTTP 200 (streaming) | The stream failed midway | Yes, as a new request |
| `stop_reason: "refusal"` (HTTP 200) | Safety classifiers declined | Not on the same model |
| `stop_reason: "max_tokens"` | Truncated | Not at the same cap |

Other providers draw the lines differently. OpenAI returns 429 for rate limits and also for `credit_balance_exhausted`, which must not be retried, and 503 `server_is_overloaded` for overload. Gemini uses 429 `RESOURCE_EXHAUSTED` and 503 `UNAVAILABLE`. Retry logic has to read the error type, not just the status code.

#### Retries: backoff, jitter, deadlines, one layer

- **Exponential backoff** doubles the wait after each failure, giving a struggling service room to recover.
- **Jitter** randomizes the wait. Without it, clients that failed together retry together and knock the service over again. AWS measured "Full Jitter" (a uniform random wait up to the backoff cap) cutting total calls by more than half with 100 contending clients.
- **Retry at one layer.** AWS's Builders' Library shows five layers that each try three times multiplying load on the bottom layer 243×. The Anthropic SDKs already retry twice by default (connection errors, 408, 409, 429, 5xx), honoring `retry-after`. If your loop or gateway also retries, set the SDK's `max_retries=0`.
- **Deadlines beat attempt counts.** SDK timeouts are themselves retried, so wall-clock time can reach `timeout × (max_retries + 1)`. A client-side timeout also doesn't prove the provider did no work, and you may still be billed for it **(⚠ verify)**.

```python
import os
import random
import time

import anthropic

# max_retries=0: this function owns retries, so the SDK's own retries don't multiply with ours.
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0, timeout=60.0)
CHAIN = ["claude-sonnet-5-5", "claude-haiku-5-5"]   # primary first; each model has its own rate limit
RETRYABLE = {408, 429, 500, 502, 503, 504, 529}

def full_jitter(attempt, base=1.0, cap=20.0):
    return random.uniform(0, min(cap, base * 2 ** attempt))  # random spread breaks retry synchrony

def create_with_fallback(messages, attempts_per_model=3, deadline_s=60.0):
    start = time.monotonic()
    for model in CHAIN:
        for attempt in range(attempts_per_model):
            try:
                msg = client.messages.create(model=model, max_tokens=1024, messages=messages)
                if msg.stop_reason == "refusal":       # HTTP 200 but declined: a failure all the same
                    break                              # same model, same answer: try the next one
                return msg
            except anthropic.APIStatusError as e:
                if e.status_code not in RETRYABLE or "spend_limit" in str(e.body):
                    raise                              # bad request, auth, or spend cap: retrying can't help
                if e.status_code == 529 and attempt >= 1:
                    break                              # provider still overloaded: move down the chain
                hinted = e.response.headers.get("retry-after")
                wait = float(hinted) if hinted else full_jitter(attempt)
            except anthropic.APIConnectionError:       # network failure or client-side timeout
                wait = full_jitter(attempt)
            if time.monotonic() - start + wait > deadline_s:
                raise TimeoutError("retry budget spent")   # the caller degrades gracefully
            time.sleep(wait)
    raise RuntimeError("every model in the chain failed")
```

It obeys the server's `retry-after`, refuses to retry errors that can't succeed, and stops at a deadline rather than an arbitrary count. OpenAI's SDK has the same shape, with `openai.RateLimitError` and `openai.APIStatusError`.

#### Fallbacks across models and providers

- **Model fallback** within a provider helps with 429s, because rate limits are per model.
- **Provider fallback** survives an outage. Claude is also served through Amazon Bedrock, Google Cloud and Microsoft Foundry, with platform-specific features and pricing; a cross-vendor fallback means a different model family.
- **Refusal fallback:** Anthropic's server-side `fallbacks` parameter **(Preview)** retries a declined request on a model recommended for that refusal category.

Prompts aren't portable, so a fallback is only as good as its eval results (P4). Run the same eval set against every model in the chain, and log which model served each request so dashboards don't silently mix them ([§27](27-observability.md)).

#### AI gateways and routers

Once several teams call several models, every app reimplements keys, retries, logging and fallbacks for every provider: the N×M problem (P11). A **gateway** is the shared layer. Huyen's GenAI platform post defines it as "an intermediate layer that allows your organization to interface with different models in a unified and secure manner", with access control, cost management, fallbacks, load balancing, logging and sometimes caching and guardrails.

```text
apps ──► GATEWAY ──► Anthropic / Bedrock / Vertex / OpenAI / self-hosted (§31)
          ├ virtual keys per team (real keys never leave the gateway)
          ├ quotas and budgets per key, team, user
          ├ routing, retries, cooldowns, fallbacks
          └ logs, traces, cost attribution (§27); optional caching, guardrails (§32)
```

- **LiteLLM** (open source) is a Python router and proxy with load balancing, cooldowns, fallbacks, timeouts and retries, plus virtual keys with spend tracking and budgets.
- **OpenRouter** (hosted) is one API over many providers. A `models` array falls back in priority order, and a `provider` object controls ordering, fallbacks, price or latency sorting, and data-retention filters.
- **Cloud gateways** include Cloudflare AI Gateway (analytics, logging, caching, rate limiting, retries, model fallback) and Azure API Management's AI gateway (per-consumer token limits and quotas, load balancing, semantic caching).

The costs are an extra hop, a new single point of failure that needs its own redundancy, and a lowest-common-denominator API. Provider-specific features such as cache breakpoints, thinking blocks or citations may not survive translation, so test them end to end.

#### Idempotency, degradation and spend caps

A model call changes nothing at the provider, so a retry is safe for correctness, but you pay again and get a new sample. Side effects live in your tools (P6), and a retried "send email" needs an **idempotency key** derived from the task and step ID, like an exactly-once sink ([§20](20-agent-runtime.md)). Give batch requests deterministic `custom_id`s so reprocessing results is an upsert.

Decide in advance what users get when the model path fails: fallback model → cached or precomputed answer → non-AI path → queue for later → an honest "try again". Shed load by priority so interactive users keep capacity. Prefer a retry budget to a hair-trigger circuit breaker, which, AWS warns, can "introduce modal behavior into systems that can be difficult to test."

The classic LLM cost incident is a loop that never stops, such as an agent retrying a failing tool all night. Defend in layers:
1. **Provider caps.** On Anthropic, an organization or workspace spend limit; requests over a self-set limit fail with a 400, and batches can overshoot slightly.
2. **Gateway budgets** per key, team or user.
3. **Application caps:** maximum turns per task, task budgets **(Preview)**, per-user quotas ([§21](21-loop-engineering.md)).
4. **Alerts on rates:** p95 cost per task, tokens per turn and turns per task, by route and model, fed by usage logs or Anthropic's Usage and Cost Admin API.

#### SLOs for probabilistic systems

The Google SRE book defines an **SLI** (a measured indicator), an **SLO** (its target) and an **error budget** (the allowed shortfall, which you can spend on risk). The difference for LLMs is that HTTP 200 no longer means success. Count a "good event" only if the call didn't error, wasn't truncated or refused, passed schema validation and met its latency target, then add a statistical quality SLI:

| SLO family | Example SLI | Measured by |
|---|---|---|
| Availability | Requests answered by any model in the chain | Gateway logs |
| Latency | p95 TTFT < 1.5 s; p95 task time < 60 s | Traces |
| Quality | ≥ 95% of sampled responses pass the rubric, rolling 7 days | Online evals ([§26](26-evals.md), [§27](27-observability.md)) |
| Cost | p95 cost per completed task < $0.50 | Usage logs joined to outcomes |

Quality is sampled because you can't unit-test a distribution (P4). For agents, also track pass^k, the chance that all k trials succeed, since P8 compounds every per-step miss. The error budget becomes a cost lever: moving a route to a cheaper model is allowed as long as the quality SLO holds.

### Failure modes

- **Silent cache regression:** a new field in the system prompt drops the hit rate to zero; nothing errors, and the bill quadruples.
- **Retry storms:** retries without jitter, or at several layers, turn a blip into an outage.
- **Runaway loops** with no cap on turns or spend.
- **Silent fallback degradation:** the backup model serves 30% of traffic for a week and quality drops unnoticed.
- **Retrying the unretryable:** spend-cap 429s and 400s burn time and hide the cause.

## Comparison

| Lever | Mechanism | Typical effect | Tradeoff | When not to use |
|---|---|---|---|---|
| Prompt caching | Reuse prefix KV cache | Large on loops; reads 0.025–0.1× input | Write premium; strict prefix match | Prompts differ from the first tokens; gaps over 1 h |
| Batch / flex | Provider fills idle capacity | 50% off (batch); batch rates (flex) | Hours, not seconds; no tool loops in batch | A user is waiting |
| Lower effort | Fewer thinking tokens, terser tool use | Often large on routine work | Quality loss on hard tasks | Hard coding without a measured sweep |
| Routing / cascade | Cheap model for easy inputs | Over 2× in RouteLLM's tests | Router errors, escalation latency, split caches | No reliable confidence signal |
| Output shaping | Fewer output tokens (5× price) | Proportional to output share | Possible loss of detail | Output is already short |
| Context trimming | Fewer resent tokens | Helps long sessions | Breaks the cache at each edit | Short loops |
| Semantic cache | Skip the call for similar queries | High on FAQ-like traffic | False hits, leakage, staleness | Personalized, agentic or fast-changing answers |

| Reliability pattern | Protects against | Cost | Pitfall |
|---|---|---|---|
| Backoff + jitter + deadline | Transient 429/5xx, unbounded waits | Latency | Retrying at several layers |
| Model / provider fallback | Rate limits, outages | Eval and prompt upkeep per model | Untested fallback quality |
| Gateway | N×M integration, key sprawl | Extra hop, new dependency | Lost provider-specific features |
| Idempotency keys | Duplicate side effects | Key plumbing | Missing a non-obvious side effect |
| Spend caps + alerts | Runaway loops | Hard failure at the cap | Caps without alerts surprise users |

## What it didn't solve

All of these levers assume someone else's model on someone else's servers. Past some volume the per-token price exceeds what the hardware would cost you, and some data can't leave your network at all, for regulatory, contractual or residency reasons. Pinning a model version forever, serving a custom fine-tune cheaply or running offline also requires the weights themselves. For that, you run models yourself.

→ Next: [§31 Open-Weight Models and Self-Hosting](31-open-weights-self-hosting.md)

## Check your understanding

**Q: Why does an agent's cost per task grow faster than linearly with its number of steps?**

The model is stateless, so each step resends the system prompt, the tools and the entire history, and the history grows every step, so total input grows with roughly the square of the step count. Caching reprices the resent prefix but doesn't stop the resending, so cutting steps still pays. A workflow with a fixed, small number of calls doesn't have this problem.

**Q: What would happen to your bill if a deploy added the current date to the top of the system prompt?**

Every request's prefix would differ from the cached one at the first changed byte, so cache reads fall to zero and every request pays full input price plus write premiums. Nothing errors, so only the usage fields or the bill reveal it. Put volatile values after the last breakpoint and alert on hit rate.

**Q: 429 vs 529: why should your client treat them differently?**

A 429 means you exceeded your own per-model quota and usually carries `retry-after`, so wait that long or use a model with its own limit. A 529 means the provider is overloaded for everyone, so back off, and switching models or providers may get you served sooner. A spend-cap 429 has no `retry-after` and must not be retried at all.

**Q: Why add jitter to exponential backoff?**

Clients that failed together would otherwise retry together and recreate the spike. Randomizing each wait spreads the retries, and AWS measured total calls more than halved under contention. Jitter can't fix retries that multiply across layers, so retry in one place.

**Q: Cascade vs a single model at lower effort: which should you try first, and why?**

Lower effort first. It keeps one prompt, one cache and one quality profile, and lower effort often holds quality on routine work. A cascade adds a confidence check that can be wrong, bills failed cheap attempts, adds latency on escalation and splits the cache. Use one when you have a reliable external check and a large price gap between models.

**Q: What would go wrong if you added a semantic cache to a customer-support agent?**

Similar-looking questions can need opposite answers, and an answer personalized for one customer can be served to another, which is a privacy breach. Answers also go stale and can be poisoned. Restrict it to non-personalized FAQ-style queries with tenant-scoped keys and short TTLs, or skip it.

**Q: Why isn't "HTTP 200 rate" a good availability SLI for an LLM feature?**

A 200 can carry a refusal, a truncated answer, invalid JSON or a fluent wrong answer. Count a good event only when the response is complete, valid and on time, and add a sampled quality SLI because correctness is statistical (P4). The error budget then tells you when a cheaper model is acceptable.

**Q: Why should retries of a side-effecting tool carry an idempotency key when model-call retries don't need one?**

A model call changes nothing at the provider, so a retry only costs money and a new sample. A tool that sends email or moves money may have succeeded before the timeout, so a blind retry doubles the effect. A key derived from the task and step lets the downstream service deduplicate; read-only tools can skip it.

## Takeaways

- Measure cost per completed task and per user, not per token (P10).
- Agent input grows with the square of the turn count; caching and fewer serial steps are the big levers.
- Apply free wins first (caching, batch, hygiene, spend caps), then tradeoffs (effort, model, cascades) against an eval.
- Lay out prompts by stability and monitor `cache_read_input_tokens`; regressions are silent.
- Streaming fixes perceived latency; parallel tool calls and fewer steps fix actual latency.
- Retry with backoff, jitter and a deadline at one layer, and read the error type before retrying.
- Gateways turn N×M provider plumbing into one layer, but you must make them redundant.
- An LLM feature's SLO needs a statistical quality SLI on top of availability, latency and cost.

## Sources

- Anthropic, Pricing (cache, batch, data residency multipliers): https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic, Optimizing for cost and intelligence: https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence
- Anthropic, Prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Anthropic, Batch processing: https://platform.claude.com/docs/en/build-with-claude/batch-processing
- Anthropic, Rate limits (token bucket, ITPM/OTPM, spend limits): https://platform.claude.com/docs/en/api/rate-limits
- Anthropic, Errors (429, 529, retries, long requests): https://platform.claude.com/docs/en/api/errors
- Anthropic, Refusals and fallback: https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback
- Anthropic, Usage and Cost Admin API: https://platform.claude.com/docs/en/manage-claude/usage-cost-api
- Anthropic, "How we built our multi-agent research system" (Jun 2025): https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic, "Building effective agents" (Dec 2024): https://www.anthropic.com/engineering/building-effective-agents
- OpenAI, Batch API: https://developers.openai.com/api/docs/guides/batch
- OpenAI, Flex processing: https://developers.openai.com/api/docs/guides/flex-processing
- OpenAI, Error codes: https://developers.openai.com/api/docs/guides/error-codes
- Google, Gemini API troubleshooting (retry strategy): https://ai.google.dev/gemini-api/docs/troubleshooting
- Chip Huyen, "Building a Generative AI Platform" (Jul 2024): https://huyenchip.com/2024/07/25/genai-platform.html
- Chen, Zaharia and Zou, "FrugalGPT" (2023): https://arxiv.org/abs/2305.05176
- Ong et al., "RouteLLM" (2024): https://arxiv.org/abs/2406.18665
- Marc Brooker, "Exponential Backoff and Jitter" (AWS Architecture Blog): https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- AWS Builders' Library, "Timeouts, retries, and backoff with jitter": https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
- Dean and Barroso, "The Tail at Scale" (CACM 2013): https://research.google/pubs/the-tail-at-scale/
- Google SRE book, "Service Level Objectives": https://sre.google/sre-book/service-level-objectives/
- LiteLLM, Routing: https://docs.litellm.ai/docs/routing ; Virtual keys: https://docs.litellm.ai/docs/proxy/virtual_keys
- OpenRouter, Model fallbacks: https://openrouter.ai/docs/guides/routing/model-fallbacks ; Provider selection: https://openrouter.ai/docs/guides/routing/provider-selection
- Cloudflare AI Gateway: https://developers.cloudflare.com/ai-gateway/ ; Caching: https://developers.cloudflare.com/ai-gateway/features/caching/
- Microsoft, AI gateway capabilities in Azure API Management: https://learn.microsoft.com/en-us/azure/api-management/genai-gateway-capabilities
- Snowflake, Warehouse overview (size and credits): https://docs.snowflake.com/en/user-guide/warehouses-overview
