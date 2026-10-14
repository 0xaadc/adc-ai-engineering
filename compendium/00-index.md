# AI Engineering Compendium: Index

This is a principles-first compendium of **AI engineering**, the discipline of building reliable software on top of foundation models. It starts with what happens inside an LLM. It then follows the field's evolution as a chain of problems: prompting, grounding, tools, agents, design patterns, multi-agent systems and graphs, protocols, context engineering, memory, skills, harnesses, runtimes, and loops. It ends with how to measure, run, secure, and ship the result.

It is written for engineers who know software or data systems but have never built with LLMs or looked under the hood.

**How to use it:** read [§01 First Principles](01-first-principles.md) first. It defines twelve principles (P1–P12), and every other section works out its facts from them. When a section writes "(P8)", it means "this follows from errors compounding across steps." If you understand *why* something works, you rarely need to memorize *what* it is.

> As of October 2026. AI tooling changes monthly. Status tags: **(GA)** generally available, **(Preview)** beta/preview, **(⚠ verify)** not confirmed against primary sources. Check the vendor docs before relying on a limit, price, or parameter name.

## The principles at a glance

| ID | Principle | One-line mechanism |
|---|---|---|
| P1 | An LLM is a next-token probability function | Chat, JSON, tool calls, and "thinking" are all just tokens in one sequence |
| P2 | The model is stateless; context is its only working memory | Every call starts from zero, so durable state lives outside the model |
| P3 | Context is a finite attention budget, and it rots | More tokens cost more and dilute attention, so curate rather than stuff |
| P4 | Output is sampled, so behavior is probabilistic | Correctness is a rate, so evals are the tests |
| P5 | Knowledge lives in the weights or arrives at runtime | Ground for facts; fine-tune for behavior |
| P6 | The model proposes; code disposes | The model emits requests, and the harness executes them |
| P7 | Who owns control flow is the autonomy dial | Code decides in a workflow; the model decides in an agent |
| P8 | Errors compound; verification is the bottleneck | p^n collapses, so separate the checker from the maker |
| P9 | Instructions and data share one channel | Prompt injection can't be prompted away, so use least privilege |
| P10 | Every token costs compute and time | Prefill, decode, caching, and thinking are cost dials |
| P11 | Standard interfaces turn N×M into N+M | MCP, A2A, Agent Skills, OTel |
| P12 | The bitter lesson: scaffolding gets deleted | Build thin scaffolding that improves along with the model |

## Contents

★ = the core sections, the ones to read if you read nothing else

