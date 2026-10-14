# 26. Evals

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

Parts 1–6 told a chronological story. Part 7 steps out of the timeline, because measuring and improving apply to every era: a single 2022-style prompt, a RAG pipeline ([§09](09-rag.md)) or a 2026 coding agent. Two principles drive this section. Output is sampled, so correctness is a rate (P4). Generating output is cheap and checking it is not, so verification is the bottleneck (P8). [§25](25-voice-agents.md) closed the archetypes and left the problem every earlier section left too: none of these agents is useful unless you can measure whether it works. An **eval** is that measurement.

## Why this exists

A unit test asserts `f(x) == y`. That works because `f` is deterministic, its inputs can be enumerated or partitioned, and "correct" is crisp. An LLM feature breaks all three assumptions:

1. **The output is a draw from a distribution (P1, P4).** The same input can pass on Monday and fail on Tuesday, even at temperature 0 ([§02](02-how-llms-work.md)). You can't unit-test a probability distribution; you can only measure a pass *rate* over many inputs and runs.
2. **The input space is open.** Users write anything, so you can only sample cases and check that the sample resembles production.
3. **"Correct" is often fuzzy.** "Is this summary faithful?" has no `==`. Someone, or something, has to judge.

Then add change. Every prompt edit ([§05](05-api-and-prompting.md)), harness change ([§19](19-harness-engineering.md)) or model upgrade (P12) shifts behavior somewhere you weren't looking. Anthropic describes the breaking point as users reporting that the agent "feels worse" while the team is "flying blind," and notes that teams with evals can "upgrade in days" when a new model ships, while teams without them face weeks of testing.

If you've written dbt tests, you know the shape of the answer. You never prove a pipeline correct. You assert properties (`not_null`, `unique`, `accepted_values`) on every run and fail the build when they break. Evals do the same for model output, with two twists: some assertions need a model to check them, and every result is a statistic.

## How it works (under the hood)

### Vocabulary and anatomy

Anthropic's "Demystifying evals for AI agents" (Jan 9, 2026) defines the terms. A **task** is one input with success criteria, and a **suite** is a set of tasks. A **trial** is one attempt; you run several because outputs vary. A **grader** scores one aspect of a trial. The **transcript** (or trace, or trajectory) records the whole trial. The **outcome** is the environment's final state: an agent may *say* "booked," but the outcome is whether the reservation row exists. The **eval harness** runs, grades and aggregates; it evaluates the model together with its agent harness ([§19](19-harness-engineering.md)).

```text
golden set ──► system under test ──► transcripts ──► graders ──► scores ──► aggregate ± CI ──► decision
(tasks,        (prompt, model,       (k trials       (code,      (per task,  (per metric,       (ship, block
 slices)        tools, harness)       per task)       judge,      per trial)  per slice)          or investigate)
                                                      human)
```

### Step zero: error analysis

The tempting first move is to pick metrics such as "helpfulness" or "coherence." Hamel Husain and Shreya Shankar, whose evals FAQ distills questions from more than 5,000 students, argue for the opposite: read your data first.

1. **Gather traces.** A **trace** is the full record of one interaction, from the user's first message to the final response, including tool calls and retrievals. Use real traffic, or synthetic inputs if you have none yet.
2. **Open coding.** A domain expert reads traces and writes free-form notes on what went wrong. Note the *first* failure in each trace, because upstream errors cause downstream ones.
3. **Axial coding.** Group the notes into a **failure taxonomy** (named failure categories) and count each one. They call this the most important step; an LLM can help cluster.
4. **Iterate to saturation.** Stop when new traces stop revealing new failure modes, which qualitative researchers call **theoretical saturation**. They suggest at least 100 traces.

Open and axial coding come from grounded theory in the social sciences, where categories *emerge* from data instead of being imposed. A support agent's taxonomy might look like this (illustrative numbers from 120 traces):

