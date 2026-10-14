# 34. Governance and Regulation

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

Governance applies to every era in this compendium, from a single prompted call to a fleet of agents. P4 (output is sampled) and P8 (errors compound, so verification is the bottleneck) drive it. [§33](33-agent-identity.md) gave agents identities and scoped permissions, which are obligations you owe to the users whose data and accounts an agent touches. Regulators add obligations to society: to people who never chose your system but are screened, scored or shown content by it. **This section is not legal advice.** It explains the mechanisms so you can build the right controls and talk usefully with counsel, and every date in it is as of October 2026.

## Why this exists

Most software regulation assumes you can specify behavior and test against the specification. A probabilistic system breaks that assumption. The same input can produce different outputs (P4), and the space of possible outputs can't be enumerated and certified. The stakes also depend on where you put the model: the same weights can draft marketing copy or rank job applicants. The European Commission names the core problem: "it is often not possible to find out why an AI system has made a decision or prediction and taken a particular action," so it "may become difficult to assess whether someone has been unfairly disadvantaged, such as in a hiring decision."

So regulators stopped trying to certify the artifact and started regulating the **process** around it. You must know what you deployed and why, assess the risk first, keep records that let you reconstruct decisions, put humans where errors are costly, tell people when they are dealing with AI, and report serious failures. That is P8 written as law. If silent errors are the dangerous ones, the regulator's lever is to make errors *observable and correctable*.

If you have lived through GDPR, the pattern is familiar. Catalogs, lineage and retention became mandatory once "we don't know where that data went" stopped being an acceptable answer. AI governance makes the same move one layer up, for "we don't know why the system said that."

## How it works (under the hood)

### The EU AI Act: regulate the use, scale the duty to the risk

The AI Act is Regulation (EU) 2024/1689. It entered into force on August 1, 2024, and its duties switch on in stages through 2028. Three design choices explain most of it.

**1. Duties attach to the intended purpose, not the technology.** A model in a spam filter is minimal-risk, and the same model screening CVs is high-risk. You classify the *use case*.

**2. Duties attach to roles.** A **provider** develops an AI system or general-purpose model, or has one developed, and puts it on the market under its own name (Art. 3(3)). A **deployer** uses an AI system under its authority (Art. 3(4)). If you sell a product built on Claude or GPT, you are the provider of an *AI system*, the vendor is the provider of a *general-purpose AI model*, and your customer is the deployer. Roles shift: under Art. 25 you become the provider of a high-risk system if you put your name on it, substantially modify it, or repurpose a non-high-risk system into a high-risk use.

**3. Reach is extraterritorial.** The Act covers third-country providers and deployers "where the output produced by the AI system is used in the Union" (Art. 2(1)(c)).

### The four risk tiers

```text
            ┌────────────────────┐
            │ PROHIBITED (Art 5) │  banned practices: don't build
          ┌─┴────────────────────┴─┐
          │   HIGH-RISK (Art 6)    │  Annex I products + Annex III use cases:
          │                        │  risk mgmt, data governance, logs, docs,
          │                        │  human oversight, accuracy, registration
        ┌─┴────────────────────────┴─┐
        │ TRANSPARENCY (Art 50)      │  chatbots disclose, generated content
        │                            │  is marked, deepfakes are labeled
      ┌─┴────────────────────────────┴─┐
      │ MINIMAL (everything else)      │  no new duties beyond AI literacy
      └────────────────────────────────┘     ("the vast majority" of systems)
```

**Prohibited (Art. 5).** The Commission lists nine practices:

- harmful manipulation and deception
- exploitation of vulnerabilities
- social scoring
- predicting an individual's criminal offences from profiling
- untargeted face scraping to build recognition databases
- emotion recognition at work and in education
- biometric categorisation to infer protected traits
- real-time remote biometric identification for policing in public spaces
- since the 2026 amendments, systems that generate non-consensual intimate imagery or child sexual abuse material

The first eight have applied since February 2, 2025, and the ninth applies from December 2, 2026.

