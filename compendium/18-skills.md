# 18. Agent Skills

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This is the context-and-harness era of late 2025 and 2026. Anthropic launched Agent Skills on **Oct 16, 2025** for the Claude apps, Claude Code and the API, and on **Dec 18, 2025** published the format as an open standard at agentskills.io. [§17](17-memory.md) gave agents memory for facts and past experiences, but *procedural* know-how ("how our team reviews a dbt model") still had to live in the system prompt or be pasted in again each session, which bloats every call (P3). A skill packages a procedure as a folder the agent loads only when the task needs it. As of October 2026 the agentskills.io showcase lists 46 products that read the format, among them Claude Code, OpenAI's ChatGPT and Codex, Cursor, GitHub Copilot, VS Code, Gemini CLI, Databricks Genie Code and Snowflake Cortex Code.

## Why this exists

Start from P2: the model is stateless, and the context window is its only working memory. Anything it doesn't know (your naming conventions, the steps of your release process, which script validates a form) has to arrive as tokens. Before skills you had four places to put that know-how, and each fails differently:

1. **The system prompt** (or an always-loaded `CLAUDE.md` / `AGENTS.md`). Every call pays for every procedure, relevant or not (P10), and the irrelevant ones dilute attention for the relevant one (P3). Ten 3,000-token procedures put 30,000 tokens on every turn, and you use one of them.
2. **Fine-tuning** (P5, [§29](29-adapting-models.md)). It puts behavior into the weights, but it's slow, expensive and frozen. You can't retrain every time a team convention changes.
3. **RAG** ([§9](09-rag.md)). Retrieval returns similar chunks, chosen by the harness. A procedure is sequential (step 4 depends on step 2), so chunking breaks it.
4. **Tools and MCP servers** ([§10](10-tool-use.md), [§15](15-protocols-mcp-a2a.md)). These give *actions*, not *know-how*, and their schemas usually load up front. Simon Willison observed that GitHub's official MCP server alone "famously consumes tens of thousands of tokens of context."

What made skills possible is the agent itself ([§11](11-agents.md)). An agent with a filesystem and a shell can read files on its own. So the context doesn't need the procedure, only a line saying the procedure *exists* and *when it applies*; the agent fetches the rest. Anthropic compares this to "a well-organized manual that starts with a table of contents, then specific chapters, and finally a detailed appendix." In the CoALA memory taxonomy from [§17](17-memory.md), skills are **procedural memory** stored as plain files.

A data-platform analogy: a query planner reads table names and comments from the metastore, not the data, and scans partitions only when the query needs them. Skills apply the same pruning to instructions.

## How it works (under the hood)

### The anatomy of a skill

A skill is a directory with one required file, `SKILL.md`. It starts with **YAML frontmatter** (a small metadata block between two `---` lines), followed by free-form markdown instructions. Optional subfolders hold scripts, reference documents and assets:

```text
reviewing-dbt-models/
├── SKILL.md              # required: frontmatter + instructions
├── scripts/
│   └── lint_models.py    # executable: run, not read
├── references/
│   ├── incremental.md    # loaded only for incremental models
│   └── pii-policy.md     # loaded only when PII columns are touched
└── assets/
    └── model_template.sql
```

The open specification requires two frontmatter fields:

- **`name`**: up to 64 characters of lowercase letters, digits and hyphens, matching the folder name.
- **`description`**: up to 1,024 characters, saying what the skill does *and* when to use it.

Optional fields are `license`, `compatibility` (environment needs, such as network access), `metadata` (free key-value pairs) and `allowed-tools` (experimental). Anthropic's API also bans XML tags and the reserved words "anthropic" and "claude" in names. An example:

```markdown
---
name: reviewing-dbt-models
description: Reviews dbt model changes against the data-platform team's conventions
  (naming, grain tests, incremental strategy, PII handling). Use when the user asks to
  write, review or refactor a dbt model, or when a diff touches models/ or schema.yml.
license: Apache-2.0
metadata:
  owner: data-platform
  version: "1.3"
---

**Workflow**
1. Run `python scripts/lint_models.py <changed .sql files>`. Fix every error it prints,
   then run it again until it exits cleanly.
2. Check the grain: every model needs `unique` + `not_null` tests on its key in schema.yml.
3. If the model is incremental, read [references/incremental.md](references/incremental.md).
4. If any column is tagged `pii`, read [references/pii-policy.md](references/pii-policy.md).

**Conventions**
- Staging: `stg_<source>__<entity>`. Marts: `fct_<event>` or `dim_<entity>`.
- No `SELECT *` outside staging models.
- New models start from `assets/model_template.sql`.

**Output**: a checklist, blocking issues first, then suggestions, each with file and line.
```

### Progressive disclosure in three levels

**Progressive disclosure** means loading information in stages, only as the task calls for it. Anthropic's docs and the open spec describe the same three levels:

| Level | What loads | When | Typical token cost |
|---|---|---|---|
| 1. Metadata | `name` + `description` of every installed skill | At startup, into the system prompt | About 100 tokens per skill |
| 2. Instructions | The `SKILL.md` body | When the task matches the description | Under 5,000 tokens recommended (spec: under 500 lines) |
| 3. Resources | Files in `references/`, `scripts/`, `assets/` | Only when the body points to them and the task needs them | Zero until accessed; for scripts, only their output |

What the context window holds at each stage:

```text
 startup                     task matches skill           task needs a detail
+------------------------+  +-------------------------+  +-------------------------+
| system prompt          |  | system prompt           |  | system prompt           |
| skill index:           |  | skill index             |  | skill index             |
|  - reviewing-dbt-...   |  | user message            |  | user message            |
|  - filling-pdf-forms   |  | > cat .../SKILL.md      |  | SKILL.md body           |
|  - ... (~100 tok each) |  | SKILL.md body (~2k tok) |  | > cat references/       |
| user message           |  |                         |  |     incremental.md      |
|                        |  |                         |  | > python scripts/lint.. |
|                        |  |                         |  | lint OUTPUT only        |
+------------------------+  +-------------------------+  +-------------------------+
```

Compare the arithmetic with the system-prompt approach. Fifty skills cost about 5,000 tokens while idle. Fifty 5,000-token procedures in the system prompt would cost 250,000 tokens on *every call*. Prompt caching ([§5](05-api-and-prompting.md)) would lower the dollar cost of that prefix, but not the attention cost: the model still attends across all of it, and irrelevant instructions compete with the relevant one (P3). The fixed context stays small however many skills you install, and that is why the design works.

### Who does the matching: the model

Claude's implementation has no separate retriever or keyword matcher. The descriptions sit in the system prompt, the **model decides** whether a skill applies, and then it loads the body with an ordinary tool call (Anthropic's docs show `bash: cat pdf-processing/SKILL.md`). Triggering is therefore an inference step, which makes it probabilistic (P1, P4): a skill can fail to fire, or fire on the wrong task. Claude Code adds explicit invocation as an escape hatch. You can type `/skill-name`, and `disable-model-invocation: true` stops the model from triggering a skill on its own, which is useful for a deploy procedure.

This snippet builds the mechanism by hand with the Messages API. It scans only the frontmatter, puts the index in the system prompt, lets the model choose, and loads the body only after the model asks for it:

```python
import os, pathlib
import anthropic, yaml  # pip install anthropic pyyaml

SKILLS = pathlib.Path("skills")  # one sub-folder per skill

def frontmatter(path):
    """Level 1: read only the YAML block between the two '---' lines."""
    lines = []
    with path.open() as f:
        f.readline()                      # opening '---'
        for line in f:
            if line.strip() == "---":     # closing '---': stop, body is never read
                break
            lines.append(line)
    return yaml.safe_load("".join(lines))

def body(name):
    """Level 2: full instructions, loaded only after the model picks the skill."""
    text = (SKILLS / name / "SKILL.md").read_text()
    return text.split("---", 2)[2]        # drop the frontmatter, keep the markdown

index = {m["name"]: m["description"]
         for m in (frontmatter(p) for p in SKILLS.glob("*/SKILL.md"))}
system = "Skills you can use. Call load_skill before following one:\n" + \
         "\n".join(f"- {n}: {d}" for n, d in index.items())  # ~100 tokens each
load_skill = {"name": "load_skill", "description": "Load a skill's full instructions.",
              "input_schema": {"type": "object", "required": ["name"],
                               "properties": {"name": {"type": "string", "enum": list(index)}}}}

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
messages = [{"role": "user", "content": "Review my change to models/fct_orders.sql"}]
resp = client.messages.create(model="claude-sonnet-5-5", max_tokens=4096,
                              system=system, tools=[load_skill], messages=messages)
messages.append({"role": "assistant", "content": resp.content})
results = [{"type": "tool_result", "tool_use_id": b.id, "content": body(b.input["name"])}
           for b in resp.content if b.type == "tool_use"]  # the MODEL did the matching
if results:
    messages.append({"role": "user", "content": results})  # body enters context now
# Level 3: the body names references/*.md and scripts/*.py; a read_file or bash tool
# loads or runs them in later turns of the loop, and only if the model asks.
```

