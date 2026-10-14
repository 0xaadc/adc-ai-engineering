# 10. Tool Use and Tool Design

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This section covers 2022–2023, the start of Part 4. [§09](09-rag.md) gave the model fresh, private facts by placing retrieved text in its context, but the model could still only read and write text. It could say an order had *probably* shipped. It could not look the order up, issue the refund, or run the query that settles the question. Tool use closes that gap. The model asks for an action in a structured form, and your code performs it. The idea grew from a prompting technique (ReAct, 2022) into a standard API feature (OpenAI, 2023; Anthropic, 2024). Agents and everything after them are built on it.

## Why this exists

An LLM is a next-token function (P1). It has no network socket, file handle or database connection. Retrieval alone leaves three gaps:

- **Only the model knows what it needs next.** In RAG, your code chooses what to fetch before the model reasons. Often only the model, partway through, knows it needs order A-1042's status.
- **Side effects.** Sending, writing and booking need code.
- **Exact computation.** Toolformer's authors note that language models "struggle with basic functionality, such as arithmetic or factual lookup."

The first fix was a **text protocol**. ReAct prompted the model to write `Thought:`, `Action: search[...]` and `Observation:` lines. The harness parsed each `Action` line with string matching, ran it, and pasted the result back in as the next observation. With one or two examples it beat imitation and reinforcement learning baselines by 34 and 10 absolute points of success rate on the ALFWorld and WebShop benchmarks. But it was brittle: the format drifted, arguments had no schema, and parse failures were silent. The durable fix moved the protocol **into training and into the API**. You declare tools with JSON Schema. The model is post-trained to emit calls in a fixed format. The API hands you each call as structured data.

| Date | Milestone | What it added |
|---|---|---|
| Oct 2022 | ReAct (Yao et al.) | Reasoning interleaved with actions and observations, in plain text |
| Feb 2023 | Toolformer (Schick et al., Meta) | A model trained, self-supervised, to decide which API to call, when, and with what arguments |
| Jun 13, 2023 | OpenAI function calling | JSON Schema definitions in the API; models fine-tuned to detect when to call a function and reply with matching JSON |
| May 30, 2024 | Anthropic tool use **(GA)** | Tool use across Claude 3, including forced tool use. Parallel calls were not supported yet |
| Nov 2024 | MCP | A standard plug for tool servers (P11); see [§15](15-protocols-mcp-a2a.md) |
| Nov 24, 2025 | Anthropic "advanced tool use" | Tool search, programmatic tool calling and tool use examples, for large tool libraries |

## How it works (under the hood)

### The round trip, step by step

```text
 YOUR CODE                                MESSAGES API + MODEL
 1. POST tools[] + messages[]  ────────▶  schemas rendered into the prompt; model emits a call
 2.                            ◀────────  stop_reason "tool_use"; content [text, tool_use]
 3. validate, authorize, EXECUTE          (model idle: nothing runs on its side)
 4. POST history + tool_result ────────▶  model reads the result as new context
 5.                            ◀────────  stop_reason "end_turn" + answer (or another call → §11)
```

**Step 1: declare the tool.** This is an ordinary `POST https://api.anthropic.com/v1/messages` with headers `x-api-key` and `anthropic-version: 2023-06-01`:

```json
{
  "model": "claude-sonnet-5-5",
  "max_tokens": 16000,
  "tools": [{
    "name": "get_order_status",
    "description": "Look up the shipping status and delivery date of one order. Call this whenever the user asks where an order is. Order IDs look like 'A-1042'.",
    "input_schema": {
      "type": "object",
      "properties": {"order_id": {"type": "string", "description": "Order ID, e.g. A-1042"}},
      "required": ["order_id"]
    }
  }],
  "messages": [{"role": "user", "content": "Where is my order A-1042?"}]
}
```

The model never sees "a function". The API renders the definitions into the prompt, along with a tool-use system prompt of its own (286 extra tokens on Claude Sonnet 5.5 with `tool_choice` `auto`, as of Oct 2026). To the model, a tool is just more context (P1, P3), and the `description` is a prompt.

**Step 2: the model returns a request, not an action.**

