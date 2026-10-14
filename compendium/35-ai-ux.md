# 35. AI UX and Generative UI

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

The interface followed the system thread. ChatGPT (Nov 2022) made the **chat box** the default AI interface. **Copilots** then embedded models inside existing tools: code completion, "draft this email," "explain this query." From 2024–2025 **agents with approvals** acted on the user's behalf and paused for permission ([§11](11-agents.md), [§20](20-agent-runtime.md)). From 2024–2026 **generative UI** let the model emit interface components instead of prose. [§34](34-governance-regulation.md) ended on a gap: law can require disclosure and the *ability* to override, but whether people actually understand, trust appropriately and correct the system is decided by design. P4 (outputs vary and can be wrong), P10 (every token costs time), P6 (the model proposes; code disposes) and P8 (verification is the bottleneck) drive this section.

## Why this exists

Classic UX design assumes deterministic software. A button does the same thing every time, and when it doesn't, that's a bug you fix. An AI feature breaks this in three ways.

**Its outputs vary and are sometimes wrong, fluently (P4).** A wrong answer looks exactly like a right one: same tone, same formatting, same confidence. The interface is the only place the user can tell the difference, so its job shifts from "make it easy to use" to "make it easy to check, correct and stop." The goal is **calibrated trust**: users rely on the system where it is reliable and check it where it isn't.

**It is slow, and unpredictably so (P10).** Generation is sequential, one token at a time ([§03](03-inference.md)). A reasoning model may think for a minute before writing anything, and an agent may run for hours. A spinner that works for a 200 ms API call is useless here.

**It acts (P6).** Once a model can call tools, the UI becomes the consent layer for actions. Human attention is the scarcest resource in the loop (P8), so the UI decides whether verification actually happens or turns into a ritual.

## How it works (under the hood)

### Streaming and perceived latency

The model produces output token by token. Waiting for the whole answer makes the user sit through all of it, while **streaming** shows each token as it is decoded. Total time is unchanged, but *perceived* latency drops to the **time to first token** (TTFT), and the user reads at roughly the speed the model writes.

The Anthropic Messages API streams over **Server-Sent Events (SSE)**: a long-lived HTTP response of `text/event-stream`, in which each event is an `event:` line, a `data:` line of JSON, and a blank line.

```text
event: message_start
data: {"type":"message_start","message":{"id":"msg_...","type":"message",...}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":12}}

event: message_stop
data: {"type":"message_stop"}
```

Tool calls stream as `input_json_delta` fragments of partial JSON, and thinking streams as `thinking_delta`. The stream can also carry `ping` events and a mid-stream `error` event (for example, `overloaded_error`). The docs say new event types may be added, so handle unknown types gracefully. OpenAI's Responses API streams typed events with different names over the same SSE mechanism.

Your **backend** should hold the API key, consume this stream, and re-emit **app-level events** to the browser: text deltas, plus events only your harness knows about, such as tool progress, approval requests and run status. A renderer for such a stream:

```python
import json

# Stub of what YOUR backend streams to the browser. It relays the model's text
# (Anthropic's content_block_delta / text_delta) and adds its own app-level events.
STUB = """event: text_delta
data: {"text": "Found 3 failed runs. "}

event: tool_progress
data: {"tool": "query_warehouse", "step": 2, "of": 5, "detail": "scanning partitions"}

event: text_delta
data: {"text": "The fix is a full refresh of nightly_orders."}

event: approval_required
data: {"id": "ap1", "tool": "rerun_job", "args": {"job": "nightly_orders", "full_refresh": true}, "reversible": false}

event: done
data: {"stop_reason": "end_turn"}"""

def parse_sse(raw: str):
    for frame in raw.split("\n\n"):                      # a blank line ends each event
        fields = dict(line.split(": ", 1) for line in frame.splitlines())
        yield fields["event"], json.loads(fields["data"])

def render(raw: str, ask_human) -> None:
    for event, data in parse_sse(raw):
        if event == "text_delta":                        # paint at once: perceived latency = TTFT
            print(data["text"], end="", flush=True)
        elif event == "tool_progress":                   # a status line you REPLACE, not append
            print(f"\n  [{data['tool']} {data['step']}/{data['of']}: {data['detail']}]")
        elif event == "approval_required":               # exact args + reversibility, untruncated
            print(f"\n  APPROVE? {data['tool']}({json.dumps(data['args'])})"
                  f"{'' if data['reversible'] else '  [cannot be undone]'}")
            decision = ask_human(data)                   # nothing runs until this returns (P6)
            print(f"  -> {decision}; POST /approvals/{data['id']}, then the run resumes with it")
        elif event == "done":
            print(f"\n  [finished: {data['stop_reason']}]")

render(STUB, ask_human=lambda req: "approve" if req["reversible"] else "deny")
```