Production harnesses usually skip the dedicated `load_skill` tool. They give the model a general file-read or bash tool and list each skill's path in the index, and the mechanism is otherwise the same. With OpenAI's Responses API you would declare the tool as `{"type": "function", "name": ..., "parameters": ...}` and return the body as a `function_call_output` item. Codex reads the same `SKILL.md` format, so the folder itself is portable.

### Scripts run; their source stays out of context

Level 3 holds two kinds of file. Reference documents are *read*, so they enter context. Scripts are *run* through the agent's shell or code-execution tool, and only their output comes back. In Anthropic's words, when Claude runs `validate_form.py`, "the script's code never loads into the context window. Only its output (such as 'Validation passed' or a specific error message) consumes tokens." Two benefits follow:

- **Determinism.** Sorting, parsing or validating is cheaper and more reliable as code than as token generation. A bundled script gives the same answer every run (P4).
- **Token efficiency.** A 400-line validator costs nothing in context; its three-line verdict costs a few tokens (P10).

One caveat: "never enters context" holds only if the agent *runs* the script rather than *reads* it. Nothing stops a model from running `cat scripts/lint_models.py`, so Anthropic advises saying explicitly in `SKILL.md` whether a script is to be executed or read as reference.

Skills therefore need an execution environment. On the Claude API **(GA)** you attach up to 20 skills per request through the `container` parameter, along with the code-execution tool. That container has no network access and can't install packages at runtime:

```json
{
  "model": "claude-sonnet-5-5",
  "max_tokens": 4096,
  "container": {"skills": [
    {"type": "anthropic", "skill_id": "xlsx", "version": "latest"},
    {"type": "custom", "skill_id": "skill_01AbCdEfGhIjKlMnOpQrStUv", "version": "latest"}
  ]},
  "tools": [{"type": "code_execution_20250825", "name": "code_execution"}],
  "messages": [{"role": "user", "content": "Build a budget workbook from this CSV"}]
}
```

The tool version string is the one Anthropic's Skills guide shows as of October 2026; newer code-execution versions exist, so check which one your model supports. Claude Code runs skills on your own machine, with the same network access as any other program you run.

### The description is the trigger

The model chooses skills from their descriptions alone, so the description works as a routing rule, and it's the part most worth writing carefully:

- **Say what and when.** "Extracts text and tables from PDF files, fills forms, merges documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction" works. "Helps with PDFs" doesn't.
- **Use the words users type**: file extensions, tool names, paths (`schema.yml`, `models/`).
- **Write in the third person.** The description is injected into the system prompt, and Anthropic notes that an inconsistent point of view "can cause discovery problems."
- **Put the key use case first.** Claude Code truncates description plus `when_to_use` at 1,536 characters in its skill listing.
- **Test triggering like a classifier** (P4, [§26](26-evals.md)). Run prompts that *should* trigger the skill and near-misses that *shouldn't*, several times each, and count.

### Where skills live in Claude Code

| Location | Path | Scope |
|---|---|---|
| Enterprise | `.claude/skills/<name>/SKILL.md` in the managed-settings directory | Every user on machines where the organization deploys it |
| Personal | `~/.claude/skills/<name>/SKILL.md` | All your projects on this machine |
| Project | `.claude/skills/<name>/SKILL.md` in the repo | Everyone who clones it (commit it) |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | Wherever the plugin is enabled, namespaced `/plugin:skill` |

