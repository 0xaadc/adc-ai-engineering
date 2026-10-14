# 11. Agents and the Agent Loop

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This section covers 2023–2025. [§10](10-tool-use.md) made one tool call reliable, but one call is one step. In spring 2023, AutoGPT (public launch Mar 30, 2023) and BabyAGI (described by Yohei Nakajima on Mar 28, 2023) went viral by putting GPT-4 in a loop that invented its own subtasks. They were thrilling demos and mostly failed at real work: they got stuck in loops, hallucinated, and burned money. Agents became dependable for real work, coding above all, only in 2024–2025, and the loop itself barely changed. The model did. Models were post-trained for tool use and agentic tasks, reasoning models learned to plan and recover ([§04](04-reasoning-models.md)), and context windows grew large enough to hold a long trajectory. METR measured the result: the length of task frontier models can finish at 50% success has doubled roughly every seven months since 2019. It attributes this mainly to "greater reliability and ability to adapt to mistakes."

## Why this exists

Many tasks are discovered step by step. Take "why did last night's dbt run fail?" You read the log, which names a model. You read that model's SQL, which references a column. You check the upstream schema and find the column was renamed. No one could have written that sequence in advance, because each step depends on what the previous one revealed. A fixed pipeline of model calls (a **workflow**) can handle this only by listing every branch ahead of time. The alternative is to give the model control of the flow: after each observation, it chooses the next action. That is the autonomy end of P7's dial.

The 2023 attempts show what this costs. AutoGPT had no native function calling (that arrived in June 2023) and small context windows. It chased open-ended goals by inventing its own subtasks, with no external check on progress. Each step had a real chance of going wrong, the chances multiplied (P8), and every step was a paid GPT-4 call (P10). The idea was right, but the per-step reliability was too low.

## How it works (under the hood)

### What an agent is

Anthropic's "Building effective agents" (Dec 19, 2024) says agents "are typically just LLMs using tools based on environmental feedback in a loop." Simon Willison's version (Sep 18, 2025) is shorter: "An LLM agent runs tools in a loop to achieve a goal." Four parts matter here:

- **Tools.** The model can act, as described in [§10](10-tool-use.md).
- **A loop.** The model can take as many steps as the task needs.
- **Environmental feedback.** Each action's real result (test output, query rows, an error) goes back into context. Anthropic calls this getting "ground truth" from the environment at each step.
- **A stopping condition.** Something decides when the loop ends.

The building block is the **augmented LLM**: "an LLM enhanced with augmentations such as retrieval, tools, and memory" ([§09](09-rag.md), [§10](10-tool-use.md), [§17](17-memory.md)). A workflow arranges augmented-LLM calls in code. An agent puts one in a loop and lets it steer.

### The loop in code

The loop itself, `run_agent`, is about 20 lines, and with the stub model and two tools the whole agent is under 40. The stub replays scripted replies in the Messages API shape, so the code runs offline. Swap `call_model` for `client.messages.create(...)` to go live.

```python
import json

# Stub model: scripted replies in the Messages API shape, so this runs offline.
SCRIPT = [
    {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": "t1",
        "name": "search_tickets", "input": {"query": "refund"}}]},
    {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": "t2",
        "name": "get_ticket", "input": {"ticket_id": 7}}]},
    {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Ticket 7 is the open refund."}]},
]
def call_model(messages):  # live: client.messages.create(model=..., tools=..., messages=...)
    return SCRIPT[sum(m["role"] == "assistant" for m in messages)]
TOOLS = {  # plain functions that YOUR code owns and runs (P6)
    "search_tickets": lambda query: json.dumps([{"id": 7, "title": "Refund not received"}]),
    "get_ticket": lambda ticket_id: json.dumps({"id": ticket_id, "status": "open"}),
}

def run_agent(task, max_turns=10):
    messages = [{"role": "user", "content": task}]
    resp, turns = call_model(messages), 1
    while resp["stop_reason"] == "tool_use":            # the model wants to act
        if turns >= max_turns:                          # stopping condition: turn budget
            raise RuntimeError(f"No answer after {turns} turns")
        messages.append({"role": "assistant", "content": resp["content"]})
        results = []
        for block in (b for b in resp["content"] if b["type"] == "tool_use"):
            try:                                        # execute; never crash the loop
                out, err = TOOLS[block["name"]](**block["input"]), False
            except Exception as e:                      # unknown tool, bad args, tool failure
                out, err = f"{type(e).__name__}: {e}", True
            results.append({"type": "tool_result", "tool_use_id": block["id"],
                            "content": out, "is_error": err})
        messages.append({"role": "user", "content": results})  # the observation
        resp, turns = call_model(messages), turns + 1
    return resp, turns   # end_turn, or max_tokens / refusal / pause_turn: check which

print(run_agent("Find the open refund ticket."))
```

