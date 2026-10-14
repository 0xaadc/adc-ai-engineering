# 16. Context Engineering

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

Mid-2025 is where the context-and-harness era (Part 5) begins. [§15](15-protocols-mcp-a2a.md) turned N×M integrations into N+M (P11), so connecting an agent to dozens of tools became easy. That ease created the next problem: tool definitions, tool results and long run histories flood the context window and degrade the model. Anthropic measured 58 tools from five MCP servers taking about 55K tokens before a conversation even started.

The label "context engineering" grew out of this pressure:

- **Apr 2025.** HumanLayer says Dex Horthy coined it in its "12-factor agents" guide (a company claim).
- **Jun 2025.** Shopify CEO Tobi Lütke, then Andrej Karpathy, endorsed it over "prompt engineering".
- **Jul 2025.** LangChain gave it an organizing frame.
- **Sep 2025.** Anthropic called it "the natural progression of prompt engineering".

This section covers context *within* a session. [§17](17-memory.md) covers what persists *across* sessions.

## Why this exists

**The window is the only working memory (P2).** The model keeps nothing between calls. Every turn of an agent loop ([§11](11-agents.md)) re-sends everything: system prompt, tool definitions, and every earlier tool call and result. What the model "knows" is exactly the tokens in the current request. So you choose the window's contents on every turn, not once at design time.

**Attention is a budget, and it rots (P3).** Every token attends to every other token, so n tokens create n² pairwise relationships ([§02](02-how-llms-work.md)), and attention spreads thinner as n grows. Models also see fewer long sequences in training. Anthropic calls the result "a performance gradient rather than a hard cliff."

Chroma's July 2025 "Context Rot" report tested 18 models on deliberately simple tasks while varying only input length. Performance fell with length in every experiment. Its LongMemEval test is the most practical result. Models did well on focused prompts of about 300 tokens that held only the relevant history. They did consistently worse on the full prompts of about 113K tokens, where they had to find the relevant parts first. "Lost in the Middle" (2023) found that facts buried mid-context are used less reliably than facts at the start or end.

**Every token is re-paid every turn (P10).** If each step adds t tokens, step k sends about k·t, and n steps send about t·n²/2 in total. Fifty tool calls returning 2K tokens each make the last request about 100K tokens and the run about 2.5M input tokens. Manus reported an input-to-output ratio of about 100:1, so agents mostly pay for prefill, not decode ([§03](03-inference.md)).

So a bigger window doesn't help by default. Karpathy's definition is "the delicate art and science of filling the context window with just the right information for the next step." Anthropic's is more operational: find "the smallest possible set of high-signal tokens that maximize the likelihood of some desired outcome." An honest note on the label: RAG, summarization and prompt trimming came first. It stuck because agents made curation continuous, and prompt engineering ([§05](05-api-and-prompting.md)) became one part of it.

## How it works (under the hood)

### What's in the window

```text
 ┌─────────────────── one request (re-sent every turn) ───────────────────┐
 │ tools         definitions and schemas           stable    ← cacheable  │
 │ system        role, rules, CLAUDE.md            stable    ← cacheable  │
 │ messages      user / assistant turns            grows                  │
 │               tool_use + tool_result pairs      grows fastest          │
 │               (old file reads, search hits, logs, stack traces ...)    │
 │ latest turn   new question, today's date        volatile               │
 └────────────────────────────────────────────────────────────────────────┘
```

Every layer competes for the same attention budget. In long runs, old tool results usually take up most of the window and are the least useful part of it.

### Four ways context fails

Drew Breunig's June 2025 taxonomy:

| Failure | Mechanism | Evidence he cites |
|---|---|---|
| **Poisoning** | A hallucination or error enters the context and keeps being referenced | Gemini 2.5's Pokémon agent, with "poisoned" goals, chased impossible objectives |
| **Distraction** | The context grows so long that the model leans on it instead of on its training | The same agent, past ~100K tokens, repeated old actions instead of planning new ones |
| **Confusion** | Irrelevant content, often extra tools, gets used anyway | A small model failed with 46 tools and succeeded with 19 |
| **Clash** | Parts of the context contradict each other | "Sharded" multi-turn prompts (Microsoft/Salesforce): 39% average drop, as early wrong attempts stayed in context |

