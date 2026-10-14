# 38. The Disciplines and Skills Map

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This section is the synthesis, and it covers every era. Between 2023 and 2026 the field produced a stream of "X engineering" labels: prompt, flow, context, harness, loop, graph, agentic, compound, eval-driven, spec-driven, memory, environment. Each one claims to be the new thing. Earlier sections explain the practices themselves. This section sorts out the *labels*: where each came from, how mature it really is, how they fit inside one another, and which skills sit underneath all of them.

## Why this exists

Labels are compression. A good one packs a set of practices into a word that a team can coordinate around. "We need better context engineering" says something specific in a way "make the AI better" does not. Labels also attract hype, and in AI they arrive faster than most people can tell which ones have substance.

There is a pattern behind the labels, and it explains why they keep appearing. **Each new label marks the place where the bottleneck moved.**

- When models were weak and the API was new, the bottleneck was *the words*. That gave us **prompt engineering**.
- When agents began pulling in tools, documents, and long histories, it became *everything the model sees*. That gave us **context engineering**.
- When agents ran for hours with sandboxes, hooks, and subagents, it became *the whole system around the model*. That gave us **harness engineering**.
- When a capable harness existed but a human still had to prompt and check every run, it became *human attention*. That gave us **loop engineering**.

Each layer's work did not disappear. It got absorbed into the layer above it. Prompts still matter; they are now one input to context, which is one product of a harness, which is one component a loop drives. This is the bitter lesson (P12) applied to people: as the model takes over more of a layer, the engineering moves to the layer above.

## How it works (under the hood)

### The core nesting

```text
┌──────────────────────────────────────────────────────────────────────┐
│ LOOP ENGINEERING: the system that prompts the system                  │
│  automations, stop conditions, back pressure, parallel worktrees      │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ HARNESS ENGINEERING: everything except the model                  │ │
│ │  tools, sandbox, hooks, subagents, guides & sensors, runtime      │ │
│ │ ┌──────────────────────────────────────────────────────────────┐ │ │
│ │ │ CONTEXT ENGINEERING: everything the model sees on this call   │ │ │
│ │ │  retrieval, memory, compaction, skills, tool results          │ │ │
│ │ │ ┌──────────────────────────────────────────────────────────┐ │ │ │
│ │ │ │ PROMPT ENGINEERING: the instructions themselves           │ │ │ │
│ │ │ └──────────────────────────────────────────────────────────┘ │ │ │
│ │ └──────────────────────────────────────────────────────────────┘ │ │
│ └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
   side branch: GRAPH ENGINEERING (explicit control flow)
   application: AGENTIC ENGINEERING (all of it, applied to building software)
```

Practitioners themselves state this nesting. Anthropic calls context engineering "the natural progression of prompt engineering." LangChain writes that "harnesses today are largely delivery mechanisms for good context engineering." Birgitta Böckeler calls a user's harness "a specific form of context engineering." Addy Osmani places loop engineering "one floor above the harness." No single canonical source lays out the full chain *prompt → context → harness → loop*; it is the community's synthesis, and each link is attested separately.

### Prompt engineering (2020– · established, now a subset)

- **What it is:** writing instructions, examples, and structure so a model produces what you want. Covered in [§05](05-api-and-prompting.md).
- **Where it came from:** the GPT-3 era (2020), when few-shot prompting showed you could "program" a model with examples.
- **What it still means today:** clear instructions, good examples, structure (such as XML tags), and system prompts at the right level of detail. It still matters, but on its own it is no longer enough to build an application.
- **Status:** established. Its standalone reputation faded once people saw how much of the job had moved into context and systems.

### Flow engineering (Jan 2024 · historical precursor)

- **What it is:** replacing one big prompt with a multi-stage, test-driven flow. Generate, run tests, reflect, and iterate.
- **Where it came from:** the AlphaCodium paper, "From Prompt Engineering to Flow Engineering" (Ridnik, Kredo, Friedman, Jan 2024). Its flow raised GPT-4's pass@5 on CodeContests from 19% to 44%.
- **Status:** a precursor. The term is rarely used now, but its idea survives in evaluator-optimizer patterns ([§12](12-agentic-design-patterns.md)), back pressure in loops ([§21](21-loop-engineering.md)), and explicit graphs ([§14](14-graph-engineering.md)).

### Context engineering (2025 · established)

