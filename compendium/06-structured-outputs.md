# 06. Structured Outputs and Constrained Decoding

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This is the 2023–2025 part of the system thread. [§05](05-api-and-prompting.md) showed how to call a model and steer it with a prompt, but what comes back is free text written for a human. Code can't reliably parse free text: a pipeline expecting `{"total": 42.5}` breaks when it gets "Sure! Here's the JSON:" and a markdown fence. This section follows the fix through four steps (asking politely, a function-calling trick and JSON mode in 2023, then schema-guaranteed structured outputs from 2024) and explains the decoding mechanism that makes the guarantee possible. The same mechanism later makes tool calls reliable ([§10](10-tool-use.md)).

## Why this exists

As a data engineer you know **schema-on-write** (reject a record that doesn't match) and **schema-on-read** (store whatever arrives and hope it parses later). By default an LLM's output is schema-on-read text whose shape is probabilistic (P4). Your consumers (a dbt model, a Kafka topic with a registered Avro schema, a function with typed arguments) need schema-on-write.

Prompting alone can't close the gap, for three reasons that follow from first principles:

1. **The model emits one token at a time, sampled from a distribution (P1).** A *token* is a chunk of text from a fixed vocabulary of roughly 100k–200k entries. At each step the model gives every token a *logit* (a raw score). The scores become probabilities (softmax), and one token is sampled.
2. **"Reply only in JSON" shifts probabilities; it doesn't remove options.** `{` gets more likely and "Sure" less likely, but "Sure" is never impossible.
3. **Small error rates compound (P8).** If the model picks a grammar-legal token 99.9% of the time, a 300-token object is fully valid only 0.999³⁰⁰ ≈ 74% of the time. At a million records a day, that is about 260,000 broken records.

Before structured outputs, the typical failures were chatty preambles, code fences, trailing commas, missing keys, invented enum values, and objects cut off mid-string.

The key insight comes from P6 (*the model proposes; code disposes*). Sampling is done by inference code, not by the model: the model only supplies scores, and code picks the token. So code can **make invalid tokens impossible** instead of merely unlikely. That is constrained decoding, and the rest of this section builds on it.

## How it works (under the hood)

### The progression: from asking to guaranteeing

| Step | Era | What you do | What is guaranteed |
|---|---|---|---|
| 1. Prompt and parse | 2020–2023 | Instructions, few-shot examples, regex out of a code fence, JSON repair, retry | Nothing |
| 2. Function calling as a JSON trick | Jun 2023 (OpenAI) | Define a function you never run; force the model to call it; keep the arguments | Usually valid JSON; schema not enforced |
| 3. JSON mode | Nov 2023 (OpenAI DevDay) | `response_format: {"type": "json_object"}` | Valid JSON syntax, **not** your schema |
| 4. Strict structured outputs | Aug 2024 (OpenAI); Nov 2025 beta, Jan 2026 GA (Anthropic) | Send a JSON Schema; the API constrains decoding to it | Output matches the schema, except in the failure modes below |

Details worth knowing:

- **Prefill.** A step-1 trick on Claude was *prefill*: you wrote the start of the assistant's reply (say `{`) and the model continued from inside the object. Claude Opus 4.6 (Feb 5, 2026) dropped prefill, and current Claude models return a 400 error for it.
- **JSON mode's sharp edge.** OpenAI's docs warn that without an explicit request for JSON "the model may generate an unending stream of whitespace", so the API errors if "JSON" appears nowhere in the context. Keep that in mind: a constraint can force *legal* output that never ends.
- **OpenAI Structured Outputs (GA)** arrived Aug 6, 2024, as `strict: true` on functions plus a `json_schema` response format. OpenAI reported 100% on its complex-schema eval for `gpt-4o-2024-08-06`, against under 40% for `gpt-4-0613` (**⚠ verify**: vendor eval; the post was not reachable for this review). OpenAI staff said the first request with a new schema is slow because they "preprocess the JSON schema into a context-free grammar". Since May 2025 that support has used the open-source llguidance engine, according to that project.
- **Anthropic structured outputs (GA)** launched in public beta on Nov 14, 2025, and came out of beta on the Claude API on Jan 29, 2026, when `output_format` moved to `output_config.format`. As of Oct 2026 it is GA on the Claude API, Claude Platform on AWS, Google Cloud and Microsoft Foundry; on Amazon Bedrock it is offered only through the legacy integration. The docs say it works "through constrained decoding". It has two halves: **JSON outputs** (`output_config.format`) for the response, and **strict tool use** (`strict: true`) for tool arguments.

### Constrained decoding: masking the logits

Constrained decoding adds one step to the ordinary decode loop from [§03](03-inference.md):

```text
  token prefix ──► model forward pass ──► logits: one score per vocabulary token
                                               │
  grammar state ──► "which tokens are legal here?" ──► mask: score = -inf if illegal
                                               │
                                               ▼
                          softmax over legal tokens ──► sample one token
                                               │
                         advance grammar state ◄┘   (repeat until grammar reaches END)
```

1. **Compile the schema into a grammar.** A *grammar* is a precise rule set for which strings are legal. A flat pattern (an enum, a date) can be a *regular expression*, which compiles to a **finite-state machine (FSM)**: a set of states where each allowed piece of text moves you to another state. Nested JSON needs a **context-free grammar**, which adds a stack to track open brackets (a *pushdown automaton*).
2. **Compute the legal-token mask.** From the current grammar state, find which vocabulary tokens keep the output on an accepted path.
3. **Mask and renormalize.** Set illegal tokens' logits to −∞, so their probability is exactly zero after softmax. The remaining probability is spread over the legal tokens.
4. **Sample as usual, then advance the grammar.** Temperature still applies (P4). Only the set of choices has shrunk.

Here is the whole idea over an 11-token vocabulary. The fake model "wants" to start with `Sure`, but the mask makes that impossible:

```python
import math
import random
# A tiny vocabulary. Real tokenizers have 100k+ entries, many multi-character.
VOCAB = ['{"', 'status', '":', ' "', 'ok', 'error', 'pending', '"}', 'Sure', '```', '\n']

# The grammar for {"status": "ok" | "error" | "pending"} as a finite-state machine:
# state -> {token the grammar allows here: next state}
FSM = {
    0: {'{"': 1},
    1: {'status': 2},
    2: {'":': 3},
    3: {' "': 4},
    4: {'ok': 5, 'error': 5, 'pending': 5},
    5: {'"}': "END"},
}

def fake_model_logits(prefix):
    """Stand-in for the LLM (P1): one raw score (logit) per vocabulary token."""
    rng = random.Random(len(prefix))
    scores = [rng.uniform(-1.0, 1.0) for _ in VOCAB]
    scores[VOCAB.index("Sure")] += 3.0   # a chatty model wants to say "Sure, here's..."
    return scores

def constrained_decode():
    state, out = 0, []
    while state != "END":
        logits = fake_model_logits(out)
        allowed = FSM[state]
        # The mask: every token the grammar forbids gets -inf, i.e. probability 0.
        masked = [s if tok in allowed else -math.inf for tok, s in zip(VOCAB, logits)]
        total = sum(math.exp(s) for s in masked)          # exp(-inf) == 0.0
        probs = [math.exp(s) / total for s in masked]     # renormalize over legal tokens
        token = random.choices(VOCAB, weights=probs)[0]   # sample, as usual (P4)
        out.append(token)
        state = allowed[token]                            # advance the grammar
    return "".join(out)

print(VOCAB[max(range(len(VOCAB)), key=fake_model_logits([]).__getitem__)])  # Sure
print(constrained_decode())  # e.g. {"status": "pending"} - always valid; the value is sampled
```

The output is always valid, but which status comes out is still the model's sampled choice. Remember that split: **the grammar owns the shape; the model still owns the content.**

#### What real engines add

- **Tokens don't line up with grammar symbols.** Grammars are defined over characters, but tokens are chunks like `"},`. Checking every one of 100k+ tokens against the grammar at every step would be far too slow.
- **Precomputed indexes.** Outlines (Willard & Louf, Jul 2023) precomputes, for each FSM state, the set of allowed token IDs, so each step becomes a lookup.
- **Smarter checks for nested grammars.** XGrammar (Nov 2024) prechecks the tokens whose legality doesn't depend on the stack, checks only the rest at runtime, and overlaps that work with the GPU. The paper reports up to 100× speedups over earlier engines. llguidance (Microsoft's guidance project) reports about 50 μs of CPU per token for a 128k vocabulary.

