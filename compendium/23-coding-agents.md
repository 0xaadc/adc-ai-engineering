# 23. Coding Agents and Agentic Engineering

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

Part 6 covers agent archetypes, the specific kinds of agent built from the parts in Parts 4 and 5. [§22](22-build-a-harness.md) built a harness from scratch, and this section studies the archetype where that machinery matured first. A **coding agent** is an agent that can read, edit and run code in a loop until a goal is met. Coding became the dominant agent category of 2025–26 because code is the ideal domain for P8: compilers, type checkers, linters and tests give cheap, computational verification after every step. The road there had four stages, and each one removed a human hand-off:

| Stage | What the tool does | Who runs the code | Examples |
|---|---|---|---|
| Autocomplete | Predicts the next lines as you type | You | GitHub Copilot preview (Jun 29, 2021), built on OpenAI's Codex *model* |
| Chat in the IDE | You paste code and errors in and copy answers out | You | Copilot Chat, Cursor (2023) |
| Agentic IDEs and CLIs | Searches, edits and runs tests in a loop on your machine | The agent, with your approval | Copilot agent mode (Feb 6, 2025); Claude Code preview (Feb 24, 2025), **(GA)** May 22, 2025; Codex CLI (Apr 16, 2025); Gemini CLI (Jun 25, 2025) |
| Cloud and background agents | Takes an assigned task, works in a remote sandbox, opens a PR | The agent, in a sandbox | Devin (Mar 2024); Codex cloud (May 2025); Copilot coding agent (May 19, 2025); Claude Code on the web (Oct 20, 2025, **(GA)** as "cloud sessions" Sep 23, 2026) |

## Why this exists

In the chat era the human was the tool executor. They copied the suggestion, ran it and pasted the error back, so every iteration cost a round trip through a person. Simon Willison names what removed that hand-off: "Code execution is the defining capability that makes agentic engineering possible." Four properties made software the first domain where agents worked:

1. **Cheap verifiers (P8).** At a per-step success rate of 0.95, twenty unchecked steps all succeed only 36% of the time (0.95²⁰). A compiler error or failing test catches a bad step within seconds, so the agent retries that step instead of building on it.
2. **Code is text in files.** The model reads and writes tokens (P1), and a repository is tokens the agent can search, read and diff.
3. **Git provides free checkpoints.** Any state can be saved, compared and undone, so letting an agent experiment is cheap.
4. **Training targeted this loop.** Reinforcement learning with verifiable rewards ([§04](04-reasoning-models.md)) needs a pass/fail signal, and tests provide one. OpenAI's Codex model (May 2025) was trained to "iteratively run tests until it receives a passing result."

The consequence shapes the rest of this section. Writing code got cheap, but knowing that the code is right did not. Willison: "Delivering new code has dropped in price to almost free... but delivering good code remains significantly more expensive than that."

## How it works (under the hood)

### Anatomy: the loop plus a handful of tools

A coding agent is the `while` loop from [§11](11-agents.md), with tools chosen for software work. The model proposes each action and the harness executes it (P6). The SWE-agent paper (May 2024) called this tool layer the **agent-computer interface (ACI)** and showed that designing it for the model, rather than for humans, raises success rates.

```text
 task + system prompt + AGENTS.md ──▶ MODEL ──▶ tool call?  ── no ──▶ done? (verify!)
                                        ▲          │ yes
        ┌───────────────┬───────────────┼──────────┴────┬─────────────────┐
        ▼               ▼               │               ▼                 ▼
     SEARCH           READ              │             EDIT               RUN
  grep / glob      read_file            │      str_replace / patch   bash: tests,
  (find code)   (numbered lines)        │      (exact, unique)       build, lint
        └───────────────┴──── tool_result ◀─────────────┴─────────────────┘
                    (matches, file text, "Edited", exit code + tail of output)

 GIT underneath: commit = checkpoint · diff = review surface · reset/revert = undo
```

### Finding code: agentic search vs a pre-built index

