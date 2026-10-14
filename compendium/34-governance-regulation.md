# 34. Governance and Regulation

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

Governance applies to every era in this compendium, from a single prompted call to a fleet of agents. P4 (output is sampled) and P8 (errors compound, so verification is the bottleneck) drive it. [§33](33-agent-identity.md) gave agents identities and scoped permissions, which are obligations you owe to the users whose data and accounts an agent touches. Regulators add obligations to society: to people who never chose your system but are screened, scored or shown content by it. Since 2024 these obligations have become law in the EU, and in the US they are a shifting mix of executive orders and state statutes. **This section is not legal advice.** It explains the mechanisms so you can build the right controls and have a useful conversation with counsel. Every date in it is as of October 2026, and the law moves.

## Why this exists

Most software regulation assumes you can specify behavior and then test that the software meets the specification. A probabilistic system breaks that assumption. The same input can produce different outputs (P4), and the set of possible outputs is effectively unbounded, so nobody can enumerate and certify them. Quality is a distribution, which you measure with evals rather than prove with unit tests.

The cost of a wrong output also depends on where you put the model. A model that drafts marketing copy and the same model that ranks job applicants have identical weights and very different stakes. The Commission names the core problem in its explainer of the AI Act: "it is often not possible to find out why an AI system has made a decision or prediction and taken a particular action," so it "may become difficult to assess whether someone has been unfairly disadvantaged, such as in a hiring decision."

Regulators therefore stopped trying to certify the artifact and started regulating the **process** around it:

- know what you deployed and for what purpose
- assess the risk before you ship
- keep records good enough to reconstruct what happened
- put a human where errors are costly
- tell people when they are dealing with AI
- watch the system in production, and report serious failures

That list is P8 turned into law. If verification is the bottleneck and silent errors are the dangerous ones, a regulator's best lever is to require that errors become *observable and correctable*: logs, oversight, monitoring, incident reports.

If you have worked through GDPR, this is familiar. Data governance (catalogs, lineage, retention, access control) became mandatory engineering once regulation made "we don't know where that data went" an unacceptable answer. AI governance is the same move one layer up: "we don't know why the system said that" is becoming an unacceptable answer.

## How it works (under the hood)

### The EU AI Act: regulate the use, scale the duty to the risk

The AI Act is Regulation (EU) 2024/1689. It was published in the Official Journal on July 12, 2024 and entered into force on August 1, 2024. Its duties switch on in stages through 2028. Three design choices explain most of it.

**1. Duties attach to the intended purpose, not the technology.** The same model can be minimal-risk in a spam filter and high-risk in CV screening. You classify the *use case*.

**2. Duties attach to roles.** The two you will meet most:

- A **provider** develops an AI system or a general-purpose AI model, or has one developed, and places it on the market or puts it into service under its own name or trademark (Art. 3(3)).
- A **deployer** uses an AI system under its authority, other than for personal non-professional use (Art. 3(4)).

If you build a product on Claude or GPT and sell it, you are the provider of an *AI system*, and the model vendor is the provider of a *general-purpose AI model*. Your customer is the deployer. Roles can shift. Under Art. 25 a deployer becomes the provider of a high-risk system if it puts its own name on that system, makes a substantial modification to it, or changes the intended purpose of a non-high-risk system so that it becomes high-risk.

**3. Reach is extraterritorial.** The Act covers providers placing systems on the EU market wherever they are established, and providers and deployers in third countries "where the output produced by the AI system is used in the Union" (Art. 2(1)(c)). A US company whose model output reaches people in the EU is in scope.

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

**Prohibited practices (Art. 5).** As of Oct 2026 the Commission lists nine: harmful manipulation and deception; exploitation of vulnerabilities; social scoring; predicting an individual's criminal offences from profiling; untargeted scraping of the internet or CCTV to build facial-recognition databases; emotion recognition in workplaces and education; biometric categorisation to infer protected characteristics; real-time remote biometric identification for law enforcement in public spaces; and, added by the 2026 amendments, systems that generate non-consensual intimate imagery or child sexual abuse material ("nudification" apps). The first eight have applied since February 2, 2025. The ninth applies from December 2, 2026.

**High-risk systems (Art. 6).** There are two routes in:

- **Annex I:** the AI is a safety component of, or itself is, a product already covered by EU product-safety law (machinery, toys, lifts, medical devices). These are the "embedded" systems.
- **Annex III:** standalone use cases in sensitive areas. These are biometrics, critical infrastructure, education (for example, exam scoring), employment (CV sorting, promotion, termination, worker monitoring), access to essential services (credit scoring, pricing life and health insurance, public benefits), law enforcement, migration and border control, and the administration of justice and democratic processes.