**High-risk (Art. 6).** There are two routes in. **Annex I** covers AI that is a safety component of a product already under EU product-safety law, such as machinery, toys, lifts or medical devices; these are the "embedded" systems. **Annex III** covers standalone use cases: biometrics, critical infrastructure, education, employment (CV sorting, promotion, worker monitoring), essential services (credit scoring, life and health insurance pricing, public benefits), law enforcement, migration, and justice and democratic processes. Art. 6(3) exempts Annex III systems that don't "materially influence the outcome of decision making", such as a narrow procedural task. The exemption never applies to profiling, and a provider who relies on it must document the assessment (Art. 6(4)).

What high-risk providers must do:

- **Requirements:** risk management, data governance, technical documentation, automatic logging, information for deployers, human oversight, and accuracy, robustness and cybersecurity (Arts. 9–15)
- **Processes:** a quality management system, a conformity assessment, registration in an EU database, post-market monitoring and incident reporting

Deployers must use the system as instructed, assign competent human oversight, monitor it and keep its logs for at least six months (Art. 26). Public bodies, and deployers that use AI for credit scoring or insurance pricing, must also run a fundamental-rights impact assessment (Art. 27).

**Transparency (Art. 50).** These duties apply whether or not the system is high-risk:

- systems that talk to people must tell them they are dealing with an AI, "unless this is obvious"
- generated audio, image, video and text must be marked "in a machine-readable format and detectable as artificially generated"
- deployers must label deepfakes, and also AI-written text published to inform the public, unless a human reviewed it and someone holds editorial responsibility
- notices must be "clear and distinguishable", given at the latest at first interaction, and accessible

Article 50 has applied since **August 2, 2026**. Generative systems already on the market have until December 2, 2026 to meet the marking duty. A voluntary Code of Practice on Transparency of AI-generated Content backs it (about 190 signatories by late July 2026).

**Minimal.** These systems carry no new duties beyond AI literacy (Art. 4). The 2026 amendments softened that duty to "take measures to support" staff literacy.

### General-purpose AI models

A **general-purpose AI (GPAI) model** can competently perform a wide range of distinct tasks. The Commission's indicative test is training compute above 10²³ FLOP plus the ability to generate language, images or video. Since **August 2, 2025**, GPAI providers must keep technical documentation, inform downstream integrators of the model's capabilities and limits, maintain a copyright policy that honors text-and-data-mining opt-outs, and publish a training-content summary (Art. 53). A model is presumed to have *systemic risk* above 10²⁵ FLOP (Art. 51). Its provider must also evaluate the model "including conducting and documenting adversarial testing", mitigate systemic risks, report serious incidents and secure the model (Art. 55). The AI Office has been able to enforce these duties, with fines, since August 2, 2026.

The **GPAI Code of Practice** (published Jul 10, 2025) is the voluntary route to showing compliance. It has three chapters: Transparency, Copyright, and Safety and Security, the last only for systemic-risk models. Signatories as of Oct 2026 include Amazon, Anthropic, Google, IBM, Microsoft, Mistral AI and OpenAI.

**If you call a model through an API, you are usually not a GPAI provider.** Fine-tuning changes that only past the Commission's indicative criterion: a modification that uses more than **one third** of the original model's training compute. Even then, your obligations cover only the modification. LoRA ([§29](29-adapting-models.md)) is orders of magnitude below that line.

### The timeline, including the 2026 amendments

In November 2025 the Commission proposed a "Digital Omnibus" simplification package. Its AI-Act part, the **"Digital Omnibus on AI"** (or "AI Omnibus"), went through the legislature in 2026:

- **May 7:** political agreement
- **Jun 16:** Parliament adopted it
- **Jun 29:** the Council adopted it
- **Jul 24:** published in the Official Journal as **Regulation (EU) 2026/1744**
- **Jul 27:** entered into force

The headline change delays the high-risk rules, which were originally due in August 2026 (Annex III) and August 2027 (Annex I), so that they apply "when companies have the right support tools to facilitate implementation, such as standards."

