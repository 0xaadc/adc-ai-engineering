# 05. The API and Prompt Engineering

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This section starts the system thread and the prompt-engineering era (2020–2023). Part 1 explained the model, and [§04](04-reasoning-models.md) ended in 2025; now we rewind to 2020. On Jun 11, 2020, OpenAI opened the GPT-3 API in private beta as a "text in, text out" interface: you sent a prompt string and the model continued it. On Mar 1, 2023, Chat Completions replaced the string with a list of role-tagged messages. Anthropic's Messages API took the same shape, replacing its older Text Completions format of `\n\nHuman:` / `\n\nAssistant:` turns (launch date **⚠ verify**). This section covers what goes over the wire, why the API forgets everything between calls, and which prompt techniques work, and why.

## Why this exists

**You don't run the model; a vendor does.** Frontier models need GPU clusters (P10), so you reach them over HTTP. The API is the contract between your code and a stateless next-token function (P1, P2).

**Underneath every API is one token sequence.** The model never sees "messages" or "roles". The server renders your request into a single sequence using a *chat template*, with special tokens marking who said what, and the model predicts what comes next. Post-training ([§02](02-how-llms-work.md)) taught the model that template. That's why vendors expose structured messages instead of raw strings: they control the rendering, and the model behaves best in the format it was trained on.

**In the GPT-3 era, the prompt was the whole program.** With no tools, structured outputs or reasoning models, the only lever was the text in front of the model. *Prompt engineering*, the craft of choosing that text, grew up around that lever.

## How it works (under the hood)

### The raw request and response

