# 27. Observability and Tracing

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

Observability applies from the API era onward ([§05](05-api-and-prompting.md)): once your code calls a model in production, you need to see those calls. It matters most for agents ([§11](11-agents.md)), where one user request becomes dozens of model and tool calls along a path the model chose (P7). Like evals, it is a Part 7 discipline that cuts across eras. P2, P4, P8 and P10 explain why it's needed, and P11 explains why a standard is forming. [§26](26-evals.md) left the gap: offline evals miss what real users do in production. Observability is the record of what actually happened.

## Why this exists

Classic application monitoring (latency, error rate, a stack trace) assumes failures are exceptions. An LLM failure is usually an HTTP 200 carrying a wrong answer, a skipped verification or a ten-step detour. Four mechanisms make LLM apps opaque without special tracing:

1. **The model is stateless (P2).** Everything it knew came in the request: system prompt, history, retrieved passages, tool results. That request *is* the explanation of its behavior, and if you didn't record it, you can't explain the behavior later.
2. **Output is sampled (P4).** Rerunning the request may not reproduce the failure, so you have to capture it when it happens.
3. **Agents choose their own path (P7) and errors compound (P8).** To find which of 30 steps went wrong, you need the whole tree of steps, not the final answer.
4. **Cost and latency vary per request (P10).** The same feature can cost 10× more when the agent takes more steps or the cache misses, and only per-request accounting shows it.

Data engineers know this gap as the difference between "the job succeeded" and "the data is right," the gap data-observability tools fill.

## How it works (under the hood)

### Traces and spans

A **trace** is the complete record of one request or task, from the user's input to the final response, including every model call, tool call and retrieval along the way (Husain and Shankar's definition). A **span** is one timed operation inside a trace. Each span carries a trace ID, its own span ID, its parent's span ID, a name, start and end times, a status and **attributes** (key-value pairs). Parent links make the spans a tree. Traces from one multi-turn conversation are grouped by a conversation or session ID. Vendors use these terms slightly differently, so check what a tool means by "trace" before comparing.

```text
trace 4bf92f…  "Where is order 1234?"                                     2.41 s   $0.0143
└─ invoke_agent support                                                   2.41 s
   ├─ chat claude-sonnet-5-5      in 8,900 (8,000 cached) / out 250 tok   0.92 s   stop=tool_use
   ├─ execute_tool lookup_order   {"order_id": "1234"} → {"status": …}    0.08 s
   ├─ retrieval policy_index      5 passages                              0.05 s
   └─ chat claude-sonnet-5-5      in 9,400 (8,900 cached) / out 140 tok   0.71 s   stop=end_turn
```

The numbers are illustrative. The spans in an LLM app are model calls (inference), tool executions, retrievals, embedding calls, agent invocations and workflow steps. Newer drafts of the conventions below add spans for memory operations, planning and loading Agent Skills ([§18](18-skills.md)).

### What to log

The rule follows from P2: log enough to reconstruct what the model saw and did.

| Field | Why | OTel GenAI attribute (draft names, Oct 2026) |
|---|---|---|
| Provider; model requested and model that answered | Aliases resolve to snapshots, and regressions follow silent changes | `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.response.model` |
| System prompt, messages, tool definitions | Replay and debugging | `gen_ai.system_instructions`, `gen_ai.input.messages`, `gen_ai.tool.definitions` (opt-in) |
| Output and why it stopped | Truncations, refusals, tool calls | `gen_ai.output.messages` (opt-in), `gen_ai.response.finish_reasons` |
| Tokens: input, output, cached, reasoning | Cost and cache hit rate | `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.reasoning.output_tokens` |
| Cost | Spend per task, user and feature | Not standardized; derive from tokens × the answering model's prices |
| Latency, time to first token | User experience; which step is slow | Span duration; `gen_ai.response.time_to_first_chunk` |
| Tool name, call ID, arguments, result | Debug tool misuse | `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.call.arguments` and `.result` (opt-in) |
| Conversation ID, prompt template and version | Group turns; tie quality to prompt versions | `gen_ai.conversation.id`; `gen_ai.prompt.name` and `.version` on the new repo's main branch |
| Errors | Rate limits, timeouts, tool failures | `error.type` |
| Your own context | Slicing and rollback | App version, harness config, experiment arm, pseudonymized user and tenant |