A production parser must also handle multi-line `data:` fields, comment lines and reconnection. Ignore event types you don't know rather than crashing. Streaming has consequences that batch responses don't:

- **You can't un-show text.** If an output guardrail ([§32](32-security-guardrails.md)) trips halfway through, the user has already read the first half. Either buffer high-risk outputs and check them before display, or design a visible retraction.
- **Partial structure is invalid structure.** Streamed JSON and Markdown are incomplete until the end. Render tolerantly (close open code fences for display) and validate only at the end ([§06](06-structured-outputs.md)).
- **Thinking looks like silence.** On Opus 5.5, Sonnet 5.5 and other current Claude models, thinking `display` defaults to `"omitted"` as of Oct 2026, so a reasoning model streams nothing visible while it thinks. Set `display: "summarized"`, or `"updates"` for short progress notes between tool calls **(Preview)**, or show your own activity indicator. Never leave a frozen screen.
- **Stop must work.** A visible, keyboard-reachable stop button that actually closes the stream and cancels the run.

### Progress visibility for long-running agents

A chat stream works for seconds. An agent that runs for twenty minutes needs a different surface, which shows four things:

- **the plan:** a task list that updates as steps finish
- **the current step:** what is running now, with tool progress
- **artifacts so far:** files changed, rows written, drafts produced
- **budget burn:** elapsed time, tokens or cost against the cap

Honest progress beats fake progress bars. If the total number of steps isn't known, show an activity log, not a percentage. Durable runs ([§20](20-agent-runtime.md)) outlive the browser tab, so the UI must be able to **reattach** to a run in progress and send a notification when a run finishes or blocks. Protocols now standardize these signals. AG-UI has step and "activity" events for structured progress (below), and MCP's Tasks extension gives long-running tool operations durable handles ([§15](15-protocols-mcp-a2a.md)).

### Designing for verification

**Verifying must cost less than doing the task yourself, or users skip it.** That is P8 in product terms. The main techniques:

- **Citations.** Anthropic's citations feature (enable it per `document` block) returns text blocks that carry `citations` with `cited_text` and a location: a character range, page range or content block. The docs state that citations "are guaranteed to contain valid pointers to the provided documents." That guarantees the quote exists, not that it supports the claim. Render citations as inline markers that open the source *at the cited span*, so checking takes one click. (Citations can't be combined with structured outputs; the API returns a 400.)
- **Show sources, including absences.** "Searched 3 runbooks, none mention this error" is more useful and more honest than a confident guess. Make "I couldn't find it" a first-class answer in both the prompt and the UI.
- **Diffs.** For edits, show the change, not the result. Coding agents show diffs, and documents should show tracked changes. A reviewer can check a 12-line diff and can't re-read a 400-line file.
- **Previews and dry runs.** Before an action, show its effect: the SQL that will run and its row estimate, the email as the recipient will see it, the files that will be deleted. This is `terraform plan` for agents.
- **Undo.** Reversibility is the cheapest safety mechanism. Drafts instead of sends, soft deletes, checkpoints and git commits make most actions safe to auto-approve, and they leave approvals for the few that can't be undone.
- **Evidence over confidence scores.** A model's self-reported "90% confident" is not a calibrated probability unless you have checked it against your eval set ([§26](26-evals.md)). Prefer showing the evidence.

### Human-in-the-loop UX: approvals, fatigue, autonomy

The mechanics live in the harness. A tool call arrives, policy says `ask`, and the run pauses durably until a person answers ([§20](20-agent-runtime.md)). The UX question is what the person sees and how often.

