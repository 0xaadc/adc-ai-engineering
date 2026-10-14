# 28. Data Flywheels and Synthetic Data

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This Part 7 discipline applies to every era: a single prompt, a RAG system and a multi-step agent all improve the same way. [§26](26-evals.md) gave you evals, the tests for a probabilistic system (P4). [§27](27-observability.md) gave you traces, the record of what happened in production. A trace shows you a failure but doesn't fix it. Something has to turn traces into labeled examples, examples into datasets, and datasets into changes you can measure. That is a data pipeline, the part of AI engineering closest to what you already do. P4 (correctness is a rate measured on data), P5 (some fixes belong in context, some in weights) and P12 (models get replaced, datasets carry over) drive it.

## Why this exists

Watch what most teams do with traces. They open a dashboard, read a few bad conversations, tweak the prompt and move on. Nothing accumulates. After the next model upgrade the same failure returns, and nobody can say whether the new prompt is better, because there is no fixed set of cases to compare on.

A **data flywheel** is a loop in which usage produces data that improves the product, which attracts more usage:

**usage → traces → labeled failures → datasets → better prompts, retrieval, evals or fine-tunes → better product → more usage**

Each turn should leave something durable: an eval case that keeps a fixed bug fixed, a few-shot example, a retrieval fix, a training pair. OpenAI's optimization guide describes the same loop as "a flywheel of feedback that leads to better prompts and better training data for fine-tuning."

**Why data, not the model, is the defensible asset.** The model is rented. Competitors call the same API with the same weights, and within months you will both switch to a better model (P12). Prompts are partly model-specific, and fine-tunes are retired along with their base model ([§29](29-adapting-models.md)). The data is different: the real distribution of your users' tasks, the failures you found and your judgments of good and bad can't be copied, and they survive a model switch. Your eval set is how you migrate to the next model safely; your labeled failures are what you prompt or train it with.

Be honest about the limits. "Data moat" is an old pitch, and a16z's Martin Casado and Peter Lauten argued in 2019 ("The Empty Promise of Data Moats") that for most enterprise companies data network effects are hard to find and the value of more data flattens out. An unlabeled trace is worth about as much as an unread log file. The defensible part is narrow and expensive to copy: labeled examples of your domain's hard cases, rubrics written by your experts, and an eval set that mirrors your real traffic. And the flywheel turns only if someone closes the loop.

## How it works (under the hood)

### The loop as a pipeline

```text
production ─► traces (§27) ─► triage ─────► candidates ──► labels ────────► datasets ─────► change ONE lever ─► eval (§26)
 traffic      raw events      failure       redacted,      experts,         versioned,      prompt, retrieval,   same frozen
    ▲                         signals,      deduped,       vendor, or       eval and        tools, few-shot,     dataset
    │                         sampling      with lineage   LLM + audit      train splits    fine-tune (§29)      version ──┐
    └──────────────────────────────────────── ship, then more and better usage ◄──────────────────────────────────────────┘
```

If you know the medallion architecture, this is it: traces are bronze (raw, append-only), candidate examples are silver (cleaned, deduplicated, scrubbed of personal data), and labeled datasets are gold (curated, versioned, under contract). Two rules keep the loop honest. **Fix with the cheapest lever**: most failures yield to a prompt, retrieval or tool change, not to training. And **every fixed failure becomes an eval case**, so it stays fixed as a regression test.

### Data engineering for AI datasets

**The unit is an example, and it needs a schema.** An *example* is one input plus what you know about the right output:

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

**Lineage from trace to example.** Each example keeps its source trace ID and the model and prompt version that produced it. That lets you debug ("why is this case in the eval?") and audit contamination. It also lets you honor deletion requests. Deleting a user's rows is easy, but data trained into weights can't be removed without retraining ([§17](17-memory.md)), so you must know which datasets and which models contain it.

**Versioning.** An eval score means nothing without the dataset version behind it, just as a metric means nothing without its table snapshot. Freeze eval sets as named versions (Delta or Iceberg time travel, DVC, lakeFS or hub dataset revisions all work) and log dataset version, prompt version and model ID with every run. Two prompts compared on two eval versions have taken two different tests.

