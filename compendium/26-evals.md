# 26. Evals

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

Parts 1–6 told a chronological story, from the transformer to voice agents. Part 7 steps out of the timeline, because measuring and improving apply to every era: a single 2022-style prompt, a RAG pipeline ([§09](09-rag.md)) or a 2026 coding agent. Two principles drive this section. Output is sampled, so correctness is a rate (P4). Generating output is cheap and checking it is not, so verification is the bottleneck (P8). [§25](25-voice-agents.md) closed the archetypes with voice agents and left the problem that every earlier section left too: none of these systems is useful unless you can measure whether it works. An **eval** is that measurement.

## Why this exists

A unit test asserts `f(x) == y`. That works because `f` is deterministic, its inputs can be enumerated or at least partitioned into classes, and "correct" is a crisp property. An LLM feature breaks all three assumptions.

1. **The output is a draw from a distribution (P1, P4).** The same input can pass on Monday and fail on Tuesday, even at temperature 0 ([§02](02-how-llms-work.md)). One passing run is a sample of size one. What you can measure is a pass *rate* over many inputs and many runs.
2. **The input space is open.** Users write anything. You can't enumerate the cases, only sample them and check that the sample resembles production.
3. **"Correct" is often fuzzy.** "Is this summary faithful?" and "was the tone right?" have no `==`. Someone, or something, has to judge.

Then add change. Every prompt edit ([§05](05-api-and-prompting.md)), retrieval tweak, harness change ([§19](19-harness-engineering.md)) or model upgrade shifts behavior somewhere you weren't looking, and models get replaced every few months (P12). Without measurement, debugging is reactive. Anthropic describes the breaking point as the moment users report the agent "feels worse" after a change and the team is "flying blind." The same post makes the economic case: when a new model ships, teams with evals "can quickly determine the model's strengths, tune their prompts, and upgrade in days," while teams without them face weeks of testing.

If you've written dbt tests, you already know the shape of the answer. You never prove a pipeline correct. You assert properties (`not_null`, `unique`, `accepted_values`) over the data on every run, and the build fails when they break. Evals apply the same idea to model output, with two twists: some assertions need a model to check them, and every result is a statistic.

## How it works (under the hood)

### Vocabulary and anatomy

Anthropic's "Demystifying evals for AI agents" (Jan 9, 2026) gives a clean vocabulary:

- A **task** (or test case) is one input with defined success criteria. An **eval suite** is a set of tasks with a shared goal.
- A **trial** is one attempt at a task. Outputs vary, so you run several trials.
- A **grader** is logic that scores one aspect of a trial. A task can have several graders.
- The **transcript** (also called a trace or trajectory) is the full record of a trial: messages, tool calls and intermediate results.
- The **outcome** is the final state of the environment. A flight-booking agent may *say* "your flight is booked"; the outcome is whether the reservation row exists.
- The **eval harness** runs the tasks, records transcripts, grades them and aggregates the scores. Don't confuse it with the **agent harness** of [§19](19-harness-engineering.md). When you evaluate "an agent," you're evaluating the model and its agent harness together.

```text
golden set ──► system under test ──► transcripts ──► graders ──► scores ──► aggregate ± CI ──► decision
(tasks,        (prompt, model,       (k trials       (code,      (per task,  (per metric,       (ship, block
 slices)        tools, harness)       per task)       judge,      per trial)  per slice)          or investigate)
                                                      human)
```

### Step zero: error analysis

The tempting first move is to pick metrics such as "helpfulness," "coherence" or "toxicity." Hamel Husain and Shreya Shankar, who teach evals and compiled a widely used FAQ from the questions of more than 5,000 students, argue for the opposite: read your data first. Their process, adapted from qualitative research, has four steps:

1. **Gather traces.** A **trace** is the complete record of one interaction, from the user's first message to the final response, including every tool call and retrieval. Use real traffic, or synthetic inputs if you don't have traffic yet.
2. **Open coding.** A domain expert reads traces and writes free-form notes on what went wrong, like a journal. Note the *first* failure in each trace, because upstream errors cause downstream ones. Annotate the first 30 or so yourself before letting an agent help.
3. **Axial coding.** Group the notes into a **failure taxonomy**, a set of named failure categories, and count each one. They call this the most important step. An LLM can help with the clustering.
4. **Iterate to saturation.** Keep reviewing until new traces stop revealing new failure modes, which qualitative researchers call **theoretical saturation**. They suggest reviewing at least 100 traces.

