# 19. Harness Engineering

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

By 2026 harness engineering is an established discipline. It takes on the problem [§18](18-skills.md) left open: the loop, tools, context management, memory and skills all exist, but someone has to assemble them into one system and tune it until the agent stops repeating its mistakes. The practice grew out of Anthropic's long-running-agent work in late 2025, and the label caught on in February 2026. Who coined it is disputed. Mitchell Hashimoto's Feb 5 post uses it as his own term ("I've grown to calling this 'harness engineering'"), while HumanLayer and Addy Osmani credit LangChain's Vivek Trivedy.

| Date | Author, org | Contribution |
|---|---|---|
| Nov 26, 2025 | Justin Young, Anthropic | "Effective harnesses for long-running agents": initializer agent, feature list, progress file plus git, `init.sh` |
| Feb 5, 2026 | Mitchell Hashimoto | "My AI Adoption Journey": every agent mistake gets an engineered fix so it never recurs |
| Feb 11, 2026 | Ryan Lopopolo, OpenAI | "Harness engineering: leveraging Codex in an agent-first world": about 1M lines and 1,500 PRs, no hand-written code |
| Feb 17, 2026 | Vivek Trivedy, LangChain | "Improving Deep Agents with harness engineering": 52.8% → 66.5% on Terminal Bench 2.0, changing only the harness |
| Mar 10, 2026 | Vivek Trivedy, LangChain | "The Anatomy of an Agent Harness": Agent = Model + Harness |
| Mar 24, 2026 | Prithvi Rajasekaran, Anthropic | "Harness design for long-running application development": planner/generator/evaluator; resets vs compaction |
| Apr 2, 2026 | Birgitta Böckeler, Thoughtworks | "Harness engineering for coding agent users" (martinfowler.com): guides vs sensors, computational vs inferential |
| Apr 19, 2026 | Addy Osmani | "Agent Harness Engineering": a synthesis, and the ratchet |

## Why this exists

P6 says the model only proposes: it emits text, and code you control executes. So every agent already has a harness, even if it's only the `while` loop from [§11](11-agents.md). Something has to assemble the context, run the tools, store state, enforce limits and decide when the job is done. The question is whether that code is engineered or improvised. Three pressures made it a discipline:

1. **Errors compound over long runs (P8).** OpenAI reports single Codex runs working "upwards of six hours." At a per-step success rate p, n steps all succeed with probability pⁿ, so the checks between steps decide outcomes more than small differences between models do.
2. **The harness turned out to be a large lever.** LangChain held the model fixed (`gpt-5.2-codex`) and raised its agent from 52.8% to 66.5% on Terminal Bench 2.0 (89 terminal tasks) by changing only prompts, tools and middleware.
3. **Human attention became the scarce resource.** OpenAI's team found progress was slow "not because Codex was incapable, but because the environment was underspecified." The fix "was almost never 'try harder'"; instead they asked "what capability is missing, and how do we make it both legible and enforceable for the agent?"

A hype check: the definition is deliberately broad (Böckeler calls it "a very wide definition"), and much of the practice is old: CI, linters, docs, a regression test for every incident. What's new is that the consumer is an LLM that reads error messages and docs *as instructions*, and that the harness is tuned continuously against observed failures.

## How it works (under the hood)

### Agent = Model + Harness

Trivedy's definition: "Agent = Model + Harness. If you're not the model, you're the harness." A **harness** is "every piece of code, configuration, and execution logic that isn't the model itself." Each component exists because a raw model can't keep state, run code, see fresh information or set up an environment on its own. His anatomy lists:

- **System prompts**, plus always-loaded files like `AGENTS.md`.
- **Tools, skills and MCP servers**, and their descriptions ([§10](10-tool-use.md), [§15](15-protocols-mcp-a2a.md), [§18](18-skills.md)).
- **Bundled infrastructure:** a filesystem with git for durable state, a sandbox and a browser, with bash and code execution as the general-purpose tool.
- **Orchestration logic:** subagent spawning, handoffs, model routing ([§13](13-multi-agent.md)).
- **Hooks and middleware** for deterministic execution: compaction, continuation, lint checks.