| Date | What starts to apply |
|---|---|
| Aug 1, 2024 | Entry into force; no duties yet |
| Feb 2, 2025 | Prohibitions 1–8; AI literacy |
| Aug 2, 2025 | GPAI model obligations; governance bodies; penalty rules |
| Aug 2, 2026 | Most of the Act, including Art. 50 transparency; enforcement begins |
| Dec 2, 2026 | Prohibition 9 (NCII/CSAM); Art. 50(2) marking deadline for systems already on the market |
| Aug 2, 2027 | GPAI models placed before Aug 2, 2025 must comply |
| **Dec 2, 2027** | **High-risk rules for Annex III (standalone) systems** |
| **Aug 2, 2028** | **High-risk rules for Annex I (embedded in regulated products) systems** |

The Omnibus also:

- extended SME simplifications to small mid-caps
- slimmed, but kept, high-risk registration
- widened bias-detection use of sensitive data, with safeguards
- centralized oversight of GPAI-based systems in the AI Office

A separate Digital Omnibus amending the GDPR, NIS2 and the Data Act was still in the legislative process in July 2026 (secondary source), and I couldn't confirm its October status **(⚠ verify)**. Fines reach €35M or 7% of worldwide turnover for prohibited practices and €15M or 3% for most other breaches (Art. 99).

### The US landscape (high level, as of Oct 2026)

There is no comprehensive federal AI statute. Policy runs through executive orders and existing law, such as the FTC Act's ban on deceptive practices, civil-rights law and sector regulators.

- **Federal executive orders.**
  - Jan 2025: EO 14148 rescinded the 2023 safety order (EO 14110), and EO 14179 set a deregulatory direction.
  - Dec 11, 2025: EO 14365, "Ensuring a National Policy Framework for Artificial Intelligence", created a DOJ **AI Litigation Task Force** to challenge state AI laws. It also ordered Commerce to list "onerous" state laws within 90 days and asked for legislation to preempt them, with carve-outs for child safety and state procurement. I couldn't confirm whether the Commerce list has been published **(⚠ verify)**.
  - Sep 29, 2026: EO 14434 directs agencies to say "Super Intelligence" ("SI") instead of "AI" in executive-branch documents, so expect the new term in federal texts.
- **Colorado.** SB 24-205 (2024), the first broad state AI act, was delayed to June 30, 2026. In May 2026 SB 26-189 replaced it with a narrower automated-decision law **effective January 1, 2027**. The new law requires notice, an adverse-action process with human review, and records kept for three years, and only the attorney general can enforce it **(⚠ verify: law-firm summaries)**.
- **California.** SB 53, the Transparency in Frontier AI Act, took effect Jan 1, 2026. It requires large frontier developers to publish safety frameworks and report critical safety incidents. SB 243 requires companion chatbots to disclose that they are AI and to follow self-harm protocols **(⚠ verify both)**.

The practical consequence: don't track regimes feature by feature. Build one set of controls that meets the strictest common requirements (disclosure, logging, human review of consequential decisions, documented risk assessment), and map each law onto it.

### Frameworks: NIST AI RMF and ISO/IEC 42001

Laws say *what* must be true. Frameworks give you a process to *make* it true, and customers ask for them by name.

**NIST AI RMF 1.0** (Jan 26, 2023) is voluntary. It is organized as **Govern** (policies and accountability, cross-cutting), **Map** (context, who is affected), **Measure** (assess and track; this is where evals live) and **Manage** (prioritize, mitigate, respond). Its **Generative AI Profile** (NIST AI 600-1, Jul 26, 2024) lists twelve risks, among them confabulation, data privacy, information security, harmful bias, value-chain integration and "human-AI configuration" (automation bias and anthropomorphizing; see [§35](35-ai-ux.md)). As of Oct 2026 NIST says the RMF "is being revised as part of the White House AI Action Plan."

**ISO/IEC 42001:2023** is a certifiable **AI management system** standard. It has the same shape as ISO 27001: a policy, roles, risk and impact assessments, controls, internal audit and continual improvement, checked by a third-party auditor. NIST gives you vocabulary and practices. ISO 42001 gives you a certificate that you run the process. Neither creates AI Act conformity by itself; the Act's presumption of conformity comes from harmonised European standards, and waiting for those standards is part of why the high-risk dates moved.