Open and axial coding come from grounded theory in the social sciences, where categories are meant to *emerge* from the data instead of being imposed on it. After 120 traces, a support agent's taxonomy might look like this (illustrative numbers):

| Failure category | Count | What it becomes |
|---|---|---|
| Promised a refund the policy doesn't allow | 14 | LLM-judge eval (needs judgment) |
| Didn't mention the order ID it looked up | 9 | Code eval (a regex) |
| Called `update_address` before verifying identity | 6 | Code eval on the tool-call log, plus a guardrail |
| Retrieval returned last year's policy | 5 | A bug fix in the index; no eval needed |
| Rambling answers | 2 | Ignore for now |

The reason this works is mechanical. An LLM's failure space is unbounded and specific to your prompt, data and users, so generic metrics measure qualities that may have nothing to do with your failures. Shankar and colleagues (2024) observed **criteria drift**: "users need criteria to grade outputs, but grading outputs helps users define criteria." You can't fully write the rubric before you've seen outputs. Error analysis also turns up plain bugs, like the fourth row, which need a fix rather than a permanent eval. The FAQ's rules follow from this. Write evaluators for "errors you discover, not errors you imagine." Prefer binary pass/fail to 1–5 scales, because adjacent points are subjective and annotators drift to the middle. And expect to spend 60–80% of development time on error analysis and evaluation.

### Graders: code, model and human

**Code-based graders** check what a program can decide: exact or normalized match, regex, JSON schema validation ([§06](06-structured-outputs.md)), unit tests on generated code, running a query and comparing results, inspecting the environment's end state, and checking which tools were called with which arguments. They're fast, cheap, objective and reproducible. Their weakness is rigidity. Anthropic reports that Opus 4.5 first scored 42% on CORE-Bench, partly because a grader rejected "96.12" when it expected "96.124991…". After the team fixed grading bugs and ambiguous tasks and loosened the scaffold, the score was 95%. Normalize both sides before you compare.

**LLM-as-judge** means a second model call that reads the input, the output and a rubric, and returns a verdict. Common forms are rubric scoring, natural-language assertions ("the reply states the return window"), **pairwise comparison** (which of A and B is better?) and reference-based grading (compare against a known good answer). A judge is flexible and handles open-ended output, but its output is sampled too (P4), so it needs the same scrutiny as the system it grades. Zheng et al. (2023) documented three biases:

- **Position bias.** In pairwise comparisons, judges favor one slot. Randomize or swap the order, and count a win only if it holds both ways.
- **Verbosity bias.** Judges favor longer answers. Tell the judge not to reward length, then check that it doesn't.
- **Self-enhancement (self-preference) bias.** A model tends to prefer outputs that resemble its own.

The same paper found GPT-4 judges agreed with human preferences over 80% of the time, about as often as humans agree with each other. That's useful, but not good enough to trust blind. The remedy is **calibration**: treat the judge as a classifier and measure it against human labels. Husain and Shankar suggest at least 50 human-labeled passes and 50 fails, split into a train set (examples you may put in the judge's prompt), a dev set (for iterating on the prompt) and a test set (used only at the end). Report two numbers. The **true positive rate (TPR)** is the share of real failures the judge catches. The **true negative rate (TNR)** is the share of good outputs it correctly passes.

A few more rules appear in both sources. Use one judge per failure mode, not one judge for "quality." Give the judge a way out, such as answering "Unknown," so it doesn't invent a verdict. Wrap the judged text in tags as data, because the output being judged can contain instructions aimed at the judge (P9). The sources differ on whether a model may judge its own output. Self-enhancement bias suggests keeping the model under test away from judging itself. Husain and Shankar say the same model is usually fine for a narrow binary task, because what matters is measured agreement with humans. Either way, calibration decides.

**Human graders** (subject-matter experts, spot checks, crowdsourced raters) are the gold standard, and the slowest and most expensive option. In a mature setup their main jobs are calibrating model graders and covering subjective domains. **Inter-annotator agreement**, how often two humans give the same verdict, tells you whether the task itself is well defined. If experts disagree, no grader can be right.