**A good approval card** shows:

- *what* will happen: the tool and its **full, untruncated arguments**. Hidden arguments are how tool poisoning slips data out ([§15](15-protocols-mcp-a2a.md)).
- *why*: the agent's stated reason
- the *effect*: a preview
- *reversibility*
- *scope choices*: approve once, approve this tool for this project, deny with a note that goes back to the model, or edit the arguments

**Approval fatigue** is what happens when you ask too often. People stop reading and click yes, and the approval becomes theater. Anthropic reported in Oct 2025 that sandboxing Claude Code "safely reduces permission prompts by 84%" internally: it drew a boundary once instead of asking a hundred times. The design rule is **ask rarely and meaningfully**:

- reads run freely
- reversible writes run with undo
- only irreversible or externally visible actions ask

Measure approval rate, time-to-decision and edits-before-approve. Near-100% approvals in under two seconds means there is no real oversight, which is exactly what [§34](34-governance-regulation.md) warns about.

**Autonomy settings** make the P7 dial visible to the user. Claude Code's permission modes run from plan-only to auto-approve ([§20](20-agent-runtime.md)). Feng et al. describe the user's role as operator, collaborator, consultant, approver or observer ([§11](11-agents.md)). Expose the dial per task or scope, start conservative, and let users grant more autonomy as the agent earns it. For background ("ambient") agents, LangChain names three human-in-the-loop patterns: **notify** (flag it, take no action), **question** (ask instead of guessing) and **review** (approve a proposed action).

### Error and uncertainty communication

Different failures need different UI states. Silently collapsing them into "Something went wrong" throws away information the user needs.

| Situation | Signal | What the UI should do |
|---|---|---|
| Truncated output | `stop_reason: "max_tokens"` | Show it is incomplete; offer "continue" |
| Refusal | `stop_reason: "refusal"` | Say so plainly; suggest what *is* possible |
| Tool failed | `is_error` tool result | Name the failing step; offer retry; keep partial work |
| Overloaded or rate-limited | HTTP 429/529, stream `error` | Retry with backoff; tell the user if it takes long |
| Wrong answer | **No signal** | Make verification cheap (above); invite correction |

The last row is the important one. The most common failure produces no error at all, which is why verification design matters more than error design. Language matters too. The UI and the model's own text should never claim more than happened: "I ran the tests" is only allowed if a tool result shows the tests ran.

### Feedback capture

Feedback turns usage into improvement ([§28](28-data-flywheels.md)). The signals differ a lot in quality:

- **Explicit:** thumbs, reason codes, free text. They are cheap to build but sparse (most users never click) and skewed toward strong reactions.
- **Implicit:**
  - **edits**: the diff between the AI's draft and what the user actually sent is the richest signal
  - accept/reject of suggestions, the classic copilot metric
  - regenerate, copy, abandon
  - follow-ups like "no, I meant…"
  - time to accept

The engineering rule is to **attach every feedback event to the trace ID** of the response it judges ([§27](27-observability.md)). A thumbs-down that can't be joined to the exact prompt, model version and retrieved context is a vanity metric. Joined, it becomes an eval case ([§26](26-evals.md)). Tell users how their feedback is used, especially if it may become training data.

### Generative UI

**Generative UI** means the model emits a description of interface components (a card, a table, a form, a chart) instead of, or alongside, prose, and the application renders it. The idea goes back to Vercel's AI SDK 3.0 (Mar 1, 2024), which streamed React Server Components from LLM tool calls. As of 2026 there are three levels, from most to least constrained.

**1. Tool-bound components.** Each tool has a pre-built component, so the model only picks the tool and its arguments, and the app renders the result in a fixed widget. This is the most predictable level.

**2. Declarative catalogs.** The model emits a component tree (JSON) that uses only components from a catalog the app owns. The app validates it and renders it with native widgets. Examples:

- **OpenAI ChatKit widgets**: a `WidgetRoot` container such as a `Card` with `confirm`/`cancel` actions, holding components. Clicks arrive at your backend as action payloads.
- **A2UI**: an Apache-2.0 spec created by Google. Its site lists v0.9.1 as current and v1.0 as a candidate as of Oct 2026.

