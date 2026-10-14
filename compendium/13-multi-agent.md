# 13. Multi-Agent Systems

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

Multi-agent ideas showed up almost as soon as ChatGPT did. CAMEL (Mar 2023) had two role-playing agents, a "user" and an "assistant," talk each other through a task. Microsoft's AutoGen (Aug 2023) turned "multi-agent conversation" into a framework. By 2025 the idea was in production: OpenAI's Agents SDK (Mar 2025) shipped handoffs and agents-as-tools, and Anthropic's Research feature (Jun 2025) ran a lead agent with parallel subagents. Then, from late 2025 into 2026, came the evidence: controlled experiments and production write-ups showing when it helps. [§12](12-agentic-design-patterns.md) left a question open. Orchestrator-workers and subagents appear in every pattern catalog, but does splitting work across agents actually pay? This section answers with mechanism and evidence, and ends with a decision rule.

## Why this exists

A **multi-agent system** is several LLM instances, each with its own context (system prompt, conversation history, tools), coordinated by code or by another LLM. On the wire, a second agent is just a second, separate `messages` list (P2). Anthropic's January 2026 guidance names three situations in which several agents beat one. Each follows from a principle:

1. **Parallelism.** Independent subtasks run at the same time, which cuts wall-clock latency but not total compute (P10). In Anthropic's Research system, parallel subagents and parallel tool calls cut research time by up to 90% on complex queries.
2. **Context isolation.** A context window is finite and rots as it fills (P3). A subagent can burn tens of thousands of tokens reading and searching, then hand back a distilled summary, "often 1,000-2,000 tokens," so the lead's context stays clean. As the Research write-up puts it, "The essence of search is compression."
3. **Specialization.** Different roles need different prompts, tools or models. An agent juggling 20+ tools across unrelated domains picks the wrong one more often.

Underneath all three, more agents is a way to spend more tokens productively. In Anthropic's BrowseComp analysis, token usage alone explained 80% of the variance in performance. One window caps how much one agent can usefully spend, and several windows lift that cap.

The counter-forces come from the same principles:

- **Handoffs lose information.** Every handoff compresses context, because the receiver sees a brief rather than the history (P2).
- **Errors compound.** They compound across agents just as they do across steps (P8).
- **Tokens multiply.** Anthropic measured agents at about 4× the tokens of chat, and multi-agent systems at about 15× (P10).

The rest of this section is about where the benefits outweigh those costs.

## How it works (under the hood)

### What a subagent is on the wire

In the most common design, a subagent is a tool whose implementation runs another agent loop. The lead model emits a tool call. The harness runs it as a fresh loop with its own `messages` list and returns only the final summary as a `tool_result` (P6). One assistant turn can contain several `tool_use` blocks, so the lead can fan out in a single step:

```json
[
  {"role": "assistant", "content": [
    {"type": "tool_use", "id": "toolu_01", "name": "spawn_subagent",
     "input": {"objective": "Pricing models of Snowflake, Databricks, BigQuery",
               "output_format": "3 bullets with source URLs", "boundaries": "read-only"}},
    {"type": "tool_use", "id": "toolu_02", "name": "spawn_subagent",
     "input": {"objective": "Streaming-ingestion options of the same three",
               "output_format": "3 bullets with source URLs", "boundaries": "read-only"}}
  ]},
  {"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "toolu_01", "content": "- ... (~300 tokens)"},
    {"type": "tool_result", "tool_use_id": "toolu_02", "content": "- ... (~300 tokens)"}
  ]}
]
```

Both results go back in *one* user message, which is the Anthropic Messages API contract for parallel tool use. OpenAI's Responses API (`function_call` / `function_call_output` items) and Google's Gemini API (`functionCall` / `functionResponse` parts) carry the same idea in different shapes. The harness side, with a stub model:

