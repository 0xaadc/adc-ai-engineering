# 09. Retrieval-Augmented Generation (RAG)

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

Lewis et al. coined "retrieval-augmented generation" in May 2020. Their system paired a text generator with a DPR retriever ([§08](08-embeddings-and-search.md)) over a dense vector index of Wikipedia, and trained the two together. They described the combination as joining "parametric and non-parametric memory". RAG stayed mostly a research topic until 2023, when ChatGPT made every company want answers from its own documents. It then became the default architecture, usually in a simpler form than the paper's: nothing is trained, and a frozen model, an off-the-shelf retriever and some prompt assembly do the work. [§08](08-embeddings-and-search.md) left one problem open: search returns passages, not answers. RAG hands those passages to the model and asks it to answer from them, with citations.

## Why this exists

The root is P5: knowledge lives in the weights or arrives at runtime. Parametric knowledge, meaning what the weights learned in training, is frozen at the training cutoff and compressed lossily. It can't point to a source, it never contained your private data, and you can't revoke one fact for one user. P2 says the context window is the only other way in. So your facts have to arrive as tokens, at request time.

RAG does four jobs that weights can't:

- **Unseen knowledge:** private documents, and anything published after the training cutoff.
- **Citations:** each claim can point to a passage, which makes verification cheap (P8).
- **Freshness:** to update knowledge, you re-index a row instead of retraining a model.
- **Access control:** you filter per user at retrieval time. Weights can't forget per user.

Why not paste everything in? Context is finite and rots (P3), and every token costs (P10). Then there's hallucination: the model always emits *some* next token (P1), so when the fact is missing it emits a plausible one. Grounding gives it the right tokens to copy and quote.

## How it works (under the hood)

### The pipeline

```text
INGEST (offline, like an ELT job)
  sources ──▶ parse ──────────▶ chunk ──────────────▶ embed ──────────▶ index
  PDFs,       text + structure  + LLM context         pinned model      dense + BM25
  wikis,      (headings,        + metadata            version           + metadata
  tickets     tables)           (source, ACL, date)                     filters
                                                                          │
QUERY (online, per request)                                               │
  question ──▶ rewrite ──────▶ retrieve ◀────────────────────────────────┘
  + history    standalone,     hybrid + ACL/tenant filters
               expanded        ──▶ rerank (~150 → ~5-20)
                               ──▶ assemble context (sources first, stable IDs)
                               ──▶ generate with citations ──▶ answer + sources
```

### Ingest: parse → chunk → embed → index

- **Parse.** Turn PDFs, HTML and slides into text that keeps its structure (headings, lists, tables), with tools such as Docling ([§07](07-multimodal.md)). Many RAG failures start here. A table flattened into word soup can't be retrieved or read correctly.
- **Attach metadata to every chunk:** source URI, title, section path, version, effective date and ACL (the access-control list of who may read it). Metadata is what makes filtering, citation and freshness possible.
- **Embed** with a pinned model version, and **index** into a dense index and a BM25 index ([§08](08-embeddings-and-search.md)).
- **Run it incrementally,** from a change data feed or Dynamic Tables. Deletes and permission changes must propagate as fast as inserts. Otherwise the index keeps serving content that should be gone.

### Chunking strategies and tradeoffs

You chunk because one vector for a 50-page document averages away every specific fact, because the context budget is finite, and because citations need small units. The strategies are compared in the table under Comparison. In short, they run from fixed-size windows, through recursive splitting (Snowflake ships `SPLIT_TEXT_RECURSIVE_CHARACTER`), structure-aware and semantic splits, and parent-child ("small-to-big") retrieval, to **late chunking** (Günther et al., Sep 2024). Late chunking, like contextualized chunk models such as `voyage-context-4`, embeds the whole document with a long-context model and then pools per chunk, so each chunk's vector "knows" its document.

The core tradeoff is that small chunks match precisely but lose their referents ("It rose 3% that quarter": what is "it"?), while large chunks keep context but dilute the vector and spend more tokens per hit (P3, P10). Snowflake recommends at most 512 tokens per chunk for Cortex Search. No size is universal, so sweep chunk sizes against recall@k on your own evaluation set.

