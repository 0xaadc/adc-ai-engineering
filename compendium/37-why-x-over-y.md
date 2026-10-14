# 37. Why X over Y

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This is the decision bank for the whole compendium, the synthesis of [§02](02-how-llms-work.md)–[§36](36-product-thinking.md). It applies to every era. Each earlier section explained one mechanism and argued its tradeoffs from the inside. This section puts the choices side by side, the way you meet them in a design review. [§36](36-product-thinking.md) ended on the point that every decision is a tradeoff, so this is where they are collected and argued in both directions. The principles that decide most of them are cost (P3, P10), verification (P4, P8), control flow (P7) and model progress (P12).

## Why this exists

Most AI architecture arguments reach you one-sided. In June 2025 Cognition published "Don't Build Multi-Agents", and the next day Anthropic described how its multi-agent research system beat a single agent by 90.2% on its internal eval. Both were right, about different tasks ([§13](13-multi-agent.md)). That is the general pattern. Each option wins where its mechanism fits and loses where it doesn't. A memorized verdict such as "RAG beats fine-tuning" or "agents beat workflows" will be wrong whenever the conditions differ, and the conditions change with every model release (P12). If you know the mechanism, you can derive the verdict for your own case.

Data engineers already work this way. Nobody settles normalize vs denormalize, batch vs streaming, or ETL vs ELT with a slogan. You ask about the read pattern, the freshness requirement and the cost, and the answer follows. This section gives you the same habit for AI systems: first a method, then a table of cues, then 22 tradeoffs, each argued from both sides.

## How it works (under the hood)

### The five-step method

The method sharpens the five questions from [§01](01-first-principles.md) for choosing between options.

1. **Which force?** Knowledge, uncertainty, agency, scarcity or change ([§01](01-first-principles.md)). Naming the force tells you which family of options is even relevant. A model that doesn't know your schema has a knowledge problem, and no amount of agent autonomy will fix it.
2. **Which mechanism or principle?** Say in one sentence how each option works and which principle it relies on. If you can't, you are comparing brand names.
3. **What does each option cost (P3, P10)?** Count tokens per call, latency, context space, and build and operating effort. Count per *successful task*, not per call.
4. **How will you verify it (P4, P8)?** Which option gives you a cheaper, more reliable check? The option with the better check often wins even if it looks slightly worse on paper, because you can tell when it fails.
5. **What happens when models improve (P12)?** Which option gets better for free with a stronger model, and which one becomes dead weight?

A worked example: *should we fine-tune a model to write SQL for our warehouse?*

```text
1. Force      Mostly knowledge (our schema, our metric definitions), plus a little behavior
              (our dialect and style).
2. Mechanism  P5: the schema and metrics are facts, so ground them (tools that list tables and
              columns, a skill for conventions). Dialect is behavior: try examples in the prompt first.
3. Cost       Fine-tuning: data prep, training, and retraining on every schema change and model
              release. Grounding: a few thousand cacheable tokens per call (P10).
4. Verify     SQL is cheap to check (P8): run it and compare the rows with gold queries.
              Build that eval first, because it decides every later question.
5. Models     Base models keep getting better at SQL; a fine-tune pins you to an older base (P12).
Decision      Schema tools + a conventions skill + an execution-checked eval. Revisit fine-tuning
              a small model only if evals plateau and volume makes per-call cost matter.
```

### Decision cues: if you see X, lean Y

These are starting points, not verdicts. Each row says which way the mechanism usually tips, and the tradeoffs below say when it tips back.

