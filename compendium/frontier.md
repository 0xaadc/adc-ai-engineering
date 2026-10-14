# Frontier Watchlist

> As of October 2026. This page covers what is emerging but not yet settled. Expect names, standards, and winners to change. Tags: **(⚠ verify)** means not confirmed against a primary source. Most claims here come from early adopters and vendors, so treat them as signals, not facts.

The rest of the compendium covers practices you can rely on. This page covers the edges. For each item it gives what it is, which principle makes it interesting, its honest status, and what to watch. When something here matures, it will be absorbed into one of the main sections, just as context engineering and harness engineering were.

## 1. Agentic commerce: agents that buy things

- **What:** protocols that let an agent discover products, check out, prove it is authorized to pay, and settle payment for a user. The main ones as of 2026:
  - **ACP** (Agentic Commerce Protocol; OpenAI and Stripe): agent-to-merchant checkout.
  - **AP2** (Agent Payments Protocol; Google): signed "mandates" that prove the user authorized a purchase.
  - **UCP** (Universal Commerce Protocol; Google and Shopify, reported Jan 2026 **(⚠ verify)**): merchant capability discovery.
  - **x402** (Coinbase): HTTP-native payments that reuse the long-dormant `402 Payment Required` status code, aimed at machine-to-machine micropayments.
- **Why it matters:** this is P11 (standard interfaces) meeting P9 (any text can be an instruction) with money attached. An injected instruction that triggers a purchase is the lethal trifecta with a payment rail added ([§32](32-security-guardrails.md)). Authorization ([§33](33-agent-identity.md)) becomes the whole game.
- **Honest status:** fragmented and fast-moving. Commentators mostly describe these as *layers* (discovery, checkout, authorization, settlement) rather than competitors. Reported adoption figures conflict, and some product features built on them have already been wound down **(⚠ verify)**. Learn the layering; don't bet on a winner yet.
- **Watch:** whether one protocol emerges per layer, how mandates and identity standards converge, and whether payment networks treat agent-initiated transactions differently.

## 2. Personal "claw" agents

- **What:** always-on personal agents that run on your own hardware, talk to you through messaging apps, and act on schedules. Karpathy's informal name for them, "claws" (Feb 2026), comes via Simon Willison **(⚠ verify)**. "Claws & Personal Agents" was a track at AI Engineer World's Fair 2026.
- **Why it matters:** these agents combine everything in Part 5: memory across months ([§17](17-memory.md)), skills ([§18](18-skills.md)), scheduled loops ([§21](21-loop-engineering.md)), and wide permissions over your personal accounts. The P9 risks are severe, because the agent reads untrusted content (email, messages, the web) and holds your credentials.
- **Honest status:** enthusiast territory. Powerful, with security models still immature.
- **Watch:** sandboxing and permission models for personal agents, and whether platform vendors ship first-party versions.

## 3. Proactive and ambient agents

- **What:** agents that act on *triggers* (events, schedules, changes in data) instead of waiting for a prompt. Examples are a background agent that triages new issues overnight, or one that watches a dashboard and opens a fix.
- **Why it matters:** this moves the human from the inner loop to the outer loop ([§21](21-loop-engineering.md)). The bottleneck becomes human attention for *reviewing* (P8), and interruption design becomes a UX problem ([§35](35-ai-ux.md)).
- **Honest status:** the building blocks are mature: scheduled automations, webhooks, background mode, durable runtimes ([§20](20-agent-runtime.md)). Products that are proactive *and* trusted are rare. The hard part is knowing when *not* to act.
- **Watch:** the economics of always-on agents (P10), and approval designs that avoid approval fatigue.

## 4. Continual learning

- **What:** systems that improve from experience after deployment. Today this is approximated by memory, skills, and periodic fine-tuning. The research goal is models that update themselves safely. "Memory & Continual Learning" was an AI Engineer World's Fair 2026 track.
- **Why it matters:** it would blur P5, the line between knowledge in the weights and knowledge supplied at runtime. It would also make the data flywheel ([§28](28-data-flywheels.md)) run continuously instead of in batches.
- **Honest status:** research plus approximations. In production, "learning" still means writing to memory, updating skills and rules (the ratchet in [§19](19-harness-engineering.md)), or retraining offline ([§29](29-adapting-models.md)).
- **Watch:** safe online-update methods, and how evals keep up when the system changes itself.