Art. 6(3) carves out Annex III systems that do not "materially influence the outcome of decision making", for example a narrow procedural task or a preparatory step. The carve-out never applies when the system profiles people, and a provider who relies on it must document the assessment before shipping (Art. 6(4)).

High-risk providers must meet a set of requirements and then pass a conformity assessment, register the system in an EU database and run post-market monitoring:

- risk management (Art. 9)
- data governance (Art. 10)
- technical documentation (Art. 11)
- automatic logging (Art. 12)
- information for deployers (Art. 13)
- human oversight (Art. 14)
- accuracy, robustness and cybersecurity (Art. 15)
- a quality management system (Art. 17)

Deployers have their own duties (Art. 26): use the system as instructed, assign oversight to competent people, monitor it, and keep its logs for at least six months. Public bodies, and deployers that use AI for credit scoring or life and health insurance pricing, must also run a fundamental-rights impact assessment before use (Art. 27).

**Transparency duties (Art. 50).** These apply to systems that are not necessarily high-risk:

- **Chatbots.** Providers must design systems that interact with people so that people are told they are dealing with an AI, "unless this is obvious" (50(1)).
- **Generated content.** Providers of systems that generate synthetic audio, image, video or text must mark outputs "in a machine-readable format and detectable as artificially generated or manipulated" (50(2)).
- **Deepfakes and public-interest text.** Deployers must disclose deepfakes. They must also disclose AI-generated text published "with the purpose of informing the public on matters of public interest", unless a human reviewed it and someone holds editorial responsibility (50(4)).
- **How and when to disclose.** The notice must be "clear and distinguishable", given at the latest at first interaction, and must meet accessibility requirements (50(5)).

Article 50 has applied since **August 2, 2026**. Generative systems already on the market before that date have until December 2, 2026 to comply with the marking duty. The Commission backs Article 50 with guidelines (Jul 2026) and a voluntary Code of Practice on Transparency of AI-generated Content. The code has a section for providers (marking and detection) and one for deployers (labelling), and about 190 organizations had signed it by the end of July 2026.

**Minimal risk.** There are no new duties beyond AI literacy (Art. 4). The 2026 amendments softened that duty to "take measures to support" staff literacy, and they state explicitly that it does not require guaranteeing any individual's level.

### General-purpose AI models

A **general-purpose AI (GPAI) model** is a model that can competently perform a wide range of distinct tasks. The Commission's indicative test is training compute above 10²³ FLOP plus the ability to generate language, images or video. GPAI rules have applied since **August 2, 2025**, and they bind the model provider, not you (unless you are one):

- **Every GPAI provider (Art. 53)** must keep technical documentation for the AI Office, give downstream providers enough information to understand the model's capabilities and limits, keep a copyright policy that honors text-and-data-mining opt-outs, and publish a summary of training content using the Commission's template.
- **GPAI models with systemic risk** are presumed when training compute exceeds 10²⁵ FLOP (Art. 51). Their providers must also run model evaluations "including conducting and documenting adversarial testing", assess and mitigate systemic risks, track and report serious incidents, and secure the model and its infrastructure (Art. 55).

Models placed on the market before August 2, 2025 have until August 2, 2027. From August 2, 2026 the AI Office can enforce these rules, including with fines.

The **GPAI Code of Practice** (published Jul 10, 2025) is the voluntary way to show compliance. It has three chapters. Transparency includes a Model Documentation Form. Copyright is the second. Safety and Security applies only to systemic-risk models. The Commission and the AI Board confirmed that it is an adequate tool. Signatories listed as of Oct 2026 include Amazon, Anthropic, Google, IBM, Microsoft, Mistral AI and OpenAI. xAI signed only the Safety and Security chapter.

**What this means if you call a model through an API:** you are usually not a GPAI provider. Fine-tuning can change that. The Commission's indicative criterion is that a downstream modifier becomes the provider of a new GPAI model when the modification's training compute exceeds **one third** of the original model's, and even then the obligations cover only the modification. A LoRA adapter ([§29](29-adapting-models.md)) is many orders of magnitude below that line.

### The timeline, including the 2026 amendments