As of Oct 2026, OpenAI is retiring Agent Builder (shutdown scheduled for Nov 30, 2026), and ChatKit remains available.

**3. Sandboxed apps.** The server ships a whole HTML application, and the host isolates it. **MCP Apps** launched on Jan 26, 2026 as the *first official MCP extension* (`modelcontextprotocol/ext-apps`). It was proposed in Nov 2025, building on the MCP-UI project and OpenAI's Apps SDK, and was developed with both. As an extension it sits alongside the core spec (now 2026-07-28), not inside it. It works like this:

- A tool's description includes `_meta.ui.resourceUri`, which points at a `ui://` resource.
- The host fetches the HTML and renders it in a **sandboxed iframe** that can't touch the parent page's DOM, cookies or storage. The resource's `_meta.ui.csp` controls which external origins the app may load from.
- The app talks to the host over JSON-RPC carried by `postMessage` (`ui/initialize`, plus regular `tools/call`). Its actions therefore go through the host's consent path like any tool call.

Supported hosts listed in Oct 2026 include Claude, Claude Desktop, VS Code GitHub Copilot, Microsoft 365 Copilot and Goose.

**AG-UI** is different in kind. It is not a UI spec but the **event protocol between an agent backend and a frontend**, born at CopilotKit and now an open spec at 1.0 as of Oct 2026. Its default binding is an HTTP POST carrying the run input, answered by an SSE stream. It defines eight event families:

- run lifecycle (`RUN_STARTED`, `RUN_FINISHED`, `RUN_ERROR`)
- text (`TEXT_MESSAGE_START`/`_CONTENT`/`_END`)
- tool calls (`TOOL_CALL_*`)
- reasoning
- state snapshots and JSON-Patch deltas
- activity
- subagents
- raw and custom events

Approvals are modeled as **interrupts**: a run ends with `RUN_FINISHED` whose `outcome` is an interrupt, and the next run carries the answers in its `resume` list. AG-UI can carry A2UI or MCP-UI payloads. It is the standardized version of the hand-rolled event stream in the snippet above, and standardizing it turns N agent backends × M frontends into N+M (P11).

**Validate before rendering.** Model-emitted UI is untrusted output (P9), and the renderer is your code (P6). Structured outputs ([§06](06-structured-outputs.md)) can force the JSON *shape*. The semantic rules are still yours: which components exist, which actions are allowed, and size limits.

```python
import json
from dataclasses import dataclass

# The catalog: the ONLY components the model may emit, each rendered by YOUR code.
CATALOG = {
    "card":   {"required": {"title", "children"}},
    "table":  {"required": {"columns", "rows"}, "max_rows": 50},
    "button": {"required": {"label", "action"}},
}
ALLOWED_ACTIONS = {"open_run", "rerun_job"}   # each maps to a tool behind the normal permission check
@dataclass
class Node:
    type: str
    props: dict

def validate(raw: dict, depth: int = 0) -> Node:
    kind, props = raw.get("type"), raw.get("props", {})
    spec = CATALOG.get(kind)
    if spec is None or depth > 3:
        raise ValueError(f"unknown component {kind!r} or tree too deep")   # no raw HTML, ever
    if missing := spec["required"] - props.keys():
        raise ValueError(f"{kind} missing {sorted(missing)}")
    if kind == "table" and len(props["rows"]) > spec["max_rows"]:
        raise ValueError("too many rows: paginate instead")
    if kind == "button":
        action = props["action"]
        if not isinstance(action, dict) or action.get("name") not in ALLOWED_ACTIONS:
            raise ValueError(f"action {action!r} is not allowed")
    if kind == "card":
        props = {**props, "children": [validate(c, depth + 1) for c in props["children"]]}
    return Node(kind, props)

emitted = json.loads("""{"type": "card", "props": {"title": "Failed runs", "children": [
  {"type": "table", "props": {"columns": ["job", "error"], "rows": [["nightly_orders", "timeout"]]}},
  {"type": "button", "props": {"label": "Rerun", "action": {"name": "drop_table", "args": {}}}}]}}""")
try:
    tree = validate(emitted)
    print("render:", tree.type, [child.type for child in tree.props["children"]])
except ValueError as err:
    print("fall back to plain text:", err)        # an invalid spec is never half-rendered
```