| If you see… | Lean toward… | Because | See |
|---|---|---|---|
| Facts that change often or differ per user | RAG or tools, not fine-tuning | Supplied knowledge is fresh and filterable (P5) | [§09](09-rag.md) |
| A small, stable corpus everyone may read | Long context plus prompt caching | No retrieval to tune; cached prefixes are cheap (P10) | [§09](09-rag.md), [§16](16-context-engineering.md) |
| IDs, error codes or product names in queries | Hybrid search | BM25 matches the exact tokens that embeddings blur | [§08](08-embeddings-and-search.md) |
| "What are the themes across everything?" | GraphRAG or map-reduce summaries | No single chunk holds the answer | [§09](09-rag.md) |
| Steps you can write down in advance | A workflow | Code-owned control flow is cheap and testable (P7) | [§11](11-agents.md) |
| Steps that depend on what earlier steps find | An agent loop with caps | Only the model can choose the next step | [§11](11-agents.md) |
| Breadth-first, read-heavy research worth many times the tokens | Orchestrator + read-only subagents | Parallel contexts, one writer | [§13](13-multi-agent.md) |
| Tightly coupled edits, such as most coding | One agent | Parallel writers make conflicting decisions | [§13](13-multi-agent.md) |
| Approvals, compliance gates, SLAs | An explicit graph, with an agent inside a node if needed | Business structure belongs in edges | [§14](14-graph-engineering.md) |
| Many chained calls over large intermediate data | Code as action / programmatic tool calling | Intermediate results stay out of context (P3) | [§10](10-tool-use.md) |
| Tool definitions above about 10K tokens | Tool search | Deferred definitions keep context lean | [§10](10-tool-use.md), [§15](15-protocols-mcp-a2a.md) |
| The same tools needed by several hosts or teams | MCP | N×M becomes N+M (P11) | [§15](15-protocols-mcp-a2a.md) |
| Long "how we do X here" procedures | Skills | Loaded only when they match (P3) | [§18](18-skills.md) |
| Short rules that apply to nearly every task | The system prompt or AGENTS.md | Always relevant, so always loaded | [§18](18-skills.md) |
| Per-user preferences and history | Memory | The agent writes it, scoped per user | [§17](17-memory.md) |
| A model that rushes as its context fills | A context reset with a handoff file | A clean slate, where compaction keeps the noise | [§16](16-context-engineering.md), [§19](19-harness-engineering.md) |
| Multi-step logic, debugging, planning | Higher reasoning effort | Thinking tokens buy accuracy (P10) | [§04](04-reasoning-models.md) |
| Classification or extraction at high volume | Low effort or a small model, maybe routed | Cost and latency dominate | [§04](04-reasoning-models.md), [§30](30-cost-latency-reliability.md) |
| Output that code will parse | Strict structured outputs | The grammar guarantees the shape | [§06](06-structured-outputs.md) |
| A property a program can check | A code grader | Deterministic, cheap, not lenient | [§26](26-evals.md) |
| Quality only a reader can judge | A calibrated LLM judge | Code can't read meaning; calibrate the judge (P4) | [§26](26-evals.md) |
| A voice flow with audits and heavy tool use | Cascaded STT → LLM → TTS | Inspectable text at every step | [§25](25-voice-agents.md) |
| An app that has an API | The API, not computer use | Structured, cheap, deterministic | [§24](24-computer-use-and-research-agents.md) |
| Irreversible or external actions | Human approval for that action | Verification after the fact is impossible (P8, P9) | [§20](20-agent-runtime.md), [§32](32-security-guardrails.md) |
| Data that can't leave your network, or steady high volume | Self-hosted open weights | Control, and utilization economics | [§31](31-open-weights-self-hosting.md) |
| Durable execution or checkpoints you'd otherwise build | A framework or durable runtime | Hard infrastructure, already debugged | [§14](14-graph-engineering.md), [§20](20-agent-runtime.md) |

### Reading the tradeoffs

Each tradeoff below gives the conditions for each side, then the principle that decides between them and the section that explains the mechanism. They are grouped by force: knowledge (1–5), agency and control flow (6–12), context (13–15), uncertainty (16–17), scarcity (18–21) and change (22). Two habits apply to all of them. Defaults lean toward the cheaper, more controllable option, and you move away from it only when an eval says you must. And many of the best answers are combinations rather than either side.

### 1. Prompting vs RAG vs fine-tuning

- **Choose prompting when** the model already has the knowledge and the task is about instructions, examples and format. It is the cheapest option to try and the fastest to change, and it improves with every model release.
- **Choose RAG when** answers depend on facts that are private, changing, per-user or must be cited. Supplied knowledge is fresh and permission-filtered.
- **Choose fine-tuning when** you need behavior that prompting can't produce reliably at your volume: a strict style or format, a narrow skill, or a small model distilled to match a large one on one task. Don't fine-tune facts in: they blur, can't be cited, and can't be revoked per user.
- **Principle:** P5, ground for facts and fine-tune for behavior. Try prompting, then retrieval, then fine-tuning, and combine them freely. Mechanism: [§05](05-api-and-prompting.md), [§09](09-rag.md), [§29](29-adapting-models.md).

### 2. Long context vs RAG

