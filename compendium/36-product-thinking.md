# 36. AI Product Thinking

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This is Part 9, and it applies to every era, from a single prompt ([§05](05-api-and-prompting.md)) to a fleet of unattended loops ([§21](21-loop-engineering.md)). [§35](35-ai-ux.md) showed how to design the interface: streaming, approval steps, feedback capture. A well-designed AI product can still be the wrong product. It can target the wrong task or take the wrong amount of autonomy. Its cost can grow faster than its value, or it can depend on a capability that the next model gives away for free. This section is about choosing what to build. Four principles drive it: output is probabilistic, so value is a rate (P4); verification is the bottleneck, so the cost of checking decides where AI pays (P8); every token costs money (P10); and models keep improving, so some products should wait (P12).

## Why this exists

Traditional product thinking assumes the feature works. If a button computes a total, it computes it every time, and the only question is whether people want it. An LLM feature has no yes-or-no answer to "does it work?" (P4). It works at some rate, on some distribution of inputs, at some cost per attempt, and its failures land on someone. So the product question splits into three:

1. **Is the value of a correct output larger than the total cost?** That means the cost of producing it, plus checking it, plus cleaning up the failures that get through.
2. **Will that still hold in production?** That means real volume, real users, and the inputs they actually send, not the ones chosen for the demo.
3. **Will it still hold after the next model release?** Or will the model vendor, or a competitor using the same API, ship it for free?

Demos make all three look answered. A demo is one sample (P4), drawn from the easy part of the input distribution, with an expert watching who quietly fixes small errors. That is why the most common failure in AI products is not technical. It is building something that works in the demo and doesn't pay in production. The data-engineering equivalent is the beautiful dashboard nobody opens after launch week. This section gives you the tools to ask the three questions before you build.

## How it works (under the hood)

### Where probabilistic output is acceptable (P4)

Start from the failure, not the feature. An AI feature is worth building where an occasional wrong output is acceptable *given how it will be caught*. Three properties decide that.

**1. Verification is cheaper than generation (P8).** Jason Wei calls this the **asymmetry of verification**: "some tasks are much easier to verify than to solve." A sudoku is slow to solve and instant to check. Code with good tests is quick to check. A novel legal argument may take as long to verify as to write. The product consequence is direct. If a reviewer needs 1 minute to check what took 20 minutes to write, AI drafting can save up to 19 minutes per task, even if some drafts get thrown away. If checking takes as long as doing, AI saves nothing, because a careful person has to redo the work before they can trust it.

Anthropic's "Building effective agents" (Dec 2024) picked out two especially promising agent applications for this reason. In customer support, "success can be clearly measured through user-defined resolutions". In coding, "code solutions are verifiable through automated tests". Wei adds a corollary he calls the verifier's rule: "the ease of training AI to solve a task is proportional to how verifiable the task is." That matters for build-vs-wait below, because tasks that are easy to verify are also the ones models get better at fastest.

**2. Tolerance for errors, and the cost of each kind.** Errors don't all cost the same. Ask four questions about each type of failure:

- *Visible or silent?* A wrong autocomplete is visible: the user sees it and ignores it. A wrong number in a contract summary is silent.
- *Reversible or irreversible?* A drafted email is reversible until someone sends it. A refund, a deleted record or a trade is not.
- *Which direction is worse?* A spam filter's false positive hides a real email, and its false negative shows a spam. In fraud screening, missing fraud is costly, while flagging a good transaction costs a support call. You tune the threshold to the asymmetry, so you need the price of each direction.
- *Who absorbs it?* An internal analyst who knows the tool is fallible, or a customer who takes the answer as your company's word.

Data engineers know error budgets from SLOs. The same idea works here. Decide the acceptable failure rate for each error type before you build, and design the product so that failures land on the cheap side.