### Contextual retrieval (Anthropic, Sep 2024)

Anthropic's fix for lost referents is to have an LLM write the missing context into each chunk at index time:

```text
<document>
{{WHOLE_DOCUMENT}}
</document>
Here is the chunk we want to situate within the whole document
<chunk>
{{CHUNK_CONTENT}}
</chunk>
Please give a short succinct context to situate this chunk within the overall document for the
purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else.
```

The answer, usually 50 to 100 tokens, is prepended to the chunk before embedding ("Contextual Embeddings") **and** before BM25 indexing ("Contextual BM25"). So "The company's revenue grew by 3% over the previous quarter" becomes "This chunk is from an SEC filing on ACME corp's performance in Q2 2023; …", and both the vector and the inverted index now contain "ACME" and "Q2 2023". Averaged across their test domains, the top-20 retrieval failure rate fell from 5.7% to 3.7% with contextual embeddings (−35%), to 2.9% when contextual BM25 was added (−49%), and to 1.9% with reranking on top (−67%).

The cost is one LLM call per chunk at ingest, and another whenever the document changes. Because every chunk of a document shares the same document prefix, prompt caching ([§05](05-api-and-prompting.md)) makes this cheap. The post, which used Claude 3 Haiku, estimated a one-time cost of $1.02 per million document tokens (Sep 2024 prices). The same post gives the counter-advice too: if your knowledge base is under 200,000 tokens (about 500 pages), skip RAG and put it all in the prompt.

### Query: rewrite → retrieve → rerank → assemble → generate

- **Rewrite.** "And for digital ones?" means nothing to a retriever, so rewrite it into a standalone query using the chat history. You can also expand acronyms, split a compound question into sub-queries, or use HyDE (Gao et al., 2022): have the LLM draft a hypothetical answer and embed *that*, because answers look more like documents than questions do. Each rewrite is an extra model call (P10).
- **Retrieve** with hybrid search plus filters (tenant, ACL, date), and keep a generous top-N.
- **Rerank** down to top-k ([§08](08-embeddings-and-search.md)).
- **Assemble.** Remove near-duplicates, give each passage a stable ID, put sources before the question, and instruct the model to answer only from the sources and to say when they lack the answer.
- **Generate with citations.** Anthropic's Messages API accepts `search_result` content blocks **(GA, no beta header)**. With `citations: {"enabled": true}`, the response's text blocks carry `search_result_location` citations, each with `source`, `title`, `cited_text` and block indices, and `cited_text` doesn't count toward output tokens. Whole files go in `document` blocks, which support citations too. OpenAI and Google offer their own hosted file-search and grounding tools, with different citation shapes.

The whole loop, with a stub embedding so it runs without any key:

```python
import json, math, os, re, urllib.request, zlib
CORPUS = {  # source id -> chunk text. In production: parsed, chunked, versioned docs.
    "kb://refunds#1": "Refunds are issued within 14 days of receiving the returned item.",
    "kb://refunds#2": "Digital downloads are not eligible for refunds once opened.",
    "kb://shipping#1": "Standard shipping within the EU takes 3 to 5 business days.",
    "kb://errors#7": "Error E-4012 means the API key expired. Rotate it under Settings."}

def embed(text, dim=256):
    """STUB embedding: hash each word into one of `dim` buckets, then L2-normalize.
    It matches spelling, not meaning; swap in a real model (same interface) for that."""
    v = [0.0] * dim
    for word in re.findall(r"[a-z0-9-]+", text.lower()):
        v[zlib.crc32(word.encode()) % dim] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]

INDEX = {src: embed(text) for src, text in CORPUS.items()}       # INGEST: embed + index

def retrieve(query, k=2):                                        # QUERY: embed + top-k
    q = embed(query)
    scores = {src: sum(a * b for a, b in zip(q, vec)) for src, vec in INDEX.items()}
    return sorted(scores, key=scores.get, reverse=True)[:k]

question = "How many days until refunds are issued?"
hits = retrieve(question)
body = {"model": "claude-sonnet-5-5", "max_tokens": 16000,
        "system": "Answer only from the search results. If they lack the answer, say so.",
        "messages": [{"role": "user", "content": [                # ASSEMBLE: sources first
            *({"type": "search_result", "source": s, "title": s, "citations": {"enabled": True},
               "content": [{"type": "text", "text": CORPUS[s]}]} for s in hits),
            {"type": "text", "text": question}]}]}
if "ANTHROPIC_API_KEY" not in os.environ:                        # runs with no key
    print("retrieved:", hits, "\n", json.dumps(body, indent=1)[:600])
else:                                                            # GENERATE with citations
    req = urllib.request.Request("https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(), headers={"content-type": "application/json",
        "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"})
    for block in json.load(urllib.request.urlopen(req))["content"]:
        if block["type"] == "text":                              # cited spans carry sources
            print(block["text"], [c["source"] for c in block.get("citations") or []])
```

