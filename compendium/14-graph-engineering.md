# 14. Graph Engineering: Orchestration as State Machines

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

The practice is from early 2024. LangChain released LangGraph on January 17, 2024, as a library for building "cyclical graphs, often needed for agent runtimes". The label is from July 2026. It caught on over one weekend on X, and LangChain's post "3 Years of Graph Engineering with LangGraph" (Sydney Runkle and Harrison Chase, Jul 22, 2026) calls it a buzzword and "the latest name for a well established approach". So treat "graph engineering" as a niche label for an established practice. The post's title says three years, but the library's public launch was January 2024. [§13](13-multi-agent.md) left a problem: once a system has several agents, branches, retries and human approvals, its control flow needs an explicit structure, and its state has to survive crashes and pauses. This section covers that structure.

## Why this exists

Three principles set up the problem.

- **The autonomy dial works per step, not per system (P7).** A support bot always classifies first, and a compliance flow always needs approval before an external action. Inside those fixed stages, the model still judges open-ended content. You want code to own the transitions you know and the model to own the ones you don't.
- **Errors compound (P8).** At a per-step success rate p over n steps, a run succeeds with probability p^n. So you need verification steps, checkpoints to resume from, and humans at the risky points. In a plain `while` loop the state lives in local variables. A crash means starting over, and a human approval means a process blocking for hours.
- **The model is stateless (P2).** All state lives in your code. If it is implicit, scattered across variables, you can't persist, inspect or replay it.

You have solved a version of this before. Airflow and dbt make dependencies explicit, persist run state and retry failed tasks. Agent orchestration needs the same explicitness with two twists: the graph must allow **cycles**, and some steps produce **probabilistic** output.

## How it works (under the hood)

### Three parts: state, nodes, edges

A **state machine** is a system that is always in one of a set of named steps and moves between them by explicit rules. An agent graph has three parts:

- **State.** A typed dictionary shared by every step, such as `{"draft": str, "attempts": int}`. Steps don't overwrite the whole state. Each returns a *partial update*, and a **reducer** decides how the update merges in. The default reducer overwrites the key. An `add` reducer appends to a list. Reducers matter most when two steps run in parallel and write the same key: without a merge rule, one write would silently win. It is the same idea as a per-column rule in a `MERGE` statement.
- **Nodes.** Functions from state to update. A node can be deterministic code, a single LLM call, a tool call, or a whole agent with its own internal loop (LangChain, Jul 2026). That range is the autonomy dial again, now set node by node.
- **Edges.** They decide what runs next. A **fixed edge** always goes from A to B. A **conditional edge** runs a routing function on the state and returns the name of the next node. Virtual `START` and `END` nodes mark entry and exit.

Here is the running example, a summary that a checker validates and a human approves:

```text
 START ──> draft ──> check ──ok──> approve ──yes──> END
             ^         │              │
             └──fail───┘              │ (interrupt: wait for a human)
             ^                        │
             └─────────no─────────────┘
```

### The runtime: super-steps and a step limit

LangGraph's runtime is modeled on Google's Pregel graph-processing system. Execution moves in discrete **super-steps**: every ready node runs (in parallel if there are several), then their updates are applied through the reducers, and a **checkpoint** (a snapshot of the state) is written at the boundary. Since v1.0.6 the default **recursion limit** is 1,000 super-steps, after which the run raises `GraphRecursionError`. Lower it per run with `config={"recursion_limit": 25}`.

### Why agent graphs have cycles

Airflow and dbt build **DAGs** (directed acyclic graphs). They are acyclic for a reason: a dependency graph of transformations with a cycle has no valid execution order. In a DAG each task runs once per run, and a retry re-runs the same node rather than looping through the graph. LangChain's January 2024 launch post made the same contrast: its earlier chains were "directed acyclic graphs (DAGs) - as are most data orchestration frameworks", and LangGraph existed to add cycles.

Agents need cycles because looping is the work itself. An agent retries failed tool calls, asks the user for missing information, revises an answer after validation, and calls tools until it has enough context (LangChain, Jul 2026). The consequence is the key tradeoff. **In a DAG, the structure guarantees termination. In a cyclic graph, termination is a runtime decision, often the model's, so you have to enforce it yourself** with counters, recursion limits and budgets (P8, P10).

### A loop is a degenerate graph

The agent loop from [§11](11-agents.md) is a graph with two nodes and one conditional edge:

```text
 START ──> model ──(tool requested?)──yes──> tools
             ^                                 │
             └─────────────────────────────────┘
             └──no──> END
```