**3. "The human in the loop is the product."** Many successful AI products are not automation at all. Code completion, a draft reply for a support agent, a first-pass SQL query for an analyst: the AI proposes, a skilled person accepts, edits or rejects, and what the product sells is *speed for that person*. The human isn't a crutch to remove once the model gets good enough. The review step is the design, and it is what makes a 70%-accurate model useful, because the person catches the other 30%. It also produces labels. Every accept, edit and reject is a free judgment about quality that feeds your evals and datasets ([§28](28-data-flywheels.md)).

The evidence supports augmentation, with a warning attached:

- **Gains are real and uneven.** In a study of 5,179 customer-support agents, an AI assistant raised issues resolved per hour by 14% on average and by 34% for novice and low-skilled workers, with minimal impact on the most experienced (Brynjolfsson, Li and Raymond).
- **Gains reverse outside the model's competence.** In a preregistered experiment with 758 BCG consultants, GPT-4 users on tasks inside the model's capability frontier completed 12.2% more tasks, worked 25.1% faster, and produced higher-quality work. On a task chosen to lie outside that frontier, the AI groups were correct 60% and 70.6% of the time, against 84.5% without AI (Dell'Acqua et al., *Organization Science*, 2026). The authors call the uneven boundary of AI competence the **jagged frontier**.

Human-in-the-loop only works if the human actually checks, and people stop checking a tool that is usually right. Design for that: show sources, flag low-confidence parts, and make each check fast ([§35](35-ai-ux.md)).

### Picking use cases: value × feasibility × risk

Chip Huyen's *AI Engineering* (2025) starts this planning in chapter 1, under use case evaluation, setting expectations, milestone planning and maintenance. A practical version scores each candidate on four dimensions:

| Dimension | Question | How to measure it honestly |
|---|---|---|
| Value | What is a correct output worth? | Volume × time or money per task, from current logs rather than estimates |
| Feasibility | Can a model do it with the data you can supply? | A pilot eval of 50–100 real inputs ([§26](26-evals.md)), not a demo |
| Risk | What does an uncaught error cost? | Error types × cost per error × who absorbs it |
| Verification cost | How long does checking take compared with doing? | Time a reviewer on real outputs |

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

**Automate vs augment.** Automate when errors are cheap, the check is computational (a schema, a totals check, tests), and volume makes human review the bottleneck. Augment when the work needs judgment, when errors are costly or silent, or when only a person can do the check. Most products start as augmentation and move toward automation one task at a time, as evals show the success rate is high enough and the remaining failures are cheap. That is P7 applied to a product: you turn the autonomy dial up with evidence.

**Start narrow.** Pick one workflow, one user group and one measurable outcome. Narrow scope isn't timidity. It is what makes the system measurable. A narrow task has an input distribution you can sample for evals (P4), a short list of failure types you can name, and tools you can scope to least privilege (P9). "An assistant for the whole company" has none of these.

The scoring function below encodes the grid. The weights are a judgment call; the structure is the point. Verification cost gates everything, because a task that takes as long to check as to do has no leverage (P8).

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

Invoice extraction comes out on top and fully automated, because a schema and an arithmetic check catch most errors for free. Support drafts and SQL drafts rank next as augmentation. The legal memo scores zero despite high value, because checking it means redoing it.

### Build, buy, or wait (P12)

There are three options, not two.

**Wait.** If the gap is model capability (the model can't reliably read your handwritten forms, or can't hold a 40-step task together), the cheapest move may be to build the eval and nothing else. Models improve every few months, and scaffolding written to compensate for a weak model is exactly the kind that gets deleted (P12). The compendium has examples. Reasoning models absorbed the step-by-step prompt scaffolds of 2023 ([§04](04-reasoning-models.md)). Anthropic dropped context resets once Opus 4.5 stopped showing "context anxiety" ([§16](16-context-engineering.md)). Wei's verifier's rule adds a prediction: labs can train on tasks that are easy to verify, so those tend to improve fastest. A maintained eval tells you the day a model crosses your bar. Waiting isn't idling. You build what survives model changes (the eval, data access, workflow integration) and skip the workaround.

**Buy.** Vendor platforms are the right call when the capability is a commodity and your workflow is standard. That includes support automation, coding agents, enterprise chat assistants, and the AI functions inside your data platform. You get someone else's evals, updates and integrations. MIT NANDA's July 2025 report (labeled "preliminary findings", based on 52 interviews, 153 surveyed leaders and 300+ public initiatives) found that external partnerships reached deployment about 67% of the time, against about 33% for internal builds. The report itself warns that these outcomes are self-reported and may reflect organizational capability rather than the approach. Read it as a hint, not a law.

**Build.** Build when the workflow, the data or the integration is your differentiator. Build when you need control over the data path (privacy, residency), the evals or the unit cost, or when no vendor covers your edge cases. Building also means owning maintenance, which is why Huyen lists it as a planning step. Every model release means re-running evals, and possibly re-tuning prompts (P12).

**Wrapper risk.** A **wrapper** is a product that is mostly a prompt and a UI over someone else's model. Two things can kill it. The model vendor can ship the same feature natively, and vendors keep moving up the stack into document chat, research agents, memory and coding. And anyone with the same API can copy it quickly. Defensibility comes from what the API doesn't give: deep workflow integration, proprietary data and feedback loops, distribution, trust, and evals specific to your domain. A useful test: if the next model were twice as good and half the price, would your product get better or become unnecessary? Build the products that ride model improvements, so that P12 works in your favor.

### Measuring value

Five families of metrics matter, and each one can mislead on its own:

| Metric | What it measures | How it misleads | Pair it with |
|---|---|---|---|
| Task success | Share of tasks completed correctly | Graded on easy inputs, or by a lenient judge | Evals on sampled production inputs; graders checked against human labels ([§26](26-evals.md)) |
| Time saved | Minutes saved per task | Self-reports overstate it | Measured time, including review and rework |
| Deflection | Share of contacts that never reach a human | Users who gave up count as "deflected" | Repeat-contact rate, resolution, satisfaction |
| Quality | Accuracy, completeness, tone | Fluent output looks correct (P1) | Error-type audits; edit distance on accepted drafts |
| Adoption and retention | Who uses it, and who keeps using it | Novelty spikes in week one | Week-4 and week-8 retention by cohort; usage per active user |

**Perceived savings aren't measured savings.** In METR's randomized trial (Jul 2025), experienced open-source developers expected AI tools to speed them up by 24%. Afterwards they believed they had been sped up by 20%. In fact they took 19% longer. METR's Feb 2026 follow-up says developers are probably faster with late-2025 tools. But because many developers now refuse to work without AI, selection effects made its new data "only very weak evidence" of the size of the gain. Both halves are the lesson: self-reports are unreliable, and measuring productivity well is hard. Measure time with logs, not surveys.

**Deflection isn't resolution.** In Feb 2024 Klarna announced that its assistant had handled two-thirds of its customer-service chats in its first month, "the equivalent work of 700 full-time agents", with satisfaction on par with human agents and a 25% drop in repeat inquiries. In May 2025 its CEO told Bloomberg the company was hiring human agents again, so customers could always reach a person, and acknowledged that the cost-focused approach had produced lower quality (secondary reports, **⚠ verify**). The launch release did track repeat inquiries and satisfaction. The lesson is that a deflection headline doesn't settle the value question, so keep tracking quality long after launch.

**Why demos mislead, and the pilot-to-production gap.** A demo uses inputs from the head of the distribution, runs once (P4), and has an expert silently correcting small errors. Production brings the long tail, real volume and no expert. LinkedIn's team (Apr 2024) "achieved 80% of the basic experience we were aiming to provide within the first month and then spent an additional four months attempting to surpass 95%." The last 20% is where hallucinations, edge cases, latency and cost live. At industry scale, the NANDA report's headline was that "95% of organizations are getting zero return" from generative AI. That figure comes from a small sample with a loose definition of success, so don't quote it as precise. Its diagnosis is more useful than its number: "Most GenAI systems do not retain feedback, adapt to context, or improve over time." Systems that learn from their own usage ([§28](28-data-flywheels.md)) are the ones that cross the gap.

The ROI model below makes those costs explicit. It counts review time and rework, errors that escape review, low adoption and fixed costs, which are the things a demo leaves out:

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

The base case nets about $30K a month. Each variant changes one input and turns the result negative. With a 6-minute review, the check eats most of the time saved. At 10% adoption, the fixed costs win. At $400 per escaped error, the errors cost twice the value. Token cost is the smallest line in every scenario, which is common for augmentation products. The people and the errors usually dominate.

### Unit economics and pricing

Traditional software has close to zero marginal cost per user. AI products don't. Every task burns tokens (P10), and your heaviest users can cost many times what light users do. Three numbers decide whether the product is a business:

- **Cost per successful task, not per call.** If an attempt costs $0.08 and succeeds 80% of the time, then with retries each success costs $0.10, plus the review time. Agents make this number volatile, because the same task can take 5 turns or 50 (P7). Budget for the tail, not the mean.
- **Value per successful task,** taken from the ROI model.
- **Margin at scale,** after caching, routing and batching ([§30](30-cost-latency-reliability.md)). The price of reaching a *fixed* level of capability has fallen fast: Epoch AI (Mar 2025) measured declines of 9× to 900× per year, depending on the benchmark milestone. But products tend to move to bigger models and more thinking tokens as they grow, so don't assume the bill will shrink.

Pricing follows from where the cost and the value sit:

| Pricing model | Works when | Risk |
|---|---|---|
| Per seat | Cost per user is predictable and modest | Heavy users erase the margin |
| Usage-based (per token, task or credit) | Cost scales with use | Customers can't predict the bill, so they ration use |
| Outcome-based (per resolution, per accepted change) | Success is clearly measurable | You absorb the cost of failures, and disputes arise over what counts |

Outcome pricing is the strongest signal of confidence. Anthropic noted in Dec 2024 that several companies selling support agents use "usage-based pricing models that charge only for successful resolutions." It only works when success can be measured, which brings you back to verification (P8).

### The org side

**Forward-deployed engineering.** A **forward-deployed engineer** is embedded with a customer and builds the last mile: connecting data, writing tools, tuning prompts on the customer's real inputs, and setting up evals. Palantir popularized the role in the 2000s, and AI labs and startups revived it because the pilot-to-production gap is mostly integration and evaluation work that can't be done from outside (secondary, **⚠ verify** origin details). Forward Deployed Engineering was a track at the AI Engineer World's Fair on Jun 30, 2026. [§38](38-disciplines-map.md) calls it "a role, not a technique," which is right. It is where product thinking happens on site.

**Tiny teams.** swyx (Latent Space, Jul 2025) defined **Tiny Teams** aspirationally as "teams with more $m in ARR than employees." He surveyed seven such teams at the 2025 World's Fair, about 100 people and $200M in ARR between them. The mechanism is that coding agents and AI tools raise output per engineer, so a small group of senior generalists can ship what used to take a department. Be careful with the inference, though. The teams in that survey are survivors, and their figures are self-reported.

**AI engineer vs ML engineer.** [§01](01-first-principles.md) draws the line: ML engineers build models, while AI engineers build around a model they didn't train. Huyen's chapter 1 has a section on the same distinction. For staffing, an AI product team needs product-minded engineers who write evals and read traces more than it needs model trainers. Bring in ML engineers when you fine-tune, distill or self-host ([§29](29-adapting-models.md), [§31](31-open-weights-self-hosting.md)), or when the LLM feature sits next to a classical model you own, such as ranking or forecasting.

**Change management.** The NANDA report also found that general chat tools are widely adopted for individual work, while tools for specific workflows stall. Value comes from changing the workflow, not from adding a chat box. In practice that means:

- training people on where the tool can be trusted (the jagged frontier)
- adjusting incentives, such as who gets credit for AI-assisted work
- redesigning the process around the review step
- naming owners who measure adoption

People who don't trust a tool quietly route around it. Your adoption metric will show that before your ROI does.

### Data as moat

"Our data is our moat" is often wrong in the sense people mean. Frontier models were pretrained on much of the public web, so generic text in your warehouse rarely gives you a capability a competitor can't get. What does compound is narrower ([§28](28-data-flywheels.md)):

- **Outcome-labeled traces:** inputs, outputs, and what happened next (accepted, edited, escalated, refunded). Only your product sees these.
- **Your eval set:** curated failure cases from your domain. It survives every model change (P12), which makes it the most durable data asset you have.
- **Human corrections:** edits and rejections that become training data for fine-tuning or prompt optimization ([§29](29-adapting-models.md)).

The flywheel runs usage → traces → labeled failures → better evals, prompts or models → better product → more usage. It is a moat only if it actually spins. If you don't log, label and feed back, you just have data. P12 also cuts against fine-tuned models: a better base model can leapfrog your tuned one, while your eval set lets you adopt the better model the same week.

### Failure patterns

- **A solution looking for a problem.** "We need an AI strategy" produces a chatbot nobody asked for. Start from a task with volume, a cost, and an owner who wants it done faster.
- **An eval-less launch.** Without a measured success rate (P4), you can't tell whether a prompt change helped, whether a new model regressed, or whether the product works at all. Build 50–100 graded examples before launch ([§26](26-evals.md)).
- **Unbounded agent scope.** "It can do anything" means it can't be evaluated, secured or priced. Errors compound (P8), each tool widens the attack surface (P9), and cost has no ceiling (P10). Narrow the task, cap turns and spend, and widen scope only with evidence.
- **Ignoring cost at scale.** A pilot with 20 friendly users costs pennies. 50,000 users with long contexts and agents in loops cost a fortune. Model the cost per successful task at the target volume before you commit ([§30](30-cost-latency-reliability.md)).
- **Measuring the demo.** This means reporting accuracy on inputs you chose, or time saved from a survey. Sample production inputs, and measure.

## Comparison

**Automate, augment, wait, or skip**

| Mode | Choose when | What the human does | What you measure | Example |
|---|---|---|---|---|
| Automate | Errors are cheap and reversible; checks are computational; volume is high | Samples outputs, handles escalations | Error rate per type, escalation rate, cost per success | Invoice field extraction with schema and totals checks |
| Augment (review) | Verification is much cheaper than generation; errors are moderate | Accepts, edits or rejects each output | Acceptance rate, edit distance, time per task | Support reply drafts, SQL drafts for analysts |
| Augment (approve) | Errors are costly, silent or irreversible | Signs off on every output before it takes effect | Approval rate, override reasons, errors caught | Contract risk flags, refunds above a threshold |
| Wait | The value is real, but the model fails your pilot eval | Keeps the eval current | Pass rate on each new model release | Messy handwriting, very long autonomous tasks |
| Skip | Checking costs as much as doing, or value is low | Does the work as before | Nothing to measure | Novel legal research memos |

**Build, buy, or wait**

| Option | Choose when | You own | Main risk | Under P12 |
|---|---|---|---|---|
| Buy | The capability is a commodity; your workflow is standard | Configuration, change management, vendor evals | Lock-in; a generic fit for your edge cases | The vendor absorbs model upgrades for you |
| Build | Workflow, data or integration is your edge; you need control of data, cost or evals | Everything, including maintenance and re-evaluation | Slow delivery; scaffolding that ages | Thin harnesses improve with models; heavy workarounds rot |
| Wait | The model can't do it yet, and the task is verifiable | The eval, data access, integration points | Arriving late if a competitor gets there first | Often the cheapest option: the next model may close the gap |

## What it didn't solve

Product thinking tells you which problem to solve and how to judge success. It doesn't tell you which mechanism to use once you have chosen: RAG or fine-tuning, a workflow or an agent, one model or a router. Every decision in this compendium is a tradeoff like that, argued in its own section. The next section collects them in one place and argues each one in both directions. → Next: [§37 Why X over Y](37-why-x-over-y.md)

## Check your understanding

**Q: Why is "verification is cheaper than generation" the first test for an AI use case?**

Because the human time saved is roughly the time to do the task minus the time to check the AI's output (P8). If checking takes a minute and doing takes twenty, AI drafting pays even when some drafts are discarded. If checking takes as long as doing, a careful person must redo the work to trust it, so the AI adds cost and saves nothing. Tasks with computational checks (tests, schemas, totals) are the best candidates. Tasks that only an expert can verify slowly are the worst.

**Q: What would happen if you launched a support agent and reported only its deflection rate?**

You would count every customer who gave up as a success. Deflection measures contacts that didn't reach a human, not problems solved, so a frustrating bot can raise it. Pair deflection with repeat-contact rate, resolution checks and satisfaction, and keep tracking them after launch, since novelty and cost pressure both distort early numbers. Klarna's case shows that a strong deflection headline doesn't settle whether quality held up.

**Q: Automate vs augment: when should a feature keep a human approving every output?**

When errors are costly, silent or irreversible, and no computational check can catch them: refunds, contract terms, medical or legal content. Approval makes the human the verifier at the point where mistakes can't be undone (P8). The cost is human time and the risk of rubber-stamping, so make each check fast and show the evidence. Move to automation step by step, as evals show high success rates and the remaining errors become cheap.

**Q: Why might "wait" be the best answer to a build-vs-buy question?**

Because scaffolding built to work around a weak model tends to be deleted when a better model arrives (P12). Months spent on elaborate workarounds can become worthless after one release. Verifiable tasks are also the ones labs improve fastest. Waiting means building the eval, data access and integration now, all of which survive model changes, and re-running the eval on each new model. It's the wrong answer when the window matters competitively and a narrower version works today.

**Q: Why do AI demos overstate value, and what closes the pilot-to-production gap?**

A demo is one sample (P4) on hand-picked inputs, with an expert silently fixing errors and nobody paying for review time or failures. Production adds the long tail of inputs, real volume, latency and cost limits. LinkedIn reached 80% quality in a month and spent four more months trying to pass 95%. The gap closes through evals on sampled production inputs, error analysis, and feedback loops that let the system improve from its own usage, not through a better demo.

**Q: Why is per-seat pricing risky for an agent product?**

Because cost per user is not fixed (P10). Agents take a variable number of turns, and heavy users can consume many times the tokens of light ones, so a flat seat price can turn negative on your best customers. Usage-based pricing tracks cost but makes bills unpredictable for buyers. Outcome-based pricing aligns value and price, but only when success is clearly measurable and you can afford to absorb failed attempts.

**Q: Is your company's data a moat for an AI product?**

Usually not in the form people mean. Generic documents add little that a frontier model or a competitor can't get. What compounds is data only your product produces: traces labeled with outcomes, human corrections, and an eval set of your domain's failure cases. That eval set is the most durable asset, because it survives model changes (P12) and lets you adopt better models quickly. A moat exists only if the flywheel actually turns usage into improvements.

## Takeaways

- An AI feature works at a rate (P4), so value means correct outputs minus the cost of checking and of the errors that escape.
- The best use cases are verifiable: checking is much cheaper than doing (P8).
- Price each error type by visibility, reversibility, direction and who absorbs it, and set an error budget.
- Augment first, automate with evidence, and start narrow enough to evaluate.
- Build, buy and wait are all options; build the eval in every case, because it survives model changes (P12).
- Measure task success, measured time, resolution, quality and retention, not demos, surveys or deflection alone.
- Unit economics are per successful task, and pricing should follow where cost and value sit.
- The durable moat is outcome-labeled traces and a domain eval set that keep the flywheel turning.

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