Two lessons hide in this toy. First, with `dim=64` instead of 256, hash collisions push the *shipping* chunk into the top 2. A retriever can be confidently wrong in ways the model can't see. Second, current models think by default, so the response can include `thinking` blocks before the text, and production code should check `stop_reason` before reading `content` ([§05](05-api-and-prompting.md)). A citation proves where a sentence came from, not that the model read it correctly. Still, checking a cited span is far cheaper than checking an uncited answer (P8).

### Failure modes

1. **Retrieval miss**, the most common failure. Debug it as a funnel, the way you reconcile row counts across pipeline stages. Is the answer in the corpus? Did parsing keep it? Does it sit within one chunk? Is it in the top-N? Did it survive reranking? Did it reach the context? Did the answer use it?
2. **Lost in the middle** (Liu et al., Jul 2023). Accuracy is "often highest when relevant information occurs at the beginning or end of the input context", and it degrades in the middle, even for long-context models. Send fewer, better-ranked chunks, and put the strongest ones at the edges (P3).
3. **Conflicting or stale documents.** When v1 and v2 of a policy are both retrieved, the model blends them or picks one, and it cites the stale one *faithfully*. Fix this in the data. Version documents, filter out superseded ones, show effective dates in the context, and ask the model to surface conflicts. Freshness is a pipeline SLA.
4. **Permission leaks.** Ingestion typically runs as a service account that can read everything. If retrieval doesn't filter by the *end user's* identity, the model will summarize the board memo for anyone who asks. A system-prompt line such as "don't reveal confidential documents" is not a control (P9), because once text is in context it can come out. Enforce permissions in the retriever: pre-filter by ACL (and avoid the post-filter trap from [§08](08-embeddings-and-search.md)), sync ACL changes, and include identity in cache keys. Retrieved text is also untrusted input. A wiki page that says "ignore previous instructions" is indirect prompt injection ([§32](32-security-guardrails.md)).
5. **Unfaithful generation.** The model mixes in parametric "knowledge" or over-generalizes. Faithfulness metrics measure this (see below).

### RAG vs long context vs fine-tuning

- **Long context** puts the whole corpus into every prompt. Current Claude models accept 1M tokens, and prompt caching cuts the cost of a repeated prefix. It fits small, stable corpora that every user may see. The downsides are that every call still pays to process those tokens (P10), quality degrades with length (P3), and there's no per-user filtering. Chroma's "Context Rot" study (Jul 2025) found that performance across 18 models degrades as input length increases, "often in surprising and non-uniform ways".
- **Fine-tuning** ([§29](29-adapting-models.md)) changes the weights. It's good for *behavior*: format, tone, domain style, habits. It's poor for *facts*: recall is unreliable, there are no citations, the knowledge is stale on day one, and nothing can be revoked per user. P5 sums it up: ground for facts, fine-tune for behavior.
- **They combine.** Fine-tune the embedder or reranker for your domain, use RAG to select, and use long context to hold what RAG selected.

### Evaluating RAG

Evaluate the two halves separately, because the fixes differ. The RAGAS definitions (Es et al., Sep 2023) are the common vocabulary:

- **Retrieval:** recall@k, MRR and nDCG ([§08](08-embeddings-and-search.md)) on labeled queries. *Context precision* asks whether the relevant chunks are ranked at the top of what you retrieved. *Context recall* is the share of claims in a reference answer that the retrieved context supports.
- **Generation:** *Faithfulness*, also called groundedness, is the number of claims in the response that the retrieved context supports divided by the total number of claims. *Response relevancy* asks whether the answer addresses the question. *Correctness* compares the answer with a reference answer.