- **What it is:** "the delicate art and science of filling the context window with just the right information for the next step" (Karpathy). It covers retrieval, memory, compaction, tool-result management, isolation through subagents, and progressive disclosure. See [§16](16-context-engineering.md) and [§17](17-memory.md).
- **Where it came from:** HumanLayer says Dex Horthy's "12-factor agents" (Apr 2025) used it first. Tobi Lütke's and Andrej Karpathy's posts (Jun 2025) made it mainstream. LangChain's write/select/compress/isolate framework (Jul 2025) and Anthropic's "Effective context engineering for AI agents" (Sep 2025) gave it shape.
- **Why it's real:** it names a distinct bottleneck, the finite and decaying attention budget (P3). It has distinct failure modes (poisoning, distraction, confusion, clash) and techniques you can teach.
- **Status:** established.

### Harness engineering (Nov 2025 → 2026 · established)

- **What it is:** designing everything in an agent except the model: tools, sandbox, hooks, subagents, guides (feedforward) and sensors (feedback), and the runtime. "Agent = Model + Harness." See [§19](19-harness-engineering.md) and [§20](20-agent-runtime.md).
- **Where it came from:** Anthropic's "Effective harnesses for long-running agents" (Nov 2025) used the word. Mitchell Hashimoto named the practice (Feb 5, 2026): "anytime you find an agent makes a mistake, you… engineer a solution such that the agent never makes that mistake again." OpenAI's "Harness engineering" post (Feb 11, 2026), LangChain's "Anatomy of an Agent Harness" (Mar 10, 2026), and Böckeler on martinfowler.com (Apr 2, 2026) established it.
- **Why it's real:** it has artifacts (AGENTS.md, hooks, linters with fix-it messages, progress files), a measurable effect (the same model scores differently in different harnesses), and a core practice, the ratchet, in which every mistake becomes a permanent fix.
- **Status:** established. All the major labs and toolmakers use the term.

### Loop engineering (practice Jul 2025, label Jun 2026 · emerging)

- **What it is:** instead of prompting the agent yourself, you design the system that prompts it. That means scheduled runs, stop conditions checked by a separate model, back pressure from tests and linters, parallel loops in git worktrees, and state kept on disk between fresh-context iterations. See [§21](21-loop-engineering.md).
- **Where it came from:** Geoffrey Huntley's "Ralph Wiggum" loop (Jul 2025). In its purest form it is a bash `while` loop that keeps feeding the same prompt to a coding agent. Huntley followed it with "everything is a ralph loop" (Jan 2026), and Addy Osmani named the discipline in "Loop Engineering" (Jun 2026).
- **Honest status:** emerging. The practice is real and widely used. The label is new, overlaps heavily with harness engineering, and attracts SEO content. Treat it as "the outer layer of harness engineering" until the term settles.

### Graph engineering (practice 2024, label Jul 2026 · niche label, established practice)

- **What it is:** making control flow explicit as a state machine. Nodes (code, model calls, tools, or whole agents), conditional edges, cycles, shared state, checkpoints, and interrupts for human approval. See [§14](14-graph-engineering.md).
- **Where it came from:** the practice goes back to LangGraph (early 2024). LangChain popularized the label in "3 Years of Graph Engineering with LangGraph" (Jul 22, 2026), after it trended among practitioners. Google ADK 2.0 and Microsoft Agent Framework have since converged on graph runtimes.
- **The naming trap:** it is *not* GraphRAG, which uses knowledge graphs for retrieval ([§09](09-rag.md)).
- **Status:** niche label, established practice. It sits *beside* the core nesting: it is about who owns control flow (P7), not about what the model sees.

### Agentic engineering (Feb 2026 · established)

- **What it is:** professional software development with coding agents. You still review and own the code, use git deliberately, and lean on subagents and tests. See [§23](23-coding-agents.md).
- **Where it came from:** Andrej Karpathy proposed it around Feb 2026 as the disciplined successor to his own "vibe coding" (Feb 2025: prompting without reading the code). Simon Willison's "Agentic Engineering Patterns" guide (Mar 2026) developed it.
- **Status:** established. It is less a new layer than the whole stack applied to one domain, building software.

### The rest of the label zoo

