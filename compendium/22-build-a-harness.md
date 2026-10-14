# 22. Build a Harness from Scratch

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This is the capstone of Parts 1–5. By 2026 every part of an agent system had a name: tool calling (2023), the agent loop (2023–2025), context engineering (2025), skills (late 2025), and harness engineering, durable runtimes and loop engineering (2026). [§21](21-loop-engineering.md) ended on the remaining problem: you have seen every piece on its own, but that isn't the same as knowing how they fit, where the seams are and which one breaks first. So now you build one. The result is [`code/mini_harness.py`](code/mini_harness.py), a single stdlib-only Python file that assembles eleven layers, runs offline against a scripted stand-in for the model, and switches to the real Messages API with one flag.

## Why this exists

Every earlier section explained one mechanism with its own snippet, from the raw request in [§05](05-api-and-prompting.md) to the loop driver in [§21](21-loop-engineering.md). Each snippet worked alone. A harness is where they meet, and the hard problems live at the meeting points:

- **Compaction vs thinking.** Compaction rewrites history, but a thinking block is valid only with the history that produced it.
- **Replay vs approvals.** The durable log replays recorded results, so a human approval has to be recorded too, or the human gets asked twice.
- **`end_turn` vs done.** The loop ends when the model says `end_turn`, which is only a claim. Something else has to decide whether the task is done.

You only meet these problems by wiring the parts together. It's like writing a 300-line toy dbt that renders the Jinja, builds the DAG and runs the models in order. Nobody uses the toy afterwards, but you come away knowing what each part of the real tool is for.

Every layer in the program exists because a principle from [§01](01-first-principles.md) requires it:

| # | Layer | What it does | Principles | Explained in |
|---|---|---|---|---|
| 1 | Model interface | A stub or a real backend, both returning Messages-shaped responses | P1, P6 | [§05](05-api-and-prompting.md) |
| 2 | Stateless call | Sends the system prompt, the tools and the full history every time | P2, P10 | [§05](05-api-and-prompting.md) |
| 3 | Tool registry | JSON-schema tools, an executor, `tool_result` with `is_error`, a workspace jail | P6, P9 | [§10](10-tool-use.md) |
| 4 | Agent loop | `while stop_reason == "tool_use"`, with turn and token caps | P7, P8 | [§11](11-agents.md) |
| 5 | Hooks | Deny calls, ask for approval, feed check results back | P6, P8, P9 | [§19](19-harness-engineering.md), [§21](21-loop-engineering.md) |
| 6 | Context management | A token estimate, and compaction past a threshold | P3, P10 | [§16](16-context-engineering.md) |
| 7 | Skills | Names and descriptions up front, bodies on demand | P2, P3, P11 | [§18](18-skills.md) |
| 8 | Memory | A progress file that outlives every context | P2 | [§17](17-memory.md) |
| 9 | Durable step log | A JSONL journal: reruns replay instead of redoing | P4, P8 | [§20](20-agent-runtime.md) |
| 10 | Tracing | Spans with timing and token usage | P4, P10 | [§27](27-observability.md) |
| 11 | Outer loop | A fresh context per iteration and a separate goal check | P2, P3, P8 | [§21](21-loop-engineering.md) |

A hype check: this is neither a framework nor production code. It is about 380 lines of code (about 490 with comments and blank lines). Production harnesses such as Claude Code, Codex and LangChain's Deep Agents are much larger, mostly because of the items under "What this toy leaves out" below. Their skeleton is the same.

## How it works (under the hood)

### Run it first

You need Python 3.9 or later and nothing else. From the repository root:

```bash
python3 compendium/code/mini_harness.py --fresh   # first run: empty workspace and journal
python3 compendium/code/mini_harness.py           # second run: replays from the journal
```

The task is tiny on purpose: create `greet.py` that prints exactly `hello, harness`, and make the check pass. The model is a **stub**, a scripted stand-in that returns responses in the exact shape of the Messages API, so the harness runs offline, free and identically every time. The script makes a deliberate mistake so that every layer has work to do. The first run prints the following (your millisecond column and workspace path will differ, and stub token counts are estimates):

```text
== iteration 1/3: fresh context, 0 note(s) on disk ==
  model   i1.t1          tool_use: load_skill(name='python-scripts')
  tool    load_skill     ok: <skill name='python-scripts'> | 1. Print exactly the expected text: same case, punctuation, spacing. | 2. Write w...
  model   i1.t2          tool_use: write_file(path='greet.py', content="print('Hello, harness!')\n")
  hook    approve        write_file('greet.py') -> yes (auto)
  tool    write_file     ok: wrote greet.py (25 bytes) | [back pressure] check FAILED: expected 'hello, harness', got 'Hello, harness!' (exit 0)
  model   i1.t3          tool_use: run_check(command='rm -rf __pycache__ && python3 greet.py')
  tool    run_check      ERROR: Blocked: 'rm -rf __pycache__ && python3 greet.py' deletes files or chains commands. Run one python3 file.
  compact 7 -> 3 msgs    ~426 -> ~301 message tokens
  model   i1.t4          tool_use: save_note(note=...)
  tool    save_note      ok: saved note to progress.md
  goal    i1             after max_turns, NOT DONE: expected 'hello, harness', got 'Hello, harness!' (exit 0)

== iteration 2/3: fresh context, 2 note(s) on disk ==
  model   i2.t1          tool_use: write_file(path='greet.py', content="print('hello, harness')\n")
  hook    approve        write_file('greet.py') -> yes (auto)
  tool    write_file     ok: wrote greet.py (24 bytes) | [back pressure] check passed: greet.py printed 'hello, harness'
  model   i2.t2          tool_use: run_check(command='python3 greet.py')
  tool    run_check      ok: exit=0 stdout='hello, harness'
  model   i2.t3          end_turn: "greet.py now prints exactly 'hello, harness' and the check passes."
  goal    i2             after end_turn, DONE: PASS: greet.py prints the required line and nothing else.

trace summary
  kind     spans replayed errors  tok in tok out       ms
  model        7        0      0    4867     293      4.0
  tool         6        0      1       0       0     59.4
  compact      1        0      0       0       0      0.1
  goal         2        0      1       0       0     39.2

result: DONE after 2 iteration(s) | steps executed 18, replayed 0 | ~5,160 of 20,000 tokens
workspace: /tmp/mini_harness/stub
```

