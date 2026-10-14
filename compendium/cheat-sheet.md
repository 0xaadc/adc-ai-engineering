# Cheat Sheet

> As of October 2026. This is the compendium on a few pages. Each line points to the section that explains it. If a line doesn't make sense, read the section; don't memorize the line.

## 1. The twelve principles ([§01](01-first-principles.md))

| ID | Principle | In one line |
|---|---|---|
| P1 | Next-token function | Chat, JSON, tool calls, and thinking are all tokens in one sequence |
| P2 | Stateless; context is the only memory | Every call starts from zero, so resend history and keep state outside the model |
| P3 | Finite attention budget that rots | More tokens cost more and dilute attention, so curate and don't stuff |
| P4 | Sampled, so probabilistic | Correctness is a rate, so evals are the tests |
| P5 | Weights vs. runtime knowledge | Ground for facts; fine-tune for behavior |
| P6 | Model proposes, code disposes | The harness executes, so capability and risk live there |
| P7 | Control flow is the autonomy dial | Code decides in a workflow; the model decides in an agent |
| P8 | Errors compound | pⁿ collapses, so verify and keep the checker separate from the maker |
| P9 | One channel for instructions and data | Injection can't be prompted away, so use least privilege |
| P10 | Tokens cost compute and time | Prefill, decode, caching, and thinking are dials |
| P11 | N×M → N+M | MCP, A2A, Agent Skills, AGENTS.md, OTel |
| P12 | Scaffolding gets deleted | Keep it thin, and re-check it with evals when models change |

**Five forces** behind every technique: **knowledge** (P5), **uncertainty** (P4, P8), **agency** (P6, P7, P9), **scarcity** (P1, P3, P10), **change** (P11, P12).

**Five questions for anything new:**
1. Which force does it address?
2. Which mechanism does it use?
3. What does it cost?
4. How is it verified?
5. What happens when models improve?

## 2. The chain of problems ([§01](01-first-principles.md), [Timeline](timeline.md))

Each step exists because the one before it left a problem open:

prompting → **structured output** (code can't parse prose) → **multimodal** (the world isn't only text) → **embeddings and search** (find *your* data) → **RAG** (answer from it) → **tools** (act, not just read) → **agents** (many steps) → **patterns** (a loop isn't a design) → **multi-agent** (parallelism, isolation) → **graphs** (explicit, durable control flow) → **protocols** (stop writing N×M glue) → **context engineering** (the context floods and rots) → **memory** (persist across sessions) → **skills** (know-how on demand) → **harness engineering** (assemble and tune it all) → **runtime** (run safely and durably) → **loop engineering** (stop being the human bottleneck).

## 3. The disciplines ([§38](38-disciplines-map.md))

```text
prompt engineering ⊂ context engineering ⊂ harness engineering ⊂ loop engineering
(the words)          (all the model sees)  (all but the model)    (what prompts the system)
graph engineering   = explicit control flow, a side branch (≠ GraphRAG)
agentic engineering = the whole stack applied to building software
```

| Label | Origin | Status |
|---|---|---|
| Prompt engineering | 2020 (GPT-3) | Established; now a subset |
| Context engineering | Apr–Jun 2025 | Established |
| Harness engineering | Nov 2025 → Feb 2026 | Established |
| Loop engineering | Jul 2025 practice; Jun 2026 label | Emerging |
| Graph engineering | 2024 practice; Jul 2026 label | Niche label, established practice |
| Agentic engineering | Feb 2026 | Established |
| Spec-driven / compound / eval-driven | 2024–2025 | Buzzword / moderate / contested |

**Four tests for a real discipline:** a distinct bottleneck, its own artifacts, its own failure modes, and teachable without naming a product.

## 4. Mechanisms in a few lines each

**Generation ([§02](02-how-llms-work.md)):** tokenize → embed → attention layers → logits → sample a token → append → repeat. Hallucination is fluent continuation with no grounding (P1, P5).

**Inference ([§03](03-inference.md)):** *prefill* reads the input in parallel and is compute-bound. *Decode* writes one token at a time and is memory-bandwidth-bound. The **KV cache** stores the processed prefix, which is why output tokens cost more, long contexts cost more, and prompt caching works.

**Reasoning models ([§04](04-reasoning-models.md)):** these models are trained with RL on verifiable rewards to "think" before answering. You buy accuracy with thinking tokens, set through effort or budget controls.

**The API ([§05](05-api-and-prompting.md)):** `POST /v1/messages` with `model`, `max_tokens`, `system`, and `messages`. It's stateless, so you resend the whole history each turn. Read `stop_reason` and `usage`.

**Tool round trip ([§10](10-tool-use.md)):**

```text
you: tools=[{name, description, input_schema}] + messages
model: stop_reason="tool_use", content=[{type:"tool_use", id, name, input}]
you:   run it yourself (validate, authorize, execute)  ← P6
you:   messages += [{role:"user", content:[{type:"tool_result", tool_use_id, content, is_error}]}]
model: continues... until stop_reason="end_turn"
```

**The agent loop ([§11](11-agents.md)):** `while stop_reason == "tool_use": execute tools, append results, call again`, with caps on turns, tokens, and cost. `end_turn` is a *claim* that the work is done, not proof.

**RAG ([§09](09-rag.md)):** parse → chunk → embed → index, then rewrite → retrieve (hybrid search) → rerank → assemble → generate with citations. *Agentic RAG* lets the model decide when and what to retrieve.

**Context engineering ([§16](16-context-engineering.md)):** **write** (notes, progress files), **select** (just-in-time retrieval), **compress** (compaction, clearing tool results), **isolate** (subagents). Put the stable prefix first and the volatile content last so caching works.

**Skills ([§18](18-skills.md)):** a folder with `SKILL.md` (frontmatter `name` and `description`). Progressive disclosure: (1) only name and description are loaded, (2) the body loads when the description matches, (3) files load or run only when referenced.

**Harness ([§19](19-harness-engineering.md)):** Agent = Model + Harness. The harness is the system prompt, tools/skills/MCP, filesystem/sandbox/browser, subagents and routing, and hooks/middleware. Its controls are **guides** (feedforward) and **sensors** (feedback), each either computational or inferential. **The ratchet:** every mistake becomes a permanent fix.

**Runtime ([§20](20-agent-runtime.md)):** a sandbox (isolated filesystem, network, and processes), durable execution (a step journal plus replay), idempotent tools, and human-in-the-loop as an interrupt that waits.

**Loop ([§21](21-loop-engineering.md)):** `while :; do cat PROMPT.md | agent; done`. Each pass starts with a fresh context and keeps state on disk, and back pressure (tests, types, linters) pushes errors back into the loop. A separate model checks the goal, and spend caps bound the run.

**Build one ([§22](22-build-a-harness.md)):** `compendium/code/mini_harness.py` puts every layer above into one runnable, stdlib-only file.

## 5. Numbers worth knowing (as of Oct 2026; check before quoting)

| What | Number | Section |
|---|---|---|
| Compounding: 0.95²⁰ / 0.99²⁰ | ≈ 36% / ≈ 82% | [§11](11-agents.md) |
| Agent transcript cost growth | ~n²/2 resent input tokens over n turns | [§11](11-agents.md) |
| Agents vs. chat tokens | ~4×; multi-agent research ~15× (Anthropic) | [§13](13-multi-agent.md), [§30](30-cost-latency-reliability.md) |
| Multi-agent effect (Google study) | +81% on parallelizable tasks, −70% on sequential ones | [§13](13-multi-agent.md) |
| Prompt cache (Anthropic) | write 1.25× (5 min) or 2× (1 h); read 0.1× (0.05× on Opus/Sonnet 5.5) | [§30](30-cost-latency-reliability.md) |
| Batch APIs | ~50% off; results within 24 h | [§30](30-cost-latency-reliability.md) |
| Image tokens (Anthropic) | ⌈w/28⌉ × ⌈h/28⌉ | [§07](07-multimodal.md) |
| Human gap between conversation turns | ~200 ms; voice agents target well under 1 s | [§25](25-voice-agents.md) |
| Harness-only gain (LangChain, Terminal Bench 2.0) | 52.8% → 66.5% | [§19](19-harness-engineering.md) |
| Skills with critical issues (Snyk, Feb 2026) | 13.4% of 3,984 scanned | [§18](18-skills.md) |

## 6. Decision cues ([§37](37-why-x-over-y.md))

| If you see… | Lean toward… |
|---|---|
| Facts that change or differ per user | RAG or tools, not fine-tuning |
| A small, stable corpus | Long context plus caching |
| IDs or codes in queries | Hybrid search |
| "Themes across everything" | GraphRAG or map-reduce summaries |
| Steps you can write down in advance | A workflow |
| Steps that depend on what you find | An agent loop with caps |
| Breadth-first research | An orchestrator plus read-only subagents |
| Tightly coupled edits (coding) | One agent |
| Approvals, compliance, SLAs | An explicit graph |
| Tool definitions over ~10K tokens | Tool search |
| The same tools for many hosts | MCP |
| Long procedures | Skills |
| Short rules for every task | System prompt or AGENTS.md |
| A model that rushes as context fills | A context reset with a handoff file |
| Output that code will parse | Strict structured outputs |
| A property a program can check | A code grader, not an LLM judge |
| An app that has an API | The API, not computer use |
| Irreversible actions | Human approval for that action |

## 7. Security in six lines ([§32](32-security-guardrails.md), [§33](33-agent-identity.md))

1. Any text in context can act as an instruction (P9). Prompts can't fix this.
2. The **lethal trifecta** is private data + untrusted content + external communication. Break one leg.
3. Use least-privilege tools, sandboxes, egress controls, and approval for consequential actions.
4. Never render or execute model output unsanitized. Markdown images can exfiltrate data.
5. Treat MCP servers and skills as supply chain: review them like dependencies.
6. Agents act *on behalf of* someone, so use scoped, short-lived tokens the model never sees, with no token passthrough.

## 8. Current facts that changed recently (Oct 2026)

- Current Claude models reject non-default `temperature`, `top_p`, and `top_k`. Prefill is gone, and forced `tool_choice` returns 400 on the 5.5 family. Use effort settings, structured outputs, and evals instead ([§05](05-api-and-prompting.md)).
- Anthropic structured outputs went GA on Jan 29, 2026, through `output_config.format` ([§06](06-structured-outputs.md)).
- MCP 2026-07-28 has a stateless core, an extensions framework, and Multi Round-Trip Requests, and it deprecates Dynamic Client Registration. MCP Apps has been an extension since Jan 2026. The Python SDK v2 class is `MCPServer`, formerly `FastMCP` ([§15](15-protocols-mcp-a2a.md)).
- MCP and A2A are now governed by the Agentic AI Foundation (Linux Foundation). A2A v1.0 methods are `SendMessage` and `GetTask` ([§15](15-protocols-mcp-a2a.md)).
- The OpenTelemetry GenAI conventions moved to their own repo in Jun 2026 and are still in Development status ([§27](27-observability.md)).
- OpenAI is winding down self-serve fine-tuning, which closes to new jobs on Jan 6, 2027 ([§29](29-adapting-models.md)).
- The OWASP Agentic Top 10 (ASI01–ASI10) came out Dec 2025, and the OWASP LLM Top 10 2026 edition on Aug 3, 2026 ([§32](32-security-guardrails.md)).
- The EU AI Act Omnibus is Regulation (EU) 2026/1744: high-risk obligations now apply from Dec 2, 2027 for standalone systems and Aug 2, 2028 for embedded ones ([§34](34-governance-regulation.md)).

## 9. Ecosystem map (examples, not endorsements)

| Layer | Examples (Oct 2026) | Section |
|---|---|---|
| Frontier models (API) | Anthropic Claude, OpenAI GPT, Google Gemini | [§02](02-how-llms-work.md), [§04](04-reasoning-models.md) |
| Open-weight models | Llama, Qwen, DeepSeek, Mistral, Gemma, gpt-oss | [§31](31-open-weights-self-hosting.md) |
| Serving engines | vLLM, SGLang, llama.cpp / Ollama | [§31](31-open-weights-self-hosting.md) |
| Retrieval | pgvector, dedicated vector databases, lakehouse search (e.g. Databricks AI Search) | [§08](08-embeddings-and-search.md) |
| Agent SDKs and frameworks | Claude Agent SDK, OpenAI Agents SDK, Google ADK, LangGraph, Microsoft Agent Framework, Pydantic AI, CrewAI, smolagents, Mastra, DSPy | [§13](13-multi-agent.md), [§14](14-graph-engineering.md) |
| Agent harnesses (products) | Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot agent | [§19](19-harness-engineering.md), [§23](23-coding-agents.md) |
| Standards | MCP, A2A, Agent Skills, AGENTS.md, OTel GenAI conventions | [§15](15-protocols-mcp-a2a.md), [§18](18-skills.md), [§27](27-observability.md) |
| Durable runtimes | Temporal, Restate, Inngest, DBOS, LangGraph checkpointers | [§20](20-agent-runtime.md) |
| Observability and evals | LangSmith, Langfuse, Arize Phoenix, Braintrust, Datadog | [§26](26-evals.md), [§27](27-observability.md) |
| Gateways | LiteLLM, OpenRouter, cloud AI gateways | [§30](30-cost-latency-reliability.md) |

## 10. Failure modes to recognize on sight

- **Confident fabrication.** The model is fluent with no grounding (P1, P5). Fix it with RAG, citations, or tools.
- **Context rot.** The agent gets worse as the run gets longer (P3). Fix it with compaction, resets, or subagents.
- **Premature "done".** `end_turn` was a claim, not proof (P8). Fix it with a separate checker or tests.
- **Reward hacking.** Tests get weakened until they pass. Fix it by guarding test files and keeping the checker separate from the maker.
- **Prompt injection.** Fix it with least privilege and by breaking the trifecta (P9).
- **Cost blowup.** Quadratic resends, multi-agent token use, or retries (P10). Fix it with caching, caps, and routing.
- **Scaffolding rot.** Workarounds hurt a newer model (P12). Fix it by re-running evals and deleting what no longer helps.
- **"It worked when I tried it."** A sample size of one (P4). Fix it with an eval.