Self-hosted servers such as vLLM let you choose among these as the "structured outputs backend". Done well, the mask is computed on the CPU while the GPU runs the forward pass, so the overhead is near zero (P10).

On the Claude API, grammar compilation has two visible effects:

- **Caching.** Compiled grammars are cached for 24 hours from last use. Changing the schema's structure or the tool set recompiles; changing only names or descriptions doesn't.
- **Ordering.** Required properties are emitted before optional ones. That matters for the "reason first" trick below.

Tie this back to P1. Constrained decoding doesn't change the model; it changes what the harness does with the model's distribution. You sample from that distribution *conditioned on staying valid*. If the prompt already made legal tokens likely, the mask barely bites. If the model put 95% on `Sure`, the other 5% is inflated to 100%, pushing the model down a path it considered unlikely. That picture explains the reasoning debate at the end of this section.

### Tool use is structured output with a name attached

A tool call ([§10](10-tool-use.md)) is the model emitting a tool name plus a JSON object that must match the tool's `input_schema`. With `strict: true`, the same grammar machinery guarantees the arguments validate. Function calling is constrained decoding plus routing: the harness reads the name, runs the function and returns the result (P6).

Two practical consequences in 2026:

- **The fake-tool trick is gone on current Claude models.** Forcing an unused tool with `tool_choice` was the classic way to get JSON from Claude. On Claude Fable 5.1, Opus 5.5 and Sonnet 5.5, forced `tool_choice` (`any` or `tool`) returns a 400 error, and Anthropic points you to strict tools or `output_config.format`.
- **The grammar doesn't cover thinking.** On Claude it applies only to the direct output and strict tool inputs. As the docs put it, "grammar state resets between sections, allowing Claude to think freely while still producing structured output in the final response".

