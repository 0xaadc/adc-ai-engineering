#!/usr/bin/env python3
"""mini_harness.py: every layer of an agent harness in one stdlib-only file (compendium §22).

  python3 mini_harness.py              offline, scripted stub model; rerun it to watch the replay
  python3 mini_harness.py --fresh      wipe the workspace and journal first
  python3 mini_harness.py --fresh --crash-after 6; python3 mini_harness.py   crash, then resume
  python3 mini_harness.py --real --fresh    the real Messages API (needs ANTHROPIC_API_KEY)
"""
import argparse, atexit, json, os, re, shlex, shutil, subprocess, sys, tempfile, time
import urllib.error, urllib.request
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path

MODEL = "claude-sonnet-5-5"
Task = namedtuple("Task", "prompt file expected")
TASK = Task("Create greet.py in the workspace that prints exactly: hello, harness\n"
            "Check: `python3 greet.py` must exit 0 and print that line.",
            "greet.py", "hello, harness")
SYSTEM = """You are a coding agent working in a sandboxed workspace directory.
- Use only the tools provided. Paths are relative to the workspace root.
- After you write a .py file, the harness runs the task's check and appends the verdict.
- Your context is wiped between iterations. Keep progress notes with save_note.
- When the check passes, stop and say what you did in one sentence.

Skills (call load_skill with a name before following that skill):
{skills}"""

def say(kind, name, note):
    print(f"  {kind:<7} {name:<14} {note if len(note) <= 120 else note[:117] + '...'}")

def short(args: dict) -> str:
    return ", ".join(f"{k}={v!r}" if len(repr(v)) <= 45 else f"{k}=..." for k, v in args.items())

def estimate_tokens(obj) -> int:  # ~4 characters per token; real counts come from usage
    return len(obj if isinstance(obj, str) else json.dumps(obj)) // 4 + 1

# ── Layer 1: model interface ─────────────────────────────────────────────────────
def text(t):
    return {"type": "text", "text": t}

def tool_use(tool, **args):
    return {"type": "tool_use", "id": None, "name": tool, "input": args}

SCRIPT = {  # the stub's replies, keyed by step id; iteration 1 makes a deliberate mistake
    "i1.t1": [text("A Python task: loading the matching skill first."),
              tool_use("load_skill", name="python-scripts")],
    "i1.t2": [tool_use("write_file", path="greet.py", content="print('Hello, harness!')\n")],
    "i1.t3": [text("Clearing stale bytecode, then re-running."),
              tool_use("run_check", command="rm -rf __pycache__ && python3 greet.py")],
    "i1.t4": [tool_use("save_note", note="greet.py prints 'Hello, harness!' but the check wants "
                       "exactly 'hello, harness'. Next: fix the string, then run_check.")],
    "i2.t1": [text("My notes say the printed string is wrong. Fixing it."),
              tool_use("write_file", path="greet.py", content="print('hello, harness')\n")],
    "i2.t2": [tool_use("run_check", command="python3 greet.py")],
    "i2.t3": [text("greet.py now prints exactly 'hello, harness' and the check passes.")],
    "i2.judge": [text("PASS: greet.py prints the required line and nothing else.")],
}

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

# ── Layer 2: messages and the stateless call (P2) ────────────────────────────────
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

# ── Layer 3: tool registry, workspace jail, tool_result with is_error ─────────────
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