```python
import json
from concurrent.futures import ThreadPoolExecutor


def call_model(system: str, messages: list) -> str:
    """Stub for client.messages.create(model=..., system=system, messages=messages).
    Each call gets its OWN messages list: that is what makes it a separate agent."""
    if system.startswith("Plan"):
        return json.dumps([{"objective": f"Find the {t} of Snowflake, Databricks, BigQuery",
                            "output": "3 bullets, each with a source URL",
                            "boundaries": "public docs only; read-only"}
                           for t in ("pricing model", "streaming ingestion", "governance features")])
    if system.startswith("Research"):
        brief = json.loads(messages[0]["content"])
        return f"- findings on: {brief['objective']}"  # a real subagent compresses ~30k -> ~300
    return "SYNTHESIS\n" + messages[0]["content"]


def run_subagent(brief: dict) -> str:
    # Fresh context: the subagent sees only its brief, not the lead's history (P2, P3).
    # A real subagent runs its own tool loop here (search, fetch, read). Read-only tools.
    try:
        return call_model("Research only. Change nothing. Return a short summary.",
                          [{"role": "user", "content": json.dumps(brief)}])
    except Exception as err:      # one failed worker must not sink the whole run
        return f"- FAILED: {brief['objective']} ({err})"


def orchestrate(question: str, max_subagents: int = 4) -> str:
    plan = call_model("Plan independent subtasks as JSON briefs.",
                      [{"role": "user", "content": question}])
    briefs = json.loads(plan)[:max_subagents]            # cap fan-out: cost scales with it
    with ThreadPoolExecutor(max_workers=max(1, len(briefs))) as pool:
        findings = list(pool.map(run_subagent, briefs))  # concurrent; results keep order
    # Single writer: only the lead turns the findings into the final artifact.
    return call_model("Synthesize the findings into one answer with citations.",
                      [{"role": "user", "content": "\n".join(findings)}])


print(orchestrate("Compare three warehouses for a streaming-heavy team."))
```

Two things make this *multi-agent* rather than "one agent calling functions." Each subagent starts from an empty context that holds only its brief, and only the lead writes the final artifact. Platforms now package this pattern. In Claude Managed Agents' multiagent orchestration **(Preview)**, a session's agent delegates to subagents that run in isolated threads (one level deep, at most 25 child threads at a time), or writes a "dynamic workflow" that runs many agents in phases.

### Topologies: one taxonomy, many names

Google Research's "Towards a Science of Scaling Agent Systems" (Kim et al., arXiv Dec 2025; blog Jan 28, 2026) defines five canonical architectures. Frameworks use their own names for the same shapes:

| Google architecture | Shape | Practitioner names | What Google measured |
|---|---|---|---|
| Single-agent (SAS) | One agent, one memory stream, steps in sequence | Single-threaded agent (Cognition); the loop of [§11](11-agents.md) | Baseline; best on sequential work |
| Independent | N agents in parallel that never talk; results merged at the end | Sectioning/voting (Anthropic 2024); map-reduce; "agent teams" on disjoint partitions (Anthropic 2026) | Errors amplified up to 17.2×, since nobody checks anybody |
| Centralized | Hub and spoke: an orchestrator delegates, workers report back, the orchestrator synthesizes | Supervisor (LangGraph); orchestrator-workers / orchestrator-subagent (Anthropic); agents-as-tools (OpenAI); subagents (LangChain) | +80.9% on Finance-Agent; error amplification held to 4.4× |
| Decentralized | Peer-to-peer mesh; agents message each other and reach consensus (for example, debate rounds) | Network (LangGraph); swarm (OpenAI Swarm, langgraph-swarm); shared state and message bus (Anthropic 2026) | +9.2% on dynamic web navigation (paper v3); hurt sequential planning |
| Hybrid | Orchestrator plus limited peer-to-peer links | Supervisor with peer messaging; orchestrator with a shared store for one subtask | Carries both overheads |

Two of these names need care:

- **Hierarchical is still centralized.** LangGraph's 2024 docs listed network, supervisor, supervisor-with-tool-calling, and hierarchical (a supervisor of supervisors). A hierarchy is a tree of hubs, so it remains a centralized design.
- **"Swarm" doesn't mean parallel.** The word suggests many agents working at once. In OpenAI Swarm and langgraph-swarm, it means agents *handing control to one another*, with only one active at a time. It's decentralized routing over time, not parallelism.

### Subagents (agents-as-tools) vs handoffs

These are the two delegation primitives that every framework now ships.

- **Agents-as-tools (subagents).** A manager calls a specialist the way it calls a tool. The specialist runs in isolation and returns a result. The manager keeps the conversation and writes the final answer. OpenAI's Agents SDK exposes this as `Agent.as_tool()`.
- **Handoffs.** Control *transfers*: the specialist becomes the active agent and answers the user directly. In the Agents SDK, the model sees a handoff as a tool named `transfer_to_<agent_name>`. By default the new agent "gets to see the entire previous conversation history," and an `input_filter` can trim it.