LangChain quotes David Khourshid: "a loop is just a directed, cyclic graph", and LangChain's own agent loop runs on LangGraph. So loop vs graph is a question of how much structure you write down. Graph engineering means deciding which edges you fix in code and which the model chooses at runtime.

### A framework-free state machine

Strip away the framework and the mechanism is small. This sketch has nodes, a fixed edge, a conditional edge that closes a cycle, a checkpoint keyed by thread, and an interrupt that the next call resumes:

```python
CHECKPOINTS = {}  # thread_id -> {"state": ..., "next": ...}; a database table in production

class Interrupt(Exception): pass  # raised by a node to pause the run until a human answers

def draft(state):    # a node: in real life an LLM call (client.messages.create), a tool, or an agent
    n = state["attempts"] + 1
    return {"attempts": n, "draft": f"churn summary v{n}"}   # nodes return partial updates

def check(state):    # a deterministic verifier node (pretend v1 always fails)
    return {"ok": state["attempts"] >= 2}

def approve(state):  # human-in-the-loop node
    if state.get("answer") is None:
        raise Interrupt({"question": "Publish this?", "draft": state["draft"]})
    return {"approved": state["answer"], "answer": None}   # consume the human's answer

NODES = {"draft": draft, "check": check, "approve": approve}
EDGES = {"draft": lambda s: "check",                              # fixed edge
         "check": lambda s: "approve" if s["ok"] else "draft",     # conditional edge, closes a cycle
         "approve": lambda s: "END" if s["approved"] else "draft"}  # rejection loops back too

def run(thread_id, inputs=None, resume=None, max_steps=20):
    saved = CHECKPOINTS.get(thread_id)
    state, node = (dict(saved["state"]), saved["next"]) if saved else (dict(inputs), "draft")
    if resume is not None:
        state["answer"] = resume                          # deliver the human's answer
    for _ in range(max_steps):                            # cycles need an explicit bound
        try:
            state.update(NODES[node](state))              # default reducer: overwrite each key
        except Interrupt as pause:                        # the paused node re-runs from the top on resume
            CHECKPOINTS[thread_id] = {"state": state, "next": node}
            return {"interrupt": pause.args[0]}           # the process may now exit
        node = EDGES[node](state)
        CHECKPOINTS[thread_id] = {"state": state, "next": node}  # checkpoint after every step
        if node == "END":
            return {"done": state}
    raise RuntimeError("step limit reached")

print(run("t1", inputs={"attempts": 0}))   # draft -> check -> draft -> check -> approve: pauses
print(run("t1", resume=True))              # loads the checkpoint, finishes
```

The checkpoint is plain JSON-serializable data, so it can live in Postgres. The process may exit between the two `run` calls, even for days, and the second call works only because the first saved both the state *and* the next node.

### The same shape in LangGraph

LangGraph **(GA, v1.0 Oct 2025; 1.2.x as of Oct 2026)** gives you the same parts as library primitives. This was run against langgraph 1.2.15:

```python
from typing import TypedDict
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

class State(TypedDict, total=False):   # the shared state; no reducers, so every key overwrites
    attempts: int
    draft: str
    ok: bool
    approved: bool

def draft(state: State):
    n = state.get("attempts", 0) + 1
    return {"attempts": n, "draft": f"churn summary v{n}"}

def check(state: State):
    return {"ok": state["attempts"] >= 2}

def approve(state: State):
    answer = interrupt({"question": "Publish this?", "draft": state["draft"]})  # pauses here
    return {"approved": answer}        # on resume, answer is the Command(resume=...) value

builder = StateGraph(State)
builder.add_node("draft", draft)
builder.add_node("check", check)
builder.add_node("approve", approve)
builder.add_edge(START, "draft")
builder.add_edge("draft", "check")                                                    # fixed edge
builder.add_conditional_edges("check", lambda s: "approve" if s["ok"] else "draft")  # the cycle
builder.add_conditional_edges("approve", lambda s: END if s["approved"] else "draft")
graph = builder.compile(checkpointer=InMemorySaver())   # PostgresSaver in production

config = {"configurable": {"thread_id": "t1"}}           # which checkpoint to load and write
result = graph.invoke({"attempts": 0}, config)
print(result["__interrupt__"])                           # the payload the human sees
result = graph.invoke(Command(resume=True), config)      # same thread_id, so it resumes
print(result["approved"], result["draft"])
print([s.next for s in graph.get_state_history(config)])  # time travel: every checkpoint
```