## 5. Model–harness co-training and RL environments

- **What:** frontier models are increasingly post-trained with reinforcement learning *inside* agent harnesses and environments (sandboxed software plus verifiers). The result is a model tuned to a particular toolset.
- **Why it matters:** this is P12 in action. The model and the harness co-evolve, so the same model can score very differently in different harnesses ([§19](19-harness-engineering.md)). It also blurs evals and training ([§29](29-adapting-models.md)): an RL environment is an eval you can learn from.
- **Honest status:** real and heavily funded at the labs. For application engineers, the practical consequence is to use the tool formats your model was trained on.
- **Watch:** whether open standards for environments and graders emerge, and whether harness-specific tuning reduces portability across tools.

## 6. Software factories

- **What:** loops of agents that take a spec all the way to merged, deployed code with minimal human involvement ([§21](21-loop-engineering.md), [§23](23-coding-agents.md)).
- **Why it matters:** this is the end state of P8. If verification can be automated well enough, more of software development can be. If it can't, factories produce plausible garbage at scale.
- **Honest status:** an aspiration with impressive demos. Production use depends on very strong back pressure (tests, types, linters) and narrow scopes.
- **Watch:** how teams keep humans in charge of intent and review without becoming the bottleneck.

## 7. Agent identity standards

- **What:** standards work on giving agents their own verifiable identity, with delegated authority from a user, beyond reusing human OAuth tokens ([§33](33-agent-identity.md)). Expect IETF and OpenID drafts, along with A2A's signed Agent Cards.
- **Why it matters:** least privilege (P9) needs a notion of *whose* privilege. Auditing "who did what on whose behalf" is a regulatory need too ([§34](34-governance-regulation.md)).
- **Honest status:** early drafts and vendor-specific implementations **(⚠ verify)**.
- **Watch:** convergence between the MCP authorization spec, A2A, and the identity standards bodies.

## 8. Generative UI as a protocol

- **What:** agents that return interactive UI components instead of text, for example MCP Apps (sandboxed UI as an MCP extension), AG-UI, and vendor widget kits ([§35](35-ai-ux.md)).
- **Why it matters:** UI is where verification happens (P8). Showing a diff, a preview, or a form is often the cheapest way to let a human check an agent's work.
- **Honest status:** standardizing in 2026. The protocols are real; the patterns for when to use generated UI are still forming.
- **Watch:** security boundaries for agent-rendered UI (P9) and cross-host portability (P11).

## 9. Local and on-device AI

- **What:** capable open-weight models running on laptops, phones, and edge devices ([§31](31-open-weights-self-hosting.md)). "Local AI" was an AI Engineer World's Fair 2026 track.
- **Why it matters:** privacy and latency (P10), offline use, and a different cost curve with no per-token bill.
- **Honest status:** practical for many narrower tasks. A capability gap remains on hard agentic work.
- **Watch:** how small models are used *inside* harnesses (routing, classification, compaction) alongside frontier models.

## 10. Out of scope, but adjacent

**Robotics and world models** (models of physical dynamics used for planning and control) appear at AI engineering conferences, but they are a different engineering discipline, with different data, safety constraints, and runtimes. This compendium leaves them out on purpose.

## How to evaluate anything new

Use the five questions from [§01](01-first-principles.md):

1. Which force does it address?
2. Which mechanism or principle does it rely on?
3. What does it cost?
4. How would you verify that it works?
5. What happens when models improve?

Then apply the four tests for a real discipline from [§38](38-disciplines-map.md): does it have a distinct bottleneck, its own artifacts, its own failure modes, and can it be taught without naming a product?

## Sources

- AI Engineer World's Fair 2026 tracks: https://ai.engineer/wf/llms.md
- AP2 (Agent Payments Protocol): https://ap2-protocol.org
- Agent payment protocols compared (secondary): https://atxp.ai/blog/agent-payment-protocols-compared
- Agent payment protocols compared (secondary): https://crossmint.com/learn/agentic-payments-protocols-compared
- Simon Willison's weblog (for "claws"): https://simonwillison.net
- LangChain, "The Anatomy of an Agent Harness" (on model–harness co-training): https://blog.langchain.com/the-anatomy-of-an-agent-harness/
- MCP Apps extension: https://modelcontextprotocol.io/extensions/apps/overview