The lineage starts with OpenAI **Swarm** (Oct 2024), labelled "experimental, educational," whose only primitives were agents and handoffs. In Swarm, a handoff swapped the system prompt but kept the chat history. Its README now says it "is now replaced by the OpenAI Agents SDK" (Mar 2025), "a production-ready evolution of Swarm."

| | Agents-as-tools (subagents) | Handoffs |
|---|---|---|
| Who owns the conversation | The manager, always | Whoever was last handed control |
| What the specialist sees | Only its brief (strong isolation, P3) | Full history by default |
| State across turns | Stateless; re-invoked each time | The active agent persists |
| Model calls (LangChain's comparison) | One extra per request, since results flow back through the manager | Fewer; stateful patterns save 40–50% of calls on repeat requests |
| Best for | Bounded subtasks, parallel fan-out, a single owner of the answer | Triage to a specialist who should talk to the user |
| Typical failure | Vague briefs; summaries drop details | Wrong transfer; history bloat; agents bouncing control back and forth |

### Evidence 1: Anthropic's multi-agent research system (Jun 13, 2025)

Anthropic's Research feature uses orchestrator-workers. A lead agent plans and saves its plan to memory, because contexts beyond 200,000 tokens were truncated. It then spawns subagents that search in parallel, evaluate results with interleaved thinking, and report back. Finally, a CitationAgent attributes each claim to a source. The reported numbers:

- A system with a Claude Opus 4 lead and Claude Sonnet 4 subagents **outperformed single-agent Opus 4 by 90.2%** on an internal research eval. The example task, listing the board members of every IT company in the S&P 500, splits naturally into pieces.
- Three factors explained 95% of the variance on BrowseComp, and **token usage alone explained 80%**. The other two were the number of tool calls and the model choice.
- Agents use **about 4×** the tokens of chat, and multi-agent systems **about 15×**. In the authors' words, "multi-agent systems require tasks where the value of the task is high enough to pay for the increased performance."
- **Poor fit:** tasks "that require all agents to share the same context or involve many dependencies between agents." In particular, "most coding tasks involve fewer truly parallelizable tasks than research."

The engineering lessons travel well:

- **Teach the orchestrator to delegate.** Each brief needs an objective, an output format, guidance on tools and sources, and clear task boundaries. Vague briefs such as "research the semiconductor shortage" led subagents to duplicate one another's searches.
- **Scale effort to the query.** Simple fact-finding needs 1 agent and 3–10 tool calls. Comparisons need 2–4 subagents. Complex research needs 10 or more. Early versions spawned 50 subagents for simple queries.
- **Parallelize twice.** The lead spawns 3–5 subagents at once, and each subagent runs 3+ tools at once.
- **Avoid the "game of telephone."** Have subagents write outputs to a filesystem and pass references back instead of full content.
- **Engineer for state.** Use resumable execution, full tracing, and rainbow deployments that keep old and new versions running side by side so in-flight agents don't break. Fan-out was synchronous, so the lead waited for the slowest subagent.

### Evidence 2: Cognition, "Don't Build Multi-Agents" (Jun 12, 2025) and the 2026 follow-up

Walden Yan's post, published the day before Anthropic's, set out two principles:

1. "Share context, and share full agent traces, not just individual messages."
2. "Actions carry implicit decisions, and conflicting decisions carry bad results."

His example splits "build a Flappy Bird clone" into a background and a bird. One subagent builds a Super Mario-style background, while the other builds a bird in a different visual style. Each acted sensibly on assumptions the other couldn't see, and copying the original task to both doesn't fix that. His default was a single-threaded linear agent, plus, for very long tasks, a model dedicated to compressing history into key decisions. He also noted that Claude Code's subagents, as of June 2025, were usually asked only to answer a question, not to write code, and never worked in parallel with the main agent.

The April 22, 2026 follow-up, "Multi-Agents: What's Actually Working," kept that diagnosis for "parallel-writer swarms," which still see little real adoption. It reported a narrower class that works: "multiple agents contribute intelligence to a task while writes stay single-threaded." The examples:

- a clean-context code reviewer looping with the coder;
- a stronger "smart friend" model the primary agent can consult;
- a manager Devin that splits work across child Devins, which Yan calls "map-reduce-and-manage."

It called unstructured swarms "mostly a distraction" and said the open problems "are all communication problems."

### Evidence 3: Google, "Towards a Science of Scaling Agent Systems" (Dec 2025; blog Jan 28, 2026)

Earlier comparisons mixed up architecture effects with differences in prompts, tools and budgets. Google held those fixed and varied only the architecture. The blog version covers 180 configurations, five architectures, four benchmarks, and three model families (OpenAI, Google, Anthropic). The results:

- **Alignment.** Centralized coordination improved parallelizable financial reasoning (Finance-Agent) by **80.9%**. On sequential planning (PlanCraft), every multi-agent variant **lost 39–70%**.
- **The coordination tax.** In the paper's words, multi-agent systems "incur an unavoidable coordination tax in which the global context must be compressed into inter-agent messages." Messages use up each agent's token budget and split reasoning that needed to stay in one place. The tax rises with tool count, as on a 16-tool business workflow.
- **The capability ceiling.** Once a single agent already does well (above about 45% accuracy, in the April 2026 revision), extra agents give negative returns.
- **Error amplification.** Independent agents amplified errors 17.2×. Centralized systems held amplification to 4.4×, because the orchestrator acts as a "validation bottleneck."
- **Prediction.** A model built on measurable task properties, such as decomposability and tool count, picked the best architecture for 87% of held-out configurations.

The April 2026 arXiv revision (v3) expands the study to 260 configurations and six benchmarks, and reports +80.8% and −70.0% at the two extremes.

### The decision rule

> **Default to one agent. Use multiple agents when the work is breadth-first, parallelizable, read-heavy and high-value. Keep writes single-threaded.**

Each clause rests on a mechanism:

- **Breadth-first and parallelizable.** Gains appear only when the task breaks into independent pieces (Google's +81% vs −70%). Decompose by *context boundary*, not by job title (Anthropic, Jan 2026). One agent should write a feature *and* its tests, because it already holds the context. Splitting work into planner, implementer, tester and reviewer agents produced subagents that "spent more tokens on coordination than on actual work."
- **Read-heavy.** Reads don't commit decisions that other agents must agree with, and summaries of reads merge cleanly. Writes are where implicit decisions collide (Cognition's principle 2). It's the rule you'd apply to any table without a transaction manager: concurrent readers are safe, but concurrent writers need coordination you probably don't have.
- **High-value.** At 3–10× the tokens of a single agent (Anthropic, Jan 2026), and about 15× chat, the answer has to be worth the spend (P10).
- **Single-threaded writes.** One agent owns every change to shared state: code, files, records, the final report. The other agents contribute findings, reviews or advice.

```text
Is one well-tooled agent failing on your evals?
 ├─ no ───────────────────────────────────────► single agent (+ compaction, tool search)
 └─ yes: does the work split into independent, mostly read-only pieces?
      ├─ no (sequential, tightly coupled) ───► single agent; fix its context instead (§16)
      └─ yes: is the result worth 3-15x the tokens?
           ├─ no ───────────────────────────► single agent, or a cheap fan-out in code
           └─ yes ──────────────────────────► orchestrator + read-only subagents,
                                               one writer, central verification
```

### Failure modes

- **Conflicting implicit decisions.** Parallel writers each make reasonable but incompatible choices about style, schemas or edge cases, and the merge step can't reconcile them. Fix: use a single writer, and share the plan and decisions through plan files and todo lists.
- **Telephone-game context loss.** Every hop compresses. The lead's brief drops intent, and the subagent's summary drops detail. Fix: use structured briefs (objective, output format, tools, boundaries), pass artifacts by reference, and share full traces where they fit.
- **Cost blowups.** Fan-out multiplies tokens. Over-spawning, endless searching, and reactive loops in shared-state designs (A responds to B, which responds to A) burn budget without converging. Fix: set effort-scaling rules, cap subagent count and tokens, enforce hard spend limits, and define termination conditions.
- **Unchecked error propagation.** Without a central verifier, one agent's mistake flows straight into the result: 17.2× amplification for independent agents.
- **Stragglers and opacity.** Synchronous fan-out waits on the slowest worker, and nondeterministic paths make bugs hard to reproduce. You need per-agent tracing ([§27](27-observability.md)) and end-state evals ([§26](26-evals.md)).

### A2A, briefly

Everything above happens *inside* one system you control. When agents built by different teams or vendors, on different frameworks, need to work together, you need a wire protocol. **A2A (Agent2Agent)**, launched by Google in April 2025 and donated to the Linux Foundation, fills that role:

- Agents publish **Agent Cards** that describe their capabilities.
- They exchange **tasks** and stream progress.
- They stay "opaque": they don't share memory, tools or internal logic.

Its docs say it is "not a sub-agent or tool-call protocol." Your subagents use your framework's primitives, and A2A is for crossing organizational boundaries. The usual framing is that MCP connects agents to tools and A2A connects agents to agents. A2A now sits in the Agentic AI Foundation alongside MCP. See [§15](15-protocols-mcp-a2a.md).

## Comparison

**Topologies.**

| Topology | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Single agent | One loop, one context | Full context continuity; cheapest; easiest to debug | One window; serial | The default; sequential or tightly coupled work, including most coding |
| Centralized (orchestrator + subagents) | Lead delegates briefs, synthesizes reports | Parallel reading, context isolation, central verification | Orchestrator is an information bottleneck; quality depends on the briefs | Breadth-first research, multi-aspect review |
| Independent fan-out | Parallel workers, merged in code | Simple; maximum parallelism | No cross-checking | Truly disjoint partitions, with verification at the end |
| Handoffs (swarm) | Control passes between specialists | Focused prompts; the specialist talks to the user; few calls | Misroutes; history bloat | Triage and support-style routing |
| Decentralized (peer mesh, shared state) | Agents read and write a shared store or message each other | No single point of failure; findings flow directly | Duplicate work, reactive loops, hard to trace | Collaborative exploration with explicit termination |
| Generator–verifier pair | Maker plus separate checker | Catches what the maker misses | Rubber-stamps without explicit criteria | Quality-critical outputs ([§12](12-agentic-design-patterns.md)) |

**The evidence at a glance.**

| Source | Setting | Finding | Implication |
|---|---|---|---|
| Anthropic Research (Jun 2025) | Opus 4 lead + Sonnet 4 subagents | +90.2%; tokens explain 80% of variance; ~15× chat tokens | Multi-agent buys token capacity; worth it for high-value breadth-first work |
| Cognition (Jun 2025) | Production coding agents | Parallel writers make conflicting implicit decisions | Single-threaded by default |
| Google (Dec 2025 / Jan 2026) | 180 controlled configurations | +81% parallelizable, −39 to −70% sequential; 17.2× vs 4.4× error amplification | Match topology to task structure; centralize verification |
| Anthropic guidance (Jan and Apr 2026) | Customer deployments | 3–10× tokens; decompose by context; start with orchestrator-subagent | Use multi-agent only on specific triggers |
| Cognition (Apr 2026) | Devin, Windsurf | Reviewer loops, smart friend and manager/children work; swarms don't | Many contributors, one writer |

## What it didn't solve

The decision rule tells you *which* topology to pick, but it doesn't make that topology robust. Control flow across steps and agents still lives in prompts and in-process loops. Suppose a subagent crashes at minute forty, a human has to approve a write before it lands, or a deploy happens mid-run. A plain loop has nowhere to persist where it was, and no way to resume. You need explicit structure: named states, fixed and conditional edges, checkpoints, and the ability to pause and resume.

→ Next: [§14 Graph Engineering](14-graph-engineering.md)

## Check your understanding

**Q: Why did token usage explain most of the performance variance in Anthropic's research system, and what does that say about why multi-agent helps?**

Hard research needs a lot of reading, and one agent can usefully spend only as many tokens as its context window allows before it fills and rots (P3). Subagents each get a fresh window, so the system can spend far more tokens in parallel and pass only compressed findings to the lead. Multi-agent works here mainly as a way to scale token spend. The price is about 15× the tokens of chat, so it pays only when the work is valuable and splits into breadth-first pieces.

**Q: What would happen if you split "build a feature" into planner, implementer, tester and reviewer agents?**

Each handoff compresses context. The tester doesn't know why the implementer made its choices, and the reviewer never saw the exploration, so information degrades at every hop. Anthropic saw subagents split this way spend more tokens on coordination than on the work itself. Decompose by context boundary instead: one agent writes the feature and its tests, and a separate verifier black-box tests the result, since verification needs little context. Splitting by role makes sense only when the roles genuinely need different, isolated context.

**Q: Subagents (agents-as-tools) vs handoffs: when would you choose each?**

With subagents, the manager keeps control. Each specialist sees only its brief, runs in isolation and returns a result, which gives strong context isolation, parallel fan-out and one owner of the final answer, at the cost of an extra model call per request. With handoffs, control moves to the specialist, who sees the history by default and talks to the user directly, which takes fewer calls and works well for triage. Choose subagents for bounded, parallel, read-only work. Choose handoffs when routing to a specialist is the workflow. Avoid handoffs when misroutes are costly or histories are long.

**Q: Why is "read-heavy" part of the decision rule, and not just "parallelizable"?**

Write-heavy work can look perfectly parallelizable on paper and still fail, because every write commits implicit decisions about style, schema and edge cases that other writers can't see (Cognition's Flappy Bird example). Reads commit nothing, and their summaries merge cleanly. It's the many-readers, one-writer rule from any data system without a transaction manager. Parallel writers work only when partitions are truly disjoint and a verification step checks the merge.

