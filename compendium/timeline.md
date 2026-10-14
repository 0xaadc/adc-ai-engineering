# Timeline: Two Threads, 2017 → 2026

> As of October 2026. Tags: **(⚠ verify)** marks a date not confirmed against a primary source. Each entry links to the section that explains it.

The field moves along two threads at once:

- **The model thread:** what the model can do on its own.
- **The system thread:** what engineers build around the model.

Each system step exists because the step before it left a problem unsolved, and those steps are the chain that [§01](01-first-principles.md) maps out. Read the right-hand column of the table below top to bottom and you have the whole story in miniature.

## The model thread

| When | Milestone | Why it mattered | Section |
|---|---|---|---|
| Jun 2017 | "Attention Is All You Need" introduces the transformer | Self-attention lets every token relate to every other token, and it parallelizes on GPUs | [§02](02-how-llms-work.md) |
| 2018–2019 | GPT-1/GPT-2, BERT | Pretraining on raw text, then adapting the model, works | [§02](02-how-llms-work.md) |
| Jan 2020 | Scaling laws (Kaplan et al.) | Loss falls predictably as you scale parameters, data, and compute | [§02](02-how-llms-work.md) |
| May 2020 | GPT-3 | Few-shot prompting: tasks taught through examples in the prompt, with no training | [§05](05-api-and-prompting.md) |
| Mar 2022 | InstructGPT (RLHF); Chinchilla | Instruction-following from human feedback; compute-optimal training | [§02](02-how-llms-work.md) |
| Nov 2022 | ChatGPT | Chat models reach the public; the API boom begins | [§05](05-api-and-prompting.md) |
| Mar 2023 | GPT-4; vision input soon after | Much stronger reasoning; multimodal input | [§07](07-multimodal.md) |
| May 2023 | DPO | Preference tuning without a separate reward model | [§02](02-how-llms-work.md) |
| 2023–2024 | Long context (100K → 1M tokens) | Whole documents fit in context, but quality degrades (context rot) | [§16](16-context-engineering.md) |
| Sep 2024 | OpenAI o1 | Models trained with RL to think before answering (test-time compute) | [§04](04-reasoning-models.md) |
| Jan 2025 | DeepSeek-R1 | Open reasoning model; RL with verifiable rewards | [§04](04-reasoning-models.md) |
| 2025–2026 | Models post-trained inside agent harnesses | Model and harness co-evolve (P12) | [§19](19-harness-engineering.md) |

## The system thread