It's the bronze-layer habit from a medallion architecture: keep the raw record before you aggregate it.

### The OpenTelemetry GenAI semantic conventions

**OpenTelemetry (OTel)** is the open standard for telemetry. It provides SDKs that create traces, metrics and logs; a wire protocol, **OTLP**; and the **Collector**, a service that receives, processes and forwards telemetry. **Semantic conventions** are its agreed names for span names and attributes. Without them, every instrumentation library invents its own names (one says `prompt_tokens`, another `input_tokens`), and every backend has to map every library: N×M integrations. With them, each library emits one schema and each backend reads it: N+M (P11).

The GenAI conventions standardize:

- **Span names and kinds.** An inference span is named `{gen_ai.operation.name} {gen_ai.request.model}`, such as `chat claude-sonnet-5-5`, with kind CLIENT. Tool spans are `execute_tool {gen_ai.tool.name}` (INTERNAL), and agent spans `invoke_agent {gen_ai.agent.name}`.
- **Operation names** such as `chat`, `generate_content`, `embeddings`, `retrieval`, `execute_tool`, `create_agent` and `invoke_agent`.
- **Attributes,** as in the table above, with content capture opt-in.
- **Events,** including `gen_ai.evaluation.result` (with `gen_ai.evaluation.name`, `gen_ai.evaluation.score.value`, `.score.label` and `.explanation`), so online eval results attach to traces in a standard shape.
- **Metrics** for client operation duration and token usage, and server-side time to first token and time per output token.
- **Provider and protocol specifics** for Anthropic, OpenAI, AWS Bedrock, Azure AI Inference and MCP.

Their status needs care. Every GenAI convention is still marked **Development**, meaning not stable. In semantic-conventions v1.42.0 (June 2026), the GenAI conventions moved out of the core repository into a dedicated one, `open-telemetry/semantic-conventions-genai`, which had no tagged release as of mid-October 2026. Names keep changing. `gen_ai.system` became `gen_ai.provider.name`, and `prompt_tokens` became `input_tokens`. v1.41's `gen_ai.usage.cache_creation.input_tokens` is `gen_ai.usage.cache_write.input_tokens` on the new repository's main branch, where v1.41's single `gen_ai.client.token.usage` metric is split into per-type metrics. Instrumentations use the environment variable `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` to opt into the newest names. Adopting them is still worthwhile, because backends already ingest them (Datadog documents support for the 1.37+ GenAI conventions). Pin the convention version your instrumentation emits, and expect renames.

The conventions also settle a provider difference that breaks naive dashboards. Anthropic's `input_tokens` *excludes* cached tokens, and the Anthropic convention says the OTel total must be `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`. OpenAI's `input_tokens` already *includes* cached tokens, reported as a subset in `input_tokens_details.cached_tokens`. On a cache-heavy Claude agent, a dashboard that reads `input_tokens` alone sees 900 of 8,900 input tokens.

Arize's **OpenInference** is a parallel convention, "complementary to OpenTelemetry" and used by Phoenix. Datadog accepts both.

### Snippet: a minimal tracing decorator

This decorator turns nested function calls into spans with GenAI-style attributes. It shows the mechanism that an OTel SDK and an instrumentation package provide for you in production.

```python
import contextvars, functools, time, uuid

SPANS = []                                             # stand-in for an OTLP exporter
_current = contextvars.ContextVar("current_span", default=None)
NAME_KEYS = ("gen_ai.request.model", "gen_ai.tool.name", "gen_ai.agent.name")

def traced(operation, **attrs):  # nested calls become child spans of the same trace
    label = next((attrs[k] for k in NAME_KEYS if k in attrs), "")
    def decorate(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            parent = _current.get()
            span = {"name": f"{operation} {label}".strip(),     # e.g. "chat claude-sonnet-5-5"
                    "trace_id": parent["trace_id"] if parent else uuid.uuid4().hex,
                    "span_id": uuid.uuid4().hex[:16],
                    "parent_id": parent["span_id"] if parent else None,
                    "status": "OK", "attributes": {"gen_ai.operation.name": operation, **attrs}}
            token, start = _current.set(span), time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                if operation == "chat" and "usage" in result:  # only model-call spans carry usage
                    u, a = result["usage"], span["attributes"]
                    cached = u.get("cache_read_input_tokens", 0)
                    a["gen_ai.response.model"] = result["model"]
                    a["gen_ai.response.finish_reasons"] = [result["stop_reason"]]
                    a["gen_ai.usage.cache_read.input_tokens"] = cached
                    # Anthropic's input_tokens excludes cached tokens; OTel's total includes them
                    a["gen_ai.usage.input_tokens"] = (u["input_tokens"] + cached
                                                      + u.get("cache_creation_input_tokens", 0))
                    a["gen_ai.usage.output_tokens"] = u["output_tokens"]
                return result
            except Exception as exc:
                span["status"], span["attributes"]["error.type"] = "ERROR", type(exc).__name__
                raise
            finally:                                        # always close and export the span
                span["duration_s"] = time.perf_counter() - start
                _current.reset(token)
                SPANS.append(span)
        return wrapper
    return decorate
```