```json
{
  "role": "assistant",
  "stop_reason": "tool_use",
  "content": [
    {"type": "text", "text": "Let me look that order up."},
    {"type": "tool_use", "id": "toolu_01A...", "name": "get_order_status",
     "input": {"order_id": "A-1042"}}
  ]
}
```

Sampling stopped when the model emitted the end of a call. The API parsed those tokens into a `tool_use` block (with `input` already a JSON object) and returned control to you. Current Claude models think adaptively by default, so `content` may also contain `thinking` blocks. Echo every block back unchanged.

**Step 3: your code executes it (P6).** Validate `input`, or set `"strict": true` on the tool (the schema then needs `"additionalProperties": false`) to have constrained decoding ([§06](06-structured-outputs.md)) guarantee a schema match. Authorize the call: may *this user* see this order? Then run it and capture any failure.

**Step 4: send back a `tool_result`.** You resend the full history (P2): the user turn, the assistant turn exactly as received, then a new user turn:

```json
{"role": "user", "content": [
  {"type": "tool_result", "tool_use_id": "toolu_01A...",
   "content": "{\"status\": \"shipped\", \"eta\": \"2026-10-16\"}"}
]}
```

The result must come in the user turn right after the call, and `tool_result` blocks must come before any text in it. Every `tool_use_id` needs an answer.

**Step 5: the model continues.** It answers (`"stop_reason": "end_turn"`, "Your order shipped and should arrive October 16") or asks for another tool. Repeating steps 2–4 is the agent loop of [§11](11-agents.md).

### The same round trip in Python

```python
import json
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-5-5"
TOOLS = [{
    "name": "get_order_status",
    "description": ("Look up the shipping status and delivery date of one order. Call this "
                    "whenever the user asks where an order is. Order IDs look like 'A-1042'."),
    "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}},
                     "required": ["order_id"]},
}]
ORDERS = {"A-1042": {"status": "shipped", "eta": "2026-10-16"}}  # stands in for your DB

def get_order_status(order_id: str) -> str:  # YOUR code: the model never runs it (P6)
    if order_id not in ORDERS:
        raise ValueError(f"No order {order_id}. IDs look like 'A-1042'; ask the user to check.")
    return json.dumps(ORDERS[order_id])

messages = [{"role": "user", "content": "Where is my order A-1042?"}]
resp = client.messages.create(model=MODEL, max_tokens=16000, tools=TOOLS, messages=messages)
messages.append({"role": "assistant", "content": resp.content})  # every block, unchanged

results = []
for block in resp.content:                    # present when stop_reason == "tool_use"
    if block.type == "tool_use":
        try:
            out, failed = get_order_status(**block.input), False
        except (ValueError, TypeError) as e:  # unknown ID or bad arguments: tell the model
            out, failed = str(e), True
        results.append({"type": "tool_result", "tool_use_id": block.id,
                        "content": out, "is_error": failed})

if results:                                   # all results go back in ONE user message
    messages.append({"role": "user", "content": results})
    resp = client.messages.create(model=MODEL, max_tokens=16000, tools=TOOLS, messages=messages)
print(resp.stop_reason, "".join(b.text for b in resp.content if b.type == "text"))
```

Production code also checks for other stop reasons before executing anything. On `max_tokens` the input may be truncated. On `refusal`, run nothing.

### Why the model never runs anything itself

The model's whole interface is tokens in and tokens out (P1). "Calling a tool" means predicting a token pattern that post-training taught it to emit. The API converts that pattern into a block and stops. Anthropic's docs say it directly: "The model never executes anything on its own." Three consequences follow:

- **All capability and all risk live in the executor** (P6). Authorization, validation, rate limits, audit logs and approval gates belong there, as code, not as prompt text.
- **Treat tool inputs like web-form input.** The model can request a hallucinated ID, a path outside the project, or a refund above policy.
- **The same rule holds for server tools.** When Anthropic runs web search, Anthropic's code runs it. The model still only asked; only the owner of the code that disposes changes.

### Parallel calls and `tool_choice`

