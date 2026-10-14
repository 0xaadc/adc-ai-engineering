# 12. Agentic Design Patterns

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This section covers the system thread from 2022 to 2026. [§11](11-agents.md) ended with a working definition: an agent is a model calling tools in a loop, while the harness executes each call (P6). That's true, but "a loop" isn't a design: it doesn't say how to split a task, where to check results, when to stop, or which decisions belong to code rather than to the model. Between ReAct (Oct 2022) and the planner–generator–evaluator harnesses of 2026, the field settled on a small vocabulary of recurring shapes. This section collects the three canonical catalogs, merges them into one taxonomy, explains how each pattern works, and ends with a guide for choosing one.

## Why this exists

A **design pattern** is a named, reusable solution to a problem that keeps coming back. Agent builders hit the same four forces again and again, and each one comes straight from the principles:

1. **Errors compound (P8).** If each step succeeds with probability p, n unchecked steps succeed with p^n. At p = 0.95, twenty steps give 0.36. Patterns shorten the chain, make each step easier, or add checks so an error made at step 3 is caught at step 3.
2. **Context is a finite budget that rots (P3).** One call that does everything carries every instruction, tool definition and intermediate result. Splitting the work gives each call a smaller, sharper context.
3. **Control flow has to live somewhere (P7).** Each pattern decides who picks the next step. Code is cheap, predictable and testable. The model is flexible, but costlier and less reliable.
4. **Compute buys accuracy (P10).** Some patterns deliberately spend more tokens to get better answers: they sample several answers, explore a tree of options, or run a critic.

Be honest about the label. "Agentic design patterns" turned into a book title and a genre of conference talk in 2024–25, and the catalogs overlap heavily under different names. What carries over is the mechanism, which is why this section maps every name onto one taxonomy.

## How it works (under the hood)

### Three canonical catalogs

**Andrew Ng's four (Mar 20, 2024).** In *The Batch*, Ng named four patterns:

- **Reflection**: the model critiques and revises its own output.
- **Tool use**: the model calls tools.
- **Planning**: the model writes a multistep plan and executes it.
- **Multi-agent collaboration**: agents split up a task and discuss it.

His evidence came from published HumanEval coding results that his team analysed: GPT-3.5 zero-shot scored 48.1% and GPT-4 zero-shot 67.0%, but GPT-3.5 inside an iterative agent loop reached up to 95.1%. The loop can matter more than the model generation. The four name capabilities, not control-flow shapes, so they make a good vocabulary and a poor blueprint.

**Anthropic's "Building effective agents" (Dec 19, 2024).** Erik Schluntz and Barry Zhang split *agentic systems* into two kinds. **Workflows** are systems where "LLMs and tools are orchestrated through predefined code paths". **Agents** are systems where "LLMs dynamically direct their own processes and tool usage". That's P7 as an architecture. The catalog climbs a ladder of autonomy:

- **Augmented LLM**: the building block, one call with retrieval, tools and memory.
- **Prompt chaining**: fixed steps with programmatic **gates** between them.
- **Routing**: classify the input, then send it to a specialized handler.
- **Parallelization**: **sectioning** (independent subtasks run at the same time) or **voting** (the same task run several times).
- **Orchestrator-workers**: a central LLM invents the subtasks at runtime and delegates them.
- **Evaluator-optimizer**: one call generates and another critiques, in a loop.
- **Autonomous agent**: "typically just LLMs using tools based on environmental feedback in a loop."

Its core advice is to find "the simplest solution possible, and only increase complexity when needed." For engineering it's the most useful of the three, because every entry says who owns the control flow.

**Antonio Gullí's *Agentic Design Patterns* (Springer, 2025).** This is the broadest catalog: 21 pattern chapters, checked against the publisher's chapter metadata, plus appendices. The chapters, in order:

1. Prompt chaining
2. Routing
3. Parallelization
4. Reflection
5. Tool use
6. Planning
7. Multi-agent collaboration
8. Memory management
9. Learning and adaptation
10. Model Context Protocol
11. Goal setting and monitoring
12. Exception handling and recovery
13. Human-in-the-loop
14. Knowledge retrieval (RAG)
15. Inter-agent communication (A2A)
16. Resource-aware optimization
17. Reasoning techniques
18. Guardrails/safety
19. Evaluation and monitoring
20. Prioritization
21. Exploration and discovery