Read it as a story. In iteration 1 the agent loads a skill and writes the wrong string, `Hello, harness!`. Back pressure reports the failure inside the write's own result. The agent tries to "clean up" with `rm -rf`, and a hook blocks it. The context crosses a deliberately tiny threshold and is compacted, the agent saves a note, and it hits the four-turn cap. The goal check fails, and the harness writes down why. Iteration 2 starts from an empty context plus the two notes on disk. The agent fixes the string, confirms it with `run_check` and claims success, and the goal check runs the file itself and asks a separate judge before printing DONE. Each trace line is one layer at work.

### The shape of the program

```text
drive()                                         layer 11: outer loop, a fresh context per iteration
 ├─ memory.read() ─▶ messages = [task + notes]        8: progress file on disk
 ├─ agent_loop()                                      4: inner loop
 │   ├─ compactor.needed()? ─▶ compact()              6: context management
 │   ├─ log.step(call_model)                      9 + 2: journaled, stateless call
 │   │     └─ StubModel | AnthropicModel              1: model interface
 │   └─ for each tool_use: log.step(hooks.run_tool)   9
 │         ├─ pre-hooks: jail, dangerous command, approval   5
 │         ├─ registry.execute() ─▶ tool_result, is_error     3  (load_skill: 7, save_note: 8)
 │         └─ post-hook: back pressure re-runs the check      5
 ├─ log.step(goal_check): check in a new process, then a judge    11
 └─ not done ─▶ memory.append(why) ─▶ next iteration
 every step ─▶ tracer.record()                       10: live trace, summary at the end
```

### Layer 1: the model interface

Both backends have one method, `create(body, step_id)`, and return the same shape:

- `content`, a list of typed blocks (`text`, `tool_use`, and on real models `thinking`)
- `stop_reason`
- `usage`

That shape is the whole contract between harness and model: tokens in, typed blocks out (P1). The model never touches a file. It can only return a `tool_use` block asking for one (P6). This is the API from [§05](05-api-and-prompting.md), seen from the harness side.

```python
class StubModel:
    """Layer 1a: a scripted stand-in that returns Messages-API-shaped responses offline.
    It looks up its reply by step id; a real model works everything out from the messages."""
    def __init__(self, script):
        self.script = script

    def create(self, body: dict, step_id: str) -> dict:
        blocks = json.loads(json.dumps(self.script.get(step_id, [text("(script exhausted)")])))
        for n, b in enumerate(blocks):
            if b["type"] == "tool_use":
                b["id"] = f"toolu_{step_id.replace('.', '_')}_{n}"
        calls_tool = any(b["type"] == "tool_use" for b in blocks)
        prompt = [body["system"], body.get("tools"), body["messages"]]
        return {"id": f"msg_stub_{step_id}", "type": "message", "role": "assistant",
                "model": body["model"], "content": blocks,
                "stop_reason": "tool_use" if calls_tool else "end_turn",
                "usage": {"input_tokens": estimate_tokens(prompt),
                          "output_tokens": estimate_tokens(blocks)}}

class AnthropicModel:
    """Layer 1b: the real backend, one HTTPS POST to the Messages API per call."""
    def __init__(self):
        base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        self.url = base.rstrip("/") + "/v1/messages"
        self.headers = {"x-api-key": os.environ["ANTHROPIC_API_KEY"],  # never hardcode keys
                        "anthropic-version": "2023-06-01", "content-type": "application/json"}

    def create(self, body: dict, step_id: str) -> dict:  # step_id: only the stub needs it
        req = urllib.request.Request(self.url, json.dumps(body).encode(), self.headers)
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:  # 4xx/5xx: show the API's own error message
            raise SystemExit(f"Messages API error {e.code}: {e.read().decode()[:500]}")
```

`StubModel` is a test double. It looks up its reply by step id (`"i1.t2"` is iteration 1, turn 2) so that a resumed run lines up with the script (layer 9); a real model needs no such thing. It estimates `usage` from the request size, so the budget and trace behave realistically. `AnthropicModel` is the real thing with no SDK: one `POST /v1/messages` through `urllib`, with the key from the environment and the pinned `anthropic-version` header. `ANTHROPIC_BASE_URL` points it at a gateway or a mock. OpenAI's Responses API has the same shape under other names: a `function_call` item whose `arguments` is a JSON *string*, answered by a `function_call_output` item ([§10](10-tool-use.md)).

### Layer 2: messages and the stateless call

```python
def call_model(model, system: str, tools: list, messages: list, step_id: str) -> dict:
    """One stateless call. The model keeps nothing between calls, so the system prompt,
    every tool definition and the WHOLE history go over the wire every time."""
    body = {"model": MODEL,
            "max_tokens": 16000,   # hard cap on output tokens, thinking included
            "system": system,      # frozen for the run: a stable, cacheable prefix
            "messages": messages}  # alternating user/assistant turns of typed blocks
    if tools:
        body["tools"] = tools      # JSON-schema definitions; tool_choice stays "auto"
    return model.create(body, step_id)  # no temperature/top_p: current models reject them

def total_input(usage: dict) -> int:  # uncached + cache-write + cache-read = true prompt size
    keys = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    return sum(usage.get(k) or 0 for k in keys)
```

The model keeps nothing between calls (P2), so every call carries the system prompt, every tool definition and the whole history, and each call's input grows turn by turn (P10, [§11](11-agents.md)). Three choices here come from earlier sections:

- **No sampling knobs.** There's no `temperature`, `top_p`, `top_k` or forced `tool_choice`, which current Claude models reject with a 400 ([§05](05-api-and-prompting.md), [§10](10-tool-use.md)).
- **A stable prefix.** The system prompt is built once and never edited, the volatile notes go in the first user message, and history is append-only, with every response block kept as returned. That's what prompt caching rewards ([§16](16-context-engineering.md)), although this toy doesn't set `cache_control`.
- **True prompt size.** `total_input` adds all three input counters, because `input_tokens` alone is only the uncached part.

### Layer 3: tools, the jail and `is_error`

`Workspace` is the directory jail. `ToolRegistry` maps each tool name to a JSON-schema definition, which the model sees, and a Python function, which actually runs.

