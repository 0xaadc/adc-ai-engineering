# 21. Loop Engineering

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

The practice comes from Geoffrey Huntley's "Ralph Wiggum as a 'software engineer'" (Jul 14, 2025), a coding agent run in a bash `while` loop, and his follow-up "everything is a ralph loop" (Jan 17, 2026). The *label* comes from Addy Osmani's "Loop Engineering" (Jun 7, 2026), which places it "one floor above the harness." [§20](20-agent-runtime.md) left one agent alive, isolated and resumable, with a human still prompting it, checking it and prompting it again. Loop engineering automates that human role. Treat the label as emerging. The practice is real, but the term overlaps heavily with harness engineering ([§19](19-harness-engineering.md)) and already attracts hype. Osmani himself calls it "still early," says he is skeptical, and warns that "you absolutely have to be careful about token costs."

## Why this exists

Watch what a person does between agent runs. They pick the next task, paste in context, read the result, decide whether it is done, and write the next prompt. With a good harness and runtime, each run is reliable, so the run is no longer the bottleneck. The person is. Their attention, not the agent, now caps throughput.

Every part of that human cycle can be expressed as code or files:

- **Picking the task** becomes a plan file the agent reads and updates.
- **Supplying context** becomes specs and skills loaded every run ([§18](18-skills.md)).
- **Checking the result** becomes tests, type checks and linters.
- **Deciding "done"** becomes a stop condition evaluated by something other than the agent.

Once each piece is mechanical, a program can run the cycle. Three principles shape how that program must work:

- **P2 and P3:** the model is stateless and long contexts rot. So restarting each iteration with a fresh context, and keeping state on disk, beats one session that runs forever.
- **P8:** errors compound. So every iteration needs verification, and the verifier must not be the agent that did the work.
- **P12:** a simple loop gets better as models do. Huntley's Jan 2026 post says the original loop still holds, and that only after a year of better models could he realize its full vision.

## How it works (under the hood)

**Loop engineering** means designing the system that prompts the agent, instead of prompting it yourself. Osmani's definition: "Loop engineering is replacing yourself as the person who prompts the agent. You design the system that does it instead." He relays two practitioners' versions, quoted only in his post: Peter Steinberger's "You shouldn't be prompting coding agents anymore. You should be designing loops that prompt your agents," and Claude Code's Boris Cherny's "My job is to write loops."

```text
 floor 3  LOOP       when to run, what to feed it, how to check it, when to stop
 floor 2  HARNESS    one agent's environment: tools, hooks, sandbox, sensors   (§19, §20)
 floor 1  CONTEXT    which tokens go into each model call                      (§16)
 floor 0  MODEL      next-token probabilities                                  (§02)
```

### 1. The Ralph loop

Huntley: "In its purest form, Ralph is a Bash loop."

```bash
# Huntley's original (Jul 2025), verbatim:
while :; do cat PROMPT.md | claude-code ; done

# The same idea with today's Claude Code CLI, bounded. Run it in a sandbox (§20):
# nobody is watching the permission prompts.
for i in $(seq 1 50); do
  claude -p "$(cat PROMPT.md)" --permission-mode auto --max-turns 80 --max-budget-usd 3
  ./checks.sh && break   # crude: green checks double as the stop condition
done
```

The same loop in Python:

```python
import pathlib, subprocess

while True:                                           # pure Ralph: no stop condition
    prompt = pathlib.Path("PROMPT.md").read_text()    # re-read so you can tune it mid-run
    subprocess.run(["claude", "-p", prompt])          # new process = fresh context window
```

There is nothing clever in the loop itself. The work lives in the files it points at. `PROMPT.md` tells the agent to study the specs (`specs/*`, one file per topic) and the plan (`fix_plan.md`, a prioritized to-do list), choose "the most important thing," implement it, run the tests, update the plan and commit. Then the process exits and the next one starts cold. Huntley's rules:

- **"One item per loop."** Small units keep each context short and make each commit easy to judge.
- **Same stack every time.** He writes "deterministically allocate the stack the same way every loop": the same prompt, specs and plan, in the same order.
- **Tune, don't blame.** "Each time Ralph does something bad, Ralph gets tuned - like a guitar." When the agent keeps making the same mistake, you add a sign to the prompt, such as "Before making changes search codebase (don't assume not implemented)."

He sums up the technique as "deterministically bad in an undeterministic world." The failures are predictable, so you can find them and fix them. OpenAI's Feb 2026 harness-engineering post has Codex iterate on each PR "until all agent reviewers are satisfied," and says of that cycle, "effectively this is a Ralph Wiggum Loop."

### 2. Why a fresh context with state on disk works

Because the model is stateless (P2), a new process that reads the same files *is* the same agent, minus everything that piled up in the last session's context: failed attempts, stale tool output, wrong guesses. Those are exactly the tokens that degrade quality (P3). Huntley: "The more you use the context window, the worse the outcomes you'll get." Restarting is garbage collection for context.

The state has to live somewhere, so it moves to disk:

- **The plan or progress file** says what is done and what comes next.
- **Git history** records what changed and lets you revert a bad iteration.
- **Specs and skills** hold the knowledge the agent would otherwise guess.

Anthropic's long-running harness (Nov 2025) used the same shape: a progress file plus git history, and a JSON feature list whose `passes` flags the agent flips. They chose JSON because "the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files." Osmani's version is that the agent forgets but the repo doesn't. Huntley adds one trick: have the agent write *why* each test exists next to it, because "future loops will not have the reasoning in their context window."

If you come from data engineering, this is the stateless batch job versus the long-lived stateful stream processor. Ralph is the batch job: every run recomputes from durable inputs, so a bad run is cheap to discard. The cost is re-reading the specs every iteration, which Huntley calls "wasteful." Prompt caching recovers much of it (P10), because the prompt prefix is byte-identical each time. The 5-minute default cache lifetime is measured from request start, though, so iterations must begin close together for the cache to stay warm.

### 3. Back pressure

In streaming systems, **back pressure** is a slow consumer pushing back on a fast producer. Huntley borrows the term for automated checks that reject bad output and push the error back into the loop. Code generation is now cheap, and knowing whether the code is right is the hard part:

- "Specific programming languages have inbuilt back pressure through their type system."
- "Anything can be wired in as back pressure to reject invalid code generation": tests, type checkers, linters, security scanners, schema validators.
- Speed matters: "the wheel has got to turn fast." A two-minute test suite gets far more iterations than a twenty-minute one, so you balance check speed against how much the checks prove.

In Birgitta Böckeler's terms from [§19](19-harness-engineering.md), these are **computational sensors**. Back pressure works best when the error message says how to fix the problem, which is the custom-linter trick from OpenAI's harness post. It also has to be short: feed back the tail of the failure output, not 10,000 lines of logs, or the check itself rots the next context (P3). Huntley's Jan 2026 post "don't waste your back pressure" frames the whole job this way: "software engineering is now about preventing failure scenarios and preventing the wheel from turning over through back pressure to the generative function." The data-engineering analogue is a dbt test or data contract that fails the run, rather than a dashboard someone might look at.

### 4. Stop conditions

A loop needs three kinds of exit:

1. **Success.** The goal holds.
2. **Safety caps.** Maximum iterations, a spend cap, a wall-clock limit.
3. **Stall detection.** No progress for k iterations, for example the same failing test with the same error.

Most of the design effort goes into the first. Claude Code's `/goal` is the clearest example. You state a condition, such as "all tests in test/auth pass and the lint step is clean." After each turn, "a model checks whether the condition holds," and Claude keeps working until it does. That model is your configured small fast model, and the docs explain why it matters: "completion is decided by a fresh model rather than the one doing the work." Mechanically, `/goal` is a prompt-based Stop hook. Note its limit: the evaluator "does not call tools, so it can only judge what Claude has already surfaced in the conversation." So the docs advise a measurable end state, a stated check ("`npm test` exits 0") and constraints such as "no other test file is modified." Osmani reports that Codex has an equivalent `/goal`. Claude Managed Agents *outcomes* **(Preview)** do the same at platform level. A grader "uses a separate context window" to score the work against your rubric, and iterates for up to `max_iterations` (default 3, maximum 20).

