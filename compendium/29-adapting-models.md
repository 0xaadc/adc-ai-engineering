# 29. Adapting Models: Prompt Optimization, Fine-Tuning, Distillation, RL

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

You have prompts ([§05](05-api-and-prompting.md)), structured outputs ([§06](06-structured-outputs.md)), retrieval ([§09](09-rag.md)), tools ([§10](10-tool-use.md)), evals ([§26](26-evals.md)) and a pipeline that turns failures into datasets ([§28](28-data-flywheels.md)), and quality has plateaued. This section is about the next lever: using that data to change the model's behavior, either by searching for a better prompt automatically or by changing the weights. It applies in every era, from single calls to agents. Two principles govern it. P5: fine-tune for behavior, ground for facts. P12: the next model may make your fine-tune obsolete, so every adaptation has a shelf life. The 2026 market makes P12 concrete: OpenAI is winding down self-serve fine-tuning.

## Why this exists

On a rented model the prompt is your main knob, and its limits follow from the principles:

- **Instructions compete for attention (P3).** A prompt with twenty rules still breaks rule 17 a few percent of the time.
- **Context is paid for on every call (P10).** Few-shot examples cost tokens on every request; a weight change is paid for once.
- **Some behavior is easier to show or check than to describe.** You can't write an expert's judgment as rules, but you can show 2,000 examples, rank pairs, or write a program that checks the answer.
- **A frontier model may be overkill** for a narrow, high-volume task, and you pay for its breadth in money and latency.

Adapting the model either finds a better context automatically or moves behavior into the weights. Weights change slowly, can't be read or diffed like a prompt, are tied to a base model that will be retired, and can lose abilities you relied on. So climb a ladder, cheapest rung first, and measure every step.

## How it works (under the hood)

### The ladder, cheapest first

```text
 CHANGES THE CONTEXT: minutes to hours, reversible            CHANGES THE WEIGHTS: days, sticky, tied to a base model
 1 prompt ─► 2 few-shot ─► 3 RAG + tools ─► 4 prompt optimization ─► 5 SFT ─► 6 DPO ─► 7 RFT ─► 8 distillation
 data:  none   3–20 examples  corpus, APIs     dev set + metric        demos    pairs    prompts    teacher outputs
                                                                                         + grader   on real inputs
```

Rungs 1–3 are earlier sections ([§05](05-api-and-prompting.md), [§09](09-rag.md), [§10](10-tool-use.md)). Don't skip them. Most plateaus come from a missing piece of context, a vague instruction or a fact the model never received.

### Rung 4: prompt optimization

*Prompt optimization* treats the prompt as a parameter and the eval metric as the objective, then searches. It is a training loop in which the "weights" are text.

**DSPy** (Khattab et al., Oct 2023; "programming, not prompting") gives the search a structure:

- A **signature** declares a step's inputs and outputs, such as `"question, context -> answer"`, in place of a hand-written prompt.
- A **module** turns a signature into model calls. `dspy.Predict` answers directly, `dspy.ChainOfThought` reasons first, and `dspy.ReAct` runs a tool loop. Modules compose into programs.
- An **optimizer** (formerly "teleprompter") rewrites a program's prompts to maximize a metric on a training set. `BootstrapFewShot` runs the program and keeps traces that pass the metric as few-shot demonstrations. `MIPROv2` proposes instructions grounded in your data and code, then runs a Bayesian search over instruction and demonstration combinations. `BootstrapFinetune` distills the program into weights; combining prompt and weight optimization beat either alone in the authors' "BetterTogether" experiments (Jul 2024).

**GEPA** (Agrawal et al., "Reflective Prompt Evolution Can Outperform Reinforcement Learning", Jul 25, 2025, revised Feb 2026; shipped as `dspy.GEPA`) replaces blind search with reflection. It collects whole trajectories (reasoning, tool calls, tool outputs) and has a model read them to diagnose failures and propose prompt edits. It keeps a **Pareto frontier**, meaning every candidate that is best on at least one example survives, so complementary strategies can be merged later instead of lost to a greedy pick. The argument is about information: a written diagnosis carries far more signal than the single scalar reward an RL update sees. The current revision reports beating GRPO (the RL algorithm in [§04](04-reasoning-models.md)) by 6% on average and up to 20% with up to 35× fewer rollouts, and beating MIPROv2 by over 10%. Those are the authors' benchmarks; check on yours.

The stub below is the core loop: score the prompt on a dev set, show a model the failures, keep any variant that beats the best so far, and report a held-out test score. It is greedy where GEPA keeps a frontier.