- **Choose long context when** the corpus is small and stable, every user may see all of it, and questions need reading across the whole thing. With prompt caching, a stable prefix is cheap on repeat (a cache hit costs a small fraction of the base input price), and there is no retrieval pipeline to tune or let go stale.
- **Choose RAG when** the corpus is large, changes often, or needs per-user permissions, or when you pay per call at high volume. Every long-context call processes every token, quality degrades with length (P3), and a prompt can't filter by user.
- **Principle:** P3 and P10 on one side, pipeline complexity on the other. A common hybrid: RAG selects, and long context holds what RAG selected. Mechanism: [§09](09-rag.md), [§16](16-context-engineering.md), [§03](03-inference.md).

### 3. Vector search vs hybrid search

- **Choose vector-only when** queries paraphrase the documents and exact tokens rarely matter: conceptual questions, multilingual content, FAQs. One index is simpler to run.
- **Choose hybrid (BM25 plus vectors, fused with reciprocal rank fusion, then a reranker) when** queries contain IDs, codes, names, numbers or new jargon. It is the production default because it covers both failure modes, at the cost of a second index.
- **Principle:** embeddings capture topic, not identity, because contrastive training rewards similarity, while lexical indexes match exact tokens. Measure recall@k on your own queries before choosing. Mechanism: [§08](08-embeddings-and-search.md).

### 4. RAG vs GraphRAG

- **Choose plain RAG when** the answer lives in a few passages ("what's the refund window?"). Hybrid search is cheaper and just as good for needle lookups.
- **Choose GraphRAG when** the question is about the whole corpus ("what themes recur across 5,000 incident reports?") or connects entities across many documents. Top-k retrieval would summarize a biased sample.
- **Principle:** P10 at index time. GraphRAG pays LLM calls for every chunk and community up front, bakes extraction errors into the graph, and needs re-indexing when data changes. It is also not graph engineering: there the graph is control flow, not data. Mechanism: [§09](09-rag.md).

### 5. Memory vs RAG

- **Choose memory when** the knowledge is about *this* user or project and comes from the agent's own history: preferences, decisions, lessons learned. The agent or a background job writes it, it is scoped per user, and it is fresh by the next session.
- **Choose RAG when** the knowledge is a shared, reviewed corpus: policies, documentation, product facts. An ingestion pipeline owns it, and everyone sees the same version.
- **Principle:** both put tokens into context (P2). The difference is who writes and who reads. Agent-written memory is a persistent injection risk (P9), so keep shared facts in the reviewed corpus. Mechanism: [§17](17-memory.md), [§09](09-rag.md).

### 6. Workflow vs agent

- **Choose a workflow when** you can write the steps down: classify, extract, route, summarize, approve. Code owns control flow, so cost is bounded, failures happen at a known step, and each step is testable.
- **Choose an agent when** each step depends on what the previous ones found: debugging, open-ended research, multi-hop questions. Only the model can pick the next action, and it can recover from surprises.
- **Principle:** P7, the autonomy dial, together with P8: at 95% per step, 20 steps succeed about 36% of the time. Use the least autonomy the task allows, and remember that a workflow can contain one agentic step. Mechanism: [§11](11-agents.md), [§12](12-agentic-design-patterns.md).

### 7. Single agent vs multi-agent

- **Choose one agent when** the work is sequential or tightly coupled, which includes most coding. One context keeps every implicit decision consistent, costs the least and is easiest to debug. Google's scaling study measured multi-agent setups at 39–70% worse on sequential work.
- **Choose an orchestrator with subagents when** the work is breadth-first, parallelizable, read-heavy and high-value, such as research across many sources or a review from several angles. Separate contexts read in parallel, and the lead keeps only their summaries. Expect 3–10× the tokens of one agent.
- **Principle:** a second agent is a second context (P2, P3). Keep writes single-threaded and verification central. Mechanism: [§13](13-multi-agent.md).

### 8. Graph vs harness loop

- **Choose an explicit graph when** the process has a known shape with branches, approvals, compliance gates or SLAs, and you need checkpoints, resume and an audit trail. Edges that encode business structure stay valuable however good models get.
- **Choose a harness loop when** the task is open-ended (coding, research) and the best path changes from run to run. A loop is a degenerate graph whose next edge the model picks, and it improves as models do.
- **Principle:** P7 plus P12. Fix in code the edges that reflect the business, and leave to the model the edges that only compensate for model weakness, because those are the ones that get deleted. You can combine the two by putting an agent inside one node of a graph. Mechanism: [§14](14-graph-engineering.md), [§19](19-harness-engineering.md), [§21](21-loop-engineering.md).

### 9. Tool calls vs code as action