The common cause: the model attends to everything in the window (P3) and can't tell stale, wrong or irrelevant tokens from useful ones unless you remove or label them.

### The organizing frame: write, select, compress, isolate

LangChain's July 2025 post sorts the techniques into four buckets:

```text
            ┌─ WRITE ──── save state outside the window (notes, progress files)
 context ───┼─ SELECT ─── pull in only what this step needs (JIT retrieval, tool search)
 window     ├─ COMPRESS ─ keep fewer tokens for the same information (clearing, compaction)
            └─ ISOLATE ── split work across windows (subagents, sandboxes, state fields)
```

### Write: structured note-taking and progress files

The agent writes notes outside the window and reads them back later. Anthropic calls this "structured note-taking, or agentic memory": a to-do list, a `NOTES.md`, a progress log. It works for two reasons:

- **Notes survive compression.** After a summary or reset, the notes are still on disk. In Anthropic's Pokémon example, Claude kept tallies across thousands of steps and reread its notes after context resets.
- **Notes recite the goal.** Manus agents keep rewriting a `todo.md`, which puts the plan at the end of the context, where recent tokens get the most attention.

Anthropic's long-running coding harness (Nov 2025) formalized the pattern. An initializer agent writes `claude-progress.txt`, a JSON feature list and an initial git commit, and every later session starts by reading the progress file and `git log`. The feature list is JSON because the model is "less likely to inappropriately change or overwrite JSON files compared to Markdown files." Once notes outlive the session, they become memory ([§17](17-memory.md)).

### Select: the right altitude, just in time

**System prompts at the right altitude.** Anthropic names two failure modes: brittle if-else logic hardcoded into the prompt, and vague guidance that "falsely assumes shared context". Aim between them, for specific heuristics rather than scripts, and remember that "minimal does not necessarily mean short." Start minimal on the best model, then add instructions only for failures you observe. A few canonical examples beat a "laundry list of edge cases."

**Tool selection.** Every tool definition costs tokens on every turn and adds a risk of confusion. With Anthropic's tool search tool you mark tools `defer_loading: true`, so only the search tool and your core tools load up front, and matching definitions are appended when Claude searches. In Anthropic's example, context use fell from about 77K to about 8.7K tokens (vendor-reported, Nov 2025). It no longer needs a beta header (Feb 2026).

**Just-in-time retrieval and agentic search.** Classic RAG ([§09](09-rag.md)) retrieves before inference from a pre-built index. The just-in-time alternative keeps lightweight references (paths, stored queries, URLs) and loads content with tools when needed. Claude Code loads CLAUDE.md files up front, then uses `glob` and `grep` to find files on demand, "bypassing the issues of stale indexing and complex syntax trees." File names, folders and timestamps act as free metadata. The cost is speed: exploring is slower than a lookup, and a badly guided agent wastes tokens on dead ends. For less dynamic domains such as legal or finance, Anthropic suggests a hybrid.

**Progressive disclosure.** The agent builds understanding "layer by layer": it lists a directory, reads a file's head, then opens the one section that matters. Show a short description first and load the detail only when relevant. [§18](18-skills.md) builds skills on this idea.

### Compress: tool-result clearing and compaction

**Tool-result clearing** is the lightest form of compression. Once the agent has acted on a 20K-token file read, it rarely needs the raw text again. The Claude API's context editing (`context-management-2025-06-27`, **(Preview)**) does this server-side with the `clear_tool_uses_20250919` strategy. Past a trigger (default: 100K input tokens), it replaces the oldest tool results with a placeholder and keeps the most recent few (default: 3), and you can exclude specific tools. At launch in Sep 2025, Anthropic reported a 29% gain on an internal agentic-search eval (39% with the memory tool) and 84% fewer tokens on a 100-turn web-search eval (vendor-reported). Manus adds a rule: make compression **restorable**. Drop the page content but keep the URL, so the agent can fetch it again. On the 5.5-family models (Opus 5.5, Sonnet 5.5, Haiku 5.5, Fable 5.1), clearing or shortening an earlier tool result *by hand* breaks preserved thinking: it changes the prefix of every later thinking block, and the API rejects the request with a 400 by default for accounts created on or after Aug 31, 2026 (older accounts can opt in). Server-side context editing and compaction don't count as edits, because the check compares what you sent, so on these models let the API clear or compact for you.