| Label | Origin | What it means | Status |
|---|---|---|---|
| **Spec-driven development** | Kiro, GitHub Spec Kit (2025); Böckeler's analysis (Oct 2025) | Write specs (requirements → design → tasks) and let agents implement them. Variants: spec-first, spec-anchored, spec-as-source | Established buzzword; definition still shifting |
| **Compound engineering** | Kieran Klaassen, Every (2025) | Plan → Work → Review → Compound: each lesson is written back into docs and rules so the next run is better. Most time goes to planning and review | Moderate. A named form of the ratchet |
| **Eval-driven development** | arXiv 2411.13768 (Nov 2024) | Write evals first, like TDD for LLM features | Evals are established; "evals first" is contested. Practitioners such as Hamel Husain recommend error analysis on real traces first ([§26](26-evals.md)) |
| **Memory engineering** | Vendors and books, 2026 | Designing what agents remember and how | Niche. Really a sub-field of context engineering ([§17](17-memory.md)) |
| **RL environments / "environment engineering"** | 2025 industry buildout | Sandboxed copies of real software plus verifiers, used to post-train models and to evaluate them | RL environments are a real and well-funded industry; the label is niche ([§29](29-adapting-models.md)) |
| **Agent experience (AX)** | Mathias Biilmann, Netlify (Jan 2025) | Designing products and APIs so agents can use them, by analogy with developer experience (DX) | Real idea, mostly vendor-driven |
| **12-factor agents** | Dex Horthy, HumanLayer (2025) | Principles for production agents: own your prompts, own your context window, small focused agents, and others | Influential practitioner guide |
| **Forward-deployed engineering** | Long-standing role, revived in AI | Engineers embedded with customers who build the last mile of AI systems | A role, not a technique. It got its own AI Engineer World's Fair track in 2026 |

### How to tell a discipline from a buzzword

Apply four tests to any new "X engineering":

1. **Does it name a distinct bottleneck?** Context engineering does: the attention budget. A label that just renames "doing it well" fails.
2. **Does it have its own artifacts?** For example a progress file, AGENTS.md, a stop-condition checker, or a checkpointer.
3. **Does it have its own failure modes?** Context rot, the ratchet left unturned, a loop that games its own tests.
4. **Can you teach its practices without naming a product?** If the only way to explain it is "use our tool," it is marketing.

Context and harness engineering pass all four. Loop engineering passes the first three and is working on the fourth. Graph engineering passes them, but as a description of control flow rather than a new layer.

### The skills underneath the labels

Labels change, but the competencies underneath them have stayed fairly stable. Each one is anchored to principles and sections:

| # | Competency | What it looks like in practice | Principles | Sections |
|---|---|---|---|---|
| 1 | **Model literacy** | Knowing what tokens, sampling, context limits, and thinking budgets do to quality, cost, and latency | P1, P4, P10 | [§02](02-how-llms-work.md)–[§04](04-reasoning-models.md) |
| 2 | **Context design** | Deciding what the model sees, in what order, at what level of detail; caching-aware layout | P2, P3 | [§16](16-context-engineering.md)–[§18](18-skills.md) |
| 3 | **Interface design for agents** | Tools, error messages, and docs written for a model reader: few, high-level, informative | P6, P11 | [§10](10-tool-use.md), [§15](15-protocols-mcp-a2a.md) |
| 4 | **Control-flow design** | Choosing between workflow, agent, graph, and loop; picking the least autonomy that works | P7 | [§11](11-agents.md)–[§14](14-graph-engineering.md), [§21](21-loop-engineering.md) |
| 5 | **Verification design** | Keeping checkers separate from makers, preferring computational sensors, placing humans where the stakes are | P8 | [§12](12-agentic-design-patterns.md), [§19](19-harness-engineering.md) |
| 6 | **Error analysis and evals** | Reading traces, labeling failures, building datasets and graders, measuring rates | P4 | [§26](26-evals.md), [§27](27-observability.md) |
| 7 | **Runtime engineering** | Sandboxes, durable execution, idempotent tools, checkpoints | P6, P8 | [§20](20-agent-runtime.md) |
| 8 | **Security thinking** | Assuming any text can be an instruction; least privilege; avoiding the lethal trifecta | P9 | [§32](32-security-guardrails.md), [§33](33-agent-identity.md) |
| 9 | **Cost engineering** | Token budgets, model routing, caching, spend caps | P10 | [§30](30-cost-latency-reliability.md), [§31](31-open-weights-self-hosting.md) |
| 10 | **Data skills** | Turning traces into datasets, labeling, flywheels | P4, P5 | [§28](28-data-flywheels.md), [§29](29-adapting-models.md) |
| 11 | **Product judgment** | Picking problems where probabilistic output is acceptable; designing for verification and trust | P4, P8 | [§35](35-ai-ux.md), [§36](36-product-thinking.md) |
| 12 | **Taste for deletion** | Noticing when scaffolding has stopped helping, and removing it | P12 | [§19](19-harness-engineering.md), [§37](37-why-x-over-y.md) |