- **Choose JSON tool calls when** actions are few, discrete and consequential. Each call can be validated, gated, approved and logged on its own, with no sandbox for arbitrary code.
- **Choose code as action (CodeAct, programmatic tool calling) when** the task chains many calls, loops, filters or joins large intermediate data. The code runs in a sandbox and only its output enters context. CodeAct beat JSON actions by up to 20%, and Anthropic's code-execution-with-MCP example cut 150,000 tokens to 2,000.
- **Principle:** context and cost (P3, P10) against control (P6, P9). Code composes well and saves context, but it makes per-action gating coarse and requires a real sandbox. Mechanism: [§10](10-tool-use.md), [§20](20-agent-runtime.md).

### 10. MCP vs direct tool definitions

- **Choose direct tool definitions when** one application uses a handful of tools you own. There is no extra process, no JSON-RPC and no second auth system, so they are the fastest to build and debug.
- **Choose MCP when** tools serve several hosts, third parties maintain them, users bring their own, or you want one governed catalog. MCP is a distribution layer, not a better way to call a function.
- **Principle:** P11, which turns N×M into N+M. But every connected tool still costs context on every request (P3), and every server is part of your supply chain (P9). Mechanism: [§15](15-protocols-mcp-a2a.md), [§10](10-tool-use.md).

### 11. Computer use vs API

- **Choose an API or MCP tool when** one exists. A typed call is cheap, fast, deterministic and easy to limit.
- **Choose computer use when** there is no API: legacy desktop apps, third-party portals, one-off tasks across several GUIs. When the task stays in a browser, read the accessibility tree before falling back to pixels. When a flow repeats, have the agent write a script once and run that instead.
- **Principle:** P3 and P10. Every step carries a screenshot, and a 1280×720 one is about 1,196 visual tokens on Claude. Many small steps compound errors (P8), and everything on screen is untrusted input (P9). Mechanism: [§24](24-computer-use-and-research-agents.md), [§07](07-multimodal.md).

### 12. Human approval vs autonomy

- **Choose human approval when** an action is irreversible, external or expensive: payments, deletions, customer emails, production deploys. Show the full arguments, not a summary, and implement the wait as a durable interrupt that saves state and resumes on the answer.
- **Choose autonomy inside a sandbox when** actions are reversible or contained, the checks are computational, and approvals would come so often that people click yes without reading. One sandbox boundary replaces hundreds of per-action prompts.
- **Principle:** P8 and P9. Put humans where verification after the fact is impossible, not everywhere. Approval fatigue turns oversight into theater (OWASP lists it as ASI09). Mechanism: [§20](20-agent-runtime.md), [§32](32-security-guardrails.md), [§11](11-agents.md), [§35](35-ai-ux.md).

### 13. Skills vs MCP

- **Choose an MCP server when** the agent needs *access*: query a warehouse, read tickets, post a message. A running process enforces authentication and executes the actions.
- **Choose a skill when** the agent needs *know-how*: the order of queries for profiling a table, a team's review checklist, a document recipe, optionally with scripts. A skill is a folder of markdown that costs about 100 tokens until it is used.
- **Principle:** they aren't rivals, and real agents use both. The MCP server provides `run_query`, and the skill says which queries to run and how to read them. Ask "what can it reach?" versus "how do we do it here?" Mechanism: [§18](18-skills.md), [§15](15-protocols-mcp-a2a.md).

### 14. Skills vs system prompt

- **Choose the system prompt (or AGENTS.md / CLAUDE.md) when** a rule is short and applies to almost every task: identity, hard constraints, the build command. It is always loaded, so there is no trigger to miss.
- **Choose a skill when** a procedure is long and needed only sometimes. Fifty 5,000-token procedures in a system prompt cost 250,000 tokens on every call. As skills, they cost about 5,000 tokens while idle.
- **Principle:** P3. Caching lowers the dollar cost of a long prefix, but not its attention cost. The tradeoff also runs the other way: a skill fires on its description, which is probabilistic (P4), so a rule that must always apply shouldn't depend on a match. Mechanism: [§18](18-skills.md), [§16](16-context-engineering.md).

### 15. Compaction vs context reset