Run it and it falls back to plain text, because a prompt-injected document talked the model into a `drop_table` button. Three more rules apply:

- **Escape every string prop at render time.** A title is text, never markup.
- **Clicked actions are tool calls.** They go through the same authorization and approval path as any other call, because a button is just a pre-filled proposal (P6).
- **Never let generated UI imitate system chrome.** A widget styled like your approval dialog is a spoofing attack.

**When not to use generative UI.** Don't use it when text is enough. Don't use it when users need a stable layout they can learn: P4 applies to UI, and a dashboard that rearranges itself on every answer can't be learned. And don't use it when you can't make the generated components accessible.

### Chat, embedded and ambient interfaces

There are three placements, each with a different trade-off:

- **Chat** is maximally flexible and suffers from the blank-box problem: users don't know what to ask, or what the system can do.
- **Embedded** (copilot) features live inside an existing workflow: "explain this query" next to the SQL editor, inline suggestions, a summarize button on a ticket. Context comes for free, the scope is narrow, and verification is natural because the user is already looking at the artifact.
- **Ambient** agents are triggered by events rather than messages and run in the background. Their natural UI is an inbox of notifications, questions and reviews rather than a conversation.

Most mature products mix all three. Embedded features cover the frequent narrow tasks, chat covers the long tail, and ambient agents cover the work nobody wants to trigger by hand.

### Accessibility

- **Streaming and screen readers conflict.** Updating an ARIA live region on every token makes a screen reader chatter or re-read the whole text. Announce at sentence or paragraph boundaries, or on completion. Expose status messages ("Searching 3 sources…") in a way assistive tech can announce without moving focus (WCAG 2.2, SC 4.1.3 Status Messages).
- **Controls must be operable without a mouse.** That includes stop, approve and deny.
- **Use a component catalog over raw HTML,** partly because catalog components can be built accessible once and reused.
- **Respect reduced-motion preferences** for typing animations.
- **AI disclosures themselves must be accessible.** The EU AI Act requires it (Art. 50(5)).

### Anthropomorphism and over-trust

Fluent first-person text triggers social responses: people attribute understanding, intent and reliability to something that sounds like a competent colleague. NIST's Generative AI Profile lists this as a named risk, "Human-AI Configuration": anthropomorphizing, automation bias, over-reliance and emotional entanglement. It even notes that the word "hallucination" anthropomorphizes. The EU AI Act names automation bias in its human-oversight article ([§34](34-governance-regulation.md)).

Design against it:

- **Disclose that it is an AI.** This is required in the EU (Art. 50(1)) and, for companion chatbots, in California (SB 243, **⚠ verify**).
- **Avoid fake human cues.** Human names and photos for bots, or typing delays added to seem human, push users the wrong way.
- **Don't let the assistant claim feelings or memories it doesn't have.** Show what it actually remembers ([§17](17-memory.md)).
- **Make friction proportional to stakes.** A one-click accept is fine for an autocomplete and wrong for a payment.

The opposite failure, **algorithm aversion** (rejecting the system after one visible mistake), is also real. The goal is calibration, not distrust.

### Onboarding and expectation setting

The first minutes decide the user's mental model. Microsoft's guidelines for human-AI interaction (Amershi et al., CHI 2019) open with "make clear what the system can do" and "make clear how well the system can do what it can do." In practice:

- give example tasks instead of an empty box
- state limits plainly ("I can read your project's tables, not production")
- say what data is used and remembered
- give agents time and cost expectations up front
- grant autonomy progressively rather than all at once

Unmet expectations turn into distrust faster than modest promises that are kept.

### Failure modes

| Failure | Mechanism | Fix |
|---|---|---|
| Spinner of death | No streaming; reasoning shown as silence | Stream; show thinking summaries or activity |
| Approval fatigue | Prompts on every action | Sandbox boundaries; risk-based gating; undo |
| Hidden arguments | Approval card truncates tool args | Show full args and a preview |
| Confident wrong answer | P4 plus fluent text | Citations, diffs, "not found" as a valid answer |
| Unjoinable feedback | Thumbs not tied to traces | Log feedback with trace IDs |
| UI injection or spoofing | Rendering model-authored markup | Catalog validation, escaping, sandboxed iframes |
| Chattering screen reader | Per-token live-region updates | Announce at boundaries |
| Over-trust | Human-like persona, no evidence | Disclose, show sources, proportional friction |

