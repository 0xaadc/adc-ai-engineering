# 17. Agent Memory

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

The vocabulary came from two 2023 papers:

- **CoALA** (Sumers, Yao, Narasimhan & Griffiths, Sep 2023) borrowed memory types from cognitive science.
- **MemGPT** (Packer et al., Oct 2023) treated the context window like RAM in an operating system and let the model page data in and out.

In 2025 these ideas became products: the mem0 paper (Apr 2025), Letta (the company behind MemGPT), LangGraph's long-term stores, and Anthropic's memory tool (beta, Sep 29, 2025). In 2026 vendors started saying "memory engineering". That is a niche label for a subset of context engineering: deciding which tokens from *past* sessions enter the *current* window. [§16](16-context-engineering.md) managed context inside a session. It left the question of what should persist across sessions, and how.

## Why this exists

**The model is stateless (P2).** A new session starts with an empty window. Without memory, users restate their preferences, the agent rediscovers the repository, and last week's mistake happens again. "Remembering" can only mean one thing: code outside the model saved some information and later put it back into a context.

Knowledge can reach the model from three places (P5):

- **The weights**, through fine-tuning. Slow, expensive, and you can't delete one user's data from them.
- **A corpus**, through RAG ([§09](09-rag.md)): facts someone curated.
- **The agent's own history**, through memory: facts, events and lessons produced by the agent and its users.

Why not keep the whole history and skip the machinery? Because of P3 and P10. Chroma's LongMemEval experiment from [§16](16-context-engineering.md) is a memory benchmark. The same questions were asked with about 300 relevant tokens and with the full ~113K-token history, and every model family did worse on the full version. mem0 reported over 90% lower token cost and 91% lower p95 latency than a full-context baseline (vendor-reported). Memory is a selection problem with a write path, a store and a read path.

For a data engineer the shape is familiar: memory is a small, continuously running ELT pipeline in which an LLM does the transform. It extracts facts from transcripts, MERGEs them into a keyed store, and serves a small, relevant slice at query time. All the usual data-quality problems appear: duplicates, stale rows, conflicting sources, deletion requests. There is one new one: the rows get read back as instructions (P9).

## How it works (under the hood)

### The CoALA memory types

CoALA splits memory into a short-term **working memory** and three long-term memories. Here they are for a data-platform assistant:

| Type | Holds | Concrete example | Typical storage | How it reaches the window |
|---|---|---|---|---|
| **Working** | State of the current decision cycle: goal, plan, latest observations | "Goal: fix failing `orders_daily`; step 3 of 5; last error: warehouse timeout" | Context window plus run state | It *is* the window, assembled each call |
| **Semantic** | Facts about the world, the user, the agent itself | "Prod warehouse is `ANALYTICS_PROD`; user prefers SQL to pandas" | Profile documents, key-value or vector store | Always loaded or retrieved |
| **Episodic** | Specific past experiences | "On 2026-09-02 a full backfill of `orders` timed out; splitting by month worked" | Event log, transcripts, trajectories | Retrieved, often as few-shot examples |
| **Procedural** | How to act: rules, code, skills | "Run `dbt build --select state:modified+` before opening a PR" | System prompt, CLAUDE.md, agent code; implicitly the weights | Always loaded, or loaded on demand |

In warehouse terms, semantic memory is like dimension tables, episodic memory like a fact table of events, and procedural memory the transformation code. Two details from the paper matter. CoALA's working memory is "a data structure that persists across LLM calls", and each prompt is assembled from a subset of it. Procedural memory is implicit in the weights and explicit in the agent's code, and writing new procedural memory "is significantly riskier" than writing the other types, because it changes behavior.

### Short-term vs long-term memory

LangGraph makes the split concrete:

```text
 thread A ──[checkpoint 1]──[checkpoint 2]──[checkpoint 3]    SHORT-TERM
 thread B ──[checkpoint 1]──[checkpoint 2]                    state per thread_id
                 │ read/write              │ read/write
                 ▼                         ▼
 ┌──────────────────── store (shared across threads) ───────────┐  LONG-TERM
 │ ("user-42", "prefs")     "sql_style"  → {"prefers": "CTEs"}  │  namespaced JSON
 │ ("user-42", "episodes")  "2026-09-02" → {"backfill": "..."}  │  documents;
 │ ("org", "rules")         "dbt"        → {"rule": "..."}      │  filter + vector search
 └──────────────────────────────────────────────────────────────┘
```