RAGAS computes most of these with an LLM judge, and judges are probabilistic (P4), so validate them against human labels ([§26](26-evals.md)). Read the results as quadrants. Good retrieval with an unfaithful answer points to the prompt or the model. Bad retrieval with a faithful answer should produce "I don't know". Remember that faithful isn't correct: a perfectly grounded answer from a stale document is still wrong.

### Agentic RAG

Classic RAG is a **workflow** (P7). Code decides to retrieve exactly once, using the user's words as the query, before the model speaks. **Agentic RAG** gives the model a search tool and lets *it* decide whether to search, what to search for, whether the results are enough, and when to search again. That is what multi-hop questions need. "Which customers hit by last week's outage are on the enterprise plan?" requires finding the outage report first, then querying with what it says.

The lineage runs from ReAct (2022), which interleaved reasoning with search actions, through Self-RAG (Oct 2023), which trained a model to decide when to retrieve, to today's function calling ([§10](10-tool-use.md)). `search_result` blocks can also be returned from a tool call, so citations survive. Anthropic's context-engineering post (Sep 2025) calls this "just in time" retrieval: agents keep lightweight identifiers (file paths, queries, links) and load data at runtime. Claude Code, for example, navigates with glob and grep, "effectively bypassing the issues of stale indexing". This is P12: as models search better, some index-time scaffolding becomes optional, though not for huge or permission-heavy corpora. The costs are more calls, tokens and latency, and less predictability (P7, P8, P10). Use agentic RAG for multi-hop questions, not FAQ lookups.

### GraphRAG

Some questions have no answer chunk. "What are the main themes across 5,000 incident reports?" is a property of the whole corpus, and top-k retrieval would summarize a biased sample of it. Edge et al. (Microsoft, Apr 2024) call these "global sensemaking questions". Their **GraphRAG** builds a different index:

```text
INDEX:  corpus ─▶ TextUnits ─▶ LLM extracts entities, relationships, claims ─▶ knowledge graph
        ─▶ Leiden community detection (hierarchical clusters of densely linked entities)
        ─▶ LLM writes a summary ("community report") per community, bottom-up
QUERY:  global: map-reduce over community reports at one level
                (map: each batch → rated key points; reduce: best points → answer)
        local:  start at the entities named in the question, fan out to neighbors,
                relationships, claims and source text
        (also DRIFT = local plus community context; basic = plain vector top-k)
```

For global questions over datasets of about 1 million tokens, the paper reports "substantial improvements" over a conventional RAG baseline in the comprehensiveness and diversity of answers. The price is indexing. LLM calls for every chunk and every community make it far more expensive and slower than embedding, extraction errors get baked into the graph, changes mean re-indexing, and the docs strongly recommend tuning the prompts. LazyGraphRAG (Nov 2024) defers the LLM work to query time to reduce indexing cost **(⚠ verify)**. GraphRAG beats vector RAG on whole-corpus themes and on connect-the-dots questions across documents. For needle lookups ("what's the refund window?"), hybrid search is cheaper and just as good.

A note on names. Vendors also use "GraphRAG" loosely for any retrieval backed by a graph database. More importantly, it is **not** graph engineering ([§14](14-graph-engineering.md)). In graph engineering, the graph is the agent's *control flow*: nodes are steps and edges are transitions, as in LangGraph. In GraphRAG, the graph is the *data*: nodes are entities and edges are relationships. It's the same word at a different layer.

## Comparison

**Ways to give a model knowledge**

| Approach | How knowledge gets in | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Classic RAG | Code retrieves top-k once, model answers from it | Fresh, private, citable, per-user ACLs, cheap per call | Retrieval misses; fixed one-shot query | Most Q&A over documents |
| Long context | Whole corpus in every prompt (cached) | No retrieval to tune; sees everything | Per-call cost (P10), context rot (P3), no per-user filtering | Small, stable corpus that everyone may see |
| Fine-tuning | Weights updated by training | Behavior, style, format, domain habits | Facts unreliable, no citations, stale, irrevocable | Teaching *how* to respond, not *what* is true |
| Agentic RAG | Model calls a search tool as often as it needs | Multi-hop, self-correcting queries | More calls, latency, variance (P7, P8) | Questions that need several lookups |
| GraphRAG | Entity graph + community summaries, built by an LLM | Whole-corpus "sensemaking" questions | Expensive indexing; extraction errors | Themes and trends across many documents |