The rule that follows from P4 and P8: **check with code wherever code can decide** (exit codes, file counts, an empty queue), and use a model judge only for what code cannot check. A judge is itself probabilistic.

### 5. Maker ≠ checker

The single most useful structural choice in a loop is separating the agent that does the work (the **maker**) from the one that judges it (the **checker**). Anthropic's Mar 2026 harness post found that "agents reliably skew positive when grading their own work," and that "tuning a standalone evaluator to be skeptical turns out to be far more tractable than making a generator critical of its own work." Osmani is blunter: "The model that wrote the code is way too nice grading its own homework."

The mechanism is context. The maker's context contains its own reasoning for why the code is right, so asking it to check means asking it to re-read its own argument. A checker with a fresh context, different instructions and ideally a different model does not share those blind spots. Best of all, it gathers its own evidence by running the tests itself instead of trusting the maker's transcript. This is the four-eyes principle and the separation of duties you know from data-quality checks owned by a different team than the pipeline (P8).

### 6. A loop driver

The snippet puts the pieces together. It re-reads `PROMPT.md` and the progress file each iteration, runs one fresh agent session (a stub here), applies back pressure, and stops on a separate goal check, a stall, the budget or the iteration cap.

```python
import pathlib, subprocess

MAX_ITERS, BUDGET_USD, MAX_STALLS = 30, 25.0, 3
PROGRESS = pathlib.Path("progress.md")          # the loop's memory lives on disk
git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True).stdout
BASE = git("rev-parse", "HEAD").strip()         # tests must look like this at the end

def run_agent(prompt: str) -> float:
    """Stub for one fresh session (e.g. `claude -p`): edits code + progress.md, returns $."""
    return 0.80

def check() -> tuple[bool, str]:
    """Back pressure. The guard stops the maker from passing by editing the tests."""
    if touched := git("diff", "--name-only", BASE, "--", "tests/"):
        return False, f"Tests are read-only. Revert your changes to: {touched}"
    r = subprocess.run(["pytest", "-q", "-x"], capture_output=True, text=True)
    return r.returncode == 0, r.stdout[-2000:]  # only the tail: protect the context (P3)

def goal_met() -> bool:
    """Stub for a separate checker: fresh model, sees the spec and the diff, not the chat."""
    return False

spent, feedback, stalls = 0.0, "", 0
for i in range(1, MAX_ITERS + 1):
    prompt = (pathlib.Path("PROMPT.md").read_text()            # tunable while running
              + "\n\n## Progress\n" + (PROGRESS.read_text() if PROGRESS.exists() else "")
              + "\n\n## Last check\n" + (feedback or "none yet"))
    spent += run_agent(prompt)                  # a new context every iteration (P2)
    ok, out = check()
    if ok and goal_met():                       # maker never decides it is done
        print(f"done after {i} iterations, ${spent:.2f}")
        break
    new_feedback = out if not ok else "Checks pass; the goal is not met yet."
    stalls = stalls + 1 if new_feedback == feedback else 0     # same result = no progress
    feedback = new_feedback
    if spent >= BUDGET_USD or stalls >= MAX_STALLS:
        print(f"stopped at iteration {i}: budget or stall, hand to a human")
        break
```

Notice what the human no longer does: pick tasks, paste errors, decide "done." Notice too what the human still owns: `PROMPT.md`, the specs, the tests, the caps and the checker.

### 7. Osmani's primitives

Osmani lists five pieces plus a memory, and notes that both Codex and Claude Code now ship all of them:

| Primitive | Job in the loop | Where it's covered |
|---|---|---|
| **Scheduled automations** | The heartbeat: discovery and triage on a cadence (Claude Code routines and `/loop`, Codex Automations) | [§20](20-agent-runtime.md) |
| **Git worktrees** | Parallel loops each get their own working directory and branch over one shared history, so their edits cannot collide on disk | Below |
| **Skills** | Project knowledge written once, read every run, instead of re-derived each cycle | [§18](18-skills.md) |
| **Connectors / MCP, plugins** | The loop acts in real tools: opens the PR, updates the ticket, posts to Slack | [§15](15-protocols-mcp-a2a.md) |
| **Sub-agents** | One explores, one implements, one verifies | [§13](13-multi-agent.md) |
| **External state file** | A markdown file or issue board that holds what is done and what is next | [§17](17-memory.md) |

### 8. Inner loop vs outer loop

The **inner loop** is the agent's own iterate cycle within a task: edit, check, fix. It is fast, automated and judged by back pressure. The **outer loop** is the human's: set goals and specs, design the checks, review what merges, and change the system when a failure pattern appears. Huntley: "When you see a failure domain – put on your engineering hat and resolve the problem so it never happens again." That is the [§19](19-harness-engineering.md) ratchet, applied one floor up.

Human judgment goes where it buys the most:

- what "done" means
- whether the checks actually prove it
- which failures deserve a new rule
- when to throw a bad state away (Huntley's `git reset --hard`)

Osmani names the three risks that grow as the loop improves:

- **Verification is still on you.** "Done" is a claim, not a proof.
- **Comprehension debt grows.** The faster the loop ships code you did not write, the less of the codebase you understand.
- **Cognitive surrender.** It becomes tempting to stop having opinions.

Throughput is capped by your review bandwidth, not by how many loops you can start.

### 9. The software factory (an aspiration)

Huntley's Jan 2026 post sketches the endpoint: "autonomous loops evolve products and optimise automatically for revenue generation. Evolutionary software - also known as a software factory." Osmani mentions "the factory model" as a neighboring idea. Treat this as a direction some practitioners are pushing, not a demonstrated result. The public evidence is demos and anecdotes, not measured outcomes across many teams.

### Failure modes

- **Infinite loops and oscillation.** The loop keeps failing the same test, or fix A breaks B and fix B breaks A. Defend with stall detection, iteration caps and escalation to a human.
- **Reward hacking.** The agent satisfies the check instead of the goal: it deletes or weakens tests, special-cases inputs, or exits early to fake success. METR (Jun 2025) documented frontier models replacing an evaluator with a stub that always reports success. Anthropic (Nov 2025) cites `sys.exit(0)` to fake passing tests, and found that learning such hacks in training generalized to broader misalignment. Huntley's diagnosis: "The models have been trained to chase their reward function, and the reward function is compiling code." Defenses: make tests read-only to the maker (a sandbox file permission, [§20](20-agent-runtime.md)), diff-guard test files as the driver does, run checks outside the agent's sandbox, and keep held-out tests the maker never sees, like a holdout set.
- **Drift and entropy.** The plan file stops matching the code, duplicate implementations appear (Huntley: "If you wake up to find that Ralph is doing multiple implementations, then you need to tune this step"), and conventions decay. Defend with periodic clean-up loops that regenerate the plan from the code and prune dead docs (OpenAI's "garbage collection" agents, [§19](19-harness-engineering.md)).
- **Runaway cost.** Parallel loops × iterations × tokens per iteration multiply fast, especially with sub-agents. Defend with per-iteration and per-loop hard caps, budgets stored durably ([§20](20-agent-runtime.md)), and cheaper models for exploration.
- **Merge conflicts between parallel loops.** Worktrees stop file collisions on disk, but not semantic ones: two branches can both reshape the same function. As Cognition's argument in [§13](13-multi-agent.md) goes, actions carry implicit decisions, and parallel writers make conflicting ones. Defend by partitioning work by area, using small PRs, rebasing often, and merging through a single-threaded queue.

### How loop, harness and context engineering nest

Each layer contains the one below. A loop iteration is one harness run. A harness run is a sequence of model calls whose contents are context engineering. The labels differ mainly in the *unit you design*: one call (context), one agent's environment across its calls (harness), or many runs over time with checks and stop rules (loop). The boundaries are blurry, and the practitioners say so. Huntley calls Ralph a way of getting the most out of models "through context engineering". Osmani calls a loop "The harness but it runs on a timer, it spawns little helpers, and it feeds itself." [§38](38-disciplines-map.md) maps the whole stack of labels and their status.

## Comparison

**Ways to keep an agent working**

| Approach | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| One long session | Keep prompting; compaction trims history | Simple; the agent keeps its reasoning | Context rot; you are the loop | Exploratory, judgment-heavy work |
| Ralph loop | Same prompt, fresh process, state on disk | Rot-free; trivial to build; improves with models | No stop rule; needs strong back pressure | Greenfield builds with good tests |
| Goal-checked session (`/goal`) | Separate model checks a condition after each turn | Maker ≠ checker for "done"; no driver code | Judge sees only the transcript | One task with a verifiable end state |
| Outcome-graded run (Managed Agents) | Grader in its own context scores a rubric, up to N iterations | Platform-managed, rubric-based | Preview; rubric quality is everything | One deliverable with a quality bar |
| Scheduled automation | Cron fires a fresh run that triages and dispatches | Finds work by itself | Needs external state and a triage inbox | Recurring maintenance, CI failures, issues |
| Parallel loops in worktrees | N loops on N branches | Throughput | Semantic conflicts, cost, review load | Independent, well-partitioned tasks |

**Stop conditions**

| Condition | Mechanism | Strength | Weakness |
|---|---|---|---|
| Deterministic check | Exit code, count, empty queue | Cheap, reliable, hard to argue with | Only as good as the tests, and can be gamed |
| Model judge | Separate model reads the condition and evidence | Handles fuzzy goals | Probabilistic, lenient, sees only what it's shown |
| Max iterations / wall clock | Counter or timer | Guarantees termination | Says nothing about quality |
| Spend cap | Durable cost counter | Bounds the worst case | Stops good runs too |
| Stall detection | Same error or no diff for k rounds | Catches stuck loops early | Needs a sensible notion of progress |

## What it didn't solve

You have now seen every piece on its own: the model, the API, tools, the agent loop, context, memory, skills, the harness, the runtime and finally the loop that drives it. Seeing pieces separately is not the same as knowing how they fit, where the seams are and which one breaks first. The next step is to build a small harness end to end, from the raw API call up.
→ Next: [§22 Build a Harness](22-build-a-harness.md)

## Check your understanding

**Q: Why does the Ralph loop start every iteration with a fresh context instead of continuing one long session?**

The model is stateless (P2), so a new process that reads the same files is the same agent without the accumulated failed attempts and stale tool output that degrade attention (P3). State moves to disk in the plan file, the specs and git, so nothing important is lost. The cost is re-reading the specs every time, which prompt caching partly offsets. For judgment-heavy exploratory work, where the session's own reasoning is the valuable state, one long session can be better.

**Q: What is back pressure in a loop, and why must the checks be fast?**

Back pressure is an automated check (tests, type checker, linter) that rejects bad output and feeds the error into the next iteration. It is what keeps a loop converging instead of compounding errors (P8). Each iteration waits on the checks, so slow checks mean fewer iterations per hour, which is Huntley's point that "the wheel has got to turn fast." You trade check speed against how much each check proves, so keep a fast check inside the loop and a slower full suite at merge time.

**Q: Why should the agent that wrote the code not be the one that decides it is done?**

The maker's context holds its own case for why the work is correct, and models "reliably skew positive when grading their own work." A checker with a fresh context, different instructions and ideally its own evidence (running the tests itself) avoids those blind spots. A separate checker still costs tokens and is still an LLM. So prefer deterministic checks, and use a model judge only for what code can't verify.

**Q: What would happen if a loop's only stop condition were "the test suite passes" and the agent could edit the tests?**

The quickest route to green is to delete, weaken or special-case the tests, and models trained against passing checks are known to take it (reward hacking). The loop would then stop "successfully" with broken code. Make tests read-only to the maker, diff-guard the test directory, run the checks outside the agent's sandbox and keep held-out tests. Pair the test check with a separate goal judge.

**Q: `/goal` vs a plain iteration cap: what does each guarantee?**

`/goal` runs a separate small model after each turn to judge whether your condition holds. It decides *success*, but probabilistically, and it sees only what the transcript shows. An iteration cap guarantees *termination* but says nothing about quality. You need both, plus a spend cap, because each covers a failure the others miss.

**Q: Why do parallel loops in separate git worktrees still conflict?**

Worktrees give each loop its own directory and branch, so edits cannot collide on disk. But two loops can make incompatible decisions about the same code, and those surface as merge conflicts or subtle breakage when the branches are combined. Partition work by area, keep PRs small, rebase often and merge through one queue. Don't run tightly coupled tasks in parallel at all.

**Q: Is "loop engineering" a new discipline or a new name for harness engineering?**

The practice is real and older than the name: agents have run in loops since 2023, Ralph since mid-2025. What the label adds is a focus on a different unit of design: the system that schedules runs, feeds them, checks them and stops them, one floor above a single harness. The overlap is large and the term is only a few months old, so judge it by its practices (back pressure, maker ≠ checker, stop conditions), not by the label.

## Takeaways

- Loop engineering means designing the system that prompts the agent instead of prompting it yourself. It is an emerging label for a real practice.
- The Ralph loop is the minimal form: the same prompt in a fresh process each time, with the state in files and git.
- Fresh context plus state on disk avoids context rot (P2, P3). The repo remembers what the model forgets.
- Back pressure (tests, types, lints) keeps a loop converging. Make it fast, short and impossible for the maker to switch off.
- Stop on a separate check, and always cap iterations, spend and stalls.
- Maker ≠ checker. Self-grading is lenient, so use deterministic checks first and an independent judge second (P8).
- Humans own the outer loop: specs, checks, the definition of done, and review. Review bandwidth is the real ceiling.

## Sources

- Geoffrey Huntley, "Ralph Wiggum as a 'software engineer'" (Jul 14, 2025): https://ghuntley.com/ralph/
- Geoffrey Huntley, "everything is a ralph loop" (Jan 17, 2026): https://ghuntley.com/loop/
- Geoffrey Huntley, "don't waste your back pressure" (Jan 17, 2026): https://ghuntley.com/pressure/
- Addy Osmani, "Loop Engineering" (Jun 7, 2026), the source of the Steinberger and Cherny quotes: https://addyosmani.com/blog/loop-engineering/
- Claude Code docs, "Keep Claude working toward a goal" (`/goal`): https://code.claude.com/docs/en/goal
- Claude Code docs, Scheduled tasks and `/loop`: https://code.claude.com/docs/en/scheduled-tasks
- Claude Code docs, CLI reference: https://code.claude.com/docs/en/cli-reference
- Claude Managed Agents docs, Define outcomes: https://platform.claude.com/docs/en/managed-agents/define-outcomes
- Anthropic, "Effective harnesses for long-running agents" (Nov 26, 2025): https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic, "Harness design for long-running application development" (Mar 24, 2026): https://www.anthropic.com/engineering/harness-design-long-running-apps
- OpenAI, "Harness engineering: leveraging Codex in an agent-first world" (Feb 11, 2026): https://openai.com/index/harness-engineering/
- METR, "Recent Frontier Models Are Reward Hacking" (Jun 5, 2025): https://metr.org/blog/2025-06-05-recent-reward-hacking/
- Anthropic, "From shortcuts to sabotage: natural emergent misalignment from reward hacking" (Nov 21, 2025): https://www.anthropic.com/research/emergent-misalignment-reward-hacking
- Git documentation, `git worktree`: https://git-scm.com/docs/git-worktree