### What this means for engineers

**1. Logging and record-keeping.** High-risk systems must "technically allow for the automatic recording of events (logs) over the lifetime of the system" (Art. 12), kept at least six months (Arts. 19, 26). The log must reconstruct a decision months later. That differs from data pipelines in one key way. A SQL result can be recomputed from inputs and code. A model output can't (P4), and the model may have been retired by then. So **log the output itself**, plus everything that shaped it. Keep these **audit records** separate from **observability traces** ([§27](27-observability.md)). Traces are sampled and short-lived. Audit records are complete, append-only and retention-governed, and they join to traces by ID.

```python
import hashlib, json, uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True)
class AuditRecord:
    use_case_id: str            # key into the AI inventory (your catalog)
    risk_tier: str              # from classify(); drives retention and review rules
    actor: str                  # "user:4411", or "agent:triage on-behalf-of user:4411" (§33)
    model_id: str               # the exact model string, e.g. "claude-sonnet-5-5"
    prompt_version: str         # git SHA or registry version of the system prompt/template
    config_hash: str            # hash of tool definitions, effort, guardrail settings
    input_ref: str              # pointer + content hash; keep raw PII out of the log line
    output_ref: str             # store the OUTPUT: unlike a SQL result, it can't be recomputed (P4)
    sources: list = field(default_factory=list)     # lineage: [{"doc_id": ..., "version": ...}]
    tool_calls: list = field(default_factory=list)  # [{"name": ..., "args_hash": ..., "ok": ...}]
    ai_disclosed: bool = True   # was the "you are using AI" notice shown? (Art. 50)
    human_review: dict | None = None   # {"reviewer": ..., "decision": "approve|override", "at": ...}
    trace_id: str = ""          # joins this record to the OTel trace (§27)
    retain_days: int = 183      # high-risk logs: at least six months; legal sets the real value
    prev_hash: str = ""         # hash chain: editing any record breaks every later hash
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    at: str = field(default_factory=now)

    def sealed(self) -> dict:   # what you append to WORM storage (object lock, append-only table)
        body = asdict(self)
        body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        return body

rec = AuditRecord("cv-screener", "high", "user:4411", "claude-sonnet-5-5", "prompt@9f2c1e",
                  "cfg@77ab", "s3://audit/in/7f3a.json#sha256=ab12", "s3://audit/out/7f3a.json#sha256=cd34",
                  sources=[{"doc_id": "job-req-118", "version": 3}],
                  human_review={"reviewer": "user:208", "decision": "override", "at": now()},
                  trace_id="4bf92f3577b34da6", prev_hash="e3b0c442")
print(json.dumps(rec.sealed())[:160], "...")
```

The record holds references and hashes, not raw prompts full of personal data. The payloads sit in a separately access-controlled store with their own retention, which reconciles "keep logs" with GDPR's data minimization. The hash chain makes later edits detectable, which matters once the log is evidence.

**2. Human oversight design.** Art. 14 is unusually concrete. Overseers must be able to:

- understand the system's limits
- "remain aware of the possible tendency of automatically relying or over-relying on the output" (**automation bias**)
- interpret its output
- override or reverse it
- halt it "through a 'stop' button or a similar procedure"

In engineering terms:

- put approvals at the consequential step ([§11](11-agents.md), [§20](20-agent-runtime.md))
- show evidence, not only the verdict
- make override as easy as accept, and log both
- build the stop path
- **measure** oversight: a 99.8% approval rate at two seconds per item is a rubber stamp, and your audit log will show it

**3. Transparency and disclosure.** Disclose AI at first contact in the UI, not in the terms of service. Mark generated media machine-readably, for example with C2PA Content Credentials or watermarks. For high-risk systems, ship deployers **instructions for use**: intended purpose, measured accuracy, known limits, oversight measures (Art. 13).