**Compaction** summarizes the conversation as it nears the limit and continues from the summary. Claude Code keeps "architectural decisions, unresolved bugs, and implementation details", plus the five most recently accessed files. The hard part is what to keep. Anthropic's advice is to tune the summarization prompt on real traces, for recall first and then for precision. The minimal mechanism, which summarizes old turns past a threshold and keeps recent turns verbatim:

```python
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL, SYSTEM = "claude-sonnet-5-5", "You are a data-platform assistant."  # SYSTEM never changes
THRESHOLD = 120_000  # compact once the context crosses this many tokens
KEEP = 6             # most recent messages kept word for word
ASK = ("Summarize the conversation so far for your future self. Keep decisions, open "
       "questions, names, numbers and user preferences. Drop raw tool output.")

def call(messages, max_tokens=4000):
    resp = client.messages.create(model=MODEL, max_tokens=max_tokens, system=SYSTEM,
                                  messages=messages, cache_control={"type": "ephemeral"})
    u = resp.usage  # input_tokens is only the uncached part, so add all three
    size = u.input_tokens + u.cache_creation_input_tokens + u.cache_read_input_tokens
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return text, size + u.output_tokens

def compact(messages):
    cut = len(messages) - KEEP
    while messages[cut]["role"] != "user":  # the kept tail must start on a user turn
        cut += 1
    old, recent = messages[:cut], messages[cut:]
    # Same prefix as the real conversation, so this summary call reads the cache
    summary, _ = call(old + [{"role": "user", "content": ASK}], max_tokens=2000)
    recent[0] = {"role": "user",
                 "content": f"<summary>\n{summary}\n</summary>\n\n{recent[0]['content']}"}
    return recent

def chat(messages, user_text, used):
    messages.append({"role": "user", "content": user_text})
    if used > THRESHOLD and len(messages) > KEEP:
        messages[:] = compact(messages)  # one cache miss now, cheap cache hits after
    reply, used = call(messages)
    messages.append({"role": "assistant", "content": reply})  # text only: no thinking replayed
    return reply, used
```

The API can also compact for you **(Preview)**. Threshold compaction (`compact_20260112`, default trigger 150K tokens) fires inside a normal request. On-demand compaction (`compact-2026-09-04`, Sep 2026) runs when you ask, can keep recent turns verbatim, and can run in the background. One 2026 catch: on models with preserved thinking (Opus 5.5, Sonnet 5.5, Haiku 5.5, Fable 5.1), a summary you write yourself invalidates the thinking blocks in the turns you keep, and newer accounts get a 400 for sending them. Either replay no thinking, as the snippet does, or let the API write the summary.

### Resets vs compaction, and "context anxiety"

Compaction keeps one agent going on a shorter history. A **context reset** starts a fresh agent with an empty window and a structured handoff: the progress file and next steps. Anthropic's March 2026 harness post explains why the difference mattered. Some models showed **context anxiety**: "wrapping up work prematurely as they approach what they believe is their context limit." Compaction gives no clean slate, so for Sonnet 4.5 resets became essential, despite the extra orchestration, tokens and latency. Opus 4.5 then "largely removed that behavior on its own", and the newer harness dropped resets in favor of the Agent SDK's automatic compaction. That's the bitter lesson (P12) in miniature: the workaround was deleted once the model improved.

### Isolate: subagents and sandboxes

A subagent gets a clean window and a narrow task. It may spend tens of thousands of tokens exploring but returns a distilled summary, "often 1,000-2,000 tokens", so the lead's context holds only conclusions. The price: Anthropic's multi-agent research system used about 15× the tokens of chat, and parallel agents can make conflicting implicit decisions ([§13](13-multi-agent.md)). A code sandbox also isolates: it can hold a large dataframe as a variable and return only a printed summary.

### Cache-aware layout (P10)