| Failure category | Count | What it becomes |
|---|---|---|
| Promised a refund the policy doesn't allow | 14 | LLM-judge eval |
| Didn't mention the order ID it looked up | 9 | Code eval (regex) |
| Called `update_address` before verifying identity | 6 | Code eval on the tool log, plus a guardrail |
| Retrieval returned last year's policy | 5 | Bug fix in the index; no eval |

This works because an LLM's failure space is unbounded and specific to your prompt, data and users, so generic metrics can miss your failures entirely. Shankar et al. (2024) observed **criteria drift**: "users need criteria to grade outputs, but grading outputs helps users define criteria." You can't fully write the rubric before seeing outputs. The FAQ's rules follow: write evaluators for "errors you discover, not errors you imagine," prefer binary pass/fail to 1–5 scales (adjacent points are subjective), and expect error analysis and evaluation to take 60–80% of development time.

### Graders: code, model and human

**Code-based graders** check what a program can decide: normalized match, regex, schema validation ([§06](06-structured-outputs.md)), unit tests, query results, the environment's end state, or which tools were called with which arguments. They're fast, cheap and reproducible, but rigid: Opus 4.5 first scored 42% on CORE-Bench partly because a grader rejected "96.12" when it expected "96.124991…", and after Anthropic fixed grading bugs and ambiguous tasks and loosened the scaffold, it scored 95%.

**LLM-as-judge** is a second model call that reads the input, the output and a rubric and returns a verdict. Forms include rubric scoring, natural-language assertions ("the reply states the return window"), **pairwise comparison** (is A or B better?) and comparison to a reference answer. The judge is sampled too (P4), and Zheng et al. (2023) documented three biases:

- **Position bias:** in pairwise comparisons, judges favor one slot. Swap the order and count a win only if it holds both ways.
- **Verbosity bias:** judges favor longer answers.
- **Self-enhancement (self-preference) bias:** a model favors outputs resembling its own.

GPT-4 judges agreed with human preferences over 80% of the time in that study, about as often as humans agree with each other: useful, not trustworthy blind. The remedy is **calibration**: treat the judge as a classifier and measure it against human labels. Husain and Shankar suggest at least 50 labeled passes and 50 fails, split into train (examples allowed in the judge prompt), dev (for iterating) and test (used once, at the end). Report the **true positive rate (TPR)**, the share of real failures the judge catches, and the **true negative rate (TNR)**, the share of good outputs it passes. Use one judge per failure mode, give it a way out ("Unknown"), and wrap the judged text in tags as data, since it can contain instructions aimed at the judge (P9). Should a model judge its own output? Self-preference bias argues against it; Husain and Shankar find the same model usually fine for a narrow binary task that agrees with humans. Calibration decides.

**Human graders** are the gold standard and the slowest option. Their main jobs are calibrating judges and covering subjective domains. **Inter-annotator agreement**, how often two humans give the same verdict, tells you whether the task itself is well defined. Anthropic's rule of thumb: deterministic graders where possible, LLM graders where necessary, humans judiciously for validation.

### Datasets

A **golden set** is a curated collection of tasks with reference answers or criteria, versioned together with its graders (change either and old scores stop being comparable). Anthropic: "20-50 simple tasks drawn from real failures is a great start," because early changes have large effects that small samples detect. Three properties matter more than size:

- **Unambiguous tasks.** "A good task is one where two domain experts would independently reach the same pass/fail verdict." A reference solution that passes every grader proves the task is solvable. With frontier models, 0% across 100 trials usually means a broken task.
- **Balance and slices.** Anthropic's web-search evals included queries where Claude should search and queries where it shouldn't, because a one-sided set rewards searching for everything. Tag each case with a **slice** (task type, language, customer tier) and report per slice, since an aggregate can rise while one slice collapses.
- **Synthetic cases** fill gaps when you lack traffic or need rare failures: generate inputs along chosen dimensions (persona × intent × difficulty), run them through the full system, and review the traces.

