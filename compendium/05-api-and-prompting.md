# 05. The API and Prompt Engineering

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This is the start of the system thread, and of the prompt-engineering era (2020–2023). Part 1 explained the model; [§04](04-reasoning-models.md) ended in 2025, and this section rewinds to 2020. On Jun 11, 2020, OpenAI opened the GPT-3 API in private beta as a "text in, text out" interface: you sent a prompt string and the model continued it. On Mar 1, 2023, the Chat Completions endpoint replaced the single string with a list of role-tagged messages. Anthropic's Messages API followed the same shape, replacing its older Text Completions format of `\n\nHuman:` / `\n\nAssistant:` turns (exact launch date **⚠ verify**). This section shows what actually goes over the wire, why the API forgets everything between calls, and which prompt techniques work, and why.

## Why this exists

**You don't run the model; a vendor does.** Frontier models need clusters of GPUs (P10), so you reach them through an HTTP API. The API is the contract between your code and a stateless next-token function (P1, P2).

**Underneath every API there is one token sequence.** The model never sees "messages" or "roles". The server renders your request into one sequence using a chat template, with special tokens marking who said what, and the model predicts what comes next. Post-training ([§02](02-how-llms-work.md)) taught the model that template, which is why vendors expose structured messages rather than raw strings: they control the rendering, and the model behaves best in the format it was trained on.

**In the GPT-3 era, the prompt was the whole program.** There were no tools, no structured outputs and no reasoning models. The only control surface was the text you put in front of the model. *Prompt engineering*, the craft of choosing that text, existed because it was the only lever.

## How it works (under the hood)

### The raw request and response

One HTTPS `POST` to `https://api.anthropic.com/v1/messages` **(GA)**. Three headers: your API key, a pinned API version (`anthropic-version: 2023-06-01`) and the content type. The JSON body names the model, sets an output cap and carries the conversation.

```python
import json
import os
import requests

resp = requests.post(
    "https://api.anthropic.com/v1/messages",
    headers={
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],  # never hardcode keys
        "anthropic-version": "2023-06-01",  # API version, pinned per request
        "content-type": "application/json",
    },
    json={
        "model": "claude-sonnet-5-5",
        "max_tokens": 4096,  # required: hard cap on generated tokens (thinking included)
        "system": "You are a concise data-engineering assistant.",
        "messages": [  # the conversation so far: here, a single user turn
            {"role": "user", "content": "In one sentence: what is a slowly changing dimension?"}
        ],
    },
    timeout=120,
)
resp.raise_for_status()
body = resp.json()
print(json.dumps(body, indent=2))
text = "".join(b["text"] for b in body["content"] if b["type"] == "text")  # select by type
print(body["stop_reason"], "|", text)
```

The response (values illustrative):

```json
{
  "id": "msg_01XyZ...",
  "type": "message",
  "role": "assistant",
  "model": "claude-sonnet-5-5",
  "content": [
    {"type": "thinking", "thinking": "", "signature": "EqQBCkYI..."},
    {"type": "text", "text": "A slowly changing dimension is a dimension table whose attributes change over time, handled by overwriting (Type 1) or by keeping versioned rows (Type 2)."}
  ],
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 31,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
    "output_tokens": 96,
    "output_tokens_details": {"thinking_tokens": 52}
  }
}
```

`content` is a *list of typed blocks*, not a string. Current Claude models think adaptively by default ([§04](04-reasoning-models.md)), so a `thinking` block, empty unless you ask for summaries, may come first. Always select blocks by `type`.

### Roles and the system prompt

- **`messages`** holds the conversation as `user` and `assistant` turns. The first must be `user`, and consecutive turns with the same role are merged. `content` is a string or a list of blocks: text, images, documents, tool calls and results ([§10](10-tool-use.md)), thinking.
- **`system`** is a top-level field, not a message. It carries the developer's instructions: role, rules, output format, background. Post-training gives it more weight than user text, which is why it's where standing instructions go. Newer models (Claude Opus 5.5 and Claude Sonnet 5.5, among others) also accept `role: "system"` messages *inside* `messages` **(GA)**, for operator instructions that arrive mid-conversation.
- **Everything becomes one sequence.** The server renders tools, then the system prompt, then the messages, and the model continues from the end:

