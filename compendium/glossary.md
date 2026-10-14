# Glossary

> As of October 2026. Each term links to the section that explains it. Principles (P1–P12) are defined in [§01](01-first-principles.md).

**Jump to:** [A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [J](#j) · [K](#k) · [L](#l) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · [Q](#q) · [R](#r) · [S](#s) · [T](#t) · [V](#v) · [W](#w)

## #

**12-factor agents**: HumanLayer's 2025 practitioner guide (Dex Horthy) of principles for production agents, such as owning your prompts and your context window and keeping agents small and focused; HumanLayer says it was the first use of "context engineering." → [§38](38-disciplines-map.md) · [§16](16-context-engineering.md)

**429 vs 529**: A 429 means you exceeded your own quota (wait for `retry-after`, or use a model with its own limit; a spend-cap 429 must not be retried); a 529 `overloaded_error` means Anthropic is overloaded for everyone (back off, or fall back to another model or provider). → [§30](30-cost-latency-reliability.md)

## A

**A2A (Agent2Agent)**: Google's protocol (Apr 2025, now an AAIF project) for agents to delegate tasks to other, opaque agents across vendors and frameworks, using Agent Cards and tasks that move through states (working, input-required, completed, failed and others), with outputs as artifacts and updates by polling, SSE streaming or push notifications. MCP is agent↔tool; A2A is agent↔agent. It is not meant for your own internal subagents. → [§15](15-protocols-mcp-a2a.md) · [§13](13-multi-agent.md)

**Access token and refresh token**: An access token is a short-lived credential, typically a JWT (a signed set of claims), sent on every API request; whoever holds it can use it. A refresh token is a longer-lived credential the client trades for fresh access tokens, kept in a vault and never sent to resource servers. Neither belongs in the model's context (P9). → [§33](33-agent-identity.md)

**Accessibility tree**: The semantic view of a page that screen readers use, derived from the DOM (the browser's raw element tree, which also hides invisible text where injections lurk): each element's role, name and state, such as `button "Search"`. Reading it costs fewer tokens than a screenshot and names exact targets, but it is blind to canvas, video and poorly marked-up pages. → [§24](24-computer-use-and-research-agents.md)

**ACL (access-control list)**: The list of who may read a document, stored as chunk metadata so the retriever can filter by the end user's identity before passages reach the model. Permissions must be enforced in the retriever, never in the prompt (P9). → [§09](09-rag.md)

**Adaptation ladder**: The order in which to try fixes, cheapest and most reversible first: prompt, few-shot, RAG and tools, prompt optimization (all changing the context), then SFT, DPO, RFT and distillation (changing the weights). Measure every rung with evals. → [§29](29-adapting-models.md)

**AG-UI**: An open event protocol (1.0 as of Oct 2026) between an agent backend and a frontend, usually an HTTP POST answered by an SSE stream with run, text, tool-call, reasoning, state, activity and subagent events; approvals are modeled as interrupts and resumes. It carries UI rather than defining it (P11). → [§35](35-ai-ux.md)

**Agent**: An LLM using tools in a loop, getting feedback from the environment and choosing each next action, until a stopping condition fires. The model owns control flow (P7). Not to be confused with a *workflow*, where your code decides the sequence. → [§11](11-agents.md)

**Agent Card**: A JSON document, conventionally at `/.well-known/agent-card.json`, where an A2A agent advertises its interfaces, capabilities, security schemes and skills; it can be signed so clients can verify the publisher. Like an OpenAPI document plus a registry entry. → [§15](15-protocols-mcp-a2a.md)

**Agent legibility**: Making logs, UI, metrics and docs accessible to the agent in context, because "anything it can't access in-context while running effectively doesn't exist." → [§19](19-harness-engineering.md)

**Agent loop**: The core `while stop_reason == "tool_use"` loop, about 20 lines: call the model, execute each requested tool, append the results as an observation, and repeat. Everything later sections add is code around this loop. → [§11](11-agents.md)

**Agent runtime**: The layer under the harness that decides where it runs and keeps it alive, with four jobs: isolation (sandboxing), durability (surviving crashes), duration (running with no client attached) and control (approvals and spend). → [§20](20-agent-runtime.md)

**Agent Skill**: A folder that packages procedural know-how, a required `SKILL.md` plus optional scripts, references and assets, which the agent loads only when the task needs it. Idle skills cost about 100 tokens each (P3), and bundled scripts are run rather than read, so only their output enters context. Launched by Anthropic in Oct 2025 and published as an open standard at agentskills.io in Dec 2025 (P11). Not to be confused with a *tool* (one typed action the harness runs) or an *MCP server* (access to an external system): a skill says *how*, tools and MCP give *access*. → [§18](18-skills.md)

**Agentic AI Foundation (AAIF)**: A Linux Foundation directed fund launched Dec 2025 by Anthropic, Block and OpenAI that hosts MCP, goose and AGENTS.md, and since Aug 2026 A2A. → [§15](15-protocols-mcp-a2a.md)

**Agentic browser**: An agent built into your everyday browser with your logged-in sessions; it combines real cookies, untrusted pages and the power to act, the worst case for the lethal trifecta (P9). → [§24](24-computer-use-and-research-agents.md)

**Agentic engineering**: Karpathy's term (Feb 2026) for professional development where agents write most of the code and you orchestrate, specify, verify and review. The tools are the same as vibe coding; the accountability differs. → [§23](23-coding-agents.md) · [§38](38-disciplines-map.md)

**Agentic RAG**: Giving the model a search tool and letting it decide whether, what and how often to search, instead of code retrieving once up front. It suits multi-hop questions at the cost of more calls, latency and variance (P7). → [§09](09-rag.md)

**Agents Rule of Two**: Meta's 2025 guideline that within one session an agent should have at most two of untrustworthy inputs, access to sensitive systems or private data, and the ability to change state or communicate externally; all three need human or other reliable supervision. → [§32](32-security-guardrails.md)

**AGENTS.md**: The cross-vendor instruction file: plain Markdown with commands, conventions and boundaries that coding agents load at the start of every session, because a stateless model needs whatever a new teammate would (P2). A shared name since Aug 2025, now stewarded by the AAIF; keep it a short map (about 100–200 lines), and in a monorepo the closest file to the edited code wins (P11). → [§23](23-coding-agents.md) · [§19](19-harness-engineering.md)

**AI disclosure (Art. 50)**: The EU AI Act transparency duty, applying since Aug 2, 2026, to tell people they are dealing with an AI unless obvious, mark generated media in a machine-readable way, and label deepfakes (for example with C2PA Content Credentials or watermarks). Disclose at first contact in the UI, not in the terms of service. → [§34](34-governance-regulation.md) · [§35](35-ai-ux.md)

**AI engineering**: The discipline of turning a general-purpose foundation model (one large pretrained model, reachable through an API, that does many tasks depending on the text you give it) into reliable software, by building around the model rather than training it. Not to be confused with *ML engineering*, where you collect labeled data and train one model per task. → [§01](01-first-principles.md)

**AI gateway**: A shared layer between apps and model providers that handles access control (virtual keys per team, so real keys never leave it), budgets, routing, retries, fallbacks, logging and sometimes caching and guardrails, turning N×M provider plumbing into one layer (P11). It needs its own redundancy. → [§30](30-cost-latency-reliability.md)

**AI inventory**: A list of every AI use case with its owner, purpose, models, data, risk tier and status, the AI version of a data catalog. Without it you can't answer a regulator, a customer questionnaire or your own security team. Pair it with a reviewed rules table that maps each use case to a risk tier and its controls. → [§34](34-governance-regulation.md)

**Ambient agent**: An agent triggered by events rather than messages that runs in the background; its natural UI is an inbox, with three human-in-the-loop patterns: notify (flag, take no action), question (ask instead of guessing) and review (approve a proposed action). → [§35](35-ai-ux.md)

**Anthropomorphism**: Attributing understanding, intent and reliability to fluent first-person text, which drives over-trust; NIST lists it under "Human-AI Configuration." Disclose that it's an AI and avoid fake human cues. The opposite failure, algorithm aversion, is rejecting the system after one visible mistake; aim for calibration. → [§35](35-ai-ux.md)

**Approval card**: The UI for a paused consequential action: what will happen (the tool and its full, untruncated arguments), why, a preview of the effect, whether it can be undone, and scope choices (once, always for this project, deny with a note, edit). → [§35](35-ai-ux.md)

**Approval fatigue**: People rubber-stamping approval prompts because there are too many of them. A sandbox boundary replaces a hundred per-action prompts with one decision; in UX, let reads run freely, give reversible writes an undo, and ask only for irreversible or externally visible actions. → [§20](20-agent-runtime.md) · [§35](35-ai-ux.md)

**Approximate nearest neighbor (ANN) search**: Vector search that returns most of the true nearest neighbors much faster than exact kNN, which scores every stored vector like a full table scan. The share it returns is the index's recall, traded against speed through index knobs. Common indexes are HNSW, IVF (k-means partitions, like partition pruning) and product quantization (lossy compression of the vectors). → [§08](08-embeddings-and-search.md)

**Asymmetry of verification**: Jason Wei's observation that "some tasks are much easier to verify than to solve." AI pays where checking an output is much cheaper than producing it; if checking takes as long as doing, a careful person must redo the work (P8). Wei's corollary, the verifier's rule, says the easier a task is to verify, the easier it is to train AI on, so verifiable tasks improve fastest. → [§36](36-product-thinking.md)

**At-least-once vs effectively-once**: A durable step records its result only after its side effect, so a crash in between re-runs it (at-least-once). Making each side effect idempotent with a key from the run and step ID turns that into effectively-once, as in streaming pipelines. → [§20](20-agent-runtime.md)

**Audience**: The resource server a token is valid for (the `aud` claim). The `resource` parameter (RFC 8707, a resource indicator) asks the authorization server to bind a token to one audience, and servers must reject tokens not issued for them. → [§33](33-agent-identity.md) · [§15](15-protocols-mcp-a2a.md)

**Audit log**: A complete, append-only, retention-governed record of each decision (actor, model, prompt version, sources, tool calls, output reference, human review) that can reconstruct it months later. Store the output, because a sampled result can't be recomputed (P4). Not to be confused with an *observability trace*, which is sampled and short-lived; they join by trace ID. → [§34](34-governance-regulation.md) · [§32](32-security-guardrails.md)

**Augmented LLM**: The basic building block of agentic systems: an LLM enhanced with retrieval, tools and memory. A workflow arranges augmented-LLM calls in code; an agent puts one in a loop. → [§11](11-agents.md) · [§12](12-agentic-design-patterns.md)

**Authorization drift**: A time-of-check to time-of-use gap where a user's permissions change mid-workflow but the agent carries on with its original token; short-lived tokens limit it. → [§33](33-agent-identity.md)

**Automate vs augment**: Automate when errors are cheap and reversible and the check is computational; augment (AI drafts, a human reviews or approves) when work needs judgment or errors are costly or silent. Most products start as augmentation and automate one task at a time as evals justify it (P7). → [§36](36-product-thinking.md)

**Automation bias**: The tendency to rely, or over-rely, on automated output. The EU AI Act requires overseers to stay aware of it; a 99.8% approval rate at two seconds per item is a rubber stamp. → [§34](34-governance-regulation.md) · [§35](35-ai-ux.md)

**Autoregressive generation**: Generating text by sampling one token, appending it to the sequence, and repeating, so each output becomes input for the next step (P1). → [§01](01-first-principles.md) · [§02](02-how-llms-work.md)

## B

**Back pressure**: Automated checks (tests, type checkers, linters, schema validators) that reject bad output and push a short error back into the next iteration, keeping a loop converging instead of compounding errors (P8). It must be fast, terse and impossible for the maker to switch off. → [§21](21-loop-engineering.md) · [§23](23-coding-agents.md)

**Background consolidation**: A separate job that reads transcripts after the fact and updates the memory store: deduplicating, replacing stale entries and adding insights, with no latency to the user (examples: Generative Agents' reflection, Anthropic's Dreams). → [§17](17-memory.md)

**Barge-in**: The user starting to talk while the agent is speaking. Handling it means stopping playback, flushing buffers, cancelling in-flight work and truncating the history to the audio the user actually heard, because the model believes whatever the history says (P2). Backchannels ("mm-hm"), coughs and the agent's own echo are not interruptions. → [§25](25-voice-agents.md)

**Base model**: The raw pretrained model, which continues documents rather than answering. Mostly seen in open-weights releases as a starting point for fine-tuning. Not to be confused with a *chat model*. → [§02](02-how-llms-work.md)

**Batch API**: An asynchronous API mode where the provider schedules your requests into spare capacity in exchange for a 50% discount on input and output. Fits work that doesn't need an answer now. OpenAI's flex processing offers Batch rates on synchronous calls in exchange for slower responses. → [§03](03-inference.md) · [§30](30-cost-latency-reliability.md)

**Bi-encoder**: A retriever that encodes the query and each document separately, so they meet only in one dot product. Scalable because document vectors are computed once at ingest, but the model never reads the two together. → [§08](08-embeddings-and-search.md)

**Bitter lesson**: Rich Sutton's 2019 observation that general methods using more computation beat hand-coded human knowledge over time. In AI engineering it means scaffolding built for a weaker model gets deleted when a stronger one arrives, so keep it thin and removable (P12). → [§01](01-first-principles.md)

**BM25**: The standard ranking function for lexical search over an inverted index (term → list of documents). It weights query terms by rarity (IDF) and frequency with diminishing returns and normalizes for document length, so it excels at exact IDs, error codes and new jargon. It remains a robust baseline that dense retrievers often fail to beat outside their domain. → [§08](08-embeddings-and-search.md)

**Browser agent**: An agent that drives web pages, either by reading page structure (the DOM or accessibility tree) or by screenshots and coordinates. Read the tree first and fall back to pixels. → [§24](24-computer-use-and-research-agents.md)

**Build, buy or wait**: Three options for an AI capability. Buy commodity capabilities, build where workflow, data or integration is your edge, and wait when the gap is model capability, building only the eval, data access and integration that survive model changes (P12). → [§36](36-product-thinking.md)

**Byte-pair encoding (BPE)**: The tokenizer-building method most models use: start from single bytes and repeatedly merge the most frequent adjacent pair into a new vocabulary entry until the vocabulary reaches its target size. → [§02](02-how-llms-work.md)

## C

**Cache-aware layout**: Ordering the prompt by stability (tools, then system, then messages), keeping history append-only, and putting volatile values like the date in the newest turn, so prompt caching keeps hitting (P10). Curating and caching pull against each other. → [§16](16-context-engineering.md) · [§30](30-cost-latency-reliability.md)

**Calibrated trust**: The AI UX goal that users rely on the system where it is reliable and check it where it isn't, rather than maximal trust. Not to be confused with model *calibration*, a property of the model's confidence scores. → [§35](35-ai-ux.md)

**Calibration**: How well a model's or grader's confidence matches its actual accuracy. Post-training can hurt it (§02), browsing models were worse calibrated (§24), and LLM judges must be calibrated against human labels (§26). Not to be confused with *calibrated trust*, a UX goal. → [§02](02-how-llms-work.md) · [§26](26-evals.md)

**CaMeL**: A 2025 design that fixes the dual-LLM flaw: the privileged LLM writes a restricted program from the trusted query before any data is read, a custom interpreter runs it, every value carries capabilities (provenance and allowed readers), and policies are checked at each tool call. It solved 77% of AgentDojo tasks with provable security versus 84% undefended. → [§32](32-security-guardrails.md)

**Capability ceiling**: Google's finding that once a single agent already does well (above about 45% accuracy), adding agents gives negative returns. → [§13](13-multi-agent.md)

**Capability eval vs regression eval**: Capability evals start low and give you a hill to climb; regression evals sit near 100% and catch backsliding. Saturated capability tasks graduate into the regression suite. → [§26](26-evals.md)

**Cascade (STT → LLM → TTS)**: A voice architecture that chains speech-to-text, a text LLM and text-to-speech. The text transcript can be logged, redacted and checked, and any LLM (Claude included) fits, but latency adds up across handoffs and prosody (tone, emphasis, hesitation) is lost. Not to be confused with a *model cascade* in cost engineering. → [§25](25-voice-agents.md) · [§07](07-multimodal.md)

**Catastrophic forgetting**: Losing earlier abilities when a network trains on something new, because the loss mentions only the new task. Mitigate with LoRA, mixed-in general data, low learning rates, a pull toward the reference model, and regression evals on general skills. → [§29](29-adapting-models.md)

**Causal mask**: The rule in decoder-only (GPT-style) models that a token can attend only to itself and earlier tokens. It is why earlier tokens' keys and values never change, which makes the KV cache and prompt caching possible. → [§02](02-how-llms-work.md) · [§03](03-inference.md)

**Chain of thought (CoT)**: Having the model write intermediate reasoning before its answer, which buys one extra forward pass per token and a scratchpad later steps can attend to (P1). Prompted CoT imitates the form of reasoning; on current models it is built in and governed by effort. → [§04](04-reasoning-models.md)

**Chat model**: A model post-trained to follow a conversation format (also called an instruct model). The conversation is still one token sequence rendered through a chat template. → [§02](02-how-llms-work.md)

**Chat template**: The format, with special tokens marking each role, that a server uses to render structured messages into the single token sequence the model actually sees. Self-hosted models must use the template they were trained on; gpt-oss, for example, should only be used with the harmony format. → [§05](05-api-and-prompting.md) · [§31](31-open-weights-self-hosting.md)

**Checkpoint**: A snapshot of the whole run state saved after a step, like a periodically materialized table, so a failure rolls back to the last good point rather than to zero. A resumed node re-runs from its start, so code before the checkpoint boundary must be idempotent. → [§20](20-agent-runtime.md) · [§14](14-graph-engineering.md)

**Checkpointer**: The component that saves graph state after every step (a LangGraph "super-step"), keyed by a `thread_id` (one conversation or workflow instance). One mechanism gives short-term memory, durable resumption, human-in-the-loop and time travel. Checkpoints sit at step boundaries, so a resumed node re-runs from its first line. → [§14](14-graph-engineering.md) · [§17](17-memory.md)

**Chunking**: Splitting documents into retrievable units before embedding. Small chunks match precisely but lose referents; large chunks keep context but dilute the vector and spend more tokens. Variants include parent-child retrieval (match on small chunks, return the enclosing section) and late chunking (embed the whole document, then pool per chunk). Choose sizes by measuring recall@k on your own queries. → [§09](09-rag.md)

**Citations**: Pointers from each claim in a response to the source span that supports it. Anthropic's citations guarantee the quoted text exists in the documents you supplied, not that it supports the claim; their value is making verification one click (P8). → [§35](35-ai-ux.md) · [§09](09-rag.md)

**CLAUDE.md**: Claude Code's instruction file, loaded at the start of every session; Claude Code also reads `AGENTS.md` when no `CLAUDE.md` exists. → [§23](23-coding-agents.md) · [§17](17-memory.md)

**Client ID Metadata Document (CIMD)**: An OAuth client registration method where the `client_id` is an HTTPS URL pointing to a JSON document with the client's name and redirect URIs, preferred in MCP over the now-deprecated Dynamic Client Registration. → [§33](33-agent-identity.md)

**Client vs server tools**: A client tool's code runs in your application: user-defined, or Anthropic-schema (a schema Anthropic publishes and trains in, such as bash or the text editor, which the model calls more reliably). A server tool, such as web search or code execution, runs on the provider's side, so you never build a `tool_result`; when its internal loop hits a cap you get `stop_reason: "pause_turn"` and resend to continue. → [§10](10-tool-use.md)

**CoALA**: A 2023 framework (Cognitive Architectures for Language Agents) that borrowed memory types from cognitive science: short-term working memory (the current goal, plan and observations, in practice the context window) plus long-term semantic, episodic and procedural memory. → [§17](17-memory.md)

**Code as action (CodeAct)**: Having the agent write executable code as its action instead of one JSON call, so it can loop, branch and hold data between calls. It needs a sandbox and makes individual actions harder to gate and audit. → [§10](10-tool-use.md) · [§12](12-agentic-design-patterns.md)

**Coding agent**: An agent that can read, edit and run code in a loop until a goal is met: the agent loop plus search, read, exact-match edit and run tools, with git as checkpoint, review surface and undo. Code led adoption because tests and compilers are cheap verifiers (P8). The SWE-agent paper called the tool layer the agent-computer interface (ACI) and showed that designing it for the model raises success rates. → [§23](23-coding-agents.md)

**Cohen's kappa**: An agreement score corrected for chance (1 is perfect, 0 is chance), used to check LLM labelers against humans and humans against each other. → [§28](28-data-flywheels.md)

**ColBERT (late interaction)**: A retriever that stores one vector per document token and scores with MaxSim (each query token takes its best-matching document token, and the maxima are summed). Near-reranker quality with precomputed vectors, at the cost of storage that grows with document length. → [§08](08-embeddings-and-search.md)

**Compaction**: Summarizing the conversation as it nears the limit and continuing from the summary, keeping recent turns verbatim. It keeps one agent going but is lossy, so tune the summary prompt for recall first. Not to be confused with a *context reset*, which starts a fresh agent. → [§16](16-context-engineering.md)

**Component catalog**: The fixed set of UI components a model may emit in declarative generative UI (OpenAI ChatKit widgets, A2UI), which the app validates and renders with its own native, accessible widgets. → [§35](35-ai-ux.md)

**Compound engineering**: Every's practice (2025) that "each unit of engineering work should make subsequent units easier": Plan → Work → Review → Compound, where the compound step writes each lesson into `CLAUDE.md` or a reviewer agent. It is the ratchet with a name. → [§23](23-coding-agents.md)

**Compounding error**: If each step succeeds independently with probability p, n steps all succeed with probability pⁿ: 95% per step over 20 steps is about 36%. Verification and retries turn silent errors into recoverable ones (P8). → [§11](11-agents.md) · [§01](01-first-principles.md)

**Comprehension debt**: The growing gap between how much code a loop or agent ships and how much of the codebase you actually understand. → [§21](21-loop-engineering.md) · [§23](23-coding-agents.md)

**Computational vs inferential controls**: Harness checks that are deterministic and cheap (tests, linters, type checkers) versus ones where an LLM judges meaning (AI review, LLM-as-judge), which are slower, costlier and probabilistic. Prefer computational ones where they exist (P8). → [§19](19-harness-engineering.md) · [§11](11-agents.md)

**Computer-use agent**: An agent that drives a desktop through screenshots and clicks: the model emits an action such as `left_click` at coordinates, the harness performs it in a sandboxed VM, and the new screen returns as image tokens (P1, P6). It works on any GUI but is slow, costly and has no built-in verifier. It succeeds RPA, scripts recorded against screen positions that broke when layouts changed. → [§24](24-computer-use-and-research-agents.md)

**Confidence interval**: A range that, across repeated samples, would contain the true rate 95% of the time; near 50% it is about ±1/√n, so ±10 points at 100 cases. The Wilson interval behaves well at small n; clustered standard errors widen it for related cases (sometimes threefold); paired comparisons on the same cases cut noise; power analysis gives the n needed to detect a change you'd act on. → [§26](26-evals.md)

**Confused deputy**: A program with authority tricked into using it for someone else, such as a shared service-account agent that any user, or any document it reads, can steer into actions the requester couldn't take. Authorize each hop against the original user's identity (P9). → [§33](33-agent-identity.md) · [§15](15-protocols-mcp-a2a.md)

**Constrained decoding**: Making invalid tokens impossible rather than unlikely: at each step the inference code sets the logits of tokens the grammar forbids to −∞, renormalizes, and samples from what is left. The grammar owns the shape; the model still owns the content (P6). → [§06](06-structured-outputs.md)

**Contamination**: Benchmark or eval data leaking into training data, so scores measure memorization rather than skill; decontamination removes eval items from training sets. → [§26](26-evals.md) · [§28](28-data-flywheels.md)

**Context anxiety**: Some models "wrapping up work prematurely as they approach what they believe is their context limit." Context resets fixed it for Sonnet 4.5; later models largely removed the behavior, so the workaround was deleted (P12). → [§16](16-context-engineering.md) · [§19](19-harness-engineering.md)

**Context distraction, confusion and clash**: Three of Drew Breunig's four ways context fails, alongside poisoning: distraction (a context so long the model leans on it instead of its training), confusion (irrelevant content, often extra tool definitions, gets used anyway) and clash (parts of the context contradict each other). → [§16](16-context-engineering.md)

**Context engineering**: Choosing, on every turn, the smallest set of high-signal tokens that maximize the chance of the desired outcome: everything the model sees, not just the prompt wording (P2, P3). Prompt engineering is one part of it. → [§16](16-context-engineering.md)

**Context isolation**: Giving a subagent its own fresh window so it can burn tens of thousands of tokens reading and searching and hand back a 1,000–2,000-token summary, keeping the lead's context clean (P3). → [§13](13-multi-agent.md) · [§16](16-context-engineering.md)

**Context poisoning**: A hallucination or error that enters the context and keeps being referenced, such as a false goal the agent chases. Keep observed errors as evidence, but correct invented content, especially in summaries and notes. Not to be confused with *memory poisoning*, where an attacker plants content in persistent memory. → [§16](16-context-engineering.md)

**Context reset**: Starting a fresh agent with an empty window and a structured handoff (progress file and next steps) instead of summarizing. It gives a clean slate and cured context anxiety in some models, at the cost of orchestration. Not to be confused with *compaction*. → [§16](16-context-engineering.md) · [§19](19-harness-engineering.md)

**Context rot**: The gradual decline in how reliably a model uses its context as input grows, even on simple tasks (Chroma's 2025 study of 18 models). Context is a finite attention budget, every irrelevant token competes with useful ones, and the decline is a gradient, not a cliff (P3). → [§16](16-context-engineering.md) · [§02](02-how-llms-work.md)

**Context window**: The most tokens one call can hold, input plus output. It is the model's only working memory (P2), and the useful window is smaller than the advertised one because quality degrades as it fills (P3). → [§02](02-how-llms-work.md) · [§16](16-context-engineering.md)

**Context-centric decomposition**: Splitting work by context boundary rather than by job title, so one agent writes a feature *and* its tests because it already holds the context. Role-based splits spent more tokens on coordination than on work. → [§13](13-multi-agent.md)

**Contextual retrieval**: Anthropic's technique (Sep 2024) of having an LLM write 50–100 tokens of document context for each chunk and prepending it before both embedding and BM25 indexing. In Anthropic's tests it cut top-20 retrieval failures by 49%, and by 67% with reranking. → [§09](09-rag.md)

**Continuous batching**: Rebuilding the batch after every decode step so finished sequences leave and queued ones join immediately (Orca's iteration-level scheduling). Batching, advancing many sequences in one pass over the weights, is the core economic lever of serving; with static batching, short answers wait on the longest one. → [§03](03-inference.md)

**Contrastive learning**: The training method for embedding models: each batch of matching pairs becomes a multiple-choice test where the model must pick a query's true partner over the other passages in the batch (in-batch negatives), using the InfoNCE loss. Hard negatives, passages that look relevant but aren't, sharpen it. "Similar" ends up meaning whatever the training pairs said. → [§08](08-embeddings-and-search.md)

**Coordination tax**: The unavoidable cost in multi-agent systems of compressing global context into inter-agent messages, which eats each agent's token budget and splits reasoning that needed to stay together. It rises with tool count. → [§13](13-multi-agent.md)

**Cosine similarity**: The angle-based similarity between two vectors, `a·b / (|a| |b|)`, ignoring length. If you normalize every vector to length 1 at write time, cosine, dot product and L2 distance give the same ranking. Scores are not probabilities. → [§08](08-embeddings-and-search.md)

**Cost per completed task**: What you actually buy: total spend for a task to finish, including extra turns, retries and human cleanup. A cheaper model that needs more turns isn't cheaper, so compare models on this, not per token (P10). → [§30](30-cost-latency-reliability.md) · [§36](36-product-thinking.md)

**Credential broker**: Harness-side code that holds refresh tokens from a vault, mints short-lived, audience-bound, minimum-scope access tokens per tool call, and returns only data to the model, so credentials never enter context (P6, P9). → [§33](33-agent-identity.md)

**Criteria drift**: The finding that "grading outputs helps users define criteria," so you can't fully write a rubric before seeing outputs. It is the main argument against writing all evals up front. → [§26](26-evals.md)

**Cross-encoder**: A model that reads the query and one document together and outputs a relevance score. It is far more precise than a bi-encoder but can precompute nothing, so it is used only to rerank the top 50–150 candidates. → [§08](08-embeddings-and-search.md)

## D

**DAG (directed acyclic graph)**: The dependency graph of data orchestrators like Airflow and dbt, where structure guarantees termination and each task runs once per run. Agent graphs need cycles, so termination becomes a runtime decision you must enforce. → [§14](14-graph-engineering.md)

**Data contract**: An agreed schema and set of guarantees between a dataset's producer and its consumers, enforced by tests (uniqueness, accepted values, no leakage across splits, a cap on the synthetic share). → [§28](28-data-flywheels.md)

**Data flywheel**: A loop in which usage produces traces, traces become labeled failures and datasets, datasets drive better prompts, retrieval, evals or fine-tunes, and the better product attracts more usage. Each turn should leave something durable, such as an eval case that keeps a bug fixed. → [§28](28-data-flywheels.md)

**Data moat**: The claim that proprietary data makes a product defensible. Honest version: the model is rented and raw logs are cheap, but labeled hard cases, expert rubrics and a representative eval set are expensive to copy and survive a model switch. → [§28](28-data-flywheels.md) · [§36](36-product-thinking.md)

**Decode**: The inference phase that generates one token per sequence per pass. It is memory-bandwidth-bound, which is why output tokens are slower and pricier than input tokens (P10). → [§03](03-inference.md)

**Decoding strategy**: The rule that turns the next-token distribution into a chosen token: greedy (always the top token), temperature (rescaling the logits), top-k (keep the k likeliest tokens) or top-p, also called nucleus sampling (keep the smallest set whose probabilities reach p). Frontier APIs increasingly fix these settings themselves (P4). → [§02](02-how-llms-work.md)

**Deduplication**: Removing repeated examples in three layers: exact (hash a normalized form), near (shingles, the overlapping k-word windows, compared by Jaccard similarity, with MinHash signatures and LSH buckets at scale) and paraphrase (embeddings). In training data duplicates encourage memorization; across splits they leak test answers. → [§28](28-data-flywheels.md)

**Deep-research agent**: An agent that answers a question by running a long plan, search, read and reflect loop, often with parallel subagents, and writes a report with citations. → [§24](24-computer-use-and-research-agents.md) · [§13](13-multi-agent.md)

**Deflection**: The share of support contacts that never reach a human. It counts users who gave up as successes, so pair it with repeat-contact rate, resolution and satisfaction. → [§36](36-product-thinking.md)

**Delegated vs autonomous authority**: A principal is anything that can be authenticated and granted permissions. With delegated authority the agent has its own client identity and acts on a user's behalf, so its rights are the user's permissions intersected with the granted scopes (agent in `client_id`, user in `sub`). With autonomous authority it is its own principal, for work with no user in the loop. Impersonation, presenting the user's own credentials, is the anti-pattern. → [§33](33-agent-identity.md)

**Direct vs indirect injection**: Direct injection is the attacker typing into your app; indirect injection plants instructions in content the agent reads later: web pages, emails, documents, issues, tool results, MCP descriptions, images or memory. Microsoft calls the indirect kind XPIA (cross-prompt injection attack). → [§32](32-security-guardrails.md)

**Distillation**: Training a smaller "student" model on the outputs of a larger "teacher", such as fine-tuning small open models on DeepSeek-R1's reasoning traces. It is one reason closed vendors hide raw reasoning. → [§04](04-reasoning-models.md) · [§29](29-adapting-models.md)

**Doom loop**: An agent stuck repeating the same edits or calls without progress; harnesses break it with loop-detection middleware that counts repeats and nudges the agent to rethink. → [§19](19-harness-engineering.md) · [§11](11-agents.md)

**DPO (Direct Preference Optimization)**: A classification-style loss trained directly on (chosen, rejected) pairs, with no reward model and no RL loop, so it is stable and cheap. → [§02](02-how-llms-work.md) · [§29](29-adapting-models.md)

**Drift**: (1) In agents, wandering into side quests or forgetting the original constraint as context rot buries the goal; fix with a progress file, compaction and subagents. (2) In production monitoring, a shift in input or output distributions over time (§27). → [§11](11-agents.md) · [§27](27-observability.md)

**DSPy**: A framework (2023, "programming, not prompting") where a signature declares a step's inputs and outputs, modules turn signatures into model calls, and optimizers (such as `BootstrapFewShot` and `MIPROv2`, which searches instruction and demonstration combinations) rewrite the prompts to maximize a metric. → [§29](29-adapting-models.md)

**Dual-LLM pattern**: Willison's 2023 design where a privileged LLM with tools sees only trusted input, a quarantined LLM with no tools reads untrusted content, and code passes the quarantined outputs as opaque variables. Its flaw: untrusted content can still choose tool arguments. → [§32](32-security-guardrails.md)

**Durable execution**: Writing each step's result to durable storage and, after a crash, re-running the orchestration code from the top so completed steps return their recorded results and real work resumes at the first unrecorded step. It is at-least-once per step, so side effects need idempotency keys. Orchestration code between steps must be deterministic (no clock reads, random numbers or direct I/O); LLM calls may be random because each is a recorded step. → [§20](20-agent-runtime.md) · [§14](14-graph-engineering.md)

**Durable interrupt**: A human approval treated as a step whose result comes from a person: the runtime saves state and releases compute, nothing runs or bills while it waits, and the run replays and continues when the answer arrives. → [§20](20-agent-runtime.md) · [§14](14-graph-engineering.md)

## E

**Effort**: A soft dial (`low` through `max`) for how readily and deeply the model thinks and how many tool calls it makes. On current Claude models, adaptive thinking (the model decides per request whether and how long to think) is the default, `max_tokens` is the only hard cap, and effort replaces fixed thinking budgets and temperature as the main control. → [§04](04-reasoning-models.md) · [§05](05-api-and-prompting.md)

**Egress allow-list**: A network policy that permits only listed destinations and blocks everything else, usually enforced by a proxy outside the sandbox. Prefer allow-lists to deny-lists, because you can list what a task needs but not everything dangerous. → [§20](20-agent-runtime.md)

**Embedded copilot**: An AI feature inside an existing tool, working on the artifact the user is already looking at ("explain this query"), so context comes free and verification is natural. → [§35](35-ai-ux.md)

**Embedding**: A fixed-length vector that an embedding model (usually a transformer trained to output one vector per input) produces for a piece of text, placed so similar meanings land near each other, which addresses keyword search's vocabulary mismatch ("money back" vs "refund"). Vectors are comparable only within one model version, so changing models means re-embedding, and they capture topic rather than truth. Not to be confused with the *embedding table* inside an LLM. → [§08](08-embeddings-and-search.md)

**Embedding table**: The model's first layer, a learned matrix with one vector per vocabulary entry; it works like a lookup join from token ID to a dense feature vector. Not to be confused with a search *embedding model*, which turns a whole passage into one vector. → [§02](02-how-llms-work.md)

**Enterprise-Managed Authorization (ID-JAG)**: An MCP extension where employees sign in once through the corporate identity provider, which issues an Identity Assertion JWT Authorization Grant per policy; the IdP decides which servers each employee may reach, and offboarding is one revocation. → [§33](33-agent-identity.md)

**Episodic memory**: Long-term records of specific past experiences ("on 2026-09-02 a full backfill timed out; splitting by month worked"), often retrieved as worked examples. Like a fact table of events; git history is one. → [§17](17-memory.md)

**Error amplification**: How much multi-agent setups magnify errors: independent agents amplified them 17.2× in Google's study, while a centralized orchestrator acting as a validation bottleneck held it to 4.4×. → [§13](13-multi-agent.md)

**Error analysis**: Reading real traces before choosing metrics: a domain expert notes the first failure in each (open coding), groups notes into a failure taxonomy and counts them (axial coding), and stops at theoretical saturation, when new traces reveal no new failure modes (about 100+ traces). Each failure category then becomes a code eval, a judge eval, a guardrail or simply a bug fix. → [§26](26-evals.md)

**Error budget (product)**: An acceptable failure rate set per error type before you build, priced by visibility, reversibility, direction and who absorbs it, so you can design failures to land on the cheap side. Borrowed from SRE. → [§36](36-product-thinking.md) · [§30](30-cost-latency-reliability.md)

**EU AI Act**: Regulation (EU) 2024/1689, which regulates the process around AI rather than certifying the artifact: duties attach to a use case's intended purpose and risk tier and to your role, and reach any output used in the EU. Duties switch on in stages through 2028. This compendium's coverage is not legal advice. → [§34](34-governance-regulation.md)

**Eval**: A measurement of whether an LLM feature works: a dataset of tasks, graders and repeated trials, whose result is a rate with an interval rather than a pass/fail (P4). It plays the role unit tests and dbt tests play for deterministic code. → [§26](26-evals.md)

**Eval harness**: The code that runs eval tasks, grades them and aggregates scores. Not to be confused with the *agent harness* (§19); evaluating "an agent" means evaluating the model and its agent harness together. → [§26](26-evals.md)

**Eval-driven development (EDDOps)**: Writing evals before building, as in test-driven development; EDDOps frames evaluation as a continuous, governing function. Contested: write evals first for what you can specify exactly, and grow the rest from error analysis. → [§26](26-evals.md)

**Evaluator-optimizer**: A loop where a generator drafts and a separate evaluator grades the draft against explicit criteria and returns feedback, until it passes or a cap is hit. Only the critique flows back to the generator (P8). Watch for the early victory problem: an evaluator that runs one or two checks, sees them pass and declares success. → [§12](12-agentic-design-patterns.md)

**Event-driven orchestration**: An orchestration style where steps subscribe to events, so the topology emerges from who listens to what, like Kafka consumers. You gain decoupling and lose visibility. → [§14](14-graph-engineering.md)

**Evol-Instruct**: A 2023 method (WizardLM) where an LLM rewrites seed instructions to be harder ("in-depth") or different ("in-breadth"), and an eliminator drops failed rewrites, producing a spread of difficulty. → [§28](28-data-flywheels.md)

**Exact-match edit (str_replace)**: An edit format where the model quotes the exact text it replaces (Claude's `str_replace`, Aider's search/replace blocks), and the edit is refused if the text is missing or matches more than once. Stale or ambiguous context fails loudly instead of corrupting the file. OpenAI's equivalent is the `apply_patch` tool with V4A diffs; models overfit to their native edit format. → [§23](23-coding-agents.md)

**Explicit vs implicit feedback**: Explicit feedback is direct (thumbs, ratings, corrections) but sparse and self-selected; implicit feedback is inferred from behavior (retries, rephrasing, abandonment, accepted suggestions) and plentiful but ambiguous. Use both to pick traces for review, not as a metric to optimize. → [§27](27-observability.md) · [§28](28-data-flywheels.md)

**Exponential backoff with full jitter**: Doubling the wait after each failure and randomizing it (a uniform wait up to the cap), so clients that failed together don't retry together. AWS measured full jitter cutting total calls by more than half under contention. → [§30](30-cost-latency-reliability.md)

## F

**Faithfulness (groundedness)**: The share of claims in a response that the retrieved context supports. Faithful is not the same as correct: a perfectly grounded answer from a stale document is still wrong. → [§09](09-rag.md)

**Fallback chain**: An ordered list of models or providers to try when the primary fails: a different model for per-model 429s, a different provider for outages, a different model for refusals. A fallback is only as good as its eval results, and you should log which model served each request. → [§30](30-cost-latency-reliability.md)

**Feature list**: In Anthropic's long-running harness, a JSON file of end-to-end features, each marked passing or failing, that an initializer agent writes once (with an `init.sh`, a progress file and a first commit) and later coding sessions work through one at a time. JSON was chosen because models are less likely to overwrite it inappropriately than Markdown. → [§19](19-harness-engineering.md) · [§16](16-context-engineering.md)

**Few-shot prompting**: Putting worked input→output examples in the prompt so the model learns the task in context. Models copy everything about the examples (length, phrasing, label balance), so keep them diverse and tagged. → [§05](05-api-and-prompting.md)

**Filler speech**: A short acknowledgment ("Let me pull up your order") spoken while a tool call runs, so latency doesn't become dead air. Keep it non-committal; it must not claim a result the tool hasn't produced. → [§25](25-voice-agents.md)

**Fine-tuning**: Continuing to train a model's weights on your own data to change its behavior (format, style, a narrow skill). It won't reliably add facts, is tied to a base model that will be retired, and can erode safety and general skills. Ground for facts, fine-tune for behavior (P5, P12). → [§29](29-adapting-models.md)

**Five forces**: The five ways a foundation model differs from ordinary components, which every technique in the compendium answers: knowledge (it doesn't know your world), uncertainty (it is probabilistic), agency (it can only talk), scarcity (it is expensive and finite) and change (it keeps changing). → [§01](01-first-principles.md)

**Five-step method**: The compendium's way to choose between options: name the force, name the mechanism or principle, count the cost per successful task (P3, P10), ask how you will verify it (P4, P8), and ask what happens when models improve (P12). → [§37](37-why-x-over-y.md) · [§01](01-first-principles.md)

**Flow engineering**: A Jan 2024 label (from the AlphaCodium paper) for replacing one big prompt with a multi-stage, test-driven flow of generate, test, reflect and iterate. Rarely used now; its ideas live on in evaluator-optimizer patterns, back pressure and explicit graphs. → [§38](38-disciplines-map.md)

**Forward-deployed engineer**: An engineer embedded with a customer to build the last mile (data connections, tools, prompts tuned on real inputs, evals), the role that crosses the pilot-to-production gap. A role, not a technique. → [§36](36-product-thinking.md) · [§38](38-disciplines-map.md)

**FP8**: 8-bit floating-point quantization of weights and often activations, which uses the FP8 math units on H100-class GPUs; one large study found it effectively lossless. → [§31](31-open-weights-self-hosting.md) · [§03](03-inference.md)

**Full duplex**: A voice model that can listen and speak at the same time. The 2026 hybrid pairs a full-duplex front model that handles the conversation with a delegated backend (any model or agent harness) that does reasoning and tool calls. → [§25](25-voice-agents.md)

## G

**Gate**: A programmatic check between workflow steps (a schema validation, a count, a regex, a cheap classifier) that retries or stops on failure, so an error is caught at the step that made it (P8). Like a dbt test between models. → [§12](12-agentic-design-patterns.md)

**Generative UI**: The model emitting a description of interface components (card, table, form, chart) that the app renders, at three levels: tool-bound components, declarative catalogs, and sandboxed HTML apps. Model-emitted UI is untrusted output, so validate it before rendering (P6, P9). → [§35](35-ai-ux.md)

**GEPA**: A reflective prompt optimizer (2025, shipped as `dspy.GEPA`) where a model reads whole trajectories, diagnoses failures and proposes edits, keeping a Pareto frontier of candidates that are each best on at least one example. Its authors report beating GRPO and MIPROv2 on their benchmarks. → [§29](29-adapting-models.md)

**GGUF**: A single-file container format for llama.cpp with metadata and memory-mappable tensors, carrying its own quantization types such as `Q4_K_M` or `Q8_0`. It is a format, not a single quantization method. → [§31](31-open-weights-self-hosting.md)

**Git worktree**: A git feature that gives each parallel agent or loop its own working directory and branch over one shared history, so edits can't collide on disk; semantic conflicts can still happen at merge. → [§21](21-loop-engineering.md) · [§23](23-coding-agents.md)

**Golden set**: A curated, versioned collection of eval tasks with reference answers or criteria, versioned with its graders. 20–50 tasks drawn from real failures is a good start; keep it unambiguous, balanced and out of anything you tune. → [§26](26-evals.md)

**Goodhart's law**: When a measure becomes a target, it stops being a good measure. Generators learn a rubric's quirks, and optimized prompts or fine-tunes overfit graders. → [§12](12-agentic-design-patterns.md) · [§28](28-data-flywheels.md)

**GPAI Code of Practice**: The EU's voluntary route (Jul 2025) for GPAI providers to show compliance, with chapters on transparency, copyright, and safety and security; signatories include Anthropic, Google, Microsoft, OpenAI and others. → [§34](34-governance-regulation.md)

**GPAI model (general-purpose AI model)**: A model that can competently perform a wide range of tasks (indicatively, over 10²³ training FLOP). Its provider owes documentation, a copyright policy and a training-content summary since Aug 2025; above 10²⁵ FLOP it is presumed to carry systemic risk, adding adversarial testing and incident reporting. Calling a model through an API usually doesn't make you a GPAI provider. → [§34](34-governance-regulation.md)

**GPTQ and AWQ**: Two methods for quantizing weights to 4 bits. GPTQ rounds layer by layer to minimize each layer's output error on a calibration set; AWQ protects the most important ~1% of weight channels, found from activation statistics. Both are mostly weight-only (W4A16: 4-bit weights, 16-bit activations), suited to latency-bound serving, while W8A8 suits high-throughput batching. → [§31](31-open-weights-self-hosting.md)

**Graceful degradation**: Deciding in advance what users get when the model path fails: fallback model, then a cached or precomputed answer, then a non-AI path, a queue, or an honest "try again." → [§30](30-cost-latency-reliability.md)

**Grader**: The component that scores one aspect of a trial: code (match, regex, schema, tests, end-state checks), an LLM judge, or a human. Use deterministic graders where possible, LLM graders where necessary, and humans to validate. In fine-tuning, the grader also scores outputs as the reward (§29). → [§26](26-evals.md) · [§29](29-adapting-models.md)

**Grammar**: A precise rule set for which strings are legal, which constrained decoding compiles your schema into. Flat patterns such as an enum compile to a finite-state machine (FSM); nested JSON needs a context-free grammar (CFG), which adds a stack to track open brackets. → [§06](06-structured-outputs.md)

**Graph engineering**: A July 2026 label for an established (2024) practice: modeling agent systems as state machines with typed state, nodes, and fixed or conditional edges, so code owns the transitions you know and the model owns the ones you don't (P7). Not to be confused with *GraphRAG*, where the graph is data rather than control flow. → [§14](14-graph-engineering.md) · [§38](38-disciplines-map.md)

**GraphRAG**: Microsoft's retrieval method (2024) for whole-corpus "global sensemaking" questions: an LLM extracts entities and relationships into a knowledge graph, Leiden clustering groups them into communities, and an LLM writes a community report for each. Global search map-reduces over the reports; local search fans out from entities named in the question. Indexing is expensive. Not to be confused with *graph engineering*, where the graph is an agent's control flow rather than its data. → [§09](09-rag.md)

**Grounding**: Giving the model the relevant facts as tokens in its context (via retrieval or tools) so it copies and cites them instead of guessing from its weights (P5). → [§09](09-rag.md)

**Group-based split**: Splitting train, dev and test sets by account, conversation or time rather than by row, because near-identical records from one customer would otherwise land on both sides and the test would measure memory. → [§28](28-data-flywheels.md)

**GRPO (Group Relative Policy Optimization)**: A variant of PPO, the standard RLHF algorithm, that drops PPO's separate value model and uses the mean reward of a group of sampled answers to the same prompt as the baseline, saving a second large model. DeepSeek-R1 used it. → [§04](04-reasoning-models.md)

**Guardrail**: A check outside the main model call, on inputs, outputs or tool calls, that can block, redact or reroute: input classifiers, output classifiers, PII detection and deterministic policy checks. In the OpenAI Agents SDK a failed check raises a tripwire that halts the run. Guardrails lower the rate of bad events; architecture bounds the damage. Not to be confused with an *online eval*, which runs afterwards and measures rather than blocks. → [§32](32-security-guardrails.md) · [§27](27-observability.md)

**GUI grounding**: Mapping a description such as "the blue Submit button" to an exact screen location; training models to count pixels accurately was the hard part of computer use. → [§24](24-computer-use-and-research-agents.md)

**Guides and sensors**: Böckeler's split of harness controls: guides are feedforward (steer before the agent acts: `AGENTS.md`, skills, specs) and sensors are feedback (observe after it acts: tests, linters, reviewers). You need both, and the human's job (the steering loop) is to improve them whenever an issue repeats. → [§19](19-harness-engineering.md)

**gVisor and microVMs**: Two sandbox boundaries stronger than a plain container. gVisor is a user-space "application kernel" that intercepts a container's system calls (OCI runtime `runsc`); a microVM such as Firecracker boots a minimal VM with its own guest kernel, the strongest common boundary. → [§20](20-agent-runtime.md)

## H

**Hallucinated citation**: A plausible URL or title the model never retrieved, emitted because it knows from its weights what citations look like (P1, P5). Accept citations only to documents the harness fetched, and check quoted spans in code. → [§24](24-computer-use-and-research-agents.md)

**Hallucination**: Fluent, confident output that is false or unsupported. It follows from the mechanism (no "unknown" state, lossy weights, benchmarks that reward guessing), and the fixes live outside the model: grounding, abstention, verification and evals (P1, P5). → [§02](02-how-llms-work.md)

**Handoff**: Transferring control from one agent to a specialist, who becomes the active agent, sees the previous history by default and answers the user directly. Fits triage; fails through misroutes and history bloat. → [§13](13-multi-agent.md)

**Harness**: Every piece of code, configuration and execution logic around a model that isn't the model itself: prompts, tools, infrastructure, orchestration and hooks ("Agent = Model + Harness"). Every agent has one, even a bare `while` loop; all its real capability and risk live there (P6). The outer harness is what you build around a product's built-in one for your codebase: `AGENTS.md`, skills, hooks, custom linters. Not to be confused with a *framework* (LangGraph, an agent SDK), which is a library of primitives you can build a harness on. → [§19](19-harness-engineering.md) · [§37](37-why-x-over-y.md)

**Harness engineering**: The discipline (the label caught on in Feb 2026) of assembling the loop, tools, context management, memory and skills into one system and continuously tuning it against observed failures. With the model fixed, harness changes alone moved one agent from 52.8% to 66.5% on Terminal Bench 2.0. It is mostly context engineering in practice, plus control over allowed actions and verification. → [§19](19-harness-engineering.md) · [§38](38-disciplines-map.md)

**Harnessability**: How easy a codebase is to build a harness for: strong typing gives a free sensor, clear module boundaries allow architecture rules, and legacy code is the hard case. → [§19](19-harness-engineering.md) · [§23](23-coding-agents.md)

**Hash chain**: Linking records so each includes a hash of the one before, making any later edit detectable; used to make audit logs tamper-evident. (§03 describes the same structure in vLLM's prefix cache, where it is why one changed early token invalidates every later block.) → [§34](34-governance-regulation.md) · [§03](03-inference.md)

**Head vs tail sampling**: Head sampling decides at the start of a trace whether to keep it (cheap, but blind to errors); tail sampling decides after the trace completes, usually in the Collector, so it can keep every error, slow or flagged trace. Agent failures are rare, so tail sampling usually fits better. → [§27](27-observability.md)

**High-risk system**: An EU AI Act category reached through Annex I (a safety component of a regulated product) or Annex III (standalone uses such as employment, credit scoring or education), carrying duties for risk management, logging, documentation, human oversight and accuracy. The Art. 6(3) exemption covers systems that don't materially influence decisions, never profiling. As of Oct 2026, after the 2026 AI Omnibus amendment, the rules apply from Dec 2, 2027 (Annex III) and Aug 2, 2028 (Annex I). → [§34](34-governance-regulation.md)

**HNSW (Hierarchical Navigable Small World)**: The default ANN index: a layered proximity graph, like a skip list, where search enters at a sparse top layer and hops greedily toward the query. Best general recall/speed tradeoff, but memory-hungry and slow to build. → [§08](08-embeddings-and-search.md)

**Hooks (middleware)**: Functions the harness runs at fixed points in the loop (before a tool call, after it, when the agent tries to stop, before compaction). They hold computational sensors and hard guardrails because they run every time, whatever the model decides (P6). A stop-time hook that sends the agent back to work is a continuation hook. → [§19](19-harness-engineering.md)

**Hosted open-weight API**: A provider serving an open model per token (cloud platforms or inference APIs), giving cheap tokens with no ops and an exit to self-hosting later. Two providers of "the same model" may run different precisions, context limits and chat templates. A dedicated endpoint, where a provider runs your checkpoint on reserved GPUs, sits between this and self-hosting. → [§31](31-open-weights-self-hosting.md)

**Hot-path memory write**: The agent saving a memory during the conversation, usually through a memory tool, so it is usable immediately and visible to the user, at the cost of latency and attention. Contrast with *background consolidation*. → [§17](17-memory.md)

**Hybrid search**: Running lexical (BM25) and dense vector retrieval together and merging the results, which covers both failure modes. It is the production default, usually followed by a reranker. → [§08](08-embeddings-and-search.md) · [§09](09-rag.md)

## I

**Idempotency (idempotency key)**: The property that doing an operation twice has the same effect as doing it once, usually achieved by sending an idempotency key with each external write. Agents, graph resumes, durable replays and API retries all may repeat a step, so side-effecting tools need it. → [§20](20-agent-runtime.md) · [§30](30-cost-latency-reliability.md)

**In-context learning**: A model's ability to do a task described or demonstrated in the prompt with no weight updates, first shown at scale by GPT-3. It is why prompting works. → [§02](02-how-llms-work.md) · [§05](05-api-and-prompting.md)

**Inner loop vs outer loop**: The inner loop is the agent's own edit-check-fix cycle within a task, judged by back pressure; the outer loop is the human's: setting goals and specs, designing checks, reviewing merges and fixing the system when a failure pattern appears. → [§21](21-loop-engineering.md)

**Instruction hierarchy**: Training a model to rank system instructions over user messages over tool output. Like spotlighting, it lowers a rate that adaptive attacks are built to beat. → [§32](32-security-guardrails.md)

**Inter-annotator agreement**: How often two humans give the same verdict on the same output; low agreement means the task itself is poorly defined. Cohen's kappa is a common measure. → [§26](26-evals.md) · [§28](28-data-flywheels.md)

**Interrupt (human-in-the-loop)**: Pausing a graph inside a node: state is saved, a payload goes to the caller, and nothing blocks. The run resumes days later with the human's answer on the same thread, and the paused node restarts from its top. → [§14](14-graph-engineering.md) · [§35](35-ai-ux.md)

**is_error**: The `tool_result` flag that tells the model a tool call failed. Pair it with an instructive message that says how to fix the problem, because the model is the only component that can change the plan. Not to be confused with API errors (429, 5xx), which the model never sees and your code retries. → [§10](10-tool-use.md)

**ISO/IEC 42001**: A certifiable AI management system standard (2023) with the same shape as ISO 27001: policy, roles, risk and impact assessments, controls, internal audit and continual improvement. It proves you run the process, but alone doesn't create EU AI Act conformity. → [§34](34-governance-regulation.md)

## J

**Jagged frontier**: The uneven boundary of model competence found in a BCG experiment: consultants using GPT-4 did better on tasks inside it but were less often correct than those without AI on a task outside it. Train users on where the tool can be trusted. → [§36](36-product-thinking.md)

**Jailbreak**: The *user* trying to make the model break its *provider's* safety policy, fought with model training and safety classifiers. Not to be confused with *prompt injection*, where a third party attacks your user through content your agent reads, which your architecture must defend. → [§32](32-security-guardrails.md)

**Journal (step log)**: An append-only record of every step's result from which a durable engine rebuilds state by replay (Temporal, Restate, Inngest, DBOS), like a change log. Not to be confused with a *checkpoint*, which snapshots the whole state. → [§20](20-agent-runtime.md)

**JSON mode**: An older API option (Nov 2023) that constrains decoding to *some* valid JSON but not your schema; keys, types and enums are unchecked, and it can loop on whitespace. Treat it as legacy. Not to be confused with *structured outputs*. → [§06](06-structured-outputs.md)

**Judge biases**: Systematic errors of LLM judges: position bias (favoring one slot in a pairwise comparison), verbosity bias (favoring longer answers) and self-enhancement bias (favoring outputs like its own). Swap orders and count only wins that hold both ways. → [§26](26-evals.md)

**Just-in-time retrieval (agentic search)**: Keeping lightweight identifiers (file paths, queries, links) in context and loading data with tools such as `glob` and `grep` at the moment of need, instead of querying a pre-built index. Nothing goes stale, but it costs more tool calls and can wander. It is the default for coding agents. → [§16](16-context-engineering.md) · [§23](23-coding-agents.md)

## K

**Kill switch**: A way to stop a compromised agent fast: interrupting a session, a disable flag checked each turn, revoking credentials at the identity provider, blocking egress, or de-listing a server or skill. → [§32](32-security-guardrails.md)

**Knowledge cutoff**: The date after which the weights know nothing (P5). Anthropic publishes a reliable knowledge cutoff and a broader training data cutoff. Models don't know today's date unless the context says so. → [§02](02-how-llms-work.md)

**KV cache**: The server-side store of earlier tokens' keys and values, kept so each decode step doesn't recompute the whole prefix. It trades GPU memory for compute, and its size often caps how many requests a GPU can serve. Not to be confused with *prompt caching*, which reuses a prefix's KV cache across requests. → [§03](03-inference.md)

## L

**Lethal trifecta**: Simon Willison's name for the dangerous combination of private data, untrusted content, and a way to communicate externally in one agent. One malicious input can then trigger exfiltration, so remove a leg (P9). → [§10](10-tool-use.md) · [§32](32-security-guardrails.md)

**Levels of autonomy**: Ways to grade how much an agent controls: by how much the LLM's output controls the program (router, tool call, multi-step, multi-agent), or by the user's role (operator, collaborator, consultant, approver, observer). Autonomy is a design decision separate from capability (P7). → [§11](11-agents.md)

**Lineage (dataset)**: Each example keeping its source trace ID and the model and prompt version that produced it, so you can debug, audit contamination and honor deletion requests across datasets and the models trained on them. Freeze datasets as named versions and log the version with every run. → [§28](28-data-flywheels.md) · [§27](27-observability.md)

**LLM-as-judge**: A second model call that reads the input, the output and a rubric and returns a verdict, as a rubric score, an assertion, a pairwise comparison (which of two is better?) or a comparison to a reference. It is sampled and biased, so treat it as a classifier: measure its true positive rate (failures caught) and true negative rate (good outputs passed) against held-out human labels before trusting it. → [§26](26-evals.md)

**Logit**: The raw score the model produces for every vocabulary entry after the final layer (via the unembedding matrix); softmax turns logits into next-token probabilities. → [§02](02-how-llms-work.md) · [§06](06-structured-outputs.md)

**Loop engineering**: Designing the system that prompts the agent instead of prompting it yourself: when to run, what to feed it, how to check it and when to stop, "one floor above the harness." The label (Osmani, Jun 2026) is emerging; the practice is older. → [§21](21-loop-engineering.md) · [§38](38-disciplines-map.md)

**LoRA (low-rank adaptation)**: Fine-tuning by freezing each weight matrix and training a low-rank update B·A of rank r (typically 8–64), which cuts trainable parameters from d_in × d_out to r × (d_in + d_out); full fine-tuning instead needs about 16 bytes per parameter, roughly 128 GB for an 8B model. Small adapters can be merged into the weights or swapped per request on one base model (multi-LoRA serving). Applied to all layers, LoRA matches full fine-tuning at typical dataset sizes and forgets less. → [§29](29-adapting-models.md) · [§31](31-open-weights-self-hosting.md)

**Lost in the middle**: The finding (Liu et al., 2023) that models use information at the start or end of a long context more reliably than information in the middle. Send fewer, better-ranked chunks and put the strongest at the edges (P3). → [§09](09-rag.md) · [§02](02-how-llms-work.md)

## M

**Maker ≠ checker (generator/evaluator separation)**: Separating the agent that does the work from the one that judges it, with its own prompt, rubric, fresh context and ideally its own evidence (running the tests itself), because agents reliably grade their own work too generously. A skeptical standalone evaluator is easier to tune than a self-critical generator (P8). → [§21](21-loop-engineering.md) · [§12](12-agentic-design-patterns.md)

**Markdown image exfiltration**: An injected model writing an image link whose URL carries a secret; when the client renders it, the browser's fetch sends the secret to the attacker with no tool call at all. Render images and links only from allow-listed domains. → [§32](32-security-guardrails.md)

**MCP (Model Context Protocol)**: Anthropic's open protocol (Nov 2024, now under the AAIF) for connecting AI applications to tools and data through a standard client–server interface over JSON-RPC 2.0 (requests with an id, method and params; responses; notifications), turning N×M integrations into N+M (P11). It standardizes discovery and invocation, not tool quality, and every connected tool costs context (P3). Not to be confused with *A2A*, which connects agents to agents, or with a *skill*, which packages know-how rather than access. → [§15](15-protocols-mcp-a2a.md)

**MCP Apps**: An official MCP extension (Jan 2026) where a tool declares a UI resource that the host renders as HTML in a sandboxed iframe. The UI asks the host to make tool calls for it, so its actions pass the same consent path. → [§15](15-protocols-mcp-a2a.md) · [§35](35-ai-ux.md)

**MCP extensions**: Opt-in, independently versioned additions to MCP, negotiated through capabilities. The official ones include Tasks (long-running work behind a handle the client polls, updates or cancels), MCP Apps and Skills over MCP. → [§15](15-protocols-mcp-a2a.md)

**MCP host, client and server**: The host is the AI application that owns the model, the conversation and user consent; it holds one MCP client (connector) per server; a server is a program exposing capabilities, local if launched as a subprocess and remote if reached over HTTP. → [§15](15-protocols-mcp-a2a.md)

**MCP primitives**: The three capabilities a server offers, split by who controls them: tools (model-controlled functions), resources (application-driven read-only context addressed by URI), and prompts (user-controlled templates such as slash commands). → [§15](15-protocols-mcp-a2a.md)

**MemGPT (virtual context management)**: A 2023 design that treats the context window like RAM: the model pages data with function calls between main context and external archival storage (searchable text) and recall storage (every message). Before evicting messages it warns the model of "memory pressure" so it can save what matters. Its company, Letta, adds pinned memory blocks and git-backed memory files. → [§17](17-memory.md)

**Memory (agent memory)**: The write path, store and read path that save information from past sessions and put a relevant slice back into a later context; the model itself learns nothing (P2). "Memory engineering" is a 2026 label for this subset of context engineering. Not to be confused with *RAG*, which retrieves from a curated corpus someone else wrote; memory holds the agent's own history: preferences, project state and lessons. → [§17](17-memory.md)

**Memory poisoning**: Untrusted content written into long-term memory so that any injected instruction is replayed into every future session: persistent prompt injection (OWASP ASI06). Defend with provenance, reviewed writes, read-only shared memory and versions (P9). Not to be confused with *context poisoning*, a within-session error. → [§17](17-memory.md) · [§32](32-security-guardrails.md)

**Memory tool**: Anthropic's client-side tool (`memory_20250818`) whose schema Anthropic supplies: Claude issues file commands (`view`, `create`, `str_replace` and others) under a virtual `/memories` path and your code executes them on storage you own. Your handler owns path checks, size caps and access control (P6). → [§17](17-memory.md)

**Mixture-of-experts (MoE)**: An architecture where each token runs through only a few "expert" sub-networks. Memory scales with total parameters, because every expert must be loaded, while per-token compute scales with active parameters (gpt-oss-120b: 117B total, 5.1B active). → [§31](31-open-weights-self-hosting.md)

**Model card and system card**: A model card documents a model's intended use, evaluation across groups and limitations (a datasheet does the same for a dataset); a system card covers a deployed model plus its safeguards and red-teaming. Write a system card per use case, and generate as much as you can from config and eval output so it doesn't drift. → [§34](34-governance-regulation.md)

**Model cascade**: Trying a small model first and escalating to a larger one when a confidence check fails; cost ≈ small + P(escalate) × large. The confidence signal should be external (schema validation, tests), not the model's own claim (P8). Not to be confused with a voice *cascade* (STT → LLM → TTS). → [§30](30-cost-latency-reliability.md)

**Model collapse**: Irreversible loss of the tails of the original distribution when models are trained on the previous generation's output, replacing real data each time. Accumulating synthetic data alongside real data avoided it, so keep real data as the anchor and tag provenance. → [§28](28-data-flywheels.md)

**Model–harness co-training**: Post-training models with their vendor's harness in the loop (Claude Code, Codex), so the model improves inside that harness and can overfit to it. A benchmark score therefore describes a model–harness pair, never the model alone (P12). → [§19](19-harness-engineering.md)

**MRR and nDCG**: Ranking metrics. MRR (mean reciprocal rank) averages 1 / rank of the first relevant result, for when one right answer is enough; nDCG (normalized discounted cumulative gain) rewards putting the best results first using graded labels, for judging the final order after reranking. → [§08](08-embeddings-and-search.md)

**Multi-agent system**: Several LLM instances, each with its own context (system prompt, history, tools), coordinated by code or by another LLM. It pays through parallelism, context isolation and specialization, at about 15× the tokens of chat (P3, P10). Default to one agent. → [§13](13-multi-agent.md)

## N

**Native PDF support**: An API feature that rasterizes each PDF page to an image and also extracts its text, giving the model both. It needs the least code and handles charts best, but you pay on every query and nothing becomes searchable. Contrast with a parse-once pipeline. → [§07](07-multimodal.md)

**NIST AI RMF**: The US National Institute of Standards and Technology's voluntary AI Risk Management Framework (2023), organized as Govern, Map, Measure and Manage; its Generative AI Profile lists twelve risks. → [§34](34-governance-regulation.md)

**Nodes and edges (graph)**: The parts of an agent graph besides its shared state. A node is a function from state to a partial update (code, one LLM call, a tool or a whole agent), so autonomy is set node by node. A fixed edge always goes from A to B; a conditional edge runs a routing function on the state to pick the next node, which is how agent graphs close cycles. → [§14](14-graph-engineering.md)

**N×M integration problem**: Without a shared protocol, N applications each need custom code for M tools, giving N×M integrations; a standard interface reduces this to N+M (P11). → [§01](01-first-principles.md) · [§15](15-protocols-mcp-a2a.md)

## O

**OAuth 2.1**: The (still-draft) consolidation of OAuth 2.0 practice for delegated authorization: PKCE required, implicit and password grants removed, exact redirect matching, no bearer tokens in query strings. MCP's HTTP authorization builds on it. → [§33](33-agent-identity.md) · [§15](15-protocols-mcp-a2a.md)

**Observability (LLM)**: Capturing what actually happened in each production request (content, tokens, cost, latency, tool calls) because an LLM failure is usually an HTTP 200 with a wrong answer, and a stateless, sampled model can't be reproduced later (P2, P4). → [§27](27-observability.md)

**Observation**: The tool result fed back to the model after an action, its only view of the world (P2). Lead with the signal, bound the size, show the effect of actions, and clear stale ones (P3). → [§11](11-agents.md)

**OCR (optical character recognition)**: Converting pixels to characters, needed for scans with no text layer. A parsing pipeline pairs it with layout analysis (regions and reading order) and table-structure recognition to turn documents into structured text once, ahead of time. → [§07](07-multimodal.md)

**Offline vs online eval**: Offline evals run a fixed dataset before deployment (reproducible but limited to inputs you thought of); online evals run reference-free graders on sampled production traffic. A failure found online becomes an offline test case. → [§26](26-evals.md) · [§27](27-observability.md)

**Open weights**: A model whose trained parameters you can download, run and fine-tune (usually with a config, tokenizer, chat template, model card and license), but typically without the training data or full training code, so you can't rebuild it. Not to be confused with *open source*, which under the OSI definition also requires data information and complete code. Read each checkpoint's license. → [§31](31-open-weights-self-hosting.md)

**OpenAI-compatible API**: The Chat Completions request shape that most serving engines, gateways and providers accept, making models swappable by changing a base URL (P11); the Anthropic Messages shape is a second common envelope. Compatible envelopes don't mean identical behavior, so re-run your evals. → [§31](31-open-weights-self-hosting.md)

**OpenID Connect (OIDC)**: The identity layer on top of OAuth, adding a signed ID token that states who the user is; enterprise flows reuse it as an identity assertion. → [§33](33-agent-identity.md)

**OpenTelemetry (OTel)**: The open standard for telemetry: SDKs that create traces, metrics and logs, a wire protocol (OTLP), and the Collector, a service that receives, processes and forwards telemetry. → [§27](27-observability.md)

**Orchestration tax**: The real but invisible human work of briefing agents, switching between their threads, answering their questions and merging their branches. Not to be confused with the *coordination tax* inside multi-agent systems. → [§23](23-coding-agents.md)

**Orchestrator-workers**: A pattern where a central LLM decides at runtime which subtasks an input needs, delegates them to workers and synthesizes the results. Unlike sectioning, the subtasks aren't defined in advance, so control flow moves to the model (P7). → [§12](12-agentic-design-patterns.md) · [§13](13-multi-agent.md)

**OTel GenAI semantic conventions**: OpenTelemetry's agreed names for LLM spans, attributes, events and metrics (for example `chat claude-sonnet-5-5` spans and `gen_ai.usage.input_tokens`), turning N×M instrumentation mappings into N+M (P11). As of Oct 2026 they are still in Development status, so pin a version and expect renames. Arize's OpenInference is a parallel, complementary convention. → [§27](27-observability.md)

**Out-of-band verification**: Checking an agent's end state through a separate channel (querying the system of record, a separate checker, a human) instead of trusting the acting model's own reading of a screenshot (P8). → [§24](24-computer-use-and-research-agents.md)

**Outcome-based pricing**: Charging per successful result (a resolution, an accepted change) rather than per seat or per token. It aligns price with value but works only when success is clearly measurable, and you absorb failed attempts. → [§36](36-product-thinking.md)

**OWASP Top 10 for Agentic Applications**: The OWASP GenAI Security Project's Dec 2025 list of agent risks, from ASI01 Agent Goal Hijack through ASI06 Memory & Context Poisoning to ASI10 Rogue Agents, alongside the separate Top 10 for LLM Applications. → [§32](32-security-guardrails.md)

## P

**Parallelization**: Running LLM calls at the same time, either as *sectioning* (independent subtasks known in advance, merged in code) or *voting* (the same task run N times and aggregated). Voting assumes independent errors, so vary prompts or models. → [§12](12-agentic-design-patterns.md)

**Parametric vs supplied knowledge**: Parametric knowledge is what pretraining compressed into the weights: broad, lossy, frozen at a cutoff, impossible to cite and expensive to change. Supplied knowledge is whatever you put in the context at runtime (retrieved passages, tool results, memory): fresh, private, citable and permission-controlled. The rule of thumb is *ground for facts, fine-tune for behavior* (P5). → [§01](01-first-principles.md) · [§09](09-rag.md)

**pass@k**: The probability that at least one of k trials succeeds. It fits products where a verifier picks a winner, such as patches filtered by tests. Not to be confused with *pass^k*: the same trials can give pass@8 = 100% and pass^8 = 25%. → [§26](26-evals.md)

**pass^k ("pass hat k")**: The probability that *all* k trials succeed, from τ-bench. It measures consistency, which customer-facing agents need because each user gets one attempt. Not to be confused with *pass@k*. → [§26](26-evals.md)

**Payback period**: One-off adaptation cost divided by the monthly saving against the best cheap alternative (not the naive baseline). A fine-tune is worth it only if payback is well inside the base model's remaining life. → [§29](29-adapting-models.md)

**Permission mode**: A setting that decides which agent actions need a human first, from plan-only and ask-on-first-use through auto-review to bypass (only in isolated environments). Rules are enforced by the harness, not the model. → [§20](20-agent-runtime.md)

**pgvector**: A Postgres extension that adds a `vector` type, distance operators and HNSW/IVFFlat indexes, so you keep transactions, joins and existing access control. With approximate indexes it applies `WHERE` filters after the index scan, which can silently return too few rows. → [§08](08-embeddings-and-search.md)

**PII (personally identifiable information)**: Names, emails, phone numbers, addresses and account numbers. Redact it at ingestion, before any labeler, vendor, trace viewer or training job sees it, and pseudonymize user IDs so deletion still works. → [§28](28-data-flywheels.md) · [§27](27-observability.md)

**Pilot-to-production gap**: The distance between a demo (hand-picked inputs, one run, an expert fixing errors) and production (the long tail, volume, no expert). It closes through evals on sampled production inputs, error analysis and feedback loops, not better demos. → [§36](36-product-thinking.md)

**PKCE (Proof Key for Code Exchange)**: An OAuth safeguard where the client sends only a hash of a secret verifier with the authorization request and presents the verifier when redeeming the code, so an intercepted code is useless. Required by OAuth 2.1 and MCP (S256 method). → [§33](33-agent-identity.md)

**Plan-and-execute**: A planner LLM writes the steps once, cheaper executors run them, and a replanning step fires only if the plan fails. The big model is called once, but a plan written before any observation can be wrong. → [§12](12-agentic-design-patterns.md)

**Planner–generator–evaluator harness**: Anthropic's 2026 three-agent harness for long builds: a planner writes a product spec, a generator builds one feature at a time, and a separate evaluator drives the running app and grades it against hard thresholds. Each component encodes an assumption about what the model can't do alone (P12). → [§12](12-agentic-design-patterns.md) · [§19](19-harness-engineering.md)

**Policy gate**: Code in the harness between the model's tool request and its execution that allow-lists tools by risk class, asks a human before destructive actions, and blocks external egress after untrusted input. Because it is code, the model can't talk its way past it (P6). → [§32](32-security-guardrails.md)

**Post-training**: The training stages after pretraining (SFT, RLHF, DPO, RLAIF, RL with verifiable rewards) that use little compute but decide most visible behavior: format, tone, refusals and tool-call syntax. → [§02](02-how-llms-work.md)

**Preference pair**: A prompt with a chosen (better) and a rejected (worse) response, the training unit for DPO. A user's edit next to the model's draft is the cheapest source; watch for confounds like chosen answers always being longer. → [§28](28-data-flywheels.md) · [§29](29-adapting-models.md)

**Prefill**: The inference phase that processes the whole prompt in one parallel pass and builds the KV cache. It is compute-bound and drives time to first token. Not to be confused with *assistant prefill*, an old API technique of writing the start of the model's reply. → [§03](03-inference.md)

**Prefill (assistant prefill)**: The old technique of ending the messages with a partial assistant turn so the model continues from your text, used to force JSON or skip preambles. Claude 4.6 and later reject it with a 400; structured outputs and instructions replace it (P12). Not to be confused with the inference phase *prefill*. → [§05](05-api-and-prompting.md) · [§06](06-structured-outputs.md)

**Premature "done"**: An agent declaring the task finished when it isn't, because it predicts a plausible ending and grades itself leniently. Decide "done" with an external check: tests, reconciliation or a human (P8). → [§11](11-agents.md) · [§19](19-harness-engineering.md)

**Pretraining**: The first and costliest training stage: self-supervised next-token prediction over trillions of tokens, minimizing cross-entropy (minus the log-probability given to the token that actually came next). Broad knowledge emerges as a side effect of compression. → [§02](02-how-llms-work.md)

**Procedural memory**: How to act: rules, code and skills, held in the system prompt, CLAUDE.md, agent code or a skill (and implicitly the weights). Writing it is the riskiest kind of memory write, because it changes behavior. → [§17](17-memory.md) · [§18](18-skills.md)

**Programmatic tool calling**: Letting the model write a script in a sandbox that calls your tools as functions; each result flows back into the script, not the model's context, and only the script's final output does. It saves context and round trips on chained calls. → [§10](10-tool-use.md)

**Progress file**: A file such as `claude-progress.txt` that records what has been done and what is next, read at the start of every session or loop iteration so a fresh context can pick up the work (P2). → [§16](16-context-engineering.md) · [§19](19-harness-engineering.md)

**Progressive disclosure**: Showing a short description first and loading detail only when it becomes relevant, layer by layer. It is the design principle behind Agent Skills (P3). → [§16](16-context-engineering.md) · [§18](18-skills.md)

**Prompt caching**: Reusing the stored KV cache of an exact prompt prefix across requests, so that part skips prefill and is billed at a fraction of the input price. Entries live 5 minutes by default on Claude (refreshed on each hit), up to a `cache_control` breakpoint. It requires stable content first and volatile content last, and misses fail silently (P10). → [§03](03-inference.md) · [§16](16-context-engineering.md)

**Prompt chaining**: A workflow that breaks a task into fixed steps, each step's output becoming the next step's input, usually with gates in between. Each call gets an easier task and a smaller context (P3). → [§12](12-agentic-design-patterns.md)

**Prompt engineering**: The craft of choosing the text in front of the model so the next-token distribution concentrates on the output you want (P1). It is now one part of context engineering. → [§05](05-api-and-prompting.md)

**Prompt injection**: Untrusted text in the context changing what the system does, against the intent of the developer or user, named by Simon Willison in 2022 after SQL injection. There is no parameterized query for LLMs, so no prompt reliably prevents it (adaptive attacks broke most published defenses in 2025); security has to come from limiting what a fooled model can do (P9). Not to be confused with a *jailbreak*, where the user attacks the provider's safety policy. → [§32](32-security-guardrails.md) · [§01](01-first-principles.md)

**Prompt optimization**: Treating the prompt as a parameter and an eval metric as the objective, then searching automatically for better prompts. It is a training loop where the "weights" are text, so it needs a metric you trust and a held-out test split. → [§29](29-adapting-models.md)

**Prompt template**: A prompt that separates fixed instructions from variable slots, so it can be version-controlled and evaluated per version. The variable is untrusted data entering the instruction channel, so tag it (P9). → [§05](05-api-and-prompting.md)

**Protected Resource Metadata**: A JSON document (RFC 9728) at a well-known URL where an MCP server lists its authorization servers, so clients can discover where to get tokens. → [§33](33-agent-identity.md) · [§15](15-protocols-mcp-a2a.md)

**Provider vs deployer**: Under the EU AI Act, a provider develops an AI system or model and puts it on the market under its own name; a deployer uses one under its authority. Roles shift: rebranding, substantially modifying or repurposing a system into a high-risk use makes you its provider. → [§34](34-governance-regulation.md)

## Q

**QLoRA**: LoRA with the frozen base stored in 4 bits (the NF4 "NormalFloat" type) while adapters train in 16 bits, fitting a 65B model's fine-tune on one 48 GB GPU. → [§29](29-adapting-models.md)

**Quantization**: Storing weights (and sometimes the KV cache) in fewer bits than 16, such as FP8, INT8 or INT4. Because decode is memory-bound, fewer bytes means faster steps and bigger batches, at some cost in precision (usually small at 8 bits, more noticeable at 4) that only your evals can measure. Embeddings can be quantized too. → [§03](03-inference.md) · [§31](31-open-weights-self-hosting.md)

**Query rewriting**: Turning a follow-up like "and for digital ones?" into a standalone search query using the chat history, and optionally expanding acronyms or splitting compound questions. HyDE goes further and embeds a hypothetical answer the LLM drafts, because answers look more like documents than questions do. Each rewrite is an extra model call. → [§09](09-rag.md)

## R

**RAG (retrieval-augmented generation)**: Retrieving relevant passages at request time and putting them in the context so the model answers from them, with citations. It gives the model unseen, fresh, citable and permission-filtered facts that weights can't (P5). Not to be confused with *memory*, which stores what the agent learned across sessions. → [§09](09-rag.md)

**RAGAS**: A framework (Es et al., 2023) whose definitions are the common RAG eval vocabulary: faithfulness, response relevancy, context precision (are the relevant chunks ranked at the top of what was retrieved?) and context recall (what share of a reference answer's claims does the retrieved context support?). It computes most of them with an LLM judge, which should be validated against human labels. → [§09](09-rag.md)

**Ralph loop**: Geoffrey Huntley's minimal loop (Jul 2025): the same prompt run in a fresh agent process over and over, with state kept in a plan file, specs and git. A fresh context each iteration avoids context rot; it needs strong back pressure and added stop rules (P2, P3). → [§21](21-loop-engineering.md)

**Ratchet**: The habit of engineering a permanent fix every time an agent makes a mistake, so every line of a good `AGENTS.md` traces back to a specific failure. Fixes can sit at rising heights (prompt line, skill, tool, hook, linter, architectural constraint) and are removed when a better model makes them redundant (P12). → [§19](19-harness-engineering.md)

**Rate limits (RPM, ITPM, OTPM)**: Per-model provider limits on requests, input tokens and output tokens per minute, enforced as token buckets, plus acceleration limits on ramping up too fast. Exceeding them returns a 429 with `retry-after`. → [§30](30-cost-latency-reliability.md)

**ReAct**: The 2022 pattern where the model alternates Thought, Action (a tool call) and Observation until it decides it's done. Native function calling and extended thinking now implement it directly; it is the autonomous agent loop. → [§12](12-agentic-design-patterns.md) · [§10](10-tool-use.md)

**Reasoning model**: A model trained with reinforcement learning to write a long internal "thinking" passage before answering, so it can spend more compute on harder problems. In 2026 one hybrid model usually carries an effort dial instead of being a separate model. → [§04](04-reasoning-models.md)

**recall@k**: The share of a query's relevant documents that appear in the top k results. For RAG, first-stage recall@k matters most, because the model can't use a passage it never sees. Not to be confused with an ANN index's recall, which measures how many true nearest vectors it returns. → [§08](08-embeddings-and-search.md)

**Reciprocal Rank Fusion (RRF)**: A way to merge ranked lists using only ranks: each document earns 1/(k + rank) per list (k = 60 by convention), so unbounded BM25 scores and cosine scores never need calibrating. It rewards agreement across lists over one strong signal. → [§08](08-embeddings-and-search.md)

**Red teaming**: Attacking your own system first, manually to find new attack classes and with automated scanners (garak, PyRIT, AgentDojo) to scale known ones. Run it continuously as an eval suite against the whole harness, reporting attack success as a rate (P4). → [§32](32-security-guardrails.md)

**Redaction**: Removing personal or secret data from telemetry before storage, in an in-process span processor or in the Collector, using regexes for structured IDs and NER (named-entity recognition) models for free text. Redaction is itself probabilistic, so sample and check it. → [§27](27-observability.md)

**Reducer**: The rule that decides how a node's partial update merges into shared state (overwrite by default, or append). It matters most when parallel nodes write the same key, like a per-column rule in a `MERGE`. → [§14](14-graph-engineering.md)

**Reflection**: Having the model critique and revise its own output (Self-Refine; Reflexion, which writes a verbal lesson to episodic memory after a failed trial and retries). Without external feedback it often fails, which led to separating the checker from the maker. → [§12](12-agentic-design-patterns.md)

**Reinforcement fine-tuning (RFT)**: Applying RL with verifiable rewards to your task: the platform samples several responses per prompt, scores them with your grader and updates toward higher scores. It can only reinforce what the model already does sometimes, so it fails at a 0% success rate. → [§29](29-adapting-models.md)

**Reranker**: A second-stage model, usually a cross-encoder, that reorders a high-recall candidate set (around 100–150) down to the few passages (5–20) that reach the LLM's context. → [§08](08-embeddings-and-search.md) · [§09](09-rag.md)

**Retry budget**: Bounding retries by an overall deadline rather than per-layer attempt counts, and retrying at one layer only, because three attempts at each of five layers multiply load on the bottom layer 243×. → [§30](30-cost-latency-reliability.md)

**Reward hacking**: A model optimizing the checker rather than the intent, such as special-casing tests or reporting unrun work as done. It leaks from RL training into behavior, so keep the checker separate from the maker (P8). → [§04](04-reasoning-models.md) · [§21](21-loop-engineering.md)

**ReWOO and LLMCompiler**: Planning patterns that write tool calls up front: ReWOO's planner names every call's output with a placeholder variable so no LLM call is needed between tools, and LLMCompiler treats the plan as a DAG and runs independent calls in parallel. → [§12](12-agentic-design-patterns.md)

**Risk tiers (EU AI Act)**: Four levels: prohibited practices (Art. 5), high-risk systems (Art. 6), transparency duties (Art. 50) and minimal risk (everything else). Tier by intended purpose: the same model is minimal-risk in a spam filter and high-risk screening CVs. Obligations stack, so a public-facing CV screener is high-risk and has transparency duties. → [§34](34-governance-regulation.md)

**RL environment**: A task, the tools and sandbox to attempt it, and a verifier that scores the attempt, behind an interface like `reset()` and `step(action)`. Structurally the same as an agent eval; the difference is that the score becomes a reward, so a foolable verifier gets attacked. → [§29](29-adapting-models.md) · [§26](26-evals.md)

**RLHF (reinforcement learning from human feedback)**: The InstructGPT recipe: humans rank outputs, a reward model learns to predict the rankings, and RL (PPO) pushes the model toward higher reward while keeping it close to the SFT model. Constitutional AI / RLAIF replaces human harm labels with AI feedback guided by written principles. → [§02](02-how-llms-work.md)

**RLVR (reinforcement learning with verifiable rewards)**: RL on problems a program can check, such as math with known answers or code with unit tests, so there is no neural judge to flatter. It is the recipe behind reasoning models and produced backtracking and self-checking. → [§04](04-reasoning-models.md) · [§29](29-adapting-models.md)

**Routing**: Classifying an input and dispatching it to a specialized handler with its own prompt, tools and possibly model; also used to send easy traffic to a cheaper model (P10). The failure mode is silent misrouting, so keep a safe default route and a routing eval. → [§12](12-agentic-design-patterns.md) · [§30](30-cost-latency-reliability.md)

**Rug pull**: An MCP server changing a tool's description after it was approved, so install-time approval proves nothing about tomorrow. Pin versions and hash tool definitions. → [§15](15-protocols-mcp-a2a.md)

## S

**safetensors**: The usual file format for open weights, preferred over pickle-based checkpoints because those can execute code when loaded. → [§31](31-open-weights-self-hosting.md)

**Sampling, roots and elicitation (MCP)**: Client features offered to MCP servers: sampling let a server borrow the host's model, roots told it which directories were in scope, and elicitation lets it ask the user for input mid-call (a form, or a URL for flows like sign-in). The 2026-07-28 spec deprecates sampling and roots and keeps elicitation. → [§15](15-protocols-mcp-a2a.md)

**Sandbox**: An execution environment whose reach (filesystem, network, processes) is limited by the operating system or a hypervisor rather than by the model's good behavior. Filesystem and network isolation only work together, and secrets should stay outside it (P6, P9). → [§20](20-agent-runtime.md) · [§32](32-security-guardrails.md)

**Saturation (benchmark)**: A benchmark near its ceiling, where real capability gains show up as tiny score changes and it stops guiding improvement. → [§26](26-evals.md) · [§23](23-coding-agents.md)

**Scaling laws**: The finding that loss falls along a smooth power law as parameters, data and compute grow (Kaplan 2020), refined by Chinchilla (2022) to scale model size and training tokens together. → [§02](02-how-llms-work.md)

**Schema escape hatch**: A legal path for the honest answer, such as a nullable field, an `"unknown"` enum value or a `not_found` list. Without one, a required field forces the model to invent data. → [§06](06-structured-outputs.md) · [§07](07-multimodal.md)

**Schema-on-write vs schema-on-read**: The data-engineering distinction between rejecting records that don't match a schema at write time and storing anything and parsing later. Raw LLM output is schema-on-read text; structured outputs make it schema-on-write. → [§06](06-structured-outputs.md)

**Scope**: A named permission in a token, such as `invoices:read`. Request the minimum and step up later; avoid wildcard scopes. → [§33](33-agent-identity.md)

**Self-attention**: The transformer step where every token gathers information from other tokens: its query is scored against the other tokens' keys, and the output is a weighted average of their values. Many attention heads run in parallel, each learning its own pattern. Its cost grows with the square of the sequence length, the mechanism behind the attention budget (P3). → [§02](02-how-llms-work.md)

**Self-consistency**: Sampling several independent answers and taking the majority; wrong reasoning paths scatter while right ones converge, and the agreement rate is a free confidence score (P4). Costs N× and needs comparable answers. Not to be confused with *best-of-N*, where a scorer or verifier picks the best of N samples instead of a vote. → [§04](04-reasoning-models.md) · [§12](12-agentic-design-patterns.md)

**Self-Instruct**: A 2022 method where a model expands a small pool of human seed tasks into thousands of new instructions, keeping one only if its ROUGE-L word-overlap similarity to existing ones is below 0.7. Alpaca used it. → [§28](28-data-flywheels.md)

**Semantic cache**: Returning a cached answer when a new query's embedding is close enough to a previous one. Risky: "cancel my order" and "don't cancel my order" embed close together, and personalized answers can leak across users. Not to be confused with *prompt caching*, which reuses only the prefill and leaves the output distribution unchanged, or an exact response cache keyed on the full request. → [§30](30-cost-latency-reliability.md)

**Semantic memory**: Long-term facts about the world, the user or the agent ("prod warehouse is `ANALYTICS_PROD`"), stored as profile documents or in a key-value or vector store. Like dimension tables. → [§17](17-memory.md)

**Serious incident**: An event a high-risk provider must report under Art. 73, within 15 days at most (2 days for widespread infringement or critical infrastructure, 10 days if someone died). Preserve evidence (model, prompt, config, audit records) before you hotfix. → [§34](34-governance-regulation.md)

**Server-sent events (SSE)**: The streaming format LLM APIs use: one long-lived HTTP response made of named events carrying token deltas. An error event can arrive after the HTTP 200, so streaming code must handle mid-stream failure. → [§05](05-api-and-prompting.md) · [§35](35-ai-ux.md)

**Serving engine**: The server side of inference packaged as a program (vLLM, SGLang, llama.cpp): continuous batching, paged KV cache, prefix caching and quantized kernels behind an HTTP API; SGLang's RadixAttention reuses KV caches for any shared prefix. Fleet engines batch many users; local tools fit one model on one machine. → [§31](31-open-weights-self-hosting.md) · [§03](03-inference.md)

**Session log**: An append-only log of everything that happened in an agent run, kept outside the harness as the source of truth; the context window is a view derived from it, so compaction becomes a reversible transformation. Moving state into the log turned the harness and sandbox from pets (hand-tended, irreplaceable) into cattle (replaced, not repaired). → [§20](20-agent-runtime.md)

**Short-term vs long-term memory**: Short-term memory is thread-scoped state saved by a checkpointer, so one conversation can resume; long-term memory lives in a store shared across threads, namespaced by user or org. → [§17](17-memory.md) · [§14](14-graph-engineering.md)

**Silent invalidator**: Anything that quietly breaks the prompt-cache prefix, such as a timestamp, unsorted JSON or a per-user tool list, so every request pays full price while nothing errors. Watch the cache-read share of input tokens. → [§16](16-context-engineering.md) · [§03](03-inference.md)

**Single-threaded writes**: The rule that one agent owns every change to shared state while other agents contribute findings, reviews or advice ("many contributors, one writer"), because parallel writers make conflicting implicit decisions. → [§13](13-multi-agent.md) · [§12](12-agentic-design-patterns.md)

**SIP (Session Initiation Protocol)**: The signaling protocol of internet telephony. A SIP trunk provider turns a phone number into IP traffic, and encrypted audio travels as SRTP. Phone audio is narrowband (G.711 at 8 kHz), which hurts recognition, and keypad presses arrive as DTMF events. SIP headers and caller ID are untrusted metadata, not authentication. → [§25](25-voice-agents.md)

**Skill description (trigger)**: The frontmatter description, the only part of a skill in context before activation. The model reads it to decide whether to load the body, so it works as a probabilistic routing rule: vague ones under-trigger, greedy ones over-trigger (P4). Test it like a classifier. → [§18](18-skills.md)

**Skill supply chain**: The risk that a third-party skill carries malicious instructions or scripts that run with the agent's permissions; Snyk found critical issues in 13.4% of 3,984 public skills (Feb 2026). Review, pin, scan and sandbox skills like dependencies (P9). → [§18](18-skills.md) · [§32](32-security-guardrails.md)

**SKILL.md**: A skill's one required file: YAML frontmatter (a metadata block between two `---` lines) with a `name` (up to 64 lowercase characters, matching the folder) and a `description` (up to 1,024 characters saying what and when), followed by free-form markdown instructions. → [§18](18-skills.md)

**Skills over MCP**: An official MCP extension that lets a server publish Agent Skills as resources; host and SDK support is still rolling out as of Oct 2026. → [§18](18-skills.md) · [§15](15-protocols-mcp-a2a.md)

**SLI, SLO and error budget**: A measured indicator, its target, and the allowed shortfall you can spend on risk (Google SRE). For LLMs, an HTTP 200 isn't success: count good events only if complete, valid and on time, and add a sampled quality SLI (P4). → [§30](30-cost-latency-reliability.md) · [§36](36-product-thinking.md)

**Slice**: A tag on each eval case (task type, language, customer tier) so results are reported per slice, because an aggregate can rise while one slice collapses. → [§26](26-evals.md)

**Slopsquatting (package hallucination)**: Models suggesting packages that don't exist (at least 5.2% of commercial-model suggestions in one 2024 study), and attackers registering those names so anyone who trusts the suggestion installs their code. Defend with lockfiles, a vetted package proxy and existence checks. → [§23](23-coding-agents.md) · [§32](32-security-guardrails.md)

**Span**: One timed operation inside a trace (a model call, tool execution, retrieval or agent step), carrying trace, span and parent IDs, timing, status and attributes. Parent links make spans a tree. → [§27](27-observability.md)

**Spec-driven development (SDD)**: Writing a structured specification before the agent codes and treating it as the source of truth. Böckeler found three levels: spec-first (written for one task, then discarded), spec-anchored (kept and maintained) and spec-as-source (humans edit only the spec). Tools include Kiro (EARS-notation acceptance criteria) and Spec Kit (with a "constitution" of fixed principles). → [§23](23-coding-agents.md)

**Speculative decoding**: A small draft model guesses the next k tokens and the large model checks them all in one pass, accepting the run consistent with its own distribution. Output is mathematically unchanged; only speed improves. → [§03](03-inference.md)

**Speech-to-speech (S2S)**: A voice architecture where one model takes audio tokens in and produces audio tokens out, giving the lowest latency, tone in both directions and built-in barge-in, at the cost of harder auditing and testing. → [§25](25-voice-agents.md) · [§07](07-multimodal.md)

**Spend cap**: A hard limit on spend at the provider, gateway or application level (max turns, per-user quotas), the defense against a loop that never stops. In durable runs, keep the counter in the durable log so a crash doesn't reset it. → [§30](30-cost-latency-reliability.md) · [§20](20-agent-runtime.md)

**Spotlighting**: Marking untrusted text by delimiting it with tags, interleaving a special character between its words, or encoding it, so the model treats it as data. Cheap and effective at lowering attack rates, but probabilistic, so never the boundary. → [§32](32-security-guardrails.md)

**Sprint contract**: An agreement the generator and evaluator negotiate before coding on what "done" means for a chunk of work, in Anthropic's planner–generator–evaluator harness. → [§19](19-harness-engineering.md) · [§12](12-agentic-design-patterns.md)

**Stateless MCP**: The 2026-07-28 spec's core change: no `initialize` handshake or session ID; every request carries its version and capabilities in `_meta`, so any server instance can serve any request behind a plain load balancer. Servers keep state through explicit handles the model passes back, and a server that needs input mid-call returns `input_required` with an opaque `requestState` for the client to retry with (Multi Round-Trip Requests). → [§15](15-protocols-mcp-a2a.md)

**Statelessness**: The API keeps nothing between calls, so your code resends the full conversation every time and owns the history. Server-side state options only move the replay to the vendor (P2). → [§05](05-api-and-prompting.md)

**stdio and Streamable HTTP**: MCP's two standard transports. With stdio, the host launches the server as a subprocess and exchanges JSON-RPC over stdin/stdout (so stdout is the wire; log to stderr). With Streamable HTTP, each message is a `POST` to one endpoint, answered with JSON or an SSE stream, using OAuth 2.1. → [§15](15-protocols-mcp-a2a.md)

**Step-up authorization vs step-up approval**: Step-up authorization gets *more scope* from the authorization server (MCP's `insufficient_scope` challenge); step-up approval has a human confirm *one specific action*. A UI click alone is not authorization; CIBA can bind approval to an authorization-server event pushed to the user's phone. → [§33](33-agent-identity.md)

**stop_reason**: The response field that says why generation ended: `end_turn`, `max_tokens` (the required hard cap on output, thinking included, was hit, so the answer is truncated), `stop_sequence`, `tool_use`, `pause_turn`, `refusal` and others. Check it before using the content; a refusal is a normal HTTP 200. → [§05](05-api-and-prompting.md) · [§10](10-tool-use.md)

**Stopping condition (stop condition)**: Whatever decides an agent loop is over: the model's `end_turn`, max turns, a token or cost budget (Anthropic's task budgets also show the model its remaining budget), a wall-clock timeout, stall detection (no progress for k iterations), an external goal check, or a human interrupt. Real agents layer several, because `end_turn` is a claim, not a proof. → [§11](11-agents.md) · [§21](21-loop-engineering.md)

**Store**: A cross-thread key-value layer, namespaced by something like a user ID, for data that outlives any single run, such as preferences and learned facts. Not to be confused with a *checkpointer*, which is scoped to one thread. → [§14](14-graph-engineering.md) · [§17](17-memory.md)

**Strict tool use**: Applying the same grammar-constrained decoding to tool arguments (`strict: true`), so calls always validate against the tool's input schema. → [§06](06-structured-outputs.md) · [§10](10-tool-use.md)

**Structured note-taking**: The agent writing notes outside the window (a to-do list, `NOTES.md`, a progress log) and reading them back later. Notes survive compaction and resets, and rewriting them recites the goal. Once they outlive the session, they become memory. → [§16](16-context-engineering.md) · [§17](17-memory.md)

**Structured outputs**: An API feature that compiles your JSON Schema into a grammar and constrains decoding to it, so the response is guaranteed to match except on refusal or truncation. It guarantees syntax and schema, not correct values, so a validator such as Pydantic still checks business rules. → [§06](06-structured-outputs.md)

**Subagent (agents-as-tools)**: A specialist agent that a lead agent calls like a tool: it runs its own loop in a fresh context holding only its brief and returns a short summary as the tool result. The lead keeps the conversation and writes the final answer. Not to be confused with a *handoff*, where control transfers. → [§13](13-multi-agent.md)

**Supervised fine-tuning (SFT)**: Next-token training on curated (prompt, ideal response) pairs, also called instruction tuning. It teaches format and tone but can only imitate demonstrations. → [§02](02-how-llms-work.md) · [§29](29-adapting-models.md)

**Swarm**: In OpenAI Swarm and langgraph-swarm, agents handing control to one another with only one active at a time: decentralized routing over time, not parallelism. Not to be confused with the centralized *supervisor* (orchestrator-workers) topology, where one hub delegates and synthesizes. → [§13](13-multi-agent.md)

**SWE-bench**: A 2023 coding benchmark of 2,294 real GitHub issues in 12 Python repositories, graded by hidden tests. SWE-bench Verified (2024) is a 500-task screened subset; OpenAI stopped reporting it in Feb 2026, citing saturation, flawed tests and contamination. → [§23](23-coding-agents.md)

**Sycophancy**: A post-training side effect where the model favors convincing, agreeable answers over correct ones, because people (and preference models) often prefer agreement. → [§02](02-how-llms-work.md)

**Synthetic data**: Data generated by a model rather than collected from users. It buys coverage of rare cases, privacy and volume; diversity has to come from conditioning (personas, seeds, difficulty; Persona Hub scaled personas to a billion), quality from filters run cheapest first, and diversity should be measured (distinct-n, embedding spread). → [§28](28-data-flywheels.md)

**System of record (docs)**: A structured, versioned `docs/` directory (design docs, architecture maps, plans) that a short `AGENTS.md` points into, checked by CI for freshness and kept current by a recurring doc-gardening agent, instead of one giant instruction file. → [§19](19-harness-engineering.md)

**System prompt**: The developer's standing instructions (role, rules, format, background), sent as a top-level field and given extra weight by post-training. It is just more tokens in the same channel as user text, so it sets priorities but is not a security boundary (P9). → [§05](05-api-and-prompting.md)

## T

**Taint tracking**: Marking data from untrusted sources and following the mark to everything that depends on it, so a policy gate can block risky actions once tainted content has entered the context. Taint must survive summaries, memory writes and subagent handoffs. → [§32](32-security-guardrails.md)

**Task and trial (eval)**: A task is one input with success criteria (a suite is a set of them); a trial is one attempt at it, run several times because outputs vary (P4). The outcome is the environment's final state, which you grade by default: the agent may *say* "booked," but did the reservation row appear? → [§26](26-evals.md)

**Temperature**: A sampling knob that divides the logits by T before softmax: below 1 sharpens the distribution, above 1 flattens it, and near 0 approaches greedy. Many current hosted models reject non-default values. → [§02](02-how-llms-work.md)

**Terminal-Bench**: A benchmark of terminal tasks, each a Docker environment with a human-written solution and tests (version 2.0 has 89 tasks), now maintained continuously by dropping tasks every frontier model solves. → [§23](23-coding-agents.md)

**Test-time compute**: Compute spent per query at answer time, either serially (one sample that thinks longer) or in parallel (many samples plus a vote or a scorer). Not to be confused with *train-time compute*, spent before release. → [§04](04-reasoning-models.md)

**Thinking block**: A response content block holding the model's reasoning, shown as a summary or empty by default; its `signature` carries the full encrypted reasoning. With interleaved thinking the model also reasons after each tool result, so thinking and redacted-thinking blocks must go back unchanged with their tool calls, and history stays append-only. Thinking is billed as output whether or not you see it. → [§04](04-reasoning-models.md)

**Time travel**: Listing a thread's checkpoints and replaying or forking from an old one. Replay re-executes later nodes, LLM calls included, so results can differ (P4); for audits use traces, not replay. → [§14](14-graph-engineering.md)

**Tiny Teams**: swyx's term (2025) for teams with more millions in annual recurring revenue than employees, enabled partly by coding agents raising output per engineer; the surveyed figures are self-reported. → [§36](36-product-thinking.md)

**Token**: A chunk of text from a fixed vocabulary (a word with its leading space, a fragment, a punctuation mark or a byte). The model sees only integer token IDs, and tokens are the unit of cost and limits (P10). → [§02](02-how-llms-work.md)

**Token passthrough**: An MCP server accepting a token not issued to it and forwarding it downstream. Forbidden: it bypasses audience-based controls, logs the wrong identity and turns a stolen token into a proxy. Each hop gets its own token; token exchange (RFC 8693) can narrow it, with an `act` claim recording who acts for whom. → [§33](33-agent-identity.md) · [§15](15-protocols-mcp-a2a.md)

**Tool poisoning**: Hiding instructions in a tool's description, which the model reads as context, for example to make it read a secret file and smuggle it out through a parameter. User approval of calls doesn't stop it (P9). In tool shadowing, a malicious server's description changes how the agent uses a trusted server's tools. → [§15](15-protocols-mcp-a2a.md) · [§32](32-security-guardrails.md)

**Tool search**: Marking most tools `defer_loading: true` so the model starts with only a search tool and pulls matching definitions into context when needed. It is retrieval applied to tools, worth it once definitions exceed about 10K tokens (P3). → [§10](10-tool-use.md) · [§16](16-context-engineering.md)

**Tool use (function calling)**: The contract in which you declare tools with JSON Schema, the model emits a structured request to call one, your code executes it, and the result goes back as context. The model never runs anything itself, so all capability and risk live in the executor (P6). Good tools are few, high-level, clearly named (namespaced when many servers are connected), described for the model, and mistake-proofed (poka-yoke). Not to be confused with *MCP*, a protocol for distributing tools across hosts, or *skills*, which package know-how rather than actions. → [§10](10-tool-use.md)

**Tool-result clearing (context editing)**: Replacing old tool results with a placeholder once the agent has acted on them, the lightest and safest form of compression. Make it restorable: drop the content but keep the path or URL so the agent can fetch it again. Anthropic's API does it server-side; clearing by hand breaks the cache and, on 5.5-family models, preserved thinking. → [§16](16-context-engineering.md)

**tool_choice**: The API setting for whether the model may, must or must not call tools (`auto`, `any`, `tool`, `none`). As of Oct 2026, the newest Claude models reject forced `any` and `tool` with a 400; use `auto` plus instructions and `strict`. → [§10](10-tool-use.md)

**tool_use and tool_result blocks**: The Anthropic API's typed content blocks for a tool call (name, id and JSON `input`) and its answer (`tool_use_id` and content), which must come in the user turn right after the call. Every `tool_use` needs a matching `tool_result`, or the API rejects the history. One response can hold several `tool_use` blocks (parallel tool calls): run independent ones concurrently and return all results in one user message. → [§10](10-tool-use.md)

**Trace**: The complete record of one request or task, from the user's input to the final response, including every model call, tool call and retrieval; in eval vocabulary also called the transcript or trajectory. Log enough to reconstruct what the model saw (P2). → [§27](27-observability.md) · [§26](26-evals.md)

**Transformer**: The 2017 architecture behind LLMs: a stack of identical layers, each combining self-attention with a feed-forward network (MLP) that holds most of the weights, joined by residual connections. It processes all positions in parallel during training. → [§02](02-how-llms-work.md)

**Tree of Thoughts (ToT)**: A search pattern that explores partial "thoughts" breadth- or depth-first, with the model scoring branches and backtracking; LATS applies Monte Carlo tree search to ReAct trajectories with a value function and environment feedback. Reasoning models now do most of this inside their thinking, so explicit scaffolding is mostly dead weight unless a cheap, trustworthy verifier exists (P12). → [§12](12-agentic-design-patterns.md)

**TTFT and TPOT**: Time to first token (request to first output token, covering network, queueing and prefill; it grows with uncached prompt length) and time per output token (the average gap after that; ITL is each individual gap). End-to-end latency ≈ TTFT + TPOT × (output tokens − 1). Throughput counts tokens per second across all users, and goodput counts only requests that meet their latency targets. → [§03](03-inference.md)

**Turn detection**: Deciding that the user has finished speaking: by a fixed silence window (simple but either interrupting or sluggish), by a semantic classifier over the words (semantic VAD), or by an audio model that also uses intonation and rhythm. It is a prediction problem, as in human conversation. → [§25](25-voice-agents.md)

## V

**Valid but wrong**: Output that parses and matches the schema but holds incorrect values, such as an invented total. It is the failure that matters, because nothing flags it; only evals measure it (P4). → [§06](06-structured-outputs.md)

**Vector database**: A database built for ANN search at scale (Pinecone, Weaviate, Qdrant, Milvus, Chroma and others). Since most databases have added vector types, the choice is now mostly operational. Treat any vector index as a derived dataset with lineage, freshness and delete propagation. → [§08](08-embeddings-and-search.md)

**Verifier**: A program that scores an output as right or wrong (an answer key, a test suite), used as the reward in RLVR and in reinforcement fine-tuning. → [§04](04-reasoning-models.md) · [§29](29-adapting-models.md)

**Vibe coding**: Karpathy's term (Feb 2025) for accepting every AI diff without reading it and forgetting "the code even exists," scoped to throwaway projects. Not to be confused with *agentic engineering*, where you still own and review the result. → [§23](23-coding-agents.md)

**Vision-language model (VLM)**: A model that takes images as well as text; small VLMs are also used to parse page images straight into structured text. Its dangerous failure is hallucinated reading: writing clean, plausible text for a region it couldn't read, where classic OCR would fail visibly. → [§07](07-multimodal.md)

**Visual token**: The vector one image patch becomes after a vision encoder (such as a Vision Transformer) and a projector map it into the LLM's embedding space. Visual tokens sit in the context like text tokens and cost money, prefill time and attention; on Claude, one per 28×28-pixel patch (P3, P10). → [§07](07-multimodal.md)

**vLLM**: An open-source serving engine built around PagedAttention, which stores the KV cache in fixed-size blocks like operating-system memory pages so almost no memory is wasted. It is the default for GPU self-hosting, and it still exposes the sampling knobs that hosted APIs hide. → [§03](03-inference.md) · [§31](31-open-weights-self-hosting.md)

**Voice activity detection (VAD)**: A small classifier that labels short audio frames as speech or non-speech. Not to be confused with *turn detection*, which asks whether the user is done. → [§25](25-voice-agents.md)

**Voice-to-voice latency**: The time from the user's last syllable to the agent's first audible sound, measured at the user's ear. Budget it at p50 and p95 against human turn gaps of about 200 ms (P10). → [§25](25-voice-agents.md)

## W

**WebRTC**: The browser and mobile standard for real-time media over UDP, with jitter buffers, packet-loss concealment and echo cancellation; it drops late packets instead of waiting. Not to be confused with *WebSocket*, a reliable, ordered TCP connection better suited to server-to-server links. → [§25](25-voice-agents.md)

**Workflow**: A system where LLM calls and tools are orchestrated through predefined code paths, so your code owns control flow. It is predictable, cheap and testable, like a DAG you wrote (P7). Not to be confused with an *agent*, where the model decides each next step. → [§11](11-agents.md) · [§12](12-agentic-design-patterns.md)

**Workload identity**: A short-lived signed identity the platform issues to a running workload (Kubernetes, cloud VM, CI runner), such as an OIDC JWT or a SPIFFE ID, exchanged for an access token so no long-lived secret is stored anywhere. → [§33](33-agent-identity.md)

**Wrapper risk**: The risk that a product that is mostly a prompt and a UI over someone else's model gets shipped natively by the vendor or copied by anyone with the same API. Test: would a model twice as good and half the price make your product better or unnecessary? → [§36](36-product-thinking.md)

**Write, select, compress, isolate**: LangChain's four buckets of context-engineering technique: save state outside the window, pull in only what this step needs, keep fewer tokens for the same information, and split work across windows. → [§16](16-context-engineering.md)