It absorbs the other two and adds the operational patterns production needs. The cost of that breadth is that protocols (MCP) sit next to mechanisms (routing) as if they were the same kind of thing.

### One merged taxonomy

Group the patterns by *the problem they solve* and the three catalogs reduce to ten families:

| # | Family | Problem it solves | Ng | Anthropic | Gullí ch. | Research and 2025–26 names |
|---|---|---|---|---|---|---|
| 1 | Building block | One call needs facts and actions | Tool use | Augmented LLM | 5, 14 | Function calling ([§10](10-tool-use.md)) |
| 2 | Composition | Fixed multi-step work; code owns the flow | — | Chaining, routing, parallelization | 1, 2, 3 | Map-reduce, fan-out/fan-in |
| 3 | Reasoning–acting | Next step depends on what you just observed | Tool use | Autonomous agent | 17 | ReAct, CodeAct |
| 4 | Planning | Decide the steps before taking them | Planning | (inside orchestrator-workers) | 6, 11, 20 | Plan-and-Solve, Plan-and-Execute, ReWOO, LLMCompiler |
| 5 | Search | Many possible paths, only some good | — | Voting (partly) | 17, 21 | Self-consistency, Tree of Thoughts, LATS |
| 6 | Self-improvement | The first draft is wrong | Reflection | Evaluator-optimizer | 4, 9 | Self-Refine, Reflexion, generator/evaluator separation |
| 7 | Delegation | Too much for one context or one role | Multi-agent | Orchestrator-workers | 7 | Subagents, handoffs, planner–generator–evaluator ([§13](13-multi-agent.md)) |
| 8 | State | Work outlives one context window | — | (memory) | 8 | Checkpoints, progress files ([§14](14-graph-engineering.md), [§17](17-memory.md)) |
| 9 | Control and safety | Bound behavior, cost and damage | — | Gates, stop conditions | 12, 13, 16, 18, 19 | HITL, spend caps, guardrails ([§32](32-security-guardrails.md)) |
| 10 | Interop | Reach tools and agents you didn't build | — | (MCP mentioned) | 10, 15 | MCP, A2A ([§15](15-protocols-mcp-a2a.md)) |

Families 8–10 get their own sections. The rest of this section covers families 1–7.

### Composition workflows: code owns the control flow

**Prompt chaining with a gate.** Break the task into fixed steps, so that each step's output becomes the next step's input. A **gate** is a programmatic check that runs between steps: a schema validation, a count, a regex, or a cheap classifier. On failure, the chain either retries the step with the reason it failed or stops. Two mechanisms make this work. Each call gets an easier task with a smaller context (P3), and an error is caught at the step that made it instead of compounding (P8). If you know dbt: the chain is a model DAG and the gate is a test between models. You'd rather fail at `stg_orders` than publish a wrong `fct_revenue`.

```python
def call_model(system: str, user: str) -> str:
    """Stub for one Messages API call. The real version is:
    resp = client.messages.create(model="claude-sonnet-5-5", max_tokens=2048,
                                  system=system, messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in resp.content if b.type == "text")"""
    if system.startswith("Outline"):
        return "- Why table formats exist\n- How the transaction log works\n- When not to use one"
    return "[article written only from these bullets]\n" + user


def gate_outline(outline: str) -> list:
    """Code, not the model, decides whether step 1 is good enough (P6, P8)."""
    bullets = [line[2:].strip() for line in outline.splitlines() if line.startswith("- ")]
    if not 3 <= len(bullets) <= 6:
        raise ValueError(f"expected 3-6 bullets, got {len(bullets)}")
    if any(len(b) > 80 for b in bullets):
        raise ValueError("a bullet is longer than 80 characters")
    return bullets


def write_article(topic: str, max_retries: int = 2) -> str:
    request = topic
    for _ in range(max_retries + 1):
        outline = call_model("Outline the topic as 3-6 '- ' bullets.", request)  # step 1
        try:
            bullets = gate_outline(outline)                 # the gate between steps
            break
        except ValueError as err:
            request = f"{topic}\n(Your last outline was rejected: {err})"  # say why
    else:
        raise RuntimeError("outline never passed the gate; stop rather than compound errors")
    # Step 2 sees only the validated outline, not step 1's prompt or retries (P3).
    return call_model("Write one paragraph per bullet.", "\n".join(bullets))


print(write_article("Lakehouse table formats"))
```

