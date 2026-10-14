# 28. Data Flywheels and Synthetic Data

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

Part 7 covers disciplines that apply in every era. This one applies to all of them: a single prompt, a RAG system and a multi-step agent all get better the same way. [§26](26-evals.md) gave you evals, which are the tests for a probabilistic system (P4). [§27](27-observability.md) gave you traces, the record of what actually happened in production. A trace shows you a failure, but it doesn't fix it. Something has to turn the trace into a labeled example, the example into a dataset, and the dataset into a change you can measure. That conversion is a data pipeline, and it is the part of AI engineering closest to what you already do. Three principles drive it. P4: correctness is a rate measured on data. P5: some fixes belong in the context and some in the weights. P12: models get replaced, but datasets carry over.

## Why this exists

Watch what most teams do with traces. They open a dashboard, read a few bad conversations, tweak the prompt, and move on. Nothing accumulates. After the next model upgrade the same failure comes back, and nobody can say whether the new prompt is better, because there is no fixed set of cases to compare on.

A **data flywheel** is a loop in which usage produces data, the data improves the product, and the better product attracts more usage. For an LLM product it runs:

**usage → traces → labeled failures → datasets → better prompts, retrieval, evals or fine-tunes → better product → more usage**

Each turn should leave something durable behind: an eval case that keeps a fixed bug fixed, a few-shot example, a retrieval fix, or a training pair. OpenAI's optimization guide describes the same loop as "a flywheel of feedback that leads to better prompts and better training data for fine-tuning."

**Why data and not the model is the defensible asset.** The model is rented. Your competitors call the same API with the same weights, and within months both of you will switch to a better model (P12). Prompts are partly model-specific, and fine-tunes are retired along with their base model ([§29](29-adapting-models.md)). The data is different. The real distribution of your users' tasks, the failures you found and your judgments of good and bad can't be copied by a competitor, and they still work after you switch models. Your eval set is how you migrate to the next model safely. Your labeled failures are what you will use to prompt or train it.

That claim needs a caveat. "Data moat" is an old pitch, and Martin Casado and Peter Lauten of a16z argued in 2019 ("The Empty Promise of Data Moats") that for most enterprise companies, data network effects are hard to find and the value of more data flattens out. Raw logs are not an asset: an unlabeled trace is worth about as much as an unread log file. The defensible part is narrow and expensive to copy. It is labeled examples of your domain's hard cases, rubrics written by your experts, and an eval set that mirrors your real traffic. The flywheel only turns if someone closes the loop.

## How it works (under the hood)

### The loop as a pipeline

```text
production ─► traces (§27) ─► triage ─────► candidates ─► labels ───────► datasets ──► change ONE lever ─► eval (§26) ─► ship
 traffic      raw events      failure       redacted,     experts,        versioned    prompt, retrieval,   same frozen     │
    ▲                         signals and   deduped,      vendor, or      eval and     tools, few-shot,     dataset         │
    │                         sampling      with lineage  LLM + audit     train splits fine-tune (§29)      version         │
    └──────────────────────────────────────── more, better usage ◄──────────────────────────────────────────────────────────┘
```

If you know the medallion architecture, this is it. Traces are bronze (raw and append-only), candidate examples are silver (cleaned, deduplicated, scrubbed of personal data), and labeled datasets are gold (curated and versioned, with contracts).

Two rules keep the loop honest. First, **fix with the cheapest lever**: most failures yield to a prompt, retrieval or tool change, not to training. Second, **every fixed failure becomes an eval case**, so it works as a regression test and stays fixed.

### Data engineering for AI datasets

**The unit is an example, and it needs a schema.** An *example* is one input plus what you know about the right output. A practical record looks like this:

```json
{
  "example_id": "ex_0193",
  "input": {"messages": [{"role": "user", "content": "Refund to <EMAIL> for order 1182..."}]},
  "model_output": "Done! Your refund is on its way.",
  "reference": "I can't issue refunds myself. I've opened a refund request for order 1182...",
  "labels": {"failure_mode": "claimed_unperformed_action", "severity": "high"},
  "provenance": {"origin": "production", "source_trace_id": "t1", "model": "claude-sonnet-5-5",
                 "prompt_version": "support-v14", "pii_scrubbed": true, "labeler": "expert"},
  "split": "test",
  "dataset_version": "support-evals@2026-10-01"
}
```

**Lineage from trace to example.** Every example keeps the ID of the trace it came from, plus the model and prompt version that produced it. You need this for three reasons:

- **Debugging:** you can answer "why is this case in the eval?"
- **Deletion requests:** deleting a user's rows from a table is easy. Once their data has been trained into weights, you can't remove it without retraining ([§17](17-memory.md)). So you need to know which datasets, and which models, contain it.
- **Contamination audits:** you can trace any test item back to its source.

**Versioning.** An eval score means nothing without the dataset version it was computed on, just as a metric means nothing without the table snapshot behind it. Freeze eval sets as named versions. Delta or Iceberg time travel, DVC, lakeFS or dataset revisions on a hub all work. Record the dataset version, prompt version and model ID with every run. If you compare two prompts on two different eval versions, you have run two different tests.

**Deduplication.** Duplicates cause damage everywhere they appear:

- **In training data** they over-weight a few cases and encourage memorization. Lee et al. (2021) found that deduplicating training data made models emit memorized text ten times less often and reach the same or better accuracy in fewer training steps.
- **In eval data** they inflate the score of whatever case is repeated.
- **Across splits** they leak test answers into training.

Catching them takes three layers:

- **Exact duplicates.** Hash a normalized form (lowercase, collapsed whitespace, personal data replaced by placeholders) and drop repeats.
- **Near duplicates.** Break each text into *shingles*, the set of overlapping k-word windows, and compare those sets with *Jaccard similarity*, |A ∩ B| / |A ∪ B|.
  - Comparing every pair is O(n²), so at scale you use *MinHash*. It compresses each shingle set into a short signature, and the rate at which two signatures agree estimates their Jaccard similarity.
  - You add *locality-sensitive hashing (LSH)*, which puts signatures into buckets so that only likely matches get compared.
  - Spark MLlib ships this as `MinHashLSH`. Lee et al. used MinHash over 5-grams.
- **Paraphrases.** "How do I get a refund" and "refund process?" share almost no shingles. Catching them needs embeddings ([§08](08-embeddings-and-search.md)) and a similarity threshold.

The snippet pulls candidate examples out of traces, keeps their lineage, and applies the first two layers:

```python
import hashlib, re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
SIGNALS = ("thumbs_down", "edited", "retried", "error")

def redact(text):  # scrub PII BEFORE the text becomes a dataset row
    return PHONE.sub("<PHONE>", EMAIL.sub("<EMAIL>", text))
def normalize(text):  # canonical form: lowercase, collapsed whitespace
    return " ".join(text.lower().split())
def shingles(text, k=5):  # the set of overlapping k-word windows
    w = normalize(text).split()
    return {" ".join(w[i:i + k]) for i in range(max(1, len(w) - k + 1))}
def jaccard(a, b):  # |A ∩ B| / |A ∪ B|; 1.0 means identical shingle sets
    return len(a & b) / len(a | b) if a | b else 1.0

def extract(traces, near_dup=0.8):
    hashes, kept = set(), []
    for t in traces:
        signals = [s for s in SIGNALS if t.get(s)]
        if not signals:  # only traces with a failure signal become candidates
            continue
        text = redact(t["input"])
        h, sh = hashlib.sha256(normalize(text).encode()).hexdigest(), shingles(text)
        if h in hashes or any(jaccard(sh, k["_sh"]) >= near_dup for k in kept):
            continue  # exact dup (hash) or near dup (shingles); MinHash + LSH at scale
        hashes.add(h)
        kept.append({"input": text, "model_output": redact(t["output"]),
                     "user_fix": redact(t["edit"]) if t.get("edit") else None,
                     "signals": signals, "source_trace_id": t["trace_id"],  # lineage
                     "content_hash": h, "_sh": sh})
    return [{k: v for k, v in ex.items() if k != "_sh"} for ex in kept]

T1 = "Refund to jo@x.com for order 1182, the parcel never arrived at my flat"
traces = [  # rows exported from the observability store (§27)
    {"trace_id": "t1", "input": T1, "output": "Done!", "thumbs_down": True},
    {"trace_id": "t2", "input": "Hi! " + T1, "output": "Done!", "retried": True},  # near dup
    {"trace_id": "t3", "input": "SLA for P1 tickets?", "output": "24h", "edited": True, "edit": "4h"}]
for ex in extract(traces):  # t2 is dropped: Jaccard(t1, t2) is 0.9
    print(ex["source_trace_id"], ex["signals"], ex["input"], "| fix:", ex["user_fix"])
```