**4. Data governance and provenance.** Art. 10 requires data that is relevant, representative and examined for bias. If you don't train the model, provenance moves to what you control: the RAG corpus ([§09](09-rag.md)), eval sets, fine-tuning data, and the memories a system writes about users ([§17](17-memory.md)). Recording each retrieved chunk's source version in the audit record is lineage applied to context.

**5. Model and system documentation.** A **model card** (Mitchell et al., 2018) documents a model's intended use, evaluation across groups and limitations. A **datasheet** (Gebru et al., 2018) does the same for a dataset. A **system card**, the label frontier labs use for release documents, covers a deployed model plus its safeguards and red-teaming. Write a system card per use case: purpose, model versions, data sources, eval results, failure modes, oversight design and a change log. Generate as much of it as you can from config and eval output, the way dbt generates docs. Hand-written documents drift from the system they describe.

**6. Incident reporting.** Art. 73 sets three deadlines for high-risk providers reporting a **serious incident**:

- "immediately" after establishing a causal link, or its likelihood, and within **15 days** of becoming aware at most
- **2 days** for widespread infringement or serious disruption of critical infrastructure
- **10 days** if a person died

Providers must not alter the system in ways that affect the investigation before informing authorities. So **preserve evidence before you hotfix**: pin the model, prompt and config, and snapshot the audit records. This is the AI version of GDPR's 72-hour breach clock, and only good logs make it feasible.

**7. Evals as compliance evidence.** The Act keeps asking for testing:

- testing against defined metrics as part of risk management (Art. 9)
- declared accuracy levels (Art. 15)
- adversarial testing for systemic-risk models (Art. 55)
- post-market monitoring (Art. 72)

Your eval suite ([§26](26-evals.md)), red-team results ([§32](32-security-guardrails.md)) and online monitors are that evidence, provided they are versioned, tied to releases and archived. A notebook run once is not evidence. A release gate that stores its report is.

### Internal governance

Your organization needs three things before the law tells it to.

- **An AI inventory** lists every use case with its owner, purpose, models, data, tier and status. Without it you can't answer a regulator, a customer questionnaire or your own security team.
- **Model approval** keeps an approved-models list. Each entry records vendor terms, data retention, processing region, Code of Practice status and eval results *on your tasks*. Pin versions, and re-evaluate on every swap, because you can't diff a model's behavior (P4) and vendors retire models (P12). Prompt edits go through the same review and eval gate.
- **AI use policies** state what employees may paste into which tools, mapped to your data classification. Pair each with an approved tool that beats the shadow alternative.

**Risk tiering** decides how much process each use case gets. A rules table is readable by legal, testable by engineering and versioned like code:

```python
from dataclasses import dataclass, field

@dataclass
class UseCase:
    name: str
    area: str                          # business area from intake: "employment", "support", ...
    shapes_decisions: bool             # output materially influences a decision about a person
    profiles_people: bool = False
    faces_public: bool = False         # people interact with it directly
    publishes_media: bool = False      # generated image/audio/video/text shown to others
    practices: set = field(default_factory=set)   # intake tags, e.g. {"social_scoring"}
PROHIBITED = {"social_scoring", "workplace_emotion_recognition", "face_db_scraping", "manipulation"}
ANNEX_III = {"biometrics", "critical_infrastructure", "education", "employment", "credit_scoring",
             "life_health_insurance", "public_benefits", "law_enforcement", "migration", "justice"}
annex = lambda u: u.area in ANNEX_III
consequential = lambda u: u.shapes_decisions or u.profiles_people
# The rules table, most severe first: (predicate, tier, reason). Several rules can match.
RULES = [
    (lambda u: bool(u.practices & PROHIBITED), "prohibited", "matches an Art. 5 practice"),
    (lambda u: annex(u) and consequential(u), "high", "Annex III area, shapes decisions"),
    (lambda u: annex(u) and not consequential(u), "review", "Annex III area: document Art. 6(3)"),
    (lambda u: u.faces_public or u.publishes_media, "limited", "Art. 50 disclosure or marking"),
    (lambda u: True, "minimal", "every use case goes in the inventory"),
]
CONTROLS = {  # YOUR internal policy per tier, not a copy of the law
    "prohibited": ["block at intake"],
    "high": ["governance sign-off", "system card + risk file", "human review UI",
             "audit log kept >= 6 months", "eval gate per release", "incident runbook"],
    "review": ["legal sign-off on the exemption", "audit log"],
    "limited": ["AI disclosure at first interaction", "machine-readable output marking"],
    "minimal": ["register in AI inventory", "standard logging"],
}
def classify(u: UseCase) -> dict:
    hits = [(tier, why) for rule, tier, why in RULES if rule(u)]
    tier = hits[0][0]                  # first hit = most severe tier; it gates approval
    hits = hits[:1] if tier == "prohibited" else hits    # a banned use case simply doesn't ship
    controls = sorted({c for t, _ in hits for c in CONTROLS[t]})   # obligations stack
    return {"tier": tier, "reasons": [why for _, why in hits], "controls": controls}
print(classify(UseCase("cv-screener", "employment", shapes_decisions=True, faces_public=True)))
print(classify(UseCase("sql-helper", "analytics", shapes_decisions=False)))
```