```text
what you send                            what the model sees
─────────────                            ───────────────────────────────────────────────
tools:    [...]        ─┐
system:   "..."         ├── render ──▶   [tools][system][user][assistant][user] … [assistant: ▌
messages: [u, a, u, …]  ┘                                                          next token
```

That has a security consequence. The system prompt is just more tokens in the same channel as user text and retrieved documents. Text in any of them can act as an instruction (P9). The system prompt sets priorities; it is not a security boundary ([§32](32-security-guardrails.md)).

### Statelessness (P2): you resend everything

The API keeps nothing between calls. In Anthropic's words, the Messages API "is stateless, which means that you always send the full conversational history". Memory in a chat app is an illusion your code maintains:

```python
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
SYSTEM = "You are a concise data-engineering assistant."
history = []  # YOUR copy of the conversation; the API keeps none (P2)

def ask(user_text):
    history.append({"role": "user", "content": user_text})
    response = client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=4096,
        output_config={"effort": "low"},  # chat: think little, answer fast
        system=SYSTEM,
        messages=history,  # the WHOLE history goes over the wire on every call
    )
    # Append the full content (thinking blocks included); never edit earlier turns.
    history.append({"role": "assistant", "content": response.content})
    print(f"turn {len(history) // 2}: input_tokens={response.usage.input_tokens}")
    return "".join(b.text for b in response.content if b.type == "text")

ask("My warehouse is Snowflake and my main fact table is fct_orders.")
ask("Suggest a clustering key for it.")  # works only because turn 1 was resent
history.clear()  # "forgetting" just means not sending it
print(ask("Which warehouse did I say I use?"))  # the model now cannot know
```

The printed `input_tokens` climbs every turn. The consequences:

- **Cost grows with conversation length.** Turn k resends all k−1 earlier turns, so total input over n turns grows roughly with n². Prompt caching (below) is what keeps this affordable.
- **The context window is a hard wall (P3).** Eventually history must be dropped, summarized or compacted ([§16](16-context-engineering.md)).
- **You own the history.** You can insert synthetic turns (few-shot examples written as fake past exchanges) or trim old ones. On current models, though, editing earlier turns invalidates stored thinking blocks, so append-only is the safe default (§04).

A data-engineering analogy: each call recomputes a view from the full event log, with no materialization. Prompt caching is the materialization.

Some APIs offer server-side state. OpenAI Responses has `store` and `previous_response_id`, Google's Interactions API has `previous_interaction_id`, and Anthropic offers sessions in Managed Agents ([§20](20-agent-runtime.md)). The model underneath is still stateless: the server replays the history for you. OpenAI's docs state that the replayed tokens are still billed as input.

### Parameters

- **`max_tokens`** (required): a hard cap on generated tokens, *including thinking*. The model usually stops earlier. If it hits the cap, `stop_reason` is `"max_tokens"` and the text ends mid-thought. The Python SDK requires streaming above 21,333 tokens to avoid HTTP timeouts.
- **`temperature`**: the classic randomness dial. The model's raw scores (*logits*) are divided by T before the softmax turns them into probabilities. T < 1 sharpens the distribution toward the top token; T > 1 flattens it. Even T = 0 isn't fully deterministic, because serving-side numerics vary (P4). **Status, Oct 2026:** Anthropic has deprecated it. Models released after Claude Opus 4.6, which includes every current model ID, reject any value other than 1.0 with a 400 error, and they reject non-default `top_p` and `top_k` too. Google's Gemini 4 and 3.6+ models ignore custom sampling values and return deprecation warnings. Neither vendor's docs give a reason. A plausible reading is that RL-trained reasoning models are tuned at their native sampling settings, and effort ([§04](04-reasoning-models.md)) is now the dial you're expected to turn.
- **`stop_sequences`**: strings that end generation when the model produces them. `stop_reason` becomes `"stop_sequence"` and the `stop_sequence` field names the match. They were classically used to cut output at a delimiter such as `</answer>`.
- **`output_config.effort`** and **`thinking`**: the reasoning controls from §04.