| When | Milestone | Problem it solved | Section |
|---|---|---|---|
| 2020 | GPT-3 API; prompt engineering | Programming a model with text | [§05](05-api-and-prompting.md) |
| May 2020 | RAG paper (Lewis et al.) | Grounding generation in retrieved documents | [§09](09-rag.md) |
| Jan 2022 | Chain-of-thought prompting | Better multi-step answers from "think step by step" | [§05](05-api-and-prompting.md) |
| Sep 2022 | "Prompt injection" named (Willison) | Naming the core security flaw | [§32](32-security-guardrails.md) |
| Oct 2022 | ReAct | Interleaving reasoning with actions, the seed of the agent loop | [§10](10-tool-use.md) |
| Feb 2023 | Toolformer | Models that learn to call APIs | [§10](10-tool-use.md) |
| Mar–Apr 2023 | AutoGPT, BabyAGI | Autonomous-agent hype, unreliable in practice | [§11](11-agents.md) |
| 2023 | Vector database boom; RAG goes mainstream | Searching private data by meaning | [§08](08-embeddings-and-search.md) |
| Jun 2023 | Function calling (OpenAI) | Structured tool requests the harness can execute | [§10](10-tool-use.md) |
| Jun 2023 | "The Rise of the AI Engineer" (swyx) | Naming the discipline | [§01](01-first-principles.md) |
| Sep–Oct 2023 | CoALA; MemGPT | A vocabulary and architecture for agent memory | [§17](17-memory.md) |
| Nov 2023 | JSON mode (OpenAI DevDay) | Machine-readable output, without a guarantee yet | [§06](06-structured-outputs.md) |
| Jan 2024 | AlphaCodium ("flow engineering") | Multi-stage, test-driven flows beat single prompts | [§38](38-disciplines-map.md) |
| Jan 2024 | LangGraph | Agent workflows as stateful graphs | [§14](14-graph-engineering.md) |
| Mar 2024 | Ng's four agentic patterns | A first common vocabulary for agent patterns | [§12](12-agentic-design-patterns.md) |
| Apr 2024 | GraphRAG (Microsoft) | Whole-corpus questions answered over knowledge graphs | [§09](09-rag.md) |
| Aug 2024 | Strict structured outputs (OpenAI; Anthropic followed with a beta in Nov 2025, GA Jan 2026) | Schema-guaranteed output through constrained decoding | [§06](06-structured-outputs.md) |
| Sep 2024 | Contextual retrieval (Anthropic) | Chunks that keep their surrounding context | [§09](09-rag.md) |
| Oct 2024 | Computer use (Anthropic) | Agents that operate screens | [§24](24-computer-use-and-research-agents.md) |
| Nov 2024 | Model Context Protocol (MCP) | One standard for agent↔tool connections (P11) | [§15](15-protocols-mcp-a2a.md) |
| Dec 2024 | "Building effective agents" (Anthropic) | Workflows vs. agents; the pattern catalog | [§12](12-agentic-design-patterns.md) |
| Feb 2025 | "Vibe coding" (Karpathy) | Name for coding by prompting without reading the code | [§23](23-coding-agents.md) |
| Mar 2025 | OpenAI Agents SDK | Agents, handoffs, guardrails as primitives | [§13](13-multi-agent.md) |
| Apr 2025 | A2A protocol (Google); "12-factor agents" | Agent↔agent interoperability; context ownership as a principle | [§15](15-protocols-mcp-a2a.md), [§16](16-context-engineering.md) |
| Jun 2025 | "Context engineering" (Lütke, Karpathy); Anthropic multi-agent research system; Cognition, "Don't build multi-agents"; the lethal trifecta | Curating context; multi-agent evidence, for and against; a security model for agents | [§16](16-context-engineering.md), [§13](13-multi-agent.md), [§32](32-security-guardrails.md) |
| Jul 2025 | "Context Rot" (Chroma); Ralph Wiggum loop (Huntley) | Measured degradation of long contexts; a bash loop that keeps re-prompting an agent | [§16](16-context-engineering.md), [§21](21-loop-engineering.md) |
| Aug 2025 | "Compounding engineering" (Every; later "compound engineering") | Every lesson gets fed back into the system | [§23](23-coding-agents.md) |
| Sep 2025 | "Effective context engineering for AI agents" (Anthropic) | Compaction, note-taking, sub-agents, just-in-time retrieval | [§16](16-context-engineering.md) |
| Oct 2025 | Agent Skills (Anthropic); spec-driven development analyzed | Procedural know-how loaded on demand; specs as the source of truth | [§18](18-skills.md), [§23](23-coding-agents.md) |
| Nov 2025 | "Effective harnesses for long-running agents" (Anthropic) | Initializer agents, progress files, multi-session work | [§19](19-harness-engineering.md) |
| Dec 2025 | Agent Skills open standard; MCP moves under the Agentic AI Foundation; OWASP Agentic Top 10 | Cross-vendor skills; neutral protocol governance; a shared risk list | [§18](18-skills.md), [§15](15-protocols-mcp-a2a.md), [§32](32-security-guardrails.md) |
| Jan 2026 | MCP Apps goes live as an official MCP extension | Tools that return interactive UIs | [§15](15-protocols-mcp-a2a.md) |
| Feb 2026 | "Harness engineering" named (Hashimoto Feb 5; OpenAI Feb 11; coinage also credited to Trivedy); "agentic engineering" (Karpathy; Willison's patterns guide) | The harness becomes a discipline of its own | [§19](19-harness-engineering.md), [§23](23-coding-agents.md) |
| Mar 2026 | "Agent = Model + Harness" (LangChain); planner–generator–evaluator harness (Anthropic) | Anatomy of a harness; keeping the maker separate from the checker | [§19](19-harness-engineering.md) |
| Apr 2026 | Böckeler's guides and sensors; Managed Agents (Anthropic); Cognition's "what's actually working" | Harness theory; separating session, harness, and sandbox; single-threaded writes | [§19](19-harness-engineering.md), [§20](20-agent-runtime.md), [§13](13-multi-agent.md) |
| Jun 2026 | "Loop engineering" (Osmani); EU AI Act Omnibus adopted (Parliament Jun 16, Council Jun 29) | Designing the systems that prompt agents; high-risk obligations moved to Dec 2027 and Aug 2028 | [§21](21-loop-engineering.md), [§34](34-governance-regulation.md) |
| Jul 2026 | "Graph engineering" label (LangChain); MCP 2026-07-28 spec (stateless core, extensions framework, Tasks as an extension); AI Act Omnibus published as Regulation (EU) 2026/1744 (Jul 24) | Naming graph orchestration; protocol maturity; the new regulatory timeline becomes law | [§14](14-graph-engineering.md), [§15](15-protocols-mcp-a2a.md), [§34](34-governance-regulation.md) |

## The chain in one breath

Prompting let you program the model in words. Its free-text output needed **structure**, and its frozen knowledge needed **grounding**. Retrieval could only read, so models got **tools**. One tool call is one step, so tools went into a **loop**, and that loop is an agent. Loops needed **patterns**, then **multiple agents**, then explicit **graphs**. Integrations multiplied, so **protocols** standardized them. Protocols flooded the context, so **context engineering** curated it. Context resets every session, so agents needed **memory**. Memory still couldn't hold procedures cheaply, so **skills** loaded them on demand. All the pieces had to be assembled and tuned, which became **harness engineering**. Harnesses needed somewhere safe and durable to run, which is the **runtime**. Finally, a human prompting every run became the bottleneck, so engineers started building the systems that prompt agents: **loop engineering**.