For streaming UIs, the docs recommend `graph.stream_events(..., version="v3")`, which exposes `stream.interrupts`.

### Checkpointers: state per thread

A **checkpointer** saves the graph state after every super-step, keyed by a `thread_id`, which is one conversation or one workflow instance. `InMemorySaver` is for development. `SqliteSaver` and `PostgresSaver` persist across restarts. One mechanism gives you four capabilities:

1. **Short-term memory.** Reuse the `thread_id` to continue a thread. A new `thread_id` starts empty.
2. **Durable execution (fault tolerance).** After a crash, rerun with the same `thread_id` and execution resumes from the last checkpoint. [§20](20-agent-runtime.md) compares this with Temporal-style replay.
3. **Human-in-the-loop**, covered next.
4. **Time travel.** `get_state_history` lists every checkpoint. Invoking with an old checkpoint's config **replays** from there, and `update_state` **forks** a branch with modified state, leaving the original history intact. It resembles Delta Lake time travel, except that replay *re-executes* later nodes, LLM calls included, so results can differ (P4).

The consequence that bites is that **checkpoints sit at super-step boundaries, not mid-function.** A resumed or retried node runs again from its first line, so any side effect before the pause, such as a sent email, happens again. This is the at-least-once problem from Kafka consumers, and the fix is the same: make nodes **idempotent** (safe to run twice), or put side effects after the pause point.

### Interrupts: human-in-the-loop

`interrupt(payload)` inside a node saves the state, hands the payload to the caller and stops. Nothing blocks, so the human can answer next week. You continue by invoking with `Command(resume=value)` on the same `thread_id`. The paused node restarts from its top, and this time `interrupt()` returns `value`. This builds P8's "humans at the right points" into the structure and extends P6: the model proposes, a human approves, code executes.

### Dynamic fan-out: map-reduce with `Send`

Static edges can't express "one worker per document" when you only learn the number of documents at runtime. A conditional edge can instead return a list of `Send` objects, such as `[Send("summarize", {"doc": d}) for d in state["docs"]]`. Each `Send` launches a parallel invocation of the node with its own private input. A merging reducer, `summaries: Annotated[list[str], operator.add]`, appends the workers' outputs, and a downstream `combine` node runs once all of them finish. It is the split-apply-combine shape of a Spark map over partitions, and the orchestrator-workers pattern from [§12](12-agentic-design-patterns.md), now with explicit, durable state.

### Stores: long-term memory across threads

A checkpointer is scoped to one thread. A **store** is a separate key-value layer, namespaced by something like a user ID, that every thread can read and write, for preferences and learned facts. You compile with both: `builder.compile(checkpointer=..., store=...)`. [§17](17-memory.md) builds memory on this.

### Three orchestration styles

| Style | Who defines the next step | Examples |
|---|---|---|
| **Loop** | The model, every turn. The harness is a `while` loop around tool calls | Claude Agent SDK, OpenAI Agents SDK, smolagents |
| **Graph / state machine** | You declare nodes and edges, and the model chooses only at conditional edges or inside agent nodes | LangGraph, Google ADK 2.0 graph workflows, Microsoft Agent Framework workflows, Mastra workflows |
| **Event-driven** | Steps subscribe to events, so the topology emerges from who listens to what | CrewAI Flows (`@start`, `@listen`), Inngest (durable functions triggered by events), ADK's event loop |

Event-driven orchestration resembles Kafka consumers: nobody draws the whole graph. You gain decoupling and lose visibility, since answering "what runs after X?" means reading every subscriber.

### The 2026 convergence on graphs

Independent frameworks have moved toward explicit graphs:

- **Google ADK 2.0** introduced a Workflow Runtime, "transitioning ADK from a hierarchical agent executor to a graph-based execution engine". In it, agents, tools and functions are all evaluated as nodes. Python reached GA May 19, 2026, Go June 30, 2026, and TypeScript August 21, 2026 **(GA)**.
- **Microsoft Agent Framework**, the successor to both AutoGen and Semantic Kernel, offers "functional and graph-based workflows that connect agents and functions through explicit execution paths", with checkpoints and human-in-the-loop. Version 1.0 shipped April 3, 2026 **(GA)**.
- **Mastra** (TypeScript) composes `createStep` units with `.then()`, `.branch()` and `.parallel()`, and supports suspend and resume.

The forces are the ones above: explicit order, persistent state and human pauses.