The `ContextVar` holds the current span, so a function called inside another traced function becomes its child, and it works across `async` code too. The `finally` block guarantees the span is exported even when the call raises, which is when you need it most. Only `chat` spans copy token usage. An earlier draft let any function that *returned* a model response record usage, so the agent span, which returns the final reply, counted that call twice. Parent spans duplicating child usage is a common real-world cost bug. Real OTel spans also carry a span kind and nanosecond epoch timestamps, and they're batched to a Collector over OTLP.

### Snippet: cost and latency aggregation

Spans are rows in an event table, and dashboards are `GROUP BY` queries over it. This continues the snippet above with a stubbed agent:

```python
import collections, random, statistics, time   # continues the decorator snippet above

PRICE = {"claude-sonnet-5-5": {"in": 2.00, "cache_read": 0.20, "out": 10.00}}  # USD per 1M tokens
SONNET = {"gen_ai.provider.name": "anthropic", "gen_ai.request.model": "claude-sonnet-5-5"}

@traced("chat", **SONNET)
def call_model(messages):  # stub that returns the Messages API response shape
    time.sleep(random.uniform(0.002, 0.009))              # pretend model latency
    return {"model": "claude-sonnet-5-5", "stop_reason": "end_turn",
            "usage": {"input_tokens": 900, "cache_read_input_tokens": 8000, "output_tokens": 250}}

@traced("execute_tool", **{"gen_ai.tool.name": "lookup_order"})
def lookup_order(order_id):
    return {"order_id": order_id, "status": "shipped"}

@traced("invoke_agent", **{"gen_ai.agent.name": "support"})
def support_agent(question):
    for _ in range(random.randint(1, 4)):                 # agents take a variable number of steps
        call_model([question])
        lookup_order("1234")
    return call_model([question])

def cost_usd(a):  # price cached and uncached input separately (cache writes ignored for brevity)
    p, cached = PRICE[a["gen_ai.response.model"]], a["gen_ai.usage.cache_read.input_tokens"]
    return ((a["gen_ai.usage.input_tokens"] - cached) * p["in"] + cached * p["cache_read"]
            + a["gen_ai.usage.output_tokens"] * p["out"]) / 1e6

for _ in range(50):
    support_agent("Where is order 1234?")
cost = collections.defaultdict(float)                     # trace_id -> dollars
for s in SPANS:
    if s["attributes"]["gen_ai.operation.name"] == "chat":
        cost[s["trace_id"]] += cost_usd(s["attributes"])
roots = [s for s in SPANS if s["parent_id"] is None]       # one root span per trace
lat = statistics.quantiles([r["duration_s"] * 1000 for r in roots], n=100)
print(f"traces={len(roots)}  cost/trace mean=${statistics.mean(cost.values()):.4f} "
      f"max=${max(cost.values()):.4f}  latency p50={lat[49]:.0f}ms p95={lat[94]:.0f}ms")
```

```text
traces=50  cost/trace mean=$0.0195 max=$0.0295  latency p50=18ms p95=35ms
```

Your numbers will differ, because step counts are random. Three habits show up even in a toy. Cost is aggregated per trace, because a task is what the user experiences and pays for, not a single call. Latency is reported as percentiles, because the p95 user waits about twice as long as the median one here. And the same fold works for any attribute: group by `gen_ai.response.model`, prompt version or customer slice. The prices are Claude Sonnet 5.5's per-million-token rates as of October 2026 ($2 input, $0.20 cache read, $10 output). With caching off, each call would bill all 8,900 input tokens at the full rate, about 3.4× the cost per call.