On a name clash, enterprise beats personal and personal beats project. Claude Code merged its older custom slash commands into skills, and it accepts extra frontmatter beyond the spec (`disable-model-invocation`, `context: fork` to run the skill in a subagent, `hooks`, `model`). Those extras don't travel: claude.ai uploads and the Skills API accept only the spec's fields and reject the rest with a hard error. Skills also don't sync automatically between claude.ai, the API and Claude Code.

### Authoring guidance

- **Start from observed failures.** Anthropic's advice is to run the agent on representative tasks, see where it struggles, and write skills for those gaps rather than imagined ones.
- **Assume the model is smart.** Add only what it doesn't know (your conventions, scripts and edge cases). Once loaded, every token of the body competes with the task.
- **Split by exclusivity.** Rarely used or mutually exclusive material goes in separate reference files, linked one level deep from `SKILL.md`.
- **Match freedom to fragility.** Fragile, exact operations get a script and "run exactly this"; judgment calls get heuristics.
- **Build in a feedback loop.** "Run the validator, fix, repeat until it passes" is P8 at the scale of one skill.
- **Harvest from success.** After a good session, ask the agent to write what worked into the skill.

### Security: skills are a supply chain

A skill is instructions *and* code. The instructions enter context looking like trusted guidance, and under P9 any text in context can act as an instruction. The scripts run with whatever permissions the agent has. Installing a third-party skill is closer to `pip install` from an unknown author than to reading a blog post.

Snyk's **ToxicSkills** audit (Feb 5, 2026) scanned 3,984 skills from the public ClawHub and skills.sh registries:

- 534 skills (13.4%) had at least one critical issue (malware, prompt injection or exposed secrets).
- 1,467 (36.82%) had at least one issue of any severity.
- Human review confirmed 76 malicious payloads, and 91% of those combined prompt injection with malicious code.
- 2.9% of ClawHub skills fetched instructions from a remote URL at runtime (`curl ... | source`). A skill like that passes review and changes its behavior later.

Those figures describe open community marketplaces, not curated vendor skills, but the mechanism applies to any skill you don't control. Treat skills like dependencies:

- Read every bundled file before installing.
- Pin versions or vendor the skill into your repo, and review changes like code.
- Avoid skills that fetch remote instructions.
- Scan them (Snyk's `mcp-scan --skills`; Claude Enterprise scans skills uploaded in claude.ai).
- Run them in a sandbox with egress controls.

Read `allowed-tools` with care: in Claude Code it *pre-approves* tools for the skill's turn, so it widens permissions rather than narrowing them. [§32](32-security-guardrails.md) covers the defenses in depth.

### The open standard and cross-vendor adoption

Without a shared format, N agent products and M teams' procedures mean N×M translations: one copy as Cursor rules, another as Copilot instructions, another as a Claude prompt. One folder format makes it N+M (P11). agentskills.io publishes the specification, a reference validator (`skills-ref validate ./my-skill`), a guide for client authors and the adopter showcase. MCP has an official "Skills over MCP" extension (`io.modelcontextprotocol/skills`, SEP-2640, status Final) that lets a server publish skills as resources; MCP's site says host and SDK support is still rolling out **(Preview)**.

Portability has limits. The folder and the spec fields carry over. Vendor frontmatter, execution environments (network, installed packages) and each model's triggering behavior do not, so test a skill on every agent you run it on.

### Failure modes

- **Under-triggering:** a vague description, and the skill never loads.
- **Over-triggering:** a greedy description, and the body loads on unrelated tasks, wasting tokens and pulling in the wrong rules.
- **Sprawl.** Overlapping descriptions confuse selection (Drew Breunig's "context confusion"), and each skill adds about 100 index tokens. At hundreds of skills, the index itself becomes noise.
- **Stickiness.** A loaded body stays in the conversation and keeps costing tokens on later turns, until compaction or a reset ([§16](16-context-engineering.md)).
- **Staleness.** Skills rot like documentation, and under P12 a workaround for a weaker model becomes dead weight once a stronger model handles the task natively.
- **Environment mismatch.** A script that needs the network fails in a sandboxed API container.

## Comparison

**Where know-how and capability can live**

| Mechanism | What it adds | When loaded | Context cost | Who executes | Best for |
|---|---|---|---|---|---|
| System prompt / `CLAUDE.md` / `AGENTS.md` | Standing rules, identity, constraints | Every call | Full size on every call | Nothing runs; the model reads it | Short rules that apply to almost every task |
| Tool (function calling, [§10](10-tool-use.md)) | One typed action the model can request | Schema on every call (unless tool search defers it) | Schema always; results when called | The harness runs your code (P6) | Discrete actions with structured inputs |
| MCP server ([§15](15-protocols-mcp-a2a.md)) | A bundle of tools, resources and prompts over a standard protocol | When the server connects; schemas usually up front | Can reach tens of thousands of tokens | The server process | Access to external systems and data |
| Skill | Procedural know-how plus optional scripts and reference files | Metadata at startup; body on match; files on reference | ~100 tokens per idle skill; body when used; script output only | The model follows it; scripts run in the agent's sandbox | Repeatable workflows, team conventions, document recipes |
| Subagent ([§13](13-multi-agent.md)) | A separate context window with its own prompt and tools | Spawned on demand | Only the returned summary | Another model loop | Isolating noisy exploration; parallel work |
| Memory ([§17](17-memory.md)) | Facts and experiences persisted across sessions | Retrieved, or loaded at session start | Whatever is retrieved | The harness stores; the model reads and writes | Personalization, continuity across sessions |

**Skills vs MCP: complementary, not competing**

| | MCP server | Skill |
|---|---|---|
| Question it answers | "What can I reach and do?" (access) | "How do we do this here?" (know-how) |
| Form | A running process speaking a protocol | A folder of markdown and scripts |
| Typical content | `run_query`, `list_tables`, `get_issue` | "To profile a new source table: row counts by load date, then null rates per column, then..." |
| Context profile | Tool schemas, often up front | Tiny index; body on demand |
| Main risk | Over-broad permissions on the server | Malicious instructions or scripts |

They combine naturally: a Snowflake MCP server provides the query tools, and a `profiling-source-tables` skill says which queries to run, in what order, and how to read the results. Willison's first-day verdict was that skills are "maybe a bigger deal than MCP." Two facts suggest the two are complementary instead. Anthropic's launch post said it would "explore how Skills can complement Model Context Protocol (MCP) servers by teaching agents more complex workflows that involve external tools and software." And MCP itself now has an extension for serving skills.

## What it didn't solve

Skills deliver know-how on demand, but they are one more part to configure. The loop ([§11](11-agents.md)), tools ([§10](10-tool-use.md)), context management ([§16](16-context-engineering.md)), memory ([§17](17-memory.md)) and skills still have to be assembled into one reliable system. Someone has to decide which checks run after each action, what happens when the agent tries to stop early, and how a mistake the agent made today becomes a rule it follows tomorrow. That assembly-and-tuning work became a discipline of its own.

→ Next: [§19 Harness Engineering](19-harness-engineering.md)

## Check your understanding

**Q: Why does a skill's description matter more than its body for whether the skill is useful at all?**

Before activation the description is the only part in context, and the model reads it to decide whether to load the body. It works as a probabilistic routing rule (P4): a strong body behind a vague description never loads, and a greedy description loads it on unrelated tasks. So you write what *and* when, use the user's keywords, and test with should and shouldn't prompts. For a skill you only invoke explicitly (`/name`), the description matters much less.

**Q: What would happen if you moved all 40 of your team's skills into one big system prompt instead?**

Every call would carry all 40 procedures, perhaps 100k+ tokens, adding cost and latency (P10); caching would soften the bill but not the attention cost. Adherence to the one relevant procedure would drop as attention spreads (P3), rules from different procedures would collide, and scripts would no longer stay out of context. A single always-on file only makes sense for a few short rules that apply to nearly every task.

**Q: Skills vs MCP servers: which one should you build for "our team's process for backfilling a partitioned table"?**

The process is know-how (ordered steps, checks, conventions), so it's a skill. An MCP server gives *access*, for example `run_sql` or `trigger_job` tools the skill's steps call. Hard-coding the process as MCP tools would freeze it into code paths and load schemas up front. If the agent can't reach the warehouse yet, you need the MCP server or a CLI as well, because a skill can't create access.

**Q: Why do bundled scripts make a skill more reliable, and when does that benefit disappear?**

A script runs deterministically and only its output enters context, so the agent gets the same validation every time without paying tokens for the code (P4, P10). Regenerating the logic each run would vary and cost more. The benefit disappears if the agent reads the script instead of running it, if the runtime lacks a dependency or network access the script needs, or if the task is a judgment call that code can't capture.

**Q: Why is installing a third-party skill a supply-chain risk even if you never run its scripts?**

The `SKILL.md` body enters context as instructions, and the model can't reliably separate trusted instructions from malicious ones in the same channel (P9). A poisoned body can tell the agent to run commands, exfiltrate files or fetch remote instructions, using the permissions the agent already has. Snyk found critical issues in 13.4% of the 3,984 public skills it scanned. Review, pin and sandbox skills, and rely on least privilege rather than on the skill behaving well.

**Q: How does progressive disclosure change the cost of installing your 100th skill compared with your 10th?**

The idle cost per skill stays roughly constant, about 100 tokens for one name and description, while bodies and files cost nothing until used. The real limit becomes selection quality: with a hundred overlapping descriptions the model chooses less reliably, and the index turns into noise. At that point, prune, merge, or route groups of skills to subagents.

**Q: Why might a skill that helped last year make your agent worse today?**

Many skills encode workarounds for a model's weaknesses, such as step-by-step hand-holding or rigid templates. Under P12, newer models absorb those abilities, and over-prescriptive instructions then constrain a model that would do better on its own. Re-run your evals when you change models, and delete skills that no longer move the results.

## Takeaways

- A skill is a folder: `SKILL.md` (frontmatter `name` and `description`, then markdown instructions) plus optional `scripts/`, `references/` and `assets/`.
- Progressive disclosure keeps the idle cost at about 100 tokens per skill: metadata at startup, body on match, files only when referenced.
- The model matches skills from their descriptions, so the description is a probabilistic trigger. Write it with what and when, and test it.
- Scripts run and only their output enters context, which buys determinism and saves tokens.
- Skills give know-how; MCP and tools give access. Real agents use both.
- Third-party skills are code plus instructions, so review, pin, scan and sandbox them like dependencies (P9).
- The format is an open standard (agentskills.io, Dec 2025) read by dozens of agents, turning N×M instruction formats into N+M (P11).
- Skills rot and can become dead scaffolding as models improve (P12), so prune them against your evals.

## Sources

- Anthropic, "Introducing Agent Skills" (Oct 16, 2025; updated Dec 18, 2025): https://www.anthropic.com/news/skills
- Anthropic Engineering, Barry Zhang, Keith Lazuka, Mahesh Murag, "Equipping agents for the real world with Agent Skills" (Oct 16, 2025): https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Anthropic docs, Agent Skills overview: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Anthropic docs, Skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Anthropic docs, Using Agent Skills with the API: https://platform.claude.com/docs/en/build-with-claude/skills-guide
- Claude Code docs, Skills: https://code.claude.com/docs/en/skills
- Agent Skills open standard, overview: https://agentskills.io
- Agent Skills specification: https://agentskills.io/specification
- Agent Skills client showcase: https://agentskills.io/clients
- Model Context Protocol, Skills extension: https://modelcontextprotocol.io/extensions/skills/overview
- Snyk, "ToxicSkills" study of the agent skills supply chain (Feb 5, 2026): https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/
- Simon Willison, "Claude Skills are awesome, maybe a bigger deal than MCP" (Oct 16, 2025): https://simonwillison.net/2025/Oct/16/claude-skills/
- Sumers et al., "Cognitive Architectures for Language Agents" (CoALA), arXiv 2309.02427: https://arxiv.org/abs/2309.02427