**Short-term memory** is thread-scoped. A **checkpointer** saves the agent's state (messages, artifacts) after each step, keyed by `thread_id`. That lets a conversation resume, pause for human input or survive a crash ([§14](14-graph-engineering.md), [§20](20-agent-runtime.md)). It is still one thread's context, so it is [§16](16-context-engineering.md)'s problem.

**Long-term memory** lives in a **store**. Namespaces work like folders, often holding user or org IDs, and keys work like file names. You `put` JSON documents, and `get` or `search` them with a content filter plus a semantic query.

LangGraph's docs describe two layouts for semantic memory:

- **A profile**: one document per entity, rewritten on each update. It gets error-prone as it grows.
- **A collection**: many small documents. Easier to write, harder to search as a whole.

### Write paths: hot path vs background

**Hot path.** The agent decides to save something during the conversation, usually by calling a memory tool. LangGraph's docs cite ChatGPT's `save_memories` tool. Anthropic's memory tool and Claude Code's auto memory work the same way. The memory is available immediately and visible to the user. The costs: added latency, one more decision per turn, and a model splitting its attention between the task and the memory.

**Background consolidation.** A separate job reads transcripts afterwards and updates the store. It can be triggered after inactivity, on a cron schedule, or manually. It adds no latency, and a focused job can deduplicate and reconcile entries. The cost is that other threads see new memories late, and you have to tune when the job runs. Examples:

- Generative Agents' periodic "reflection" synthesizes higher-level observations from raw memories.
- Anthropic's **Dreams** **(Preview)** is a research preview on Managed Agents since May 2026. A dream reads a memory store plus 1 to 100 past sessions and writes a *new* store: duplicates merged, stale or contradicted entries "replaced with the latest value", insights added. The input store is never modified, so you can review the output before adopting it. A data engineer will recognize the pattern: build the new table, validate it, swap it in.

### Retrieval: recency, relevance, importance

Writing happens once and reading happens on every turn, so retrieval decides whether a memory system works. Generative Agents (Park et al., Apr 2023) defined the classic scoring rule:

```text
score(m) = α_rec · recency(m) + α_imp · importance(m) + α_rel · relevance(m, query)

recency     = 0.995 ^ (game hours since m was last retrieved)   # exponential decay
importance  = the LLM's 1-10 rating of m, assigned when m is written
relevance   = cosine(embedding(m), embedding(query))
# Each term is min-max scaled to [0, 1]; the paper set every α to 1.
# The top-scoring memories that fit in the window go into the prompt.
```

Other read strategies trade precision for simplicity:

- **Always-load a small index.** Claude Code loads the first 200 lines (or 25KB) of `MEMORY.md` every session and reads topic files on demand. This is [§16](16-context-engineering.md)'s progressive disclosure.
- **Agentic search over files.** Letta's MemFS has no vector index by default; agents search Markdown with ordinary file tools.
- **Vector search in a store**, as in LangGraph and mem0.

Retrieval can fail in visible ways. In a talk at the AI Engineer World's Fair, Simon Willison described ChatGPT pulling his location from memory into an image he had asked for. LangChain's write-up of that example says users can feel the context "no longer belongs to them". A wrongly retrieved memory is context confusion that persists across sessions.

### MemGPT and Letta: the LLM as an operating system

MemGPT's "virtual context management" borrows from operating-system virtual memory:

```text
        MAIN CONTEXT  (prompt tokens = "RAM")            EXTERNAL CONTEXT  ("disk")
 ┌─────────────────────────────────────────────┐
 │ system instructions   read-only             │     ┌──────────────────────────────┐
 │ working context       fixed size; editable  │◄───►│ archival storage             │
 │                       only by function call │     │ arbitrary text, searchable   │
 │ FIFO queue            recent messages;      │     ├──────────────────────────────┤
 │                       slot 0 holds a        │◄───►│ recall storage               │
 │                       recursive summary     │     │ every message, searchable    │
 └─────────────────────────────────────────────┘     └──────────────────────────────┘
  at the warning threshold (e.g. 70%): "memory pressure" message; model saves what matters
  at the flush threshold (e.g. 100%): evict ~half the queue, fold it into the summary
```