```python
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def call(system, user):  # one Messages API call; low effort keeps the eval loop cheap
    r = client.messages.create(model="claude-sonnet-5-5", max_tokens=2048, system=system,
                               output_config={"effort": "low"},
                               messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in r.content if b.type == "text").strip()

def evaluate(prompt, data):  # the metric: exact-match accuracy, plus the failures
    runs = [(x, y, call(prompt, x)) for x, y in data]
    return sum(out == y for _, y, out in runs) / len(runs), [r for r in runs if r[2] != r[1]]

def propose(prompt, failures, n=3):  # reflective mutation: show failures, ask for a rewrite
    shown = "\n".join(f"INPUT: {x}\nEXPECTED: {y}\nGOT: {o}" for x, y, o in failures[:5])
    return [call("You improve system prompts. Reply with the new prompt only.",
                 f"Prompt:\n{prompt}\n\nFailures:\n{shown}\n\nDiagnose why it failed and "
                 f"write improved variant #{i + 1}.") for i in range(n)]

def optimize(prompt, dev, test, rounds=3):
    best_score, failures = evaluate(prompt, dev)
    for rnd in range(rounds):
        for cand in propose(prompt, failures) if failures else []:
            score, fails = evaluate(cand, dev)
            if score > best_score:  # greedy: keep a variant only if it beats the best on dev
                prompt, best_score, failures = cand, score, fails
        print(f"round {rnd}: dev accuracy {best_score:.2f}")
    print(f"test accuracy {evaluate(prompt, test)[0]:.2f}  <- never optimized on: report this")
    return prompt

tickets = [("I was charged twice this month", "billing"), ("API returns 500 since 9am", "outage"),
           ("Add a teammate to our workspace", "account"), ("Refund my last invoice", "billing"),
           ("Dashboard is down for everyone", "outage"), ("Reset my password", "account")]
best = optimize("Label this support ticket as billing, outage or account.",
                dev=tickets[:4], test=tickets[4:])
```

The output is still a prompt: readable, diffable, reversible and portable (re-optimize after switching models). Each round costs about variants × dev-set size calls, and a small dev set overfits, which is why the optimizer never sees the test split. Without a metric you trust, don't bother: an optimizer exploits a weak judge just as RL does.

### Rung 5: supervised fine-tuning, full and low-rank