### `stop_reason`: why the model stopped

Check this field before you use `content`. A refusal is a normal HTTP 200.

| `stop_reason` | Meaning | What your code should do |
|---|---|---|
| `end_turn` | Natural stopping point | Use the output |
| `max_tokens` | Hit your cap | Treat as truncated: raise the cap, lower effort, or continue |
| `stop_sequence` | Emitted one of your stop strings | Expected; parse up to the stop |
| `tool_use` | Model wants a tool run | Execute it and send the result ([§10](10-tool-use.md)) |
| `pause_turn` | Long server-side turn paused | Send the response back as-is to continue |
| `refusal` | Declined by safety classifiers | Read `stop_details.category`; don't treat as an answer |
| `model_context_window_exceeded` | Ran out of context window | Trim or compact the history |

### Usage and token counts

Every response reports `usage`. `input_tokens` covers uncached input. `cache_creation_input_tokens` and `cache_read_input_tokens` cover cached input, and the true total input is the sum of all three. `output_tokens` includes thinking, broken out in `output_tokens_details.thinking_tokens`. Counts won't match the visible text exactly, because the server adds formatting tokens. To estimate before sending, `POST /v1/messages/count_tokens` takes the same body. This is your cost meter. With `claude-sonnet-5-5` at $2 per million input tokens and $10 per million output tokens (Oct 2026), a 20,000-token history plus a 500-token answer costs $0.045 per turn before caching.

### Streaming (SSE)

Without streaming, you wait for the whole response. Streaming sends tokens as they are decoded, so the user sees the first words after the time-to-first-token from [§03](03-inference.md) rather than after the whole generation. Set `"stream": true` and the response becomes *server-sent events* (SSE), a long-lived HTTP response made of named events:

```text
event: message_start        data: {"type":"message_start","message":{"id":"msg_...","content":[],"usage":{...}}}
event: content_block_start  data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}
event: content_block_delta  data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Idempotent"}}
event: ping                 data: {"type":"ping"}
event: content_block_stop   data: {"type":"content_block_stop","index":0}
event: message_delta        data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":87}}
event: message_stop         data: {"type":"message_stop"}
```

Delta types are `text_delta`, `input_json_delta` (tool arguments), `thinking_delta` and `signature_delta`. Usage counts in `message_delta` are cumulative. An `error` event (for example `overloaded_error`) can arrive *after* the HTTP 200, so streaming code must handle errors mid-stream. Since prefill is gone (below), the way to recover a cut-off stream on current models is a new user message: "Your previous response was interrupted and ended with [...]. Continue from where you left off."

```python
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

with client.messages.stream(  # sets "stream": true and parses the SSE events
    model="claude-sonnet-5-5",
    max_tokens=8000,
    messages=[{"role": "user", "content": "Explain idempotent pipeline loads in 3 bullets."}],
) as stream:
    for event in stream:  # raw event types arrive in wire order
        if event.type == "message_start":
            print("[start] input tokens:", event.message.usage.input_tokens)
        elif event.type == "content_block_start":
            print(f"\n[block {event.index}: {event.content_block.type}]")
        elif event.type == "content_block_delta" and event.delta.type == "text_delta":
            print(event.delta.text, end="", flush=True)  # tokens as they are decoded
        elif event.type == "message_delta":
            print("\n[stop]", event.delta.stop_reason, "| output:", event.usage.output_tokens)
    final = stream.get_final_message()  # the same Message a non-streaming call returns
print(len(final.content), "content blocks")
```