**Routing.** A first call classifies the input. Code then dispatches it to a handler that has its own prompt, its own tools and possibly its own model. Without routing, "optimizing for one kind of input can hurt performance on other inputs" (Anthropic), because one prompt has to carry every case. Routing also controls cost by sending easy traffic to a small model (P10). The failure mode is silent misrouting: the wrong specialist answers confidently. To guard against it, you need a safe default route, a confidence threshold and a routing-accuracy eval ([§26](26-evals.md)).

```python
import json

ROUTES = {  # route -> (model, system prompt). Each handler sees only its own instructions (P3).
    "billing":   ("claude-haiku-5-5",  "You handle refunds and invoices. Tool: refund_lookup."),
    "technical": ("claude-sonnet-5-5", "You debug failed pipeline runs. Tool: search_logs."),
    "other":     ("claude-sonnet-5-5", "You are a general assistant. Escalate when unsure."),
}


def classify(text: str) -> str:
    """Stub for a cheap classifier call (a small model, or a non-LLM classifier).
    Real: claude-haiku-5-5 with structured outputs for {"route": ..., "confidence": ...}."""
    lowered = text.lower()
    if "refund" in lowered or "invoice" in lowered:
        return json.dumps({"route": "billing", "confidence": 0.93})
    if "error" in lowered:
        return json.dumps({"route": "technical", "confidence": 0.81})
    return "Probably billing?"  # models sometimes break the format


def route(text: str, min_confidence: float = 0.6) -> tuple:
    try:
        decision = json.loads(classify(text))
        name = decision["route"] if decision["confidence"] >= min_confidence else "other"
    except (json.JSONDecodeError, KeyError, TypeError):
        name = "other"            # unparseable reply: take the safe default, never guess
    if name not in ROUTES:
        name = "other"            # the model invented a route that does not exist
    model, system = ROUTES[name]
    # Next: call the chosen model with `system`, and LOG `name` so you can eval routing.
    return name, model


for msg in ["Please refund invoice 44", "Run failed with error 137", "Hello!"]:
    print(f"{msg!r} -> {route(msg)}")
```

**Parallelization.** *Sectioning* runs independent parts at the same time and merges the results in code. For example, one call screens the input with a guardrail while another answers. *Voting* runs the same task N times and aggregates the answers by majority, by threshold, or by "any one flags it." Voting works because output is sampled (P4): if errors are roughly independent, the majority is right more often than any single sample. That assumption is the failure mode. N copies of the same model with the same prompt often make the *same* mistake, so vary the prompts or the models. The cost is N times the tokens, and latency equals the slowest branch.

### Model-owned control flow: the loop and its upgrades

**ReAct and the autonomous agent.** ReAct (Yao et al., Oct 2022) has the model alternate *Thought*, *Action* (a tool call) and *Observation* (the result) until it decides it's done. Native function calling ([§10](10-tool-use.md)) and extended thinking ([§04](04-reasoning-models.md)) now implement this directly, and it's what Anthropic calls the autonomous agent. **CodeAct** (Wang et al., Feb 2024) makes each action a Python snippet rather than one JSON tool call, so a single step can compose several tools. Use the loop when you can't predict the number of steps. Its hidden cost is that every turn resends the growing transcript, so input tokens grow roughly with the square of the step count unless prompt caching ([§05](05-api-and-prompting.md)) absorbs the repeated prefix (P10).

**Orchestrator-workers.** A central LLM reads the input, decides which subtasks it needs (for example, which files a change must touch), dispatches them to workers and synthesizes the results. Unlike sectioning, the subtasks aren't defined in advance. This pattern is the bridge to [§13](13-multi-agent.md).

**Evaluator-optimizer.** A generator drafts, and a *separate* evaluator call grades the draft against explicit criteria and returns feedback. The two loop until the draft passes or a cap is hit. Anthropic gives two signs that the pattern fits: human feedback demonstrably improves the output, and an LLM can produce that kind of feedback. Notice what flows back to the generator: only the critique.