**PII.** *Personally identifiable information (PII)* is anything that identifies a person: names, emails, phone numbers, addresses, account numbers. Redact it at ingestion, before a labeler, a vendor or a training job sees the text.

- **Regexes are only a floor.** The ones above miss names and addresses and would redact a long order number as a phone. Real pipelines add a named-entity detector and audit samples.
- **Pseudonymize user IDs,** and keep the mapping in a restricted table so you can still honor deletion requests.
- **Synthetic data isn't automatically private.** A generator prompted with real records can copy them.

**Train, dev and test separation.** Split by group, not by row. Customers file near-identical tickets, so a random row split puts the same customer's problem on both sides, and the test score ends up measuring memory. Split by account, conversation or time, and keep the test set locked. Before every training run, run the near-duplicate check *across* splits.

**Labeling workflows.** There are three, and most teams mix them.

- **In-house experts** know what "correct" means. They are slow and expensive, but you need them for rubrics, gold sets and anything high-stakes.
- **Vendors** give you scale. The price is written guidelines, calibration rounds, hidden gold questions to measure quality, and a PII review before anything leaves your systems.
- **LLM-assisted labeling with human audit.** A model labels everything and humans label a random sample. Before you trust the model's labels, measure how often they match the humans', for example with *Cohen's kappa* (agreement corrected for chance: 1 is perfect, 0 is no better than chance). LLM judges have known biases ([§26](26-evals.md)).

Before any of this, measure agreement among the humans. If two experts working independently disagree on a label, the bug is in the task definition, and no amount of data or training will fix it ([§29](29-adapting-models.md)).

### Feedback signals

*Explicit feedback* is what users tell you on purpose: thumbs up or down, ratings, corrections, edits to a draft. *Implicit feedback* is what their behavior reveals: accepting a suggestion, copying an answer, retrying, rephrasing, abandoning the session, escalating to a human. Both are biased.

- **Selection bias.** Few users click thumbs, and the ones who do are unusually annoyed or unusually delighted.
- **Satisfaction isn't correctness.** Users upvote confident, agreeable answers. This is the same pressure that makes RLHF-trained models sycophantic ([§02](02-how-llms-work.md)). If you train on thumbs-up, you optimize for it.
- **Ambiguous intent.**
  - A retry can mean "wrong" or "show me another."
  - Abandoning a session can mean the user gave up or got the answer.
  - An accepted suggestion can be silently reverted later.
- **You only see reactions to what you showed.** The system can't learn about outputs it never produced, so learning only from feedback reinforces current behavior.
- **Anyone can click.** Feedback that flows into training data without review is a data-poisoning channel (P9, [§32](32-security-guardrails.md)).

So use signals to *route* traces to review, not as labels. The exception is the edit. The gap between what the model wrote and what the user changed it to is the richest signal you get: it is a supervised training target and a preference pair in one ([§35](35-ai-ux.md) covers designing for it).