Anthropic's rule of thumb sums it up: deterministic graders where possible, LLM graders where necessary, and human graders judiciously, for validation.

### Datasets

A **golden set** is a curated, versioned collection of tasks with reference answers or criteria. Version it together with its graders, because changing either makes old scores incomparable. Anthropic suggests that "20-50 simple tasks drawn from real failures is a great start": early changes have large effects, and a small sample can detect a large effect. Three properties matter more than size.

- **Unambiguous tasks.** "A good task is one where two domain experts would independently reach the same pass/fail verdict." Write a reference solution that passes every grader. It proves the task is solvable and the graders work. With frontier models, 0% across 100 trials usually means a broken task, not an incapable agent.
- **Balance and slices.** Test both directions. Anthropic's web-search evals included queries where Claude *should* search and queries where it shouldn't, because a one-sided set rewards searching for everything. Tag each case with a **slice**, a segment such as task type, language or customer tier, and report per slice, because the aggregate can rise while one slice collapses.
- **Synthetic cases** fill gaps. Generate inputs along chosen dimensions (persona × intent × difficulty) when you lack traffic or need a rare failure, then run them through the full system and review the traces. They tell you less about real users than real data does.

Keep test data out of anything you tune. If your few-shot examples, your judge's examples or your hand-tuned prompt came from the test set, the score measures memorization. Husain and Shankar point out that overfitting happens even without copying, because every round of "read the dev failures, edit the prompt" leaks information about the dev set into the prompt. Hold out a test set you rarely touch, and make ground truth structurally unreachable by the agent. Anthropic saw Claude gain an unfair advantage on some tasks by reading git history left over from earlier trials.

### Snippet: a tiny eval runner

The runner below has a three-case golden set, a code grader, a stubbed LLM judge whose request body has the real Messages API shape, and a pass rate reported with a **confidence interval**: a range that, across repeated samples, would contain the true rate 95% of the time.

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

Three things to notice. First, each failure mode from the taxonomy gets its own binary metric instead of one blended score. Second, making the judge real takes a few lines: send the body with the Anthropic SDK (`anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]).messages.create(**judge_request(out, c))`), check `stop_reason`, and parse the first line of the text block. Structured outputs ([§06](06-structured-outputs.md)) make that parse deterministic. OpenAI's Responses API takes `input` where Anthropic takes `messages`, and Gemini takes `contents`, but the judge works the same way. Third, look at the interval. A result of 2 out of 3 is consistent with anything from 21% to 94%, so three cases tell you almost nothing. The **Wilson interval** used here is a confidence-interval formula that stays sensible at small n and near 0% or 100%.

### Statistical honesty

An eval score is an estimate. Evan Miller's "Adding Error Bars to Evals" (Anthropic, Nov 2024) treats eval questions as a sample from an unseen "question universe." The number you care about is the average over that universe, and your score estimates it with error. His recommendations, plus two practical additions:

- **Report a confidence interval.** For a pass rate p over n independent cases, the standard error is √(p(1−p)/n), and a 95% interval is about p ± 1.96 standard errors. Near p = 50%, the half-width is roughly 1/√n: ±10 points at n = 100 and ±5 at n = 400.
- **Cluster related cases.** Ten questions about one document aren't ten independent samples. Miller found that clustered standard errors on popular evals "can be over three times as large as naive standard errors."
- **Average over trials.** Run each task several times and score the per-task average. That shrinks the variance that sampling adds (P4).
- **Compare paired.** To compare prompt A with prompt B, run both on the same cases and analyze per-case differences. Miller reports that frontier models' per-question scores correlate at 0.3–0.7, so pairing removes a lot of noise for free.
- **Plan the sample size first.** **Power analysis** tells you how many cases you need to detect the smallest change you would act on. If the noise is larger than that change, the eval can't answer your question.
- **Measure every source of variance.** The model under test is one source. The judge is another, so run it twice on the same output. The environment is a third: flaky tools and shared state make trials fail together, and Anthropic notes that such trials "are not independent."

With that in mind, a 2-point gain on 50 cases is noise.

### Offline and online evals