Two details matter. **Obligations stack**: a public-facing CV screener is high-risk *and* has transparency duties, so the classifier returns the union of controls. And the table encodes *your* policy. The "review" tier, which routes claimed Art. 6(3) exemptions to legal, is a company choice, not a tier the Act defines. Keep the table in the repo with tests for known use cases, and have legal review changes to it.

### The data-governance analogy

| Data governance | AI governance | Where it breaks |
|---|---|---|
| Data catalog | AI inventory, model registry | A model's behavior isn't described by a schema |
| Classification (PII, confidential) | Use-case risk tier | Tier depends on *purpose*, not on the data's content |
| Lineage | Provenance: model, prompt version, sources, tools per output | Lineage can't recompute the output (P4), so store it |
| Retention policies | ≥ 6-month logs vs minimization | Both apply; use references, redaction, tiered stores |
| Access control | Tool permissions, agent identity ([§33](33-agent-identity.md)) | Agents act, so you authorize actions, not just reads |
| dbt tests | Evals and monitors | Pass *rates* with judgment-call thresholds |
| Breach notification (72 h) | Serious-incident reporting (2–15 days) | Causality is harder to prove for statistical failures |

### Failure modes

- **Compliance theater.** Documents describe the system at approval time, three model versions ago. Generate documentation from the running config.
- **Rubber-stamp oversight.** A human is "in the loop" and approves everything in seconds. Measure overrides and redesign the review ([§35](35-ai-ux.md)).
- **Mis-tiering.** "It's just a chatbot," but it ranks applicants. Tier by what the output *influences*, not by what the UI looks like.
- **Role blindness.** Rebranding a vendor's high-risk system, or repurposing an assistant for hiring, makes you its provider (Art. 25).
- **Unanswerable logs.** Either nothing is reconstructable, or everything is logged raw, which creates a privacy liability bigger than the AI risk.
- **Over-governing the trivial.** A review board for internal SQL autocomplete teaches teams to route around governance. Proportionality is in the law; put it in your policy too.

## Comparison

| | EU AI Act | NIST AI RMF + GenAI Profile | ISO/IEC 42001 | US state laws |
|---|---|---|---|---|
| Nature | Binding law with fines | Voluntary framework | Certifiable management system | Binding, narrow, changing |
| Scope | Use cases by tier; GPAI models | Any AI system | The organization's AI process | Consequential decisions, frontier models, chatbots |
| Asks for | Duties per role and tier | Govern, Map, Measure, Manage | Policy, roles, assessments, controls, audit | Notices, assessments, human review, reports |
| Evidence | Tech docs, logs, conformity assessment | Your risk records | Third-party certificate | Records on request |
| Matters when | Any output used in the EU | US public sector, shared vocabulary | Enterprise buyers want a certificate | Hiring, lending, frontier development |