### Validation and retry: Pydantic as the second gate

Constrained decoding guarantees **syntax** and **schema** (types, required keys, enums). It can't guarantee **semantics**: that line items add up to the total, or that a customer ID exists in your warehouse. **Pydantic**, a Python library where you declare a data shape as a class with type hints, can generate a JSON Schema from that class and validate incoming JSON against it, including custom rules.

Some schema keywords also fall outside the grammar. `minimum`, `maxLength` and recursive schemas are rejected on the Claude API. Anthropic's Python and TypeScript SDKs remove the unsupported constraints before sending, note them in field descriptions, and check them on your side afterwards. Those constraints move from *guaranteed* to *checked*.

```python
import os
import anthropic
from pydantic import BaseModel, ValidationError, model_validator

class LineItem(BaseModel):
    description: str
    amount: float

class Invoice(BaseModel):
    vendor: str
    invoice_date: str        # the grammar guarantees a string, not a correct date
    line_items: list[LineItem]
    total: float

    @model_validator(mode="after")
    def total_matches_items(self):  # a business rule no JSON Schema keyword can express
        if abs(sum(i.amount for i in self.line_items) - self.total) > 0.01:
            raise ValueError("total does not equal the sum of line_items")
        return self

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
SCHEMA = anthropic.transform_schema(Invoice)  # Pydantic model -> API-compatible JSON Schema

def extract_invoice(text: str, max_attempts: int = 3) -> Invoice:
    messages = [{"role": "user", "content": f"Extract the invoice fields:\n\n{text}"}]
    for _ in range(max_attempts):
        resp = client.messages.create(
            model="claude-sonnet-5-5", max_tokens=4096, messages=messages,
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        )
        if resp.stop_reason in ("refusal", "max_tokens"):  # the two cases the schema can't cover
            raise RuntimeError(f"stopped with {resp.stop_reason}; fix the request, don't resample")
        raw = next(b.text for b in resp.content if b.type == "text")
        try:
            return Invoice.model_validate_json(raw)  # shape is guaranteed; the rules are not
        except ValidationError as err:  # feed the exact error back, then resample (P4)
            messages += [{"role": "assistant", "content": resp.content},
                         {"role": "user", "content": f"Validation failed:\n{err}\nCorrect it."}]
    raise RuntimeError(f"no valid invoice after {max_attempts} attempts")  # dead-letter it
```