### When to use a graph and when an agent harness

LangChain's own guidance draws the line: for tasks that are agentic by nature, "you don't want to represent the system as a graph but rather just use an agent harness (like Deep Agents)". They built early deep research on predefined LangGraph workflows, then moved it to an agentic core loop, and GPT Researcher made the same move. Microsoft's docs agree. Pick an agent when the task is open-ended or needs autonomous planning, and a workflow when the process has well-defined steps and you need explicit control over order. They add: "If you can write a function to handle the task, do that instead of using an AI agent."

P12 sharpens the rule. Edges that encode **business structure** (approvals, compliance gates, fixed stages) stay valuable however good models get. Edges that encode **workarounds for model weakness** ("always re-plan after three tool calls") are scaffolding that will need deleting. What is new in 2026 is that a node can be a whole agent, so a graph can hold the fixed process while an agent inside one node does the open-ended part ([§19](19-harness-engineering.md)).

### Not GraphRAG

**GraphRAG** (Microsoft, Edge et al., Apr 2024) builds a *knowledge graph* of entities, relationships and community summaries from your documents and retrieves from it ([§09](09-rag.md)). There the graph is **data**. In graph engineering it is **control flow**. The two can meet, since a GraphRAG retrieval can be one node in a workflow.

### Failure modes

- **Runaway cycles.** A condition the model never satisfies burns tokens until the recursion limit. Set per-run limits and route to a fallback node first.
- **Duplicate side effects** on resume, retry or replay. Make nodes idempotent.
- **Reducer surprises.** With an `add` reducer, returning `[]` doesn't clear the field. LangGraph's `Overwrite` does.
- **Unbounded checkpoints.** Prune old snapshots on a retention policy, as you would old table versions.
- **State schema drift.** Changing `State` can break threads in flight, so treat it as a migration.
- **Over-structuring.** A branch for every imagined case is brittle on the unimagined ones. If edges keep multiplying, the task belongs in a harness.

## Comparison

| Approach | How control flow is defined | Strength | Weakness | When to choose |
|---|---|---|---|---|
| Plain agent loop | The model picks the next tool each turn | Flexible, little code, improves as models do (P12) | Hard to guarantee order, approvals or termination | Open-ended tasks: research, coding, exploration |
| Explicit graph | Declared nodes, fixed and conditional edges, typed state | Predictable paths, checkpoints, HITL, replay | More code; brittle if it over-specifies | Known processes with branches, approvals and SLAs |
| Event-driven | Steps subscribe to events | Loose coupling, natural for async triggers | Topology is implicit and harder to trace | Systems that react to external events (webhooks, queues) |
| Data DAG (Airflow, dbt) | Acyclic dependency graph | Termination and ordering guaranteed by structure | No cycles; each task runs once per run | Deterministic data pipelines, not agent loops |

## What it didn't solve

A graph structures *your* control flow. But each node that touches the outside world still needs custom glue code: a Jira tool, a warehouse query tool, a call to another team's agent. You write that code for LangGraph, again for ADK, and again for the IDE agent your colleagues use. N applications times M tools means N×M integrations (P11), and nothing about graphs changes that.

→ Next: [§15 Protocols: MCP and A2A](15-protocols-mcp-a2a.md)

## Check your understanding

**Q: Why do agent graphs usually contain cycles when Airflow and dbt pipelines forbid them?**

A data DAG encodes dependencies between transformations, and a cycle would leave no valid execution order, so acyclicity guarantees that every task runs once and the run ends. Agents loop as part of their work: they retry tools, ask for missing input, and revise after validation. So the graph needs back-edges, and the run ends when a runtime condition is met rather than by structure. The tradeoff is that you must enforce termination yourself with step limits, counters and budgets. If your process really is a fixed sequence of transformations, a DAG is the better tool.

**Q: What would happen if a node sends an email and then calls `interrupt()` to ask for approval?**

Checkpoints are written at super-step boundaries, and a resumed node runs again from its first line, so the email goes out once before the pause and again on resume. The fix is idempotency: put the send in its own node after approval, or guard it with an idempotency key. It is the at-least-once lesson from Kafka consumers. You can skip the precaution only for naturally idempotent effects, such as an upsert keyed by ID.

**Q: In what sense is a ReAct-style agent loop "a degenerate graph"?**

The loop is two nodes, the model call and the tool executor, with one conditional edge ("did the model request a tool?") that either cycles back or exits. So loop and graph are the same mechanism with different amounts of structure written down. The consequence is that you can start with a loop and promote steps to explicit nodes and edges only where you need guaranteed order, persistence or approval. Over-promoting turns a flexible agent into a brittle flowchart.