One response can hold several `tool_use` blocks (weather for two cities, three file reads). Run independent calls concurrently and return **all** results in **one** user message. The docs warn that splitting them across messages teaches the model to stop making parallel calls. Parallelism matters because each round trip resends the whole context (P10). Your executor still decides what is safe to run together: two reads are safe, a commit and a push are not.

| `tool_choice` | Meaning |
|---|---|
| `{"type": "auto"}` (default) | The model calls zero, one or several tools |
| `{"type": "any"}` / `{"type": "tool", "name": ...}` | The model must call some tool, or this tool |
| `{"type": "none"}` | No tool calls |
| `"disable_parallel_tool_use": true` (inside `tool_choice`) | At most one call per turn |

As of Oct 2026, **Claude Sonnet 5.5, Opus 5.5 and Fable 5.1 reject `any` and `tool` with a 400 error.** On those models, use `auto` with an explicit instruction plus `strict: true`, and check that a call actually happened. Forcing a tool used to be the standard trick for extracting JSON. Structured outputs ([§06](06-structured-outputs.md)) now do that job directly.

### Client tools vs server tools

Anthropic sorts tools by **where the code runs**:

1. **User-defined client tools.** You write the schema and the code. This is most tool traffic.
2. **Anthropic-schema client tools.** Anthropic publishes and trains the schema, and your app executes the call. Examples are `bash_20250124`, `text_editor_20250728`, `memory_20250818` and `computer_toolset_20260801`. Because the schema is trained in, the model calls these more reliably than home-made equivalents.
3. **Server tools (GA, no beta header).** Anthropic executes them, and you never build a `tool_result`. As of Oct 2026 the latest versions are `web_search_20260318`, `web_fetch_20260318`, `code_execution_20260521`, and `tool_search_tool_regex_20251119` / `tool_search_tool_bm25_20251119`. The server runs its own capped loop. When it hits the cap you get `stop_reason: "pause_turn"`, and you resend the conversation to continue.

The date suffix is a version. Old versions keep working, so pin one and upgrade deliberately, as you would a dependency.

### Tool errors and `is_error`

When a tool fails (a timeout, an unknown ID) or a call is invalid (a missing parameter), return a `tool_result` with `"is_error": true` and an **instructive** message. The docs contrast "Rate limit exceeded. Retry after 60 seconds." with a bare "failed". Claude typically retries an invalid call 2–3 times with corrections before giving up, and `strict: true` removes schema errors altogether. Server-tool failures come back as result blocks with codes such as `max_uses_exceeded`. Don't confuse any of these with **API errors**, such as an HTTP 429 or 5xx from the model endpoint. The model never sees those, and your code retries them ([§30](30-cost-latency-reliability.md)).

Why return errors to the model instead of raising? The model is the only component that can change the plan. It can fix the argument, pick another tool, or ask the user. An exception ends the turn, while a good error message steers the next one. Never leave a call unanswered, because the API rejects history with an orphaned `tool_use`.

### Tool design: write for a model, not a programmer

Anthropic's "Writing effective tools for agents" (Sep 11, 2025) calls tools "a contract between deterministic systems and non-deterministic agents." The key asymmetry is that computer memory is cheap, but the agent's context is a small attention budget (P3). Mirroring your REST endpoints one-to-one therefore produces bad tools. The post's principles:

- **Fewer, higher-level tools.** Use `search_contacts`, not `list_contacts`. Use `schedule_event`, not `list_users` + `list_events` + `create_event`. Use `get_customer_context`, not three lookups. In data-engineering terms, wrapping every endpoint is like handing analysts raw source tables. A good tool is the curated mart that answers the question.
- **Clear names and namespacing.** With many servers connected, prefixes (`asana_search` vs `jira_search`) help the model choose. The post found that the choice between prefix and suffix naming had "non-trivial effects" on its evals.
- **Descriptions written for the model.** Write as you would for a new hire: formats, jargon, how resources relate, and *when* to use the tool. Name parameters unambiguously (`user_id`, not `user`). Anthropic credits description refinements for Claude 3.5 Sonnet's state-of-the-art SWE-bench Verified result. "Building effective agents" adds **poka-yoke** (mistake-proofing): its SWE-bench agent fumbled relative paths until the tool required absolute ones.
- **Meaningful, token-efficient results.** Return names, not UUIDs, and offer a `response_format` of `"concise"` or `"detailed"`. The post's concise Slack response used 72 tokens instead of 206. Paginate, filter and truncate with sensible defaults (as of the post, Claude Code capped tool responses at 25,000 tokens by default), and say how to get more.
- **Errors that say how to fix the problem**, "rather than opaque error codes or tracebacks."