Keep test data out of anything you tune. If few-shot examples, judge examples or prompt edits came from the test set, the score measures memorization, and even repeated rounds of "read dev failures, edit prompt" leak information. Make ground truth structurally unreachable, too: Anthropic saw Claude gain an unfair advantage on some tasks by reading git history left by earlier trials.

### Snippet: a tiny eval runner

A three-case golden set, a code grader, a stubbed LLM judge whose request body has the real Messages API shape, and pass rates with a **confidence interval**, a range that would contain the true rate 95% of the time across repeated samples.

```python
import math, re

DATASET = [  # a tiny golden set; each case says what a passing reply must contain
    {"id": "t1", "slice": "refund", "input": "Refund status for order 1234?", "must": r"\b1234\b"},
    {"id": "t2", "slice": "shipping", "input": "Order 5678 hasn't arrived.", "must": r"\b5678\b"},
    {"id": "t3", "slice": "refund", "input": "I want my money back now!", "must": r"polic(y|ies)"},
]

def app(text):  # the system under test; in real life, your prompt + model call
    ids = re.findall(r"\b\d{4}\b", text)
    return f"Sorry about that. I've checked order {ids[0]}." if ids else "Refund guaranteed today!"

def code_grader(output, case):  # deterministic: fast, cheap, reproducible
    return re.search(case["must"], output, re.IGNORECASE) is not None

def judge_request(output, case):  # the JSON body a real judge would POST to /v1/messages
    return {"model": "claude-sonnet-5-5", "max_tokens": 1024,
            "system": "You check ONE property. First line: PASS or FAIL. Then one sentence why.",
            "messages": [{"role": "user", "content":
                f"<ticket>{case['input']}</ticket>\n<reply>{output}</reply>\n"
                "Does the reply avoid promising refunds or dates the policy does not state?"}]}

def stub_judge(output, case):  # offline stand-in for client.messages.create(**judge_request(...))
    judge_request(output, case)
    return "guarantee" not in output.lower()

def wilson(k, n, z=1.96):  # 95% confidence interval for a pass rate; sane at small n
    p, d = k / n, 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return centre - half, centre + half

rows = []
for c in DATASET:  # run every case, grade it with both graders
    out = app(c["input"])
    rows.append({"has_required_fact": code_grader(out, c), "no_overpromise": stub_judge(out, c)})
for metric in ("has_required_fact", "no_overpromise"):  # one binary metric per failure mode
    k, n = sum(r[metric] for r in rows), len(rows)
    lo, hi = wilson(k, n)
    print(f"{metric}: {k}/{n} = {k / n:.0%}, 95% CI [{lo:.0%}, {hi:.0%}]")
```

```text
has_required_fact: 2/3 = 67%, 95% CI [21%, 94%]
no_overpromise: 2/3 = 67%, 95% CI [21%, 94%]
```

Each failure mode gets its own binary metric. To make the judge real, pass the body to `anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]).messages.create(...)`, check `stop_reason`, and parse the first line; structured outputs ([§06](06-structured-outputs.md)) make that deterministic. OpenAI's Responses API takes `input` instead of `messages`, and Gemini takes `contents`. Then read the interval: 2 of 3 is consistent with anything from 21% to 94%. (The **Wilson interval** stays sensible at small n and near 0% or 100%.)

### Statistical honesty

Evan Miller's "Adding Error Bars to Evals" (Anthropic, Nov 2024) treats eval questions as a sample from an unseen "question universe," so your score is an estimate of that universe's average.

- **Report an interval.** For pass rate p over n independent cases, the standard error is √(p(1−p)/n) and a 95% interval is about p ± 1.96 standard errors. Near 50%, that's roughly ±1/√n: ±10 points at n = 100, ±5 at n = 400.
- **Cluster related cases.** Ten questions about one document aren't ten independent samples; Miller found clustered standard errors "can be over three times as large as naive standard errors."
- **Average over trials** per task to shrink the variance that sampling adds (P4).
- **Compare paired.** Run both variants on the same cases and analyze per-case differences. Frontier models' per-question scores correlate at 0.3–0.7, so pairing removes much of the noise.
- **Plan the sample size.** **Power analysis** gives the n needed to detect the smallest change you'd act on.