### Prompt engineering techniques, and why each works

Every technique below works the same way: it changes the tokens the next-token distribution is conditioned on (P1), so that probability mass concentrates on the output you want.

**Clear, specific instructions.** A vague request ("summarize this") is consistent with many tasks: different lengths, audiences and emphases. The output distribution spreads across all of them. Explicit constraints prune those readings, and instruction tuning ([§02](02-how-llms-work.md)) trained the model to follow them. Giving the *reason* for a constraint helps the model generalize. Anthropic's example is "this will be read aloud by text-to-speech, so never use ellipses" rather than a bare "NEVER use ellipses". Their test: would a capable new colleague with no context understand the prompt?

**Examples (few-shot).** *Few-shot prompting* means putting worked input→output examples in the prompt. The GPT-3 paper ("Language Models are Few-Shot Learners") showed models learn tasks *in context*, from examples, without any weight update. One proposed mechanism is the *induction head* (Olsson et al. 2022), an attention circuit that finds an earlier occurrence of the current token and copies what followed it. That is pattern continuation at the circuit level. The consequence is that models copy *everything* about your examples, including length, phrasing and label balance. Use 3–5 diverse examples, wrapped in `<example>` tags so they read as examples rather than instructions.

**Structure with XML tags.** Wrapping parts of a prompt in tags (`<instructions>`, `<document>`, `<data>`) gives the model unambiguous boundaries between instructions and material. You can then refer to sections by name ("using only the text in `<contract>`"), and the distinctive tag tokens are easy for attention to match. For long inputs, put documents first and the question last. Anthropic reports that this ordering improved quality by up to 30% in its tests. Tags organize the prompt; they don't stop injected instructions inside the data (P9).

**Role prompting.** "You are a senior data engineer reviewing a migration plan" shifts the distribution toward text that kind of author would write: vocabulary, rigor, what gets flagged. It works best in the system prompt. A role adds no knowledge (P5), and superlatives ("world-class expert") add little beyond specific instructions.

**Chain of thought.** Asking the model to work step by step buys extra serial compute and a scratchpad, the mechanism in [§04](04-reasoning-models.md). It was *the* reasoning technique of 2022–2023. On current reasoning models it's built in and controlled with effort. Asking the model to write its internal reasoning into the visible answer duplicates that work, and on the newest Claude models it can trigger a `reasoning_extraction` refusal. Ask for an explanation *for the reader* if you need one, and read thinking blocks for the model's reasoning.

**Self-consistency.** Sample several independent answers and take the majority (Wang et al. 2022, +17.9% on GSM8K over plain CoT). It works because wrong reasoning paths scatter across different answers while right ones converge. It costs N×, needs answers you can compare, and the agreement rate doubles as a confidence score. It is parallel test-time compute (§04):

```text
answers = [extract_final_answer(call_model(prompt)) for _ in range(N)]  # run in parallel
best    = most_common(answers)
confidence = answers.count(best) / N        # low agreement → escalate to a human or a stronger model
```

**Prompt templates.** A *template* separates fixed instructions from variable slots: `SYSTEM + "<ticket>{ticket_text}</ticket>"`. This is engineering hygiene, not model mechanics. Templates can be version-controlled and evaluated per version ([§26](26-evals.md)), much like a dbt model with Jinja variables. Put the stable part first and the variables last, which is also what caching rewards. The variable is untrusted data in the instruction channel, so tag it and never paste it unmarked into the instructions (P9).

### Prefill: what it was, and its status

*Prefill* meant ending `messages` with a partial `assistant` turn, such as `{"role": "assistant", "content": "{"}`, so the model continued from your text. Because you wrote the first tokens of the output, everything after was conditioned on them (P1). It was used to force JSON, skip preambles ("Here is the summary:"), steer past bad refusals, keep a persona, and resume cut-off responses.