def run_python(ws: Workspace, rel: str, timeout=10):
    """Run one workspace file in a child process with a timeout. Not a sandbox (§20)."""
    try:
        r = subprocess.run([sys.executable, "-I", str(ws.resolve(rel))], cwd=ws.root,
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()[-300:]
    except subprocess.TimeoutExpired:
        return -1, "", f"timed out after {timeout}s"

def add_file_tools(reg: ToolRegistry, ws: Workspace):
    def read_file(path):
        return ws.resolve(path).read_text()[:4000]  # bounded: observations cost context (P3)

    def write_file(path, content):
        ws.resolve(path).write_text(content)
        return f"wrote {path} ({len(content)} bytes)"

    def run_check(command):
        argv = shlex.split(command)
        if len(argv) != 2 or argv[0] not in ("python", "python3"):  # allow-list, not deny-list
            raise ValueError("run_check runs only `python3 <file>`, e.g. `python3 greet.py`")
        code, out, err = run_python(ws, argv[1])
        return f"exit={code} stdout={out!r}" + (f" stderr={err!r}" if err else "")

    path = {"type": "string", "description": "Path relative to the workspace, e.g. 'greet.py'"}
    reg.register("read_file", "Read a text file in the workspace.", {"path": path}, read_file)
    reg.register("write_file", "Create or overwrite a text file in the workspace.",
                 {"path": path, "content": {"type": "string"}}, write_file)
    reg.register("run_check", "Run `python3 <file>` in the workspace; report exit and output.",
                 {"command": {"type": "string", "description": "e.g. 'python3 greet.py'"}},
                 run_check)

def task_check(ws: Workspace, task: Task):
    """The computational check (a sensor, §19): run the file and compare stdout exactly."""
    if not (ws.root / task.file).exists():
        return False, f"{task.file} does not exist yet"
    code, out, err = run_python(ws, task.file)
    if code == 0 and out == task.expected:
        return True, f"{task.file} printed {out!r}"
    return False, f"expected {task.expected!r}, got {out!r} (exit {code}) {err}".strip()

# ── Layer 4: the agent loop ──────────────────────────────────────────────────────
@dataclass
class Run:  # the parts one harness run wires together (see drive())
    model: object
    tools: ToolRegistry
    hooks: "Hooks"
    compactor: "Compactor"
    log: "StepLog"
    trace: "Tracer"
    budget: int = 20_000  # token budget for the whole run, across iterations
    spent: int = 0        # rebuilt from the journal on replay, so a crash can't reset it

def agent_loop(run: Run, it: int, system: str, messages: list, max_turns=4) -> str:
    """Call the model; while it asks for tools, run them and send the results back.
    Returns why it stopped: end_turn, max_turns, token_budget or another stop_reason."""
    for turn in range(1, max_turns + 1):
        if run.spent >= run.budget:
            return "token_budget"
        if run.compactor.needed(system, run.tools.definitions(), messages):
            messages[:] = run.compactor.compact(messages, run.trace)
        sid, t0 = f"i{it}.t{turn}", time.perf_counter()
        resp, replayed = run.log.step(sid, call_model, run.model, system,
                                      run.tools.definitions(), messages, sid)
        run.spent += total_input(resp["usage"]) + resp["usage"]["output_tokens"]
        calls = [b for b in resp["content"] if b["type"] == "tool_use"]
        words = " ".join(b["text"] for b in resp["content"] if b["type"] == "text")
        run.trace.record("model", sid, t0, replayed, resp["usage"], f"{resp['stop_reason']}: " + (
            ", ".join(f"{c['name']}({short(c['input'])})" for c in calls) or repr(words[:60])))
        messages.append({"role": "assistant", "content": resp["content"]})  # all blocks, as-is
        if resp["stop_reason"] != "tool_use":  # end_turn is a claim, not proof (§11)
            return resp["stop_reason"]          # also max_tokens, refusal, pause_turn, ...
        results = []
        for call in calls:
            t0 = time.perf_counter()
            result, replayed = run.log.step(f"{sid}.{call['id']}", run.hooks.run_tool, call)
            note = ("ERROR: " if result["is_error"] else "ok: ") + result["content"]
            run.trace.record("tool", call["name"], t0, replayed, None,
                             note.replace("\n", " | "), result["is_error"])
            results.append(result)
        messages.append({"role": "user", "content": results})  # every result in ONE user turn
    return "max_turns"

# ── Layer 5: hooks and permissions ───────────────────────────────────────────────
DANGEROUS = re.compile(r"\brm\s+-\w*[rf]|\b(curl|wget|sudo|chmod)\b|[;&|`$>]")

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

def auto_approve(call):  # the approval callback; --ask swaps in a human
    say("hook", "approve", f"{call['name']}({call['input'].get('path')!r}) -> yes (auto)")
    return True

# ── Layer 6: context management ──────────────────────────────────────────────────
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
        tail = [{"role": m["role"], "content": [b for b in m["content"] if b["type"] not in thinking]}
                for m in messages[cut:]]
        compacted = [{"role": "user", "content": summary}] + tail
        trace.record("compact", f"{len(messages)} -> {len(compacted)} msgs", t0, False, None,
                     f"~{before} -> ~{estimate_tokens(compacted)} message tokens")
        return compacted

# ── Layer 7: skills with progressive disclosure ──────────────────────────────────
DEMO_SKILLS = {
    "python-scripts": ("Write and verify small Python scripts. Use when a task asks you to "
                       "create, fix or run a .py file.",
                       "1. Print exactly the expected text: same case, punctuation, spacing.\n"
                       "2. Write with write_file; the harness re-runs the check after .py writes.\n"
                       "3. Confirm with run_check: `python3 <file>`.\n"
                       "4. Never delete files or edit the check to make it pass."),
    "release-notes": ("Format release notes in the team's changelog style. Use when asked to "
                      "write or edit CHANGELOG.md.", "Group entries under Added/Changed/Fixed."),
}

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

# ── Layer 8: memory / progress file ──────────────────────────────────────────────
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

# ── Layer 9: durable step log ────────────────────────────────────────────────────
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

# ── Layer 10: tracing ────────────────────────────────────────────────────────────
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

# ── Layer 11: the outer loop driver and the goal check ───────────────────────────
JUDGE = "You are a strict reviewer. You did not write this code. Reply PASS or FAIL, and why."

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
        if ok or stop == "token_budget":
            break
        run.log.step(f"i{it}.progress", memory.append,
                     f"[harness] iteration {it} ended ({stop}); goal check failed: {detail}")
    run.trace.summary()
    print(f"\nresult: {'DONE' if ok else 'NOT DONE'} after {it} iteration(s) | steps "
          f"executed {run.log.executed}, replayed {run.log.replayed} | "
          f"~{run.spent:,} of {run.budget:,} tokens\nworkspace: {ws.root}")
    return ok

def main():
    ap = argparse.ArgumentParser(description="A complete agent harness in one file.")
    ap.add_argument("--real", action="store_true", help="call the Messages API (needs a key)")
    ap.add_argument("--fresh", action="store_true", help="wipe the workspace and journal first")
    ap.add_argument("--ask", action="store_true", help="approve each write yourself")
    ap.add_argument("--crash-after", type=int, help="simulate a crash after N new steps")
    ap.add_argument("--workspace", type=Path, help="default: <tmp>/mini_harness/<stub|real>")
    a = ap.parse_args()
    if a.real and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("--real needs ANTHROPIC_API_KEY set in the environment")
    root = a.workspace or Path(tempfile.gettempdir(), "mini_harness", "real" if a.real else "stub")
    ask = lambda call: input(f"  allow {call['name']}({call['input'].get('path')!r})? [y/N] ") == "y"
    ok = drive(TASK, AnthropicModel() if a.real else StubModel(SCRIPT), Workspace(root, a.fresh),
               ask if a.ask else auto_approve, crash_after=a.crash_after)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