The whole request is one HTTPS `POST` to `https://api.anthropic.com/v1/messages` **(GA)**. It carries three headers (your API key, a pinned API version and the content type) and a JSON body that names the model, caps the output and carries the conversation.

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
  "usage": {"input_tokens": 31, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
            "output_tokens": 96, "output_tokens_details": {"thinking_tokens": 52}}
}
```

`content` is a *list of typed blocks*, not a string. Current Claude models think adaptively by default (§04), so a `thinking` block may come first, empty unless you ask for summaries. Always select blocks by `type`.

### Roles and the system prompt

- **`messages`** holds `user` and `assistant` turns. The first must be `user`, and consecutive same-role turns are merged. `content` is a string or a list of blocks: text, images, documents, tool calls and results ([§10](10-tool-use.md)), and thinking.
- **`system`** is a top-level field, not a message. It holds the developer's standing instructions: role, rules, format, background. Post-training gives it more weight than user text. Newer models, including Claude Opus 5.5 and Claude Sonnet 5.5, also accept `role: "system"` messages *inside* `messages` **(GA)** for operator instructions that arrive mid-conversation.
- **Everything is rendered into one sequence,** in the order tools, then system, then messages, and the model continues from the end:

```text
what you send                            what the model sees
─────────────                            ───────────────────────────────────────────────
tools:    [...]        ─┐
system:   "..."         ├── render ──▶   [tools][system][user][assistant][user] … [assistant: ▌
messages: [u, a, u, …]  ┘                                                          next token
```

So the system prompt is just more tokens in the same channel as user text and retrieved documents, and text in any of them can act as an instruction (P9). The system prompt sets priorities; it isn't a security boundary ([§32](32-security-guardrails.md)).

### Statelessness (P2): you resend everything

The API keeps nothing between calls. Anthropic's docs put it plainly: the Messages API "is stateless, which means that you always send the full conversational history". Any memory in a chat app is maintained by your code:

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

The printed `input_tokens` climbs with every turn. The consequences:

- **Cost grows with length.** Turn k resends all earlier turns, so total input over n turns grows roughly with n². Caching (below) keeps this affordable.
- **The context window is a hard wall (P3).** Eventually history has to be trimmed, summarized or compacted ([§16](16-context-engineering.md)).
- **You own the history.** You can insert synthetic turns, such as few-shot examples written as past exchanges. On current models, editing *earlier* turns invalidates stored thinking blocks, so append-only is the safe default (§04).

In data-engineering terms, each call recomputes a view from the full event log, and caching is the materialization. Server-side state (OpenAI's `previous_response_id`, Gemini's `previous_interaction_id`, Anthropic's Managed Agents sessions in [§20](20-agent-runtime.md)) only moves the replay to the vendor; OpenAI's docs state that replayed tokens are still billed as input.

### Parameters

- **`max_tokens`** (required) is a hard cap on generated tokens, *thinking included*. When the model hits it, `stop_reason` is `"max_tokens"` and the text ends mid-thought. The Python SDK insists on streaming above 21,333 tokens to avoid HTTP timeouts.
- **`temperature`** divides the model's raw scores (*logits*) by T before the softmax turns them into probabilities. T < 1 sharpens the distribution toward the top token; T > 1 flattens it. Even T = 0 isn't fully deterministic (P4). **Status, Oct 2026:** Anthropic has deprecated it. Models released after Claude Opus 4.6, which includes every current model ID, reject any value except 1.0 with a 400, and reject non-default `top_p` and `top_k` too. Google's Gemini 4 and 3.6+ ignore custom sampling values and return deprecation warnings. Neither vendor's docs give a reason. A plausible one is that RL-trained models are tuned at their native sampling settings, leaving effort (§04) as the dial you're expected to turn.
- **`stop_sequences`** are strings that end generation when produced. `stop_reason` becomes `"stop_sequence"` and the `stop_sequence` field names the match, for example to cut output at `</answer>`.

### `stop_reason`, usage and token counts

Check `stop_reason` before you use `content`. A refusal is a normal HTTP 200.

| `stop_reason` | Meaning | What your code should do |
|---|---|---|
| `end_turn` | Natural stopping point | Use the output |
| `max_tokens` | Hit your cap | Treat as truncated: raise the cap, lower effort, or continue |
| `stop_sequence` | Emitted one of your stop strings | Parse up to the stop |
| `tool_use` | Model wants a tool run | Execute it and send the result ([§10](10-tool-use.md)) |
| `pause_turn` | Long server-side turn paused | Send the response back as-is to continue |
| `refusal` | Declined by safety classifiers | Read `stop_details.category`; it isn't an answer |
| `model_context_window_exceeded` | Ran out of context | Trim or compact the history |

`usage` is your cost meter. `input_tokens` counts uncached input, `cache_creation_input_tokens` and `cache_read_input_tokens` count cached input, and the true input total is the sum of all three. `output_tokens` includes thinking (`output_tokens_details.thinking_tokens`). The counts won't match the visible text exactly, because the server adds formatting tokens. `POST /v1/messages/count_tokens` estimates a request before you send it. As a worked example, at `claude-sonnet-5-5`'s $2 / $10 per million input / output tokens (Oct 2026), a 20,000-token history plus a 500-token answer costs $0.045 per turn before caching.

### Streaming (SSE)

Streaming sends tokens as they are decoded, so the user sees words after the time-to-first-token from [§03](03-inference.md) rather than after the whole generation. Set `"stream": true` and the response becomes *server-sent events* (SSE): one long-lived HTTP response made of named events.

```text
event: message_start        data: {"type":"message_start","message":{"id":"msg_...","content":[],"usage":{...}}}
event: content_block_start  data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}
event: content_block_delta  data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Idempotent"}}
event: ping                 data: {"type":"ping"}
event: content_block_stop   data: {"type":"content_block_stop","index":0}
event: message_delta        data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":87}}
event: message_stop         data: {"type":"message_stop"}
```

The delta types are `text_delta`, `input_json_delta` (tool arguments), `thinking_delta` and `signature_delta`. Usage counts in `message_delta` are cumulative. An `error` event such as `overloaded_error` can arrive *after* the HTTP 200, so streaming code must handle mid-stream failure. On current models you recover a cut-off stream with a new user message ("Your previous response was interrupted and ended with [...]. Continue from where you left off."), not with prefill.

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

Every technique changes the tokens the next-token distribution is conditioned on (P1), so that probability mass concentrates on the output you want.

**Clear, specific instructions.** "Summarize this" is consistent with many tasks of different lengths, audiences and emphases, so the output distribution spreads across all of them. Explicit constraints prune those readings, and instruction tuning ([§02](02-how-llms-work.md)) trained the model to obey them. Giving the *reason* behind a constraint lets the model generalize: Anthropic's example is that "this will be read aloud by text-to-speech, so never use ellipses" beats "NEVER use ellipses". The test is whether a capable new colleague with no context could follow the prompt.

**Examples (few-shot).** *Few-shot prompting* puts worked input→output examples in the prompt. The GPT-3 paper ("Language Models are Few-Shot Learners") showed that models learn tasks *in context*, with no weight update. One proposed mechanism is the *induction head* (Olsson et al. 2022), an attention circuit that finds an earlier occurrence of the current token and copies what followed it. The consequence is that models copy *everything* about your examples: length, phrasing, label balance. Use 3–5 diverse examples in `<example>` tags so they read as examples, not instructions.

**Structure with XML tags.** Tags such as `<instructions>`, `<document>` and `<data>` give unambiguous boundaries between instructions and material. You can refer to sections by name ("using only `<contract>`"), and the distinctive tag tokens are easy for attention to match. For long inputs, put documents first and the question last; Anthropic reports up to 30% better quality from that ordering in its tests. Tags organize the prompt, but they don't stop instructions injected inside the data (P9).

**Role prompting.** "You are a senior data engineer reviewing a migration plan" shifts the distribution toward what that author would write: vocabulary, rigor, what gets flagged. It goes in the system prompt. It adds no knowledge (P5), and superlatives ("world-class expert") add little beyond specific instructions.

**Chain of thought.** Asking the model to work step by step buys extra serial compute and a scratchpad, the mechanism in §04. It was *the* reasoning technique of 2022–2023. On current models it's built in and governed by effort. Asking the model to write its internal reasoning into the answer duplicates that work, and on the newest Claude models it can trigger a `reasoning_extraction` refusal. If you need an explanation, ask for one written *for the reader*.

**Self-consistency.** Sample several independent answers and take the majority. Wang et al. (2022) reported +17.9% on GSM8K over plain CoT. It works because wrong reasoning paths scatter across different answers while right ones converge. It costs N×, needs answers you can compare, and the agreement rate is a free confidence score:

```text
answers    = [extract_final_answer(call_model(prompt)) for _ in range(N)]   # run in parallel
best       = most_common(answers)
confidence = answers.count(best) / N   # low agreement → escalate to a human or a stronger model
```

**Prompt templates.** A *template* separates fixed instructions from variable slots, as in `SYSTEM + "<ticket>{ticket_text}</ticket>"`. Like a dbt model with Jinja variables, it can be version-controlled and evaluated per version ([§26](26-evals.md)). Stable text first and variables last is also what caching rewards. The variable is untrusted data entering the instruction channel, so always tag it (P9).

### Prefill: what it was, and its status

*Prefill* meant ending `messages` with a partial `assistant` turn, such as `{"role": "assistant", "content": "{"}`. You wrote the first output tokens, and everything after was conditioned on them (P1). It was used to force JSON, skip preambles, steer past bad refusals and resume cut-off responses.

**Status, Oct 2026:** Claude 4.6 and later models return a 400 error for a prefilled final assistant turn. Earlier models already disallowed it while thinking was on, presumably because a prefilled answer would skip the thinking meant to come first. Assistant turns *earlier* in the history are still fine. The replacements are structured outputs for format ([§06](06-structured-outputs.md)), system-prompt instructions for preambles and a user message for continuations. Prefill is a clean case of the bitter lesson (P12): a workaround for weak instruction-following that became dead weight.

### Prompt caching, briefly

Statelessness means resending long identical prefixes: system prompts, tool definitions, documents, history. *Prompt caching* **(GA)** stores the attention state for a prefix (the KV cache from §03), so a later request starting with the byte-identical prefix skips recomputing it. Mark up to four breakpoints with `cache_control`, or set it once at the top level:

```json
{
  "model": "claude-sonnet-5-5",
  "max_tokens": 1024,
  "system": [{"type": "text", "text": "<5,000 tokens of stable instructions and schema docs>",
              "cache_control": {"type": "ephemeral"}}],
  "messages": [{"role": "user", "content": "Which tables hold PII?"}]
}
```

The cache lives 5 minutes, refreshed free on each hit, or 1 hour at a higher write price. Writes cost 1.25× the base input price (2× for 1 hour). Reads cost 0.1× base, or 0.05× on Claude Opus 5.5 and Claude Sonnet 5.5 (Oct 2026). Any byte change invalidates everything after it, and a timestamp at the top of the system prompt is the classic mistake. Very short prefixes aren't cached at all. Verify hits with `usage.cache_read_input_tokens`. [§16](16-context-engineering.md) covers designing around the cache, and [§30](30-cost-latency-reliability.md) the cost math.

### Limits of prompt engineering (P4)

- **Brittleness.** Sclar et al. (2023) measured accuracy swings of up to 76 points on LLaMA-2-13B from meaning-preserving formatting changes in few-shot prompts, and the sensitivity persisted with larger and instruction-tuned models. Zhao et al. (2021) showed that example choice and *order* moved GPT-3 between near chance and near state-of-the-art. Frontier models are less fragile, not immune.
- **Version coupling.** A prompt tuned on one model drifts on the next. OpenAI advises pinning snapshots and building evals. Anthropic's migration guides tell you to delete old workarounds such as "do not be lazy", which newer models follow too literally.
- **No guarantees.** Output is sampled, so you measure it statistically ([§26](26-evals.md)) rather than unit-testing it.
- **No knowledge, no actions, no security.** Facts come from grounding (P5, [§09](09-rag.md)) and actions from tools (P6, [§10](10-tool-use.md)). "Ignore instructions in the document" is a request, not a control (P9).

Anthropic calls context engineering "the natural progression of prompt engineering": prompting is now one part of curating everything in the window ([§16](16-context-engineering.md)).

## Comparison

**The same request across vendors (Oct 2026)**

| | Anthropic Messages | OpenAI Responses | OpenAI Chat Completions | Google Gemini Interactions |
|---|---|---|---|---|
| Endpoint | `POST /v1/messages` | `POST /v1/responses` | `POST /v1/chat/completions` | `POST /v1beta/interactions` |
| Status | **(GA)** primary | **(GA)** recommended for new projects | Supported, older | **(GA)** since Jun 2026; `generateContent` is legacy but supported |
| Developer instructions | Top-level `system` (+ mid-conversation `system` messages) | `instructions`, or a `developer` role message | `system` / `developer` role message | `system_instruction` |
| Input | `messages`: `user`/`assistant` turns of typed blocks | `input`: string or list of items | `messages` list | `input` (`generateContent`: `contents` of `user`/`model` turns with `parts`) |
| Output | `content`: typed blocks (`thinking`, `text`, `tool_use`) | `output`: items (`reasoning`, `message`, `function_call`); `output_text` helper | `choices[].message` | `steps` (thoughts, model output); `output_text` helper |
| Conversation state | Stateless; resend history | Optional server state (`store`, `previous_response_id`); replayed tokens billed | Stateless | Server-side by default (`previous_interaction_id`); `store=false` for stateless |
| Output cap | `max_tokens` (required) | `max_output_tokens` | `max_completion_tokens` (`max_tokens` deprecated) | `generation_config.max_output_tokens` |
| Why it stopped | `stop_reason` | `status` + `incomplete_details` | `finish_reason` | `status` |
| Streaming | SSE named events (`message_start` … `message_stop`) | SSE semantic events (`response.output_text.delta`, …) | SSE `data:` chunks | SSE |

The substance is the same everywhere: model, instructions, conversation, output cap and reasoning dial in; typed output and a stop signal out. Server-side history is a convenience, not a stateful model.

## What it didn't solve

The model's output is free-form text. Code that needs a field, a label or a JSON object has to parse prose, and a sampled model (P4) sometimes adds a preamble, drops a field or renames a key. Asking nicely for JSON, and the old prefill trick, reduced failures but never eliminated them. Software needs output that is guaranteed to match a schema.

→ Next: [§06 Structured Outputs](06-structured-outputs.md)

## Check your understanding

**Q: Why does a chatbot built on the Messages API remember your name from three turns ago, if the model is stateless?**

Your code resends the whole conversation on every call, so the earlier turn is literally back in the context window (P2). As a result, cost and latency grow with conversation length, and the context window eventually forces trimming or summarizing. Server-side state options only move the replay to the vendor; you still pay for those input tokens.

**Q: What would happen if you put the current timestamp at the top of a long cached system prompt?**

Caching is an exact prefix match, so a prefix that changes on every request never hits. Every call would pay the cache-write price (1.25× base) instead of the read price (0.1× or less), which is worse than not caching at all. Put volatile values after the last cache breakpoint, or in the user turn.

**Q: Why did Anthropic remove assistant prefill, and what replaces it?**

Prefill worked by writing the first output tokens yourself (P1). That clashes with thinking, which is meant to come before the answer, and newer models follow instructions well enough that the trick became dead weight (P12). Claude 4.6 and later return a 400 for it. Use structured outputs for format, system-prompt instructions for preambles, and a user message for continuations.

**Q: Temperature vs effort: which dial controls what on a current Claude model?**

Temperature rescales logits before sampling, trading determinism for diversity; on current Claude models it's deprecated and anything but 1.0 is rejected. Effort controls how much work goes into a response: how readily and deeply the model thinks and how many tool calls it makes. To reduce variability now, use structured outputs and evals rather than temperature.

**Q: Why do few-shot examples sometimes make output worse?**

The model continues every pattern in its context, so it copies your examples' length, phrasing and label balance along with the format you intended. Three short positive examples teach "be short and positive". Make examples diverse and tagged, and drop them once structured outputs can enforce the format.

**Q: What would happen if your streaming code assumed an HTTP 200 meant the response would complete?**

An SSE stream can carry an `error` event such as `overloaded_error` after the 200, partway through the text. Code that ignores it shows a truncated answer as if complete, or hangs waiting for `message_stop`. Handle error events, check the final `stop_reason`, and resume through a user message, not prefill.

**Q: Why are XML tags in a prompt not a defense against prompt injection?**

Tags help the model tell instructions from data, but every token, tagged or not, flows through the same attention channel, and a persuasive instruction inside a `<document>` can still be followed (P9). Treating tags as a defense gives false confidence. Real defenses are least privilege on tools and human approval for risky actions ([§32](32-security-guardrails.md)).

## Takeaways

- An LLM API call is one stateless `POST`: model, `max_tokens`, `system`, and the full `messages` history every time (P2).
- Roles are rendered into a single token sequence; the system prompt sets priority, not security (P9).
- Read `content` by block type and check `stop_reason` before trusting the output; `usage` is your cost meter.
- Streaming is SSE, and errors can arrive after the HTTP 200.
- Every prompt technique works by conditioning the next-token distribution (P1); know the mechanism and you know when it fails.
- On current Claude models, temperature, top-p/top-k and prefill are gone; effort and structured outputs replace them.
- Prompt caching makes resending long prefixes affordable, as long as the prefix stays byte-identical.
- Prompts are brittle and version-coupled, so measure them with evals (P4).

## Sources

- OpenAI, "OpenAI API" (Jun 11, 2020): https://openai.com/index/openai-api/
- OpenAI, "Introducing ChatGPT and Whisper APIs" (Mar 1, 2023): https://openai.com/index/introducing-chatgpt-and-whisper-apis/
- Brown et al., "Language Models are Few-Shot Learners" (GPT-3, 2020): https://arxiv.org/abs/2005.14165
- Anthropic docs, Messages API reference: https://platform.claude.com/docs/en/api/messages
- Anthropic docs, Using the Messages API: https://platform.claude.com/docs/en/build-with-claude/working-with-messages
- Anthropic docs, Streaming: https://platform.claude.com/docs/en/build-with-claude/streaming
- Anthropic docs, Prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Anthropic docs, Pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic docs, Thinking (sampling and prefill limits): https://platform.claude.com/docs/en/build-with-claude/thinking
- Anthropic docs, Prompting best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- Anthropic, "Effective context engineering for AI agents" (Sep 29, 2025): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- OpenAI docs, Migrate to the Responses API: https://developers.openai.com/api/docs/guides/migrate-to-responses
- OpenAI docs, Conversation state: https://developers.openai.com/api/docs/guides/conversation-state
- OpenAI docs, Text generation: https://developers.openai.com/api/docs/guides/text
- Google, Gemini Interactions API: https://ai.google.dev/gemini-api/docs/interactions
- Google, Gemini text generation (sampling deprecation note): https://ai.google.dev/gemini-api/docs/text-generation
- Wang et al., "Self-Consistency" (2022): https://arxiv.org/abs/2203.11171
- Olsson et al., "In-context Learning and Induction Heads" (2022): https://transformer-circuits.pub/2022/in-context-learning-and-induction-heads/index.html
- Zhao et al., "Calibrate Before Use" (2021): https://arxiv.org/abs/2102.09690
- Sclar et al., "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design" (2023): https://arxiv.org/abs/2310.11324