**SFT** continues training on (prompt, ideal response) pairs with the pretraining next-token loss ([§02](02-how-llms-work.md)). *Full fine-tuning* updates every weight. With the Adam optimizer in mixed precision, each trainable parameter needs about 16 bytes (16-bit weight and gradient, a 32-bit master copy, two optimizer statistics; the ZeRO paper's accounting), so an 8B model needs about 128 GB before activations, and every fine-tune is a full model copy.

**LoRA** (low-rank adaptation; Hu et al., Jun 2021) starts from one observation. Fine-tuning changes a weight matrix W by some ΔW of the same shape, and for a narrow task that change seems to need only a few independent directions: ΔW is close to *low rank*. A low-rank matrix factors into a thin matrix times a wide one:

```text
  W'x = Wx + (α/r) · B(Ax)        W: d_out × d_in   frozen
                                  A: r × d_in       trainable: projects the input onto r directions
                                  B: d_out × r      trainable: writes those r numbers back out
                                  r ≪ d (typically 8–64); B starts at zero, so training starts at the base model
```

Per matrix, trainable parameters fall from d_in × d_out to r × (d_in + d_out). After training you can merge BA into W, so inference has no extra latency, or keep adapters separate and swap them per request. The paper reported 10,000× fewer trainable parameters and 3× less GPU memory than full Adam fine-tuning of GPT-3 175B, with comparable quality. In data-engineering terms, it is a small delta stored against a large frozen base table instead of a full copy per variant.

**QLoRA** (Dettmers et al., May 2023) stores the frozen base in 4 bits, using a NormalFloat type (NF4) designed for normally distributed weights, and backpropagates through it into 16-bit adapters. That fit a 65B model on a single 48 GB GPU while matching 16-bit fine-tuning on the authors' tasks. The calculator below makes the arithmetic concrete for an 8B model:

```python
# Llama-3-8B-shaped layer (public config): hidden size 4096, MLP width 14336, 32 layers,
# grouped-query attention with 8 KV heads, so the K and V projections output 1024 dims.
D, FF, KV, LAYERS, TOTAL_PARAMS = 4096, 14336, 1024, 32, 8.0e9
SHAPES = {"q": (D, D), "k": (D, KV), "v": (D, KV), "o": (D, D),       # attention
          "gate": (D, FF), "up": (D, FF), "down": (FF, D)}            # MLP

def full(d_in, d_out):
    return d_in * d_out          # full fine-tuning: every entry of W is trainable

def lora(d_in, d_out, r):
    return r * (d_in + d_out)    # A is (r x d_in), B is (d_out x r); W itself stays frozen

def trainable(r=None, targets=tuple(SHAPES)):
    per_layer = sum(full(*SHAPES[m]) if r is None else lora(*SHAPES[m], r) for m in targets)
    return LAYERS * per_layer

base = trainable()
print(f"full fine-tune of these matrices: {base / 1e9:.2f}B trainable parameters")
for r in (1, 8, 16, 64):
    n = trainable(r)
    print(f"LoRA r={r:<3} all matrices: {n / 1e6:6.1f}M  ({100 * n / base:.2f}% of full)")
n = trainable(16, targets=("q", "v"))   # the original paper's attention-only choice
print(f"LoRA r=16  q,v only:     {n / 1e6:6.1f}M  ({100 * n / base:.2f}% of full)")

# Training memory, rule of thumb for Adam in mixed precision: ~16 bytes per TRAINABLE
# parameter (bf16 weight + grad, fp32 master copy + two optimizer moments), plus the
# FROZEN weights: 2 bytes each in bf16, ~0.5 bytes in 4-bit (QLoRA). Activations excluded.
adapters = trainable(16)
def gb(n_bytes): return f"{n_bytes / 1e9:.0f} GB"
print("full FT ~", gb(16 * TOTAL_PARAMS))
print("LoRA    ~", gb(2 * TOTAL_PARAMS + 16 * adapters))
print("QLoRA   ~", gb(0.5 * TOTAL_PARAMS + 16 * adapters))
print(f"r=16 adapter file in bf16: ~{2 * adapters / 1e6:.0f} MB, vs {gb(2 * TOTAL_PARAMS)} of weights")
```

```text
full fine-tune of these matrices: 6.98B trainable parameters
LoRA r=1   all matrices:    2.6M  (0.04% of full)
LoRA r=16  all matrices:   41.9M  (0.60% of full)
LoRA r=16  q,v only:        6.8M  (0.10% of full)
full FT ~ 128 GB    LoRA ~ 17 GB    QLoRA ~ 5 GB    (r=16 adapter file: ~84 MB)
```

Does LoRA match full fine-tuning? For the dataset sizes most product teams have, mostly yes:

- **Large datasets.** Biderman et al. (May 2024) found LoRA "substantially underperforms" full fine-tuning on code and math with large datasets but "better maintains the base model's performance on tasks outside the target domain." In their title's words, LoRA learns less and forgets less.
- **Typical post-training sizes.** Thinking Machines' "LoRA Without Regret" (Sep 29, 2025) found LoRA equal to full fine-tuning on small-to-medium instruction and reasoning datasets, and for RL "even with small ranks." The condition was applying it to all layers, especially the MLP layers.
  - Attention-only LoRA, the original paper's choice, underperformed even at matched parameter counts.
  - LoRA falls behind once the dataset exceeds its capacity.

### Rung 6: preference tuning (DPO)

Use preference pairs ([§28](28-data-flywheels.md)) when annotators can say which of two answers is better but can't write the ideal one. DPO ([§02](02-how-llms-work.md)) raises the likelihood of the chosen response relative to a frozen reference model and lowers the rejected one. Its β parameter sets how far the model may drift; OpenAI's docs describe a high β as "more conservative (favoring previous behavior)." It suits tone, emphasis in summaries, and "slightly off" outputs that SFT can't target because no single right answer exists. Its limits: it learns only from the pairs you collected, without exploring, and it learns any confound in them, such as length.

### Rung 7: reinforcement fine-tuning with graders

*Reinforcement fine-tuning (RFT)* applies the reasoning-model recipe of RL with verifiable rewards ([§04](04-reasoning-models.md)) to your task. You supply prompts and a *grader*, a function that scores any response: a string check, a text-similarity score, Python code, a model-scored rubric, or a combination. OpenAI's docs describe the loop: the platform "samples several responses per prompt, scores them with the grader, and applies policy-gradient updates based on those rewards."

Because RL can only reinforce what the model already does sometimes, the preconditions follow from the mechanism. OpenAI's RFT guide lists them:

- **Experts must agree on the answer.** Otherwise the reward is noise.
- **The model must already succeed sometimes.** "If a model has a 0% success rate at a given task, you cannot bootstrap to higher performance levels through RFT."
- **Scores must vary across samples.** If every sample scores the same, there is nothing to compare.
- **The task must be guess-proof.** Otherwise lucky guesses get reinforced along with bad reasoning.

Availability as of Oct 2026:

- **OpenAI.** RFT supported only `o4-mini`, and OpenAI's deprecation schedule removes `o4-mini` and its fine-tunes on Oct 23, 2026. Its self-serve fine-tuning platform stopped accepting new organizations on May 7, 2026, and closes to new jobs for existing customers on Jan 6, 2027.
- **Amazon Bedrock** offers RFT for Nova 2 Lite and some open-weight models (gpt-oss-20B, Qwen3 32B).
- **Open-weight models.** Open-source stacks such as Prime Intellect's `verifiers` and `prime-rl`, and Thinking Machines' LoRA-based Tinker API (launched Oct 1, 2025), run RFT on open-weight models.

### Rung 8: distillation

**Distillation** trains a small *student* model to imitate a large *teacher*. Hinton et al. (2015) introduced it as matching the teacher's full output probabilities. With API models you usually see only text, so in practice you run the teacher on your real inputs, filter its outputs with your evals or graders, and fine-tune the student on what survives with SFT. It works because a narrow task needs only a small slice of the teacher's ability, and it pays off in cost and latency (P10). The student is at most as good as the teacher on the inputs you covered and degrades quickly outside them, so pair it with routing that sends unusual inputs to the big model ([§30](30-cost-latency-reliability.md)). Terms of use apply ([§28](28-data-flywheels.md)). Anthropic notes that frontier labs "routinely distill their own models to create smaller, cheaper versions for their customers," so the small model you can already call may be the distillation you were about to build.

### RL environments: where evals and training converge

An **RL environment** packages a task, the tools and sandbox to attempt it, and a *verifier* that decides whether the attempt succeeded, usually behind an interface like `reset()` and `step(action)`. That is the anatomy of an agent eval ([§26](26-evals.md)). The difference is where the score goes:

```text
           ┌───────────── task + sandbox + tools ─────────────┐
 model ───►│ think → tool call → observation → … → final state │──► verifier ──► score ─┬─► as a metric: eval report
   ▲       └──────────────────────────────────────────────────┘                        │
   └──────────── as a reward: raise the probability of high-scoring trajectories ◄──────┘
```

The industry built these out in 2025:

- **SWE-Gym** (Dec 30, 2024) packaged 2,438 real Python tasks, each with a codebase, an executable runtime, unit tests and a task description. Training on it gave up to 19% absolute gains on SWE-Bench Verified and Lite.
- **OpenAI** said it trained o3 and o4-mini "to use tools through reinforcement learning" (Apr 2025, [§04](04-reasoning-models.md)).
- **Prime Intellect** launched an open Environments Hub on Aug 27, 2025.
- **TechCrunch** (Sep 16, 2025) described labs demanding more environments, startups such as Mechanize and Prime Intellect, and labeling firms (Surge, Mercor, Scale AI) moving in. Citing The Information, it reported that Anthropic leaders had discussed spending over $1 billion on RL environments over the following year (secondary, **⚠ verify**).
- **Meta and Hugging Face** launched OpenEnv, a shared environment spec and hub, on Oct 23, 2025.

Why it made agents better comes down to compounding error (P8). Training on whole multi-step tasks, scored on the outcome, rewards whatever raises per-step reliability, including checking tool results and recovering from mistakes. That raises *p* in *pⁿ*. Training inside realistic harnesses also couples models to the harnesses they run in ([§19](19-harness-engineering.md)).

The weak point is the verifier. If it can be fooled, RL will find the way. Anthropic's Nov 2025 study gives the example of calling `sys.exit(0)` so a test harness reports success, and found that models which learned such hacks generalized to worse behavior, including sabotage. Skeptics in the TechCrunch piece called environments "prone to reward hacking." Karpathy said he was "bullish on environments and agentic interactions but … bearish on reinforcement learning specifically." For an app team the practical point is that you rarely train a frontier model, but your agent eval harness is most of an environment already, so building it well pays twice. The label "environment engineering" is niche; the industry is real.

### What fine-tuning can't do

- **Reliably add facts.**
  - Gekhman et al. (May 2024) found that fine-tuning examples containing new facts are "learned significantly slower" than examples consistent with what the model already knows. Once learned, they "linearly increase the model's tendency to hallucinate."
  - Ovadia et al. (Dec 2023) found that retrieval "consistently outperforms" unsupervised fine-tuning for adding knowledge.
  - Ground for facts (P5, [§09](09-rag.md)).
- **Fix a bad task definition.** If your experts disagree, the model learns their disagreement. Fix the rubric first.
- **Supply runtime context.** No weight knows today's order status. That takes a tool call.
- **Leave everything else intact.** Qi et al. (Oct 2023) removed GPT-3.5 Turbo's safety guardrails with 10 adversarial fine-tuning examples costing under $0.20. They also found that even benign fine-tuning degraded safety, "to a lesser extent." Re-run safety evals on every fine-tune ([§32](32-security-guardrails.md)).

### Catastrophic forgetting

*Catastrophic forgetting* is the loss of earlier abilities when a network trains on something new. The mechanism: all skills share the same weights, and the loss you minimize mentions only the new task, so nothing protects the weights that old skills depend on. Kirkpatrick et al. (Dec 2016) countered it by "selectively slowing down learning on the weights important for those tasks." In LLM fine-tunes it shows up as weaker instruction following outside the trained format, lost safety behavior, and narrower reasoning. Mitigations:

- LoRA, which forgets less.
- Mixing general-purpose data into the training set.
- Low learning rates and few epochs.
- A KL penalty that keeps the model close to the reference model. DPO's β plays this role.
- Above all, regression evals on general capabilities, not only on the target task.

### Hosting fine-tunes

**Provider-hosted.** You upload data, and the vendor trains and serves the model. You run no GPUs, but the tuned model lives and dies with the vendor's base model. OpenAI's deprecation page states that "fine-tuned versions of these models follow the same shutdown schedule as their underlying base models," and it shuts down GPT-4.1 and GPT-4o fine-tunes on Jan 14, 2027. Other options as of Oct 2026:

- **Google Vertex AI** supports supervised tuning on Gemini 3.5 Flash, 3.1 Flash-Lite and the 2.5 family, with a configurable "adapter size."
- **Amazon Bedrock** lists fine-tuning for its Nova models, some Llama models and, among Claude models, only Claude 3 Haiku.
- **Anthropic's own API** offers no self-serve fine-tuning (**⚠ verify**).

**Self-hosted.** You own the weights, usually an open-weight base plus a LoRA adapter, and you serve them ([§31](31-open-weights-self-hosting.md)). Adapters are small, so one server can hold one base model plus many adapters and pick one per request. vLLM does this with `--enable-lora --lora-modules name=path` and a `max_loras` limit. You take on GPU capacity, upgrades and on-call.

### Cost math: when it pays off

Take a ticket classifier at 2,000,000 requests a month. Each request has a 4,000-token prompt (3,500 fixed tokens of instructions and examples, 500 tokens of ticket) and 300 output tokens. Anthropic list prices as of Oct 2026 per million tokens: Sonnet 5.5 costs $2 input, $10 output and $0.10 for cache hits; Haiku 5.5 costs $0.10 input and $0.50 output.

| Option | Per request | Per month |
|---|---|---|
| A. Sonnet 5.5, no caching | 4,000 × $2/M + 300 × $10/M = $0.0110 | $22,000 |
| B. Sonnet 5.5, fixed prefix cached ([§30](30-cost-latency-reliability.md)) | 3,500 × $0.10/M + 500 × $2/M + 300 × $10/M = $0.00435 | $8,700 |
| C. Haiku 5.5, same prompt, no caching | 4,000 × $0.10/M + 300 × $0.50/M = $0.00055 | $1,100 |
| D. Distilled open-weight model, self-hosted | *Assumed:* $3,000/month for GPUs and ops, plus a $30,000 one-off for labeling, training and evals | $3,000 + one-off |

```text
payback (months) = one-off cost / (monthly cost of the best alternative − monthly cost of the tuned model)
  vs A: 30,000 / (22,000 − 3,000) ≈ 1.6 months    ← the number in most pitches
  vs B: 30,000 / ( 8,700 − 3,000) ≈ 5.3 months
  vs C: never, if Haiku 5.5 passes your evals
worth it only if payback ≪ remaining life of the base model, and the task stays stable that long
```

There are three lessons:

- **Compare against the best cheap alternative,** not the naive baseline.
- **Count the hidden one-offs:** labeling, building evals, and retraining for every new base model.
- **Cap the horizon.** The tuned model's value ends when its base model is retired, or when a newer stock model beats it at the same price (P12). On 2025–2026 evidence, that is months, not years.

Fine-tuning tends to pay when volume is very large, the task is narrow and stable, latency is critical, or data can't leave your infrastructure.

### Evals before and after

Every rung is a hypothesis, and the eval decides ([§26](26-evals.md)).

- **Before:** freeze an eval version, record the baseline of the best prompt-only system and of a smaller stock model, and write down the target.
- **After:** run the same eval version on the target task, regression suites (general instruction following, formats, safety), and cost and latency. For agents, use repeated trials (pass^k).
- **Ship carefully:** use a shadow deployment or an A/B test.
- **Keep your data and evals in your own storage,** not only in a vendor console. OpenAI's hosted Evals platform is also being retired: read-only from Oct 31, shut down Nov 30, 2026.

When the next base model ships, the same eval decides whether to retrain the fine-tune or delete it.

## Comparison

**The ladder**

| Rung | Changes | Data needed | Cost and iteration time | Reversible? | Choose when |
|---|---|---|---|---|---|
| Prompt, few-shot | Context | 0–20 examples | Minutes; tokens on every call | Yes | Always first |
| RAG, tools | Context | Corpus, APIs | Days | Yes | Facts are missing or changing (P5) |
| Prompt optimization | Context, found by search | Dev set + metric | Hours; many eval calls | Yes | Multi-step pipelines; prompt plateaus |
| SFT (LoRA or full) | Weights | Hundreds to thousands of demos | Days; training + hosting | Keep the base to roll back | Consistent format or style; narrow task at scale |
| DPO | Weights | Thousands of pairs | Days | Same | Raters can rank but can't write the ideal |
| RFT | Weights | Prompts + a reliable grader | Days to weeks | Same | Checkable task the model sometimes solves |
| Distillation | A smaller model's weights | Teacher outputs on real inputs | Days + hosting | Fall back to the teacher | Cost or latency at high volume |

**Full fine-tuning vs LoRA vs QLoRA**

| | Full | LoRA | QLoRA |
|---|---|---|---|
| Trains | All weights | Small adapters, r × (d_in + d_out) per matrix | Same adapters over a 4-bit base |
| Training memory, 8B model (rough) | ~128 GB | ~17 GB | ~5 GB |
| Artifact | Full model copy | Megabyte-scale adapter | Megabyte-scale adapter |
| Quality | Highest ceiling on large datasets | Matches full at typical post-training sizes, if all layers are adapted | Close to LoRA |
| Forgetting | Most | Less | Less |
| Serving | One deployment per fine-tune | Many adapters on one base | Same as LoRA |

**Decision table: symptom → technique**

| Symptom | Try first | Then | Not this |
|---|---|---|---|
| Wrong, stale or missing facts | RAG or a lookup tool | Better retrieval | Fine-tuning (P5) |
| Output doesn't parse | Structured outputs ([§06](06-structured-outputs.md)) | — | Fine-tuning for format |
| Ignores some instructions some of the time | Clearer prompt, examples, context hygiene ([§16](16-context-engineering.md)) | Prompt optimization, then SFT | A longer prompt |
| Inconsistent style or tone at scale | Few-shot | SFT, then DPO | — |
| "Slightly off"; raters can rank but not write | Rubric in the prompt | DPO | SFT on one "right" answer |
| Checkable task, model succeeds sometimes | Prompt optimization, more thinking ([§04](04-reasoning-models.md)) | RFT or an RL environment | RFT at a 0% success rate |
| Multi-step pipeline, no labels for middle steps | DSPy or GEPA on the end-to-end metric | `BootstrapFinetune` | Hand-tuning each prompt |
| Too slow or costly for a narrow task | Caching, a smaller stock model, lower effort ([§30](30-cost-latency-reliability.md)) | Distillation | Fine-tuning the big model |
| Experts disagree on the right answer | Fix the task definition and rubric | — | Any training |
| A new base model shipped | Re-run evals on the stock new model | Retrain only if it still loses | Assuming the fine-tune still wins (P12) |

## What it didn't solve

A better model, whether prompted, tuned or distilled, still has to run in production. It must stay within a cost budget and a latency budget, and it must stay up when providers rate-limit, time out or fail. The cost math above is one slice of that problem. Caching, batching, routing between models, gateways and fallbacks are the rest. → Next: [§30 Cost, Latency, and Reliability](30-cost-latency-reliability.md)

## Check your understanding

**Q: Why try prompt optimization before fine-tuning?**

It changes the context, not the weights. The result is a readable, versioned prompt that you can roll back and run on any model, and it needs only a dev set and a metric. Reflective methods such as GEPA report large gains from relatively few rollouts. The costs are many eval calls per round and a risk of overfitting a small dev set. It won't fix the per-call cost or latency of a big model; that's distillation's job.

**Q: What does "low rank" mean in LoRA, and why does it cut training memory so much?**

LoRA writes each weight update as a product B·A through r dimensions, so a 4096 × 4096 matrix trains 16 × 8,192 ≈ 131K parameters at r = 16 instead of 16.8M. Optimizer state costs about 16 bytes per *trainable* parameter, while frozen weights cost only 2 bytes each in 16-bit, or about 0.5 in 4-bit with QLoRA. That takes an 8B model from about 128 GB to 17 GB, or about 5 GB. The tradeoff is capacity: if the task needs more change than the rank allows, as with large datasets, LoRA falls behind full fine-tuning.

**Q: Why not fine-tune your product documentation into the model instead of using RAG?**

Fine-tuning absorbs new facts slowly, and once it does, it increases hallucination (Gekhman et al.). Retrieval outperformed fine-tuning for adding knowledge (Ovadia et al.). A fine-tuned model also can't cite its source and goes stale with the next doc edit, while RAG stays fresh and checkable (P5). Fine-tune only for how to use the retrieved documents, such as format, tone or citation style.

**Q: What would happen if you ran RFT on a task where the model currently scores 0%?**

Nothing useful. RL raises the probability of samples that score above the group average. If every sample scores zero, every sample sits exactly at the average, so there's no gradient signal to follow. Make the task reachable first: add context or tools, decompose it, or run SFT on demonstrations. Partial-credit graders can help, but each new way to score is a new way to hack the score.

**Q: SFT vs DPO: when is a preference pair better than a demonstration?**

SFT imitates one target per prompt, so it needs someone who can write the ideal response. DPO needs only a judgment that A beats B, which is cheaper and more reliable when quality is a matter of degree, as with tone, emphasis or concision. DPO also shifts the model relative to a reference model, with β limiting drift. But it learns any confound in the pairs, such as length, and it can't explore beyond them. Use SFT for formats and skills with a right answer, and DPO for "better vs worse."

**Q: How is an RL environment different from an agent eval?**

Structurally it isn't: both are a task, tools, a sandbox and a verifier. The difference is where the score goes, into a report or back into the weights as a reward. That raises the stakes on the verifier, because an optimizer actively searches for ways to fool it, as with `sys.exit(0)` faking passing tests. It also means you can't use the same environment as a held-out eval after training on it.

**Q: Why might a fine-tune that beats your prompt today be worthless in a year?**

It is tied to its base model, and provider fine-tunes shut down with that model. OpenAI's GPT-4.1 fine-tunes end on Jan 14, 2027. Meanwhile newer stock models often match the tuned behavior at the same price or lower (P12). So the payback period has to be well inside the base model's remaining life. Keep the training data and evals, so that retraining or deleting is a measured decision rather than a guess.

**Q: Your fine-tune gained 8 points on the target metric, but users say it got worse at everything else. What happened?**

Catastrophic forgetting. Gradient updates for the new task overwrote shared weights that other skills relied on, and your eval measured only the target task. Retrain with LoRA, mix in general-purpose data, use lower learning rates or fewer epochs, and keep the model close to the reference. Then add regression suites for instruction following, formats and safety, so the next run can't ship with the same blind spot.

## Takeaways

- Climb the ladder cheapest first: prompt, few-shot, RAG and tools, prompt optimization, and only then the weights.
- Prompt optimization (DSPy, GEPA) is training with text as the parameter. It needs a trusted metric and a held-out test.
- LoRA trains a low-rank update of r × (d_in + d_out) per matrix. Applied to all layers, it matches full fine-tuning at typical sizes and forgets less.
- Use DPO for "better vs worse," RFT for checkable tasks the model sometimes solves, and distillation for cost and latency.
- RL environments are evals wired into the weights, and the verifier is what gets attacked.
- Fine-tuning won't reliably add facts or fix a bad task definition, and it can erode safety and general skills.
- A fine-tune's value ends when its base model is retired or beaten (P12). Compare against the best cheap alternative, and keep your data and evals in your own hands.

## Sources

- Khattab et al., "DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines," Oct 2023: https://arxiv.org/abs/2310.03714
- DSPy docs, Optimizers: https://dspy.ai/learn/optimization/optimizers/
- Opsahl-Ong et al., "Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs" (MIPRO), Jun 2024: https://arxiv.org/abs/2406.11695
- Soylu et al., "Fine-Tuning and Prompt Optimization: Two Great Steps that Work Better Together," Jul 2024: https://arxiv.org/abs/2407.10930
- Agrawal et al., "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning," Jul 25, 2025 (rev. Feb 14, 2026): https://arxiv.org/abs/2507.19457
- Hu et al., "LoRA: Low-Rank Adaptation of Large Language Models," Jun 2021: https://arxiv.org/abs/2106.09685
- Dettmers et al., "QLoRA: Efficient Finetuning of Quantized LLMs," May 2023: https://arxiv.org/abs/2305.14314
- Rajbhandari et al., "ZeRO: Memory Optimizations Toward Training Trillion Parameter Models" (16 bytes per parameter for mixed-precision Adam), Oct 2019: https://arxiv.org/abs/1910.02054
- Biderman et al., "LoRA Learns Less and Forgets Less," May 2024: https://arxiv.org/abs/2405.09673
- John Schulman and Thinking Machines, "LoRA Without Regret," Sep 29, 2025: https://thinkingmachines.ai/blog/lora/
- Thinking Machines, "Announcing Tinker," Oct 1, 2025: https://thinkingmachines.ai/blog/announcing-tinker/
- Rafailov et al., "Direct Preference Optimization," May 2023: https://arxiv.org/abs/2305.18290
- OpenAI, Model optimization: https://developers.openai.com/api/docs/guides/model-optimization
- OpenAI, Reinforcement fine-tuning: https://developers.openai.com/api/docs/guides/reinforcement-fine-tuning
- OpenAI, Direct preference optimization: https://developers.openai.com/api/docs/guides/direct-preference-optimization
- OpenAI, Deprecations (self-serve fine-tuning, Evals platform, model shutdowns): https://developers.openai.com/api/docs/deprecations
- Amazon Bedrock, Reinforcement fine-tuning: https://docs.aws.amazon.com/bedrock/latest/userguide/reinforcement-fine-tuning.html
- Amazon Bedrock, Fine-tuning supported models: https://docs.aws.amazon.com/bedrock/latest/userguide/custom-model-fine-tuning.html
- Google Cloud, About supervised fine-tuning for Gemini models: https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-supervised-tuning
- vLLM docs, LoRA Adapters: https://github.com/vllm-project/vllm/blob/main/docs/features/lora.md
- Anthropic, Pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Hinton, Vinyals and Dean, "Distilling the Knowledge in a Neural Network," Mar 2015: https://arxiv.org/abs/1503.02531
- Anthropic, "Detecting and preventing distillation attacks," Feb 23, 2026: https://www.anthropic.com/news/detecting-and-preventing-distillation-attacks
- Pan et al., "Training Software Engineering Agents and Verifiers with SWE-Gym," Dec 2024: https://arxiv.org/abs/2412.21139
- Prime Intellect, "Environments Hub," Aug 27, 2025: https://www.primeintellect.ai/blog/environments
- Meta and Hugging Face, "Introducing OpenEnv," Oct 23, 2025: https://huggingface.co/blog/openenv
- TechCrunch, "Silicon Valley bets big on 'environments' to train AI agents," Sep 16, 2025 (secondary): https://techcrunch.com/2025/09/16/silicon-valley-bets-big-on-environments-to-train-ai-agents/
- Anthropic, "From shortcuts to sabotage: natural emergent misalignment from reward hacking," Nov 21, 2025: https://www.anthropic.com/research/emergent-misalignment-reward-hacking
- Gekhman et al., "Does Fine-Tuning LLMs on New Knowledge Encourage Hallucinations?," May 2024: https://arxiv.org/abs/2405.05904
- Ovadia et al., "Fine-Tuning or Retrieval? Comparing Knowledge Injection in LLMs," Dec 2023: https://arxiv.org/abs/2312.05934
- Qi et al., "Fine-tuning Aligned Language Models Compromises Safety, Even When Users Do Not Intend To!," Oct 2023: https://arxiv.org/abs/2310.03693
- Kirkpatrick et al., "Overcoming catastrophic forgetting in neural networks," Dec 2016: https://arxiv.org/abs/1612.00796