**Deduplication.** In training data, duplicates over-weight a few cases and encourage memorization. Lee et al. (2021) found that deduplication made models emit memorized text ten times less often and reach the same or better accuracy in fewer steps. In eval data, duplicates inflate the score of whatever case is repeated, and across splits they leak test answers into training. There are three layers:

- **Exact:** hash a normalized form (lowercase, collapsed whitespace, PII placeholders) and drop repeats.
- **Near:** break each text into *shingles*, the set of overlapping k-word windows, and compare sets with *Jaccard similarity*, |A ∩ B| / |A ∪ B|. Pairwise comparison is O(n²). At scale, *MinHash* compresses each shingle set into a short signature whose agreement rate estimates Jaccard, and *locality-sensitive hashing (LSH)* buckets signatures so only likely matches are compared. Spark MLlib ships this as `MinHashLSH`; Lee et al. used MinHash over 5-grams.
- **Paraphrase:** "How do I get a refund" and "refund process?" share no shingles. Catching them needs embeddings and a similarity threshold ([§08](08-embeddings-and-search.md)).

This snippet extracts candidate examples from traces with lineage and the first two layers:

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

**PII.** *Personally identifiable information* (names, emails, phone numbers, addresses, account numbers) should be redacted at ingestion, before any labeler, vendor or training job sees it. The regexes above are a floor: they miss names and would redact a long order number as a phone. Real pipelines add a named-entity detector and audit samples. Pseudonymize user IDs and keep the mapping in a restricted table so deletion still works. Synthetic data isn't automatically private either, because a generator prompted with real records can copy them.

**Train, dev and test separation.** Split by group, not by row. Customers file near-identical tickets, so a random row split puts the same problem on both sides and the test score measures memory. Split by account, conversation or time, lock the test set, and run the near-duplicate check *across* splits before every training run.

**Labeling workflows.** Most teams mix three. *In-house experts* are slow and expensive but define "correct", so you need them for rubrics, gold sets and high-stakes labels. *Vendors* give scale in exchange for written guidelines, calibration rounds, hidden gold questions and a PII review. *LLM-assisted labeling with human audit* has a model label everything while humans label a random sample. Before trusting the model, measure its agreement with the humans, for example with *Cohen's kappa* (agreement corrected for chance: 1 is perfect, 0 is chance). Judges have known biases ([§26](26-evals.md)). First, though, measure agreement among the humans. If experts working independently disagree, the bug is in the task definition, and no data or training will fix it ([§29](29-adapting-models.md)).

### Feedback signals

*Explicit feedback* is what users tell you on purpose: thumbs, ratings, corrections, edits. *Implicit feedback* is what behavior reveals: accepting a suggestion, copying an answer, retrying, rephrasing, abandoning, escalating to a human. Both are biased:

- **Selection:** few users click thumbs, and those who do are unusually annoyed or delighted.
- **Satisfaction isn't correctness:** users upvote confident, agreeable answers, the pressure that makes RLHF models sycophantic ([§02](02-how-llms-work.md)).
- **Ambiguity:** a retry may mean "wrong" or "show me another"; abandonment may mean "gave up" or "done"; an accepted suggestion may be silently reverted.
- **Only what you showed:** users react only to outputs the system chose, so learning from feedback alone reinforces current behavior.
- **Anyone can click:** feedback that flows into training data unreviewed is a poisoning channel (P9, [§32](32-security-guardrails.md)).

So use signals to *route* traces to review, not as labels. The exception is the edit: the model's draft next to the user's corrected version is both a supervised target and a preference pair ([§35](35-ai-ux.md) covers capturing it).

### Synthetic data