**Chunking strategies**

| Strategy | Mechanism | Strength | Weakness |
|---|---|---|---|
| Fixed-size + overlap | Every N tokens, with overlapping windows | Simple, predictable | Splits sentences and tables |
| Recursive | Paragraph, then sentence, then word, until it fits | Respects natural breaks | Still blind to meaning |
| Structure-aware | Headings, sections, functions; table rows with the header repeated | Coherent units, good citations | Needs clean parsing |
| Semantic | Break where adjacent sentence embeddings diverge | Topic-coherent chunks | Extra compute; uneven sizes |
| Parent-child | Match on small chunks, return the enclosing section | Precise match plus full context | More tokens per hit |
| Contextual / late chunking | Add document context to each chunk at index time (LLM-written or pooled from a long-context embedder) | Fixes lost referents | Ingest cost; rerun on change |

## What it didn't solve

The model can only read what you hand it. In classic RAG, the retrieval logic is fixed in your code: one query, chosen before the model has thought about the question. If that query misses, nothing fetches again. The model also can't get live data (today's order status) or act (issue the refund). Letting the model decide what to fetch, and what to do, takes a contract in which the model requests an action and the harness executes it (P6).

→ Next: [§10 Tool Use and Tool Design](10-tool-use.md)

## Check your understanding

**Q: Why does an LLM need RAG if it was trained on the whole internet?**

Training compresses public text into weights that are frozen at a cutoff, so the model never saw your private or recent data, can't cite where a "fact" came from, and can't forget it per user (P5). RAG puts the relevant passages into the context at request time, which gives the model fresh, private, citable facts to copy instead of guess. The tradeoff is a retrieval pipeline you must build, secure and evaluate. If your corpus is small and stable and everyone may see it, long context with caching may be simpler.

**Q: What would happen if you enforce document permissions only with a system-prompt instruction?**

Once a confidential passage is in the context, it is just tokens, and any user prompt, or injected text in another document, can get the model to repeat it (P9). The instruction lowers the leak rate but can't guarantee anything, because output is sampled (P4). The real control is in the retriever: filter by the end user's ACLs before passages reach the model, and keep ACLs in sync. The prompt line is fine as an extra layer, never as the only one.

**Q: Small chunks vs large chunks: what's the tradeoff, and how do you choose?**

Small chunks give focused vectors that match queries precisely, but they lose referents such as "it" or "the company", and an answer can straddle two chunks. Large chunks keep context but average many topics into one vector and cost more tokens per hit (P3, P10). Parent-child retrieval and contextual retrieval exist to get precise matching *and* context. Choose by sweeping chunk sizes against recall@k on your own evaluation queries, not by copying a default.

**Q: Why does contextual retrieval prepend context before both embedding and BM25 indexing?**

The missing information, such as which company or which quarter, hurts both retrievers: the dense vector doesn't encode it, and the inverted index doesn't contain the term. Adding a short LLM-written context to the chunk fixes both, and in Anthropic's tests the combination cut top-20 retrieval failures by 49%, against 35% for embeddings alone. The cost is one LLM call per chunk at ingest, made cheap by prompt caching, and it has to be rerun when documents change. For a tiny corpus, skip it and use long context.

**Q: A user reports a wrong answer from your RAG bot. How do you tell a retrieval failure from a generation failure?**

Check whether the correct passage was in the context the model actually received. If it wasn't, it's a retrieval problem: walk the funnel from corpus, parsing, chunking and top-N through reranking. If it was, it's generation: the model ignored the passage, was confused by a conflicting one, or missed it in the middle of a long context. Log retrieved IDs per request so traces answer this without re-running ([§27](27-observability.md)).

**Q: Agentic RAG vs classic RAG: when is giving the model a search tool not worth it?**