```python
import json


def generate(task: str, feedback: str) -> str:
    """Stub maker. Real: a Messages API call with a writer system prompt,
    given the task plus the evaluator's last critique (never its own old reasoning)."""
    if not feedback:
        return "The new pipeline is much faster."
    return "The new pipeline cut p95 load latency from 9 s to 2 s by partitioning on event date."


def evaluate(task: str, draft: str) -> str:
    """Stub checker: a SEPARATE call, separate skeptical system prompt, explicit rubric.
    Real: request JSON with structured outputs: output_config={"format": {...}}."""
    has_number = any(ch.isdigit() for ch in draft)
    return json.dumps({"pass": has_number,
                       "feedback": "" if has_number else "Vague claim: give a measured number."})


def evaluator_optimizer(task: str, max_rounds: int = 3) -> dict:
    feedback, draft = "", ""
    for round_no in range(1, max_rounds + 1):
        draft = generate(task, feedback)                 # maker
        verdict = json.loads(evaluate(task, draft))      # checker sees only the output
        if verdict["pass"]:
            return {"draft": draft, "rounds": round_no, "passed": True}
        feedback = verdict["feedback"]                   # only the critique flows back
    # Cap reached: do not loop forever. Return the last draft, flagged for a human.
    return {"draft": draft, "rounds": max_rounds, "passed": False}


print(evaluator_optimizer("One sentence on why the new pipeline is better."))
```

### Reasoning and planning patterns (the research lineage)

These came from papers, mostly in 2022–23. Models and harnesses later absorbed many of them.