## Comparison

| Interface | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Chat | Open text box, streamed replies | Handles the long tail | Blank-box problem; verification is on the user | Exploratory, varied requests |
| Embedded copilot | AI inside an existing tool, on its artifacts | Context is free; easy to verify in place | Narrow; one feature per job | Frequent, well-defined tasks |
| Ambient agent | Event-triggered, runs in the background, reports to an inbox | Scales the user; no prompting | Hard to see and steer; needs strong HITL | Recurring work nobody wants to trigger |

| Generative UI approach | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Tool-bound components | Each tool has a fixed widget | Predictable, accessible, simple | Inflexible | Most production features |
| Declarative catalog (ChatKit widgets, A2UI) | Model emits a component tree; app validates and renders | Flexible within safe bounds | You maintain the catalog and validator | Varied answers needing structure |
| Sandboxed HTML (MCP Apps) | Server ships an HTML app into a sandboxed iframe | Full interactivity; third-party UIs | Heavier; less visual consistency; host support varies | Rich tools: maps, editors, dashboards |
| Event protocol (AG-UI) | Standard agent↔frontend event stream over SSE | Swap backends and frontends (N+M) | Another layer; carries UI, doesn't define it | Multiple agent backends or UI clients |

## What it didn't solve

Good AI UX makes a system checkable, correctable and appropriately trusted. It can't tell you whether the system should exist. A beautifully streamed, cited, approval-gated agent can still automate a task nobody needed automated, cost more than the human it assists, or fail on the one case that matters to the business. Which problems are worth building at all, and how do you tell before you've built them? → Next: [§36 AI Product Thinking](36-product-thinking.md)

## Check your understanding

**Q: Why does streaming make a response feel faster when the total generation time is unchanged?**

Decode is sequential, so tokens are produced one at a time anyway (P10). Streaming shows each one as it arrives, so perceived latency drops to time-to-first-token and the user reads while the model writes. The tradeoff is that you can't retract text already shown, and partial JSON or Markdown is invalid until the end. Buffer instead when an output must pass a check before anyone sees it.

**Q: What would happen if every tool call an agent makes required human approval?**

Users would get approval fatigue: after dozens of prompts they stop reading and click yes, so the approval looks like oversight and provides none. Anthropic found that sandboxing cut Claude Code's permission prompts by 84% by drawing the boundary once. Gate by risk instead: reads run freely, reversible writes run with undo, and only irreversible or external actions ask, with full arguments and a preview.

**Q: Citations vs "trust me": what does an API citation guarantee, and what doesn't it?**

Anthropic's citations guarantee valid pointers: `cited_text` really exists at that location in the documents you supplied. They don't guarantee that the quote supports the claim next to it, or that the documents are right. Their value is that they make checking cheap, one click to the source span, which is what turns verification from a burden into a habit (P8).

**Q: Why validate a model-emitted UI spec even when structured outputs guarantee the JSON matches your schema?**

A schema guarantees shape, not meaning. A well-formed button can still trigger `drop_table` because injected text steered the model (P9), and a valid table can still have 10,000 rows. The renderer and action handlers are your code (P6), so they enforce the catalog, the allowed actions, size limits and escaping, and they send every clicked action through normal authorization.

**Q: MCP Apps vs a declarative component catalog: when would you pick each?**

A catalog (ChatKit widgets, A2UI) keeps the model inside components you built, which makes it consistent, accessible and easy to secure, but it is only as expressive as the catalog. MCP Apps lets a server ship a full interactive HTML app, such as a map, an editor or a live dashboard, isolated in a sandboxed iframe whose actions still pass the host's consent path. Use a catalog for structured answers in your own product, and MCP Apps when a third-party tool needs rich interactivity across many hosts.

**Q: Thumbs vs edits: which feedback signal is more useful, and why?**