**Offline evals** run a fixed dataset before deployment. They're reproducible, cheap to repeat and invisible to users, but limited to the inputs you thought of. **Online evals** run graders on a sample of live production traffic, usually asynchronously. Production traffic has no reference answers, so online evals lean on reference-free graders: heuristics, calibrated judges and user signals. Husain and Shankar put the split this way: CI evals "protect against known regressions before deployment," while online monitoring finds failures in production traffic "and estimate[s] how often they occur." The two connect, because a failure found online becomes an offline test case. A/B tests sit on top, measuring real user outcomes, but slowly. Anthropic compares the layers to the Swiss cheese model from safety engineering: every layer has holes, and stacking layers catches what slips through one. Online evals need tracing infrastructure, which is the subject of [§27](27-observability.md).

### Agent evals

Agents add turns, tools and state, so mistakes compound (P8) and the same task can be solved in many ways.

- **Outcome vs trajectory.** Grade the **outcome**, the end state, whenever you can: did the tests pass, does the database row exist, did the agent change the file and nothing else? τ-bench (Yao et al., Sierra, Jun 2024) grades by comparing the database at the end of a conversation with an annotated goal state. Grade the **trajectory**, the sequence of steps, only for properties the end state can't show: rules ("verified identity before changing the address"), efficiency (turns, tool calls) and tone. Anthropic warns that requiring an exact sequence of tool calls is "too rigid," because "agents regularly find valid approaches that eval designers didn't anticipate." Its post describes Opus 4.5 "failing" a τ²-bench airline task by finding a loophole in the policy that was better for the user.
- **Environment-based evals.** The agent works in a sandbox that resets for every trial: a repository with tests (SWE-bench Verified, Terminal-Bench), a simulated website (WebArena), a full desktop (OSWorld), or a set of APIs plus an LLM-simulated user (τ-bench). State left over between trials causes correlated failures or leaks answers.
- **Transcript review.** "You won't know if your graders are working well unless you read the transcripts and grades from many trials" (Anthropic). A failed trial means either the agent erred or the grader rejected a valid solution. Only reading tells you which.
- **Partial credit.** An agent that verified the customer and found the problem but failed to issue the refund did better than one that failed at step one, and the scores should show it.
- **Cost and latency are metrics.** Record tokens, turns, tool calls, time to first token and dollars per task next to the pass rate. A variant that is 2 points better at 3× the cost is a product decision, not an obvious win (P10).

Agents also need two different aggregates. **pass@k**, from code generation (Chen et al., 2021), is the probability that at least one of k trials succeeds. It suits work where you can try several times and verify, such as generating candidate patches and letting the test suite pick one. **pass^k** ("pass hat k"), introduced by τ-bench, is the probability that *all* k trials succeed. It measures consistency, which is what a customer-facing agent needs: each user gets one trial, so an agent that succeeds 75% of the time fails one user in four. At k = 1 the two metrics are identical. As k grows, pass@k rises toward 1 and pass^k falls toward 0. τ-bench reported that a gpt-4o function-calling agent succeeded on over 60% of retail tasks per trial on average, while its pass^8 fell below 25%. Given n trials per task with c successes, both have unbiased estimators:

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

Same agent, same 32 trials, and the headline is either "100%" or "25%" depending on the metric, so always say which one you report. The estimates are computed per task and then averaged, rather than raising the mean pass rate to the k-th power, because tasks differ in difficulty. An easy task that always passes and a hard one that rarely does don't behave like two 50% tasks.

Anthropic also separates **capability evals**, which start at a low pass rate and give the team a hill to climb, from **regression evals**, which should sit near 100% and catch backsliding. When capability tasks saturate, they "graduate" into the regression suite.

### Public benchmarks vs your own evals

Public benchmarks such as MMLU, SWE-bench Verified, Terminal-Bench, τ²-bench and BrowseComp let you compare models on shared tasks. As tools for your own decisions they fail in three ways.

- **Saturation.** "An eval at 100% tracks regressions but provides no signal for improvement." In January 2026, Anthropic described frontier models as "nearing saturation at >80%" on SWE-bench Verified. Near the ceiling, large capability gains show up as small score changes.
- **Contamination.** Benchmark questions leak into training data. Zhang et al. (May 2024) built GSM1k, a fresh set that mirrors the GSM8k math benchmark's style and difficulty, and found accuracy drops of up to 8% for some model families. The size of a model's drop correlated with how likely it was to generate GSM8k examples, a sign of memorization. The authors also note that frontier models showed little overfitting.
- **Goodhart's law** ([§12](12-agentic-design-patterns.md)): when a measure becomes a target, it stops being a good measure. Singh et al.'s "The Leaderboard Illusion" (Apr 2025) found that undisclosed private testing let some providers try many variants on Chatbot Arena and publish only the best score. It identified 27 private Meta variants tested before the Llama 4 release.