### If you come from data engineering

Data engineering habits map closely onto these skills, which gives data engineers a real head start:

| Data engineering habit | AI engineering equivalent |
|---|---|
| Idempotent, replayable pipeline steps | Durable execution and idempotent tools ([§20](20-agent-runtime.md)) |
| The log as source of truth; tables as derived views | The session as an append-only event log; context as a derived view ([§20](20-agent-runtime.md), [§16](16-context-engineering.md)) |
| DAG orchestration (Airflow, dbt) | Graph engineering, except agent graphs have cycles ([§14](14-graph-engineering.md)) |
| Data quality tests and contracts | Evals, structured outputs, schemas as contracts ([§26](26-evals.md), [§06](06-structured-outputs.md)) |
| Lineage and observability | Tracing and OTel GenAI spans ([§27](27-observability.md)) |
| Indexes, pruning, and "skip work" | Retrieval, reranking, progressive disclosure ([§08](08-embeddings-and-search.md), [§18](18-skills.md)) |
| Governance in the catalog, not in each tool | Permissions in the harness, not in the prompt ([§32](32-security-guardrails.md)) |
| Cost as a dial (warehouse sizing, latency vs. freshness) | Model routing, thinking budgets, caching ([§30](30-cost-latency-reliability.md)) |

The biggest adjustment is P4. A data pipeline is either right or wrong, but an LLM feature is right *at some rate*. Getting used to measuring rates instead of asserting correctness is most of the mental shift.

## Comparison

**All the labels at a glance**

| Label | Bottleneck it names | Typical artifacts | First used | Status (Oct 2026) |
|---|---|---|---|---|
| Prompt engineering | The words | Prompt templates, few-shot examples | 2020 | Established; now a subset of context engineering |
| Flow engineering | One-shot generation | Multi-stage test-driven flows | Jan 2024 | Precursor |
| Context engineering | The attention budget | Retrieval, memory, compaction, skills | Apr–Jun 2025 | Established |
| Harness engineering | The system around the model | AGENTS.md, hooks, sandboxes, linters, progress files | Nov 2025 – Feb 2026 | Established |
| Loop engineering | Human prompting attention | Loop drivers, stop-condition checkers, automations | Jul 2025 (practice), Jun 2026 (label) | Emerging |
| Graph engineering | Implicit control flow | State graphs, checkpointers, interrupts | 2024 (practice), Jul 2026 (label) | Niche label, established practice |
| Agentic engineering | Unreviewed agent code | Review practices, git discipline, tests | Feb 2026 | Established |
| Spec-driven development | Ambiguous intent | Specs, task lists, "constitutions" | 2025 | Buzzword, still shifting |
| Compound engineering | Lessons that don't stick | Rule and doc updates after every task | 2025 | Moderate |
| Eval-driven development | Untested changes | Eval suites written first | Nov 2024 | Contested |

**Discipline vs. buzzword: the four tests applied**

| Label | Distinct bottleneck | Own artifacts | Own failure modes | Teachable without a product |
|---|---|---|---|---|
| Context engineering | Yes | Yes | Yes | Yes |
| Harness engineering | Yes | Yes | Yes | Yes |
| Loop engineering | Yes | Yes | Yes | Partly |
| Graph engineering | Partly (control flow) | Yes | Yes | Yes |
| Memory engineering | No (part of context) | Partly | Partly | Partly |
| Agent experience (AX) | Partly | Partly | No | Partly |

## What it didn't solve

A map is a snapshot. New labels will keep appearing as the bottleneck moves again, and some will matter while others won't. The four tests and the twelve principles are how you sort them. For what's emerging now (agentic commerce protocols, personal "claw" agents, proactive agents, continual learning), see the [Frontier Watchlist](frontier.md). To review everything, start with the [Cheat Sheet](cheat-sheet.md).

## Check your understanding

**Q: Why do new "X engineering" labels keep appearing?**

Because each label marks where the bottleneck moved. As models absorb more of one layer's work (P12), the hard part moves outward: from the words, to everything the model sees, to the system around the model, to the human attention needed to drive it. The old layer doesn't disappear; it becomes a component of the new one.

**Q: How are prompt, context, harness, and loop engineering related?**

They nest. The prompt is part of the context. The harness produces the context on every call, along with tools, sandboxes, and feedback. The loop drives the harness without a human prompting each run. Graph engineering sits beside this stack, because it is about who owns control flow (P7) rather than what the model sees.

