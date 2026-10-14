# 24. Computer-Use, Browser, and Deep-Research Agents

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This is Part 6, the agent archetypes, covering 2024–2026. Coding agents ([§23](23-coding-agents.md)) work as well as they do partly because code comes with built-in verifiers: compilers, type checkers and tests hand the loop ground truth at every step (P8). GUIs and the open web have nothing like that. This section covers three archetypes that work where verification is weak. **Computer-use agents** drive a desktop through screenshots and clicks (Anthropic, Oct 2024; OpenAI's Operator, Jan 2025). **Browser agents** drive web pages. **Deep-research agents** search and read the web and write a cited report (Google, Dec 2024; OpenAI, Feb 2025; Anthropic, Apr 2025). All three are the agent loop of [§11](11-agents.md) with an unusual tool surface.

## Why this exists

**Most software has no API you can call.** Legacy desktop apps, internal admin screens and vendor portals often expose nothing but a screen. The pre-LLM answer was **RPA** (robotic process automation): scripts recorded against screen positions or UI selectors, which break whenever the layout changes. Every application has a graphical user interface (**GUI**), because humans need one. An agent that reads pixels and emits clicks gets a universal adapter, and pays for it.

**Some questions need many searches.** RAG ([§09](09-rag.md)) retrieves once. An analyst instead searches, reads, notices a gap, and searches again. On OpenAI's BrowseComp benchmark (Apr 2025), giving GPT-4o browsing raised its score from 0.6% to only 1.9%, while the Deep Research agent solved 51.5%. The paper concludes that "browsing alone is not sufficient."

**From first principles,** the model only emits text (P1). To use a computer, it emits text that encodes an action, such as `left_click` at `[512, 742]`. The harness performs the action and returns the new screen as image tokens (P2, P6). The cost, latency, fragility and injection risk all follow from that.

## How it works (under the hood)

### The screenshot → action loop

```text
 task ──▶ model ── tool_use: left_click [512,742] ──▶ harness ── xdotool ──▶ VM display
            ▲         (coordinates are text tokens)                              │
            └──── tool_result: screenshot (PNG → ~1,200–2,700 visual tokens) ◀───┘
     repeat until end_turn, a step/cost budget, or a human stops it
```

Each step captures the screen, prefills the growing context, decodes an action, executes it, waits for the UI to settle, and captures again. Anthropic's Oct 2024 post names the hard part: Claude "counts how many pixels vertically or horizontally it needs to move a cursor," and "training Claude to count pixels accurately was critical." Mapping a description such as "the blue Submit button" to a screen location is called **GUI grounding**. The post also names a structural limit, the "flipbook" view. The model sees discrete screenshots rather than video, so it "can miss short-lived actions or notifications." The capability launched as a public beta, "at times cumbersome and error-prone."

### The tool shape (Anthropic, Oct 2026)

On the Claude API and Google Cloud, computer use is the **`computer_toolset_20260801`** client toolset **(GA)**: one entry, `{"type": "computer_toolset_20260801"}`, with no beta header, no `name` and no display size. Anthropic trains the schema, and your application executes every call ([§10](10-tool-use.md)). The toolset has 17 member tools, including `screenshot`, `zoom`, `left_click`, `left_click_drag`, `scroll`, `type`, `key` and `wait`.

- **The member is the block's `name`.** Each call is a `tool_use` block carrying `"toolset_name": "computer"`, and every `tool_result` must echo it. Only `screenshot` and `zoom` need an image back; `OK` covers the rest.
- **Batch actions.** One turn can hold click, type and screenshot together. You run them in order and stop at the first failure. Each later block gets `is_error: true` with the exact text `"Not executed: an earlier computer action in this turn failed."`
- **Coordinates are screenshot pixels.** The API doesn't downscale toolset images, so you resize screenshots to fit the image limits and scale returned coordinates back up.
- **Versions.** The earlier `computer_20251124` (beta header `computer-use-2025-11-24`) still serves older models and Amazon Bedrock. Claude 5.5 models on the Claude API reject it with a 400.

OpenAI's Responses API `computer` tool (with GPT-5.4, Mar 5, 2026, after the Mar 2025 `computer-use-preview`) returns a `computer_call` with an ordered `actions` array. You answer it with a `computer_call_output` screenshot. For its newest model, OpenAI's guide now recommends a code-execution tool instead, where the model writes PyAutoGUI or Playwright scripts that perform many actions per call. That is code-as-action from [§10](10-tool-use.md). Operator, OpenAI's Jan 2025 consumer agent, was folded into ChatGPT agent in Jul 2025 **(⚠ verify)**.

### A stub screenshot-act loop

The stub model replays one batch in the toolset's shape. The control flow is what matters: run the batch in order, approve consequential actions per block, halt the batch on failure, scale coordinates, and cap the steps.

```python
import base64
SCREEN_W, SHOT_W = 1920, 1280       # real display width vs the screenshot width we send
HALT = "Not executed: an earlier computer action in this turn failed."
CONSEQUENTIAL = {"key"}             # e.g. Enter on a payment form: a human approves first
def tu(i, name, inp):               # one member call, in the toolset's tool_use shape
    return {"type": "tool_use", "id": i, "name": name, "toolset_name": "computer", "input": inp}
SCRIPT = [{"stop_reason": "tool_use", "content": [tu("t1", "left_click", {"coordinate": [640, 60]}),
           tu("t2", "type", {"text": "Q3 invoices"}), tu("t3", "screenshot", {})]},
          {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Found 14 invoices."}]}]
# Live: client.messages.create(model=..., tools=[{"type": "computer_toolset_20260801"}], ...)
def call_model(messages):           # stub: replay the script, one reply per assistant turn
    return SCRIPT[sum(m["role"] == "assistant" for m in messages)]
def vm(name, inp):  # stub driver for a sandboxed VM (xdotool, Playwright...), never your laptop (P6)
    if "coordinate" in inp:
        x, y = (round(v * SCREEN_W / SHOT_W) for v in inp["coordinate"])  # back to real pixels
    if name not in ("screenshot", "zoom"):
        return "OK"
    png = b"\x89PNG..."                        # capture the display, resize to SHOT_W wide
    return [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                         "data": base64.b64encode(png).decode()}}]

def run(task, max_steps=40, approve=lambda block: False):
    messages = [{"role": "user", "content": task}]
    for _ in range(max_steps):                    # step budget: every step costs image tokens
        resp = call_model(messages)
        if resp["stop_reason"] != "tool_use":
            return resp        # the model *claims* success; check the end state out of band (P8)
        messages.append({"role": "assistant", "content": resp["content"]})
        results, failed = [], False
        for b in (b for b in resp["content"] if b["type"] == "tool_use"):   # a batch: IN ORDER
            r = {"type": "tool_result", "tool_use_id": b["id"], "toolset_name": "computer"}
            try:
                if failed or (b["name"] in CONSEQUENTIAL and not approve(b)):  # gate each block
                    raise RuntimeError(HALT if failed else "Denied by user.")
                r["content"] = vm(b["name"], b["input"])
            except Exception as e:                # halt the rest of the batch, tell the model why
                r.update(is_error=True, content=str(e)); failed = True
            results.append(r)
        messages.append({"role": "user", "content": results})   # one result per tool_use block
    raise RuntimeError("step budget exhausted")
print(run("Find the Q3 invoices in the accounting app.")["content"][0]["text"])
```

The approval runs before *each block*, because one batch can fill, submit and confirm a form within a single turn.

### Why it's slow and expensive (P10)

Every observation is an image, and every image stays in context. Under Anthropic's 28×28-pixel patch rule ([§07](07-multimodal.md)), a 1280×720 screenshot costs ⌈1280/28⌉ × ⌈720/28⌉ = 46 × 26 = 1,196 visual tokens, and a 1080p one costs 2,691. Declaring the toolset adds about 4,500 tokens to every request.

The model is stateless (P2), so step *k* resends all *k* earlier screenshots. As an illustration, take a 50-step run that keeps every 1,200-token screenshot. It sends Σ(4,500 + 1,200·k) ≈ 1.76 million input tokens. On Claude Sonnet 5.5 that costs about $3.50 uncached at $2 per million, and roughly $0.50 when most of it is cache hits at $0.20. An API call returning 200 tokens of JSON is a rounding error by comparison.

Latency is worse. Each step is a model round trip plus the action plus a render wait, so a click a person makes in under a second takes the agent seconds. Anthropic's limitations list advises: focus "on use cases where speed isn't critical."

The levers:

- **Batch actions,** to cut round trips.
- **Lower resolution plus `zoom`,** to keep detail affordable.
- **Cache breakpoints, and pruning old screenshots in batches,** so the prefix stays stable. On Claude 5.5 models, removing a screenshot client-side invalidates later thinking blocks, so the docs recommend server-side tool-result clearing ([§16](16-context-engineering.md)).
- **Page structure instead of pixels** wherever a page offers it (below).

### Reliability (P8)

The docs list failures that an API never has:

- **Grounding misses.** Clicks are consistently offset when coordinates are applied to a screen of a different size (or a 2× Retina display), targets are too small after downscaling, or elements look alike.
- **Assumed outcomes.** Claude "sometimes assumes outcomes of its actions without explicitly checking their results." The suggested fix is a prompt to screenshot and evaluate each step.
- **Timing.** A page that hasn't loaded, or a toast that vanishes between screenshots.
- **Awkward widgets.** Dropdowns, scrollbars and spreadsheet cells; keyboard shortcuts are more reliable.

Errors then compound: 50 steps at 98% each succeed end to end 0.98⁵⁰ ≈ 36% of the time. And there is no built-in verifier. "Did the form submit?" gets judged from a screenshot by the same model that clicked, so the maker is the checker. Verify **out of band**: query the system of record for the end state, use a separate checker, or have a human approve. The benchmarks show how far there was to go. On OSWorld (Apr 2024, 369 desktop tasks), humans completed over 72%, and the best model 12.24%. On WebArena (Jul 2023), a GPT-4 agent reached 14.41% against 78.24% for humans. Scores have risen a lot since, so check current leaderboards rather than trusting a frozen number (P12).

### Sandboxed VMs (P6)

Anthropic's reference implementation runs in a Docker container with a virtual X11 display (Xvfb), a light desktop, Firefox and LibreOffice. Its precautions are [§20](20-agent-runtime.md)'s sandbox rules applied to a desktop:

- a dedicated VM with minimal privileges
- no credentials or sensitive data inside it
- a domain allowlist
- human confirmation for anything with real-world consequences, including accepting cookies, making payments or agreeing to terms

Snapshot the VM before each run, so that a bad trajectory rolls back to a checkpoint.

### Injection via on-screen content (P9)

Every pixel is input, and input can act as an instruction. Anthropic's Claude in Chrome pilot (Aug 2025) ran 123 attack cases across 29 scenarios. Without mitigations, 23.6% of the attacks succeeded. One malicious email posing as "the security team" got Claude to delete the user's emails without confirmation. Mitigations cut the rate to 11.2%, so roughly one targeted attack in nine still worked. Vendors now run classifiers over screenshots that steer the model to check with the user before acting. Anthropic says its precautions "remain important even with these classifiers in place." The real control is least privilege: a fresh profile with no credentials, a network allowlist, and confirmation at the moment of each consequential action ([§32](32-security-guardrails.md)).

### Browser agents: page structure vs pixels

A browser exposes more than pixels:

- **The DOM** (Document Object Model) is the element tree the browser builds from HTML and JavaScript.
- **The accessibility tree** is the semantic view that screen readers use: each element's role, name and state, such as `button "Search"`.

Reading a tree gives the agent text instead of an image. A tree read "often costs fewer input tokens than a screenshot," names exact targets, and survives layout shifts. It is blind to content the tree doesn't describe: canvas apps, video, remote desktops, cross-origin iframes and pages with poor markup. Raw DOM also carries text that users never see, which is a hiding place for injections, so read from what the page renders. Pixels work on any page and show the real layout, at a higher token cost and with fragile coordinates. **Set-of-Mark** prompting (Oct 2023) is a hybrid: it overlays numbered marks on a screenshot so the model can say "click 7."

The tooling as of Oct 2026:

- **Anthropic's `browser_toolset_20260801`** **(GA, Claude API and Google Cloud)** has 27 default members, plus `javascript_exec`, `file_upload` and two diagnostics members that stay off until enabled. `read_page` returns the accessibility tree with references such as `[ref_2]`, and a click target is either `{"type": "ref", ...}` or a viewport coordinate. Your executor maps references to real nodes and refuses any URL scheme other than http(s).
- **Playwright** is Microsoft's browser automation library. **Playwright MCP** drives it "through structured accessibility snapshots, bypassing the need for screenshots." Its README now steers coding agents to a CLI with skills, because that avoids "large tool schemas and verbose accessibility trees" ([§18](18-skills.md)).
- **browser-use** is an MIT-licensed library that drives Chromium over **CDP** (Chrome DevTools Protocol, the browser's remote-control interface), processes the HTML, and loops a model of your choice.
- **Agentic browsers** put the agent inside your everyday browser, logged-in sessions included. Examples are Perplexity's Comet **(⚠ verify)**, Claude in Chrome (piloted Aug 2025, beta for all Max subscribers from Nov 24, 2025), and Gemini in Chrome's auto browse **(Preview, ⚠ verify)**. The category is volatile: OpenAI's ChatGPT Atlas launched in Oct 2025 and stopped working on Aug 9, 2026, with its features moved into the ChatGPT app **(⚠ verify)**. An agentic browser is the worst case for P9, combining your real cookies, untrusted pages and the power to act. That is the lethal trifecta.

### Deep-research agents

A **deep-research agent** answers a question by running a long search-and-read loop and writing a report with citations.

- **Gemini Deep Research** (Dec 11, 2024) first proposes "a multi-step research plan for you to either revise or approve." Developers reach it as a **(Preview)** agent in Google's Interactions API, in background mode only.
- **OpenAI deep research** (Feb 2025) ran on "an early version of OpenAI o3 that is optimized for web browsing." In ChatGPT, a smaller model asks clarifying questions and rewrites the prompt first. The dedicated API models shut down on Jul 23, 2026, and OpenAI now points developers to general models with web search. The specialized model was absorbed into general ones (P12).
- **Anthropic Research** (Apr 15, 2025) uses a lead agent with parallel search subagents. [§13](13-multi-agent.md) has the numbers: a 90.2% gain over a single agent, about 15× the tokens of chat, and token usage explaining 80% of BrowseComp variance.

```text
question ─▶ (clarify / plan) ─▶ lead agent ──fan out──▶ subagent 1 … subagent N   (own contexts)
                                    ▲                    search → read → reflect → (repeat)
                                    │                         │ condensed findings + source ids
                                    └── reflect: gaps? ◀──────┘
                                        enough? ─▶ synthesize ─▶ attach + check citations ─▶ report
```

**Search → read → reflect** is the inner loop. Anthropic found that agents default to "overly long, specific queries that return few results," and prompted them to start broad and then narrow. *Reading* means fetching and filtering: Claude's newer web search versions can run code that filters results before they enter the context (P3). *Reflecting* means thinking between tool calls about quality, gaps and the next query. The lead stops on a coverage judgment or a budget.

**Citations** are attached in one of two ways. Either the writer cites as it goes, or a separate pass attributes claims afterwards. Claude's web search citations are "always enabled" and carry the URL plus up to 150 characters of `cited_text`. Anthropic's research system hands the finished report to a separate CitationAgent. Either way, part of the check is computational: does the quoted span appear in a document the agent actually fetched? Whether the span *supports* the claim is a judgment for an LLM judge.

**Hallucinated citations** are the signature failure. A next-token predictor knows from its weights what a citation looks like (P1, P5), so it can emit a plausible URL or title it never retrieved. The structural fix is to accept citations only to document IDs the harness fetched. Vendors restrict URLs for security reasons too. Claude's web fetch "can only fetch URLs that have previously appeared in the conversation." OpenAI's deep research is not allowed "to navigate to or construct arbitrary URLs," so an injected page can't leak an API key through a URL parameter.

**Evaluation.** BrowseComp's 1,266 questions are "inverted": the authors start from a fact and write a question whose short answer is "hard to find but easy to verify." Human trainers solved 29.2% of the ones they attempted, usually giving up only after about two hours. Browsing models were also *worse calibrated*, meaning confident when wrong. BrowseComp measures persistence, not report quality. For reports, Anthropic used a rubric judge covering factual accuracy, citation accuracy, completeness, source quality and tool efficiency, and started with about 20 real queries. Human testers still caught what the judge missed: early agents "consistently chose SEO-optimized content farms over authoritative but less highly-ranked sources" ([§26](26-evals.md)).

**Failure modes:**

- poor sources, stale pages, and the first results page standing in for the field
- real sources cited for claims they don't make
- contradictions flattened into one confident sentence
- injection, which OpenAI's system card splits into wrong answers and data exfiltration
- cost, which OpenAI's guide controls mainly with `max_tool_calls`, "the primary tool available to you to constrain cost and latency," plus background mode and webhooks ([§20](20-agent-runtime.md))

### A research orchestrator outline

```python
import asyncio

# Stubs so the control flow runs offline. Live: the lead and the subagents are model calls
# (e.g. claude-sonnet-5-5) with web_search / web_fetch server tools.
async def plan(question, notes):          # lead: decompose; [] means "enough evidence"
    return [] if notes else ["export rules for AI chips 2026", "HBM memory supply 2026"]

async def search(q):                       # returns {doc_id: fetched text}
    return {f"doc:{q[:6]}": f"Report on {q}: the key fact, with numbers."}

async def reflect(q, docs):                # subagent: extract claims tied to exact source spans
    return [{"claim": f"Finding about {q}", "doc_id": d, "quote": t[:30]} for d, t in docs.items()]

async def subagent(q, max_rounds=3):       # search -> read -> reflect, in its own context (P3)
    findings, sources = [], {}
    for _ in range(max_rounds):
        docs = await search(q)
        sources.update(docs)
        findings += await reflect(q, docs)
        if findings:                       # stub stop rule; real subagents judge coverage
            break
    return findings, sources               # condensed: the lead never sees raw pages

async def research(question, max_rounds=3):
    notes, sources = [], {}
    for _ in range(max_rounds):            # lead loop: plan -> fan out -> reflect
        subqs = await plan(question, notes)
        if not subqs:
            break
        for f, s in await asyncio.gather(*(subagent(q) for q in subqs)):  # parallel (§13)
            notes, sources = notes + f, {**sources, **s}
    # Computational citation check: the quote must appear in a document we actually fetched.
    cited = [n for n in notes if n["quote"] in sources.get(n["doc_id"], "")]
    return {"report": [n["claim"] for n in cited], "citations": cited,
            "dropped_unsupported": len(notes) - len(cited)}

print(asyncio.run(research("What constrains AI chip supply in 2026?")))
```

A real orchestrator adds budgets for tool calls, tokens and wall-clock time, plus briefs that give each subagent an objective, an output format and boundaries ([§13](13-multi-agent.md)). It also adds an inferential check that each quote supports its claim.

### When to use a GUI agent instead of an API or MCP

**Use an API whenever one exists.** A typed call is deterministic, costs hundreds of tokens instead of thousands, is permissioned per operation (P9), and fails with machine-readable errors (P8). Scraping numbers off a BI dashboard when you have warehouse credentials is the same mistake. The ladder:

1. **Is there an API, SDK, database or MCP server?** Use it ([§10](10-tool-use.md), [§15](15-protocols-mcp-a2a.md)). If one endpoint is missing, a small MCP server usually costs less over its lifetime than a GUI agent.
2. **Do you only need to read public pages?** Use web search and fetch, or plain HTTP and a parser.
3. **Must the agent act inside web pages?** Use a browser agent: the tree first, pixels as the fallback.
4. **Is a desktop GUI the only interface?** Use computer use in a sandboxed VM.
5. **Is the flow fixed and repeated?** Have the agent *write* a Playwright or RPA script once, review it, and run the script as a workflow (P7). Keep the agent for exceptions and for rewriting the script when the UI changes.

At every rung, put human approval on irreversible actions. High volume pushes you toward an API or a script, and an interactive latency budget rules computer use out entirely.

## Comparison

| Interface | How it works | Strength | Weakness | When to choose |
|---|---|---|---|---|
| API / MCP tool | Typed call, JSON result | Cheap, fast, deterministic, least privilege | Someone must build it | Whenever it exists |
| Browser, accessibility tree | Reads roles and names; acts on element references | Few tokens, robust targets | Blind on canvas, video, iframes, poor markup | Web tasks on well-built pages |
| Browser, pixels | Screenshots plus viewport coordinates | Any page; sees the layout | Image tokens, fragile coordinates | Visual pages; fallback for the tree |
| Computer use | Screenshots plus OS mouse and keyboard in a VM | Any GUI at all | Slowest, costliest, widest injection surface | Desktop apps with no API |
| Agent-authored script | The agent writes Playwright/RPA code once; code runs it | Fast, cheap, reviewable | Breaks when the UI changes (re-author it) | Fixed, high-volume flows |

| Research design | How it works | Strength | Weakness | When to choose |
|---|---|---|---|---|
| Single-shot RAG or search | One retrieval, one answer | Cheap, fast | Can't follow leads | Lookups with an obvious query ([§09](09-rag.md)) |
| Single-agent research loop | One context: search → read → reflect | Coherent; cheaper | Context fills on broad topics | Narrow or sequential questions |
| Orchestrator + parallel subagents | Lead plans; subagents search in separate contexts | Breadth, speed, more useful tokens | About 15× chat tokens; lossy summaries | Broad questions that split apart ([§13](13-multi-agent.md)) |

## What it didn't solve

Everything here is text and screens. An agent can take seconds per step, or minutes per report, and the user mostly doesn't mind, because they are waiting for a result rather than holding a conversation. Real-time speech adds a latency budget that no text agent has. People expect a reply within a few hundred milliseconds, and a voice agent has to listen, think and speak inside that window while being interrupted. → Next: [§25 Voice and Realtime Agents](25-voice-agents.md)

## Check your understanding

**Q: Why is one computer-use step so much slower and more expensive than one API tool call?**

The observation is an image of about 1,000–2,700 visual tokens instead of a few hundred tokens of JSON. Because the model is stateless, every earlier screenshot is also resent on every later step (P2, P10). Each step waits on a full model round trip, the action and a UI render. Batching, caching and lower resolution help, but if an API exists, the real fix is not to use computer use at all.

**Q: What would happen if you downscaled screenshots from 1920 to 1280 pixels wide but forgot to scale the returned coordinates?**

The model answers in the pixel space of the image it saw, so every click would land at two-thirds of the intended position, consistently offset toward the top left. It would miss targets or hit the wrong control, see confusing results, and burn steps retrying. Keep the scale factor and apply its inverse to every coordinate before executing.

**Q: Accessibility tree vs screenshots: when should a browser agent use each?**

The tree is text: cheaper, with exact element references that survive layout shifts, so read it first on well-built pages. Screenshots are needed when the tree doesn't describe the content (canvas, video, cross-origin iframes, poor markup) or when visual layout matters. The tradeoff is coverage against cost and coordinate fragility. Good toolsets switch between the two page by page.

**Q: Why does a computer-use agent need out-of-band verification more than a coding agent does?**

A coding agent's loop has computational checkers, tests and compilers, that report failure whatever the model believes. A GUI agent usually judges success from a screenshot read by the same model that acted. The maker is the checker, so errors compound silently over long runs (P8). Query the system of record for the end state, use a separate checker, or require human approval. Skip the extra check only for trivially reversible actions.

**Q: Why are hallucinated citations a natural failure of research agents, and what structural fix prevents them?**

The model predicts text, and from its weights it knows what citations look like, so it can produce a plausible URL or title it never retrieved (P1, P5). Telling it to "only cite real sources" is a plea, not a control. Accept only citations to document IDs the harness fetched, check in code that each quoted span appears in that document, and drop unsupported claims. A judge then checks whether each span actually supports its claim.

**Q: What would happen if a browser agent in your everyday Chrome profile opened a page with hidden instructions to email your files somewhere?**

The agent would combine private data (your sessions and files), untrusted content (the page) and the ability to act (send email): the lethal trifecta. If the model follows the injected text, the harness carries out a real exfiltration with your credentials (P9). Classifiers reduce the odds without removing them; Anthropic's pilot still saw 11.2% of attacks succeed. Run agents in a fresh profile without credentials, allowlist sites, and confirm consequential actions as they execute.

## Takeaways

- Computer use is the agent loop with screenshots as observations and coordinates as actions. It works on any GUI, and it is slow and costly because every step carries image tokens (P10).
- On the Claude API, computer use means `computer_toolset_20260801`: member tools, batches run in order, `toolset_name` on every result, coordinates in screenshot pixels.
- GUIs have no built-in verifier. Verify end states out of band, approve per block, and run in a disposable VM (P6, P8).
- Everything on screen is untrusted input. Least privilege beats classifiers (P9).
- Browser agents should read the accessibility tree first and fall back to pixels. An agentic browser running in your real profile is the riskiest setup.
- Deep research loops through plan, parallel search, read, reflect and cite. Restrict citations to fetched documents and check the quotes in code.
- Use an API or MCP whenever one exists. GUI agents are the last resort, and repeated flows should become scripts.

## Sources

- Anthropic, "Introducing computer use, a new Claude 3.5 Sonnet, and Claude 3.5 Haiku" (Oct 22, 2024): https://www.anthropic.com/news/3-5-models-and-computer-use
- Anthropic, "Developing a computer use model" (Oct 2024): https://www.anthropic.com/news/developing-computer-use
- Anthropic, Computer use tool docs (`computer_toolset_20260801`): https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool
- Anthropic, Browser use tool docs (`browser_toolset_20260801`): https://platform.claude.com/docs/en/agents-and-tools/tool-use/browser-use-tool
- Anthropic, computer-use reference implementation: https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo
- Anthropic, "Piloting Claude for Chrome" (Aug 2025; updated Nov 24, 2025): https://www.anthropic.com/news/claude-for-chrome
- Anthropic, "Claude takes research to new places" (Apr 15, 2025): https://www.anthropic.com/news/research
- Anthropic, "How we built our multi-agent research system" (Jun 13, 2025): https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic, Web search tool docs (citations): https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
- Anthropic, Web fetch tool docs (URL validation): https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool
- OpenAI, Computer use guide: https://developers.openai.com/api/docs/guides/tools-computer-use
- OpenAI, API changelog (`computer-use-preview` Mar 11, 2025; `computer` tool Mar 5, 2026): https://developers.openai.com/api/docs/changelog
- OpenAI, Deep research API guide (deprecation, `max_tool_calls`, safety): https://developers.openai.com/api/docs/guides/deep-research
- OpenAI, Deep research system card (Feb 25, 2025): https://cdn.openai.com/deep-research-system-card.pdf
- Wei et al., "BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents" (Apr 2025): https://arxiv.org/abs/2504.12516
- Google, "Try Deep Research and our new experimental model in Gemini" (Dec 11, 2024): https://blog.google/products/gemini/google-gemini-deep-research/
- Google, Gemini Deep Research agent docs: https://ai.google.dev/gemini-api/docs/deep-research
- Xie et al., "OSWorld" (Apr 2024): https://arxiv.org/abs/2404.07972
- Zhou et al., "WebArena" (Jul 2023): https://arxiv.org/abs/2307.13854
- Yang et al., "Set-of-Mark Prompting" (Oct 2023): https://arxiv.org/abs/2310.11441
- Microsoft, Playwright MCP README: https://github.com/microsoft/playwright-mcp
- browser-use repository: https://github.com/browser-use/browser-use
- Wikipedia, "OpenAI Operator" (secondary): https://en.wikipedia.org/wiki/OpenAI_Operator
- OpenAI Help Center, "Evolving Atlas into ChatGPT for browser-based agentic work" (not fetchable; ⚠ verify): https://help.openai.com/en/articles/20001371-evolving-atlas-into-chatgpt-for-browser-based-agentic-work