| Obligation | Engineering mechanism | See |
|---|---|---|
| Record-keeping (Arts. 12, 19, 26) | Append-only audit records joined to traces | [§27](27-observability.md) |
| Human oversight (Art. 14) | Approval points, override path, stop button, oversight metrics | [§20](20-agent-runtime.md), [§35](35-ai-ux.md) |
| Transparency (Art. 50) | Disclosure component, output marking | [§35](35-ai-ux.md) |
| Data governance (Art. 10) | Source versioning, eval-set lineage, bias checks | [§09](09-rag.md), [§28](28-data-flywheels.md) |
| Accuracy, documentation (Arts. 11, 15) | Eval gates, red teaming, generated system cards | [§26](26-evals.md), [§32](32-security-guardrails.md) |
| Incident reporting (Art. 73) | Runbook, evidence snapshot, severity rubric | [§27](27-observability.md) |

## What it didn't solve

Compliance is a floor. A system can disclose that it is AI, log every decision, route each one past a reviewer and pass its conformity assessment, and still be one that people misread, over-trust or can't correct. A law can require that an overseer be *able* to override. It can't make the override the obvious move, or make the evidence quick enough to check that anyone checks it. Users still have to trust, understand and correct the system, and that is a design problem. → Next: [§35 AI UX and Generative UI](35-ai-ux.md)

## Check your understanding

**Q: Why does the EU AI Act attach most duties to use cases rather than to models?**

Risk comes from where an output lands, not from the weights: the same model is harmless filtering spam and consequential ranking applicants. Behavior is probabilistic and can't be certified in advance (P4), so the Act scales duties to the stakes of the intended purpose. The model layer gets lighter GPAI duties (documentation, copyright policy, and evaluations for systemic-risk models), because the model provider can't foresee every downstream use.

**Q: You sell a CV-screening assistant, built on a vendor's model API, to EU employers. What are you, and what applies when?**

You are the provider of a high-risk system (Annex III, employment), and each employer is a deployer. The vendor is the GPAI provider. If the assistant talks to candidates, Art. 50 disclosure has applied since Aug 2, 2026, and the high-risk requirements apply from Dec 2, 2027 under the 2026 amendments. Build the logging and oversight now, and confirm the details with counsel.

**Q: What would happen if your audit log stored the inputs and the model ID but not the outputs?**

You couldn't reconstruct what the system actually said. A model call is sampled (P4), so rerunning the inputs can give a different answer, and the model may be retired by the time someone asks. Lineage tells you *how* an output was produced, but only the stored output tells you *what* it was, so store it (or a hashed reference to it).

**Q: Reviewers approve 99.8% of recommendations at about two seconds each. Do you have human oversight?**

On paper, yes. In substance, probably not. Art. 14 expects overseers who can interpret outputs, resist automation bias and override, and that approval rate and speed suggest nobody is evaluating anything. Seed known-bad cases to test whether reviewers catch them, show evidence instead of verdicts, and cut review volume so that each review gets attention.

**Q: NIST AI RMF vs ISO/IEC 42001: what does each give you?**

The NIST AI RMF is a voluntary vocabulary and practice guide (Govern, Map, Measure, Manage), and its Generative AI Profile lists twelve risks to work through. ISO/IEC 42001 is a management-system standard that a third party certifies, which proves you *run* an AI risk process. Teams often use NIST to decide what to do and ISO 42001 to demonstrate that they do it. Neither alone satisfies the AI Act.

**Q: When does fine-tuning a vendor model make you a GPAI model provider?**

Under the Commission's indicative criterion, when your modification uses more than one third of the original model's training compute, and even then your duties cover only the modification. Typical fine-tuning, especially LoRA, is far below that. You are much more likely to pick up obligations through the use case: a model fine-tuned for hiring makes the *system* high-risk, whatever the compute.

**Q: A team says, "high-risk dates moved to 2027, so governance can wait." What's wrong with that?**

Prohibitions, AI literacy and Art. 50 transparency already apply. The controls the high-risk rules require (inventory, tiering, reconstructable logs, eval gates, an incident runbook) take time to build and are good engineering anyway. Logging retrofitted in 2027 leaves you with no records of 2026.

## Takeaways