Two more gaps remain. A benchmark score describes a model-harness pair ([§19](19-harness-engineering.md)), and the harness isn't yours. And your users don't follow the benchmark's distribution. Use public benchmarks to shortlist models and your own evals to decide. Goodhart applies to your evals too: tune a prompt against the same dev set long enough and the prompt learns the set.

### The eval-driven development debate

**Eval-driven development** borrows the order of test-driven development: write the evals first, then build until they pass. Anthropic's post recommends it: "build evals to define planned capabilities before agents can fulfill them, then iterate until the agent performs well." An academic version goes further. Xia et al., "Evaluation-Driven Development and Operations of LLM Agents" (arXiv 2411.13768, first posted Nov 2024, revised Nov 2025), derives a process model and a reference architecture called EDDOps from a multivocal literature review. In it, evaluation is "a continuous, governing function rather than a terminal checkpoint," and offline and online evaluation share one feedback loop.

Husain and Shankar's FAQ answers "Should I practice eval-driven development?" with "Generally no." Their argument is about mechanism: unlike traditional software, "LLMs have infinite surface area for potential failures. You can't anticipate what will break." Evals written up front measure imagined failures, and criteria drift says you can't fully specify them before you've seen outputs. Their exception is a constraint you know exactly, such as "never mention competitors."

The positions are closer than the labels suggest. Anthropic also tells teams to start from "what you already test manually" and from tasks "drawn from real failures." EDDOps is mostly about evaluation running continuously across the lifecycle, which nobody disputes. The real disagreement is narrow: can you write useful evals before you have outputs to look at? A workable synthesis is to write evals first for what you can specify (hard constraints, required behaviors, capability bets on what the next model might manage) and grow everything else from error analysis. As of October 2026, evals are established practice, and "evals first" is contested.

### Evals as regression tests in CI

Once a suite exists, run it automatically on every change:

```text
PR changes a prompt, tool, model ID or harness
        │
        ▼
CI: regression suite (around 100 cases, mostly code graders, a few trials each)
        │   paired comparison against main's stored scores
        ▼
gate: block if any hard check fails (a safety or data-handling rule)
      block if a metric drops by more than the noise floor
      warn on smaller drops; post per-slice deltas, cost and latency on the PR
        │
nightly: full suite with LLM judges, capability evals and more trials
```

The data-engineering analogy holds closely. dbt runs tests on every build, and each test can be configured to `warn` or to `error`. Evals in CI work the same way, with two differences. Data tests are deterministic given the data, while evals are statistical, so gates need tolerance bands set from the measured noise floor, or the build will flap between pass and fail. And each run costs money and minutes, so CI uses a small, curated, mostly deterministic set; Husain and Shankar advise favoring assertions over LLM judges there. Pin everything that can move: the model snapshot, the judge model and prompt, and the dataset version. Cache results keyed by case, prompt hash and model, so unchanged cases aren't re-run. Keep a hard-fail tier for rare, high-stakes behaviors such as deleting data or leaking personal data, where an average diluted by easy cases is the wrong aggregate.

### Failure modes

- **Generic metrics.** Dashboards of "helpfulness: 4.2" that no observed failure motivated. Husain and Shankar say they "create false confidence."
- **Uncalibrated judges.** An LLM judge nobody has checked against human labels, or one judge grading everything at once.
- **Broken or ambiguous tasks** that punish correct behavior. METR found tasks that asked agents to reach a score threshold but graded only scores above it, which penalized models that followed the instructions.
- **Leaky ground truth.** Answers sitting in the sandbox, in the repository history or in the prompt.
- **Reading noise as signal.** No intervals, no paired comparison, a single trial per task.
- **Infrastructure errors scored as model failures,** such as a timeout counted as a wrong answer.
- **Stale datasets.** Products and users change. Husain and Shankar suggest re-running error analysis on 100 or more fresh traces after significant changes, with review cycles of two to four weeks being typical.
- **Goodhart inside the team.** Hill-climbing one dev set until the prompt overfits it.