**Synthetic data** is generated by a model rather than collected from users. It buys **coverage** (rare or dangerous cases production hasn't produced yet, and the cold start before you have traffic), **privacy** (lookalike records instead of real ones) and **volume** (training data at a fraction of human labeling cost).

**Methods.**

- **Seed- or persona-driven generation.** Give the generator a seed example plus a varying condition (persona, product area, difficulty) and ask for something new. Persona Hub (Ge et al., Jun 2024) scaled this to "1 billion diverse personas automatically curated from web data." Conditioning matters more now: current Claude models reject non-default `temperature` ([§02](02-how-llms-work.md)), so diversity must come from the prompt.
- **Self-Instruct** (Wang et al., Dec 2022). From 175 human-written seed tasks, the model writes new instructions, then inputs and outputs. A new instruction joins the pool only if its ROUGE-L similarity (a word-overlap score) to every existing one is below 0.7. On GPT-3 it produced about 52K instructions and a 33% absolute gain on Super-NaturalInstructions. Stanford's Alpaca (Mar 2023) ran the recipe with `text-davinci-003`, generating 52K demonstrations for under $500 to fine-tune LLaMA 7B.
- **Evol-Instruct** (Xu et al., Apr 2023, WizardLM). An LLM rewrites seed instructions "in-depth" (add constraints, deepen, concretize, increase reasoning steps, complicate the input) or "in-breadth" (mutate into a new instruction), and an "eliminator" drops failed rewrites. Simple seeds become a spread of difficulty.
- **Distillation.** A stronger *teacher* model answers your real inputs, and a smaller *student* is trained or prompted on its outputs ([§29](29-adapting-models.md); R1's distillations are in [§04](04-reasoning-models.md)).

**Quality control.** Run filters cheapest first:

1. Schema validity. Structured outputs guarantee it ([§06](06-structured-outputs.md)).
2. Length, language and refusal heuristics.
3. Dedup against the pool, then decontamination against the eval set.
4. Execution checks wherever possible: does the SQL run, do the tests pass?
5. An LLM judge with a rubric.
6. A human audit of a sample.

Measure diversity as well as quality: *distinct-n* (unique n-grams over total n-grams), spread in embedding space, and coverage of an intent taxonomy compared with production traffic. In the stub below, diversity comes from personas crossed with seeds, the filters run in cost order, and every kept row carries provenance. Its `sim` is the shingle Jaccard from above with one-word shingles.

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

- **Model collapse.** Shumailov et al. (*Nature*, Jul 2024) found that "indiscriminate use of model-generated content in training causes irreversible defects in the resulting models, in which tails of the original content distribution disappear." The mechanism is repeated resampling. Each generation learns from a finite sample of the previous one's output, rare events get under-sampled, and errors compound until behavior converges to "a point estimate with very small variance." Their setup *replaces* real data generation after generation. Gerstgrasser et al. (Apr 2024) found that *accumulating* synthetic data alongside the original real data avoided collapse. Keep real data as the anchor, tag every row's origin, and track the synthetic share.
- **Homogeneity.** A model's outputs cluster around its idea of typical. Synthetic users ask tidy questions, without the typos, mixed languages and half-formed requests of real users. So an eval built only from them measures the model's picture of your users. If the same model family grades, its preference for its own style piles on top.
- **Licensing and terms of use.**
  - Anthropic's commercial terms forbid using its services "to build a competing product or service, including to train competing AI models."
  - Google's Gemini API terms say you "may not use the Services to develop models that compete with the Services."
  - Alpaca was research-only partly because OpenAI's terms "prohibit developing models that compete with OpenAI."
  - On Feb 23, 2026, Anthropic reported "industrial-scale" campaigns by three labs to distill Claude, using over 16 million exchanges through about 24,000 fraudulent accounts. The same post calls distillation itself "a widely used and legitimate training method."
  - A narrow internal classifier is a different case from a general model, but either way read the teacher's terms, get legal review, and record the generator in provenance.

### Data for evals vs data for training

The same pipeline feeds both, with different requirements. An eval set is a measuring instrument: small, precise, human-verified, frozen, and representative of production plus the hard cases. Training data is fuel: large, diverse, filtered, tolerant of some noise. The hard rule is that they never overlap, which is why dedup and decontamination run across them. Synthetic data can feed both, but synthetic eval cases need human review, because an eval that a model wrote and a model grades can agree with itself about the wrong answer.

### Preference data for DPO

A **preference pair** is a prompt with two responses, one *chosen* (better) and one *rejected* (worse). DPO ([§02](02-how-llms-work.md)) raises the probability of the chosen response relative to a frozen reference copy of the model and lowers the rejected one, with a parameter β limiting how far the model moves. The format Hugging Face TRL uses:

```json
{"prompt":   [{"role": "user", "content": "Summarize this incident for the status page."}],
 "chosen":   [{"role": "assistant", "content": "Between 09:02 and 09:40 UTC, 4% of API requests failed..."}],
 "rejected": [{"role": "assistant", "content": "We had some issues this morning. Sorry!"}]}
```

From cheapest to most expensive, pairs come from user edits (draft rejected, edit chosen), regenerate-and-pick choices, side-by-side comparisons, a judge ranking several samples, and expert rankings. They pay off when people can tell better from worse but can't easily write the ideal. Watch for confounds: if chosen answers are systematically longer, the model learns "longer is better."

### Data contracts and quality tests

A *data contract* is an agreed schema and set of guarantees between a dataset's producer and its consumers, enforced by tests rather than goodwill. Treat dataset tables like any gold table:

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

dbt's model contracts and `unique`, `not_null` and `accepted_values` tests are the same idea for SQL models. What's new is testing for leakage across splits and for the synthetic share.

### Failure modes

- **Hoarding:** millions of traces, none labeled, so the flywheel never turns.
- **Self-reinforcement:** training on the model's own accepted outputs amplifies its habits.
- **Leakage:** scores climb because test cases leaked into prompts, few-shot pools or training data.
- **Stale evals:** the eval reflects last year's traffic, so scores rise while users complain.
- **Goodhart on feedback** (a measure that becomes a target stops being a good measure): optimizing the thumbs-up rate breeds flattering answers.

## Comparison

**Feedback signals**

| Signal | Type | What it really measures | Main bias | Best use |
|---|---|---|---|---|
| Thumbs up/down | Explicit | Momentary satisfaction | Few, extreme users; rewards agreeable answers | Route traces to review |
| Edit or correction | Explicit | What the user wanted instead | Users fix only what blocks them | Training targets, preference pairs |
| Acceptance (accept, copy, insert) | Implicit | "Good enough to use now" | Silent reverts later | Online metric with a delayed check |
| Retry or regenerate | Implicit | Dissatisfaction, or curiosity | Ambiguous intent | Finding failure clusters |
| Rephrase or follow-up correction | Implicit | Misunderstanding | Needs a classifier to detect | Finding intent failures |
| Abandonment or escalation | Implicit | Gave up, or finished | Ambiguous; confounded by UI changes | Funnel analysis, sampling |

**Ways to get examples**

| Method | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Production traces | Triage, redact, label | Your real distribution | Slow; only covers what happened | Always; the anchor |
| Seed/persona-driven | Vary conditions around seeds | Controllable coverage | Only as diverse as your conditions | Eval gaps, cold start |
| Self-Instruct | Model expands a seed pool; similarity filter | Breadth from few seeds | Drifts to generic tasks in the generator's style | Broad instruction data |
| Evol-Instruct | Rewrite seeds harder or different; eliminate failures | A range of difficulty | Can become unnatural or unsolvable | Hard cases, stress tests |
| Distillation | Teacher answers your real inputs | Strong outputs on your distribution | Terms of use; capped by the teacher | Training a student ([§29](29-adapting-models.md)) |

**Eval data vs training data**

| | Eval data | Training data |
|---|---|---|
| Job | Measure | Change behavior |
| Typical size | Tens to low thousands | Hundreds to millions |
| Quality bar | Every label verified | Filtered; some noise tolerated |
| Change rate | Frozen versions, refreshed deliberately | Grows continuously |
| Synthetic share | Low, every item reviewed | Can be high, anchored in real data |
| Biggest risk | Leakage, staleness | Collapse, homogeneity, copied PII |

## What it didn't solve

Good data fixes most failures through better prompts, retrieval and evals. Some survive all of that. The model may not hold a format or tone across thousands of cases, or may keep making a judgment subtly wrong. Or a frontier model may be too slow and expensive for a narrow, high-volume task. With labeled examples and preference pairs in hand you can change the model itself, but whether that pays off, when the next model release may beat your fine-tune, is a real question. → Next: [§29 Adapting Models](29-adapting-models.md)

## Check your understanding

**Q: Why is a labeled set of your product's failures a more durable asset than the model you use?**

The model is rented: competitors use the same weights, and you will replace it within months (P12). A labeled failure set encodes your users' real distribution and your judgments of good and bad, which nobody else has. It carries over to the next model, as the eval that validates the migration and as few-shot or training data. The cost is expert labeling time and regular refreshes, and raw unlabeled logs don't count.

**Q: What would happen if you split support tickets into train and test sets randomly by row?**

Customers file near-identical tickets, so near-duplicates land on both sides of the split. A fine-tune or few-shot selector effectively sees test answers, and the test score measures memorization rather than generalization. Split by account, conversation or time, and run near-duplicate checks across splits before each run. A random row split is fine only when rows are truly independent, which is rare for user data.

**Q: Thumbs-down vs user edits: which makes better training data, and why?**

Edits. A thumbs-down says a response failed, but not why or what would have been right, and it comes from a biased sample of users. An edit puts the corrected version next to the model's draft, giving you a supervised target and a preference pair at once. Edits are biased too, since users fix only what blocks them. Treat thumbs as triage and edits as candidate labels that still get reviewed.

**Q: Why can't you get more diverse synthetic data from current Claude models by raising the temperature, and what do you do instead?**

Current Claude models reject non-default temperature ([§02](02-how-llms-work.md)). Even where it's allowed, temperature only spreads probability across nearby phrasings of the typical answer; it doesn't invent new user types or tasks. Diversity has to come from conditioning: vary personas, seeds, topics and difficulty, evolve seeds into harder variants, and filter near-duplicates. Then measure diversity (distinct-n, embedding spread, intent coverage) rather than assuming it.

**Q: Does model collapse mean you should never train on synthetic data?**

No. Shumailov et al. showed collapse when each generation trains indiscriminately on the previous generation's output, which under-samples rare events at every step until the tails vanish. Gerstgrasser et al. found that accumulating synthetic data alongside the original real data avoided collapse. So keep real data as the anchor, filter and verify synthetic rows, tag provenance and watch the synthetic share. Keep rare cases human-sourced, because collapse removes them first.

**Q: Why should synthetic eval cases get more human review than synthetic training data?**

An eval is a measuring instrument: one wrong label skews every later comparison, while a noisy training row is diluted among thousands. Synthetic cases also reflect the generator's picture of your users, and if a related model grades them, generator and grader can agree on the wrong answer. So review every synthetic eval item and cap the synthetic share. For bulk training data, sampled audits are enough.

**Q: Why does lineage from trace to example matter for privacy?**

When a user asks to be deleted, you must find everywhere their data went. With trace IDs, dataset versions and a record of which models trained on which versions, you can delete their rows and know which models need retraining. Without lineage you can't answer the question, and data trained into weights can't be removed surgically ([§17](17-memory.md)). It costs a few columns per row.

## Takeaways

- Traces show failures. A flywheel turns them into labeled datasets that drive a change and then stay on as eval cases.
- The model is rented. Your labeled data and evals compound and carry over to the next model (P12).
- Treat datasets as gold tables: schema, lineage, versions, two-layer dedup (hash, then shingles/MinHash), PII scrubbing, group-based splits, contracts.
- Feedback signals are biased routing hints, not labels. Edits are the richest signal.
- Synthetic data buys coverage, privacy and volume. Diversity comes from conditioning, and quality comes from filters run cheapest first.
- Model collapse comes from replacing real data. Keep real data as the anchor and tag provenance.
- Read the terms before distilling from someone else's model.
- Eval and training data never overlap, and every synthetic eval case gets human review.

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