In November 2025 the Commission proposed a "Digital Omnibus" simplification package. The AI-Act part, called the **"Digital Omnibus on AI"** or "AI Omnibus", reached political agreement on May 7, 2026 and, per the Commission, **entered into force on July 27, 2026**. The Commission links the final text at OJ L 2026/1744, which suggests the number Regulation (EU) 2026/1744 **(⚠ verify: EUR-Lex was unreachable from this environment)**. Its headline change is a delay to the high-risk rules, which were originally due in August 2026 (Annex III) and August 2027 (Annex I). The Commission's stated reason: the rules should apply "when companies have the right support tools to facilitate implementation, such as standards."

| Date | What starts to apply |
|---|---|
| Aug 1, 2024 | Entry into force; no duties yet |
| Feb 2, 2025 | Prohibitions 1–8; AI literacy |
| Aug 2, 2025 | GPAI model obligations; governance bodies; penalty rules |
| Aug 2, 2026 | Most of the Act, including Art. 50 transparency; enforcement starts (AI Office for GPAI; national authorities for prohibitions, transparency, literacy) |
| Dec 2, 2026 | Prohibition 9 (NCII and CSAM generation); Art. 50(2) marking deadline for systems already on the market |
| Aug 2, 2027 | GPAI models placed before Aug 2, 2025 must comply; each member state has a regulatory sandbox |
| **Dec 2, 2027** | **High-risk rules for Annex III (standalone) systems** |
| **Aug 2, 2028** | **High-risk rules for Annex I (embedded in regulated products) systems** |
| Aug 2, 2030 | Legacy high-risk systems used by public authorities must comply |

The Omnibus also made other changes:

- It extended some SME simplifications to "small mid-caps".
- It kept the high-risk database registration duty but slimmed its content.
- It allowed processing of special-category data for bias detection more broadly, with safeguards.
- It centralized oversight of AI systems built on GPAI models in the AI Office.
- It clarified the overlap with the Machinery Regulation.

A separate Digital Omnibus amending the GDPR, NIS2 and the Data Act was still moving through the legislative process as of July 2026 (secondary source). I could not confirm its status as of October 2026 **(⚠ verify)**.

Penalties scale with the tier. Fines reach up to €35M or 7% of worldwide annual turnover for prohibited practices, €15M or 3% for most other obligations, and €7.5M or 1% for supplying misleading information to authorities (Art. 99).

### The US landscape (high level, as of Oct 2026)

The US has no comprehensive federal AI statute. Policy runs through executive orders and existing law, such as the FTC Act's ban on unfair and deceptive practices, civil-rights law and sector regulators.

**Federal executive actions:**

- **Jan 2025.** On Jan 20, EO 14148 rescinded the 2023 AI order (EO 14110). On Jan 23, EO 14179 ("Removing Barriers to American Leadership in Artificial Intelligence") set a deregulatory direction.
- **Jul 23, 2025.** The AI Action Plan was published together with three orders (data-center permitting, AI exports, and "Preventing Woke AI in the Federal Government").
- **Dec 11, 2025.** EO 14365, "Ensuring a National Policy Framework for Artificial Intelligence", targets state laws. It:
  - set up a DOJ **AI Litigation Task Force** to challenge state AI laws
  - ordered Commerce to publish, within 90 days, a list of "onerous" state laws
  - tied some federal broadband grant money to states not having such laws
  - asked for a legislative proposal to preempt state laws, with carve-outs for child safety, data-center infrastructure and state procurement

  The White House reportedly released a non-binding legislative framework on Mar 20, 2026 (secondary). I could not confirm whether the Commerce list has been published **(⚠ verify)**.
- **Jun 2, 2026.** EO 14409 focuses on AI and cybersecurity.
- **Sep 29, 2026.** EO 14434 directs agencies to use "Super Intelligence" ("SI") in place of "AI" in executive-branch documents. Expect the new term in federal documents from now on.

**State laws.** These are the moving part:

- **Colorado.** SB 24-205 (2024) was the first broad state AI act. It imposed a duty of care against algorithmic discrimination in "consequential decisions" and required impact assessments. It was delayed to June 30, 2026, then repealed and replaced in May 2026 by **SB 26-189**. The replacement is a narrower automated-decision law **effective January 1, 2027**. It requires notice to individuals, an adverse-action process with human review, and record retention of at least three years, and only the attorney general can enforce it **(⚠ verify: law-firm summaries; the legislature's site was unreachable)**.
- **California.** SB 53, the Transparency in Frontier Artificial Intelligence Act, was signed Sep 29, 2025 and took effect Jan 1, 2026. It requires large frontier-model developers to publish safety frameworks and transparency reports and to report critical safety incidents, and it protects whistleblowers. SB 243 (signed Oct 2025) requires "companion chatbots" to disclose that they are AI and to follow self-harm protocols **(⚠ verify both: secondary sources)**.
- **Others.** Texas, Illinois, New York City and other jurisdictions regulate narrower slices, often hiring **(⚠ verify specifics)**.

The engineering consequence is that you can't track fifty regimes feature by feature. You build one set of controls that satisfies the strictest common requirements: disclosure, logging, human review of consequential decisions, documented risk assessment. Then you map each law onto that set.

### Frameworks: NIST AI RMF and ISO/IEC 42001

Laws say *what* must be true. Frameworks give you a process for *making* it true, and auditors and customers often ask for them by name.

**NIST AI Risk Management Framework** (AI RMF 1.0, NIST AI 100-1, Jan 26, 2023) is voluntary and organizes the work into four functions:

- **Govern:** policies, roles and accountability. It is cross-cutting.
- **Map:** context, intended use, who is affected, what can go wrong.
- **Measure:** analyze and track risks. This is where evals live ([§26](26-evals.md)).
- **Manage:** prioritize, mitigate, respond and recover.

Its companion **Generative AI Profile** (NIST AI 600-1, Jul 26, 2024) names twelve risks specific to generative AI:

- CBRN information
- confabulation (NIST's term for hallucination)
- dangerous or violent content
- data privacy
- environmental impact
- harmful bias and homogenization
- human-AI configuration (over-reliance, automation bias, anthropomorphizing; see [§35](35-ai-ux.md))
- information integrity
- information security
- intellectual property
- obscene or abusive content
- value-chain and component integration

As of Oct 2026, NIST says AI RMF 1.0 "is being revised as part of the White House AI Action Plan," and in April 2026 it published a concept note for a critical-infrastructure profile.

**ISO/IEC 42001:2023** is a certifiable **AI management system** standard. If you know ISO 27001 for information security, it is the same shape for AI: an AI policy, assigned roles, risk and impact assessments, controls, internal audit and continual improvement (plan-do-check-act), all checked by a third-party auditor. NIST gives you vocabulary and practices. ISO 42001 gives you an auditable certificate that you run the process. Neither makes you compliant with the AI Act by itself. The Act's own presumption of conformity comes from harmonised European standards, and the delay in finishing those standards is why the high-risk dates moved.

### What this means for engineers

Each obligation turns into a mechanism you build. The seven below cover most of it.

**1. Logging and record-keeping.** High-risk systems must "technically allow for the automatic recording of events (logs) over the lifetime of the system" (Art. 12), and providers and deployers keep them at least six months (Arts. 19, 26). The log has to let you reconstruct a decision months later. Here is the key difference from data pipelines. A SQL result can be recomputed from its inputs and code. A model output can't be recomputed bit for bit (P4), and the vendor may retire the model. So you **log the output itself**, plus every input that shaped it: model ID, prompt version, retrieved sources and their versions, tool calls, and the human decision.

Keep **audit logs** separate from **observability traces** ([§27](27-observability.md)). Traces are sampled, short-lived and for debugging. Audit records are complete, append-only, retention-governed and joined to traces by ID.

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

The record stores references and hashes, not raw prompts with personal data inline. That resolves the tension between "keep logs" and GDPR's data minimization. The payloads live in a separately access-controlled store with their own retention, and the log line proves which payload was used. The hash chain makes after-the-fact edits detectable, which matters when the log is evidence.

**2. Human oversight design.** Art. 14 is unusually concrete for a law. The people overseeing a high-risk system must be able to:

- understand its capacities and limitations
- "remain aware of the possible tendency of automatically relying or over-relying on the output" (**automation bias**)
- correctly interpret its output
- decide to disregard, override or reverse it
- interrupt it "through a 'stop' button or a similar procedure" that halts in a safe state

In engineering terms, put the approval at the consequential step ([§11](11-agents.md), [§20](20-agent-runtime.md)). Show the evidence, not just the verdict. Make override as easy as accept, and log both. Build the stop path. Then **measure** oversight. A reviewer who approves 99.8% of recommendations in two seconds each is a rubber stamp, and the override rate and time-to-decide in your audit log will show it. [§35](35-ai-ux.md) covers how to design this so people actually look.

**3. Transparency and disclosure.** Tell people at first contact that they are talking to an AI, in the UI rather than in the terms of service. Mark generated media in machine-readable form, for example with C2PA Content Credentials manifests or watermarks, and label deepfakes. For high-risk systems, ship **instructions for use** to deployers (Art. 13): intended purpose, accuracy levels, known limitations, oversight measures. Disclosure is a UI component, so it must be accessible (Art. 50(5)).

**4. Data governance and provenance.** Art. 10 requires training, validation and test data that is relevant, representative and examined for bias. For an LLM application that you don't train, provenance shifts to what you *do* control:

- the RAG corpus ([§09](09-rag.md)): where each document came from, its version, its access rights
- eval sets: who labeled them and when
- fine-tuning data: its lineage, consent and licensing
- the memory a system writes about users ([§17](17-memory.md))

Each retrieved chunk in the audit record carries its source version, which is lineage applied to context.

**5. Model and system documentation.** Three formats exist:

- A **model card** (Mitchell et al., 2018) documents a model's intended use, evaluation across groups and limitations.
- A **datasheet** (Gebru et al., 2018) does the same for a dataset.
- A **system card**, the label frontier labs use for the documents they publish with model releases, covers a deployed model plus its safeguards, red-teaming and evaluations.

For your own application, write a system card per use case covering intended purpose, model versions, data sources, eval results, known failure modes, the oversight design and a change log. High-risk systems need the full Annex IV technical documentation, and GPAI providers fill in the Model Documentation Form. Generate as much of this as you can from config and eval output, the way dbt generates docs from the project. Hand-written documents drift from the system they describe.

**6. Incident reporting.** High-risk providers report a **serious incident** to the market-surveillance authority "immediately after" establishing a causal link, or its reasonable likelihood. Art. 73 sets the outer limits:

- no later than **15 days** after becoming aware
- **2 days** for a widespread infringement or serious disruption of critical infrastructure
- **10 days** if a person died

An incomplete initial report is allowed. Providers must not alter the system in a way that could affect the investigation before informing authorities, so **preserve evidence before you hotfix**: pin the model version, prompt and config, and snapshot the relevant audit records. Systemic-risk GPAI providers have a parallel duty to report to the AI Office (Art. 55). In practice this means an incident runbook with a severity rubric, and audit logs good enough to establish causality within days. It is the AI equivalent of GDPR's 72-hour breach clock.

**7. Evals as compliance evidence.** The regulation keeps asking for testing. Risk management requires testing against defined metrics (Art. 9). Accuracy levels must be declared to deployers (Arts. 13, 15). Systemic-risk models need documented adversarial testing (Art. 55). Post-market monitoring is required (Art. 72). Your eval suite ([§26](26-evals.md)) and online monitoring ([§27](27-observability.md)) are that evidence. That holds only if they are versioned, tied to a release, stored with results and reproducible. An eval you ran once in a notebook is not evidence. A release gate that blocks deploys below a threshold and archives the report is. Red-team results from [§32](32-security-guardrails.md) belong in the same file.

### Internal governance

Laws arrive slowly. Your organization needs rules for next week's use case.

**An AI inventory** lists every AI use case with its owner, purpose, models, data, tier and status. Without it you can't answer a regulator, a customer questionnaire or your own security team.

**Risk tiering of use cases** decides how much process each use case gets. A rules table works well: it is readable by legal, testable by engineering, and versioned like code.

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

Two details matter. First, **obligations stack**: a public-facing CV screener is high-risk *and* has transparency duties, so the classifier returns the union of controls rather than only the top tier. Second, the table encodes *your* policy. The "review" tier is a company choice to send Annex III use cases that claim the Art. 6(3) exemption to legal; the Act doesn't name such a tier. Keep the table in the repo with tests for known use cases, and have legal review changes to it the way you would review a change to access policy.

**Model approval.** Keep an approved-models list. Each entry records the vendor's terms, data retention (including zero-retention options), processing region, whether the vendor signed the GPAI Code of Practice, and eval results *on your tasks*. Pin versions. A model swap is a change that needs re-evaluation, because the model is a dependency whose behavior you can't diff (P4). It is also a change you will be forced to make, because vendors retire models and better ones arrive (P12). Treat prompt edits the same way. A one-line prompt change can shift behavior as much as a new model, so prompts go through review and the eval gate.

**AI use policies** say what employees may put into which tools. Map them to your data classification: public, internal, confidential, regulated. Pair each policy with an approved tool that is better than the shadow alternative. Policies that only forbid get ignored.

### The data-governance analogy

The analogy to data governance is close enough to reuse your instincts:

| Data governance | AI governance | Where the analogy breaks |
|---|---|---|
| Data catalog | AI inventory and model registry | A model's behavior isn't described by its schema |
| Classification (PII, confidential) | Use-case risk tier | Tier depends on *purpose*, not on the content of the data |
| Lineage (column-level) | Provenance: model, prompt version, retrieved docs, tools per output | You can't recompute the output from lineage (P4), so you must also store it |
| Retention policies | Log retention (≥ 6 months for high-risk) vs minimization | Both apply at once; resolve with references, redaction and tiered stores |
| Access control (grants, RBAC) | Tool permissions and agent identity ([§33](33-agent-identity.md)) | Agents act, so authorization is also about actions, not just reads |
| Data quality tests (dbt tests) | Evals and monitors | Pass rates, not pass/fail; thresholds are judgment calls |
| Data contracts | System cards and instructions for use | Contracts can't promise exact outputs, only measured rates |
| Breach notification (72 h) | Serious-incident reporting (2–15 days) | Causality is harder to establish for a statistical failure |

### Failure modes

- **Compliance theater.** Documents describe the system as it was at approval, and the system changed three model versions ago. Generate documentation from the running config, or it will drift.
- **Rubber-stamp oversight.** A human is "in the loop" but approves everything in seconds. Measure override rates and decision times, and redesign the review ([§35](35-ai-ux.md)).
- **Mis-tiering.** "It's just a chatbot," but it ranks applicants or answers benefits questions. Tier by what the output *influences*, not by what the interface looks like.
- **Role blindness.** You rebrand a vendor's high-risk system, or repurpose a general assistant for hiring, and become its provider under Art. 25.
- **Logs that can't answer the question.** Either nothing is reconstructable (no output, no prompt version) or everything is logged raw, which creates a privacy liability bigger than the AI risk.
- **Waiting for the deadline.** The high-risk dates moved once, and nobody knows whether they will move again. Inventory, tiering, logging and eval gates are good engineering on any timeline, so build them now.

### When not to apply heavy governance

Proportionality is part of the law and should be part of your policy. An internal SQL autocomplete doesn't need a review board, a risk file and a fundamental-rights assessment. Give it an inventory entry and standard logging. Heavy process on minimal-risk use cases teaches teams to route around governance entirely. Tier first, then spend process where the tier says to.

## Comparison

| | EU AI Act | NIST AI RMF + GenAI Profile | ISO/IEC 42001 | US state laws (CO, CA, ...) |
|---|---|---|---|---|
| Nature | Binding law with fines | Voluntary framework | Certifiable management-system standard | Binding, narrow, changing |
| Scope | Use cases by risk tier; GPAI models | Any AI system; process-oriented | The organization's AI management system | Specific harms: consequential decisions, frontier models, chatbots |
| What it asks for | Specific duties per role and tier | Govern, Map, Measure, Manage | Policy, roles, risk and impact assessment, controls, audit | Notices, assessments, human review, reports |
| Evidence | Technical docs, logs, conformity assessment, registration | Your own risk records | Third-party certification | Records for the attorney general on request |
| When it matters to you | Any output used in the EU | US public sector, customer questionnaires, a shared vocabulary | Enterprise buyers asking for a certificate | Hiring, lending, housing; frontier developers |

| Obligation | Engineering mechanism | Artifact | See |
|---|---|---|---|
| Record-keeping (Arts. 12, 19, 26) | Append-only audit records joined to traces | Audit log with retention policy | [§27](27-observability.md) |
| Human oversight (Art. 14) | Approval points, override path, stop button, oversight metrics | Review UI and oversight dashboard | [§20](20-agent-runtime.md), [§35](35-ai-ux.md) |
| Transparency (Art. 50) | Disclosure component, output marking | UI notice, C2PA manifests | [§35](35-ai-ux.md) |
| Data governance (Art. 10) | Source versioning, eval-set lineage, bias checks | Data sheet, corpus manifest | [§09](09-rag.md), [§28](28-data-flywheels.md) |
| Documentation (Art. 11, Annex IV) | Docs generated from config and eval runs | System card | [§26](26-evals.md) |
| Accuracy and robustness (Art. 15) | Eval gates, red teaming, monitors | Versioned eval reports | [§26](26-evals.md), [§32](32-security-guardrails.md) |
| Incident reporting (Art. 73) | Runbook, evidence snapshot, severity rubric | Incident file | [§27](27-observability.md) |

## What it didn't solve

Compliance is a floor. A system can disclose that it is AI, log every decision, route each one through a human reviewer and pass its conformity assessment, and still be one that people misread, over-trust or can't correct. A law can say that an overseer must be able to override an output. It can't make the override button the obvious thing to press, or make the evidence quick enough to check that anyone checks it. Turning legal oversight into real oversight, so that users trust, understand and correct the system, is a design problem. → Next: [§35 AI UX and Generative UI](35-ai-ux.md)

## Check your understanding

**Q: Why does the EU AI Act attach most duties to use cases rather than to models?**

Risk comes from where an output lands, not from the weights. The same model is harmless filtering spam and consequential ranking job applicants. Because behavior is probabilistic and can't be fully certified in advance (P4), the Act scales duties to the stakes of the intended purpose: banned, high-risk, transparency-only or minimal. The model layer is regulated separately and more lightly through GPAI duties (documentation, copyright policy, and evaluations for systemic-risk models), because the model provider can't know every downstream use.

**Q: You build a CV-screening assistant on a vendor's model API and sell it to EU employers. What are you, and what applies when?**

You are the provider of a high-risk AI system (Annex III, employment), and each employer is a deployer. The vendor remains the GPAI model provider. If the assistant talks to candidates, the Art. 50 disclosure has applied since Aug 2, 2026. The high-risk requirements apply from Dec 2, 2027 under the 2026 amendments: risk management, data governance, logging, documentation, human oversight, accuracy, conformity assessment and registration. Employers must keep logs for at least six months and assign competent oversight. Confirm the details with counsel, but don't wait for 2027 to build the logging and oversight.

**Q: What would happen if your audit log stored the inputs and the model ID but not the outputs?**

You could not reconstruct what the system actually said. Unlike a SQL query, a model call is sampled (P4), so rerunning the same inputs can give a different answer. The model version may also have been retired by the time someone asks. Lineage tells you *how* an output was produced, but only the stored output tells you *what* it was. Store the output, or a reference to it in an access-controlled store, and hash it so the record is evidence.

**Q: Reviewers approve 99.8% of the system's recommendations, in about two seconds each. Do you have human oversight?**

On paper, yes. In substance, probably not. Art. 14 requires that overseers can interpret outputs, stay aware of automation bias, and override or stop the system. A near-total approval rate at that speed suggests nobody is evaluating anything. Check the oversight with your own data: seed known-bad cases and see whether reviewers catch them, show evidence rather than verdicts, and reduce the volume of reviews so each one gets attention. The alternative is to drop the claim of oversight and treat the step as automated, with the risk that implies.

**Q: NIST AI RMF vs ISO/IEC 42001: what does each give you?**

The NIST AI RMF is a voluntary vocabulary and practice guide (Govern, Map, Measure, Manage), and its Generative AI Profile lists twelve generative-AI risks to work through. ISO/IEC 42001 is a management-system standard that a third party can certify, so it proves to customers that you *run* an AI risk process. Many organizations use NIST to decide what to do and ISO 42001 to demonstrate that they do it. Neither alone satisfies the AI Act, whose presumption of conformity comes from harmonised European standards.

**Q: When does fine-tuning a vendor model make you a GPAI model provider?**

Under the Commission's indicative criterion, it happens when the compute used for your modification exceeds one third of the compute used to train the original model. Even then your obligations cover only the modification, for example adding documentation of what you changed. Typical fine-tuning, especially LoRA, is far below that threshold. The more common way to pick up obligations is through the use case: fine-tuning a model for hiring makes the *system* high-risk, whatever the compute.

**Q: Why are evals compliance evidence and not just engineering hygiene?**

The Act repeatedly asks for proof of testing. It requires testing against defined metrics in risk management, declared accuracy levels, adversarial testing for systemic-risk models, and post-market monitoring. A probabilistic system can't be proven correct, so measured rates on representative data are the only credible evidence of quality (P4). That evidence counts only if it is versioned, tied to a release, reproducible and archived: a release gate with stored reports, not a one-off notebook.

**Q: A team says, "the high-risk dates moved to 2027, so we'll deal with governance then." What is wrong with that plan?**

Several things already apply. Prohibitions have applied since Feb 2025, AI literacy duties too, and Art. 50 transparency since Aug 2026. The controls the high-risk rules require also take time to build and are good engineering anyway: an inventory, use-case tiering, reconstructable audit logs, eval gates, an incident runbook. Retrofitting logging onto a system that has run for a year leaves a year with no records. The dates moved once and could move again, but the direction has not changed.

## Takeaways

- This is not legal advice. Learn the mechanisms, build the controls, and take dated specifics to counsel.
- The EU AI Act regulates purpose and role: prohibited, high-risk, transparency, minimal. Obligations stack, and roles can shift (Art. 25).
- Timeline as of Oct 2026: GPAI since Aug 2025, Art. 50 transparency since Aug 2026, high-risk Annex III from Dec 2, 2027 and Annex I from Aug 2, 2028 (the AI Omnibus, in force Jul 27, 2026).
- The US has no federal AI statute. Executive orders push to preempt state laws, and state laws keep changing (Colorado's replacement act takes effect Jan 1, 2027).
- Log outputs, not just inputs: a sampled result can't be recomputed (P4). Keep audit records separate from traces, append-only and retention-governed.
- Measure human oversight (override rates, decision times), or it becomes a rubber stamp.
- Evals, red-team results and monitors are your compliance evidence once they are versioned and tied to releases.
- Tier use cases with a reviewed rules table, and spend process in proportion to the tier.

## Sources

- Regulation (EU) 2024/1689 (AI Act), EUR-Lex: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689
- AI Omnibus final text as linked by the Commission (OJ L 2026/1744): https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202601744
- European Commission, "AI Act" regulatory framework page (risk tiers, timeline, Omnibus dates): https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
- European Commission, AI Act Service Desk, implementation timeline: https://ai-act-service-desk.ec.europa.eu/en/ai-act/timeline/timeline-implementation-eu-ai-act
- European Commission, The General-Purpose AI Code of Practice: https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai
- European Commission, General-Purpose AI Models in the AI Act: Q&A (10²³ FLOP and one-third criteria): https://digital-strategy.ec.europa.eu/en/faqs/general-purpose-ai-models-ai-act-questions-answers
- European Commission, Code of Practice on Transparency of AI-generated Content: https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content
- Future of Life Institute, AI Act Explorer (article texts incl. amendments: Arts. 2, 4, 5, 6, 12, 14, 19, 25, 26, 27, 50, 51, 53, 55, 73, 99) (secondary, consolidated text): https://artificialintelligenceact.eu/ai-act-explorer/
- Future of Life Institute, AI Act implementation timeline (updated Aug 31, 2026) (secondary): https://artificialintelligenceact.eu/implementation-timeline/
- Addleshaw Goddard, "EU AI Act: AI Omnibus formally adopted" (Jul 1, 2026) (secondary): https://www.addleshawgoddard.com/en/insights/insights-briefings/2026/technology/eu-ai-act-ai-omnibus-formally-adopted/
- Federal Register, EO 14179, Removing Barriers to American Leadership in AI (Jan 23, 2025): https://www.federalregister.gov/documents/2025/01/31/2025-02172/removing-barriers-to-american-leadership-in-artificial-intelligence
- Federal Register, EO 14365, Ensuring a National Policy Framework for AI (Dec 11, 2025); text via GovInfo: https://www.govinfo.gov/content/pkg/FR-2025-12-16/html/2025-23092.htm
- Federal Register, EO 14409, Promoting Advanced AI Innovation and Security (Jun 2, 2026): https://www.govinfo.gov/content/pkg/FR-2026-06-05/html/2026-11415.htm
- Federal Register, EO 14434, Inaugurating the Era of Super Intelligence (Sep 29, 2026): https://www.govinfo.gov/content/pkg/FR-2026-10-02/html/2026-20321.htm
- Littler, "Colorado Amends its Artificial Intelligence Law" (SB 26-189, May 15, 2026) (secondary): https://www.littler.com/news-analysis/asap/colorado-amends-its-artificial-intelligence-law-substantially-reducing
- California SB 53 (Transparency in Frontier AI Act), legislature bill page (not reachable from this environment): https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260SB53
- California SB 243 (companion chatbots), legislature bill page (not reachable from this environment): https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260SB243
- NIST, AI Risk Management Framework (page, revision status): https://www.nist.gov/itl/ai-risk-management-framework
- NIST AI 600-1, Generative AI Profile (Jul 26, 2024): https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- ISO/IEC 42001:2023, AI management systems: https://www.iso.org/standard/42001
- Mitchell et al., "Model Cards for Model Reporting" (2018): https://arxiv.org/abs/1810.03993
- Gebru et al., "Datasheets for Datasets" (2018): https://arxiv.org/abs/1803.09010
- C2PA, Content Credentials specifications: https://c2pa.org/specifications/
- OpenTelemetry, GenAI semantic conventions: https://opentelemetry.io/docs/specs/semconv/gen-ai/