The judge and the environment add variance too: run the judge twice on one output, and note that trials failing for a shared infrastructure reason "are not independent" (Anthropic). A 2-point gain on 50 cases is noise.

### Offline and online evals

**Offline evals** run a fixed dataset before deployment: reproducible and invisible to users, but limited to inputs you thought of. **Online evals** run graders asynchronously on sampled production traffic, which has no reference answers, so they rely on reference-free graders: heuristics, calibrated judges and user signals. CI evals "protect against known regressions before deployment," in Husain and Shankar's words, while online monitoring finds production failures and estimates their frequency; a failure found online becomes an offline test case. Anthropic likens the layers, with A/B tests and transcript review, to the Swiss cheese model: each has holes, and stacking them catches what slips through one. Online evals need tracing ([§27](27-observability.md)).

### Agent evals

Agents add turns, tools and state, so mistakes compound (P8), and one task can be solved in many ways.

- **Outcome vs trajectory.** Grade the outcome whenever possible. τ-bench (Yao et al., Sierra, Jun 2024) compares the database at the end of a conversation with an annotated goal state. Grade the **trajectory**, the sequence of steps, only for what the end state can't show: rules ("verified identity first"), budgets (turns, tool calls) and tone. Anthropic calls exact tool-sequence checks "too rigid," because "agents regularly find valid approaches that eval designers didn't anticipate"; Opus 4.5 "failed" a τ²-bench task by finding a policy loophole that was better for the user.
- **Environment-based evals.** The agent works in a sandbox reset per trial: a repository with tests (SWE-bench Verified, Terminal-Bench), a simulated website (WebArena), a desktop (OSWorld), or APIs plus an LLM-simulated user (τ-bench).
- **Transcript review.** A failed trial means the agent erred or the grader rejected a valid solution, and only reading tells you which.
- **Cost and latency are metrics.** Record tokens, turns, time to first token and dollars per task beside the pass rate. Two points better at 3× the cost is a product decision (P10).

Agents also need two aggregates. **pass@k** (Chen et al., 2021) is the probability that at least one of k trials succeeds; it fits work where a verifier can pick a winner, such as patches filtered by tests. **pass^k** ("pass hat k," from τ-bench) is the probability that *all* k trials succeed. It measures consistency, which customer-facing agents need: each user gets one trial, so a 75% agent fails one user in four. τ-bench reported a gpt-4o agent averaging over 60% per trial on retail tasks, with pass^8 below 25%. From n trials with c successes per task:

```python
from math import comb

# Eight independent trials per task (1 = the end state matched the goal state)
trials = {
    "refund_simple":  [1, 1, 1, 1, 1, 1, 1, 1],
    "refund_partial": [1, 1, 0, 1, 1, 0, 1, 1],
    "change_address": [1, 0, 1, 1, 0, 1, 0, 1],
    "flag_fraud":     [0, 0, 1, 0, 0, 0, 0, 0],
}

def pass_at_k(n, c, k):    # P(at least one of k trials passes); Chen et al. 2021
    return 1 - comb(n - c, k) / comb(n, k)   # comb() is 0 when n - c < k

def pass_hat_k(n, c, k):   # P(all k trials pass); "pass^k", Yao et al. 2024 (tau-bench)
    return comb(c, k) / comb(n, k)

def mean_over_tasks(metric, k):
    return sum(metric(len(t), sum(t), k) for t in trials.values()) / len(trials)

for k in (1, 2, 4, 8):
    print(f"k={k}:  pass@k = {mean_over_tasks(pass_at_k, k):.2f}"
          f"   pass^k = {mean_over_tasks(pass_hat_k, k):.2f}")
```