How the loop works:

- **It appends rather than starting over.** The model's failed answer and the validator's exact error go back in. The model is stateless (P2), so that history *is* its memory of the mistake.
- **Some failures aren't worth resampling.** Refusals and truncations are handled before validation, because a second sample won't fix them.
- **The final `raise` is a dead-letter queue.** Park the record for review rather than looping forever, and log every validation failure as eval data ([§26](26-evals.md)).
- **SDK shortcut.** `client.messages.parse(..., output_format=Invoice)` combines the schema transform and parsing into one call.

### Failure modes

1. **The schema is too complex or uses unsupported keywords.**
   - The Claude API caps a request at 20 strict tools, 24 optional parameters and 16 union-typed parameters (`anyOf` or `["string", "null"]`), summed across all strict schemas.
   - Past internal limits you get `400 "Schema is too complex for compilation"`, with a 180-second compile timeout as a backstop. Each optional parameter "roughly doubles a portion of the grammar's state space".
   - Fixes: make fields required (use `null` for "absent"), flatten nesting, mark only critical tools strict.
   - The JSONSchemaBench benchmark (Jan 2025, about 10k real-world schemas) found that engines differ widely in which features they cover. "Supports JSON Schema" always means a subset.
2. **Refusals.** If Claude declines for safety reasons you still get HTTP 200, `stop_reason: "refusal"`, a bill for the tokens, and output that "may not match your schema". OpenAI returns a separate `refusal` field. Either way, check before parsing.
3. **Truncation at `max_tokens`.** The grammar keeps every *prefix* on a valid path; it doesn't promise you reach the end. A cut-off response is a valid prefix of an invalid whole.
4. **Degenerate loops.** OpenAI's Ted Sanders: "it can get stuck in loops where it just prints technically valid output forever without ever closing the object". JSON mode's endless whitespace is the same failure. Use a sane `max_tokens`, a timeout, and a prompt that describes the format.
5. **Valid but wrong (P4).**
   - This is the failure that matters, because nothing flags it. `"total": 1250.00` parses perfectly whether or not the document says 1,250.
   - A *required* field forces the model to produce a value even when the source has none, so it invents one. Design escape hatches: nullable fields, an `"unknown"` enum value, a `not_found` list.
   - Claude may also return enum values with different capitalization, so compare them case-insensitively.
   - Measure accuracy with evals, not with the parser.
6. **Governance.** Anthropic caches compiled schemas separately from message content and says to keep protected health information out of property names, enums and patterns. Apply the same rule to any sensitive value: it belongs in message content, never in the schema.

### Do format constraints hurt reasoning?

- **The claim.** Tam et al., "Let Me Speak Freely?" (arXiv 2408.02442, Aug 2024, revised Oct 2024), reported "a significant decline in LLMs reasoning abilities under format restrictions", worse for stricter formats, though structure sometimes *helped* classification.
- **The rebuttal.** The dottxt team, who build Outlines and so are not neutral, answered with "Say What You Mean". They argue the prompts weren't comparable and that JSON mode was conflated with true constrained generation. Their reimplementation found structured output equal or better (GSM8K 0.77 → 0.78, Last Letter 0.73 → 0.77).

The mechanism explains both results. There are two separate effects:

- **Lost scratch space.** A model "thinks" only by emitting tokens, each conditioned on the ones before (P1; see [§04](04-reasoning-models.md)). A schema with `answer` first forces the model to commit before reasoning. That is a format-design problem.
- **Distribution mismatch.** If the prompt didn't prepare the model for the format, the mask cuts away most of its probability mass. That is a prompting problem.

The mitigation is the same for both: **reason first, then emit the structure.** Four ways to do it:

1. **Use a reasoning model.** Thinking blocks are unconstrained, and the grammar applies only to the final answer.
2. **Two passes.** A free-text reasoning call, then a cheap constrained extraction call.
3. **A reasoning field placed first.** Make it required, since Claude emits required fields first. Caveat from Anthropic: a property requesting "step-by-step reasoning may lead to a `reasoning_extraction` refusal", so ask for a short `explanation` instead.
4. **Describe the format in the prompt as well as the schema,** so the mask rarely has to override the model.