Edits, usually. Thumbs are sparse and skewed toward extreme reactions, while the diff between the AI's draft and what the user actually sent shows exactly what was wrong, on nearly every interaction, with no extra effort from the user. Either signal is worthless if it can't be joined to the trace that produced the response, so log feedback with trace IDs and turn the patterns into eval cases.

**Q: Why can a friendlier, more human-like assistant produce worse outcomes?**

Human cues (names, faces, emotional language, simulated typing) trigger social trust, so users over-rely on fluent output and check it less. That is automation bias, which NIST and the EU AI Act both name. Because outputs are probabilistic (P4), unchecked reliance means unchecked errors. Disclose that it is an AI, show evidence, and keep friction proportional to stakes. Warmth is fine when it doesn't stand in for reliability.

## Takeaways

- AI UX is designing for outputs that vary, are slow and can act: aim for calibrated trust, not maximal trust.
- Stream to cut perceived latency to TTFT. Handle unknown events, mid-stream errors, silent thinking and a real stop button.
- Make verification cheaper than redoing the work: citations to the exact span, diffs, previews, undo, and "not found" as an answer.
- Ask rarely and meaningfully. Approval fatigue turns oversight into theater, while sandboxes, risk-based gating and undo reduce prompts.
- Join every feedback event to its trace. Edits beat thumbs.
- Generative UI ranges from tool-bound widgets through declarative catalogs (ChatKit, A2UI) to sandboxed apps (MCP Apps). AG-UI is the event protocol that carries them.
- Validate model-emitted UI against a catalog and route its actions through normal authorization (P6, P9).
- Disclose that it is an AI, avoid fake human cues, and design for accessibility from the start.

## Sources

- Anthropic, Streaming Messages (SSE event types): https://platform.claude.com/docs/en/build-with-claude/streaming
- Anthropic, Citations: https://platform.claude.com/docs/en/build-with-claude/citations
- Anthropic, "Beyond permission prompts: making Claude Code more secure and autonomous" (Oct 20, 2025): https://www.anthropic.com/engineering/claude-code-sandboxing
- Model Context Protocol, MCP Apps overview: https://modelcontextprotocol.io/extensions/apps/overview
- MCP Blog, "MCP Apps - Bringing UI Capabilities To MCP Clients" (Jan 26, 2026): https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/
- Model Context Protocol, Extensions overview (official extensions incl. MCP Apps and Tasks): https://modelcontextprotocol.io/extensions/overview
- AG-UI documentation, introduction: https://docs.ag-ui.com/introduction
- AG-UI specification 1.0, event streams: https://docs.ag-ui.com/spec/1.0/events/index.md
- AG-UI specification 1.0, interrupts and resume: https://docs.ag-ui.com/spec/1.0/basic/patterns/interrupt-resume.md
- AG-UI specification 1.0, HTTP + SSE binding: https://docs.ag-ui.com/spec/1.0/basic/transports/http-sse.md
- A2UI, "A Protocol for Agent-Driven Interfaces": https://a2ui.org/
- OpenAI, ChatKit: https://developers.openai.com/api/docs/guides/chatkit
- OpenAI, ChatKit widgets: https://developers.openai.com/api/docs/guides/chatkit-widgets
- Vercel, "Introducing AI SDK 3.0 with Generative UI support" (Mar 1, 2024): https://vercel.com/blog/ai-sdk-3-generative-ui
- LangChain, "Introducing ambient agents" (Harrison Chase, Jan 14, 2025): https://blog.langchain.com/introducing-ambient-agents/
- Feng, McDonald & Zhang, "Levels of Autonomy for AI Agents" (Jun 2025): https://arxiv.org/abs/2506.12469
- Amershi et al., "Guidelines for Human-AI Interaction" (CHI 2019): https://doi.org/10.1145/3290605.3300233
- Google PAIR, People + AI Guidebook: https://pair.withgoogle.com/guidebook/
- NIST AI 600-1, Generative AI Profile ("Human-AI Configuration"): https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- EU AI Act, Article 50 (transparency) and Article 14 (human oversight), AI Act Explorer (secondary, consolidated text): https://artificialintelligenceact.eu/article/50/
- W3C, Web Content Accessibility Guidelines (WCAG) 2.2: https://www.w3.org/TR/WCAG22/