Agentic RAG lets the model reformulate and repeat searches, which helps on multi-hop questions where the first query can't be known in advance. Each extra step adds latency, tokens and variance, and errors compound across steps (P8). For simple lookups, such as a policy FAQ, one well-tuned hybrid retrieval inside a workflow is cheaper, faster and easier to evaluate. Move toward agentic RAG when traces show the fixed query regularly misses.

**Q: GraphRAG vs vector RAG: which questions favor GraphRAG, and why isn't it "graph engineering"?**

GraphRAG precomputes an entity graph, Leiden communities and LLM-written community summaries, so a "global" question about themes across the whole corpus can map-reduce over summaries instead of a biased top-k sample. It costs far more to index and adds little for needle lookups, where hybrid vector search is enough. The name collides with graph engineering ([§14](14-graph-engineering.md)), but there the graph is an agent's control flow (steps and transitions). In GraphRAG it is the data (entities and relationships).

## Takeaways

- RAG exists because parametric knowledge is frozen, public, uncitable and irrevocable; supplied knowledge is fresh, private, citable and filterable (P5).
- Ingest is an ELT pipeline (parse, chunk, embed, index) and inherits that discipline: metadata, lineage, incremental loads and propagated deletes.
- Most RAG failures are retrieval failures; debug as a funnel and measure recall@k first.
- Contextual retrieval adds document context to every chunk before both embedding and BM25 indexing.
- Enforce permissions in the retriever, never in the prompt (P9).
- Ground for facts, fine-tune for behavior; long context fits small, stable, shared corpora.
- Evaluate retrieval (context precision and recall) and generation (faithfulness) separately; faithful is not the same as correct.
- Agentic RAG hands the retrieval decision to the model; GraphRAG answers whole-corpus questions; neither is graph engineering.

## Sources

- Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", May 2020: https://arxiv.org/abs/2005.11401
- Anthropic, "Introducing Contextual Retrieval", Sep 19, 2024: https://www.anthropic.com/news/contextual-retrieval
- Anthropic, Search results (`search_result` blocks and citations): https://platform.claude.com/docs/en/build-with-claude/search-results
- Anthropic, Citations: https://platform.claude.com/docs/en/build-with-claude/citations
- Anthropic, "Effective context engineering for AI agents", Sep 29, 2025: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Liu et al., "Lost in the Middle: How Language Models Use Long Contexts", Jul 2023: https://arxiv.org/abs/2307.03172
- Hong et al. (Chroma), "Context Rot: How Increasing Input Tokens Impacts LLM Performance", Jul 2025: https://research.trychroma.com/context-rot
- Es et al., "Ragas: Automated Evaluation of Retrieval Augmented Generation", Sep 2023: https://arxiv.org/abs/2309.15217
- Ragas metric definitions (faithfulness, context precision and recall): https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/
- Gao et al., "Precise Zero-Shot Dense Retrieval without Relevance Labels" (HyDE), Dec 2022: https://arxiv.org/abs/2212.10496
- Günther et al., "Late Chunking: Contextual Chunk Embeddings Using Long-Context Embedding Models", Sep 2024: https://arxiv.org/abs/2409.04701
- Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models", Oct 2022: https://arxiv.org/abs/2210.03629
- Asai et al., "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection", Oct 2023: https://arxiv.org/abs/2310.11511
- Edge et al., "From Local to Global: A Graph RAG Approach to Query-Focused Summarization", Apr 2024: https://arxiv.org/abs/2404.16130
- Microsoft GraphRAG documentation (indexing, global/local/DRIFT search): https://microsoft.github.io/graphrag/
- Microsoft GraphRAG, Global Search (map-reduce over community reports): https://microsoft.github.io/graphrag/query/global_search/
- Microsoft Research, "LazyGraphRAG: Setting a new standard for quality and cost", Nov 2024: https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/
- Snowflake Cortex Search (chunking guidance, refresh semantics): https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview
- Anthropic, Embeddings guide (Voyage models incl. `voyage-context-4`): https://platform.claude.com/docs/en/build-with-claude/embeddings
- Docling (document parsing): https://docling-project.github.io/docling/