Prompt caching ([§05](05-api-and-prompting.md)) stores the computed state (the KV cache, [§03](03-inference.md)) for a prompt prefix, so a later request with a byte-identical prefix skips that prefill. Three rules follow from "prefix match":

1. **Order by stability.** Anthropic renders `tools`, then `system`, then `messages`. Put what never changes first and what changes each turn last. A timestamp at the top of the system prompt makes everything after it uncacheable.
2. **Keep history append-only.** Editing an earlier message, such as clearing a tool result or rewriting a summary, invalidates the cache from that point on, and on the 5.5-family models every later thinking block too (see Compress above). Curating and caching therefore pull against each other: batch your edits (context editing has a `clear_at_least` setting for this) and compact rarely. Manus calls the KV-cache hit rate "the single most important metric for a production-stage AI agent."
3. **Change instructions without editing the prefix.** On current Claude models, append a `{"role": "system"}` message to `messages` instead of editing `system` (no beta header, as of Oct 2026).

```json
{
  "model": "claude-sonnet-5-5",
  "max_tokens": 4000,
  "cache_control": {"type": "ephemeral"},
  "tools": [
    {"name": "query_warehouse", "description": "Run read-only SQL against the warehouse",
     "input_schema": {"type": "object", "properties": {"sql": {"type": "string"}},
                      "required": ["sql"]}}
  ],
  "system": [
    {"type": "text", "text": "<role, rules, tool guidance: frozen for the session>",
     "cache_control": {"type": "ephemeral"}}
  ],
  "messages": [
    {"role": "user", "content": "<turn 1>"},
    {"role": "assistant", "content": "<turn 1 reply>"},
    {"role": "user", "content": "Today is 2026-10-14. <new question>"}
  ]
}
```

The marker on the system block gives the expensive static part its own cache entry. The top-level `cache_control` adds a moving breakpoint at the end of the growing conversation. The volatile date goes in the newest turn.

Claude API caching prices (verified Oct 2026, per million tokens):

| Model | Base input | 5-min cache write (1.25×) | 1-hour cache write (2×) | Cache hit |
|---|---|---|---|---|
| Claude Sonnet 5.5 | $2.00 | $2.50 | $4.00 | $0.10 (0.05×) |
| Claude Opus 5.5 | $4.00 | $5.00 | $8.00 | $0.20 (0.05×) |
| Claude Haiku 5.5 (prompts ≤100K) | $0.10 | $0.125 | $0.20 | $0.01 (0.1×) |

The default TTL (time to live) is 5 minutes. Each hit refreshes it for free, and the clock runs from the *start* of a request, so a 4-minute generation leaves about 1 minute before the entry expires. Take a worked example on Sonnet 5.5: a 50K-token prefix sent 20 times within the TTL. Uncached, that costs 20 × 50K × $2/M = $2.00. Cached, it costs one write ($0.125) plus 19 hits ($0.095), so $0.22, about 89% less, with faster time-to-first-token too. A 5-minute entry pays off on its first hit. Choose the 1-hour TTL only when gaps between requests regularly fall between 5 and 60 minutes. OpenAI also caches prefixes: earlier models only implicitly, while GPT-5.6 and later add explicit breakpoints and charge 1.25× for cache writes. Google Gemini caches implicitly by default. Explicit cache objects with a TTL (default 1 hour) exist only for some Gemini 3 and 2.5 models on `generateContent`, not on Gemini 4 Argon onward or the Interactions API. The layout rule is the same everywhere.

### Measuring context usage

- **Per request.** Total prompt size is `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`; `input_tokens` alone is only the uncached remainder. A falling cache-read share after a code change usually means a silent invalidator: a timestamp, unsorted JSON, or a per-user tool list.
- **Before sending.** `POST /v1/messages/count_tokens` gives exact counts for that model's tokenizer.
- **Per component.** Break traces down into system, tools, history and tool results ([§27](27-observability.md)). Claude Code's `/context` command draws this as a grid.
- **Per outcome.** Track tokens per *completed task*, and run an eval ([§26](26-evals.md)) before and after each context change, rather than assuming it helps.

### Failure modes of the techniques themselves