The model manages its own memory with function calls. It writes key facts into working context, searches archival storage, and pages old messages back in from recall storage. A `request_heartbeat=true` argument asks for another inference step, so the model can chain several memory operations. The warning before eviction matters: it gives the model a chance to save important details before code throws them out. Memory management becomes the model's decision, executed by code (P6). The tradeoff is that every memory operation costs an extra model step and depends on the model's judgment.

Letta, the company behind MemGPT, kept the OS idea in its products:

- **Memory blocks** are labeled, character-limited sections pinned into the system prompt. They are "always visible" and can be shared between agents.
- **MemFS**, in the V2 Agent SDK, stores long-term memory as git-backed Markdown files with YAML frontmatter and a `MEMORY.md` index, and commits every edit.

The "disk" is now a git repository.

### mem0: extract, consolidate, retrieve

mem0 (Chhikara et al., Apr 2025) runs a two-phase write pipeline:

1. **Extract.** For each new message pair, an LLM reads the pair, a rolling conversation summary (refreshed asynchronously) and the last few messages, and extracts candidate facts.
2. **Consolidate.** For each candidate, the system fetches the most similar existing memories. The LLM then picks one operation by tool call: **ADD** (new fact), **UPDATE** (augment an existing memory), **DELETE** (an existing memory is contradicted) or **NOOP**. This is a MERGE statement whose matching logic is an LLM.

At query time it **retrieves** by vector similarity. A graph variant stores entity-relation triplets for multi-hop and temporal questions. On the LOCOMO benchmark the paper reports a 26% relative improvement over OpenAI's memory on an LLM-as-judge metric (vendor-reported).

### The Anthropic memory tool

You declare the memory tool as `{"type": "memory_20250818", "name": "memory"}`. Anthropic supplies the tool's schema and description, and you supply the storage. Following P6, it is **client-side**: Claude emits a `tool_use` such as `{"command": "view", "path": "/memories"}`, and your code executes it and returns a `tool_result`.

- **Paths.** `/memories` is a virtual prefix that you map onto real storage, such as a per-user directory or database keys.
- **Commands.** `view`, `create`, `str_replace`, `insert`, `delete` and `rename`.
- **Injected protocol.** The API adds an instruction to the system prompt: "ALWAYS VIEW YOUR MEMORY DIRECTORY BEFORE DOING ANYTHING ELSE", plus "ASSUME INTERRUPTION: Your context window might be reset at any moment".
- **Pairing with §16.** The docs pair it with context editing and compaction: compaction keeps the active context small, and memory preserves "the information that must survive summarization."
- **Status.** Launched in beta on Sep 29, 2025. It has needed no beta header since Feb 17, 2026 **(GA)**, though the SDK helper classes (`BetaAbstractMemoryTool`, `BetaLocalFilesystemMemoryTool`) still live in the beta namespace.

Your handler owns security. The docs list path-traversal protection, stripping sensitive data, size caps and expiring unused files. A minimal file-backed handler:

```python
from pathlib import Path
from urllib.parse import unquote

ROOT = Path("memory_store").resolve()  # real storage behind the virtual /memories path
ROOT.mkdir(exist_ok=True)
MAX_BYTES = 50_000                     # cap each file: memory must not grow without bound

def resolve(virtual: str) -> Path:
    v = unquote(virtual)               # decode %2e%2e%2f tricks before checking
    if v != "/memories" and not v.startswith("/memories/"):
        raise ValueError(f"Path must be under /memories: {virtual}")
    real = (ROOT / v.removeprefix("/memories").lstrip("/")).resolve()
    if not real.is_relative_to(ROOT):  # resolve() collapses ../ and follows symlinks
        raise ValueError(f"Path escapes /memories: {virtual}")
    return real

def handle_memory(cmd: dict) -> str:
    if cmd["command"] not in ("view", "create", "str_replace"):
        raise ValueError(f"Unsupported command: {cmd['command']}")  # insert/delete/rename omitted
    p = resolve(cmd["path"])
    if cmd["command"] == "create":
        if len(cmd["file_text"].encode()) > MAX_BYTES:
            raise ValueError("File too large: summarize it before saving.")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cmd["file_text"])  # overwriting is a valid choice per the docs
        return f"File created successfully at: {cmd['path']}"
    if cmd["command"] == "view" and p.is_dir():
        files = sorted(f for f in p.rglob("*") if not f.name.startswith("."))
        return "\n".join(f"{f.stat().st_size}\t/memories/{f.relative_to(ROOT)}"
                         for f in files) or "(empty)"
    if not p.is_file():
        raise FileNotFoundError(f"The path {cmd['path']} does not exist.")
    text = p.read_text()
    if cmd["command"] == "view":        # file contents with 6-wide line numbers
        return "\n".join(f"{i:6}\t{line}" for i, line in enumerate(text.splitlines(), 1))
    old = cmd["old_str"]                # str_replace: the match must be unique
    if text.count(old) != 1:            # zero or several matches: refuse to guess
        raise ValueError(f"old_str must appear exactly once; found {text.count(old)}.")
    p.write_text(text.replace(old, cmd.get("new_str", ""), 1))
    return "The memory file has been edited."
```