- **Choose compaction when** the model handles long contexts well and continuity matters: one agent with summarized history and no extra orchestration. Anthropic's harness dropped resets for compaction once Opus 4.5 stopped showing "context anxiety."
- **Choose a reset when** the model degrades or rushes near its limit, or the work spans many windows anyway. A fresh agent reads a handoff (progress file, git log, feature list) and starts clean.
- **Principle:** P2 and P3, with P12 in miniature: the reset was a workaround that a better model deleted, so re-test it per model. A 2026 catch: on models with preserved thinking (Opus 5.5, Sonnet 5.5, Haiku 5.5, Fable 5.1), hand-rolled compaction that keeps recent turns together with their thinking blocks breaks. Let the API compact, or replay no thinking. Mechanism: [§16](16-context-engineering.md), [§19](19-harness-engineering.md).

### 16. Structured outputs vs free text plus parsing

- **Choose strict structured outputs when** code consumes the result: extraction, classification, tool arguments. The schema is compiled into a grammar that masks illegal tokens, so the shape is guaranteed. On Anthropic this is `output_config.format` **(GA)** since Jan 2026.
- **Choose free text when** a person reads the output, when you need schema features the grammar doesn't support, or when a tight format would hurt reasoning on a non-thinking model. In that last case, use "reason, then extract": a free-text call, then a small constrained one.
- **Principle:** P1. Masking sets illegal tokens' probability to zero, which is a guarantee, while prompting only shifts probabilities. The grammar owns the shape and the model owns the values, so valid-but-wrong output still needs evals (P4). Mechanism: [§06](06-structured-outputs.md).

### 17. Code grader vs LLM-as-judge

- **Choose a code grader when** a program can decide the property: the JSON validates, the tests pass, the SQL returns the gold rows, the cited document exists. It is deterministic, fast, free and never lenient.
- **Choose an LLM judge when** the property needs reading: faithfulness to sources, tone, policy compliance, whether a summary leaves out something important. Use one judge per failure mode with a binary verdict, and calibrate it against human labels (true positive and true negative rates) before trusting its numbers.
- **Principle:** P8, verification is the bottleneck. Prefer computational sensors, and add inferential ones only where code can't reach. Judges are sampled and biased (P4), and tuning against an uncalibrated judge is Goodhart's law. Mechanism: [§26](26-evals.md), [§19](19-harness-engineering.md).

### 18. Reasoning model vs standard model

- **Choose more thinking when** the task involves multi-step logic, planning, debugging, code changes, agent loops or costly mistakes. Thinking tokens let the model check its own work before it answers.
- **Choose low effort or no thinking when** the task is classification, extraction, lookup, chat, voice or high-volume batch work. Thinking adds latency and output tokens (P10), and it can't supply missing knowledge (P5).
- **Principle:** P10, test-time compute is a dial. In 2026 the question is mostly "which effort level?" on one hybrid model. Start at the default and step down until evals drop. Mechanism: [§04](04-reasoning-models.md).

### 19. Big model vs small model and routing

- **Choose one big model when** traffic is low, tasks vary widely, or quality failures are expensive. One model means one prompt set and one eval, and at low volume your engineering time costs more than the tokens.
- **Choose small models with routing or a cascade when** volume is high and traffic is mixed. A classifier, or a cheap first attempt, sends easy inputs to a small fast model and escalates the hard ones. RouteLLM cut costs by more than 2× in some of its tests.
- **Principle:** P10 versus P8. The router is one more step that can fail silently, so it needs a default route, an external confidence signal and its own accuracy eval. Try the simpler lever first: one model at a lower effort level. Mechanism: [§12](12-agentic-design-patterns.md), [§30](30-cost-latency-reliability.md).

### 20. Hosted API vs self-hosting

- **Choose a hosted API when** you want frontier quality, your traffic varies, and you don't want to run GPUs. Providers batch many customers onto shared hardware, which is hard to match at small scale.
- **Choose self-hosted open weights when** data can't leave your environment, traffic is high and steady enough to keep GPUs busy, you need custom constrained decoding or fine-tunes the APIs don't offer, or you need a pinned model that never changes under you.
- **Principle:** P10. The economics turn on utilization, because an idle GPU costs as much as a busy one. Count operations and the eval work that quantization needs. Check first whether a hosted model offered inside your own cloud account meets the data requirement. Mechanism: [§31](31-open-weights-self-hosting.md), [§03](03-inference.md).

### 21. Cascaded voice vs speech-to-speech

- **Choose cascaded (speech-to-text → LLM → text-to-speech) when** you need inspectable text at every step: regulated flows, heavy tool use, audit logs, evals on transcripts, and the freedom to swap any component or use any text model.
- **Choose speech-to-speech when** conversational feel matters most: the lowest latency, natural interruptions, and tone preserved end to end. It is harder to control, log and test.
- **Principle:** P10 (latency adds up across chained stages) against P4 and P8 (what you can measure and check). Mechanism: [§25](25-voice-agents.md), [§07](07-multimodal.md).