- This is not legal advice: learn the mechanisms, build the controls, and take dated specifics to counsel.
- The EU AI Act regulates purpose and role across four tiers (prohibited, high-risk, transparency, minimal). Obligations stack, and roles can shift.
- As of Oct 2026: GPAI duties since Aug 2025, Art. 50 since Aug 2026, high-risk Annex III from Dec 2, 2027 and Annex I from Aug 2, 2028.
- The US has no federal AI statute. Executive orders push preemption, and state laws keep changing (Colorado's replacement act starts Jan 1, 2027).
- Log outputs, not just inputs, because a sampled result can't be recomputed (P4). Keep audit records append-only and separate from traces.
- Measure human oversight, or it becomes a rubber stamp.
- Versioned evals, red-team results and monitors are your compliance evidence. Tier use cases with a reviewed rules table, and spend process in proportion.

## Sources

- Regulation (EU) 2024/1689 (AI Act), EUR-Lex: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689
- Regulation (EU) 2026/1744 (AI Omnibus), Official Journal L, Jul 24, 2026: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202601744
- European Parliament, Legislative Observatory, procedure 2025/0359(COD) (adoption dates, final act): https://oeil.secure.europarl.europa.eu/oeil/en/procedure-file?reference=2025/0359(COD)
- European Commission, "AI Omnibus enters into force" (Jul 27, 2026): https://digital-strategy.ec.europa.eu/en/news/ai-omnibus-enters-force
- European Commission, AI Act regulatory framework (risk tiers, timeline, Omnibus dates): https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
- European Commission, AI Act Service Desk, implementation timeline: https://ai-act-service-desk.ec.europa.eu/en/ai-act/timeline/timeline-implementation-eu-ai-act
- European Commission, The General-Purpose AI Code of Practice: https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai
- European Commission, General-Purpose AI Models in the AI Act: Q&A: https://digital-strategy.ec.europa.eu/en/faqs/general-purpose-ai-models-ai-act-questions-answers
- European Commission, Code of Practice on Transparency of AI-generated Content: https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content
- Future of Life Institute, AI Act Explorer (consolidated article texts incl. 2026 amendments) (secondary): https://artificialintelligenceact.eu/ai-act-explorer/
- Future of Life Institute, AI Act implementation timeline (updated Aug 31, 2026) (secondary): https://artificialintelligenceact.eu/implementation-timeline/
- Addleshaw Goddard, "EU AI Act: AI Omnibus formally adopted" (Jul 1, 2026) (secondary): https://www.addleshawgoddard.com/en/insights/insights-briefings/2026/technology/eu-ai-act-ai-omnibus-formally-adopted/
- EO 14179, Removing Barriers to American Leadership in AI (Jan 23, 2025): https://www.federalregister.gov/documents/2025/01/31/2025-02172/removing-barriers-to-american-leadership-in-artificial-intelligence
- EO 14365, Ensuring a National Policy Framework for AI (Dec 11, 2025): https://www.govinfo.gov/content/pkg/FR-2025-12-16/html/2025-23092.htm
- EO 14434, Inaugurating the Era of Super Intelligence (Sep 29, 2026): https://www.govinfo.gov/content/pkg/FR-2026-10-02/html/2026-20321.htm
- Littler, "Colorado Amends its Artificial Intelligence Law" (SB 26-189, May 15, 2026) (secondary): https://www.littler.com/news-analysis/asap/colorado-amends-its-artificial-intelligence-law-substantially-reducing
- California SB 53 and SB 243, legislature bill pages (not reachable from here): https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260SB53 and https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260SB243
- NIST, AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- NIST AI 600-1, Generative AI Profile (Jul 26, 2024): https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- ISO/IEC 42001:2023, AI management systems: https://www.iso.org/standard/42001
- Mitchell et al., "Model Cards for Model Reporting" (2018): https://arxiv.org/abs/1810.03993
- Gebru et al., "Datasheets for Datasets" (2018): https://arxiv.org/abs/1803.09010
- C2PA, Content Credentials specifications: https://c2pa.org/specifications/