Wiring it into the tool loop from [§10](10-tool-use.md):

```python
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def run(user_text: str) -> str:
    messages = [{"role": "user", "content": user_text}]
    while True:
        resp = client.messages.create(
            model="claude-sonnet-5-5", max_tokens=4000, messages=messages,
            tools=[{"type": "memory_20250818", "name": "memory"}])  # no schema needed
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            return next((b.text for b in resp.content if b.type == "text"), "")
        results = []
        for block in resp.content:
            if block.type == "tool_use" and block.name == "memory":
                try:
                    out, err = handle_memory(block.input), False
                except (ValueError, FileNotFoundError) as e:
                    out, err = str(e), True  # report the failure back to Claude
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": out, "is_error": err})
        messages.append({"role": "user", "content": results})  # all results in one turn
```

OpenAI and Gemini don't have a built-in equivalent. Declare an ordinary function tool with the same commands, and the handler code stays the same. On Anthropic's hosted Managed Agents, **memory stores** **(Preview)** (public beta since Apr 23, 2026) provide a hosted version:

- A store is a workspace-scoped collection of small text documents (≤100KB each), mounted into the session's container as a directory.
- The agent uses its ordinary file tools on it.
- Every change creates an immutable version, which supports audit, rollback and redaction.

### Files as memory

From 2025 into 2026 the field converged on a plain answer: memory is files that the agent reads with file tools.

- **Human-written instructions.** CLAUDE.md and AGENTS.md hold procedural and semantic memory and load in every session. Claude Code's docs advise keeping each file under 200 lines and warn that when two instructions contradict, Claude "may pick one arbitrarily". Path-scoped rules load only for matching files. AGENTS.md is a cross-tool convention (Codex, Jules, Aider, Zed, Devin and others). OpenAI's harness team keeps theirs to about 100 lines, "a map, not a manual" ([§19](19-harness-engineering.md)).
- **Agent-written notes.** Claude Code's auto memory writes to `~/.claude/projects/<project>/memory/`: a `MEMORY.md` index plus topic files typed `user`, `feedback`, `project` or `reference`. It skips anything derivable from the code, and it stamps each file with a `modified` timestamp, so staleness is visible.
- **Progress files and git.** The long-running harness from [§16](16-context-engineering.md) pairs a progress log with `git log`. Git history is episodic memory with timestamps, diffs and authorship for free, and `git revert` is memory rollback.

Files won because they are inspectable, diffable and versioned. Models are also heavily trained on file tools, and there is no embedding index to drift. Files are weak at fuzzy recall across thousands of items and at isolating many users at scale. That is where a store with search earns its place, and many systems combine an index file with search.

### Failure modes

- **Memory poisoning.** This is P9 stretched across time. If an agent writes content from an untrusted source (a web page, an email, a tool result) into memory, any injected instruction is replayed into every future session: prompt injection that persists. OWASP's Top 10 for Agentic Applications (Dec 2025) lists Memory & Context Poisoning (as ASI06, per secondary sources **(⚠ verify)**). Defenses:
  - Record where each memory came from (provenance).
  - Don't auto-save from untrusted content without review.
  - Mount shared and procedural memory read-only.
  - Keep versions so you can roll back.
  - Limit what remembered text can trigger, through least privilege on tools ([§32](32-security-guardrails.md)).