**Status, Oct 2026:** Claude 4.6 and later models return a 400 error for a prefilled final assistant turn. Earlier models already disallowed it while thinking was on, presumably because a prefilled answer would skip the thinking that is meant to come first. Assistant turns *earlier* in the history, such as few-shot fake exchanges, are still fine. The replacements: structured outputs for format ([§06](06-structured-outputs.md)), system-prompt instructions for preambles, and a user message for continuations. Prefill is a clean example of the bitter lesson (P12): a workaround for weak instruction-following that became dead weight.

### Prompt caching, briefly

Statelessness means resending long, identical prefixes: system prompts, tool definitions, documents, history. *Prompt caching* **(GA)** stores the computed attention state, the KV cache from §03, for a prefix. A later request that starts with the byte-identical prefix skips recomputing it. Mark a breakpoint with `cache_control` on a block (up to four), or set it once at the top level:

```json
{
  "model": "claude-sonnet-5-5",
  "max_tokens": 1024,
  "system": [
    {"type": "text", "text": "<5,000 tokens of stable instructions and schema docs>",
     "cache_control": {"type": "ephemeral"}}
  ],
  "messages": [{"role": "user", "content": "Which tables hold PII?"}]
}
```

The default lifetime is 5 minutes, refreshed free on each hit; a 1-hour lifetime costs more. Writes cost 1.25× the base input price (2× for 1 hour). Reads cost 0.1× base, or 0.05× on Claude Opus 5.5 and Claude Sonnet 5.5 (Oct 2026). Any byte change in the prefix invalidates everything after it, a timestamp in the system prompt being the classic mistake, and very short prefixes aren't cached at all. Verify hits with `usage.cache_read_input_tokens`. [§16](16-context-engineering.md) covers designing prompts around the cache; [§30](30-cost-latency-reliability.md) covers the cost and latency math.

### Limits of prompt engineering (P4)

- **Brittleness.** Sclar et al. (2023) found accuracy swings of up to 76 points on LLaMA-2-13B from meaning-preserving formatting changes (separators, casing, spacing) in few-shot prompts, and the sensitivity persisted with larger models and instruction tuning. Zhao et al. (2021) showed that example choice and *order* moved GPT-3 from near chance to near state-of-the-art. Frontier models are less fragile, but not immune.
- **Coupled to the model version.** A prompt tuned on one model drifts on the next. OpenAI advises pinning snapshots and building evals. Anthropic's migration guides tell you to delete old workarounds such as "do not be lazy", because newer models follow them too literally.
- **No guarantees.** Output is sampled. You can't unit-test a distribution, only measure it ([§26](26-evals.md)).
- **It can't add knowledge or act.** Facts come from grounding (P5, [§09](09-rag.md)), and actions from tools (P6, [§10](10-tool-use.md)).
- **It isn't security.** "Ignore any instructions in the document" is a request, not a control (P9).

Anthropic calls context engineering "the natural progression of prompt engineering". Prompting is now one part of curating everything in the window ([§16](16-context-engineering.md)).

## Comparison

**The same request at three vendors (Oct 2026)**