- **Lossy or poisoned summaries.** Aggressive compaction drops details that matter later, and a hallucinated summary is poisoning that persists.
- **Hidden errors.** Manus found that leaving failed attempts in context stops the model repeating them. Keep *observed* errors (stack traces), and remove *invented* ones.
- **Exploration waste and cache thrash.** Badly guided search spends the budget it was meant to save, and frequent small edits to early context make every request a cache miss.

## Comparison

| Technique | Bucket | How it works | Strength | Weakness | When to choose |
|---|---|---|---|---|---|
| Notes, progress files | Write | Agent writes state to a file and rereads it | Survives compaction and resets | Wrong or stale notes persist | Multi-hour tasks with milestones |
| Agentic search | Select | Keep references; load with grep, glob, queries | Always fresh; no index | Slower; can wander | Codebases, file systems, databases |
| Pre-indexed RAG | Select | Embed and fetch top-k before the call | Fast; scales to huge corpora | Index goes stale; chunking splits meaning | Large, static document sets |
| Tool search | Select | Defer tool definitions until searched for | Big savings with many tools | Extra step; search can miss | Dozens of tools or MCP servers |
| Tool-result clearing | Compress | Replace old results with a placeholder | Simple; server-side; no hallucination | Cache miss when it fires | Tool-heavy loops |
| Compaction | Compress | Summarize old turns, keep recent ones | One continuous agent | Lossy; no clean slate | Long back-and-forth sessions |
| Context reset | Compress | Fresh agent plus handoff file | Clean slate; cures context anxiety | Orchestration overhead | Models showing context anxiety |
| Subagents | Isolate | Sub-tasks in clean windows return summaries | Parallel breadth; lean lead | About 15× tokens; lost shared context | Broad research, parallel reads |

## What it didn't solve

Everything here lives and dies with a session. When it ends, the window, the summaries and the cache are gone, and the next session starts from zero (P2). Progress files point toward a fix but raise new questions. Who decides what is worth keeping? How does the agent find the right note among thousands next month? What happens when a saved "fact" goes stale, or was planted by a malicious web page?

→ Next: [§17 Agent Memory](17-memory.md)

## Check your understanding

**Q: Why doesn't a 1M-token context window make context engineering unnecessary?**

Attention spreads thinner as the window fills (P3), and Chroma saw accuracy fall with length on all 18 models it tested, even on simple tasks. Each turn also re-sends the whole window, so an agent's total input grows roughly with the square of its step count (P10). A big window gives you room; it doesn't make filling the room free or harmless. It's still the right tool when one task truly needs a large document read in full.

**Q: What would happen if you put the current timestamp at the top of an agent's system prompt?**

Caching matches prefixes byte for byte, and a value that changes every request near the front invalidates everything after it. Every turn then pays full price and full prefill latency for the whole history, plus a write premium if markers are set. Move the date into the newest user turn or a mid-conversation system message, after the cached history.

**Q: Compaction vs a context reset: when would you choose a reset?**

Compaction summarizes old turns so the same agent continues. A reset starts a new agent with an empty window and a handoff file. That clean slate fixed "context anxiety" in models like Sonnet 4.5, but it costs orchestration code, tokens and latency, and the handoff must carry everything that matters. Prefer compaction on models without the anxiety, as Anthropic did once Opus 4.5 arrived.

**Q: Why is tool-result clearing the lightest form of compaction, and what does it cost?**

Once the model has acted on a large tool result, the raw text rarely matters again, and a placeholder can't hallucinate the way a summary can. But each clearing edits earlier context and breaks the cache from that point, so batch clearings instead of trimming every turn. On the 5.5-family models, let the API's context editing do it: clearing by hand also invalidates every later thinking block. Keep the path or URL so it's restorable, and exclude results the agent still depends on, such as the spec it's implementing.

**Q: Just-in-time agentic search vs pre-indexed RAG: when does each win?**

Agentic search loads content with tools such as grep at the moment of need, so nothing goes stale and the folder structure acts as free metadata. Each lookup costs tool calls, though, and the agent can wander. RAG answers in one fast lookup and scales to millions of documents, but the index must be kept current. Use agentic search for codebases and live systems and RAG for large, slow-changing corpora; hybrids are common.