### 22. Framework vs build your own

- **Choose a framework or managed runtime when** you need infrastructure that is hard to build: durable execution, checkpointing, human-in-the-loop interrupts, tracing. Those are long debugging projects that someone has already finished.
- **Choose to build your own loop when** the core is small (an agent loop is about 20 lines), when you need to see every token sent and received, or when a framework's abstractions encode workarounds for older models. Anthropic warns that frameworks can "obscure the underlying prompts and responses."
- **Principle:** P12. Thin, legible scaffolding ages well, and heavy abstractions over prompts age badly. A common answer is both: your own loop running on a durable runtime. Mechanism: [§11](11-agents.md), [§19](19-harness-engineering.md), [§20](20-agent-runtime.md), [§22](22-build-a-harness.md).

## Comparison

**The 22 decisions at a glance.** The default is the side to start from in Oct 2026. The last column says which way model progress has been pushing the decision (P12), which is the part most likely to change.

| # | Decision | Start with | Switch when | How model progress shifts it |
|---|---|---|---|---|
| 1 | Prompting / RAG / fine-tuning | Prompting, then RAG | Behavior prompting can't reach at your volume | Better prompting results; fewer reasons to fine-tune |
| 2 | Long context / RAG | RAG for large or permissioned data | The corpus is small, stable and shared | Bigger windows and cheaper caching favor long context |
| 3 | Vector / hybrid search | Hybrid | Pure paraphrase queries | Little change; exact tokens still need BM25 |
| 4 | RAG / GraphRAG | RAG | Whole-corpus "themes" questions | Agentic search and long context take some of its work |
| 5 | Memory / RAG | RAG for shared facts | Per-user history and preferences | Agents get better at deciding what to remember |
| 6 | Workflow / agent | Workflow | Steps can't be predicted | Higher per-step reliability makes agents viable on more tasks |
| 7 | Single / multi-agent | Single | Breadth-first, parallel, high-value reads | Longer reliable contexts reduce the need to split |
| 8 | Graph / harness loop | Loop for open tasks, graph for processes | Approvals, gates, SLAs | Workaround edges get deleted; business edges stay |
| 9 | Tool calls / code as action | Tool calls | Many chained calls, big data | Stronger coders make code as action more attractive |
| 10 | Direct tools / MCP | Direct tools | Several hosts or third-party tools | Tool search lowers MCP's context cost |
| 11 | API / computer use | API | No API exists | GUI agents improve, but stay slower and costlier |
| 12 | Approval / autonomy | Approval on irreversible actions | Contained, reversible, computationally checked work | Better sandboxes allow more autonomy safely |
| 13 | Skills / MCP | Both, for different jobs | n/a | Unchanged: know-how and access stay distinct |
| 14 | System prompt / skills | Skills for long procedures | Short, universal rules | More reliable triggering favors skills |
| 15 | Compaction / reset | Compaction | The model shows context anxiety | Resets already deleted on newer models |
| 16 | Structured / free text | Structured for machine consumers | Human readers, unsupported schemas | Grammar support widens; thinking keeps reasoning intact |
| 17 | Code grader / LLM judge | Code grader | Properties only a reader can judge | Judges improve but still need calibration |
| 18 | Reasoning / standard | Default effort, then step down | Routine high-volume work | One hybrid model with an effort dial |
| 19 | Big / small + routing | One model | High mixed volume and a reliable confidence signal | Small models catch up, which favors routing |
| 20 | API / self-host | API | Residency, steady high volume, custom decoding | Open weights narrow the quality gap |
| 21 | Cascaded / speech-to-speech | Cascaded for regulated flows | Feel and latency dominate | Speech-to-speech models get more controllable |
| 22 | Framework / build your own | Your own loop on a durable runtime | You'd otherwise rebuild checkpoints and tracing | Frameworks that hide prompts age fastest |

## What it didn't solve

A decision bank only works if everyone in the room means the same thing by the words. In practice, decisions are argued in labels: "we need better context engineering", "let's do harness engineering", "is this a loop or a graph?". New labels arrive faster than their definitions settle. Some name a real bottleneck, and others rename something old. The last section maps those labels, where they came from, and how mature each one is. → Next: [§38 The Disciplines and Skills Map](38-disciplines-map.md)