### Online evals and sampling

An **online eval** is a grader that runs asynchronously on finished production traces: a code check, or an LLM judge calibrated as in [§26](26-evals.md). It attaches its verdict to the trace, as a `gen_ai.evaluation.result` event or a vendor's score field. It is not a **guardrail**. Husain and Shankar draw the line: guardrails sit inline in the request path, are fast and usually deterministic, and block or redact before the user sees anything ([§32](32-security-guardrails.md)). Evaluators run afterwards and measure.

Judging every trace adds roughly one model call per trace, so you sample. Husain and Shankar list methods from exploratory to targeted: random (unbiased rates, but misses rare cases), clustering by content, extreme values (latency, tool count), classifier-flagged, and negative user feedback. Keep some random traces in every batch, so you can still discover failure modes your signals don't describe. Run cheap code checks on 100% of traffic for rare, high-stakes failures. Report online pass rates with intervals; their advice is to investigate when the interval's lower bound crosses your threshold.

Trace sampling is a separate decision from eval sampling. **Head sampling** decides at the start of a trace, for example keeping 5%. It's cheap, but OTel's docs note it can't guarantee keeping "all traces with an error." **Tail sampling** decides after the trace completes, typically in the Collector, so you can keep every error, slow trace and flagged trace plus a random share. Agent failures are rare and interesting, so tail sampling usually fits better. The GenAI conventions also say an instrumentation's content-upload hook should run "regardless of the span sampling decision," so prompts aren't lost just because a span was dropped. LangSmith and Langfuse, among others, ship online evaluators with configurable sampling (as of Oct 2026). Flagged traces go to an annotation queue, humans label them, and the labeled cases join the golden set: the loop [§28](28-data-flywheels.md) builds on.

### User feedback signals

**Explicit feedback** (thumbs, ratings, bug reports, corrections) is direct but sparse and self-selected, and it skews toward severe issues, as Anthropic notes. **Implicit feedback** is inferred from behavior: regenerating or retrying, rephrasing the same question, abandoning the session, copying the answer, accepting a code suggestion (and how much of it survives later edits), asking for a human, or the downstream outcome, such as whether the refund was actually processed. Attach every signal to the trace and span ID it refers to, so a thumbs-down points at the exact context the model saw. Implicit signals are proxies: a long conversation can mean engagement or frustration, and optimizing a proxy directly invites Goodhart's law. Use feedback to choose traces for review, and remember that it "misses problems that users do not report" (Husain and Shankar).

### Dashboards

Four panels cover most needs:

- **Quality:** online eval pass rates per failure mode and slice, with intervals, plus feedback rates.
- **Cost:** per completed task, per user and per feature, plus the cache hit rate (cached input ÷ total input).
- **Latency:** p50, p95 and p99 end to end, time to first token, and a per-span breakdown that shows whether the model or a tool is slow.
- **Errors:** provider errors and rate limits (HTTP 429), refusals, `max_tokens` truncations, tool errors, schema-validation failures and timeouts.

Agents add steps per task, tool error rate and stall or loop rate ([§21](21-loop-engineering.md)). Use percentiles, not means, and cost per completed task, not per request, since a cheaper call that needs more retries isn't cheaper.

### Alerting on drift

**Drift** means production moving away from what you evaluated. It comes in several kinds:

- **Input drift:** new topics, languages or document types; track input lengths and the shares of embedding clusters.
- **Output drift:** answer length, refusal rate, format failures, the mix of tools called.
- **Quality drift:** online eval pass rates falling.
- **Model drift:** `gen_ai.response.model` changing under an alias, or a provider deprecating a snapshot.
- **Cost and latency drift:** agents taking more steps, or the cache hit rate collapsing after a prompt edit puts a timestamp in the cached prefix ([§05](05-api-and-prompting.md)).

The mechanism is a comparison: a rolling window against a baseline, with the same interval logic as [§26](26-evals.md), per slice, firing only on sustained change to avoid alert fatigue. A drift alert should start error analysis on fresh traces, not an immediate prompt edit.