## Comparison

**Grader types**

| Grader | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Code: match, regex, schema | Normalize, then compare or validate | Fast, free, deterministic | Rejects valid variations; no nuance | Labels, formats, required facts, IDs |
| Code: tests, execution, state checks | Run the output or inspect the environment's end state | Grades what actually happened | You must build and reset an environment | Coding, data and tool-using agents |
| LLM judge: rubric or assertion | A model reads input, output and rubric and returns PASS/FAIL | Handles open-ended output at scale | Sampled, biased, costs a model call | Tone, faithfulness, policy compliance, after calibration |
| LLM judge: pairwise | A model picks the better of two outputs | Easier and more consistent than absolute scores | Position and verbosity bias; only gives relative answers | Comparing two prompts or models |
| Human review | Experts or raters label outputs | The reference standard | Slow, expensive, raters disagree | Calibrating judges, subjective or high-stakes domains |

**Evaluation methods**

| Method | Answers | Strength | Weakness |
|---|---|---|---|
| Offline eval suite | "Did this change break or improve known cases?" | Reproducible, runs on every commit, no user impact | Only covers inputs you collected |
| Online evals on sampled traffic | "How often does this fail in production?" | Real inputs at scale | No reference answers; needs tracing ([§27](27-observability.md)) |
| A/B test | "Do users do better with B?" | Measures real outcomes | Slow; needs traffic; says little about why |
| Transcript review | "What is actually going wrong?" | Finds new failure modes; checks graders | Doesn't scale; reviewers tire |

**Aggregate metrics**

| Metric | Meaning | Use when |
|---|---|---|
| pass@1 (= pass^1) | Average per-trial success rate | The default headline |
| pass@k | At least one of k trials succeeds | You can retry and verify automatically, e.g. patches filtered by tests |
| pass^k | All k trials succeed | Users get one attempt each and expect consistency |
| Cost and latency per task | Tokens, dollars, seconds per completed task | Always, reported next to quality |

## What it didn't solve

Offline evals measure the inputs you thought to collect, graded against the failures you've already found. Production users phrase things differently, combine features nobody tested, and change their behavior over time, and the model behind an alias can change too. Online evals can't run without a record of what happened in each request. To see what really happens, you have to capture every model call, tool call and retrieval in production as it occurs.

→ Next: [§27 Observability and Tracing](27-observability.md)

## Check your understanding

**Q: Why can't you test an LLM feature with ordinary unit tests?**

A unit test assumes a deterministic function, but an LLM samples its output (P4), so one passing run is a sample of size one and the next run may fail. The input space is also open-ended, and "correct" is often a judgment, not an equality. So you measure a rate over a dataset and repeated trials, with graders that can include a model or a human. Ordinary unit tests still belong around the deterministic code: parsers, tool implementations, schema validation.

**Q: Why start with error analysis instead of a standard set of metrics like helpfulness and coherence?**

An LLM app's failures are specific to its prompt, data and users, so generic metrics measure qualities that may not match your failures and give false confidence. Reading traces, open-coding them and grouping the notes into a taxonomy shows which failures actually occur and how often, and criteria drift means you couldn't have written the rubric beforehand anyway. Many findings turn out to be bugs to fix, not evals to maintain. The tradeoff is human time. Generic metrics are still useful for one thing: pointing you at traces worth reading.

**Q: What would happen if you shipped an LLM judge without calibrating it against human labels?**

The judge's output is sampled and biased (position, verbosity, self-preference), so its scores could track its own quirks instead of your quality bar. You might optimize prompts toward what the judge likes, which is Goodhart's law, without noticing. Measuring TPR and TNR on a held-out set of human-labeled passes and fails tells you how far to trust it. For checks code can decide, skip the judge entirely.

**Q: pass@k vs pass^k: which should a customer-support agent report, and why?**

pass^k, because each customer gets one conversation, and the business cares whether the agent handles the same kind of request correctly every time. pass@k counts a task as solved if any of k attempts succeeds, which fits settings where a verifier can pick the winner, such as code patches filtered by tests. The same trials can give pass@8 = 100% and pass^8 = 25%. Report pass@k only when the product actually retries with an automatic checker.

**Q: A prompt change moves your pass rate from 78% to 82% on 60 cases. Should you ship it?**