## Check your understanding

**Q: You're building an internal Q&A bot over 300 pages of HR policy that every employee may read, updated quarterly, with modest traffic. Long context or RAG, and why?**

Long context with prompt caching. The corpus is small, stable and readable by everyone, so RAG's main advantages (scale, freshness, per-user filtering) don't apply, and caching makes the repeated prefix cheap (P10). You skip a retrieval pipeline that could miss the right clause. Switch to RAG if the corpus grows large enough for context rot to show in your evals (P3), or if some documents become restricted to certain employees.

**Q: You're building search for a support assistant where customers paste error codes like "E-4012" alongside natural-language questions. Vector or hybrid search, and why?**

Hybrid. Embeddings capture topic, so "E-4012" and "E-4021" can land close together, while BM25 matches the exact token. Fusing both with reciprocal rank fusion and reranking the top results covers paraphrased questions and exact codes. The cost is a second index. Vector-only is fine only if your query logs show that exact identifiers rarely matter.

**Q: You're building a nightly job that classifies 2 million product reviews into 12 categories on a tight budget. Which model and output setup do you choose, and why?**

A small model at low or no reasoning effort, strict structured outputs with an enum of the 12 labels, and the batch API. The task is single-step classification, so thinking tokens add cost without accuracy (P10), the grammar guarantees a valid label, and batch pricing halves the bill because nobody is waiting. Validate on a labeled sample first. If one or two categories are genuinely ambiguous, route only low-confidence items to a bigger model.

**Q: You're building an agent to refactor a large codebase, and a colleague proposes five parallel agents, each editing its own module. Single or multi-agent, and why?**