| Pattern | Paper | Mechanism | Reported result |
|---|---|---|---|
| Self-consistency | Wang et al., Mar 2022, [arXiv 2203.11171](https://arxiv.org/abs/2203.11171) | Sample several chain-of-thought paths and majority-vote the final answer | GSM8K +17.9% over greedy CoT |
| ReAct | Yao et al., Oct 2022, [arXiv 2210.03629](https://arxiv.org/abs/2210.03629) | Interleave reasoning traces with tool actions and observations | ALFWorld +34, WebShop +10 points absolute success |
| Reflexion | Shinn et al., Mar 2023, [arXiv 2303.11366](https://arxiv.org/abs/2303.11366) | After a failed trial, write a verbal lesson to episodic memory and retry with it | HumanEval pass@1 91% vs 80% for GPT-4 |
| Plan-and-Solve | Wang et al., May 2023, [arXiv 2305.04091](https://arxiv.org/abs/2305.04091) | Prompt: devise a plan first, then carry out each step | Beat zero-shot CoT on all ten datasets |
| Tree of Thoughts | Yao et al., May 2023, [arXiv 2305.10601](https://arxiv.org/abs/2305.10601) | Breadth- or depth-first search over partial "thoughts"; the model scores branches and backtracks | Game of 24: 4% (CoT) → 74% |
| ReWOO | Xu et al., May 2023, [arXiv 2305.18323](https://arxiv.org/abs/2305.18323) | Planner writes every tool call up front with placeholders (`#E1`); workers fill them; a Solver combines | 5× fewer tokens, +4% accuracy on HotpotQA |
| LATS | Zhou et al., Oct 2023, [arXiv 2310.04406](https://arxiv.org/abs/2310.04406) | Monte Carlo tree search over ReAct trajectories, with an LM value function, reflection and environment feedback | HumanEval pass@1 92.7% (GPT-4) |

**Plan-and-execute** is LangChain's architecture version of Plan-and-Solve (May 2023, also crediting BabyAGI). A planner LLM writes the steps once, cheaper executors run them, and a replanning step fires only if the plan fails. Compared with ReAct, the big model is called once instead of every turn and has to reason about the *whole* task up front. The cost is brittleness, because a plan written before any observation can be wrong.

**ReWOO and LLMCompiler.** ReWOO ("reasoning without observation") names its tool calls with variables. That means no LLM call is needed between tool calls, and the transcript is never resent. LLMCompiler (Kim et al., Dec 2023, [arXiv 2312.04511](https://arxiv.org/abs/2312.04511)) treats the plan as a DAG and runs independent calls in parallel.

**Search.** Tree of Thoughts and LATS spend compute exploring alternatives. They need a **value function**, a way to score a partial solution, which comes from the model's judgment or, better, from the environment (tests pass, a move is legal). **Monte Carlo tree search (MCTS)** is the game-playing algorithm that repeatedly expands a promising branch, scores it and propagates the score back up the tree.

Reasoning models ([§04](04-reasoning-models.md)), trained with reinforcement learning, now do much of this branching and backtracking inside their own thinking. As a result, explicit ToT scaffolding for general reasoning is mostly the dead weight P12 predicts. Search over *environment states* still pays when you have a cheap, trustworthy verifier, such as generating several candidate patches and keeping the one whose tests pass. That judgment is this compendium's synthesis, not a single source's finding.

### Self-improvement, and the 2025–26 turn: separate the checker from the maker

Reflection, Self-Refine (Madaan et al., Mar 2023) and Reflexion all have the model critique its own output. Huang et al. (Oct 2023, [arXiv 2310.01798](https://arxiv.org/abs/2310.01798)) issued an early warning: without *external* feedback, models struggled to fix their own reasoning, and sometimes made it worse. Production reports from 2025–26 explain why.

**Generator/evaluator separation.** Anthropic's March 2026 harness post names the problem: "agents reliably skew positive when grading their own work." The fix is structural (P8): keep the checker separate from the maker, with its own prompt, rubric and context. Separation alone isn't enough, because the evaluator "is still an LLM that is inclined to be generous towards LLM-generated outputs". Even so, "tuning a standalone evaluator to be skeptical turns out to be far more tractable than making a generator critical of its own work."

Cognition (Apr 2026) found the same thing in code review. Its review agent catches about 2 bugs per PR on PRs written by its own coding agent, and roughly 58% of them are severe. Review works best when coder and reviewer share *no* prior context, because then the reviewer reads only the diff with a short, fresh window (P3).

The common failure is what Anthropic calls the **early victory problem**: the verifier runs one or two checks, sees them pass, and declares success. Concrete criteria ("run the full test suite") and negative tests counter it.

**The planner–generator–evaluator harness (Anthropic, Mar 24, 2026).** Prithvi Rajasekaran designed this three-agent harness "taking inspiration from Generative Adversarial Networks":

```text
user prompt (1-4 sentences)
      │
      ▼
 PLANNER ──► product spec: ambitious scope, high-level design, few implementation details
      │
      ▼
 GENERATOR ◄── sprint contract: both sides agree what "done" means ──► EVALUATOR
   builds one feature at a time,                               drives the running app
   commits to git, writes files ───────── reads files ──────►  with Playwright; grades
      ▲                                                        criteria with hard thresholds
      └──────────── failed criteria + specific bug reports ◄───────────────┘
```

The planner stays at the product level on purpose. Granular technical details it got wrong "would cascade into the downstream implementation."

On a prompt to build a retro game maker, a solo agent ran 20 minutes for $9 and produced an app whose core play mode didn't work. The full harness ran 6 hours for $200 and produced a working one.

When Opus 4.6 arrived, the author removed components one at a time. The sprints were dropped, and the evaluator moved to a single pass at the end. The rule that came out of this is P12 in practice: "every component in a harness encodes an assumption about what the model can't do on its own," and "the evaluator is not a fixed yes-or-no decision. It is worth the cost when the task sits beyond what the current model does reliably solo."

**Read-only subagents, single-threaded writes (Cognition, Apr 22, 2026).** Walden Yan's follow-up to "Don't Build Multi-Agents" found that what works is "multiple agents contribute intelligence to a task while writes stay single-threaded": reviewers, advisors and search subagents feeding one writer ([§13](13-multi-agent.md)).

### Failure modes

- **Over-engineering.** You build a multi-step pattern where one good call would do. Add complexity only "when it demonstrably improves outcomes", and use evals to tell (P4, [§26](26-evals.md)).
- **Weak checks.** A gate that checks only format, or an evaluator asked "is this good?", rubber-stamps errors. You get the look of quality control without the substance.
- **Correlated samples.** Voting assumes independent errors, and identical prompts produce correlated ones.
- **Oscillation.** A generator that can't satisfy the critique bounces between drafts. Cap the iterations and define the fallback: return the best draft flagged for review, or escalate to a human.
- **Goodhart's law.** When a measure becomes a target, it stops being a good measure. Generators learn the rubric's quirks: in Anthropic's experiments, the phrase "museum quality" pushed designs toward one look.
- **Stale scaffolding (P12).** Sprints, forced plans and ToT prompts that compensated for weak models become overhead. Re-test each component whenever the model changes.

## Comparison

**Pattern-selection guide.** Start at the top and stop at the first row that fits. Each row further down costs more and hands more control to the model.

| If the task looks like… | Use | Why it fits | Watch for |
|---|---|---|---|
| One well-specified transformation (extract, classify, summarize) | Single augmented LLM call | Nothing to orchestrate | Prompt quality, grounding |
| Fixed steps whose intermediate results code can check | Prompt chaining + gates | Easier steps; errors caught early (P8) | Gates that check form, not substance |
| Distinct input types needing different prompts, tools or models | Routing | Specialization; cheap model for easy traffic (P3, P10) | Silent misroutes; keep a default route |
| Independent subtasks known in advance | Sectioning | Parallel speed, focused contexts | Hidden dependencies between parts |
| A high-stakes judgment that benefits from a second opinion | Voting / self-consistency | Averages out sampling variance (P4) | Correlated errors; N× tokens |
| Subtasks you can't list until you see the input | Orchestrator-workers | Runtime decomposition | Vague briefs, duplicated work |
| Clear quality criteria, and feedback measurably improves output | Evaluator-optimizer | A separate checker catches what the maker can't (P8) | Rubber-stamping, oscillation |
| Many tool calls whose inputs are knowable up front | Plan-and-execute / ReWOO / LLMCompiler | Big model called once; no transcript resent | Brittle plans; add replanning |
| A cheap, trustworthy verifier, and branches are cheap to try | Search (best-of-N, ToT/LATS-style) | Turns compute into accuracy (P10) | No real verifier means optimizing noise |
| Open-ended, unpredictable steps with environment feedback | Autonomous agent (ReAct loop) | Adapts at every step | Compounding errors, runaway cost; set stop conditions |
| A long build with subjective and objective quality bars | Planner–generator–evaluator | Spec up front, separate skeptical QA | Hours and hundreds of dollars; re-test on new models |
| Breadth-first, read-heavy research | Read-only subagents | Context isolation, parallel reading | ~15× chat tokens; see [§13](13-multi-agent.md) |

## What it didn't solve

Patterns tell you how to shape one workflow or one agent, and several (orchestrator-workers, subagents, planner–generator–evaluator) already put more than one model instance to work, each with its own context. What they don't tell you is when splitting the work across agents actually helps. Anthropic published a 90% gain from a multi-agent research system the day after Cognition published "Don't Build Multi-Agents." Sometimes one agent isn't enough. Or is it?

→ Next: [§13 Multi-Agent Systems](13-multi-agent.md)

## Check your understanding

**Q: Why does a gate between two prompt-chain steps improve reliability more than writing one better prompt?**

A gate is deterministic code that checks an intermediate output before the next step consumes it. Errors get caught at the step that made them, so they can't compound into later steps (P8), and each step runs on a smaller, focused prompt (P3). The cost is extra calls and latency, and a gate catches only what you can express in code. If the task doesn't break into checkable steps, or one call already passes your evals, chaining just adds latency.

**Q: Orchestrator-workers vs sectioning: what is the difference if both fan out to several LLM calls?**

Sectioning fixes the subtasks in code before any input arrives. In orchestrator-workers, an LLM invents the subtasks for each input at runtime. That handles tasks whose shape varies, but control flow moves to the model (P7), so behavior is less predictable and harder to test, and you pay for a planning call and a synthesis call. If you can list the subtasks in advance, use sectioning.

**Q: Why use a separate evaluator instead of asking the same model to review its own work?**

A self-review shares the context and assumptions that produced the mistake, and agents reliably grade their own work too generously. Self-correction without external feedback often fails (Huang et al., 2023). A separate evaluator, with its own skeptical prompt, rubric and fresh context, sees only the output, so it can catch what the maker rationalized. It costs extra calls and still needs tuning, because it is lenient by default. When a deterministic check exists, such as tests or a schema, prefer it: it's cheaper and can't be argued into passing.

**Q: What would happen if you used voting with five identical calls on a question the model systematically gets wrong?**

Voting helps only when errors are roughly independent across samples. Five calls with the same prompt and the same weights share the same bias, so most of them repeat the error, and a 5/5 majority looks like certainty. You pay five times the tokens for false confidence. Vary the prompts or models, or use a real verifier. Against a systematic error, voting is the wrong tool.

**Q: ReAct vs plan-and-execute: when does planning up front beat deciding step by step?**

ReAct picks each step after seeing the last observation. That makes it adaptive, but it calls the big model every turn and resends the transcript each time (P10). Plan-and-execute calls the planner once and leaves the work to cheap executors, and ReWOO and LLMCompiler can even run independent calls in parallel. It wins when the steps are predictable from the start. A plan written before any observation can be wrong, so you need replanning. For exploratory work like debugging, where each result changes the next move, ReAct fits better.

**Q: What would happen if you upgraded the planner–generator–evaluator harness to a much stronger model and kept every component?**

Each component encodes an assumption about what the model can't do alone, and a stronger model makes some of those assumptions false. In Anthropic's case, sprints and per-sprint QA stopped paying for themselves once Opus 4.6 could sustain long builds. Keeping them means paying hours and dollars for dead weight (P12), and it can even constrain the model. Remove one component at a time, measure the effect, and keep the evaluator only for tasks beyond what the model does reliably alone.

## Takeaways

- Every agentic pattern trades along four axes: error compounding (P8), context budget (P3), control-flow ownership (P7) and compute cost (P10).
- The Ng (2024), Anthropic (2024) and Gullí (2025) catalogs reduce to ten families. Learn the mechanisms, not the names.
- Use the cheapest row of the selection guide that fits. Move down only when evals say you must.
- Gates are code: deterministic checks between model steps are the cheapest reliability you can buy.
- Keep the checker separate from the maker. Self-grading skews positive, and a skeptical standalone evaluator is easier to tune.
- Voting and search help only when errors are independent or a real verifier exists.
- Reasoning models absorbed most of the 2023 reasoning scaffolds. Re-test every harness component when the model changes (P12).

## Sources

- Andrew Ng, "Four AI Agent Strategies That Improve GPT-4 and GPT-3.5 Performance," *The Batch*, Mar 20, 2024: https://www.deeplearning.ai/the-batch/how-agents-can-improve-llm-performance/
- Schluntz & Zhang (Anthropic), "Building effective agents," Dec 19, 2024: https://www.anthropic.com/engineering/building-effective-agents
- Antonio Gullí, *Agentic Design Patterns*, Springer Nature, 2025: https://link.springer.com/book/10.1007/978-3-032-01402-3
- Self-consistency (Wang et al., 2022): https://arxiv.org/abs/2203.11171
- ReAct (Yao et al., 2022): https://arxiv.org/abs/2210.03629
- Reflexion (Shinn et al., 2023): https://arxiv.org/abs/2303.11366
- Self-Refine (Madaan et al., 2023): https://arxiv.org/abs/2303.17651
- Plan-and-Solve (Wang et al., 2023): https://arxiv.org/abs/2305.04091
- Tree of Thoughts (Yao et al., 2023): https://arxiv.org/abs/2305.10601
- ReWOO (Xu et al., 2023): https://arxiv.org/abs/2305.18323
- "Large Language Models Cannot Self-Correct Reasoning Yet" (Huang et al., 2023): https://arxiv.org/abs/2310.01798
- LATS (Zhou et al., 2023): https://arxiv.org/abs/2310.04406
- LLMCompiler (Kim et al., 2023): https://arxiv.org/abs/2312.04511
- CodeAct (Wang et al., 2024): https://arxiv.org/abs/2402.01030
- LangChain, "Plan-and-Execute Agents," May 10, 2023: https://blog.langchain.com/plan-and-execute-agents/ ; "Planning Agents," Feb 13, 2024: https://blog.langchain.com/planning-agents/
- Rajasekaran (Anthropic), "Harness design for long-running application development," Mar 24, 2026: https://www.anthropic.com/engineering/harness-design-long-running-apps
- Phillips (Anthropic), "When to use multi-agent systems (and when not to)," Jan 23, 2026: https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them
- Phillips (Anthropic), "Multi-agent coordination patterns," Apr 10, 2026: https://claude.com/blog/multi-agent-coordination-patterns
- Yan (Cognition), "Multi-Agents: What's Actually Working," Apr 22, 2026: https://cognition.ai/blog/multi-agents-working
- Anthropic structured outputs docs (for evaluator and router JSON): https://platform.claude.com/docs/en/build-with-claude/structured-outputs