```text
k=1:  pass@k = 0.62   pass^k = 0.62
k=2:  pass@k = 0.78   pass^k = 0.47
k=4:  pass@k = 0.88   pass^k = 0.32
k=8:  pass@k = 1.00   pass^k = 0.25
```

Same 32 trials, and the headline is "100%" or "25%" depending on the metric, so always name it. The estimates are per task, then averaged, because tasks differ in difficulty: one always-passing task and one rarely-passing task don't behave like two 50% tasks. Anthropic also separates **capability evals**, which start low and give you a hill to climb, from **regression evals**, which sit near 100% and catch backsliding. Saturated capability tasks "graduate" into the regression suite.

### Public benchmarks vs your own evals

Public benchmarks (SWE-bench Verified, Terminal-Bench, τ²-bench, BrowseComp) compare models on shared tasks, but fail as decision tools in three ways:

- **Saturation.** "An eval at 100% tracks regressions but provides no signal for improvement." In January 2026 Anthropic described frontier models as "nearing saturation at >80%" on SWE-bench Verified, where large capability gains appear as small score changes.
- **Contamination.** Benchmark questions leak into training data. On GSM1k (Zhang et al., May 2024), a fresh mirror of the GSM8k math set, some model families dropped up to 8%, in line with how readily they reproduced GSM8k examples; frontier models showed little overfitting.
- **Goodhart's law** ([§12](12-agentic-design-patterns.md)): a measure that becomes a target stops measuring. "The Leaderboard Illusion" (Singh et al., Apr 2025) found undisclosed private testing let some providers try many variants on Chatbot Arena and publish the best, including 27 private Meta variants before Llama 4.

A score also describes a model-harness pair ([§19](19-harness-engineering.md)), not your harness or users. Shortlist with benchmarks and decide with your own evals, remembering that Goodhart applies to them too.

### The eval-driven development debate

**Eval-driven development** borrows test-driven development's order: write evals first, then build until they pass. Anthropic's post recommends it ("build evals to define planned capabilities before agents can fulfill them"). Xia et al., "Evaluation-Driven Development and Operations of LLM Agents" (arXiv 2411.13768, Nov 2024, revised Nov 2025), goes further, deriving a process model and reference architecture (EDDOps) from a multivocal literature review in which evaluation is "a continuous, governing function rather than a terminal checkpoint" spanning offline and online evaluation.

Husain and Shankar answer "Should I practice eval-driven development?" with "Generally no," because "LLMs have infinite surface area for potential failures. You can't anticipate what will break." Up-front evals measure imagined failures, and criteria drift says you can't fully specify them before seeing outputs. Their exception: a constraint you know exactly, like "never mention competitors."

The positions are closer than the labels. Anthropic also says to start from "what you already test manually" and from "real failures," and EDDOps mainly says evaluation should run continuously, which nobody disputes. The live question is whether you can write useful evals before you have outputs. A workable synthesis: write evals first for what you can specify (hard constraints, required behaviors, bets on the next model) and grow the rest from error analysis. As of October 2026, evals are established; "evals first" is contested.

### Evals as regression tests in CI

```text
PR changes a prompt, tool, model ID or harness
   ▼
CI: regression suite (~100 cases, mostly code graders, a few trials each)
   ▼  paired comparison against main's stored scores
gate: block on any hard-check failure (safety, data handling)
      block if a metric drops more than the noise floor; warn on smaller drops
      post per-slice deltas, cost and latency on the PR
   ▼
nightly: full suite with LLM judges, capability evals, more trials
```

This is the dbt pattern: tests run on every build, each set to `warn` or `error`. Two differences matter. Data tests are deterministic given the data; evals are statistical, so gates need tolerance bands from the measured noise floor or the build flaps. And each run costs money, so CI uses a small, mostly deterministic set (Husain and Shankar favor assertions over judges there). Pin the model snapshot, judge, prompt and dataset versions, and cache results by case, prompt hash and model. Rare, high-stakes behaviors such as deleting data get a hard-fail tier, because an average diluted by easy cases hides them.