### Synthetic data

**Synthetic data** is data generated by a model rather than collected from users. There are three reasons to use it:

- **Coverage.** Rare or dangerous cases that production hasn't produced yet, and the cold start before you have any traffic.
- **Privacy.** Lookalike records in place of real ones.
- **Volume.** Training data at a fraction of the cost of human labeling.

**Methods.**

- **Seed- or persona-driven generation.** Give the generator a seed example and a varying condition (a persona, a product area, a difficulty level) and ask for something new.
  - Ge et al. (Jun 2024) took this to the extreme with Persona Hub, "a collection of 1 billion diverse personas automatically curated from web data," each one a perspective to condition generation on.
  - Conditioning matters more now than it used to. Current Claude models reject non-default `temperature` ([§02](02-how-llms-work.md)), so diversity has to come from what you put in the prompt.
- **Self-Instruct** (Wang et al., Dec 2022). Start from 175 human-written seed tasks. The model writes new instructions, then inputs and outputs for them.
  - A new instruction joins the pool only if its ROUGE-L similarity (a word-overlap score) to every existing instruction is below 0.7.
  - Applied to GPT-3, it produced about 52K instructions and a 33% absolute improvement on the Super-NaturalInstructions benchmark.
  - Stanford's Alpaca (Mar 2023) used the recipe with `text-davinci-003` as the generator. It produced 52K demonstrations for under $500 and fine-tuned LLaMA 7B on them.
- **Evolution, or Evol-Instruct** (Xu et al., Apr 2023, the WizardLM paper). An LLM rewrites existing instructions to be harder or different, and failures are filtered out.
  - "In-depth" evolution makes an instruction harder: add constraints, deepen, concretize, increase reasoning steps, complicate the input.
  - "In-breadth" evolution mutates it into a new instruction.
  - An "instruction eliminator" filters out evolutions that failed.
  - The result is that simple seeds become a range of difficulties.