```python
class Workspace:
    """The directory jail. Every path the model names is resolved and checked here."""
    def __init__(self, root: Path, fresh=False):
        if fresh:
            shutil.rmtree(root, ignore_errors=True)
        self.root = root.resolve()
        self.state = self.root / ".harness"  # the harness's own files: journal and notes
        self.state.mkdir(parents=True, exist_ok=True)

    def allows(self, rel: str) -> bool:
        p = (self.root / rel).resolve()  # resolves "..", symlinks and absolute paths
        return p.is_relative_to(self.root) and not p.is_relative_to(self.state)

    def resolve(self, rel: str) -> Path:
        if not self.allows(rel):
            raise PermissionError(f"{rel!r} is outside the workspace")
        return (self.root / rel).resolve()
```

```python
class ToolRegistry:
    """Name -> (JSON-schema definition, Python function). The model sees only the
    definitions; the functions run here, in code the harness controls (P6)."""
    def __init__(self):
        self.tools = {}

    def register(self, name, description, properties, fn):
        schema = {"type": "object", "properties": properties, "required": list(properties)}
        self.tools[name] = ({"name": name, "description": description, "input_schema": schema}, fn)

    def definitions(self) -> list:
        return [definition for definition, _ in self.tools.values()]

    @staticmethod
    def result(call, content, is_error=False):
        return {"type": "tool_result", "tool_use_id": call["id"], "content": content,
                "is_error": is_error}

    def execute(self, call: dict) -> dict:
        """Always answer a tool_use with a tool_result. Failures go back to the model as
        is_error results it can act on, never as exceptions that kill the loop."""
        if call["name"] not in self.tools:
            return self.result(call, f"Unknown tool. Available: {', '.join(self.tools)}", True)
        try:
            return self.result(call, str(self.tools[call["name"]][1](**call["input"])))
        except Exception as e:  # bad arguments, missing file, jail violation
            return self.result(call, f"{type(e).__name__}: {e}", True)
```

The registry enforces the [§10](10-tool-use.md) contract: every `tool_use` gets exactly one `tool_result` with the same id, and a failure comes back with `"is_error": true` and a message saying what went wrong, never as an exception that kills the loop. Only the model can change the plan, so the model has to hear about the failure. The jail resolves `..`, absolute paths and symlinks before comparing, and it fences off `.harness/`, so the agent can't rewrite its own notes or step log ([§19](19-harness-engineering.md): keep sensors out of the maker's write path).

`add_file_tools` registers `read_file`, `write_file` and `run_check`. `run_check` uses an **allow-list**: it accepts exactly `python3 <file>`, runs it in a child process with a 10-second timeout, and reports the exit code and output. You can list what a task needs, but not everything dangerous, so the allow-list is the real control (P9, [§20](20-agent-runtime.md)).

### Layer 4: the agent loop

```python
def agent_loop(run: Run, it: int, system: str, messages: list, max_turns=4) -> str:
    """Call the model; while it asks for tools, run them and send the results back.
    Returns why it stopped: end_turn, max_turns, token_budget or another stop_reason."""
    def ask(turn):  # one journaled, traced, stateless model call
        if run.compactor.needed(system, run.tools.definitions(), messages):
            messages[:] = run.compactor.compact(messages, run.trace)
        sid, t0 = f"i{it}.t{turn}", time.perf_counter()
        resp, replayed = run.log.step(sid, call_model, run.model, system,
                                      run.tools.definitions(), messages, sid)
        run.spent += total_input(resp["usage"]) + resp["usage"]["output_tokens"]
        calls = [f"{b['name']}({short(b['input'])})"
                 for b in resp["content"] if b["type"] == "tool_use"]
        words = " ".join(b["text"] for b in resp["content"] if b["type"] == "text")
        run.trace.record("model", sid, t0, replayed, resp["usage"],
                         f"{resp['stop_reason']}: " + (", ".join(calls) or repr(words[:70])))
        messages.append({"role": "assistant", "content": resp["content"]})  # all blocks, as-is
        return resp

    resp, turn = ask(1), 1
    while resp["stop_reason"] == "tool_use":  # the model asked to act
        results = []
        for call in (b for b in resp["content"] if b["type"] == "tool_use"):
            t0 = time.perf_counter()
            result, replayed = run.log.step(f"i{it}.t{turn}.{call['id']}", run.hooks.run_tool, call)
            note = ("ERROR: " if result["is_error"] else "ok: ") + result["content"]
            run.trace.record("tool", call["name"], t0, replayed, None,
                             note.replace("\n", " | "), result["is_error"])
            results.append(result)
        messages.append({"role": "user", "content": results})  # every result in ONE user turn
        if turn == max_turns:
            return "max_turns"
        if run.spent >= run.budget:
            return "token_budget"
        resp, turn = ask(turn + 1), turn + 1
    return resp["stop_reason"]  # end_turn is a claim, not proof (§11); or max_tokens, refusal...
```

This is the [§11](11-agents.md) loop with the rest of the harness plugged in. `ask()` wraps one model call in compaction, the journal and tracing. While the latest response asks for tools, each pass sends every call through the hooks, returns all results in one user turn, and checks the stops:

- **`end_turn`**: the model says it's finished, a claim rather than proof, which is why layer 11 exists.
- **`max_turns`**: a hard cap on calls per iteration. It ends iteration 1 on purpose.
- **`token_budget`**: a cap on total tokens, summed from `usage` and rebuilt from the journal on replay, so a crash can't reset it ([§20](20-agent-runtime.md)).
- **Any other `stop_reason`** (`max_tokens`, `refusal`, `pause_turn`) ends the loop with nothing executed. A truncated `tool_use` must never run.

The model chooses each next step (P7), and code owns the caps.

### Layer 5: hooks and permissions