Then measure on your own task (P4). This is an eval question, not one to settle by blog post.

## Comparison

**Ways to get machine-readable output**

| Approach | How it works | Strength | Weakness | When to choose |
|---|---|---|---|---|
| Prompt and parse | Instructions, few-shot, JSON repair, retry | Works with any model | No guarantee; failures compound at volume (P8) | Prototypes; models without schema support |
| JSON mode | Decoding constrained to *some* valid JSON | Always parses | No schema; whitespace loops | Legacy only |
| Strict structured outputs (vendor API) | Your schema compiled to a grammar; logits masked | Guaranteed shape; no parse retries | Schema subset and limits; compile latency; values can be wrong | Default for extraction and classification |
| Strict tool use | The same grammar applied to tool arguments | Reliable calls, routed to a function | Limited number of strict tools per request | When output triggers an action ([§10](10-tool-use.md)) |
| Self-hosted constrained decoding (Outlines, XGrammar, llguidance) | You run the mask in your inference server | Any grammar (regex, CFG, SQL); full control | You operate the stack ([§31](31-open-weights-self-hosting.md)) | Open-weight models; custom grammars |
| Reason, then extract | Free-text call, then small constrained call | Keeps reasoning quality; easy to eval | About 2× calls and latency | Hard reasoning without a thinking model |

**Request shapes by vendor (as of Oct 2026)**

| Vendor | JSON output | Strict tool arguments |
|---|---|---|
| Anthropic Messages API | `output_config: {"format": {"type": "json_schema", "schema": {...}}}` | `"strict": true` beside `input_schema` |
| OpenAI Responses API | `text: {"format": {"type": "json_schema", "strict": true, "schema": {...}}}` | `"strict": true` on the function |
| OpenAI Chat Completions | `response_format: {"type": "json_schema", "json_schema": {"strict": true, "schema": {...}}}` | `"strict": true` on the function |
| Google Gemini API | Response format with MIME type `application/json` plus a JSON Schema | Function declarations with parameter schemas |

## What it didn't solve

You can now get reliable fields out of a model, but only from text you can paste into the prompt. Most enterprise knowledge isn't plain text. It lives in scanned PDFs, slide decks, screenshots, charts, forms with checkboxes, and recorded calls. To extract an invoice total, the model first has to read the invoice image. → Next: [§07 Multimodal Models and Documents](07-multimodal.md)

## Check your understanding

**Q: Why doesn't writing "respond only with valid JSON" in the prompt guarantee valid JSON?**

The instruction changes probabilities but never removes a token from the vocabulary, so illegal tokens keep some chance of being sampled (P1, P4). Across hundreds of tokens per object and millions of objects, small per-token error rates compound into many broken records (P8). Constrained decoding sets illegal tokens' probability to exactly zero. Prompting still matters alongside it, because a prompt that matches the format keeps the mask from fighting the model.

**Q: What does JSON mode guarantee compared with strict structured outputs?**

JSON mode constrains decoding to *some* syntactically valid JSON, so it parses, but keys, types and enums are unchecked. Strict structured outputs compile *your* schema into a grammar, so required keys, types and enum values are enforced too. The tradeoff is a supported-schema subset, complexity limits and first-request compile latency. Treat JSON mode as legacy and use it only where a model lacks schema support.

**Q: What would happen if your schema put the `answer` field before the `reasoning` field?**

Each token is computed from the tokens before it, so the model commits to an answer before writing any reasoning, which then becomes after-the-fact justification (P1). Accuracy on multi-step problems can drop, which is one plausible mechanism behind the "Let Me Speak Freely?" results. Put reasoning first (both fields required), use a model whose thinking is unconstrained, or split the work into reasoning and extraction calls. For simple classification the order barely matters.

**Q: What would happen if your schema requires `invoice_number` but the document has none?**

The grammar forces the model to emit a string, so it produces a plausible invented number that passes every parser (P4). The fix is schema design: make the field nullable or add an explicit "not found" option, so the honest answer is a legal path. Then measure value accuracy with evals, because no parser can catch this.

**Q: Constrained decoding vs validate-and-retry: why do you usually need both?**