- **Distillation from a stronger model.** A *teacher* model answers your real inputs, and you train or prompt a smaller *student* on its outputs ([§29](29-adapting-models.md); DeepSeek's R1 distillations are in [§04](04-reasoning-models.md)).

**Quality control.** Run filters cheapest first:

1. Check that the output is valid against your schema. Structured outputs guarantee this ([§06](06-structured-outputs.md)).
2. Apply length and language heuristics, and catch refusals.
3. Deduplicate against the existing pool.
4. Decontaminate against the eval set.
5. Run execution checks where the output can be executed: does the SQL run, do the tests pass?
6. Have an LLM judge score the output against a rubric.
7. Audit a sample by hand.

Measure diversity as well as quality:

- **distinct-n:** unique n-grams divided by total n-grams.
- **Embedding spread:** how far apart the examples sit in embedding space.
- **Intent coverage:** how well the examples cover a taxonomy of intents, compared with production traffic.

In the stub below, diversity comes from personas crossed with seeds. The filters run in cost order, and every kept row carries its provenance. The similarity function is the snippet above with one-word shingles, to keep it short.

```python
import itertools, json, os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["question", "answer"],
          "properties": {"question": {"type": "string"}, "answer": {"type": "string"}}}

def generate(persona, seed):  # diversity comes from persona x seed, not from temperature
    r = client.messages.create(
        model="claude-sonnet-5-5", max_tokens=2048,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": f"Persona: {persona}\nSeed task: {seed}\n"
                   "Write ONE realistic question this persona would ask about a related but "
                   "different task (not a paraphrase of the seed), and a correct, short answer."}])
    return json.loads(next(b.text for b in r.content if b.type == "text"))  # schema-valid JSON

def words(t): return set(t.lower().split())
def sim(a, b): return len(words(a) & words(b)) / max(1, len(words(a) | words(b)))
def judge_ok(ex): return True  # stub: a separate grader model + rubric, spot-checked by humans

def keep(ex, pool, eval_set):  # cheap filters first, the expensive judge last
    q = ex["question"]
    if not 6 <= len(q.split()) <= 120:
        return False  # degenerate length
    if any(sim(q, p["question"]) > 0.6 for p in pool):
        return False  # near duplicate of something already kept
    if any(sim(q, e) > 0.6 for e in eval_set):
        return False  # too close to an eval item: it would contaminate the test
    return judge_ok(ex)

personas = ["a new analyst writing their first SQL", "a staff engineer debugging Spark skew"]
seeds = ["Why is my GROUP BY slow?", "How do I dedupe late-arriving events?"]
eval_set = ["Why is my GROUP BY query slow on a big table?"]
pool = []
for persona, seed in itertools.product(personas, seeds):
    ex = generate(persona, seed)
    if keep(ex, pool, eval_set):  # provenance travels with every synthetic row
        pool.append({**ex, "persona": persona, "seed": seed, "generator": "claude-sonnet-5-5"})
vocab = set().union(*(words(p["question"]) for p in pool))
print(f"kept {len(pool)}/4; distinct words: {len(vocab)} (a crude diversity metric)")
```

**Risks.**

- **Model collapse.** Shumailov et al. (Nature, Jul 2024) found that "indiscriminate use of model-generated content in training causes irreversible defects in the resulting models, in which tails of the original content distribution disappear."
  - The mechanism is repeated resampling. Each generation learns from a finite sample of the previous generation's output, rare events are under-sampled, and the errors compound. Eventually behavior converges to "a point estimate with very small variance."
  - The collapse setup *replaces* real data with synthetic data, generation after generation. Gerstgrasser et al. (Apr 2024) found that *accumulating* synthetic data alongside the original real data avoided collapse in their experiments.
  - The practical rule: keep real data as the anchor, tag every row's origin, and track the synthetic share.
- **Homogeneity.** A model's outputs cluster around its own idea of typical.
  - Synthetic users sound alike and ask tidy questions. They lack the typos, mixed languages and half-formed requests of real users.
  - An eval built only from them measures the model's picture of your users, not your users.
  - If the same model family also does the grading, it adds its preference for its own style on top.
- **Licensing and terms of use.** Model outputs come with contracts.
  - Anthropic's commercial terms forbid using its services "to build a competing product or service, including to train competing AI models."
  - Google's Gemini API terms say you "may not use the Services to develop models that compete with the Services."
  - Alpaca was released for academic research only, partly because OpenAI's terms "prohibit developing models that compete with OpenAI."
  - On Feb 23, 2026, Anthropic reported "industrial-scale" campaigns by three AI labs: over 16 million exchanges through about 24,000 fraudulent accounts, aimed at distilling Claude. The same post calls distillation "a widely used and legitimate training method."
  - Distilling a narrow internal classifier is a different question from training a general model. Either way, read the teacher's terms, get legal review, and record the generator in provenance.

### Data for evals vs data for training

The same pipeline feeds both, but the requirements differ.

- **An eval set is a measuring instrument.** It is small, precise, human-verified and frozen, and it represents production traffic plus the hard cases you care about.
- **Training data is fuel.** It is large, diverse and filtered, and it can tolerate more noise.

The one hard rule is that the two never overlap. That is why the dedup and decontamination checks run across them. Synthetic data can go into both, but synthetic eval cases need human review: an eval that a model wrote and a model grades can agree with itself about the wrong answer.

### Preference data for DPO

A **preference pair** is a prompt with two responses, one labeled *chosen* (better) and one *rejected* (worse). DPO ([§02](02-how-llms-work.md)) trains on these pairs directly. It raises the probability of the chosen response relative to a frozen reference copy of the model and lowers the probability of the rejected one. A parameter, β, controls how far the model may move from the reference. Hugging Face's TRL library uses this common format:

```json
{"prompt":   [{"role": "user", "content": "Summarize this incident for the status page."}],
 "chosen":   [{"role": "assistant", "content": "Between 09:02 and 09:40 UTC, 4% of API requests failed..."}],
 "rejected": [{"role": "assistant", "content": "We had some issues this morning. Sorry!"}]}
```

Sources of pairs, roughly from cheapest to most expensive:

- user edits (the model's draft is rejected and the edited version chosen)
- choices made after regenerating a response
- side-by-side comparisons
- a judge model ranking several samples
- expert rankings

Pairs are worth collecting when people can tell better from worse but can't easily write the ideal answer. Watch for confounds. If chosen responses are systematically longer, the model learns "longer is better" rather than what you meant.

### Data contracts and quality tests

A *data contract* is an agreed schema plus a set of guarantees between whoever produces a dataset and whoever consumes it, enforced by tests rather than goodwill. Dataset tables deserve the same treatment as any gold table, and the tests carry over almost one for one:

```text
contract: support_examples  (gold layer)
  columns:
    example_id                 unique, not null
    split                      in {train, dev, test}; immutable once assigned
    labels.failure_mode        in the failure taxonomy
    provenance.source_trace_id not null unless provenance.origin = 'synthetic'
    provenance.pii_scrubbed    = true
  tests:
    unique(content_hash)                                  # no exact duplicates
    no pair across splits with shingle Jaccard >= 0.8     # no leakage
    synthetic share of split 'test' <= <your cap>         # evals stay anchored in reality
    label distribution drift vs previous version < <threshold>
    test split re-sampled from production at least quarterly   # freshness
```

dbt's model contracts and its `unique`, `not_null` and `accepted_values` tests are the same idea applied to SQL models. Two tests are new: leakage across splits and the share of synthetic rows.

### Failure modes

- **Hoarding.** Millions of traces, none labeled. The flywheel never turns.
- **Self-reinforcing loops.** Training on the model's own accepted outputs amplifies its existing habits.
- **Leakage.** The eval score climbs because test cases leaked into prompts, few-shot pools or training data, not because the system improved.
- **Stale evals.** The eval set reflects last year's traffic, so scores rise while users complain.
- **PII in the wrong place.** Raw traces get exported to a labeling vendor or baked into a fine-tune.
- **Goodhart on feedback.** Optimizing the thumbs-up rate produces flattering answers. (Goodhart's law: a measure that becomes a target stops being a good measure.)

## Comparison

**Feedback signals**

| Signal | Type | What it really measures | Main bias | Best use |
|---|---|---|---|---|
| Thumbs up/down | Explicit | Momentary satisfaction | Few, extreme users; rewards agreeable answers | Route traces to review |
| Edit or correction | Explicit | What the user wanted instead | Users fix only what blocks them | Training targets and preference pairs |
| Acceptance (accept, copy, insert) | Implicit | "Good enough to use right now" | Silent reverts later | Online metric, with a delayed check |
| Retry or regenerate | Implicit | Dissatisfaction, or curiosity | Ambiguous intent | Finding failure clusters |
| Rephrase or follow-up correction | Implicit | The model misunderstood | Needs a classifier to detect | Finding intent failures |
| Abandonment or escalation | Implicit | Gave up, or finished | Ambiguous; confounded by UI changes | Funnel analysis, sampling |

**Ways to generate data**

| Method | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Seed/persona-driven | Vary conditions (persona, topic, difficulty) around seeds | Controllable coverage | Only as diverse as your list of conditions | Eval coverage gaps, cold start |
| Self-Instruct | Model writes new tasks from a seed pool; similarity filter | Breadth from a few seeds | Drifts toward generic tasks in the generator's style | Broad instruction data |
| Evol-Instruct | Rewrite seeds to be harder or different; eliminate failures | A range of difficulty | Evolved tasks can turn unnatural or unsolvable | Hard cases, stress tests |
| Distillation | A strong teacher answers your real inputs | High-quality outputs on your real distribution | Terms of use; capped by the teacher | Training a smaller student ([§29](29-adapting-models.md)) |
| Human-written | Experts write the cases | Real nuance; trustworthy | Slow and expensive | Gold eval sets, rubrics |

**Eval data vs training data**

| | Eval data | Training data |
|---|---|---|
| Job | Measure | Change behavior |
| Typical size | Tens to low thousands | Hundreds to millions |
| Quality bar | Every label verified | Filtered; some noise tolerated |
| Change rate | Frozen versions, refreshed deliberately | Grows continuously |
| Synthetic share | Low, every item human-reviewed | Can be high, anchored in real data |
| Biggest risk | Leakage, staleness | Collapse, homogeneity, copied PII |

## What it didn't solve

Good data lets you fix most failures with better prompts, retrieval and evals. Some failures survive all of that. The model may not hold a format or a tone across thousands of cases. It may keep getting a judgment subtly wrong. Or a frontier model may simply be too slow and expensive for a narrow, high-volume task. With labeled examples and preference pairs in hand, you can change the model itself. The open question is when that pays off, given that the next model release may beat your fine-tune. → Next: [§29 Adapting Models](29-adapting-models.md)

## Check your understanding

**Q: Why is a labeled set of your product's failures a more durable asset than the model you use?**

The model is rented: competitors call the same weights, and you will replace it within months (P12). A labeled failure set encodes your users' real distribution and your judgments of good and bad. Nobody else has it, and it carries over to the next model, both as the eval that validates the migration and as few-shot or training data. The cost is expert labeling time and regular refreshes. Raw, unlabeled logs don't count; they become an asset only once the loop is closed.

**Q: What would happen if you split support tickets into train and test sets randomly by row?**

Customers file near-identical tickets, so near-duplicates land on both sides of the split. A fine-tune or few-shot selector effectively sees test answers during training, and the test score measures memorization rather than generalization. Split by account, conversation or time, and run near-duplicate checks across splits before each run. A random row split is fine only when rows are truly independent, which is rare for user data.

**Q: Thumbs-down vs user edits: which makes better training data, and why?**

Edits. A thumbs-down says a response failed, but not why or what would have been right, and it comes from a biased sample of users. An edit puts the user's corrected version next to the model's draft, which gives you a supervised target and a preference pair at once. Edits are biased too: users fix only what blocks them, so an unedited response isn't necessarily correct. Treat thumbs as a triage signal and edits as candidate labels that still get reviewed.

**Q: Why can't you get more diverse synthetic data from current Claude models by raising the temperature, and what do you do instead?**

Current Claude models reject non-default temperature ([§02](02-how-llms-work.md)). Even where it is allowed, temperature only spreads probability across nearby phrasings of the same typical answer; it doesn't invent new user types or tasks. Diversity has to come from conditioning: vary personas, seeds, topics and difficulty in the prompt, evolve seeds into harder variants, and filter near-duplicates. Then measure diversity (distinct-n, embedding spread, intent coverage) instead of assuming it.

**Q: Does model collapse mean you should never train on synthetic data?**

No. Shumailov et al. showed collapse when each generation trains indiscriminately on the previous generation's output: rare events are under-sampled at every resampling step, so the tails vanish and variance shrinks. Gerstgrasser et al. found that accumulating synthetic data alongside the original real data avoided collapse. So keep real data as the anchor, filter and verify synthetic rows, tag their provenance, and watch the synthetic share. Rare cases, which collapse removes first, should stay human-sourced.

**Q: Why should synthetic eval cases get more human review than synthetic training data?**

An eval is a measuring instrument. One wrong label skews every comparison made with it from then on, while a noisy training row is diluted among thousands of others. Synthetic cases also reflect the generator's picture of your users, and if a related model grades them, generator and grader can agree on the wrong answer. Review every synthetic eval item and cap the synthetic share. For bulk training data, sampled audits are enough.

**Q: Why does lineage from trace to example matter for privacy?**

When a user asks to be deleted, you have to find everywhere their data went. With lineage, meaning trace IDs, dataset versions and a record of which models trained on which versions, you can delete their rows and know exactly which models need retraining. Without it you can't answer the question, and data trained into weights can't be removed surgically ([§17](17-memory.md)). Lineage costs a few columns per row, so there's no good reason to skip it.

## Takeaways

- Traces show failures. A data flywheel turns them into labeled datasets that drive a change and then stay as eval cases.
- The model is rented and will be replaced. Your labeled data and evals compound and carry over to the next model (P12).
- Treat datasets as gold tables: schema, lineage, versions, two-layer dedup (hashes, then shingles with MinHash), PII scrubbing, group-based splits, contracts.
- Feedback signals are biased and are not labels. Use them to route traces to review. Edits are the richest signal.
- Synthetic data buys coverage, privacy and volume. Diversity comes from conditioning, and quality comes from filters run cheapest first.
- Model collapse comes from replacing real data with synthetic data. Keep real data as the anchor and tag provenance.
- Read the terms before you distill from someone else's model.
- Eval data and training data never overlap, and synthetic eval cases get human review.

## Sources

- Shumailov et al., "AI models collapse when trained on recursively generated data," *Nature* 631 (Jul 2024): https://www.nature.com/articles/s41586-024-07566-y
- Gerstgrasser et al., "Is Model Collapse Inevitable? Breaking the Curse of Recursion by Accumulating Real and Synthetic Data," Apr 2024: https://arxiv.org/abs/2404.01413
- Wang et al., "Self-Instruct: Aligning Language Models with Self-Generated Instructions," Dec 2022: https://arxiv.org/abs/2212.10560
- Xu et al., "WizardLM: Empowering Large Pre-Trained Language Models to Follow Complex Instructions" (Evol-Instruct), Apr 2023: https://arxiv.org/abs/2304.12244
- Ge et al., "Scaling Synthetic Data Creation with 1,000,000,000 Personas," Jun 2024: https://arxiv.org/abs/2406.20094
- Taori et al., Stanford CRFM, "Alpaca: A Strong, Replicable Instruction-Following Model," Mar 13, 2023: https://crfm.stanford.edu/2023/03/13/alpaca.html
- Lee et al., "Deduplicating Training Data Makes Language Models Better," Jul 2021: https://arxiv.org/abs/2107.06499
- Apache Spark MLlib, Locality Sensitive Hashing (MinHash for Jaccard distance): https://spark.apache.org/docs/latest/ml-features.html
- Rafailov et al., "Direct Preference Optimization," May 2023: https://arxiv.org/abs/2305.18290
- Hugging Face TRL, dataset formats (preference): https://huggingface.co/docs/trl/dataset_formats
- OpenAI, Model optimization guide: https://developers.openai.com/api/docs/guides/model-optimization
- Anthropic, Commercial Terms of Service (section D.4): https://www.anthropic.com/legal/commercial-terms
- Google, Gemini API Additional Terms of Service: https://ai.google.dev/gemini-api/terms
- Anthropic, "Detecting and preventing distillation attacks," Feb 23, 2026: https://www.anthropic.com/news/detecting-and-preventing-distillation-attacks
- Martin Casado and Peter Lauten (a16z), "The Empty Promise of Data Moats," May 9, 2019: https://a16z.com/the-empty-promise-of-data-moats/
- Chip Huyen, *AI Engineering* (O'Reilly, 2025), table of contents (Ch. 8 Dataset Engineering; Ch. 10 User Feedback): https://github.com/chiphuyen/aie-book/blob/main/ToC.md
- dbt, Model contracts: https://docs.getdbt.com/docs/mesh/govern/model-contracts