In **agentic search**, the agent finds code the way a developer does: grep for an identifier, glob for file names, read the hits, follow the imports. Anthropic explains why Claude Code works this way rather than relying on the embedding retrieval of [§09](09-rag.md). CLAUDE.md files are "naively dropped into context up front, while primitives like glob and grep allow it to navigate its environment and retrieve files just-in-time, effectively bypassing the issues of stale indexing and complex syntax trees." Code is unusual data:

- **Identifiers are exact.** `parse_invoice_v2` is a string, not a topic, so grep finds every use while similarity search returns code that is merely *about* invoices.
- **Indexes go stale.** An embedding index is a materialized view that is out of date after every commit, including the agent's own edit a minute ago.
- **Chunking breaks code.** Cline (May 2025): "when you chunk code for embeddings, you're literally tearing apart its logic."

The price of agentic search is more tool calls and tokens (P3, P10), and the question isn't settled. Cursor reported (Nov 2025, vendor-measured) that adding its trained semantic search alongside grep raised answer accuracy by 12.5% on average, with larger gains in big codebases. Its conclusion was that the combination works best: grep for exact symbols, semantic search for "where do we handle auth?" in a repository too large to explore. A P12 footnote: as of Oct 2026, Claude Code on macOS and Linux leaves out its dedicated Grep and Glob tools by default and calls embedded `ugrep` and `bfs` through Bash. The general tool replaced the special ones.

### Editing code: why exact-match replacement won

The same change can travel in several wire formats:

```text
1. Whole file            the model re-emits every line of calc.py

2. Search/replace block  (Aider "diff" format)
   calc.py
   <<<<<<< SEARCH
       return a - b
   =======
       return a + b
   >>>>>>> REPLACE

3. str_replace call      (Claude's text editor tool; Claude Code's Edit tool)
   {"command": "str_replace", "path": "calc.py",
    "old_str": "    return a - b", "new_str": "    return a + b"}

4. Patch operation       (OpenAI's apply_patch tool, V4A diff)
   {"type": "update_file", "path": "calc.py",
    "diff": "@@\n def add(a, b):\n-    return a - b\n+    return a + b\n"}
```

Whole-file output is slow and costly (P10), and models get lazy with it. Aider saw GPT-4 Turbo replace whole sections with "# … original code here …" comments. Formats 2–4 make the model **quote what it replaces**, which turns errors into loud failures. If `old_str` isn't in the file, the model is working from a stale or imagined version, and the edit is refused instead of corrupting the file. Claude Code's Edit tool "doesn't use regex or fuzzy matching," and `old_str` must match exactly once, so ambiguity is refused too.

Both vendors ship this mechanism as a client-executed tool:

- **Anthropic** offers `{"type": "text_editor_20250728", "name": "str_replace_based_edit_tool"}` with `view`, `create`, `str_replace` and `insert` commands.
- **OpenAI's** Responses API offers `{"type": "apply_patch"}`. Its `create_file`, `update_file` and `delete_file` operations carry V4A diffs that your harness applies before it returns an `apply_patch_call_output`.

Models overfit to the format they were trained with ([§19](19-harness-engineering.md)), so keep that format.

### Running the code: tests as the feedback signal

This minimal coding agent has three tools, a stub model that replays a typical session, and the [§11](11-agents.md) loop. It runs offline.