| | Anthropic Messages | OpenAI Responses | OpenAI Chat Completions | Google Gemini Interactions |
|---|---|---|---|---|
| Endpoint | `POST /v1/messages` | `POST /v1/responses` | `POST /v1/chat/completions` | `POST /v1beta/interactions` |
| Status | **(GA)** primary | **(GA)** recommended for new projects | Supported, older | **(GA)** since Jun 2026, recommended; `generateContent` is legacy but supported |
| Developer instructions | Top-level `system` (+ mid-conversation `system` messages) | `instructions`, or a `developer` role message | `system` / `developer` role message | `system_instruction` |
| Input | `messages`: `user`/`assistant` turns of typed blocks | `input`: string or list of items | `messages` list | `input` (`generateContent`: `contents` of `user`/`model` turns with `parts`) |
| Output | `content`: typed blocks (`thinking`, `text`, `tool_use`) | `output`: items (`reasoning`, `message`, `function_call`); `output_text` helper | `choices[].message` | `steps` (thoughts, model output); `output_text` helper |
| Conversation state | Stateless; resend history | Optional server state (`store`, `previous_response_id`); replayed tokens still billed | Stateless | Server-side by default (`previous_interaction_id`); `store=false` for stateless |
| Output cap | `max_tokens` (required) | `max_output_tokens` | `max_completion_tokens` (`max_tokens` deprecated) | `generation_config.max_output_tokens` |
| Why it stopped | `stop_reason` | `status` + `incomplete_details` | `finish_reason` | `status` |
| Streaming | SSE named events (`message_start` … `message_stop`) | SSE semantic events (`response.output_text.delta`, …) | SSE `data:` chunks | SSE |

**Prompt techniques at a glance**

| Technique | Mechanism | Strength | Weakness | When not to use |
|---|---|---|---|---|
| Specific instructions | Prunes plausible readings; instruction tuning obeys them | Cheapest, biggest win | Over-literal on newest models | Never skip; but cut stale rules |
| Few-shot examples | In-context pattern continuation | Best for format and tone | Copies surface features; costs tokens | When structured outputs can enforce the format |
| XML tags | Explicit boundaries between instructions and data | Unambiguous long prompts | No security value | Tiny one-line prompts |
| Role prompting | Shifts toward an author's distribution | Sets tone and focus cheaply | Adds no knowledge | As a substitute for specifics |
| Chain of thought (prompted) | Extra tokens = extra serial compute | Helps non-reasoning models | Redundant or refused on reasoning models | On current thinking models; use effort |
| Self-consistency | Errors scatter, right answers converge | Accuracy plus a confidence score | N× cost; needs comparable answers | Long free-form outputs |
| Templates | Separate fixed text from variables | Versioning, evals, caching | Variables are an injection path | One-off exploration |

## What it didn't solve

The model's output is free-form text. Code that needs a field, a label or a JSON object has to parse prose, and a sampled model (P4) sometimes adds a preamble, drops a field or renames a key. Asking nicely for JSON and the old prefill trick reduced failures but never eliminated them, and prefill is now gone. Software needs output that is guaranteed to match a schema.

→ Next: [§06 Structured Outputs](06-structured-outputs.md)

## Check your understanding

**Q: Why does a chatbot built on the Messages API remember your name from three turns ago, if the model is stateless?**

Your code resends the whole conversation on every call, so the earlier turn is literally in the context window again (P2). The consequence is that cost and latency grow with conversation length, and the context window eventually forces you to trim or summarize. Server-side state options (Responses, Interactions) only move the replay to the vendor; you still pay for those input tokens.

**Q: What would happen if you put the current timestamp at the top of a long cached system prompt?**

Caching is an exact prefix match, so a prefix that changes every request never matches. Every call would pay cache-write prices (1.25× base) instead of reads (0.1× or less), making it more expensive than no caching. Put volatile values after the last cache breakpoint, or in the user turn.

**Q: Why did Anthropic remove assistant prefill, and what replaces it?**

Prefill worked by writing the first output tokens yourself, which conditioned everything after (P1). It conflicts with thinking, which is meant to come before the answer, and newer models follow instructions well enough that the trick became dead weight (P12); Claude 4.6 and later return a 400 for it. Use structured outputs for format, system-prompt instructions for preambles, and a user message for continuations.

**Q: Temperature vs effort: which dial controls what on a current Claude model?**

Temperature rescales the logits before sampling, trading determinism for diversity. On current Claude models it's deprecated, and any value other than 1.0 is rejected. Effort controls how much work the model puts into the response: how readily and deeply it thinks, and how many tool calls it makes. To reduce variability now, use structured outputs and evals rather than temperature.

**Q: Why do few-shot examples sometimes make output worse?**