Not on that evidence alone. At n = 60, a 95% interval on each rate is roughly ±10 points, so a 4-point move is well inside the noise. Run a paired comparison on the same cases with several trials each, check per-slice results for a hidden regression, and look at cost and latency. If the change is cheap and the paired analysis shows no harm, shipping can be fine, but don't call it an improvement.

**Q: Outcome grading vs trajectory grading: when is each one wrong?**

Outcome grading checks the end state, such as tests passing or a reservation existing. It's wrong when the path matters on its own, for example when an agent reached the right state by skipping identity verification or spending 40 tool calls. Trajectory grading is wrong when it demands one particular sequence, because agents find valid routes the designer didn't foresee, and rigid checks punish them. Grade outcomes by default and add targeted trajectory checks for rules and budgets.

**Q: Why might a model that tops a public benchmark do worse than a rival on your own eval?**

Benchmarks may be saturated, contaminated by training data, or gamed through selective reporting, which is Goodhart's law. A score also describes a model in one particular harness, and your harness, prompts, tools and user distribution differ. So the benchmark ranking only loosely predicts your task. Use benchmarks to shortlist candidates and your own eval, with intervals, to choose.

**Q: When is it right to write an eval before building the feature?**

When you can specify success exactly before seeing outputs: hard constraints ("never mention competitors," "never call `refund` without verification"), required formats, or capability bets for the next model generation. Otherwise the LLM's failure surface is too large to anticipate, and criteria drift means early evals target imagined failures. A common middle path is to write the evals you can specify first and grow the rest from error analysis.

## Takeaways

- Correctness is a rate (P4): an eval is a dataset plus graders plus repeated trials, and its result is a statistic with an interval.
- Start with error analysis. Read about 100 traces, open-code them, cluster them into a failure taxonomy, and write evals only for failures that matter.
- Use code graders wherever possible, LLM judges where you must (calibrated against human labels by TPR and TNR), and humans for calibration.
- Keep golden sets small, unambiguous, balanced and sliced, and keep test data out of anything you tune.
- For agents, grade outcomes in reset environments, read transcripts, and say whether you report pass@k or pass^k.
- Public benchmarks shortlist models. Saturation, contamination and Goodhart's law make your own evals the deciding test.
- Run regression evals in CI like dbt tests, but with tolerance bands set from the noise floor, pinned versions, and cost and latency reported next to quality.

## Sources

- Anthropic Engineering, Mikaela Grace, Jeremy Hadfield, Rodrigo Olivares and Jiri De Jonghe, "Demystifying evals for AI agents" (Jan 9, 2026): https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Hamel Husain and Shreya Shankar, "AI Evals: Everything You Need to Know" (evals FAQ): https://hamel.dev/blog/posts/evals-faq/
- Shankar, Zamfirescu-Pereira, Hartmann, Parameswaran and Arawjo, "Who Validates the Validators? Aligning LLM-Assisted Evaluation of LLM Outputs with Human Preferences" (Apr 2024): https://arxiv.org/abs/2404.12272
- Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (Jun 2023): https://arxiv.org/abs/2306.05685
- Evan Miller, "Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations" (Nov 2024): https://arxiv.org/abs/2411.00640 ; Anthropic summary, "A statistical approach to model evaluations" (Nov 19, 2024): https://www.anthropic.com/research/statistical-approach-to-model-evals
- Yao, Shinn, Razavi and Narasimhan, "τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains" (Jun 2024): https://arxiv.org/abs/2406.12045
- Chen et al., "Evaluating Large Language Models Trained on Code" (Jul 2021), the pass@k estimator: https://arxiv.org/abs/2107.03374
- Xia, Lu, Zhu, Xing, Zhao and Zhang, "Evaluation-Driven Development and Operations of LLM Agents: A Process Model and Reference Architecture" (arXiv 2411.13768, Nov 2024, rev. Nov 2025): https://arxiv.org/abs/2411.13768
- Zhang et al., "A Careful Examination of Large Language Model Performance on Grade School Arithmetic" (GSM1k, May 2024): https://arxiv.org/abs/2405.00332
- Singh et al., "The Leaderboard Illusion" (Apr 2025): https://arxiv.org/abs/2504.20879
- Anthropic, Messages API reference: https://docs.claude.com/en/api/messages