```python
import pathlib, subprocess, sys, tempfile
ROOT = pathlib.Path(tempfile.mkdtemp()).resolve()          # the agent's whole world
(ROOT / "calc.py").write_text("def add(a, b):\n    return a - b\n")            # planted bug
(ROOT / "test_calc.py").write_text("from calc import add\nassert add(2, 3) == 5, add(2, 3)\n")
def safe(path):                      # `path` is untrusted model output: confine it to ROOT
    p = (ROOT / path).resolve()
    if not p.is_relative_to(ROOT): raise PermissionError(f"{path} is outside the repo")
    return p
def read_file(path):                 # numbered lines let the model point at locations
    return "\n".join(f"{i}\t{s}" for i, s in enumerate(safe(path).read_text().splitlines(), 1))
def str_replace(path, old_str, new_str):
    p = safe(path); text = p.read_text(); n = text.count(old_str)
    if n != 1:                       # exact and unique, or refuse: never guess which one
        raise ValueError(f"old_str matched {n} times; quote more surrounding lines")
    p.write_text(text.replace(old_str, new_str)); return f"Edited {path}"
def run_tests():                     # the computational verifier (P8); -B: no stale .pyc
    r = subprocess.run([sys.executable, "-B", "test_calc.py"], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    return f"exit code {r.returncode}\n" + (r.stdout + r.stderr)[-1500:]   # tail only (P3)
TOOLS = {"read_file": read_file, "str_replace": str_replace, "run_tests": run_tests}
PLAN = [("run_tests", {}), ("read_file", {"path": "calc.py"}),   # stub model: see red,
        ("str_replace", {"path": "calc.py", "old_str": "a - b", "new_str": "a + b"}),
        ("run_tests", {})]                                       # fix, then see green
def call_model(messages):  # live: client.messages.create(model="claude-sonnet-5-5", ...)
    turn = sum(m["role"] == "assistant" for m in messages)
    if turn == len(PLAN):
        return {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Fixed."}]}
    return {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": f"t{turn}",
            "name": PLAN[turn][0], "input": PLAN[turn][1]}]}

messages = [{"role": "user", "content": "test_calc.py fails. Find and fix the bug."}]
while (resp := call_model(messages))["stop_reason"] == "tool_use":   # the §11 loop
    messages.append({"role": "assistant", "content": resp["content"]})
    results = []
    for c in resp["content"]:
        try: out, err = TOOLS[c["name"]](**c["input"]), False
        except Exception as e: out, err = f"{type(e).__name__}: {e}", True  # errors are data
        results.append({"type": "tool_result", "tool_use_id": c["id"], "content": out, "is_error": err})
        print(f'{c["name"]:12} -> {out.splitlines()[0]}')
    messages.append({"role": "user", "content": results})
```

It prints `exit code 1`, the numbered file, `Edited calc.py`, then `exit code 0`. To go live, pass JSON schemas for the tools ([§10](10-tool-use.md)). Note the order: the stub runs the tests *before* editing, which confirms the test actually catches the bug. Willison condenses this into two four-word prompts, "First run the tests" and "Use red/green TDD." Claude Code's best-practices page states the general rule: "Without a check it can run, 'looks done' is the only signal available, and you become the verification loop."

### Git as checkpoint and undo

Git gives a coding agent four things:

- **Checkpoint.** A commit is a state a fresh session can resume from ([§21](21-loop-engineering.md)).
- **Review surface.** `git diff` is what the human reads.
- **Undo.** `reset` or `revert` discards bad work.
- **Memory.** `git log` reloads recent work into context (P2), which is why Willison opens sessions with "Review changes made today."

Product undo is narrower than it looks. Claude Code's `/rewind` restores edits made through its file tools, but "Checkpointing does not track files modified by Bash commands," and for most subagent edits the docs say "Use git to revert them."

### AGENTS.md and CLAUDE.md

The model is stateless (P2), so whatever a new teammate would need must arrive in the context. An **instruction file** is plain Markdown that the harness loads at the start of every session: commands, conventions, boundaries. Codex read `AGENTS.md` from its launch in May 2025, and in Aug 2025 the name became a shared convention at agents.md, built with Amp, Google's Jules, Cursor and Factory **(⚠ verify: exact launch date)**. The site lists 60k+ repositories and says the format "is now stewarded by the Agentic AI Foundation." This is P11: one file every agent reads, instead of one rules file per agent per repository.

There are no required fields. In a monorepo, nested files apply and "the closest AGENTS.md to the edited file wins." Claude Code uses `CLAUDE.md`. Since v2.1.277 it reads `AGENTS.md` when no `CLAUDE.md` exists, and a `CLAUDE.md` can also import it with `@AGENTS.md`. The docs suggest keeping each file under 200 lines because longer ones "reduce adherence" (P3). [§19](19-harness-engineering.md) explains why the file should be a map rather than a manual, with each line traceable to a real mistake. Here is a sample for a data-pipeline repository:

```markdown
Python 3.12 + dbt project that builds the `orders` marts. Map: docs/architecture.md

### Commands (run these; don't guess)
- Setup: `uv sync`
- After every change: `uv run ruff check . && uv run pyright && uv run pytest -q -m "not slow"`
- Before you finish: `uv run pytest -q` (full suite, ~4 min)
- dbt: `uv run dbt build --select state:modified+ --target dev`. Never `--target prod`.

### Conventions
- One module per source system under `pipelines/<domain>/`; read data only via `lib/io.py`.
- Public functions are typed; pyright strict must stay clean.

### Boundaries
- Never edit `tests/golden/` or weaken an assertion. If a test looks wrong, stop and explain.
- No new dependencies without asking. If you propose one, confirm it exists on PyPI first.
- Never read or print `.env` or anything under `secrets/`.
- Keep a change under ~400 lines; split larger work into stacked PRs.

### When done
Report what changed, the commands you ran, and their results.
```

### Subagents for exploration

Exploring a repository means reading many files, and every read stays in context (P3). A **subagent** is a fresh copy of the agent with its own context window that returns only a summary ([§13](13-multi-agent.md)). Claude Code's built-in **Explore** subagent searches a codebase "without making changes" at a requested thoroughness. To keep exploration cheap, it starts without the CLAUDE.md files. Willison: the main value of subagents is "preserving that valuable root context and managing token-heavy operations." A test-runner subagent works the same way: it reads a verbose suite and reports only the failures. Run read-only subagents in parallel, but keep writes single-threaded ([§13](13-multi-agent.md)).

### Worktrees for parallel work

A **git worktree** is a second working directory, on its own branch, that shares the same repository history. Two agents in one checkout overwrite each other's files; in separate worktrees they can't. `claude --worktree feature-auth` creates `.claude/worktrees/feature-auth/` on a new branch. A subagent with `isolation: worktree` always gets its own, and `/batch` spreads a migration across 5–30 subagents, each in its own worktree. Two limits apply. A worktree is a fresh checkout, so dependencies and gitignored files like `.env` must be set up again. And worktrees prevent file collisions, not semantic ones ([§21](21-loop-engineering.md)).

### Permissions and sandboxing

A coding agent runs shell commands chosen by a model that reads untrusted text, such as issues, READMEs and dependency source code (P9). Assume it can be talked into anything it is allowed to run. Permission modes and sandboxes are covered in [§20](20-agent-runtime.md) and [§32](32-security-guardrails.md). For coding, the defaults are: explore in plan (read-only) mode, allow-list the test and build commands, confine writes to the repository, and keep credentials and open network access outside the sandbox.

### The practice spectrum: vibe coding to agentic engineering

On Feb 2, 2025, Andrej Karpathy coined **vibe coding**: "you fully give in to the vibes, embrace exponentials, and forget that the code even exists... I 'Accept All' always, I don't read the diffs anymore." He scoped it to "throwaway weekend projects." On Feb 4, 2026 he named the professional end, **agentic engineering**: "'agentic' because the new default is that you are not writing the code directly 99% of the time, you are orchestrating agents who do and acting as oversight. 'engineering' to emphasize that there is an art & science and expertise to it."

Willison began his *Agentic Engineering Patterns* guide on Feb 23, 2026. He keeps vibe coding to its original meaning, "unreviewed, prototype-quality LLM-generated code." The difference isn't the tool but who owns the result. His central anti-pattern: "Don't file pull requests with code you haven't reviewed yourself." He also warns that "Agents write convincing looking pull request descriptions. You need to review these too!" Hype check: the label is new, but the practice is ordinary engineering discipline aimed at a new collaborator ([§38](38-disciplines-map.md)).

### Spec-driven development

**Spec-driven development (SDD)** means writing a structured specification before the agent codes and treating it as the source of truth. Birgitta Böckeler's analysis (Oct 15, 2025) found three levels under one buzzword:

- **Spec-first:** a careful spec for this task, discarded afterward.
- **Spec-anchored:** the spec is kept and maintained as the feature evolves.
- **Spec-as-source:** humans edit only the spec, and the code is generated from it.