```python
class Hooks:
    """Pre-tool hooks may deny a call; post-tool hooks may add to its result. They run
    on every call, whatever the model intends, which is what makes them guardrails."""
    def __init__(self, tools, ws, task, approver):
        self.tools, self.ws, self.task, self.approver = tools, ws, task, approver
        self.pre = [self.deny_outside_workspace, self.deny_dangerous_commands, self.ask_approval]
        self.post = [self.back_pressure]

    def deny_outside_workspace(self, call):
        path = call["input"].get("path")
        if path is not None and not self.ws.allows(str(path)):
            return f"Blocked: {path!r} is outside the workspace. Use a relative path."

    def deny_dangerous_commands(self, call):  # a speed bump, not containment (§19, §20)
        command = str(call["input"].get("command", ""))
        if DANGEROUS.search(command):
            return f"Blocked: {command!r} deletes files or chains commands. Run one python3 file."

    def ask_approval(self, call):  # the human-in-the-loop gate for writes
        if call["name"] == "write_file" and not self.approver(call):
            return "Blocked: the user declined this write."

    def back_pressure(self, call, result):  # after a .py write, run the check and feed it back
        if call["name"] == "write_file" and not result["is_error"] \
                and call["input"]["path"].endswith(".py"):
            ok, detail = task_check(self.ws, self.task)
            verdict = "passed" if ok else "FAILED"
            result["content"] += f"\n[back pressure] check {verdict}: {detail}"
        return result

    def run_tool(self, call):
        for hook in self.pre:
            reason = hook(call)
            if reason:  # denied: an is_error result, so the model can change its plan
                return self.tools.result(call, reason, True)
        result = self.tools.execute(call)  # the only line with side effects (P6)
        for hook in self.post:
            result = hook(call, result)
        return result
```

Hooks are deterministic guardrails: they run on every call, whatever the model intends (P6). Pre-tool hooks can deny a call, and a denial comes back as an `is_error` result, so the model sees why and can change its plan. The post-tool hook adds to a result.

- **`deny_outside_workspace`** blocks a path outside the jail. The tool would refuse it anyway (defense in depth), but the hook's message tells the model what to do instead.
- **`deny_dangerous_commands`** is a regex blocklist, and it caught the `rm -rf` in the demo. As [§19](19-harness-engineering.md) warns, a blocklist is a speed bump, not containment. The allow-list, and in production a sandbox, do the real work.
- **`ask_approval`** calls an approval callback before every write. The demo approves automatically. With `--ask` you answer at the terminal, and anything but `y` blocks the write. The approval happens inside the journaled tool step, so a resumed run doesn't ask again: [§20](20-agent-runtime.md)'s human approval as a durable step, in miniature.
- **`back_pressure`** reruns the task's check after every successful `.py` write and appends the verdict to the write's result. That's how the agent learned at turn 2 that it had printed `'Hello, harness!'`. In [§21](21-loop-engineering.md)'s terms it is a fast computational sensor whose message says exactly what's wrong, in one line.

### Layer 6: context management

```python
class Compactor:
    """Estimate the prompt before each call. Past the threshold, replace older turns with
    a summary and keep only the latest tool round verbatim (§16)."""
    def __init__(self, threshold: int):
        self.threshold = threshold

    def needed(self, system, tools, messages) -> bool:
        big = estimate_tokens([system, tools, messages]) > self.threshold
        return big and sum(m["role"] == "assistant" for m in messages) >= 2

    def compact(self, messages: list, trace) -> list:
        t0, before = time.perf_counter(), estimate_tokens(messages)
        cut = max(i for i, m in enumerate(messages) if m["role"] == "assistant")
        lines = []  # an extractive summary; production harnesses ask the model to write it
        for m in messages[:cut]:
            for b in ([text(m["content"])] if isinstance(m["content"], str) else m["content"]):
                if b["type"] == "text" and m["role"] == "user":
                    lines.append(b["text"])  # the task statement (or an earlier summary)
                elif b["type"] == "tool_use":
                    lines.append(f"- you called {b['name']}({short(b['input'])})")
                elif b["type"] == "tool_result":
                    status = "ERROR" if b.get("is_error") else "ok"
                    lines.append(f"  -> {status}: {str(b['content']).replace(chr(10), ' ')[:160]}")
        summary = ("<summary>Earlier turns were compacted; re-read files or reload skills if you "
                   "need their full text.\n" + "\n".join(lines) + "\n</summary>")
        # Preserved thinking: on Claude 5.5-family models a thinking block is valid only with
        # the exact history that produced it. Once a summary replaces that history, replaying
        # the kept turns' thinking blocks is rejected, so strip them (text and tool_use stay).
        # Compact only between tool rounds: here every tool_use already has its tool_result.
        thinking = ("thinking", "redacted_thinking")
        tail = [{"role": m["role"],
                 "content": [b for b in m["content"] if b["type"] not in thinking]}
                for m in messages[cut:]]
        compacted = [{"role": "user", "content": summary}] + tail
        trace.record("compact", f"{len(messages)} -> {len(compacted)} msgs", t0, False, None,
                     f"~{before} -> ~{estimate_tokens(compacted)} message tokens")
        return compacted
```