| # | Section | What it answers |
|---|---|---|
| **Part 1: The model (2017–2024)** | | |
| 01 | [First Principles](01-first-principles.md) ★ | Why AI engineering exists; the twelve principles; the chain of problems |
| 02 | [How an LLM Works](02-how-llms-work.md) ★ | Tokens, attention, pretraining, post-training, sampling, and why models hallucinate |
| 03 | [Inference Under the Hood](03-inference.md) | Prefill vs. decode, KV cache, batching, quantization; why pricing and latency look the way they do |
| 04 | [Reasoning Models and Test-Time Compute](04-reasoning-models.md) | How "thinking" models work, and when to pay for them |
| **Part 2: Talking to the model, the prompt engineering era (2020–2023)** | | |
| 05 | [The API and Prompt Engineering](05-api-and-prompting.md) ★ | The raw API call, statelessness, and why prompting techniques work |
| 06 | [Structured Outputs and Constrained Decoding](06-structured-outputs.md) | Making output that code can parse, guaranteed |
| 07 | [Multimodal Models and Documents](07-multimodal.md) | Images, PDFs, audio; document AI |
| **Part 3: Grounding (2020–2024)** | | |
| 08 | [Embeddings and Search](08-embeddings-and-search.md) | Meaning as geometry; vector, lexical, and hybrid search; reranking |
| 09 | [Retrieval-Augmented Generation (RAG)](09-rag.md) ★ | Grounding answers in your data; agentic RAG; GraphRAG |
| **Part 4: Acting and architecting agents (2022–2025)** | | |
| 10 | [Tool Use and Tool Design](10-tool-use.md) ★ | How a model "calls" a tool, and how to design tools for agents |
| 11 | [Agents and the Agent Loop](11-agents.md) ★ | The loop, workflows vs. agents, compounding error |
| 12 | [Agentic Design Patterns](12-agentic-design-patterns.md) ★ | The canonical pattern catalogs, merged into one taxonomy |
| 13 | [Multi-Agent Systems](13-multi-agent.md) | Topologies, when multiple agents help, and when they hurt |
| 14 | [Graph Engineering](14-graph-engineering.md) | Orchestration as state machines; checkpoints, interrupts, durable control flow |
| 15 | [Protocols: MCP and A2A](15-protocols-mcp-a2a.md) ★ | Standard connections from agent to tool and from agent to agent |
| **Part 5: The context and harness era (2025–2026)** | | |
| 16 | [Context Engineering](16-context-engineering.md) ★ | Curating what the model sees: context rot, compaction, isolation |
| 17 | [Agent Memory](17-memory.md) | Persistence across sessions; memory types and systems |
| 18 | [Agent Skills](18-skills.md) ★ | Procedural know-how, loaded only when needed |
| 19 | [Harness Engineering](19-harness-engineering.md) ★ | Agent = Model + Harness; guides, sensors, the ratchet |
| 20 | [Agent Runtime](20-agent-runtime.md) | Sandboxes, durable execution, long-running and background agents |
| 21 | [Loop Engineering](21-loop-engineering.md) ★ | Designing the systems that prompt the agents |
| 22 | [Build a Harness from Scratch](22-build-a-harness.md) ★ | The capstone: every layer, built in code |
| **Part 6: Agent archetypes (2025–2026)** | | |
| 23 | [Coding Agents and Agentic Engineering](23-coding-agents.md) | How coding agents work; spec-driven and compound engineering |
| 24 | [Computer-Use, Browser, and Deep-Research Agents](24-computer-use-and-research-agents.md) | Agents that use screens, browsers, and the open web |
| 25 | [Voice and Realtime Agents](25-voice-agents.md) | Latency budgets, turn-taking, speech-to-speech |
| **Part 7: Measure and improve** | | |
| 26 | [Evals](26-evals.md) ★ | Error analysis, graders, LLM-as-judge, agent evals |
| 27 | [Observability and Tracing](27-observability.md) | Traces, spans, OTel GenAI conventions, online evals |
| 28 | [Data Flywheels and Synthetic Data](28-data-flywheels.md) | Turning production traces into datasets |
| 29 | [Adapting Models](29-adapting-models.md) | Prompt optimization, fine-tuning, distillation, RL environments, and when not to |
| **Part 8: Production and trust** | | |
| 30 | [Cost, Latency, and Reliability](30-cost-latency-reliability.md) | Caching, batching, routing, gateways, fallbacks |
| 31 | [Open-Weight Models and Self-Hosting](31-open-weights-self-hosting.md) | vLLM, quantization, and when self-hosting pays off |
| 32 | [Security and Guardrails](32-security-guardrails.md) ★ | Prompt injection, the lethal trifecta, OWASP Agentic Top 10, red teaming |
| 33 | [Agent Identity and Authorization](33-agent-identity.md) | OAuth for agents, delegated identity, MCP authorization |
| 34 | [Governance and Regulation](34-governance-regulation.md) | The EU AI Act timeline; logging, disclosure, oversight |
| **Part 9: Product and synthesis** | | |
| 35 | [AI UX and Generative UI](35-ai-ux.md) | Streaming, human-in-the-loop UX, MCP Apps, feedback capture |
| 36 | [AI Product Thinking](36-product-thinking.md) | Choosing use cases, build vs. buy, ROI |
| 37 | [Why X over Y](37-why-x-over-y.md) ★ | The cross-cutting decision bank, argued both ways |
| 38 | [The Disciplines and Skills Map](38-disciplines-map.md) ★ | Every "X engineering" label: origin, status, how they nest; the AI engineer's skills |
| **Review** | | |
| — | [Timeline](timeline.md) | Both threads on one page, 2017 → 2026 |
| — | [Glossary](glossary.md) | Every term, defined once |
| — | [Cheat Sheet](cheat-sheet.md) | One page: principles, the chain, the disciplines, the ecosystem map |
| — | [Question Bank](question-bank.md) | Every "Check your understanding" question, with answers hidden |
| — | [Frontier Watchlist](frontier.md) | What's emerging and not yet settled |

## Reading paths

**The full read (about 15 hours).** Go in order. Parts 1–6 form one chain of problems, and Parts 7–9 apply to all of it.

**Under the hood in 2 hours.** §02 How an LLM works → §03 Inference → §05 The API → §10 Tool use → §11 The agent loop → §22 Build a harness. This is the shortest path from "never looked inside" to "could build one."

**The disciplines (about 2 hours).** §05 Prompt engineering → §16 Context engineering → §19 Harness engineering → §21 Loop engineering → §14 Graph engineering → §38 The disciplines map.

**Just the evolution (about 45 minutes).** The [Timeline](timeline.md), then the "Where this fits" and "What it didn't solve" sections of §02–§22, in order.

**Building agents (about 4 hours).** §10 → §11 → §12 → §13 → §16 → §19 → §20 → §26 → §32.

**Before an architecture decision (about 1 hour).** §01 (the five questions) → §37 Why X over Y → the Comparison tables of the sections involved.

## Section template

Every section follows the same structure, so you can skim them the same way:

1. **Where this fits:** the era, and the problem the previous step left unsolved
2. **Why this exists:** the problem that forced it into being, from first principles
3. **How it works (under the hood):** the mechanism, step by step, with small code snippets you can run
4. **Comparison:** tables of options and tradeoffs
5. **What it didn't solve:** what's still missing, which leads to the next section
6. **Check your understanding:** questions with model answers, also collected in the [Question Bank](question-bank.md)
7. **Takeaways:** one-line summaries
8. **Sources:** primary documentation, papers, and original engineering posts