The tools she tested:

- **Kiro** (Jul 14, 2025) runs Requirements → Design → Tasks, with acceptance criteria written in EARS notation (Easy Approach to Requirements Syntax).
- **GitHub's Spec Kit** (Sep 2, 2025) runs Constitution → Specify → Plan → Tasks. The **constitution** is a rules file of "immutable" principles.
- **Tessl** explores spec-as-source, stamping generated files `// GENERATED FROM SPEC - DO NOT EDIT`.

The mechanism is sound: a spec front-loads intent and gives reviewers something to check against. Her tests exposed the costs, though. Kiro turned a small bug into "4 'user stories' with a total of 16 acceptance criteria." Spec Kit's markdown was "very verbose and tedious to review." Agents still skipped instructions, a "false sense of control." She likens spec-as-source to model-driven development, which "never took off for business applications" and now has non-determinism added. Use specs for medium-sized, well-understood features, and skip them for small fixes.

### Compound engineering

Kieran Klaassen of Every described "compounding engineering" in Aug 2025 and wrote up **compound engineering** in Dec 2025: "each unit of engineering work should make subsequent units easier—not harder." The loop is Plan → Work → Review → Compound, with "plan and review steps... 80 percent of an engineer's time." The compound step writes each lesson into `CLAUDE.md` or a new reviewer agent, then asks: "Would the system catch this automatically next time?" It is the [§19](19-harness-engineering.md) ratchet with a name and a plugin. The idea is sound, but its parallel reviewer agents cost tokens.

### Harnessable codebases

Agents do best where mistakes are cheap to detect, which Böckeler calls **harnessability** ([§19](19-harness-engineering.md)). That means:

- typed languages, where the type checker is a free sensor
- fast tests, so the loop turns often
- clear module boundaries, which structural tests can enforce
- error messages that say how to fix the problem
- "boring" technology, which OpenAI finds "easier for agents to model due to composability, api stability, and representation in the training set"
- agent legibility: logs, metrics and UI the agent can query, because "anything it can't access in-context while running effectively doesn't exist"

### Benchmarks: SWE-bench and Terminal-Bench

**SWE-bench** (Oct 2023) has 2,294 tasks from real GitHub issues in 12 Python repositories. The agent gets the repository and the issue text and must produce a patch. Hidden tests grade the patch: some must flip from fail to pass, and regression tests must keep passing. **SWE-bench Verified** (OpenAI, Aug 2024) is a 500-task subset that engineers screened for fair tests and clear issues. Devin's 13.86% on the original SWE-bench in Mar 2024 shows the starting point.

On Feb 23, 2026, OpenAI stopped reporting Verified, for three reasons:

- **Saturation.** Top scores had moved only "from 74.9% to 80.9%" in six months.
- **Flawed tests.** An audit of 138 often-failed tasks found 59.4% had material problems: tests that "reject functionally correct submissions," or underspecified descriptions.
- **Contamination.** Frontier models could reproduce gold patches from memory, because the test answers were in their training data.

OpenAI now recommends Scale's SWE-bench Pro, though later audits reportedly questioned its grading too **(⚠ verify)**. **Terminal-Bench** (May 2025) tests broader terminal work in Docker environments with human-written solutions and tests. Version 2.0 (Nov 2025) has 89 tasks. By 4.0 (Aug 2026) it had become a continuously maintained benchmark that drops tasks every frontier model solves. Its integrity notes catalogue reward hacking, including an agent that "curls the solution from the internet and includes it in its AGENTS.md."

The lessons:

- A score measures a model-plus-harness pair ([§19](19-harness-engineering.md)).
- Public tasks leak into training data.
- Tests can be wrong in both directions.
- No benchmark measures maintainability or review cost.

Shortlist with benchmarks, then decide with your own tasks ([§26](26-evals.md)).

### The human bottleneck

When agents write most of the code, the scarce resource becomes human attention. OpenAI's harness team: "As code throughput increased, our bottleneck became human QA capacity." Two forces drive it:

- **Review bandwidth.** You can start ten agents but can't review ten agents' diffs at the old depth, and merging unread code builds **comprehension debt** ([§21](21-loop-engineering.md)).
- **The orchestration tax.** Briefing agents, switching between their threads, answering their questions and merging their branches is real work that doesn't look like typing.

Self-assessment is unreliable too. METR's 2025 randomized trial found that experienced developers took 19% *longer* with early-2025 tools while believing they were 20% faster. Its Feb 2026 follow-up estimated tasks took about 18% less time for returning participants (confidence interval −38% to +9%). METR called that "only very weak evidence," because many developers now refused to work without AI, and time was hard to measure for those running "multiple AI agents concurrently." Spend human judgment where it buys the most:

- defining what "done" means
- checking that the tests prove it
- deciding architecture and boundaries
- reading the diff, especially changes to tests
- turning repeated mistakes into rules

### Failure modes

- **Plausible-but-wrong code.** Sampled output looks likely (P1, P4), so it reads well and compiles while handling the wrong case. Defend with red/green tests written from the spec and evidence attached to each PR.
- **Tests weakened to pass.** An agent rewarded for green may edit tests, special-case inputs or exit early ([§21](21-loop-engineering.md)). Defend by denying writes to protected test paths, flagging every test change in review, and keeping held-out tests outside the sandbox.
- **Dependency hallucination ("slopsquatting").** Across 576,000 generated samples from 16 models, at least 5.2% of packages suggested by commercial models and 21.7% from open-source models did not exist, 205,474 unique fake names (Spracklen et al., 2024). An attacker who registers one gets their code installed by anyone who trusts the suggestion. Defend with lockfiles, a vetted package proxy, a check that each new dependency exists and is established, and sandbox egress limits.
- **Large unreviewable diffs.** A 3,000-line PR gets skimmed, not reviewed. Defend with size caps in `AGENTS.md` and stacked PRs.
- **Secrets exposure.** Once the agent reads `.env`, the secret is in the transcript sent to the provider and in logs, and an injected instruction can send it elsewhere: the lethal trifecta of [§32](32-security-guardrails.md). Defend with deny rules such as `Read(./.env)`, credentials held outside the sandbox ([§20](20-agent-runtime.md)), an egress allow-list and pre-commit secret scanning.

## Comparison

**Ways of working with coding agents**

| Practice | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Vibe coding | Prompt, accept all, don't read the code | Fastest path to a demo | Nobody understands or owns the code | Throwaway prototypes |
| Agentic engineering | Agent writes and runs code; you specify, verify and review | Real speedup at production quality | Review becomes the bottleneck | Default for professional work |
| Spec-driven | Requirements → design → tasks, then implement | Explicit, reviewable intent | Verbose; heavy for small changes | Medium, well-understood features |
| Compound engineering | Plan → work → review → write lessons back | Improves with each task | Token and process overhead | Long-lived codebases |
| Loop-driven ([§21](21-loop-engineering.md)) | Code prompts the agent, with stop conditions | Throughput without a human per run | Reward hacking, runaway cost | Well-tested backlogs |

**Finding relevant code**

| Approach | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Agentic search | grep, glob, read, follow imports | Exact, always fresh, nothing to maintain | More calls and tokens; weak on concepts | Default |
| Semantic index | Embed chunks; nearest-neighbor search | Finds concepts in huge repos | Stale after edits; splits logic; a second copy to secure | Very large repos, alongside grep |
| Code intelligence (LSP) | Language server gives definitions, references, type errors | Precise structure; a free sensor | Per-language setup | Typed languages |

## What it didn't solve

Coding agents work because software ships with its own verifiers: tests, compilers and linters turn "is this right?" into an exit code. Most of the world has no such oracle. No test suite tells a research agent whether its synthesis of forty web pages is true, and no compiler confirms that a computer-use agent clicked the right button in an unfamiliar GUI. Agents on the open web and on screens must check their work with weaker, inferential signals, while reading untrusted content at every step.

→ Next: [§24 Computer Use and Research Agents](24-computer-use-and-research-agents.md)

## Check your understanding

**Q: Why did coding become the first domain where agents worked reliably?**