**Q: What would happen if you added agents to a task a single agent already handles at 80% accuracy?**

Google found a capability ceiling: once a single agent is already strong (above about 45% in their revised study), extra agents bring negative returns. The coordination tax, meaning messages that eat each agent's token budget and fragmented reasoning, outweighs the little headroom left. You'd pay several times the tokens for the same or worse results. Spend the effort on the single agent's context, tools and verification instead.

**Q: A2A vs your framework's subagent API: why not use A2A for everything?**

A2A is a wire protocol for agents that are opaque to each other: they're built by different teams or vendors, find each other through Agent Cards, and exchange tasks without sharing memory or tools. Inside your own system you control both sides, so a framework primitive (a tool call that runs a subagent loop) is simpler, faster and easier to trace. A2A's own docs say it is "not a sub-agent or tool-call protocol." Use it when you cross an organizational or framework boundary, not for internal delegation.

## Takeaways

- A second agent is a second context. Isolation and parallelism are the benefits; lossy handoffs and multiplied tokens are the costs.
- Default to one agent. Go multi-agent for work that is breadth-first, parallelizable, read-heavy and high-value.
- Keep writes single-threaded: many contributors, one writer.
- Topology must match task structure: +81% on decomposable work, −39 to −70% on sequential work.
- Centralize verification. Independent agents amplified errors 17.2×, against 4.4× with an orchestrator.
- Delegation is only as good as the brief: objective, output format, tools and boundaries.
- Budget explicitly: about 15× chat tokens, caps on fan-out, and termination conditions.