### Failure modes

- **Generic metrics** no observed failure motivated, which "create false confidence" (Husain and Shankar).
- **Uncalibrated judges,** or one judge grading everything.
- **Broken tasks** that punish correct behavior. METR found tasks asking agents to reach a score threshold but crediting only scores above it.
- **Leaky ground truth** in the sandbox, repository history or prompt.
- **Noise read as signal:** no intervals, no pairing, one trial per task, timeouts scored as wrong answers.
- **Stale sets.** Re-run error analysis on 100+ fresh traces after significant changes; two-to-four-week cycles are typical.

## Comparison

**Grader types**

| Grader | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Code: match, regex, schema | Normalize, then compare or validate | Fast, free, deterministic | Rejects valid variations | Labels, formats, required facts |
| Code: tests, execution, state checks | Run the output or inspect the end state | Grades what actually happened | Needs a resettable environment | Coding, data and tool-using agents |
| LLM judge: rubric or assertion | A model returns PASS/FAIL against a rubric | Open-ended output at scale | Sampled, biased, costs a call | Tone, faithfulness, policy, once calibrated |
| LLM judge: pairwise | A model picks the better of two outputs | More consistent than absolute scores | Position and verbosity bias; relative only | Comparing two prompts or models |
| Human review | Experts label outputs | The reference standard | Slow, costly, raters disagree | Calibration; subjective or high-stakes work |

**Evaluation methods**

| Method | Answers | Strength | Weakness |
|---|---|---|---|
| Offline suite | "Did this change break or improve known cases?" | Reproducible; runs on every commit | Only covers collected inputs |
| Online evals | "How often does this fail in production?" | Real inputs | No references; needs tracing ([§27](27-observability.md)) |
| A/B test | "Do users do better with B?" | Real outcomes | Slow; says little about why |
| Transcript review | "What is going wrong?" | Finds new failure modes | Doesn't scale |

**Aggregates:** pass@1 (= pass^1) is the default headline; pass@k suits retry-with-verifier products; pass^k suits one-attempt, consistency-critical products; cost and latency per completed task belong next to all of them.

## What it didn't solve

Offline evals cover the inputs you thought to collect, graded against failures you've already found. Real users phrase things differently, combine features nobody tested and change over time, and the model behind an alias can change too. Online evals can't run without a record of what happened in each request. You need to capture every model call, tool call and retrieval in production as it happens.

→ Next: [§27 Observability and Tracing](27-observability.md)

## Check your understanding

**Q: Why can't you test an LLM feature with ordinary unit tests?**

A unit test assumes a deterministic function, but an LLM samples its output (P4), so one passing run is a sample of one. The input space is open, and "correct" is often a judgment rather than an equality. So you measure a rate over a dataset and repeated trials, with graders that may include a model or a human. Unit tests still belong around the deterministic code: parsers, tools, schema validation.

**Q: Why start with error analysis instead of standard metrics like helpfulness?**

An app's failures are specific to its prompt, data and users, so generic metrics can miss them and give false confidence. Reading and coding traces shows which failures occur and how often, and criteria drift means you couldn't have written the rubric beforehand. Many findings are bugs to fix, not evals to maintain. The cost is expert time, and generic metrics still help find traces worth reading.

**Q: What would happen if you shipped an LLM judge without calibrating it against human labels?**

The judge is sampled and biased (position, verbosity, self-preference), so its scores may track its quirks rather than your quality bar. You could then tune prompts toward what the judge likes, which is Goodhart's law, without noticing. TPR and TNR on a held-out labeled set tell you how far to trust it. For checks code can decide, skip the judge.

**Q: pass@k vs pass^k: which should a customer-support agent report?**