```text
Bad:   list_contacts()                  -> all 5,000 contacts, with UUIDs; error "400"
Good:  search_contacts(query, limit=10) -> 10 matches: name, email, id; error
       "No contact matches 'Jon Smth'. Closest: 'Jon Smith' (id 42). Retry with that id."
```

The same post argues for evaluating tools on realistic tasks, as you would any prompt change ([§26](26-evals.md)). One more choice is **bash vs dedicated tools**. Bash gives the model breadth through one opaque command string. A dedicated tool (`send_email`) gives your harness typed arguments it can gate, audit, render and parallelize. Start broad, and promote an action to its own tool when you need to control it.

### The cost of tool definitions (P3)

The model is stateless (P2), so every request resends every tool definition at the front of the prompt. In Anthropic's example, five common MCP servers expose 58 tools that cost about 55K tokens before the user says anything, and Anthropic has seen 134K internally. You pay three times: in money and latency on every turn (P10), in worse selection among overlapping tools (P3), and in less room for the task. Prompt caching helps because tools are the most stable prefix, but changing the tool list invalidates the cache.

### Tool search and programmatic tool calling

Anthropic's "advanced tool use" post (Nov 24, 2025) attacks that cost from two sides. The figures below are vendor-reported internal results.

- **Tool search (GA).** Add a tool search tool and mark the other tools `"defer_loading": true`. The model starts with only the search tool (and any non-deferred tools) in context, searches when it needs something, and the API appends the matching definitions as `tool_reference` blocks (up to 5 by default), which keeps the cache intact. Anthropic reports 85% fewer tokens. On its MCP evals, accuracy rose from 49% to 74% for Opus 4 and from 79.5% to 88.1% for Opus 4.5. The price is an extra search step, so the post suggests it once definitions exceed about 10K tokens. This is retrieval ([§08](08-embeddings-and-search.md)) applied to tools.
- **Programmatic tool calling (GA).** Mark a tool `"allowed_callers": ["code_execution_20260120"]` (that code execution version or later). The model writes a script in the sandbox that calls the tool as a function. Each call pauses the script and reaches you as a normal `tool_use`. Your result flows back **into the script, not into the model's context**, and only the script's final output does. Average tokens on complex research tasks fell from 43,588 to 27,297.
- **Tool use examples.** An optional `input_examples` field shows sample calls. Accuracy on complex parameters rose from 72% to 90%.

### Code as action: CodeAct and smolagents

A JSON call is one action. It can't loop, branch, or hold a DataFrame between calls. **CodeAct** (Wang et al., Feb 2024) let the agent write executable Python instead, and across 17 LLMs it beat JSON and text actions by up to 20% in success rate. Hugging Face's **smolagents** (Dec 31, 2024) made this the default: its `CodeAgent` writes each action as code, which its docs say gives better composability, object management and generality. Anthropic's "Code execution with MCP" (Nov 4, 2025) presents MCP tools as code files the agent imports on demand, which in its example cut 150,000 tokens to 2,000. Programmatic tool calling is the same idea built into the API. The tradeoff is that arbitrary code needs a sandbox ([§20](20-agent-runtime.md)), and individual actions become harder to gate and audit.

### Security preview: tools are where injection does damage (P9)

Without tools, a successful prompt injection produces bad text. With tools, it produces bad actions. Every tool *result* (a web page, an email, a ticket) lands in the same channel as your instructions (P9). Simon Willison's **lethal trifecta** (Jun 16, 2025) names the dangerous mix: private data, untrusted content, and a way to communicate externally. Defend at the tool layer:

- read-only by default, with user-scoped credentials ([§33](33-agent-identity.md))
- separate read tools from write tools, so writes can be gated
- human approval for irreversible actions
- validate arguments (paths, SQL, URLs)
- allowlist egress
- treat MCP tool annotations as hints, never as enforcement

[§32](32-security-guardrails.md) covers this in full.

### Failure modes

- **Wrong tool**, from overlapping names. Merge or namespace the tools.
- **Wrong or hallucinated arguments.** Use enums, `strict`, examples, and instructive errors.
- **No call when one was needed.** Say *when* to call in the description.
- **Result floods that bury the task** (P3). Paginate and truncate.
- **Broken history:** dropped `thinking` blocks or unanswered calls.
- **Executing a `max_tokens`-truncated call.**
- **Obeying instructions found inside tool output** (P9).

## Comparison

**Ways a model can act**

| Approach | How it works | Strength | Weakness | When to choose |
|---|---|---|---|---|
| Text protocol (ReAct-style) | The model writes `Action: tool[args]`, and you parse it | Works with any model | Brittle; no schema; silent parse failures | Models without native tools |
| Native function calling | JSON Schema in, `tool_use` block out | Trained in, typed, easy to gate | One action per call; definitions cost tokens | The default |
| Server tools | The provider executes (search, fetch, sandbox) | No executor to build | Less control over execution and data path | Commodity capabilities |
| Tool search | Definitions deferred, found on demand | Large libraries cheaply | An extra step; needs good descriptions | Definitions above about 10K tokens |
| Code as action / PTC | The model writes code that calls tools | Loops and filtering; much less context | Sandbox needed; coarse gating | Many chained calls, big intermediate data |

**Provider shapes (as of Oct 2026)**

| | Anthropic Messages | OpenAI Responses | Google Gemini |
|---|---|---|---|
| Declare | `name`, `description`, `input_schema` | `type: "function"`, `name`, `parameters`, `strict` | function declarations |
| Model's call | `tool_use` block, `input` is an object | `function_call` item, `arguments` is a JSON *string* | function-call step |
| Your reply | `tool_result` block (`tool_use_id`, `is_error`) in a user turn | `function_call_output` item (`call_id`) | function result |
| Control | `tool_choice` `auto`/`any`/`tool`/`none` | `auto`/`required`/named/`allowed_tools`, `parallel_tool_calls` | `auto`/`any`/`none`/`validated` |

OpenAI's older Chat Completions API uses `message.tool_calls` and `role: "tool"` replies. The contract is identical everywhere. Only the field names differ.

## What it didn't solve

One tool call is one step. The round trip above worked because the question needed one lookup. Real tasks, such as "fix the failing test" or "find out why last night's pipeline broke," need many steps, and you can't know their number or order until you see each result. Something has to keep calling the model, executing its requests, feeding back results, and deciding when to stop. → Next: [§11 Agents and the Agent Loop](11-agents.md)

## Check your understanding

**Q: Why does the model never execute a tool itself, and where does that put your security checks?**

The model only emits tokens (P1). The API parses a call into a `tool_use` block, and nothing happens until your code chooses to act (P6). Authorization, validation and approval gates therefore belong in the executor, where they are deterministic. "Never refund more than $100" in a prompt is a request to a probabilistic system. The same rule in the executor is a guarantee.

**Q: Why did the field move from ReAct-style text parsing to API-level function calling?**

Text protocols need the model to reproduce a format perfectly, and sampling (P4) guarantees that it sometimes won't, failing silently. Function calling trains the format in and moves parsing into the API. You get schema-checked arguments (guaranteed with `strict`) and an explicit `stop_reason`. Text parsing remains only for models without native tools.

**Q: What would happen if a tool threw an exception and your loop crashed instead of returning `is_error: true`?**

The turn dies, and the one component that could adapt, the model, never learns what went wrong. An error result that names the fix lets it correct the argument, choose another tool, or ask the user. Crash or escalate only on failures the model can't fix, such as a revoked credential.

**Q: Why expose `search_contacts(query)` instead of the more flexible `list_contacts()`?**