```text
+------------------------------- HARNESS --------------------------------+
| GUIDES (before acting): system prompt, AGENTS.md map, skills index,    |
|                         memory files, plan / progress files            |
|                                   |                                    |
|   +-------------------- agent loop (while) -----------------------+    |
|   |  assemble context --> MODEL --> tool call? --no--> stop hook  |    |
|   |        ^                          | yes        (done? verify?)|    |
|   |        |                          v                           |    |
|   |        |                   pre-tool hooks --deny--+           |    |
|   |        |                          | allow         |           |    |
|   |        |                          v               |           |    |
|   |        |                   tool executor          |           |    |
|   |        |                          |               |           |    |
|   |        |                          v               |           |    |
|   |        +-- tool_result <-- post-tool hooks <------+           |    |
|   |            (+ lint errors)  (lint, tests, offload big output) |    |
|   +---------------------------------------------------------------+    |
| TOOLS: built-ins, MCP servers, skill scripts                           |
| INFRA: filesystem + git, bash / code exec, sandbox, browser            |
| ORCHESTRATION: subagents, handoffs, model routing                      |
| SENSORS (after acting): tests, linters, type checks, LLM reviewers     |
+------------------------------------------------------------------------+
```

Böckeler separates the harness a product ships (Claude Code's own system prompt and built-in tools) from the **outer harness** you build around it for your codebase: `AGENTS.md`, skills, hooks, custom linters. Most of what follows is outer-harness work.

### Guides and sensors (Böckeler)

Böckeler classifies harness controls on two axes. **Guides** are feedforward: they steer the agent *before* it acts, raising the odds of a good first attempt. **Sensors** are feedback: they observe *after* it acts so the agent can self-correct. Either kind can be **computational** (deterministic, run on a CPU, milliseconds to seconds) or **inferential** (an LLM judging meaning: slower, costlier, probabilistic).

| | Computational | Inferential |
|---|---|---|
| **Guides** (feedforward) | Code mods (e.g. OpenRewrite recipes behind a tool), bootstrap scripts, LSP code intelligence | `AGENTS.md` conventions, skills, specs |
| **Sensors** (feedback) | Tests, linters, type checkers, ArchUnit structural tests run from a hook | AI code review, LLM-as-judge, a separate evaluator agent |

You need both. With feedback only you get "an agent that keeps repeating the same mistakes"; with feedforward only, "an agent that encodes rules but never finds out whether they worked." Sensors work best when their output is written for an LLM, such as a linter message that says how to fix the problem, which she calls "a positive kind of prompt injection." In data-pipeline terms this is the split between a data contract, declared before the load, and data-quality tests, run after it.

Three further ideas from the article:

- **The steering loop.** The human's job is to iterate on the harness: "Whenever an issue happens multiple times, the feedforward and feedback controls should be improved."
- **Keep quality left.** Run fast sensors before commit, expensive ones (mutation testing, broad review) after integration, and drift sensors (dead code, dependency scans) continuously.
- **Harnessability.** Strong typing gives you a free sensor, clear module boundaries allow architecture rules, and opinionated frameworks shrink what can go wrong. Legacy code is the hard case: "the harness is most needed where it is hardest to build."

### OpenAI's practices

OpenAI's team built an internal product in five months with no manually written code: about a million lines and 1,500 merged PRs, from three engineers who grew to seven. Their harness rests on four practices:

- **`AGENTS.md` as a map, not a manual.** One giant instruction file failed four ways: it crowded out the task, it made everything "important" so nothing was, it rotted instantly, and it couldn't be checked mechanically. Their `AGENTS.md` is "roughly 100 lines" and points into a structured **`docs/` directory treated as the system of record**: design docs, architecture maps, quality grades and checked-in execution plans. It's the same progressive disclosure as skills ([§18](18-skills.md)). CI checks the docs for freshness and cross-links, and a recurring "doc-gardening" agent fixes stale ones.
- **Agent legibility.** "From the agent's point of view, anything it can't access in-context while running effectively doesn't exist." So the app boots per git worktree, and each worktree gets Chrome DevTools access and an ephemeral observability stack the agent can query with LogQL and PromQL. A goal like "service startup completes in under 800ms" becomes something the agent can check itself.
- **Mechanically enforced architecture.** Each domain has fixed layers with one-way dependencies (Types → Config → Repo → Service → Runtime → UI), enforced by custom linters and structural tests, and "we write the error messages to inject remediation instructions into agent context."
- **Golden principles and garbage collection.** Agents copy whatever patterns exist, bad ones included. The team once spent every Friday cleaning up "AI slop." They replaced that with "golden principles" encoded in the repo and recurring background Codex tasks that open small refactoring PRs, most of which "can be reviewed in under a minute and automerged." Pull requests are driven to completion by agent-to-agent review in a loop the post calls "effectively... a Ralph Wiggum Loop" ([§21](21-loop-engineering.md)).

The team says this "should not be assumed to generalize without similar investment."

### The ratchet

Hashimoto's definition is the core habit: "anytime you find an agent makes a mistake, you take the time to engineer a solution such that the agent never makes that mistake again." The fix is either a line in `AGENTS.md` (in his Ghostty repo, "each line in that file is based on a bad agent behavior") or a programmed tool, such as a screenshot script. Osmani calls this **the ratchet**: "every line in a good AGENTS.md should be traceable back to a specific thing that went wrong." It comes with a release valve: "You only remove them when a capable model has made them redundant" (P12).

The same fix can sit at different heights, and higher means more deterministic:

1. **Prompt line** in `AGENTS.md`: cheap, but the agent may still ignore it.
2. **Skill**: for a multi-step procedure the agent keeps getting wrong.
3. **Tool or script**: the agent calls it instead of improvising.
4. **Hook**: runs on every relevant action, so it can't be forgotten.
5. **Linter or structural test**, with an error message that says how to fix the problem.
6. **Architectural constraint**: the mistake becomes impossible to express.

OpenAI's version: "When documentation falls short, we promote the rule into code."

### Hooks and middleware

**Hooks** (LangChain calls them middleware) are functions the harness runs at fixed points in the loop: before a tool call, after it, when the agent tries to stop, before compaction. They hold the computational sensors and hard guardrails, because they run every time regardless of what the model decides (P6). Here is the mechanism wrapped around the tool executor of a raw Messages API loop:

```python
import re, subprocess

RM_RF = re.compile(r"\brm\s+-\w*(r\w*f|f\w*r)", re.I)  # rm -rf, rm -fr, rm -Rf ...

def block_rm_rf(call):
    """Pre-tool hook: return a reason to deny the call, or None to allow it."""
    if call.name == "bash" and RM_RF.search(call.input.get("command", "")):
        return "Blocked by policy: recursive force-delete. Remove specific paths instead."
    return None

def lint_python(call, output):
    """Post-tool hook: after a .py edit, run the linter and append its findings."""
    path = call.input.get("path", "")
    if call.name in ("write_file", "edit_file") and path.endswith(".py"):
        lint = subprocess.run(["ruff", "check", path], capture_output=True, text=True)
        if lint.returncode != 0:  # the model reads this on its next turn
            output += "\n\nLinter errors, fix before moving on:\n" + lint.stdout
    return output

PRE_HOOKS, POST_HOOKS = [block_rm_rf], [lint_python]

def run_tool(call, execute):
    """Middleware around the real executor; returns a tool_result block."""
    for hook in PRE_HOOKS:
        reason = hook(call)
        if reason:  # denied: the model sees why and can adapt its plan
            return {"type": "tool_result", "tool_use_id": call.id,
                    "content": reason, "is_error": True}
    output = execute(call.name, call.input)  # the only line with side effects (P6)
    for hook in POST_HOOKS:
        output = hook(call, output)
    return {"type": "tool_result", "tool_use_id": call.id, "content": output}

# Inside the agent loop from §11, after each model response `resp`:
#   results = [run_tool(b, execute) for b in resp.content if b.type == "tool_use"]
#   messages.append({"role": "user", "content": results})  # all results, one message
```

A denied call returns to the model as an error *result*, not an exception, so the model can change plans. The linter's complaint arrives as tool output, so the model fixes it on the next turn without a human. With OpenAI's Responses API the wrapper is identical, and only the envelope differs: results go back as `function_call_output` items.

Products expose the same hook points as configuration. In Claude Code's `settings.json`, a hook that exits with code 2 blocks a `PreToolUse` call (its stderr goes to Claude), surfaces stderr after a `PostToolUse`, and on `Stop` sends Claude back to work, which makes it a continuation hook:

```json
{
  "hooks": {
    "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "if": "Bash(rm *)",
      "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/block-rm.sh"}]}],
    "PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command",
      "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/lint.sh"}]}]
  }
}
```

LangChain's Terminal Bench gains came largely from middleware like this: a `PreCompletionChecklistMiddleware` that makes the agent verify against the task spec before it exits, and a `LoopDetectionMiddleware` that counts edits per file and nudges the agent to rethink, breaking "doom loops."

A caution: a regex blocklist is a speed bump, not containment. `find / -delete` or a Python one-liner walks past it. Containment comes from the sandbox and least privilege (P9, [§20](20-agent-runtime.md), [§32](32-security-guardrails.md)).

### Long-running harness designs (Anthropic)

Anthropic's Nov 2025 post starts from the shift-worker problem: each new context window "begins with no memory of what came before." Given only "build a clone of claude.ai," Opus 4.5 on the Claude Agent SDK fell short even with compaction. It tried to one-shot the app, declared victory early, marked features done without end-to-end tests, and lost time working out how to run the app. The harness answers each failure:

- **An initializer agent** runs once. It writes `init.sh` to start the dev server, `claude-progress.txt` as a log of agent work, an initial git commit, and a **feature list** of more than 200 end-to-end features, all marked failing. JSON was chosen because "the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files":

```json
{
  "category": "functional",
  "description": "New chat button creates a fresh conversation",
  "steps": ["Navigate to main interface", "Click the 'New Chat' button",
            "Verify a new conversation is created",
            "Check that chat area shows welcome state",
            "Verify conversation appears in sidebar"],
  "passes": false
}
```

- **A coding agent** handles every later session. It reads the progress file and `git log`, runs `init.sh` and a smoke test, implements *one* failing feature, tests it like a user through browser automation, flips `passes`, then commits and updates the progress file. Its prompt says "It is unacceptable to remove or edit tests."

The Mar 2026 post adds two lessons:

- **Separate maker and checker (P8).** "When asked to evaluate work they've produced, agents tend to respond by confidently praising the work." A **planner** expands a 1–4 sentence prompt into a product spec, a **generator** builds it, and an **evaluator** drives the running app with Playwright and fails any criterion below a hard threshold. The generator and evaluator negotiate a "sprint contract," defining what done means, before coding. The evaluator was lenient at first too, but "tuning a standalone evaluator to be skeptical turns out to be far more tractable than making a generator critical of its own work." It costs real money: 20 minutes and $9 for the solo run, 6 hours and $200 for the full harness.
- **Resets vs compaction.** **Compaction** summarizes history in place so the same agent continues. A **context reset** starts a fresh agent from a structured handoff. Sonnet 4.5 showed "context anxiety" (wrapping up early near its believed context limit) strongly enough that resets were essential. Opus 4.5 "largely removed that behavior," so resets were dropped, and with Opus 4.6 the sprint structure went too.

The post's general lesson is P12 in one sentence: "every component in a harness encodes an assumption about what the model can't do on its own, and those assumptions are worth stress testing." Test components by removing them one at a time.

### Model–harness co-training, and its overfitting

Claude Code and Codex are "post-trained with models and harnesses in the loop" (LangChain). That creates a cycle: a useful primitive is found, added to the harness, and used to train the next model, which then improves *inside that harness*. The side effect is overfitting. LangChain cites the `apply_patch` editing tool from OpenAI's Codex prompting guide: change the editing logic and performance drops, though "a truly intelligent model should have little trouble switching between patch methods."

So a model's home harness is a strong default but not necessarily the best one for your task. LangChain reported (Mar 2026) that on the Terminal Bench 2.0 leaderboard, Opus 4.6 in Claude Code scored "far below" Opus 4.6 in other harnesses; HumanLayer put it at #33 versus #5 **(⚠ verify: leaderboard snapshot positions)**. Two consequences follow. A benchmark score measures a model-harness pair, never the model alone, so always ask "in which harness?" ([§26](26-evals.md)). And when you swap models, re-tune the harness.

### Harness engineering as context engineering in practice

Three sources describe the same nesting. LangChain: "Harnesses today are largely delivery mechanisms for good context engineering." Böckeler: a user harness "is a specific form of context engineering." HumanLayer (Mar 12, 2026): "a subset of context engineering." Most of the harness's job is deciding which tokens are in the window at each step ([§16](16-context-engineering.md)): the map, the skill bodies, the linter messages, the compacted history. One part isn't about tokens at all, though. The harness also decides what the model's outputs are *allowed to do* (P6, P9) and how results are *verified* (P8). A working view of the nesting:

```text
loop engineering      design the system that prompts agents: schedules, stop rules   (§21)
 └ harness engineering   everything around one agent: tools, hooks, sandbox, checks   (§19)
    └ context engineering   which tokens are in the window at each step               (§16)
       └ prompt engineering    the wording of the instructions themselves             (§5)
```

[§38](38-disciplines-map.md) maps all the "-engineering" labels and their status.

### Failure modes

- **Harness bloat.** Every click of the ratchet adds tokens, latency or a check, and without pruning you rebuild the one-big-`AGENTS.md` failure.
- **Gaming the sensor.** An agent pushed to pass may weaken the test instead of fixing the code, which is why Anthropic's prompt forbids editing tests. Keep sensors out of the agent's write path where you can.
- **Lenient checkers.** An evaluator is still an LLM "inclined to be generous towards LLM-generated outputs," so calibrate it against human judgment by reading its logs.
- **Silent sensors.** As Böckeler asks, "If sensors never fire, is that a sign of high quality or inadequate detection mechanisms?"
- **Overfitting and cost.** A harness tuned to one benchmark may not transfer, and the full three-agent run cost over 20× a solo run. Add structure only where the solo agent fails.

## Comparison

**Harnesses you can use or build on (as of Oct 2026)**

| Harness | What it is | Who supplies the harness | Main extension points | Choose when |
|---|---|---|---|---|
| Claude Code | Anthropic's coding agent (terminal, IDE, desktop, web) | Anthropic; you add the outer harness | `CLAUDE.md`, skills, hooks, subagents, MCP, plugins, permission modes | Interactive and autonomous coding on Claude models |
| Codex | OpenAI's coding agent (CLI, IDE, cloud); models post-trained in it | OpenAI; you add the outer harness | `AGENTS.md`, repo-embedded skills, MCP | Coding on OpenAI models; agent-first repos |
| Deep Agents | LangChain's open-source harness library (Python, JS), model-agnostic | You, on LangChain's primitives | Middleware, planning, filesystem, subagents, skills | A harness you can read, fork and tune across models |
| Claude Agent SDK | Claude Code's harness packaged as a library | Anthropic's loop and built-in tools; you host and extend | Callback hooks, custom tools, MCP, subagents, sessions | Your own product on a batteries-included harness |
| OpenAI Agents SDK | Minimal primitives: agents, handoffs or agents-as-tools, guardrails, sessions, tracing, sandbox agents | Mostly you | Guardrails, lifecycle hooks, tools, handoffs | Few abstractions; you own most of the design |

**Context reset vs compaction**

| | Compaction | Context reset |
|---|---|---|
| How it works | Summarize earlier history in place; the same agent continues | Start a fresh agent; pass state through a handoff (progress file, git log, feature list) |
| Strength | Continuity; no extra orchestration | A clean slate; cures "context anxiety" and accumulated noise |
| Weakness | Lossy summaries; the anxiety can persist | The handoff must carry enough state; more orchestration, tokens and latency |
| Choose when | The model handles long contexts well (Anthropic dropped resets with Opus 4.5) | The model degrades or rushes near its limit, or work spans many windows |

## What it didn't solve

A harness is code, and it has to run somewhere. A process on your laptop dies with the laptop. An agent working for six hours has to survive crashes and restarts without losing progress or repeating side effects. It needs a sandbox that contains what its commands can touch, and many sessions need to run side by side. Harness engineering says *what* wraps the model, not *where* that wrapper runs or how it stays durable and contained.

→ Next: [§20 Agent Runtime](20-agent-runtime.md)

## Check your understanding

**Q: Why can the same model score very differently on a benchmark depending on the harness?**

The model only proposes tokens (P6). The harness decides what context it sees, which tools exist and in what format, what gets verified, and when it may stop, and over many steps those choices compound (P8). That's how LangChain gained 13.7 points on Terminal Bench 2.0 with the model fixed. Co-training adds a twist: models overfit to their home harness, so a new harness can help or hurt. Read every score as model plus harness.

**Q: Guides vs sensors: what goes wrong if you build only one kind?**

With guides only, the agent follows rules probabilistically and nobody checks whether they worked. With sensors only, the agent keeps making the same mistakes and burns turns getting caught. Guides raise first-attempt quality, and sensors catch what slips through. Prefer computational versions of both where they exist, because they're deterministic and cheap.

**Q: What would happen if OpenAI's team had kept a single 1,000-line AGENTS.md instead of a 100-line map?**

The file would crowd the task out of context (P3) and dilute every rule, since when everything is "important" nothing is. It would also go stale, with no mechanical way to tell live rules from dead ones. A short map plus a versioned `docs/` system of record gives progressive disclosure, and CI can check those docs. A single file works only for tiny projects with a handful of rules.

**Q: Why does Anthropic's harness use a separate evaluator agent instead of asking the generator to check its own work?**

Agents grade their own output too leniently and talk themselves out of real bugs. A separate checker (P8) can be tuned to be skeptical without making the generator timid, and it hands the generator concrete feedback to iterate against. The price was 6 hours and $200 against 20 minutes and $9 in one test, so drop the evaluator for tasks the current model already does reliably on its own.

**Q: When should you prefer a context reset over compaction?**

Prefer a reset when the model degrades or rushes as its window fills ("context anxiety"), or when work spans many windows and each session should start clean. The handoff (progress file, git history, feature list) must carry all the state, because nothing else does. Compaction is simpler and keeps continuity, and Anthropic switched back to it once Opus 4.5 stopped showing the anxiety. Re-test the choice with each new model (P12).

**Q: Why is a pre-tool hook that blocks `rm -rf` necessary but not sufficient?**

The hook runs on every call regardless of what the model decides, so it reliably stops the obvious command and tells the model why (P6). But a blocklist can't enumerate every destructive command: `find -delete`, a Python one-liner or a script the agent writes all get past it. Since any text in context can steer the model (P9), you also need containment underneath: a sandbox, least-privilege credentials, and checkpoints.

**Q: How does the ratchet interact with the bitter lesson (P12)?**

The ratchet adds a permanent fix for each observed mistake, so the harness only grows. P12 says many of those fixes are workarounds for today's model weaknesses and become dead weight as models improve. Anthropic's harness shed context resets and sprint decomposition across two model generations. So tie every rule to the failure that created it, and remove rules when you upgrade models and your evals show they no longer help.

## Takeaways

- Agent = Model + Harness: everything that isn't the model (prompts, tools, infrastructure, orchestration, hooks) is the harness, and you own it.
- The harness is a large lever: with the model fixed, harness changes alone moved one agent from 52.8% to 66.5% on Terminal Bench 2.0.
- Pair guides (feedforward) with sensors (feedback), and prefer computational controls to inferential ones where you can.
- Keep `AGENTS.md` a short map into a versioned `docs/` system of record, make logs, UI and metrics legible to the agent, and write linter messages that say how to fix the problem.
- Ratchet: turn each repeated mistake into a permanent, preferably deterministic, fix, and remove fixes that newer models make redundant (P12).
- For long runs: state in files and git, one feature at a time, a checker separate from the maker, and resets or compaction chosen per model.
- Models are co-trained with their home harness and can overfit to it, so benchmark scores describe a model-harness pair.
- Harness engineering is mostly context engineering in practice, plus control over which actions are allowed and how results are verified.

## Sources

- Anthropic Engineering, Justin Young, "Effective harnesses for long-running agents" (Nov 26, 2025): https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Mitchell Hashimoto, "My AI Adoption Journey" (Feb 5, 2026): https://mitchellh.com/writing/my-ai-adoption-journey
- OpenAI, Ryan Lopopolo, "Harness engineering: leveraging Codex in an agent-first world" (Feb 2026): https://openai.com/index/harness-engineering/
- LangChain, Vivek Trivedy, "Improving Deep Agents with harness engineering" (Feb 17, 2026): https://blog.langchain.com/improving-deep-agents-with-harness-engineering/
- LangChain, Vivek Trivedy, "The Anatomy of an Agent Harness" (Mar 10, 2026): https://blog.langchain.com/the-anatomy-of-an-agent-harness/
- HumanLayer, "Skill Issue: Harness Engineering for Coding Agents" (Mar 12, 2026): https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents
- Anthropic Engineering, Prithvi Rajasekaran, "Harness design for long-running application development" (Mar 24, 2026): https://www.anthropic.com/engineering/harness-design-long-running-apps
- Birgitta Böckeler, "Harness engineering for coding agent users," martinfowler.com (Apr 2, 2026): https://martinfowler.com/articles/harness-engineering.html
- Addy Osmani, "Agent Harness Engineering" (Apr 19, 2026): https://addyosmani.com/blog/agent-harness-engineering/
- Claude Code docs, Hooks reference: https://code.claude.com/docs/en/hooks
- Claude Agent SDK docs, Hooks: https://code.claude.com/docs/en/agent-sdk/hooks
- OpenAI Agents SDK documentation: https://openai.github.io/openai-agents-python/
- AGENTS.md format: https://agents.md