### Privacy: PII, redaction and retention

A trace store is a copy of everything users, documents and tools put into context: names, emails, health details, passages behind access controls ([§09](09-rag.md)), secrets in tool results. The GenAI conventions treat this as the default concern. Instrumentations "SHOULD NOT capture [content] by default" and offer three patterns: don't record content; record it on span attributes, "best suited" to pre-production or storage that already complies with privacy rules; or store content externally and record references on spans, recommended for production because "external storage enables separate access controls."

Redact at the source, in an in-process span processor before export, or in the Collector. Use regexes for structured identifiers (emails, card numbers), NER models (named-entity recognition, which tags names and places) for free text, and pseudonymous IDs for users. Redaction is itself probabilistic, so sample its output and check it: "Redaction tools can miss sensitive information" (Husain and Shankar). Keep raw content for less time than aggregate metrics, and key it by pseudonymous user ID so you can delete one person's data on request. Treat the trace store like a PII warehouse, with access control and audit, and remember that a SaaS backend is a data processor for whatever you send it. Traces also hold untrusted text, so a trace viewer that renders HTML, or an agent that reads traces, inherits prompt-injection risk (P9). Governance continues in [§32](32-security-guardrails.md) and [§34](34-governance-regulation.md).

### Agents reading their own traces

[§19](19-harness-engineering.md) introduced **agent legibility**: making the app's UI, logs and metrics readable by the agent. OpenAI's harness-engineering team gave each git worktree an ephemeral observability stack, so "agents can query logs with LogQL and metrics with PromQL," and prompts like "no span in these four critical user journeys exceeds two seconds" became tractable. Mechanically, telemetry becomes context (P2) and a **sensor** in Böckeler's sense: the agent checks its work against measured behavior instead of its own opinion (P8), which is the back pressure of [§21](21-loop-engineering.md). The same idea applies to debugging production: a coding agent with query access to the trace store can find the failing span. Several vendors document MCP servers for this, Langfuse and Braintrust among them (as of Oct 2026). Two principles constrain it. Traces are huge (P3), so give the agent query tools and summaries, not dumps. And traces contain user- and tool-supplied text (P9), so the debugging agent gets read-only, least-privilege access.

### The data-engineering analogy: lineage

Data observability watches freshness, volume, schema, distribution and lineage. The mapping is close. A trace is per-request lineage: which documents, tool results, model snapshot and prompt version produced this answer, much like an OpenLineage run event linking inputs, job and outputs. Drift alerts are distribution monitors, token dashboards are warehouse-credit monitoring, and content redaction is column masking. The analogy breaks in one place. Data lineage describes a dependency graph that holds for every run, while a trace records one sampled path (P4), and the next request may take another. Traces are evidence to aggregate statistically, not a fixed DAG.

### Failure modes

- **Metrics without content:** you know 4% of requests failed, not why.
- **Content without controls:** an ungoverned PII warehouse.
- **Wrong token math:** Anthropic's cached tokens left out, or parent spans double-counting child usage.
- **Head sampling** that drops the rare failures you most need.
- **Storage blow-up:** an agent re-sends its whole history every turn, so storing full content on every span grows quadratically with turns. Store deltas or references.
- **SDK lock-in:** proprietary instrumentation makes switching backends a rewrite. OTel-native instrumentation plus a Collector keeps the backend swappable.

## Comparison

**Vendor landscape (as of October 2026; capabilities change quickly, so check current docs)**

| Tool | What it is | License and hosting | OpenTelemetry | Worth knowing |
|---|---|---|---|---|
| LangSmith (LangChain) | Tracing, datasets, offline and online evals | Proprietary SaaS; self-hosting is an Enterprise add-on | Accepts OTel traces | Deepest LangChain and LangGraph integration; works without them |
| Langfuse | Tracing, prompt management, evals | Open source (MIT outside `ee/` directories); cloud or self-hosted | Built on OTel | Acquired by ClickHouse, which says no licensing changes are planned |
| Arize Phoenix | Tracing, evals, experiments | Source-available (Elastic License 2.0), self-hosted; managed version is Arize AX | OTel with OpenInference conventions | Same instrumentation works for Phoenix and AX |
| Braintrust | Evals and experiments plus production logging | Proprietary SaaS; self-hosted data plane on Enterprise | Accepts OTLP traces and logs | Eval-first design |
| W&B Weave (CoreWeave) | Tracing and evals | Apache-2.0 SDK; hosted service | OTel-compatible ingest | CoreWeave's docs name Agent Lens as Weave's successor |
| Datadog Agent Observability | LLM and agent traces and evals inside Datadog | Proprietary SaaS | Ingests OTel GenAI conventions 1.37+ or OpenInference | Docs still live under `llm_observability`; natural fit if you already use Datadog APM |