**Q: Checkpointer vs store: what does each persist, and why does a checkpointer need a `thread_id`?**

A checkpointer saves snapshots of one run's graph state after every super-step. The `thread_id` is the key that says which snapshot sequence to load and append to, so reusing it resumes and a new one starts fresh. A store is a cross-thread key-value layer for data that outlives any single run, such as user preferences. Putting long-term facts in thread state would lose them when a new thread starts, and putting per-run scratch data in the store would leak it across conversations.

**Q: What would happen if you modeled open-ended research as a fixed graph with one node per research step?**

The graph would hard-code your guess about how research unfolds: how many searches, in what order, when to stop. Real queries vary, so it wastes steps on easy questions, cuts off hard ones, and grows edges with every new case. LangChain hit exactly this and moved deep research to an agent harness. Keep a graph only for the fixed stages around such a task, such as intake, then a research agent node, then human review.

**Q: Why does map-reduce need `Send` instead of ordinary edges?**

Ordinary edges are declared before the run, so they can't express "one worker per item" when the number of items is known only at runtime. A `Send` returned from a conditional edge launches a parallel invocation of a node with its own private input. A reducer such as `operator.add` then merges the parallel writes into shared state. Without a merging reducer, the parallel updates to the same key would conflict. If the fan-out width is fixed and small, plain parallel edges are simpler.

**Q: Why doesn't replaying an agent graph from an old checkpoint reproduce the original run?**

Time travel restores the saved state and then re-executes every node after that checkpoint, including LLM calls, API requests and interrupts. Model output is sampled (P4) and external systems change, so the replayed path can diverge. That makes replay useful for asking "what if we retried from here?" or for forking with edited state, but not for exact reproduction. For audits, rely on the recorded traces ([§27](27-observability.md)), not on replay.

## Takeaways

- Graph engineering is a 2026 label for a 2024 practice: modeling agent systems as state machines with typed state, nodes and fixed or conditional edges.
- Agent graphs have cycles. Unlike a data DAG, the structure doesn't guarantee termination, so you must enforce it.
- A loop is a degenerate graph. The real decision is which edges you fix in code and which the model chooses (P7).
- Checkpointers, keyed by `thread_id`, give you resumable runs, human-in-the-loop, time travel and short-term memory. Stores hold memory across threads.
- Nodes re-run from the top on resume or retry, so nodes with side effects must be idempotent.
- `Send` gives dynamic map-reduce fan-out, and reducers say how parallel writes merge.
- Use a graph for known processes with branches and approvals. Use an agent harness for open-ended work, or embed the agent as a node.
- GraphRAG is a knowledge graph of your data, not a control-flow graph.

## Sources

- LangChain, "3 Years of Graph Engineering with LangGraph" (Runkle & Chase, Jul 22, 2026): https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph
- LangChain, "LangGraph" launch post (Jan 17, 2024): https://blog.langchain.com/langgraph/
- LangGraph Graph API (state, reducers, super-steps, `Send`, recursion limit): https://docs.langchain.com/oss/python/langgraph/graph-api
- LangGraph persistence (checkpointers and stores): https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph interrupts: https://docs.langchain.com/oss/python/langgraph/interrupts
- LangGraph time travel: https://docs.langchain.com/oss/python/langgraph/use-time-travel
- LangChain Deep Agents overview: https://docs.langchain.com/oss/python/deepagents/overview
- Google ADK workflows: https://google.github.io/adk-docs/workflows/ and ADK 2.0 release notes: https://google.github.io/adk-docs/2.0/
- Microsoft Agent Framework overview (agents vs workflows): https://learn.microsoft.com/en-us/agent-framework/overview/
- Microsoft Agent Framework 1.0 announcement (Apr 3, 2026): https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/
- Mastra workflows: https://mastra.ai/docs/workflows/overview and https://mastra.ai/docs/workflows/control-flow
- CrewAI Flows: https://docs.crewai.com/en/concepts/flows
- Inngest AgentKit: https://www.inngest.com/docs/agent-kit/overview
- Anthropic, "Building effective agents" (Dec 19, 2024): https://www.anthropic.com/engineering/building-effective-agents
- Microsoft GraphRAG: https://microsoft.github.io/graphrag/ and Edge et al., arXiv 2404.16130: https://arxiv.org/abs/2404.16130