Every step can be checked cheaply and deterministically by compiling, type-checking and running tests. That turns P8's pⁿ compounding into a chain of caught-and-retried steps. Code is text in files (P1), and git makes every state reversible. RL with verifiable rewards also trained models on exactly this edit-run-fix loop, while domains without such verifiers lag.

**Q: Why does Claude Code lean on grep and glob instead of a vector index, and when would you add one?**

Code is searched by exact identifiers, which grep matches perfectly. An index goes stale with every edit, including the agent's own, and chunking separates functions from their callers. The cost is more tool calls and tokens per question. Add semantic search alongside grep, not instead of it, when the repository is too large to explore and questions are conceptual.

**Q: What would happen if a str_replace tool silently edited the first match when old_str appears twice?**

Sometimes it would change the wrong function, and the model would believe the edit succeeded. The error would surface turns later, far from its cause, and compound (P8). The uniqueness rule turns ambiguity into an immediate `is_error` the model fixes by quoting more context. The exact-match rule does the same for stale context.

**Q: Vibe coding vs agentic engineering: if both use the same tool, what is actually different?**

Ownership and verification. Vibe coding means accepting every diff and forgetting "the code even exists," which is fine for throwaway projects. Agentic engineering means you still specify the goal, give the agent checks, review the diff and answer for the result. Willison's line makes it concrete: don't file a PR you haven't reviewed yourself.

**Q: Why did OpenAI stop reporting SWE-bench Verified, and what does that teach you about coding benchmarks?**

Most of the hard tasks models kept failing had tests that rejected correct fixes or underspecified issues, and frontier models could recite gold patches from training data. Near the top, gains reflected exposure more than skill. Treat any public score as one model-plus-harness measurement on possibly contaminated tasks, and confirm on private tasks from your own codebase.

**Q: What would happen if you ran five agents in parallel worktrees but kept your old review process?**

Worktrees prevent file collisions, so you'd get five branches of plausible diffs, but your review capacity wouldn't grow. You'd either rubber-stamp them and build comprehension debt, or queue them and lose the speedup. Branches can also conflict semantically even when they merge cleanly. Parallelism pays only with small PRs, strong automated checks and partitioned work.

## Takeaways

- A coding agent is the agent loop plus search, read, exact-match edit and run tools, with git as checkpoint, review surface and undo.
- Code led agent adoption because tests and compilers are cheap computational verifiers (P8), and models were RL-trained on that loop.
- Agentic search is the default for code because identifiers are exact and indexes go stale; semantic search complements it in very large repositories.
- Exact-match edits fail loudly on stale or ambiguous context, which is why they beat whole-file rewrites.
- AGENTS.md is the cross-vendor instruction file (P11): short, command-focused, grown from real mistakes.
- Vibe coding means not reading the code, and agentic engineering means owning it. The tools are the same; the accountability differs.
- Spec-driven and compound engineering are useful named habits, but weigh their overhead against the size of the change.
- Public benchmarks saturate and leak into training data, and review bandwidth, not code generation, now caps throughput.

## Sources

