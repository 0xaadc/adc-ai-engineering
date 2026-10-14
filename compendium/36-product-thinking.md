# 36. AI Product Thinking

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This is Part 9, and it applies to every era, from a single prompt ([§05](05-api-and-prompting.md)) to a fleet of unattended loops ([§21](21-loop-engineering.md)). [§35](35-ai-ux.md) showed how to design the interface: streaming, approval steps, feedback capture. A well-designed AI product can still be the wrong product. It can target the wrong task or take the wrong amount of autonomy. Its cost can grow faster than its value, or it can depend on a capability the next model gives away for free. This section is about choosing what to build. Four principles drive it: value is a rate (P4), checking decides where AI pays (P8), every token costs money (P10), and models keep improving, so some products should wait (P12).

## Why this exists

Traditional product thinking assumes the feature works. A button that computes a total computes it every time, and the only question is whether people want it. An LLM feature has no yes-or-no answer to "does it work?" (P4). It works at some rate, on some distribution of inputs, at some cost per attempt, and its failures land on someone. So the product question splits into three:

1. **Does the value of a correct output exceed the total cost?** That means producing it, checking it, and cleaning up the failures that get through.
2. **Will that hold in production,** with real volume and the inputs users actually send?
3. **Will it hold after the next model release,** or will the vendor, or a competitor on the same API, ship it for free?

Demos make all three look answered. A demo is one sample (P4), drawn from the easy part of the input distribution, with an expert quietly fixing small errors. So the most common failure in AI products isn't technical. It is building something that works in the demo and doesn't pay in production, the AI version of the dashboard nobody opens after launch week.

## How it works (under the hood)

### Where probabilistic output is acceptable (P4)

Start from the failure, not the feature. An AI feature is worth building where an occasional wrong output is acceptable *given how it will be caught*. Three properties decide that.

**1. Verification is cheaper than generation (P8).** Jason Wei calls this the **asymmetry of verification**: "some tasks are much easier to verify than to solve." A sudoku is slow to solve and instant to check, and so is code with good tests. A novel legal argument may take as long to verify as to write. If a reviewer needs 1 minute to check what took 20 minutes to write, AI drafting saves up to 19 minutes per task, even when some drafts are thrown away. If checking takes as long as doing, AI saves nothing, because a careful person must redo the work to trust it. Anthropic's "Building effective agents" (Dec 2024) singles out support and coding agents for this reason. In support, "success can be clearly measured through user-defined resolutions". In coding, "code solutions are verifiable through automated tests". Wei's corollary, the "verifier's rule", says "the ease of training AI to solve a task is proportional to how verifiable the task is." That matters for build-vs-wait below.

**2. Tolerance for errors, and the cost of each kind.** Errors don't all cost the same. Ask four questions about each type:

- **Visible or silent?** A wrong autocomplete is seen and ignored; a wrong number in a contract summary isn't seen.
- **Reversible or not?** A draft can be fixed; a refund, a deletion or a trade can't be undone.
- **Which direction is worse?** For fraud screening, a missed fraud costs far more than a false alarm. You tune the threshold to that asymmetry, so you need the price of each direction.
- **Who absorbs it?** An analyst who knows the tool is fallible, or a customer who takes the answer as your company's word.

Data engineers know error budgets from SLOs, and the idea transfers. Set an acceptable failure rate for each error type before you build, and design so failures land on the cheap side.

**3. "The human in the loop is the product."** Many successful AI products aren't automation. Code completion, draft replies for support agents, and first-pass SQL for analysts all follow one pattern. The AI proposes and a skilled person accepts, edits or rejects, so what the product sells is *speed for that person*. The review step is the design, not a crutch to remove later. It makes a 70%-accurate model useful because the person catches the other 30%, and every accept, edit or reject is a free quality label for your evals ([§28](28-data-flywheels.md)).

The evidence supports augmentation, with a warning attached:

- **The gains are real and uneven.** Across 5,179 customer-support agents, an AI assistant raised issues resolved per hour by 14% on average and 34% for novices, with minimal effect on the most experienced (Brynjolfsson, Li and Raymond).
- **The gains reverse outside the model's competence.** In a preregistered experiment with 758 BCG consultants, GPT-4 users completed 12.2% more tasks, 25.1% faster and at higher quality on tasks inside the model's capability frontier. On a task chosen to lie outside it, the AI groups were correct 60% and 70.6% of the time, against 84.5% without AI (Dell'Acqua et al., *Organization Science*, 2026). The authors call this uneven boundary the **jagged frontier**.

A human in the loop helps only if the human actually checks, and people stop checking a tool that is usually right. Show sources, flag low-confidence parts, and make every check fast ([§35](35-ai-ux.md)).

### Picking use cases: value × feasibility × risk

Chip Huyen's *AI Engineering* (2025) covers this in chapter 1 under use case evaluation, setting expectations, milestone planning and maintenance. A practical version scores each candidate on four dimensions:

| Dimension | Question | How to measure it honestly |
|---|---|---|
| Value | What is a correct output worth? | Volume × time or money per task, from logs, not estimates |
| Feasibility | Can a model do it with data you can supply? | A pilot eval on 50–100 real inputs ([§26](26-evals.md)), not a demo |
| Risk | What does an uncaught error cost? | Error types × cost × who absorbs it |
| Verification cost | How long does checking take vs doing? | Time a reviewer on real outputs |

```text
                      cheap to verify, low error cost     costly to verify or costly errors
                    ┌──────────────────────────────────┬──────────────────────────────────┐
 high value,        │ AUTOMATE: code checks outputs,   │ AUGMENT: AI drafts, a human      │
 feasible now       │ humans sample, track error rates │ reviews or approves every output │
                    ├──────────────────────────────────┼──────────────────────────────────┤
 low value, or not  │ CHEAP EXPERIMENT: internal tool, │ SKIP OR WAIT: keep the eval and  │
 feasible yet       │ a nice-to-have                   │ re-run it on new models (P12)    │
                    └──────────────────────────────────┴──────────────────────────────────┘
```

**Automate vs augment.** Automate when errors are cheap, the check is computational (a schema, a totals check, tests), and human review would be the bottleneck. Augment when the work needs judgment, errors are costly or silent, or only a person can check. Most products start as augmentation and automate one task at a time, as evals show the rate is high and the remaining failures are cheap. That is P7 applied to a product: you turn the autonomy dial up with evidence.

**Start narrow:** one workflow, one user group, one measurable outcome. Narrow scope is what makes a system measurable. It gives you an input distribution you can sample (P4), failure types you can name, and tools you can scope to least privilege (P9). "An assistant for the whole company" has none of these.

The scoring function below encodes the grid. The weights are a judgment call, but verification cost gates everything, because a task that takes as long to check as to do has no leverage (P8).

```python
from dataclasses import dataclass

@dataclass
class UseCase:
    name: str
    value: int           # 1-5: what a correct output is worth (volume x stakes)
    feasibility: int     # 1-5: data access + pass rate on a pilot eval, not a demo
    error_cost: int      # 1-5: harm when a wrong output is NOT caught
    verify_ratio: float  # minutes to check one output / minutes to do it by hand

def score(uc: UseCase) -> tuple[float, str]:
    if uc.verify_ratio >= 1.0:               # checking costs as much as doing (P8)
        return 0.0, "skip: a human must redo the work to trust it"
    leverage = 1.0 - uc.verify_ratio         # share of human effort the AI can remove
    risk = uc.error_cost / 5                 # 0.2 (cosmetic) .. 1.0 (severe)
    priority = uc.value * uc.feasibility * leverage * (1.0 - 0.5 * risk)
    if uc.feasibility <= 2:                  # the model can't do it yet
        mode = "wait: keep the eval, re-run it on each new model (P12)"
    elif uc.error_cost >= 4:                 # costly errors: a person signs off
        mode = "augment: AI drafts, a human approves every output"
    elif uc.verify_ratio <= 0.1 and uc.error_cost <= 2:
        mode = "automate: code checks every output, humans sample"
    else:
        mode = "augment: AI drafts, a human reviews"
    return round(priority, 1), mode

candidates = [
    UseCase("invoice field extraction", 4, 4, 2, 0.05),   # schema + totals check
    UseCase("analyst SQL drafts", 4, 4, 3, 0.15),         # run it, compare rows
    UseCase("support reply drafts", 5, 4, 3, 0.20),
    UseCase("contract risk sign-off", 5, 3, 5, 0.60),
    UseCase("novel legal research memo", 4, 3, 4, 1.00),  # verifying = redoing
    UseCase("handwritten form reading", 4, 2, 3, 0.30),
]
for uc in sorted(candidates, key=lambda u: score(u)[0], reverse=True):
    pri, mode = score(uc)
    print(f"{pri:5.1f}  {uc.name:27} {mode}")
```

Invoice extraction ranks first and is fully automated, because a schema and an arithmetic check catch most errors for free. Support and SQL drafts follow as augmentation. The legal memo scores zero despite its value, because checking it means redoing it.

### Build, buy, or wait (P12)

There are three options, not two.

**Wait.** If the gap is model capability (the model can't read your handwritten forms, or can't hold a 40-step task together), the cheapest move may be to build the eval and nothing else. Scaffolding that compensates for a weak model is exactly what gets deleted (P12). Reasoning models absorbed the step-by-step prompt scaffolds of 2023 ([§04](04-reasoning-models.md)), and Anthropic dropped context resets once Opus 4.5 stopped showing "context anxiety" ([§16](16-context-engineering.md)). The verifier's rule predicts that easily verified tasks improve fastest, because labs can train on them. Waiting isn't idling. Build what survives model changes (the eval, data access, workflow integration) and skip the workaround.

**Buy.** Vendor platforms fit when the capability is a commodity and your workflow is standard: support automation, coding agents, enterprise assistants, the AI functions in your data platform. You inherit someone else's evals, upgrades and integrations. MIT NANDA's July 2025 report ("preliminary findings" from 52 interviews, 153 surveyed leaders and 300+ public initiatives) found that external partnerships reached deployment about 67% of the time, against about 33% for internal builds. The report itself warns that the outcomes are self-reported and may reflect organizational capability rather than the approach, so treat it as a hint.

**Build.** Build when the workflow, data or integration is your differentiator, when you need control of the data path, the evals or the unit cost, or when no vendor covers your edge cases. You also own maintenance, which is why Huyen lists it as a planning step: every model release means re-running evals and perhaps re-tuning prompts.

**Wrapper risk.** A **wrapper** is a product that is mostly a prompt and a UI over someone else's model. The vendor can ship it natively as it moves up the stack (document chat, research agents, memory, coding), and anyone with the same API can copy it. Defensibility comes from what the API doesn't provide: workflow integration, proprietary feedback loops, distribution, trust, and domain evals. Test it this way: if the next model were twice as good and half the price, would your product get better or become unnecessary? Build products that ride model improvements, so P12 works for you.

### Measuring value

Five families of metrics matter, and each can mislead on its own:

| Metric | What it measures | How it misleads | Pair it with |
|---|---|---|---|
| Task success | Share of tasks done correctly | Easy inputs, or a lenient judge | Evals on sampled production inputs; graders checked against human labels ([§26](26-evals.md)) |
| Time saved | Minutes saved per task | Self-reports overstate it | Measured time, including review and rework |
| Deflection | Contacts that never reach a human | Users who gave up count as "deflected" | Repeat-contact rate, resolution, satisfaction |
| Quality | Accuracy, completeness, tone | Fluent output looks right (P1) | Error-type audits; edit distance on accepted drafts |
| Adoption and retention | Who uses it, and who keeps using it | Novelty spikes in week one | Week-4 and week-8 retention by cohort |

**Perceived savings aren't measured savings.** In METR's randomized trial (Jul 2025), experienced open-source developers expected AI to speed them up by 24% and afterwards believed it had sped them up by 20%. In fact it made them 19% slower. METR's Feb 2026 follow-up says developers are probably faster with late-2025 tools. But because many now refuse to work without AI, selection effects made the new data "only very weak evidence" of the size of the gain. Self-reports are unreliable and productivity is hard to measure, so use logs, not surveys.

**Deflection isn't resolution.** In Feb 2024 Klarna said its assistant handled two-thirds of its customer-service chats in its first month, "the equivalent work of 700 full-time agents", with satisfaction on par with human agents and 25% fewer repeat inquiries. In May 2025 its CEO told Bloomberg that Klarna was hiring human agents again so customers could always reach a person, and acknowledged lower quality (secondary reports, **⚠ verify**). A deflection headline doesn't settle the value question, so keep measuring quality after launch.

**The pilot-to-production gap.** A demo uses hand-picked inputs, runs once (P4), and has an expert silently fixing errors. Production brings the long tail, real volume and no expert. LinkedIn's team (Apr 2024) "achieved 80% of the basic experience we were aiming to provide within the first month and then spent an additional four months attempting to surpass 95%." The NANDA report's headline, that "95% of organizations are getting zero return", comes from a small sample with a loose definition of success, so don't quote it as precise. Its diagnosis is more useful: "Most GenAI systems do not retain feedback, adapt to context, or improve over time." Systems that learn from their own usage ([§28](28-data-flywheels.md)) are the ones that cross the gap.

The ROI model below counts what demos leave out: review and rework time, errors that escape review, adoption and fixed costs.

```python
def monthly_roi(
    tasks: int,               # tasks per month in scope
    adoption: float,          # share of those tasks where people actually use the tool
    manual_min: float,        # measured minutes per task today (logs, not surveys)
    review_min: float,        # minutes to check one AI output
    success: float,           # share of AI outputs accepted after review (from evals)
    rework_min: float,        # minutes to fix or redo a failed output
    escape_rate: float,       # share of failures that slip past review anyway
    escape_cost: float,       # $ per escaped error (refund, incident, churn)
    ai_cost: float,           # $ in tokens per task, retries included (P10)
    hourly_cost: float,       # $ loaded cost per hour of the people doing the work
    fixed_monthly: float,     # $ for evals, monitoring, maintenance, platform fees
) -> dict:
    used = tasks * adoption
    ai_minutes = review_min + (1 - success) * rework_min    # checking is not free (P8)
    hours_saved = used * (manual_min - ai_minutes) / 60
    escaped = used * (1 - success) * escape_rate             # errors nobody caught
    value = hours_saved * hourly_cost
    cost = used * ai_cost + escaped * escape_cost + fixed_monthly
    return {"hours_saved": round(hours_saved), "value": round(value),
            "cost": round(cost), "net": round(value - cost)}

# Support reply drafts: 20k tickets a month, 9 minutes each by hand today.
base = dict(tasks=20_000, adoption=0.6, manual_min=9, review_min=2, success=0.8,
            rework_min=8, escape_rate=0.1, escape_cost=40, ai_cost=0.05,
            hourly_cost=45, fixed_monthly=8_000)
print("base         ", monthly_roi(**base))
print("slow check   ", monthly_roi(**{**base, "review_min": 6}))    # P8 eats the gain
print("low adoption ", monthly_roi(**{**base, "adoption": 0.1}))    # fixed costs win
print("costly errors", monthly_roi(**{**base, "escape_cost": 400})) # risk dominates
```

The base case nets about $30K a month. Each variant changes one input and turns the result negative: a 6-minute review eats most of the time saved, 10% adoption lets fixed costs win, and $400 per escaped error costs twice the value created. Tokens are the smallest cost line in every scenario, which is typical of augmentation products. People and errors dominate.

### Unit economics and pricing

Traditional software has close to zero marginal cost per user. AI products don't: every task burns tokens (P10), and heavy users can cost many times what light users do. Three numbers decide whether you have a business:

- **Cost per successful task, not per call.** An attempt that costs $0.08 and succeeds 80% of the time costs $0.10 per success with retries, plus review time. Agents make this volatile, since one task can take 5 turns or 50 (P7), so budget for the tail, not the mean.
- **Value per successful task,** from the ROI model.
- **Margin at scale,** after caching, routing and batching ([§30](30-cost-latency-reliability.md)). The price of a *fixed* level of capability has fallen fast: Epoch AI (Mar 2025) measured declines of 9× to 900× per year, depending on the benchmark. But growing products tend to move to bigger models and more thinking tokens, so don't assume the bill will shrink.

| Pricing model | Works when | Risk |
|---|---|---|
| Per seat | Cost per user is predictable and modest | Heavy users erase the margin |
| Usage-based (per token, task or credit) | Cost scales with use | Bills are unpredictable, so customers ration use |
| Outcome-based (per resolution, per accepted change) | Success is clearly measurable | You absorb failed attempts; disputes over what counts |

Outcome pricing signals the most confidence. Anthropic noted in Dec 2024 that several support-agent companies use "usage-based pricing models that charge only for successful resolutions." It works only when success can be measured, which brings you back to verification (P8).

### The org side

- **Forward-deployed engineering.** A **forward-deployed engineer** is embedded with a customer and builds the last mile: data connections, tools, prompts tuned on the customer's real inputs, evals. Palantir popularized the role in the 2000s, and AI labs and startups revived it because the pilot-to-production gap is mostly integration and evaluation work that can't be done from outside (secondary, **⚠ verify** origin details). It was a track at the AI Engineer World's Fair (Jun 30, 2026). [§38](38-disciplines-map.md) calls it "a role, not a technique": it's where product thinking happens on site.
- **Tiny teams.** swyx (Latent Space, Jul 2025) defined **Tiny Teams** as "teams with more $m in ARR than employees", and surveyed seven of them at the 2025 World's Fair: about 100 people and $200M ARR between them. Coding agents raise output per engineer, so a few senior generalists can ship what once took a department. The surveyed teams are survivors, though, and their figures are self-reported.
- **AI engineer vs ML engineer.** As [§01](01-first-principles.md) puts it, ML engineers build models and AI engineers build around a model they didn't train, a distinction Huyen's chapter 1 also draws. An AI product team needs product-minded engineers who write evals and read traces more than it needs model trainers. Add ML engineers when you fine-tune, distill or self-host ([§29](29-adapting-models.md), [§31](31-open-weights-self-hosting.md)), or when the feature sits beside a classical model such as ranking.
- **Change management.** NANDA also found that general chat tools spread widely for individual work, while tools for specific workflows stall. Value comes from changing the workflow, not from adding a chat box. That means training people on where the tool can be trusted (the jagged frontier), aligning incentives, redesigning the process around the review step, and naming owners who track adoption. People who don't trust a tool quietly route around it, and adoption shows it before ROI does.

### Data as moat

"Our data is our moat" is usually wrong in the sense people mean. Frontier models were pretrained on much of the public web, so generic text in your warehouse rarely gives a capability a competitor can't get. What compounds is narrower ([§28](28-data-flywheels.md)):

- **Outcome-labeled traces:** inputs, outputs, and what happened next (accepted, edited, escalated, refunded). Only your product sees these.
- **Your eval set:** curated failure cases from your domain. It survives every model change (P12), so it is the most durable data asset you have.
- **Human corrections:** edits and rejections that become data for fine-tuning or prompt optimization ([§29](29-adapting-models.md)).

The flywheel runs usage → traces → labeled failures → better evals, prompts or models → better product → more usage. It's a moat only if it spins. P12 also cuts against fine-tunes: a better base model can leapfrog yours, while your eval set lets you adopt that model the same week.

### Failure patterns

- **A solution looking for a problem.** "We need an AI strategy" yields a chatbot nobody asked for. Start from a task with volume, a cost, and an owner who wants it done faster.
- **An eval-less launch.** Without a measured success rate (P4), you can't tell whether a prompt change helped, a new model regressed, or the product works at all. Build 50–100 graded examples before launch ([§26](26-evals.md)).
- **Unbounded agent scope.** "It can do anything" means it can't be evaluated, secured or priced. Errors compound (P8), tools widen the attack surface (P9) and cost has no ceiling (P10). Narrow the task, cap turns and spend, and widen only with evidence.
- **Ignoring cost at scale.** A pilot with 20 friendly users costs pennies, while 50,000 users with long contexts and looping agents cost a fortune. Model cost per successful task at target volume first ([§30](30-cost-latency-reliability.md)).

## Comparison

**Automate, augment, wait, or skip**

| Mode | Choose when | What the human does | What you measure | Example |
|---|---|---|---|---|
| Automate | Errors cheap and reversible; checks computational; high volume | Samples outputs, handles escalations | Error rate per type, cost per success | Invoice extraction with schema and totals checks |
| Augment (review) | Checking far cheaper than doing; moderate errors | Accepts, edits or rejects each output | Acceptance rate, edit distance, time per task | Support reply drafts, SQL drafts |
| Augment (approve) | Errors costly, silent or irreversible | Signs off before anything takes effect | Approval rate, override reasons | Contract risk flags, large refunds |
| Wait | Real value, but the model fails your pilot eval | Keeps the eval current | Pass rate on each new model | Messy handwriting, very long autonomous tasks |
| Skip | Checking costs as much as doing, or value is low | Does the work as before | Nothing | Novel legal research memos |

**Build, buy, or wait**

| Option | Choose when | You own | Main risk | Under P12 |
|---|---|---|---|---|
| Buy | Commodity capability, standard workflow | Configuration, change management, acceptance evals | Lock-in; poor fit on edge cases | The vendor absorbs model upgrades |
| Build | Workflow, data or integration is your edge; you need control | Everything, including re-evaluation on each model | Slow delivery; scaffolding that ages | Thin harnesses improve with models; workarounds rot |
| Wait | The model can't do it yet, and the task is verifiable | The eval, data access, integration points | Arriving after a competitor | Often cheapest: the next model may close the gap |

## What it didn't solve

Product thinking tells you which problem to solve and how to judge success. It doesn't tell you which mechanism to use once you've chosen: RAG or fine-tuning, a workflow or an agent, one model or a router. Every decision in this compendium is a tradeoff like that, argued in its own section. The next section collects them and argues each one in both directions. → Next: [§37 Why X over Y](37-why-x-over-y.md)

## Check your understanding

**Q: Why is "verification is cheaper than generation" the first test for an AI use case?**

Because the human time saved is roughly the time to do the task minus the time to check the AI's output (P8). If checking takes a minute and doing takes twenty, AI drafting pays even when some drafts are discarded. If checking takes as long as doing, a careful person must redo the work to trust it, so the AI adds cost. Tasks with computational checks (tests, schemas, totals) are the best candidates, and tasks only an expert can verify slowly are the worst.

**Q: What would happen if you launched a support agent and reported only its deflection rate?**

You would count every customer who gave up as a success. Deflection measures contacts that didn't reach a human, not problems solved, so a frustrating bot can raise it. Pair it with repeat-contact rate, resolution checks and satisfaction, and keep tracking them after launch. Klarna's case shows that a strong deflection headline doesn't settle whether quality held up.

**Q: Automate vs augment: when should a feature keep a human approving every output?**

When errors are costly, silent or irreversible and no computational check can catch them: refunds, contract terms, medical or legal content. Approval puts the verifier where mistakes can't be undone (P8). The costs are human time and rubber-stamping, so make each check fast and show the evidence. Automate step by step as evals show high success rates and the remaining errors become cheap.

**Q: Why might "wait" be the best answer to a build-vs-buy question?**

Because scaffolding that works around a weak model tends to be deleted when a better model arrives (P12), and verifiable tasks are the ones labs improve fastest. Waiting means building the eval, data access and integration now, since all of them survive model changes, and re-running the eval on each release. It's the wrong answer when timing matters competitively and a narrower version works today.

**Q: Why do AI demos overstate value, and what closes the pilot-to-production gap?**

A demo is one sample (P4) on hand-picked inputs, with an expert fixing errors and nobody paying for review or failures. Production adds the long tail, volume, latency and cost limits; LinkedIn reached 80% quality in a month and spent four more months trying to pass 95%. The gap closes through evals on sampled production inputs, error analysis, and feedback loops that let the system learn from its own usage, not through a better demo.

**Q: Why is per-seat pricing risky for an agent product?**

Because cost per user isn't fixed (P10). Agents take a variable number of turns and heavy users consume many times the tokens of light ones, so a flat seat price can turn negative on your best customers. Usage pricing tracks cost but makes bills unpredictable. Outcome pricing aligns price with value, but only when success is clearly measurable and you can absorb failed attempts.

**Q: Is your company's data a moat for an AI product?**

Usually not in the form people mean, because generic documents add little that a frontier model or a competitor lacks. What compounds is data only your product produces: outcome-labeled traces, human corrections, and an eval set of your domain's failures. The eval set is the most durable of these, because it survives model changes (P12) and lets you adopt better models quickly. It's a moat only if the flywheel actually turns usage into improvements.

## Takeaways

- An AI feature works at a rate (P4), so value is correct outputs minus the cost of checking and of escaped errors.
- The best use cases are verifiable: checking is much cheaper than doing (P8).
- Price each error type by visibility, reversibility, direction and who absorbs it, then set an error budget.
- Augment first, automate with evidence, and start narrow enough to evaluate.
- Build, buy and wait are all real options; build the eval in every case, because it survives model changes (P12).
- Measure task success, logged time, resolution, quality and retention, not demos, surveys or deflection alone.
- Unit economics are per successful task, and pricing should follow where cost and value sit.
- The durable moat is outcome-labeled traces plus a domain eval set, fed back through a working flywheel.

## Sources

- Chip Huyen, *AI Engineering* (O'Reilly, 2025), table of contents (chapter 1: "Planning AI Applications", "AI Engineering Versus ML Engineering"): https://github.com/chiphuyen/aie-book/blob/main/ToC.md
- Anthropic, Erik Schluntz and Barry Zhang, "Building effective agents" (Dec 19, 2024), Appendix 1, "Agents in practice": https://www.anthropic.com/engineering/building-effective-agents
- Jason Wei, "Asymmetry of verification and verifier's rule" (Jul 2025): https://www.jasonwei.net/blog/asymmetry-of-verification-and-verifiers-law
- Brynjolfsson, Li and Raymond, "Generative AI at Work," NBER Working Paper 31161 (2023); *Quarterly Journal of Economics* 140(2), 2025: https://www.nber.org/papers/w31161
- Dell'Acqua et al., "Navigating the Jagged Technological Frontier: Field Experimental Evidence of the Effects of Artificial Intelligence on Knowledge Worker Productivity and Quality," *Organization Science* (online Mar 11, 2026): https://doi.org/10.1287/orsc.2025.21838
- METR, "Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity" (Jul 10, 2025): https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/
- METR, "We are Changing our Developer Productivity Experiment Design" (Feb 24, 2026): https://metr.org/blog/2026-02-24-uplift-update/
- Juan Pablo Bottaro and Karthik Ramgopal (LinkedIn), "Musings on building a Generative AI product" (Apr 25, 2024): https://www.linkedin.com/blog/engineering/generative-ai/musings-on-building-a-generative-ai-product
- Klarna, "Klarna AI assistant handles two-thirds of customer service chats in its first month" (Feb 27, 2024): https://www.klarna.com/international/press/klarna-ai-assistant-handles-two-thirds-of-customer-service-chats-in-its-first-month/
- Entrepreneur, "Klarna Is Hiring Customer Service Agents After AI Couldn't Cut It on Calls" (May 2025; reports the Bloomberg interview) (secondary): https://www.entrepreneur.com/business-news/klarna-ceo-reverses-course-by-hiring-more-humans-not-ai/491396
- MIT NANDA, "The GenAI Divide: State of AI in Business 2025" (Jul 2025, preliminary findings), PDF copy: https://cloudelligent.com/wp-content/uploads/2026/02/v0.1_State_of_AI_in_Business_2025_Report.pdf
- Epoch AI, "LLM inference prices have fallen rapidly but unequally across tasks" (Mar 12, 2025): https://epoch.ai/data-insights/llm-inference-price-trends
- swyx, "The Tiny Teams Playbook," Latent Space (Jul 15, 2025): https://www.latent.space/p/tiny
- AI Engineer World's Fair 2026 schedule and tracks (Jun 29 – Jul 2, 2026): https://ai.engineer/wf/llms.md
- swyx, "The Rise of the AI Engineer," Latent Space (Jun 30, 2023): https://www.latent.space/p/ai-engineer
- Rich Sutton, "The Bitter Lesson" (Mar 13, 2019): http://www.incompleteideas.net/IncIdeas/BitterLesson.html