The agent's context is a scarce attention budget (P3), while your database's memory is cheap. Listing everything makes the model scan thousands of records token by token, which costs money (P10) and invites mistakes. Filtering in code returns only the signal. Keep low-level tools only where evals show the agent needs them.

**Q: Your agent has 60 tools from five MCP servers and uses three per task. Why does that still hurt, and what can you do?**

All 60 definitions are resent every turn (P2), tens of thousands of tokens that cost money and dilute selection (P3). In order: prune or merge tools, cache the stable prefix, defer rarely used tools behind tool search, and push chained calls into programmatic tool calling. With only a handful of tools, skip tool search, because the extra step isn't worth it.

**Q: Code as action vs JSON tool calls: when would you choose each?**

JSON calls are single typed actions that are easy to validate, gate and audit, which suits consequential writes. Code actions loop, filter and combine many calls in one step, saving context and round trips on bulk reads and data wrangling. Their cost is a sandbox and coarser control. Many systems use both.

**Q: Why is an agent with a "read inbox" tool and a "fetch URL" tool dangerous, even if each tool is harmless alone?**

Together they complete the lethal trifecta: private data, untrusted content (any email can carry instructions), and an exfiltration channel (a URL can carry data out in its query string). Because instructions and data share one channel (P9), one malicious email can trigger the leak. Remove a leg: allowlist egress, or require approval for outbound calls.

## Takeaways

- Tool use is a contract: the model emits a request (`stop_reason: "tool_use"`), your code executes it, and a `tool_result` goes back (P6).
- The model never runs anything, so capability, risk and security checks all live in the executor.
- Return all parallel results in one user message. Return failures as `is_error` results that say how to fix the problem.
- Design tools for a scarce context: fewer and higher-level, namespaced, described for a new hire, concise and paginated.
- Tool definitions are resent every turn. Tool search and programmatic tool calling exist because large libraries cost tokens and accuracy.
- Code as action trades per-action control for composability and context savings.
- Tools turn injection from bad text into bad actions. Defend with least privilege, not prompts (P9).

## Sources

- Anthropic, "How tool use works": https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works
- Anthropic, Tool use overview (tool system prompt tokens): https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
- Anthropic, Define tools: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
- Anthropic, Handle tool calls (`is_error`, formatting rules): https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls
- Anthropic, Parallel tool use: https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use
- Anthropic, Tool reference (versioned tool types): https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-reference
- Anthropic, Tool search tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool
- Anthropic, Programmatic tool calling: https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling
- Anthropic, "Claude can now use tools" (May 30, 2024): https://www.anthropic.com/news/tool-use-ga
- Anthropic, "Writing effective tools for agents — with agents" (Sep 11, 2025): https://www.anthropic.com/engineering/writing-tools-for-agents
- Anthropic, "Introducing advanced tool use on the Claude Developer Platform" (Nov 24, 2025): https://www.anthropic.com/engineering/advanced-tool-use
- Anthropic, "Code execution with MCP" (Nov 4, 2025): https://www.anthropic.com/engineering/code-execution-with-mcp
- Anthropic, "Building effective agents" (Dec 19, 2024), Appendix 2: https://www.anthropic.com/engineering/building-effective-agents
- Yao et al., "ReAct" (Oct 2022): https://arxiv.org/abs/2210.03629
- Schick et al., "Toolformer" (Feb 2023): https://arxiv.org/abs/2302.04761
- Wang et al., "Executable Code Actions Elicit Better LLM Agents" (CodeAct, Feb 2024): https://arxiv.org/abs/2402.01030
- OpenAI, "Function calling and other API updates" (Jun 13, 2023): https://openai.com/index/function-calling-and-other-api-updates/
- OpenAI, Function calling guide: https://developers.openai.com/api/docs/guides/function-calling
- Google, Gemini function calling: https://ai.google.dev/gemini-api/docs/function-calling
- Hugging Face, "Introducing smolagents" (Dec 31, 2024): https://huggingface.co/blog/smolagents
- Hugging Face, smolagents conceptual guide: https://huggingface.co/docs/smolagents/conceptual_guides/intro_agents
- Simon Willison, "The lethal trifecta for AI agents" (Jun 16, 2025): https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/