Context is a finite budget that rots as it grows (P3), so before each call the harness estimates the prompt at about four characters per token (real counts come from `usage` or `count_tokens`). Past the threshold, `compact()` keeps the latest tool round verbatim and replaces everything before it with a summary: the task, each call made, and the start of each result, errors included, since observed failures are worth keeping ([§16](16-context-engineering.md)). Two simplifications keep the demo deterministic. The threshold is absurdly low, 850 estimated tokens, where real triggers sit in the tens or hundreds of thousands (the API's own threshold compaction **(Preview)** defaults to 150K). And the summary is extractive, where production harnesses have the model write it with a prompt tuned for recall.

Two rules matter on current models. The first is **preserved thinking**: on Claude Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1, each thinking block is bound to the exact system prompt, tools and messages before it. A summary you write yourself changes that prefix, so replaying the kept turns' thinking blocks fails the check and the request is rejected. Anthropic's docs give two client-side fixes. One is to strip `thinking` and `redacted_thinking` from the kept turns while keeping their `text` and `tool_use` blocks, which is what `compact()` does. The other, which they recommend, is "simple compaction": one summary message plus the next instruction, with nothing earlier replayed. The second rule: never compact mid tool round. `compact()` runs only at the top of a turn, when every `tool_use` has its `tool_result`.

### Layer 7: skills

```python
class SkillLibrary:
    """Level 1: only each skill's name and description go into the system prompt.
    Level 2: the body is read from disk when the model calls load_skill (§18)."""
    def __init__(self, skills: dict):
        self.root = Path(tempfile.mkdtemp(prefix="skills-"))  # built at runtime: no extra files
        atexit.register(shutil.rmtree, self.root, True)
        for name, (description, body) in skills.items():
            (self.root / name).mkdir()
            (self.root / name / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: {description}\n---\n{body}\n")
        self.names = sorted(skills)

    def index(self) -> str:  # reads only the frontmatter: a few dozen tokens per skill
        heads = [(self.root / n / "SKILL.md").read_text().split("---")[1] for n in self.names]
        meta = [dict(line.split(": ", 1) for line in h.strip().splitlines()) for h in heads]
        return "\n".join(f"- {m['name']}: {m['description']}" for m in meta)

    def load(self, name: str) -> str:  # the load_skill tool: the body enters context now
        if name not in self.names:
            raise ValueError(f"No skill {name!r}. Installed: {', '.join(self.names)}")
        body = (self.root / name / "SKILL.md").read_text().split("---", 2)[2].strip()
        return f"<skill name={name!r}>\n{body}\n</skill>"
```

`SkillLibrary` writes two skills into a temporary directory at startup, so the program ships as one file. Each `SKILL.md` has the [§18](18-skills.md) frontmatter (`name`, `description`) and a markdown body.

- **Level 1.** `index()` reads only the frontmatter into the system prompt. Both skills cost tokens on every call, including `release-notes`, which the demo never uses.
- **Level 2.** A body enters context only when the model calls `load_skill`, as at `i1.t1`. The model matched on the descriptions, so triggering is probabilistic (P4). The schema's `enum` and the check in `load()` stop a name like `../../etc` from becoming a path.
- **Level 3.** Bundled scripts and reference files would be ordinary `read_file` and `run_check` calls.

At `i1.t4` compaction summarized the skill body away, and the summary tells the model to reload skills if it needs them: [§16](16-context-engineering.md)'s restorable compression.

### Layer 8: memory and the progress file

```python
class Memory:
    """Notes on disk. Each fresh context starts by reading them; the model adds to them
    with save_note, and the driver records why each iteration ended (§17, §21)."""
    def __init__(self, ws: Workspace):
        self.path = ws.state / "progress.md"

    def read(self) -> str:
        return self.path.read_text().strip() if self.path.exists() else ""

    def append(self, note: str) -> str:
        with self.path.open("a") as f:
            f.write(f"- {note.strip()}\n")
        return f"saved note to {self.path.name}"
```

Every iteration starts from an empty context (P2), so anything the next one needs must be on disk. The model writes notes on the hot path with `save_note` ([§17](17-memory.md)), and the driver appends why each iteration ended. Iteration 2's header, "2 note(s) on disk", is the point: the new context knew the string was wrong without ever seeing iteration 1. It's the progress-file pattern of Anthropic's long-running harness and of Huntley's plan file ([§19](19-harness-engineering.md), [§21](21-loop-engineering.md)). A wrong note persists as well as a right one (memory poisoning, [§17](17-memory.md)), so the agent can only append, never edit.

### Layer 9: the durable step log

```python
class StepLog:
    """An append-only JSONL journal of every step's result. On a rerun, finished steps
    return their recorded result: no second model call and no second side effect (§20)."""
    def __init__(self, path: Path, crash_after=None):
        self.path, self.crash_after, self.executed, self.replayed = path, crash_after, 0, 0
        lines = path.read_text().splitlines() if path.exists() else []
        self.done = {r["step"]: r["result"] for r in map(json.loads, filter(None, lines))}

    def step(self, step_id: str, fn, *args):
        if step_id in self.done:  # replay: hand back the recorded result, instantly
            self.replayed += 1
            return self.done[step_id], True
        result = fn(*args)        # first time: really execute it
        with self.path.open("a") as f:  # a crash before this write re-runs the step on resume,
            f.write(json.dumps({"step": step_id, "result": result}) + "\n")
            f.flush()                   # so tools must be idempotent (at-least-once)
            os.fsync(f.fileno())
        self.done[step_id] = result
        self.executed += 1
        if self.executed == self.crash_after:
            raise SystemExit(f"simulated crash after {self.executed} new steps; rerun to resume")
        return result, False
```

Every model call, tool call, notes read and goal check is a **step**. Its result is appended to `.harness/journal.jsonl` before the run moves on, and on a rerun `step()` returns the recorded result for any id it has already seen. Run the program a second time and nothing executes:

```text
== iteration 1/3: fresh context, 0 note(s) on disk ==
  model   i1.t1          (replayed) tool_use: load_skill(name='python-scripts')
  tool    load_skill     (replayed) ok: <skill name='python-scripts'> | 1. Print exactly the expected text: same case, punctuation, spacing. |...
  ...
trace summary
  kind     spans replayed errors  tok in tok out       ms
  model        7        7      0    4867     293      0.1
  tool         6        6      1       0       0      0.0
  compact      1        0      0       0       0      0.1
  goal         2        2      1       0       0      0.0

result: DONE after 2 iteration(s) | steps executed 0, replayed 18 | ~5,160 of 20,000 tokens
workspace: /tmp/mini_harness/stub
```

The more realistic case is a crash. `--crash-after 6` kills the process after six new steps, just after the model's third reply was journaled. The rerun replays those six instantly, with no model call and no second write, and then does the rest for real:

```text
$ python3 compendium/code/mini_harness.py --fresh --crash-after 6
  ...
  tool    write_file     ok: wrote greet.py (25 bytes) | [back pressure] check FAILED: expected 'hello, harness', got 'Hello, harness!' (exit 0)
simulated crash after 6 new steps; rerun to resume
$ python3 compendium/code/mini_harness.py

== iteration 1/3: fresh context, 0 note(s) on disk ==
  model   i1.t1          (replayed) tool_use: load_skill(name='python-scripts')
  tool    load_skill     (replayed) ok: <skill name='python-scripts'> | 1. Print exactly the expected text: same case, punctuation, spacing. |...
  model   i1.t2          (replayed) tool_use: write_file(path='greet.py', content="print('Hello, harness!')\n")
  tool    write_file     (replayed) ok: wrote greet.py (25 bytes) | [back pressure] check FAILED: expected 'hello, harness', got 'Hello, harne...
  model   i1.t3          (replayed) tool_use: run_check(command='rm -rf __pycache__ && python3 greet.py')
  tool    run_check      ERROR: Blocked: 'rm -rf __pycache__ && python3 greet.py' deletes files or chains commands. Run one python3 file.
  ...
result: DONE after 2 iteration(s) | steps executed 12, replayed 6 | ~5,160 of 20,000 tokens
```

Three rules from [§20](20-agent-runtime.md) show up in the code:

- **Step ids come from the code path** (`i1.t3`, `i1.t3.toolu_...`), never from a clock, so a replay finds them again.
- **I/O between steps is itself a step.** Even reading the notes at the start of an iteration is journaled, so a replay sees what the original run saw.
- **Execution is at-least-once.** A crash between a side effect and its journal write reruns that step. Rewriting the same file is harmless, but a tool that charges a card would need an idempotency key.

Compaction isn't journaled: it's a pure function of journaled results, so a replay recomputes the same answer. That's [§20](20-agent-runtime.md)'s Managed Agents idea at toy scale: the log is the source of truth, and the context window is a view of it. Sampling (P4) doesn't break replay, because each sample is recorded once.

### Layer 10: tracing

```python
class Tracer:
    """One span per step, with timing and token usage: printed live, summarized at the end."""
    def __init__(self):
        self.spans = []

    def record(self, kind, name, t0, replayed, usage, note, error=False):
        usage = usage or {}
        self.spans.append({"kind": kind, "ms": (time.perf_counter() - t0) * 1000, "error": error,
                           "replayed": replayed, "in": total_input(usage),
                           "out": usage.get("output_tokens", 0)})
        say(kind, name, ("(replayed) " if replayed else "") + note)

    def summary(self):
        print(f"\ntrace summary\n  {'kind':<8}{'spans':>6}{'replayed':>9}{'errors':>7}"
              f"{'tok in':>8}{'tok out':>8}{'ms':>9}")
        for kind in dict.fromkeys(s["kind"] for s in self.spans):
            ss = [s for s in self.spans if s["kind"] == kind]
            n = [sum(s[k] for s in ss) for k in ("replayed", "error", "in", "out", "ms")]
            print(f"  {kind:<8}{len(ss):>6}{n[0]:>9}{n[1]:>7}{n[2]:>8}{n[3]:>8}{n[4]:>9.1f}")
```

Each step gets a span with its kind, duration, tokens, and whether it was replayed or failed. The live lines are the trace above, and the summary aggregates them. You can't unit-test a distribution (P4), so traces are what you read to find failure patterns, and they feed evals ([§26](26-evals.md)). Production harnesses export the same fields as OpenTelemetry spans under the GenAI semantic conventions ([§27](27-observability.md)).

### Layer 11: the outer loop and the goal check

```python
def goal_check(run: Run, ws: Workspace, task: Task, it: int):
    """The checker, separate from the maker: the computational check first, in a new
    process; then, only if it passes, a model judge in a fresh context with no tools."""
    ok, detail = task_check(ws, task)
    if not ok:
        return False, detail
    source = (ws.root / task.file).read_text()
    evidence = [{"role": "user", "content": f"Task:\n{task.prompt}\n\n{task.file}:\n{source}"}]
    resp = call_model(run.model, JUDGE, [], evidence, f"i{it}.judge")  # no tools, no history
    verdict = " ".join(b["text"] for b in resp["content"] if b["type"] == "text").strip()
    return verdict.upper().startswith("PASS"), verdict
```

```python
def drive(task: Task, model, ws: Workspace, approver, max_iters=3, crash_after=None) -> bool:
    """The outer loop: each iteration gets a FRESH context (system prompt + task + notes
    from disk), runs the agent loop, then a separate goal check decides if it is done."""
    tools, memory, skills = ToolRegistry(), Memory(ws), SkillLibrary(DEMO_SKILLS)
    add_file_tools(tools, ws)
    tools.register("load_skill", "Load a skill's full instructions by name.",
                   {"name": {"type": "string", "enum": skills.names}}, skills.load)
    tools.register("save_note", "Append a short progress note that survives context resets.",
                   {"note": {"type": "string"}}, memory.append)
    run = Run(model, tools, Hooks(tools, ws, task, approver), Compactor(threshold=850),
              StepLog(ws.state / "journal.jsonl", crash_after), Tracer())
    system = SYSTEM.format(skills=skills.index())  # identical on every call: cache-friendly
    for it in range(1, max_iters + 1):
        notes, _ = run.log.step(f"i{it}.context", memory.read)
        print(f"\n== iteration {it}/{max_iters}: fresh context, "
              f"{len(notes.splitlines())} note(s) on disk ==")
        messages = [{"role": "user", "content": f"{task.prompt}\n\n<progress>\n"
                                                f"{notes or '(none yet)'}\n</progress>"}]
        stop, t0 = agent_loop(run, it, system, messages), time.perf_counter()
        (ok, detail), replayed = run.log.step(f"i{it}.goal", goal_check, run, ws, task, it)
        verdict = ("DONE: " if ok else "NOT DONE: ") + detail
        run.trace.record("goal", f"i{it}", t0, replayed, None, f"after {stop}, {verdict}", not ok)
        if ok or run.spent >= run.budget:  # done, or the hard spend cap is reached
            break
        run.log.step(f"i{it}.progress", memory.append,
                     f"[harness] iteration {it} ended ({stop}); goal check failed: {detail}")
    run.trace.summary()
    print(f"\nresult: {'DONE' if ok else 'NOT DONE'} after {it} iteration(s) | steps "
          f"executed {run.log.executed}, replayed {run.log.replayed} | "
          f"~{run.spent:,} of {run.budget:,} tokens\nworkspace: {ws.root}")
    return ok
```

`drive()` is the loop engineering of [§21](21-loop-engineering.md): up to three iterations, each from a fresh context built from the task and the notes on disk. A fresh start discards failed attempts and stale output, the tokens that rot attention (P3). The harness, not the model, decides when to stop, through `goal_check()`, which is separate from the maker in two ways:

- **It gathers its own evidence.** It runs the check itself in a new process instead of trusting the transcript, where a `run_check` output or an `end_turn` message could be wrong or invented.
- **It asks a separate judge.** Only after the computational check passes does it call a model with a different system prompt, no tools and no history, to review the file. That's [§21](21-loop-engineering.md)'s order: code first wherever code can decide, then a judge (P8). In stub mode the verdict is scripted.

A failed check's reason goes into the progress file for the next iteration. The driver didn't care why iteration 1 stopped, only whether the goal held.

### Running it against the real API

```bash
export ANTHROPIC_API_KEY=...        # read from the environment, never hardcoded
python3 compendium/code/mini_harness.py --real --fresh
```

The same harness now calls `claude-sonnet-5-5`, and the model decides every step from the messages, so expect a different trace: it may get the string right first time and finish in one iteration. Real responses carry `thinking` blocks, which the loop sends back unchanged and `compact()` strips from kept turns. At Sonnet 5.5's $2 / $10 per million input and output tokens (Oct 2026), a handful of calls with prompts of a few thousand tokens costs cents. The request shape follows the current API reference, but the `--real` run was exercised against a local mock of the Messages API, not the live service **(⚠ verify)**.

### What this toy leaves out

Roughly in the order you would miss them, a production harness adds:

- **Real sandboxing.** `run_python` is a child process with your permissions. A production harness confines filesystem and network together, at the OS, container, gVisor or microVM level, and keeps secrets outside ([§20](20-agent-runtime.md)).
- **Prompt-injection defenses.** Any file the agent reads can carry instructions (P9). Least privilege and approval gates on consequential tools matter more than any prompt ([§32](32-security-guardrails.md)).
- **Retries and idempotency.** One 429 or 5xx ends this program. Production code retries with backoff and gives side-effecting tools idempotency keys ([§30](30-cost-latency-reliability.md)).
- **Prompt caching.** The prefix is already stable. Adding `cache_control` would make the repeated part cheap and fast ([§05](05-api-and-prompting.md), [§30](30-cost-latency-reliability.md)).
- **Streaming.** SSE shows tokens as they are decoded, and the SDKs require it for large `max_tokens` ([§05](05-api-and-prompting.md)).
- **Parallel tools.** Independent reads can run concurrently, with all results still returned in one user turn ([§10](10-tool-use.md)).
- **Auth and identity.** Real agents act for users with scoped, delegated credentials that never enter the sandbox ([§33](33-agent-identity.md)).
- **Evals.** The demo proves one scripted path works once, not how often a real model succeeds (P4). That takes a task set, repeated trials and graders ([§26](26-evals.md)).
- **Refusals and strict schemas.** Production code adds refusal fallbacks and `strict: true` tool schemas ([§06](06-structured-outputs.md), [§10](10-tool-use.md)).

Each is a function or a module in a real harness, not a different architecture.

## Comparison

| | This toy (`mini_harness.py`) | Product harness (Claude Code, Codex) | Agent SDK (Claude Agent SDK, OpenAI Agents SDK) | Graph framework (LangGraph, Google ADK 2.0, Microsoft Agent Framework workflows) |
|---|---|---|---|---|
| Who owns the loop | You, in about 35 lines | The vendor; you configure it | The library; you add tools and callbacks | You draw nodes and edges; the runtime walks them |
| Tools | Five, hand-written | Built-in file, shell and search tools, plus MCP | Claude: Claude Code's built-in tools; OpenAI: your functions, hosted tools, handoffs | Any node: code, an LLM call, a tool or a whole agent |
| Guardrails | Pre- and post-tool hooks, an allow-list, an approval callback | Permission modes, allow/ask/deny rules, hooks, an OS sandbox for shell commands | Callback hooks (Claude), guardrails (OpenAI) | Interrupts before nodes; checks are nodes |
| Context management | Extractive compaction that keeps the last tool round | Automatic compaction, subagents, skills, `CLAUDE.md` or `AGENTS.md` | Built in (Claude Agent SDK); sessions (OpenAI) | State fields you design per node |
| Durability | A JSONL step journal, replayed on rerun | Resumable sessions; cloud runs on vendor infrastructure | Sessions; durable engines through integrations, such as Temporal for OpenAI's SDK | Checkpointers per `thread_id`, with time travel |
| Outer loop | `drive()` plus a goal check | Claude Code's `/goal`, routines, `claude -p` in a script | You write it | A cycle in the graph |
| Strength | Every line is visible | The best-tuned harness for its own models | A production loop without writing one | Explicit, testable control flow (P7) |
| Weakness | Neither safe nor robust | Opaque, and tuned to its vendor's models | Less control over the internals | Open-ended tasks fight a fixed graph |
| Choose when | Learning, prototypes, harness tests | Coding and computer work today | Your own product on a proven loop | Known process shapes with branches and approvals |

## What it didn't solve

You've built a general harness: a loop, tools, guardrails, memory, durability and a driver, none of it specific to any domain. Real agents specialize, and their tools, sensors and loops are shaped by what their domain can verify. The archetype where that worked first and best is coding, because compilers, type checkers and tests are back pressure that already exists.

→ Next: [§23 Coding Agents and Agentic Engineering](23-coding-agents.md)

## Check your understanding

**Q: What breaks if you remove the durable log?**

A crash at turn 30 loses the in-memory run. Every model call is paid for again, and because output is sampled (P4), the rerun takes a different path that may contradict files already written. Side effects and approval prompts repeat, and the spend counter resets, so a crash-looping agent can blow through its budget. For a run that lasts seconds, skipping the log is a fair tradeoff.

**Q: Why does the goal check rerun the check itself and use a separate model call, instead of trusting the agent's `end_turn` and its `run_check` output?**

`end_turn` only means the model stopped asking for tools, and its closing message is a prediction that sounds like success (P8). The transcript holds the maker's own reasons for believing the work is right, so a judge that reads it inherits its blind spots. Running the check in a new process gathers independent evidence, and a judge with a fresh context and no tools sees only the artifact. The price is an extra call per iteration, so the cheap computational check runs first.

**Q: What would happen if a tool raised an exception instead of returning an `is_error` result?**

The loop would crash, or the API would reject the next request, because every `tool_use` needs a matching `tool_result`. Either way, the model, which is the only component that can change the plan, never learns what went wrong. An instructive error result such as "Blocked: ... Run one python3 file." lets it adapt on its next turn. Raise only for failures the model can't fix, such as a revoked API key.

**Q: What would happen if `compact()` kept the thinking blocks of the turns it keeps, on Claude Sonnet 5.5?**

Each thinking block is bound to the system prompt, tools and messages that came before it (preserved thinking). Once the summary replaces the earlier turns, that prefix no longer matches, so the API rejects the request where the check is enforced. The fixes are to strip thinking from the kept turns, to use simple compaction with no turns kept, or to let the API compact on the server **(Preview)**. Without thinking blocks in the history, the problem doesn't arise.

**Q: Why does the system prompt stay identical for the whole run, with the progress notes in the first user message instead?**

The prefix is resent on every call (P2), and prompt caching only pays off if it is byte-identical (P10). Volatile content near the front invalidates everything after it, and on current models editing the system prompt also invalidates stored thinking. So stable content goes first, volatile content last, and history stays append-only. If instructions must change mid-run, append a system message instead ([§16](16-context-engineering.md)).

**Q: The dangerous-command hook and `run_check`'s allow-list both stop `rm -rf`. Why keep both, and which one is the real control?**

The allow-list is the control. It permits exactly `python3 <file>`, so anything unlisted fails, whatever it looks like (P9). The regex blocklist can't enumerate every destructive command (`find -delete`, a Python one-liner), but it catches common ones early, with a clearer message that helps the model recover. Neither is containment. In production, a sandbox bounds the damage when both are wrong ([§20](20-agent-runtime.md)).

**Q: Why does iteration 2 start from an empty context instead of continuing iteration 1's conversation?**

Iteration 1's history holds a failed attempt, a denied command and a summary, tokens that dilute attention and can mislead (P3). The model is stateless anyway (P2), so a fresh context that reads two notes from disk is the same agent without that baggage. The cost is that anything not written down is lost. For judgment-heavy work, where the session's own reasoning is the valuable state, one longer session with compaction can be better.

**Q: Stub vs real model: what does the stub prove, and what can't it tell you?**

The stub proves the mechanics: the request shape, tool round trip, hooks, compaction, replay and stop rules all behave correctly on a known path, deterministically and for free. It can't tell you whether a real model loads the right skill, recovers from back pressure or finishes within budget. Those behaviors are probabilistic (P4) and need evals over many real runs ([§26](26-evals.md)). Use stubs for harness tests in CI and evals for agent quality.

## Takeaways

- A harness is a stack of small layers around one stateless call; about 380 lines of code show them all.
- The model only returns typed blocks. Every action, check and limit lives in harness code (P6).
- Failures, denials and check verdicts go back to the model as tool results it can act on, never as crashes.
- Back pressure plus a goal check that gathers its own evidence turns "the model says it's done" into "the check says so" (P8).
- On Claude 5.5-family models, never replay thinking blocks after rewriting what came before them.
- Journal every step under an id from the code path, so a crash never repeats paid-for work, approvals or spend.
- Fresh context per iteration, state on disk: the repo remembers what the model forgets (P2, P3).
- The gap to production is sandboxing, security, retries, caching, streaming, parallelism, identity and evals, not a different architecture.

## Sources

Compendium sections behind each layer: [§05](05-api-and-prompting.md) (1, 2), [§10](10-tool-use.md) (3), [§11](11-agents.md) (4), [§19](19-harness-engineering.md) and [§21](21-loop-engineering.md) (5, 11), [§16](16-context-engineering.md) (6), [§18](18-skills.md) (7), [§17](17-memory.md) (8), [§20](20-agent-runtime.md) (9).

- Anthropic docs, Messages API reference: https://platform.claude.com/docs/en/api/messages
- Anthropic docs, How tool use works: https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works
- Anthropic docs, Handle tool calls (`is_error`, result ordering): https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls
- Anthropic docs, Preserved thinking (client-side compaction rules): https://platform.claude.com/docs/en/build-with-claude/preserved-thinking
- Anthropic docs, Compaction: https://platform.claude.com/docs/en/build-with-claude/compaction
- Anthropic, "Building effective agents" (Dec 19, 2024): https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, "Effective context engineering for AI agents" (Sep 29, 2025): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic, "Equipping agents for the real world with Agent Skills" (Oct 16, 2025): https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Agent Skills specification: https://agentskills.io/specification
- Anthropic, "Effective harnesses for long-running agents" (Nov 26, 2025): https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic, "Harness design for long-running application development" (Mar 24, 2026): https://www.anthropic.com/engineering/harness-design-long-running-apps
- LangChain, Vivek Trivedy, "The Anatomy of an Agent Harness" (Mar 10, 2026): https://blog.langchain.com/the-anatomy-of-an-agent-harness/
- Birgitta Böckeler, "Harness engineering for coding agent users" (Apr 2, 2026): https://martinfowler.com/articles/harness-engineering.html
- Claude Code docs, Hooks reference: https://code.claude.com/docs/en/hooks
- Claude Code docs, Permissions and permission modes: https://code.claude.com/docs/en/permissions
- Claude Agent SDK docs, Hooks: https://code.claude.com/docs/en/agent-sdk/hooks
- OpenAI Agents SDK documentation: https://openai.github.io/openai-agents-python/
- LangGraph docs, Persistence (checkpointers, time travel): https://docs.langchain.com/oss/python/langgraph/persistence
- Anthropic, "Scaling Managed Agents: Decoupling the brain from the hands" (Apr 8, 2026): https://www.anthropic.com/engineering/managed-agents
- Temporal docs, Activity Definition (results recorded only after an Activity returns): https://docs.temporal.io/activity-definition
- Geoffrey Huntley, "Ralph Wiggum as a 'software engineer'" (Jul 14, 2025): https://ghuntley.com/ralph/
- Geoffrey Huntley, "don't waste your back pressure" (Jan 17, 2026): https://ghuntley.com/pressure/
- Addy Osmani, "Loop Engineering" (Jun 7, 2026): https://addyosmani.com/blog/loop-engineering/
- Claude Code docs, "Keep Claude working toward a goal" (`/goal`): https://code.claude.com/docs/en/goal
- OpenTelemetry, GenAI semantic conventions (moved from opentelemetry.io to their own repository, as of Oct 2026): https://github.com/open-telemetry/semantic-conventions-genai
- Python docs, `subprocess.run` (timeouts): https://docs.python.org/3/library/subprocess.html
- Python docs, `urllib.request`: https://docs.python.org/3/library/urllib.request.html