A single writer, possibly helped by read-only subagents. Refactoring is tightly coupled: each edit carries implicit decisions about interfaces and naming, and parallel writers make conflicting ones (Cognition's lesson). Google's study measured multi-agent setups at 39–70% worse on sequential work. Use subagents to explore and summarize the modules in parallel, and keep one agent writing. Parallel writers make sense only for truly independent changes, each verified separately.

**Q: You're automating invoice processing: extract fields, match them to the purchase order, route anything over $10,000 to a manager, then pay. Graph or agent loop, and why?**

An explicit graph. The steps are known, the approval is business structure that should never depend on a model's choice, and you need checkpoints and an audit trail (P7). Extraction is a structured-output node with code checks such as totals and PO match. The approval is a durable interrupt that shows the full details, and payment runs only after it. If mismatches need open-ended investigation, put an agent inside that one node rather than making the whole process agentic.

**Q: You're building an agent to file 50 expense reports a week in a legacy desktop app that has no API. Which interface do you choose, and why?**

Computer use in a disposable VM, because no API exists, but plan to replace it. Every step costs screenshot tokens and compounds error risk (P8, P10), and the screen is untrusted input (P9). Have a human approve before each final submit, and verify the end state outside the GUI if you can. Because the flow repeats, have the agent author a script once and run that script, re-authoring it when the UI changes. If the vendor ever offers an API, switch to it.

**Q: Your eval for a summarization feature must catch summaries that invent facts. Code grader or LLM judge, and why?**

Mostly an LLM judge, because checking whether each claim is supported by the source requires reading meaning, which code can't do. Give it one narrow binary question (is every claim supported?), keep it separate from the summarizer, and calibrate it on at least 50 labeled passes and 50 labeled fails, measuring true positive and true negative rates before trusting its numbers. Add code graders for whatever a program can decide: length, required sections, that quoted strings appear in the source. Never tune prompts against an uncalibrated judge.

**Q: You're building a voice agent for a bank's card-replacement line, with identity verification and strict audit requirements. Cascaded or speech-to-speech, and why?**

Cascaded. Every step produces inspectable text, so you can log the transcript, run evals on it, apply guardrails before tool calls such as blocking the card, and swap components if needed (P8). You pay in latency because the stages add up (P10), so stream every stage and keep responses short. Speech-to-speech fits better where conversational feel matters more than auditability.

**Q: Your agent's system prompt holds 40 internal procedures, about 60,000 tokens, and quality is dropping. What do you change, and why?**

Move the procedures into skills and keep only short, universal rules in the system prompt. Every call currently pays for all 40 procedures while using one, and the irrelevant ones dilute attention (P3), which caching doesn't fix. As skills, the idle cost is about 100 tokens each, and a body loads only when its description matches. Because triggering is probabilistic (P4), write descriptions that say what and when, test them, and keep any rule that must always apply in the system prompt.

**Q: A healthcare client requires that patient data never leave their network, and the workload is steady, high-volume document extraction. Hosted API or self-hosting, and why?**

First check whether a hosted model available inside the client's own cloud account, with private networking, meets the requirement, since that keeps frontier quality without running GPUs. If not, self-host open weights. The steady volume keeps GPUs utilized, which is what makes self-hosting pay (P10), and extraction suits a smaller tuned or constrained model. Budget for operations, and evaluate quantized models against your extraction evals before switching.

## Takeaways

- Every option wins where its mechanism fits. Learn the conditions, not the verdicts.
- Run five steps on any choice: force, mechanism, cost (P3, P10), verification (P4, P8), model progress (P12).
- The option that is cheaper to verify often wins, because you can tell when it fails.
- Start from the cheaper, more controllable side (prompting, workflows, one agent, direct tools) and move only when evals say so.
- Business structure belongs in code. Workarounds for model weakness get deleted, so keep them thin.
- The best answers are often combinations: RAG plus long context, a graph with an agent node, MCP plus skills.
- Re-run the decision when the model changes, and keep the eval that lets you.

## Sources

- Anthropic, Erik Schluntz and Barry Zhang, "Building effective agents" (Dec 19, 2024): https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, "Effective context engineering for AI agents" (Sep 29, 2025): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (May 2020): https://arxiv.org/abs/2005.11401
- Hong et al. (Chroma), "Context Rot: How Increasing Input Tokens Impacts LLM Performance" (Jul 2025): https://research.trychroma.com/context-rot
- Cormack, Clarke and Büttcher, "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods" (SIGIR 2009): https://doi.org/10.1145/1571941.1572114
- Edge et al. (Microsoft), "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (Apr 2024): https://arxiv.org/abs/2404.16130
- Sumers et al., "Cognitive Architectures for Language Agents" (CoALA, Sep 2023): https://arxiv.org/abs/2309.02427
- Anthropic, "How we built our multi-agent research system" (Jun 13, 2025): https://www.anthropic.com/engineering/multi-agent-research-system
- Walden Yan (Cognition), "Don't Build Multi-Agents" (Jun 12, 2025): https://cognition.ai/blog/dont-build-multi-agents
- Kim et al. (Google Research), "Towards a Science of Scaling Agent Systems," arXiv 2512.08296: https://arxiv.org/abs/2512.08296
- LangChain, "3 Years of Graph Engineering with LangGraph" (Jul 22, 2026): https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph
- Wang et al., "Executable Code Actions Elicit Better LLM Agents" (CodeAct, Feb 2024): https://arxiv.org/abs/2402.01030
- Anthropic, "Introducing advanced tool use on the Claude Developer Platform" (Nov 24, 2025): https://www.anthropic.com/engineering/advanced-tool-use
- Anthropic, "Code execution with MCP" (Nov 4, 2025): https://www.anthropic.com/engineering/code-execution-with-mcp
- MCP specification 2026-07-28: https://modelcontextprotocol.io/specification/2026-07-28
- Agent Skills specification: https://agentskills.io/specification
- Anthropic, "Harness design for long-running application development" (Mar 24, 2026): https://www.anthropic.com/engineering/harness-design-long-running-apps
- Claude docs, Compaction: https://platform.claude.com/docs/en/build-with-claude/compaction ; Preserved thinking: https://platform.claude.com/docs/en/build-with-claude/preserved-thinking
- Claude docs, Structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Claude docs, Thinking: https://platform.claude.com/docs/en/build-with-claude/thinking
- Claude docs, Computer use tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool
- Birgitta Böckeler, "Harness engineering for coding agent users," martinfowler.com (Apr 2, 2026): https://martinfowler.com/articles/harness-engineering.html
- Hamel Husain and Shreya Shankar, "AI Evals: Everything You Need to Know" (evals FAQ): https://hamel.dev/blog/posts/evals-faq/
- Ong et al., "RouteLLM: Learning to Route LLMs with Preference Data" (Jun 2024): https://arxiv.org/abs/2406.18665
- OpenAI, Voice agents guide (chained vs speech-to-speech): https://developers.openai.com/api/docs/guides/voice-agents
- OWASP, "Top 10 for Agentic Applications for 2026" (Dec 2025): https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- Rich Sutton, "The Bitter Lesson" (Mar 13, 2019): http://www.incompleteideas.net/IncIdeas/BitterLesson.html