- **Self-poisoning.** The agent's own hallucination gets saved and becomes a "fact". This is Breunig's context poisoning, now crossing sessions.
- **Staleness and contradiction.** "The team uses Redshift" (2025) and "the team migrated to Snowflake" (2026) can both sit in the store and clash at read time. Defenses: timestamps, UPDATE/DELETE during consolidation, background jobs that replace stale entries with the latest value, and a rule that the newest entry wins.
- **Privacy and deletion.** Memory is personal data. Never store secrets: Anthropic's docs warn that a key written once is replayed into every later session that mounts the store. A deletion request, such as a GDPR erasure request, must reach every copy: raw memories, summaries, embeddings and version history. The reference memory handlers have no access control, so enforce per-user namespaces and authentication yourself.
- **Unbounded growth.** If the always-loaded part grows every session, it brings back [§16](16-context-engineering.md)'s rot and cost. Use hard caps (Claude Code's 200-line or 25KB index limit, file-size limits), expire memories nobody reads, and consolidate periodically.

## Comparison

**Memory vs RAG vs fine-tuning (P5):**

| | Memory | RAG | Fine-tuning |
|---|---|---|---|
| What it changes | What enters context, from the agent's own history | What enters context, from a curated corpus | The weights |
| Who writes it | The agent, a background job, or the user | An ingestion pipeline | A training job |
| Freshness | Next turn or next session | As fresh as the index | Frozen until you retrain |
| Scope | Per user or per project | Shared corpus | Everyone using the model |
| Deleting one item | Delete the record and its derived copies | Delete the document and re-index | Effectively impossible without retraining |
| Best for | Preferences, project state, lessons learned | Facts, policies, documentation | Behavior, style, output format |
| Avoid when | The fact belongs in a shared, reviewed corpus | Answers depend on this user's own history | Facts change or are per-user |

**Memory implementations:**

| System | Who writes | Storage | Retrieval | Strength | Weakness |
|---|---|---|---|---|---|
| CLAUDE.md / AGENTS.md | Humans | Repo files | Always loaded | Reviewed, versioned | Costs tokens every session |
| Claude Code auto memory | Agent (hot path) | Local Markdown with index | Index loaded; topics on demand | Zero effort; typed; timestamped | Machine-local; can collect stale notes |
| Anthropic memory tool | Agent (hot path) | Your backend behind `/memories` | Agent views files | You own the data | You build security and limits |
| Managed Agents memory store **(Preview)** | Agent; Dreams consolidate | Hosted, versioned documents | File tools | Audit and rollback built in | Anthropic platform only |
| LangGraph store | Your nodes, hot path or background | Namespaced JSON | Filter plus vector search | Flexible; fits graph agents | You design schema and policy |
| mem0 | Extraction pipeline | Vector (plus graph) | Similarity search | Automatic dedupe and updates | LLM calls per write; opaque merges |
| Letta | The agent itself (self-editing) | Memory blocks plus git-backed MemFS | Pinned blocks; file search | OS-style tiers; git history | Framework commitment |

## What it didn't solve

Memory decides which facts and experiences come back. The awkward category is procedural know-how: "how we do X here", such as the backfill runbook or the PR checklist. Kept in an always-loaded file, it costs tokens on every turn whether or not the task needs it. Copying it into each prompt, agent and tool doesn't scale across a team. The next step is packaging know-how so the agent sees only a short description and loads the full procedure when the task calls for it.

→ Next: [§18 Skills](18-skills.md)

## Check your understanding

**Q: Why can't a model "just remember" a user's preferences between sessions, and what does a memory system do instead?**

The model is stateless: nothing from one API call survives into the next (P2), and its weights don't change during use. A memory system writes chosen information to storage outside the model and puts a relevant slice back into a later context, so quality depends on the write and read policies. If you need changed behavior for everyone, that's a fine-tuning question, not a memory question.

**Q: Semantic vs episodic memory: which would you use to stop an agent repeating a failed backfill strategy, and why?**

Episodic memory stores specific experiences, such as "the full backfill timed out on 2026-09-02; splitting by month worked", which can be retrieved as worked examples when a similar task comes up. Semantic memory stores standing facts, such as "orders is partitioned by month". The lesson begins as an episode. If it keeps recurring, promote it to a procedural rule in CLAUDE.md or a skill, so it doesn't depend on retrieval finding the right episode.

**Q: What would happen if an agent saved a summary of every web page it read into long-term memory without review?**

Any instruction hidden in a page would be replayed into every future session, a persistent prompt injection: OWASP's memory and context poisoning (P9). The store would also fill with low-value, contradictory content, which hurts retrieval and costs tokens. Save only distilled facts with provenance, review writes from untrusted sources, and keep versions so you can roll back.

**Q: Hot-path vs background memory writes: when would you choose each?**