**Q: Is "graph engineering" the same as GraphRAG?**

No. Graph engineering means structuring agent control flow as a state machine: nodes, edges, cycles, checkpoints ([§14](14-graph-engineering.md)). GraphRAG builds a knowledge graph of entities and relationships from documents in order to answer whole-corpus questions ([§09](09-rag.md)). They share a word and nothing else.

**Q: How would you decide whether a new label is a real discipline?**

Ask whether it names a distinct bottleneck, has its own artifacts, has its own failure modes, and can be taught without naming a product. Context and harness engineering pass all four. A label that only renames "doing it carefully", or can only be explained through one vendor's tool, is marketing.

**Q: Why is loop engineering called "emerging" when people have run agents in loops since 2023?**

The practice is old and real: AutoGPT looped, and Huntley's Ralph loop (Jul 2025) is a bash `while` loop. What's new is a named set of practices around it, such as separate stop-condition checkers, back pressure, parallel worktrees, and scheduled automations. That set was only named in mid-2026 and overlaps heavily with harness engineering. Its boundaries are still being worked out.

**Q: Which AI engineering skill do most newcomers underestimate?**

Verification and evals (P4, P8). Making a model produce something is easy. Knowing whether it is right, at what rate, and catching regressions when the model or prompt changes is where most of the engineering goes. Error analysis on real traces is the skill that separates working systems from demos.

**Q: What is the biggest mental shift for someone coming from data engineering?**

Accepting that correctness is a rate, not a fact (P4). Many habits carry over directly: idempotency becomes durable execution, the log becomes the session event log, DAGs become graphs, and quality tests become evals. But an LLM feature passes "94% of the time on this distribution," so you have to measure, not assert.

## Takeaways

- Every "X engineering" label names the place where the bottleneck moved.
- The core labels nest: prompt ⊂ context ⊂ harness ⊂ loop. Graph engineering is a side branch about control flow.
- Context and harness engineering are established. Loop and graph engineering are 2026 labels for practices that already existed.
- Agentic engineering is the whole stack applied to building software, not a new layer.
- Test a label: distinct bottleneck, own artifacts, own failure modes, teachable without a product.
- The durable skills are context design, interface design, control-flow design, verification, evals, runtime, security, cost, data, product judgment, and the willingness to delete scaffolding.
- Data engineering habits transfer well. The big shift is measuring correctness as a rate.

## Sources

- Anthropic, "Effective context engineering for AI agents," Sep 29, 2025: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Simon Willison, "Context engineering," Jun 27, 2025: https://simonwillison.net/2025/Jun/27/context-engineering/
- LangChain, "Context engineering for agents," Jul 2, 2025: https://blog.langchain.com/context-engineering-for-agents/
- HumanLayer, "12-factor agents": https://github.com/humanlayer/12-factor-agents
- Anthropic, "Effective harnesses for long-running agents," Nov 26, 2025: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Mitchell Hashimoto, "My AI adoption journey," Feb 5, 2026: https://mitchellh.com/writing/my-ai-adoption-journey
- OpenAI, "Harness engineering: leveraging Codex in an agent-first world," Feb 11, 2026: https://openai.com/index/harness-engineering/
- LangChain, "The Anatomy of an Agent Harness," Mar 10, 2026: https://blog.langchain.com/the-anatomy-of-an-agent-harness/
- Birgitta Böckeler, "Harness engineering," martinfowler.com, Apr 2, 2026: https://martinfowler.com/articles/harness-engineering.html
- Geoffrey Huntley, "Ralph Wiggum as a 'software engineer'," Jul 14, 2025: https://ghuntley.com/ralph/
- Geoffrey Huntley, "everything is a ralph loop," Jan 17, 2026: https://ghuntley.com/loop/
- Addy Osmani, "Loop Engineering," Jun 7, 2026: https://addyosmani.com/blog/loop-engineering/
- LangChain, "3 Years of Graph Engineering with LangGraph," Jul 22, 2026: https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph
- Ridnik, Kredo, Friedman, "Code Generation with AlphaCodium: From Prompt Engineering to Flow Engineering," Jan 2024: https://arxiv.org/abs/2401.08500
- Every, "Compound engineering": https://every.to/chain-of-thought/compound-engineering-how-every-codes-with-agents
- Eval-driven development, arXiv 2411.13768: https://arxiv.org/abs/2411.13768
- AI Engineer World's Fair 2026 tracks: https://ai.engineer/wf/llms.md
