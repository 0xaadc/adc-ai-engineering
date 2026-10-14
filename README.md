# AI Engineering Compendium

A principles-first compendium of **AI engineering**, the discipline of building reliable software on top of foundation models. It covers everything from what happens inside an LLM to harness and loop engineering, and then how to measure, run, secure, and ship the result.

Most AI material is a list of tools to learn, and the tools change every month. This compendium starts from **twelve first principles** instead. Here are three of them:

- The model is a stateless next-token function.
- Context is a finite attention budget that degrades as it grows.
- Errors compound across steps, so verification is the bottleneck.

Every technique is explained as a consequence of those principles. The field's history is told as a **chain of problems**, where each step exists because the step before it left something unsolved:

> prompting → structured output → multimodal → embeddings → RAG → tools → agents → patterns → multi-agent → graphs → protocols (MCP/A2A) → context engineering → memory → skills → harness engineering → runtime → loop engineering

Once you understand the mechanism, you can work out the answer, including for tools that don't exist yet.

**Start here → [compendium/00-index.md](compendium/00-index.md)**

- [First Principles](compendium/01-first-principles.md): the twelve principles (P1–P12) that every other section relies on
- [The Agent Loop](compendium/11-agents.md) and [Agentic Design Patterns](compendium/12-agentic-design-patterns.md): how agents actually work
- [Context Engineering](compendium/16-context-engineering.md) → [Harness Engineering](compendium/19-harness-engineering.md) → [Loop Engineering](compendium/21-loop-engineering.md): the disciplines of 2025–2026
- [Build a Harness from Scratch](compendium/22-build-a-harness.md): every layer in one runnable file, [`compendium/code/mini_harness.py`](compendium/code/mini_harness.py), which needs only the Python standard library and no API key
- [Evals](compendium/26-evals.md) and [Security and Guardrails](compendium/32-security-guardrails.md): what keeps it working and what keeps it safe
- [Why X over Y](compendium/37-why-x-over-y.md) and [The Disciplines Map](compendium/38-disciplines-map.md): the decision bank, and every "X engineering" label sorted out
- [Timeline](compendium/timeline.md) · [Glossary](compendium/glossary.md) · [Cheat Sheet](compendium/cheat-sheet.md) · [Question Bank](compendium/question-bank.md) · [Frontier Watchlist](compendium/frontier.md)

## Try the capstone

```bash
python3 compendium/code/mini_harness.py --fresh   # runs offline against a scripted stub model
python3 compendium/code/mini_harness.py           # run again: the durable journal replays every step
```

The harness covers these layers: a stateless model call, a tool registry with a workspace jail, the agent loop with stop conditions, permission hooks and back pressure, compaction, skills loaded on demand, a progress file, a durable step journal, tracing, and an outer loop with a separate goal check. With `ANTHROPIC_API_KEY` set, `--real` runs the same harness against the Anthropic Messages API.

## Who it's for

It's written for engineers who know software or data systems well but have never built with LLMs or looked under the hood. Where an analogy helps, it draws on data engineering: idempotency, logs as the source of truth, DAGs, data quality tests, and catalogs. A companion primer on data engineering and architecture lives at [0xaadc/adc-data-engineering](https://github.com/0xaadc/adc-data-engineering). Its section on [AI on the data platform](https://github.com/0xaadc/adc-data-engineering/blob/main/primer/18-ai-on-data-platform.md) bridges the two.

## Accuracy

Content is current as of **October 2026**. Every section was written against primary sources (vendor documentation, specifications, original papers, and engineering posts) and then fact-checked in a second, independent pass. AI tooling changes monthly. Status is tagged **(GA)** or **(Preview)**, and the few claims that couldn't be confirmed against a primary source are tagged **(⚠ verify)**. Check the docs before you rely on a price, a limit, or a parameter name.

Licensed under the terms in [LICENSE](LICENSE).