## Sources

- Li et al., "CAMEL: Communicative Agents for 'Mind' Exploration of Large Language Model Society," Mar 2023: https://arxiv.org/abs/2303.17760
- Wu et al., "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation," Aug 2023: https://arxiv.org/abs/2308.08155
- Hadfield, Zhang et al. (Anthropic), "How we built our multi-agent research system," Jun 13, 2025: https://www.anthropic.com/engineering/multi-agent-research-system
- Walden Yan (Cognition), "Don't Build Multi-Agents," Jun 12, 2025: https://cognition.ai/blog/dont-build-multi-agents
- Walden Yan (Cognition), "Multi-Agents: What's Actually Working," Apr 22, 2026: https://cognition.ai/blog/multi-agents-working
- Kim et al. (Google Research), "Towards a Science of Scaling Agent Systems," arXiv 2512.08296 (v1 Dec 9, 2025; v3 Apr 8, 2026): https://arxiv.org/abs/2512.08296
- Google Research blog, "Towards a science of scaling agent systems: When and why agent systems work," Jan 28, 2026: https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/
- Cara Phillips (Anthropic), "When to use multi-agent systems (and when not to)," Jan 23, 2026: https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them
- Cara Phillips (Anthropic), "Multi-agent coordination patterns: Five approaches and when to use them," Apr 10, 2026: https://claude.com/blog/multi-agent-coordination-patterns
- Anthropic, "Effective context engineering for AI agents" (sub-agent architectures), Sep 29, 2025: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- OpenAI Agents SDK docs, "Agent orchestration" and "Handoffs": https://openai.github.io/openai-agents-python/multi_agent/ ; https://openai.github.io/openai-agents-python/handoffs/
- OpenAI Swarm repository (README notes replacement by the Agents SDK): https://github.com/openai/swarm
- LangChain docs, "Multi-agent" (subagents, handoffs, skills, router; call-count comparison): https://docs.langchain.com/oss/python/langchain/multi-agent
- LangGraph multi-agent concepts, 2024 version (network, supervisor, hierarchical): https://github.com/langchain-ai/langgraph/blob/0.2.60/docs/docs/concepts/multi_agent.md
- langgraph-swarm README: https://github.com/langchain-ai/langgraph-swarm-py
- Claude Managed Agents docs, "Multiagent orchestration" (beta): https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration
- Google Developers Blog, "Announcing the Agent2Agent Protocol (A2A)," Apr 9, 2025: https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/
- A2A Protocol: https://a2a-protocol.org/latest/