Hot-path writes happen during the conversation, so the memory is usable immediately and visible to the user, at the cost of latency and a model splitting its attention. Background consolidation runs later, adds no latency, and can deduplicate and reconcile carefully, but other sessions see updates late. Use the hot path for explicit "remember this" requests and corrections. Use background jobs for mining patterns across many sessions.

**Q: Why did MemGPT warn the model about "memory pressure" before evicting messages, rather than just evicting them?**

Eviction is done by code, which can't judge which details matter. The warning at a threshold such as 70% gives the model a turn to move important facts into working context or archival storage before the queue manager drops half the messages into a summary. Decide what to keep before the cut, not after.

**Q: A support agent needs each customer's plan, the refund policy and the company's tone of voice. Where should each live?**

The customer's plan is per-user and changes, so it belongs in memory or, better, a live lookup tool against the system of record. The refund policy is shared, reviewed knowledge, so retrieve it with RAG and cite it. Tone of voice is behavior, so put it in the system prompt first and fine-tune only if prompting fails at scale (P5).

**Q: Why have so many 2025-26 memory systems converged on plain files, and when is a vector store still the better choice?**

Files are readable and editable by humans, versionable with git, and navigable with file tools models are trained heavily on, with no embedding index to drift. A directory gets unwieldy with fuzzy recall across thousands of memories, many concurrent writers or strict per-user isolation. Then a store with filters and vector search fits better, often behind a small index file.

## Takeaways

- Memory is the write path, store and read path that put past-session tokens into future contexts (P2); the model itself learns nothing.
- CoALA types: working (the current window), semantic (facts), episodic (experiences) and procedural (rules and code; the riskiest to write).
- Short-term memory is thread state in a checkpointer; long-term memory is a namespaced store shared across threads.
- Hot-path writes are immediate but slow the agent; background consolidation (reflection, Dreams) deduplicates and replaces stale entries.
- Retrieval quality decides everything: score by recency, importance and relevance, or keep a small always-loaded index and read files on demand.
- The field converged on files: Claude Code's auto memory, Anthropic's memory tool, Managed Agents memory stores and Letta's MemFS.
- Memory poisoning is persistent prompt injection (P9): record provenance, review untrusted writes, version everything, and cap growth.
- "Memory engineering" is a 2026 label for a subset of context engineering.

## Sources

- Sumers, Yao, Narasimhan & Griffiths, "Cognitive Architectures for Language Agents" (CoALA, Sep 2023): https://arxiv.org/abs/2309.02427
- Packer et al., "MemGPT: Towards LLMs as Operating Systems" (Oct 2023): https://arxiv.org/abs/2310.08560
- Park et al., "Generative Agents: Interactive Simulacra of Human Behavior" (Apr 2023): https://arxiv.org/abs/2304.03442
- Chhikara et al., "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory" (Apr 2025): https://arxiv.org/abs/2504.19413
- Claude docs, Memory tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- Claude docs, Managed Agents memory: https://platform.claude.com/docs/en/managed-agents/memory
- Claude docs, Dreams (research preview): https://platform.claude.com/docs/en/managed-agents/dreams
- Claude docs, Release notes: https://platform.claude.com/docs/en/release-notes/overview
- Anthropic, "Managing context on the Claude Developer Platform" (Sep 29, 2025): https://www.anthropic.com/news/context-management
- Anthropic, "Effective context engineering for AI agents" (Sep 29, 2025): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic, "Effective harnesses for long-running agents" (Nov 26, 2025): https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Claude Code docs, "How Claude remembers your project": https://code.claude.com/docs/en/memory
- LangChain docs, Memory overview: https://docs.langchain.com/oss/python/concepts/memory
- LangChain, "Context Engineering" (Jul 2, 2025): https://blog.langchain.com/context-engineering-for-agents/
- Letta docs, Memory blocks: https://docs.letta.com/guides/agents/memory-blocks
- Letta docs, MemFS: https://docs.letta.com/concepts/memfs
- AGENTS.md: https://agents.md
- OpenAI, "Harness engineering: leveraging Codex in an agent-first world" (Feb 11, 2026): https://openai.com/index/harness-engineering/
- OWASP GenAI Security Project, "OWASP Top 10 for Agentic Applications for 2026" (Dec 2025): https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- Hong, Troynikov & Huber, "Context Rot" (Chroma, Jul 2025): https://research.trychroma.com/context-rot