Choose on data residency and hosting, whether you need evals and datasets tied to traces, your existing stack, and how cleanly the tool ingests OTel, which decides how hard leaving will be.

**Content capture (OTel GenAI options)**

| Option | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Don't record (default) | Metadata and tokens only | No PII in telemetry | Can't debug or run content-based online evals | Highly sensitive domains, with other review paths |
| On span attributes | Prompts and outputs as `gen_ai.*.messages` attributes | Simple; everything in one place | Large, sensitive, one access model for all | Pre-production, or compliant storage |
| External storage + references | A hook uploads content; spans store a pointer | Separate access control and retention | More moving parts | Production |

**Trace sampling**

| Strategy | Decides | Strength | Weakness |
|---|---|---|---|
| Head (e.g. 5% of traces) | At trace start | Cheap, simple, whole traces | Blind to errors and outliers |
| Tail (in the Collector) | After the trace completes | Keeps every error, slow or flagged trace | Buffers traces; more infrastructure |

## What it didn't solve

Traces show you failures but don't fix them. A month of production leaves you flagged traces, feedback, labels and cost curves, all evidence of what went wrong. The next step turns that evidence into better data (golden sets, training sets, synthetic cases) and, where prompting isn't enough, better models.

→ Next: [§28 Data Flywheels and Synthetic Data](28-data-flywheels.md)

## Check your understanding

**Q: Why log the full request instead of just the user's message and the final answer?**

The model is stateless (P2), so the whole request (system prompt, history, retrieved passages, tool results) is everything that shaped the output. Without it you can't tell a retrieval bug from a prompt bug from a model mistake, and because output is sampled (P4) you can't reliably reproduce the failure later. The tradeoff is storage and privacy, which is why the conventions make content opt-in and recommend external storage in production. When content can't be stored at all, log metadata and route review through people allowed to see the data.

**Q: Why does a dashboard of status codes and latency miss most LLM failures?**

Most LLM failures are successful HTTP calls carrying a wrong, unsafe or wasteful answer: hallucinated facts, skipped verification, ten extra tool calls. Status codes measure transport, not quality. You need content-aware signals: online evals, user feedback, and per-trace step and cost counts. Status and latency panels are still necessary for outages and rate limits.

**Q: What happens if you compute Claude costs from `input_tokens` alone on a cache-heavy agent?**

Anthropic reports cache reads and writes separately from `input_tokens`, so a call with 8,000 cached and 900 uncached tokens shows only 900. Your token totals undercount by about 90%, your cache hit rate is meaningless, and costs are wrong in both directions, because cached tokens bill at a tenth of the input rate and cache writes at a premium. The GenAI conventions require summing all three into `gen_ai.usage.input_tokens` and recording cached tokens separately. OpenAI's `input_tokens` already include cached tokens, so the same code would double-count there.

**Q: Head sampling vs tail sampling: which should you use to catch rare agent failures?**

Tail sampling, because it decides after the trace completes and can keep every error, slow trace and judge-flagged trace, plus a random share for unbiased rates. Head sampling decides before anything has happened, so at 5% it drops 95% of the rare failures. Tail sampling costs buffering and Collector infrastructure. For low-traffic apps, keep everything and skip sampling.

**Q: Why adopt the OTel GenAI conventions while they're still in Development status?**

Because the alternative is N×M: every library's private attribute names mapped by every backend (P11). Backends such as Datadog, Langfuse, LangSmith and Phoenix already ingest OTel-shaped GenAI spans, so instrumenting once keeps the backend swappable. The cost is churn: names like `gen_ai.system` and the cache-write attribute have already been renamed. Pin the convention version, isolate attribute names in one module, and plan for upgrades.

**Q: Explicit vs implicit feedback: how should you use each?**