- Anthropic, "Claude 3.7 Sonnet and Claude Code" (Feb 24, 2025): https://www.anthropic.com/news/claude-3-7-sonnet
- Anthropic, "Introducing Claude 4" (Claude Code GA, May 22, 2025): https://www.anthropic.com/news/claude-4
- Anthropic, "Claude Code on the web" (Oct 20, 2025; GA update Sep 23, 2026): https://www.anthropic.com/news/claude-code-on-the-web
- Anthropic, "Effective context engineering for AI agents" (Sep 29, 2025): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Claude Code docs, Best practices: https://code.claude.com/docs/en/best-practices
- Claude Code docs, Tools reference: https://code.claude.com/docs/en/tools-reference
- Claude Code docs, Memory (CLAUDE.md, AGENTS.md): https://code.claude.com/docs/en/memory
- Claude Code docs, Subagents: https://code.claude.com/docs/en/sub-agents
- Claude Code docs, Worktrees: https://code.claude.com/docs/en/worktrees
- Claude Code docs, Checkpointing: https://code.claude.com/docs/en/checkpointing
- Claude API docs, Text editor tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool
- OpenAI docs, Apply patch tool: https://developers.openai.com/api/docs/guides/tools-apply-patch
- OpenAI, "Introducing Codex" (May 2025): https://openai.com/index/introducing-codex/
- OpenAI, "Introducing o3 and o4-mini" (Codex CLI, Apr 16, 2025): https://openai.com/index/introducing-o3-and-o4-mini/
- OpenAI, "Harness engineering: leveraging Codex in an agent-first world" (Feb 2026): https://openai.com/index/harness-engineering/
- GitHub, "Introducing GitHub Copilot" (Jun 29, 2021): https://github.blog/news-insights/product-news/introducing-github-copilot-ai-pair-programmer/
- GitHub, "GitHub Copilot: The agent awakens" (Feb 6, 2025): https://github.blog/news-insights/product-news/github-copilot-the-agent-awakens/
- GitHub, "GitHub Copilot: Meet the new coding agent" (May 19, 2025): https://github.blog/news-insights/product-news/github-copilot-meet-the-new-coding-agent/
- Google, "Gemini CLI: your open-source AI agent" (Jun 25, 2025): https://blog.google/technology/developers/introducing-gemini-cli-open-source-ai-agent/
- Cognition, "Introducing Devin" (Mar 2024): https://cognition.ai/blog/introducing-devin
- AGENTS.md: https://agents.md
- Yang et al., "SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering" (May 2024): https://arxiv.org/abs/2405.15793
- Aider docs, Edit formats: https://aider.chat/docs/more/edit-formats.html
- Cline, "Why Cline Doesn't Index Your Codebase" (May 27, 2025): https://cline.bot/blog/why-cline-doesnt-index-your-codebase-and-why-thats-a-good-thing
- Cursor, "Improving agent with semantic search" (Nov 6, 2025): https://cursor.com/blog/semsearch
- Andrej Karpathy, "vibe coding" (Feb 2, 2025): https://x.com/karpathy/status/1886192184808149383
- Andrej Karpathy, "agentic engineering" (Feb 4, 2026): https://x.com/karpathy/status/2019137879310836075
- Simon Willison, "Writing about Agentic Engineering Patterns" (Feb 23, 2026): https://simonwillison.net/2026/Feb/23/agentic-engineering-patterns/
- Simon Willison, *Agentic Engineering Patterns* (guide): https://simonwillison.net/guides/agentic-engineering-patterns/
- Birgitta Böckeler, "Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl" (Oct 15, 2025): https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- Kiro, "Introducing Kiro" (Jul 14, 2025): https://kiro.dev/blog/introducing-kiro/
- GitHub, "Spec-driven development with AI" (Spec Kit, Sep 2, 2025): https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/
- Kieran Klaassen, "My AI Had Already Fixed the Code Before I Saw It," Every (Aug 18, 2025): https://every.to/source-code/my-ai-had-already-fixed-the-code-before-i-saw-it
- Kieran Klaassen, "Compound Engineering: How Every Codes With Agents," Every (Dec 11, 2025): https://every.to/chain-of-thought/compound-engineering-how-every-codes-with-agents
- Jimenez et al., "SWE-bench" (Oct 2023): https://arxiv.org/abs/2310.06770
- OpenAI, "Introducing SWE-bench Verified" (Aug 2024): https://openai.com/index/introducing-swe-bench-verified/
- OpenAI, "Why we no longer evaluate SWE-bench Verified" (Feb 23, 2026): https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- Merrill et al., "Terminal-Bench" (Jan 2026): https://arxiv.org/abs/2601.11868
- Terminal-Bench news (2.0, 4.0, leaderboard integrity): https://www.tbench.ai/news
- METR, early-2025 developer productivity RCT (Jul 10, 2025): https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/
- METR, "We are Changing our Developer Productivity Experiment Design" (Feb 24, 2026): https://metr.org/blog/2026-02-24-uplift-update/
- Spracklen et al., "We Have a Package for You!" (package hallucinations, Jun 2024): https://arxiv.org/abs/2406.10279