The model continues patterns from everything in its context, so it copies your examples' length, phrasing and label balance along with the intended format. Three short positive examples teach "be short and positive". Make examples diverse, wrap them in tags, and drop them once a schema or structured output can enforce the format.

**Q: What would happen if your streaming code assumed an HTTP 200 meant the response would complete?**

SSE streams can carry an `error` event, such as `overloaded_error`, after the 200 status and partway through the text. Code that ignores it would show a truncated answer as if it were complete, or crash on a missing `message_stop`. Handle error events and check the final `stop_reason`, and on current models resume through a user message rather than prefill.

**Q: Why are XML tags in a prompt not a defense against prompt injection?**

Tags help the model tell instructions from data, but every token, inside tags or not, flows through the same attention channel, and a persuasive instruction inside a `<document>` can still be followed (P9). Relying on tags would give false confidence. Real defenses are least privilege on tools and keeping a human in the loop for risky actions ([§32](32-security-guardrails.md)).

## Takeaways

- An LLM API is one stateless `POST`: model, `max_tokens`, `system`, and the full `messages` history every time (P2).
- Roles are rendered into a single token sequence; the system prompt sets priority, not security (P9).
- Read `content` by block type and check `stop_reason` before trusting the output.
- `usage` is your cost meter; prompt caching makes resending long prefixes affordable.
- Streaming is SSE: `message_start`, block start/delta/stop, `message_delta`, `message_stop`; errors can arrive after the 200.
- Every prompt technique works by conditioning the next-token distribution (P1); know the mechanism and you know when it fails.
- On current Claude models, temperature, top-p/top-k and prefill are gone; effort and structured outputs replace them.
- Prompts are brittle and version-coupled, so measure them with evals rather than trusting them (P4).

## Sources

- OpenAI, "OpenAI API" (Jun 11, 2020): https://openai.com/index/openai-api/
- OpenAI, "Introducing ChatGPT and Whisper APIs" (Mar 1, 2023): https://openai.com/index/introducing-chatgpt-and-whisper-apis/
- Brown et al., "Language Models are Few-Shot Learners" (GPT-3, 2020): https://arxiv.org/abs/2005.14165
- Anthropic docs, Messages API reference: https://platform.claude.com/docs/en/api/messages
- Anthropic docs, Using the Messages API: https://platform.claude.com/docs/en/build-with-claude/working-with-messages
- Anthropic docs, Streaming: https://platform.claude.com/docs/en/build-with-claude/streaming
- Anthropic docs, Versions: https://platform.claude.com/docs/en/api/versioning
- Anthropic docs, Prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Anthropic docs, Pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic docs, Thinking (sampling and prefill limits): https://platform.claude.com/docs/en/build-with-claude/thinking
- Anthropic docs, Prompting best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- Anthropic, "Effective context engineering for AI agents" (Sep 29, 2025): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- OpenAI docs, Migrate to the Responses API: https://developers.openai.com/api/docs/guides/migrate-to-responses
- OpenAI docs, Conversation state: https://developers.openai.com/api/docs/guides/conversation-state
- OpenAI docs, Text generation and prompting: https://developers.openai.com/api/docs/guides/text
- Google, Gemini Interactions API: https://ai.google.dev/gemini-api/docs/interactions
- Google, Gemini text generation: https://ai.google.dev/gemini-api/docs/text-generation
- Wei et al., "Chain-of-Thought Prompting" (2022): https://arxiv.org/abs/2201.11903
- Wang et al., "Self-Consistency" (2022): https://arxiv.org/abs/2203.11171
- Olsson et al., "In-context Learning and Induction Heads" (2022): https://transformer-circuits.pub/2022/in-context-learning-and-induction-heads/index.html
- Zhao et al., "Calibrate Before Use" (2021): https://arxiv.org/abs/2102.09690
- Sclar et al., "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design" (2023): https://arxiv.org/abs/2310.11324