Explicit feedback is clear in meaning but sparse, self-selected and skewed toward severe problems. Implicit signals (retries, rephrasing, abandonment, accepted suggestions) are plentiful but ambiguous proxies. Use both to pick traces for human review and to cross-check online evals, and attach them to trace IDs. Don't make either one the quality metric you optimize, or Goodhart's law will optimize the proxy instead of the product.

**Q: What can go wrong when a coding agent can read production traces?**

Traces contain user- and tool-supplied text, so instructions planted in them can steer the agent (P9), and with write access that becomes an incident. Traces are also huge, so dumping them into context wastes the attention budget (P3). Give the agent read-only, least-privilege query tools that return summaries and specific spans, and redact PII before it can see anything. Used that way, traces are a strong sensor for verifying fixes against measured behavior (P8).

## Takeaways

- An LLM failure is usually a 200 OK with a wrong answer, so observability has to capture content, not just status and latency.
- A trace is a tree of spans (model calls, tool calls, retrievals, agent steps); log enough to reconstruct what the model saw (P2).
- The OTel GenAI conventions give these spans standard names (P11). They're still in Development and moved to their own repository in June 2026, so pin a version and expect renames.
- Get the token math right: Anthropic's `input_tokens` excludes cached tokens, OpenAI's includes them, and parent spans must not re-count child usage.
- Run online evals asynchronously on sampled traces, keep some random samples, prefer tail sampling for rare failures, and attach results and feedback to trace IDs.
- Dashboards cover quality, cost per completed task, latency percentiles and errors; drift alerts compare windows statistically and trigger error analysis.
- Treat the trace store as a PII warehouse: content off by default, external storage in production, redaction checked, retention limited.
- Telemetry the agent can query makes it legible to itself, with least privilege.

## Sources

- OpenTelemetry GenAI semantic conventions repository: https://github.com/open-telemetry/semantic-conventions-genai ; overview (Development status): https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/README.md
- OTel GenAI client inference spans and metrics: https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/client-inference.md ; model spans and content capture: https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md ; agent spans: https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md ; Anthropic conventions: https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/anthropic.md
- OpenTelemetry semantic conventions changelog (v1.42.0 move of GenAI conventions): https://github.com/open-telemetry/semantic-conventions/blob/main/CHANGELOG.md ; v1.41.0 GenAI attribute registry: https://github.com/open-telemetry/semantic-conventions/blob/v1.41.0/docs/registry/attributes/gen-ai.md ; former docs page (now a redirect notice): https://opentelemetry.io/docs/specs/semconv/gen-ai/
- OpenTelemetry, "Sampling" concepts: https://opentelemetry.io/docs/concepts/sampling/
- Hamel Husain and Shreya Shankar, evals FAQ (traces, sampling, guardrails vs evaluators, sensitive data): https://hamel.dev/blog/posts/evals-faq/
- Anthropic Engineering, "Demystifying evals for AI agents" (Jan 9, 2026): https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- OpenAI, Ryan Lopopolo, "Harness engineering: leveraging Codex in an agent-first world" (Feb 2026): https://openai.com/index/harness-engineering/
- OpenAI, prompt caching guide (`cached_tokens`): https://developers.openai.com/api/docs/guides/prompt-caching
- LangSmith docs: OpenTelemetry tracing https://docs.langchain.com/langsmith/trace-with-opentelemetry ; online evaluations https://docs.langchain.com/langsmith/online-evaluations ; self-hosting https://docs.langchain.com/langsmith/self-hosted
- Langfuse docs: https://langfuse.com/docs ; "Langfuse joins ClickHouse": https://langfuse.com/blog/joining-clickhouse ; license: https://github.com/langfuse/langfuse/blob/main/LICENSE
- Arize Phoenix: https://github.com/Arize-ai/phoenix ; OpenInference: https://github.com/Arize-ai/openinference
- Braintrust docs: OpenTelemetry https://www.braintrust.dev/docs/integrations/sdk-integrations/opentelemetry ; self-hosting https://www.braintrust.dev/docs/guides/self-hosting
- W&B Weave docs (CoreWeave): https://weave-docs.wandb.ai/
- Datadog Agent Observability, OpenTelemetry instrumentation: https://docs.datadoghq.com/llm_observability/instrumentation/otel_instrumentation/