Running it prints the final `end_turn` reply after three model calls. Everything that later sections add (context management, memory, sandboxes, verification, human approval) is code placed around this `while`.

```text
            ┌──────────────── call_model(messages) ◀─────────────────┐
            ▼                                                          │
   stop_reason == "tool_use"? ── no ──▶ end_turn: done? (verify it!)   │
            │ yes                        max_tokens / refusal / budget │
            ▼                            → handle or stop              │
   execute each tool_use in YOUR code (validate, authorize, run)       │
            ▼                                                          │
   append assistant turn + tool_results (the observation) ─────────────┘
   check budgets: turns, tokens, cost, wall clock
```

### What each turn costs

The model is stateless (P2), so every turn resends the whole transcript: the task, every call and every observation. If each turn adds *c* tokens, turn *k* sends about *k·c*, and an *n*-turn run sends about *c·n²/2* input tokens in total. **Cost grows with the square of the number of turns**, and every observation competes for attention (P3). Prompt caching absorbs most of the repeated prefix. On Claude Sonnet 5.5, cache hits cost $0.20 per million tokens against $2 for fresh input, as of Oct 2026 ([§30](30-cost-latency-reliability.md)). Pruning stale observations handles the rest ([§16](16-context-engineering.md)).

### Workflows vs agents (P7)

Anthropic draws the line by **who owns control flow**:

- **Workflows** are "systems where LLMs and tools are orchestrated through predefined code paths."
- **Agents** are "systems where LLMs dynamically direct their own processes and tool usage, maintaining control over how they accomplish tasks."

Workflows are predictable, cheap and testable, like a DAG you wrote. Agents handle open-ended tasks at the cost of variance, spend, and "the potential for compounding errors." The advice is explicit: find "the simplest solution possible, and only [increase] complexity when needed. This might mean not building agentic systems at all." For many applications, "optimizing single LLM calls with retrieval and in-context examples is usually enough." The post also warns that frameworks can "obscure the underlying prompts and responses," which is why this section shows the bare loop. The named workflow shapes (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer) are covered in [§12](12-agentic-design-patterns.md). Multiple cooperating agents are covered in [§13](13-multi-agent.md).

### Levels of autonomy

"Agent" is a spectrum, not a yes-or-no label. Hugging Face's smolagents docs measure agency by how much the LLM's output controls the program:

| Level | The LLM's output... | Name | Shape |
|---|---|---|---|
| ☆☆☆ | has no effect on program flow | Simple processor | `process(llm_output)` |
| ★☆☆ | picks a branch | Router | `if llm_decision(): a() else: b()` |
| ★★☆ | picks a function and its arguments | Tool call | `run(llm_tool, llm_args)` |
| ★★☆ | decides whether to keep going | Multi-step agent | `while llm_should_continue(): step()` |
| ★★★ | starts other agents, or writes its own tools as code | Multi-agent / code agent | `if llm_trigger(): run_agent()` |

A complementary view describes autonomy from the user's side. Feng, McDonald and Zhang ("Levels of Autonomy for AI Agents," Jun 2025) define five levels by the user's role: **operator, collaborator, consultant, approver, observer**. They argue that an agent's autonomy "can be treated as a deliberate design decision, separate from its capability and operational environment." A capable model can still be deployed at "approver" level, for example where every irreversible action waits for a click.

### Stopping conditions

A loop without a stop is a bug. Real agents layer several stops:

- **Natural end.** `stop_reason: "end_turn"` means the model *claims* it is finished. That is a claim, not a proof (see failure modes below).
- **Other stop reasons.** These need handling, not a silent exit. `max_tokens` means the output was truncated, so raise the limit or continue. `refusal` means stop and run no tools. `pause_turn` means a server-tool loop paused, so resend. `model_context_window_exceeded` means the context is full, so compact ([§16](16-context-engineering.md)).
- **Max turns.** This is the cheapest guard against runaway loops. Anthropic notes "it's also common to include stopping conditions (such as a maximum number of iterations) to maintain control."
- **Token or cost budget.** Sum `usage` across turns and stop at a cap. Anthropic's *task budgets* **(Preview)** instead tell the model its remaining token budget so it can pace itself. That is advisory, while your cap is enforced.
- **Wall-clock timeout**, for interactive products.
- **Goal checks.** Something other than the model decides "done": the tests pass, the row counts reconcile, or a separate checker model judges a stated done condition each turn ([§21](21-loop-engineering.md)).
- **A human interrupt**, at checkpoints or when the agent hits a blocker.

### Compounding error (P8)

If each step succeeds with probability *p*, independently, then a run of *n* steps all succeeds with probability *pⁿ*:

| per-step *p* | n = 5 | n = 10 | n = 20 | n = 50 |
|---|---|---|---|---|
| 0.99 | 95.1% | 90.4% | 81.8% | 60.5% |
| 0.95 | 77.4% | 59.9% | 35.8% | 7.7% |
| 0.90 | 59.0% | 34.9% | 12.2% | 0.5% |

A step that is "95% reliable," which sounds good, gives you a 20-step agent that fully succeeds about one time in three. This is the arithmetic behind 2023's demos. Two caveats keep the model honest. Errors are **correlated**: a model that misreads the schema once will misread it again, which makes things worse than *pⁿ*. And errors can be **recovered**: an agent that sees a failing test and fixes it turns a failure into a retry, which makes things better. Most of the 2024–2025 improvement came from recovery. So the dangerous errors are the **silent** ones, because an error nobody observes can't be recovered.

### Verification and checkpoints

Verification is what turns silent errors into observed ones. Suppose a checker reliably catches a failed step and you allow *r* retries. With independent attempts and a perfect checker, the effective per-step success is *p′ = 1 − (1 − p)^(r+1)*:

| per-step *p* | retries | effective *p′* | 20-step success |
|---|---|---|---|
| 0.90 | 0 | 0.90 | 12.2% |
| 0.90 | 1 | 0.99 | 81.8% |
| 0.90 | 2 | 0.999 | 98.0% |

Real checkers aren't perfect, but the direction holds: **a cheap check per step does more than a slightly better model.** Three rules follow:

- **Prefer computational checks**, such as tests, type checks, schema validation and row-count reconciliation (the agent's equivalent of dbt tests). Use **inferential** checks (an LLM judge) for things code can't check ([§26](26-evals.md)).
- **Keep the checker separate from the maker.** Anthropic's Mar 2026 harness post found that agents asked to evaluate their own work "tend to respond by confidently praising the work—even when, to a human observer, the quality is obviously mediocre." It also found that tuning a standalone skeptical evaluator was "far more tractable."
- **Checkpoint after verified steps.** Persist state so a failure rolls back to the last good point, not to zero, the way an idempotent, restartable pipeline task does ([§14](14-graph-engineering.md), [§20](20-agent-runtime.md)). Put human approval at irreversible steps.

### Observation formatting

The tool result is the model's only view of the world (P2), and every observation stays in context for the rest of the run (P3). Format it on purpose:

- **Lead with the signal**: status, exit code, count, or error first, details after.
- **Bound the size**, and say so: "showing 50 of 1,240 rows; pass offset=50 for more."
- **Show the effect of actions**, such as the diff or the new state, so the model can check instead of assume.
- **Use readable identifiers and a stable format across turns.**
- **Clear stale observations.** Anthropic calls tool-result clearing "one of the safest lightest touch forms of compaction": once a result is deep in history, the agent rarely needs it verbatim ([§16](16-context-engineering.md)).

### Error recovery

Recovery is layered, and each layer has an owner:

1. **Tool errors → the model.** Return `is_error` results that say how to fix the problem ([§10](10-tool-use.md)). The model retries or changes approach.
2. **Transport errors → your code.** Model API 429/5xx errors and timeouts get retried with backoff. Side-effecting tools need **idempotency keys**, so that a retried "charge card" doesn't charge twice (the same reason you want exactly-once sinks).
3. **Stuck loops → the harness.** Detect the same call with the same arguments *k* times, or no progress for *k* turns. Then add a note to the next turn, force a change of strategy, or stop.
4. **Unrecoverable → a human.** Stop cleanly, save state, and return the partial result plus what remains.

### Failure modes

| Failure | Symptom | Mechanism | Mitigation |
|---|---|---|---|
| **Loops** | The same call again and again, or edits that flip back and forth | The observation doesn't change the model's beliefs; errors are uninformative; history is forgotten | Max turns, repeat detection, instructive errors, a progress note on disk |
| **Premature "done"** | `end_turn` with "all tests pass" when they don't | The model predicts a plausible ending, and self-grading is lenient. Anthropic saw later agent instances "see that progress had been made, and declare the job done" | An external done check, a feature list with pass/fail status, evidence required (test output) |
| **Tool misuse** | Wrong tool, hallucinated IDs, a destructive call | Ambiguous tools ([§10](10-tool-use.md)); sampling (P4) | Better tool design, `strict`, validation, approval gates |
| **Drift** | Side quests, forgetting the original constraint, following injected text | Context rot buries the goal (P3); instructions arrive inside data (P9) | Restate the goal and plan in a progress file, compaction, subagents, least privilege |

### When not to build an agent

Don't build one when:

- **The steps are known.** Write the workflow; it is cheaper and testable.
- **One well-grounded call answers the question.** This is the most common case.
- **Errors are costly and hard to detect.** If you can't verify the outcome, you won't know when the agent is wrong.
- **The latency or cost budget is tight.** Agents spend many calls and quadratic tokens.
- **The per-step *p* is low.** Then *pⁿ* will sink you. Raise *p* (better tools, a better model, smaller steps) before adding autonomy.

## Comparison

| | Single call | Workflow | Agent |
|---|---|---|---|
| Who decides the next step | Nobody, there is one step | Your code (P7) | The model (P7) |
| Cost and latency | Lowest, predictable | Bounded, predictable | Unbounded unless capped; quadratic context |
| Testing | Evals on one output | Evals per step and end to end | Evals on trajectories and outcomes ([§26](26-evals.md)) |
| Failure behavior | One bad answer | Fails at a known step | Compounds or recovers; can fail silently |
| When to choose | Q&A, extraction, classification | Known, repeatable multi-step processes | Open-ended tasks whose steps you can't predict |

| Stopping condition | Catches | Misses |
|---|---|---|
| `end_turn` | A model that believes it is done | A model that is wrong about being done |
| Max turns | Runaway loops | Slow, expensive runs under the cap |
| Token or cost budget | Context blowup, runaway spend | Cheap but wrong runs |
| Goal check (tests, checker) | Premature "done" | Whatever the check doesn't test |
| Human approval | Irreversible mistakes | Anything nobody looks at |

## What it didn't solve

"Put the model in a loop" is not a design, any more than "write a while loop" is a program. The bare loop tells you nothing about decomposing a task, when to plan before acting, how to have one model check another, or how to fan work out and merge it back. Practitioners converged on a vocabulary of proven structures for exactly these decisions. → Next: [§12 Agentic Design Patterns](12-agentic-design-patterns.md)

## Check your understanding

**Q: Why did AutoGPT-style agents fail in 2023 while nearly the same loop works in 2025?**

The loop was never the problem. Per-step reliability was. With no native tool calling, small context windows and weak error recovery, *p* was low, and *pⁿ* collapsed over long runs (P8). Later models were trained for tool use and agentic tasks and learned to notice and fix their own mistakes, so the same `while` loop now finishes real work. This is P12 in action: the scaffolding stayed simple, and the model improved underneath it.

**Q: Every night you must classify new support tickets and route them to one of five queues. Workflow or agent?**

A workflow. The steps are known in advance (read, classify, route), so code should own the control flow (P7). That makes the job cheaper, faster, testable and predictable. An agent would add variance and cost and gain nothing, because no step depends on discovering something new. Reconsider only if tickets regularly need open-ended investigation.

**Q: What would happen if you removed `max_turns` and relied on the model to say when it's done?**

Most runs would end fine, but a few would loop indefinitely, repeating a failing call or oscillating between two edits, and each turn would cost more than the last because the context grows (P2, P10). In a sampled system, rare behaviors appear at scale (P4), so the tail is guaranteed. Keep a turn cap and a token cap as hard backstops, even if they rarely fire.

**Q: A step is 95% reliable. Why is a 20-step agent built from it so unreliable, and what is the most effective fix?**

Independent steps multiply: 0.95²⁰ ≈ 36%. Raising *p* helps, but verification helps more. A checker that catches a failed step and allows one retry lifts the effective *p* to about 0.9975, and 20-step success to about 95% (under idealized assumptions). The checker converts silent errors into recoverable ones.

**Q: Why keep the checker separate from the maker?**

A model grading its own output shares the misunderstandings that produced it, and it tends toward leniency. Anthropic reports that agents "confidently" praise mediocre work. A separate checker, ideally computational (tests, schema checks), or a differently prompted skeptical judge, fails in different ways, so its errors don't line up with the maker's. That independence is what makes the retry math work.

**Q: Why is `stop_reason: "end_turn"` not proof that the task succeeded?**

It only means the model stopped emitting tool calls. It predicted that a final answer comes next. That prediction can be wrong, for example when a later agent sees partial progress and declares the job done. Done should be decided by an external check: tests pass, data reconciles, or a human approves.

**Q: Why does each turn of an agent cost more than the one before, and what do you do about it?**

The model is stateless, so each request resends the full transcript, and total input tokens grow roughly with the square of the turn count (P2, P10). Prompt caching makes the repeated prefix cheap, and clearing stale tool results or compacting history keeps the context small and focused (P3). For very long tasks, split the work across fresh contexts with state on disk ([§16](16-context-engineering.md)).

## Takeaways

- An agent is an LLM using tools in a loop with environmental feedback until a stopping condition fires. The core is a `while stop_reason == "tool_use"` loop of about 20 lines.
- Workflow or agent is a question of who owns control flow (P7). Start with the simplest thing that works, and often that isn't an agent.
- Errors compound as *pⁿ* (P8). 95% per step over 20 steps is about 36%.
- Verification beats raw capability: a separate checker plus retries turns silent failures into recoverable ones.
- Layer your stops: `end_turn`, max turns, token and cost budgets, goal checks, human interrupts. Handle every `stop_reason`.
- Format observations for the model: signal first, bounded size, effects shown, stale results cleared.
- Watch for the four classic failures: loops, premature "done", tool misuse and drift.

## Sources

- Anthropic, "Building effective agents" (Schluntz & Zhang, Dec 19, 2024): https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, "How tool use works" (the agentic loop): https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works
- Anthropic, "Stop reasons and fallback": https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons
- Anthropic, Pricing (prompt-caching multipliers): https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic, "Effective context engineering for AI agents" (Sep 29, 2025): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic, "Effective harnesses for long-running agents" (Nov 26, 2025): https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic, "Harness design for long-running application development" (Mar 24, 2026): https://www.anthropic.com/engineering/harness-design-long-running-apps
- Simon Willison, "I think 'agent' may finally have a widely enough agreed upon definition to be useful jargon now" (Sep 18, 2025): https://simonwillison.net/2025/Sep/18/agents/
- Hugging Face, smolagents "Introduction to agents" (agency levels): https://huggingface.co/docs/smolagents/conceptual_guides/intro_agents
- Feng, McDonald & Zhang, "Levels of Autonomy for AI Agents" (Jun 2025): https://arxiv.org/abs/2506.12469
- Kwa et al. (METR), "Measuring AI Ability to Complete Long Software Tasks" (Mar 2025): https://arxiv.org/abs/2503.14499
- Yohei Nakajima, "Task-driven Autonomous Agent Utilizing GPT-4, Pinecone, and LangChain" (Mar 28, 2023): https://yoheinakajima.com/task-driven-autonomous-agent-utilizing-gpt-4-pinecone-and-langchain-for-diverse-applications/
- Wikipedia, "AutoGPT" (release date and limitations) (secondary): https://en.wikipedia.org/wiki/AutoGPT
- Yao et al., "ReAct" (Oct 2022), the original reason–act loop: https://arxiv.org/abs/2210.03629