pass^k, because each customer gets one conversation and the business needs the agent to handle the same request correctly every time. pass@k credits a task if any of k attempts succeeds, which fits products where a verifier picks the winner, such as patches filtered by tests. The same trials can give pass@8 = 100% and pass^8 = 25%. Report pass@k only if the product really retries with an automatic checker.

**Q: A prompt change moves your pass rate from 78% to 82% on 60 cases. Should you ship it?**

Not on that evidence. At n = 60 each rate's 95% interval is about ±10 points, so a 4-point move is inside the noise. Run a paired comparison with several trials per case, check slices for hidden regressions, and compare cost and latency. Shipping a cheap change that shows no harm is fine, but don't call it an improvement.

**Q: Outcome grading vs trajectory grading: when is each one wrong?**

Outcome grading misses cases where the path matters, such as reaching the right state by skipping identity verification or burning 40 tool calls. Trajectory grading is wrong when it demands one sequence, because agents find valid routes the designer didn't foresee. Grade outcomes by default and add targeted trajectory checks for rules and budgets.

**Q: When is it right to write an eval before building the feature?**

When you can specify success exactly in advance: hard constraints ("never call `refund` without verification"), required formats, or capability bets for the next model. Otherwise the failure surface is too large to anticipate and criteria drift sends early evals after imagined failures. The middle path is to write the evals you can specify and grow the rest from error analysis.

## Takeaways

- Correctness is a rate (P4): an eval is a dataset, graders and repeated trials, and its result is a statistic with an interval.
- Start with error analysis: read about 100 traces, open-code them, cluster them into a taxonomy, and write evals for failures that matter.
- Use code graders where possible, calibrated LLM judges (TPR and TNR) where necessary, and humans for calibration.
- Keep golden sets unambiguous, balanced and sliced, and keep test data out of anything you tune.
- For agents, grade outcomes in reset environments, read transcripts, and say whether you report pass@k or pass^k.
- Benchmarks shortlist; saturation, contamination and Goodhart's law make your own evals the deciding test.
- Run regression evals in CI like dbt tests, with tolerance bands from the noise floor, pinned versions, and cost and latency beside quality.

## Sources

- Anthropic Engineering, Mikaela Grace, Jeremy Hadfield, Rodrigo Olivares and Jiri De Jonghe, "Demystifying evals for AI agents" (Jan 9, 2026): https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Hamel Husain and Shreya Shankar, "AI Evals: Everything You Need to Know" (evals FAQ): https://hamel.dev/blog/posts/evals-faq/
- Shankar, Zamfirescu-Pereira, Hartmann, Parameswaran and Arawjo, "Who Validates the Validators? Aligning LLM-Assisted Evaluation of LLM Outputs with Human Preferences" (Apr 2024): https://arxiv.org/abs/2404.12272
- Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (Jun 2023): https://arxiv.org/abs/2306.05685
- Evan Miller, "Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations" (Nov 2024): https://arxiv.org/abs/2411.00640 ; Anthropic summary (Nov 19, 2024): https://www.anthropic.com/research/statistical-approach-to-model-evals
- Yao, Shinn, Razavi and Narasimhan, "τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains" (Jun 2024): https://arxiv.org/abs/2406.12045
- Chen et al., "Evaluating Large Language Models Trained on Code" (Jul 2021), the pass@k estimator: https://arxiv.org/abs/2107.03374
- Xia, Lu, Zhu, Xing, Zhao and Zhang, "Evaluation-Driven Development and Operations of LLM Agents: A Process Model and Reference Architecture" (Nov 2024, rev. Nov 2025): https://arxiv.org/abs/2411.13768
- Zhang et al., "A Careful Examination of Large Language Model Performance on Grade School Arithmetic" (GSM1k, May 2024): https://arxiv.org/abs/2405.00332
- Singh et al., "The Leaderboard Illusion" (Apr 2025): https://arxiv.org/abs/2504.20879
- Anthropic, Messages API reference: https://docs.claude.com/en/api/messages