**Q: What would happen if a subagent returned its whole exploration transcript instead of a summary?**

A subagent exists to burn tokens exploring in its own window so the lead doesn't have to. Returning the transcript moves all that noise into the lead's context, which brings back distraction and confusion and multiplies cost. The lead should get a condensed result, often 1-2K tokens, with references to details it can fetch.

**Q: Why might cleaning errors out of an agent's context make it worse, and how does that square with context poisoning?**

A failed command and its stack trace shift the model away from repeating that action, and Manus found that keeping wrong turns improves recovery. Poisoning is a *false belief*, a hallucinated fact or goal that the model keeps treating as true. Keep observed evidence of failure, and correct invented content, especially in summaries and notes that will persist.

## Takeaways

- Context engineering means choosing, every turn, the smallest set of high-signal tokens for the next step (P2, P3).
- Context rots gradually rather than at a hard limit: accuracy fell with length on every model Chroma tested.
- The four failures are poisoning, distraction, confusion and clash; the four strategies are write, select, compress and isolate.
- Notes survive compaction; tool-result clearing is the cheapest compression; compaction is lossy, so tune it for recall first.
- Resets beat compaction only for models with context anxiety, and better models removed the need (P12).
- Put stable content first and volatile content last, and keep history append-only; a Sonnet 5.5 cache hit costs 5% of base input.
- Curating and caching pull against each other, so batch edits and measure total prompt tokens and tokens per completed task.

## Sources

- Anthropic, "Effective context engineering for AI agents" (Sep 29, 2025): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic, "Managing context on the Claude Developer Platform" (Sep 29, 2025): https://www.anthropic.com/news/context-management
- Anthropic, "Effective harnesses for long-running agents" (Nov 26, 2025): https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic, "Harness design for long-running application development" (Mar 24, 2026): https://www.anthropic.com/engineering/harness-design-long-running-apps
- Anthropic, "Introducing advanced tool use" (Nov 24, 2025): https://www.anthropic.com/engineering/advanced-tool-use
- Anthropic, "How we built our multi-agent research system" (Jun 13, 2025): https://www.anthropic.com/engineering/multi-agent-research-system
- Claude docs, Context editing: https://platform.claude.com/docs/en/build-with-claude/context-editing
- Claude docs, Compaction overview: https://platform.claude.com/docs/en/build-with-claude/compaction
- Claude docs, Preserved thinking: https://platform.claude.com/docs/en/build-with-claude/preserved-thinking
- Claude docs, Prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Claude docs, Pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Claude docs, Release notes: https://platform.claude.com/docs/en/release-notes/overview
- Claude Code docs, Commands: https://code.claude.com/docs/en/commands
- LangChain, "Context Engineering" (Jul 2, 2025): https://blog.langchain.com/context-engineering-for-agents/
- Hong, Troynikov & Huber, "Context Rot" (Chroma, Jul 2025): https://research.trychroma.com/context-rot
- Drew Breunig, "How Long Contexts Fail" (Jun 22, 2025): https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html
- Simon Willison, "Context engineering" (Jun 27, 2025): https://simonwillison.net/2025/Jun/27/context-engineering/
- HumanLayer, "12-factor agents", Factor 3: https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-03-own-your-context-window.md
- Yichao "Peak" Ji, "Context Engineering for AI Agents: Lessons from Building Manus" (Jul 18, 2025): https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- Liu et al., "Lost in the Middle" (2023): https://arxiv.org/abs/2307.03172
- Laban et al., "LLMs Get Lost In Multi-Turn Conversation" (May 2025): https://arxiv.org/abs/2505.06120
- Cognition, "Don't Build Multi-Agents" (Jun 2025): https://cognition.ai/blog/dont-build-multi-agents
- OpenAI, Prompt caching guide: https://developers.openai.com/api/docs/guides/prompt-caching
- Google, Gemini API context caching (implicit) and explicit caching: https://ai.google.dev/gemini-api/docs/caching ; https://ai.google.dev/gemini-api/docs/generate-content/caching