Constrained decoding guarantees syntax and schema at generation time, with no wasted calls. It can't express business rules such as "line items sum to the total", and unsupported keywords like `minimum` get checked only on your side. A Pydantic validator catches those violations, and a bounded retry that feeds back the exact error gives the model a targeted second sample. Don't retry refusals or `max_tokens` truncations blindly; resampling won't fix them.

**Q: Why is tool use a form of structured output?**

A tool call is the model emitting a name plus a JSON object that must match the tool's `input_schema`, which the harness then parses and executes (P6). With `strict: true`, the same grammar-constrained decoding guarantees the arguments validate. The only difference is routing: the output triggers an action instead of being stored. That is why the "fake tool to get JSON" trick worked, and why current Claude models that reject forced `tool_choice` point you to `output_config.format`.

## Takeaways

- Prompting shifts probabilities; constrained decoding sets illegal tokens' probability to zero. Only the second is a guarantee.
- The mechanism: compile the schema to a grammar, mask illegal logits to −∞ each step, renormalize, sample, advance.
- The grammar owns the shape; the model owns the values. Valid-but-wrong is the failure that matters (P4).
- Give every schema an escape hatch (nullable fields, "unknown"), or you force the model to invent data.
- Layer the checks: grammar for schema, Pydantic for business rules, bounded retries, then a dead-letter queue.
- Check `stop_reason` before parsing: refusals and `max_tokens` truncations break the guarantee.
- Reason first, then emit structure: thinking blocks, two passes, or a reasoning field placed first.
- Tool calling is structured output plus routing ([§10](10-tool-use.md)).

## Sources

- Anthropic, Structured outputs (limits, grammar caching, invalid outputs, property ordering): https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Anthropic, Strict tool use: https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use
- Anthropic, Claude Platform release notes (Nov 14, 2025 beta; Jan 29, 2026 GA; Opus 4.6 prefill removal; forced `tool_choice` changes): https://platform.claude.com/docs/en/release-notes/overview
- OpenAI, Structured Outputs guide (JSON mode vs Structured Outputs, refusals, whitespace warning): https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI, "Introducing Structured Outputs in the API" (Aug 6, 2024): https://openai.com/index/introducing-structured-outputs-in-the-api/
- OpenAI Developer Community, "How do I use the new JSON mode?" (Nov 2023; JSON mode launch at DevDay) (secondary): https://community.openai.com/t/how-do-i-use-the-new-json-mode/475890
- Simon Willison, "OpenAI: Introducing Structured Outputs in the API" (Aug 6, 2024; quotes Ted Sanders on CFG preprocessing and loops) (secondary): https://simonwillison.net/2024/Aug/6/openai-structured-outputs/
- Google, Gemini API structured outputs: https://ai.google.dev/gemini-api/docs/structured-output
- Willard & Louf, "Efficient Guided Generation for Large Language Models" (Outlines), arXiv 2307.09702: https://arxiv.org/abs/2307.09702
- Outlines library: https://github.com/dottxt-ai/outlines
- Dong et al., "XGrammar: Flexible and Efficient Structured Generation Engine for Large Language Models", arXiv 2411.15100: https://arxiv.org/abs/2411.15100
- llguidance (Microsoft guidance project): https://github.com/guidance-ai/llguidance
- Geng et al., "JSONSchemaBench: A Rigorous Benchmark of Structured Outputs for Language Models", arXiv 2501.10868: https://arxiv.org/abs/2501.10868
- vLLM, Structured outputs (backends): https://docs.vllm.ai/en/latest/features/structured_outputs.html
- Tam et al., "Let Me Speak Freely? A Study on the Impact of Format Restrictions on Performance of Large Language Models", arXiv 2408.02442: https://arxiv.org/abs/2408.02442
- Will Kurt (dottxt), "Say What You Mean: A Response to 'Let Me Speak Freely'": https://blog.dottxt.co/say-what-you-mean.html
- Pydantic documentation: https://docs.pydantic.dev/
- Chip Huyen, *AI Engineering* (O'Reilly, 2025), Ch. 2 covers sampling and structured outputs: https://github.com/chiphuyen/aie-book/blob/main/ToC.md
