# 08. Embeddings and Search

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

The idea is older than LLMs. In 2013, word2vec (Mikolov et al.) trained a small network to place words as points in space so that words used in similar contexts landed near each other. In 2019 and 2020, Sentence-BERT and Dense Passage Retrieval (DPR) did the same for whole sentences and passages, which turned "find passages that mean what this question means" into a nearest-neighbor problem. Then, in 2023, everyone wanted ChatGPT over their own documents, and vector databases boomed.

[§07](07-multimodal.md) left this problem open. The model can read text, images and PDFs, but only what you put into its context. It doesn't know your data (P5), and you can't paste the whole corpus into every call (P3, P10). You have to find the few pieces that matter. This section covers how that search works. [§09](09-rag.md) connects it to generation.

## Why this exists

Keyword search fails on **vocabulary mismatch**. A user asks "how do I get my money back?", and the answer sits in a document titled "Refund policy" that shares none of those words. Stemming and synonym lists help, but they are brittle. LLM users make it worse, because they type whole questions in any phrasing or language.

What you want is a function that maps any text to a fixed-length list of numbers, such that texts with similar meaning get nearby lists. That function is an **embedding model**, and its output is an **embedding** (a vector). Once meaning is geometry, search becomes "which stored vectors are nearest to the query vector?", and geometry can be indexed.

Why not let the LLM read everything? Tokens cost money (P10) and dilute attention (P3). Retrieval is a cheap, selective filter in front of the expensive operator, which is predicate pushdown for meaning.

## How it works (under the hood)

### What an embedding is: meaning as geometry

An embedding model is usually a transformer, like the one in [§02](02-how-llms-work.md), trained to output one vector of `d` numbers per input instead of predicting the next token. `d` is the **dimension**, for example 1,024. No single dimension means anything a human could name. Meaning lives in relative positions and directions. The word2vec papers famously showed `vector("King") − vector("Man") + vector("Woman")` landing nearest to `vector("Queen")`. word2vec gave each word one fixed vector. A transformer instead produces a contextual vector per token, and a **sentence embedding** pools those into one vector per passage. One vector per passage is what makes indexing cheap, and it is also the root of most weaknesses below: a 500-word passage gets squeezed into a single point.

Three consequences follow:

- **Vectors are comparable only within one model version.** Each model learns its own space, so changing the model means re-embedding the corpus, a full backfill, like changing the hash behind a partition key. The deliberate exception is a family trained into a shared space. Voyage's 4-series (Jan 2026) lets you embed documents with `voyage-4-large` and queries with `voyage-4-lite`.
- **Queries and documents may be embedded differently.** Voyage models take `input_type="query"` or `"document"` and prepend a different instruction to each. If you omit it, retrieval quality suffers. (Anthropic offers no embedding model of its own; its docs point to Voyage AI, now part of MongoDB. OpenAI serves its own models at `/v1/embeddings`.)
- **Similarity is not truth.** "The refund window is 14 days" and "The refund window is not 14 days" embed close together. Embeddings capture *aboutness*. They are weak on negation, exact numbers and identifiers.

### How embedding models are trained: contrastive learning

The training data is pairs that should match: a question and its answer passage, a title and its body, a query and the result someone clicked. Increasingly the pairs come from LLM-generated queries for existing passages. **Contrastive learning** treats each batch as a multiple-choice test:

```text
batch: (q1, p1) (q2, p2) ... (qB, pB)          s = cosine similarity, τ = temperature
loss(q1) = −log(  exp(s(q1, p1) / τ)  /  Σ_j exp(s(q1, pj) / τ)  )
           "which passage in this batch is q1's partner?"; the other B−1 are in-batch negatives
```

This is the InfoNCE loss (van den Oord et al., 2018), the same idea behind CLIP in [§07](07-multimodal.md). **Hard negatives**, passages that look relevant but aren't (DPR mined them with BM25), sharpen the model. The consequence is that "similar" means whatever the training pairs said. Jargon, part numbers and acronyms the model never saw land poorly, which is why domain-specific models exist. A public leaderboard such as MTEB is good for a shortlist, but test on *your* queries.

### Cosine similarity and normalization

**Cosine similarity** is `a·b / (|a| |b|)`. It measures the angle between two vectors and ignores their length: 1 means the same direction, 0 means unrelated. **Normalizing** every vector to length 1 at write time makes cosine equal to a plain dot product. For unit vectors, `‖a − b‖² = 2 − 2·cos(a, b)`, so L2 distance gives the same ranking too. This is why Databricks AI Search, which ranks by L2, tells you to normalize first if you want cosine behavior, and why Voyage returns embeddings that are already normalized.

```python
import heapq
import math

def normalize(v):
    """Scale v to length 1. After this, cosine similarity is just a dot product."""
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v

def cosine(a, b):
    """cos(angle) = a.b / (|a| |b|). 1 = same direction, 0 = unrelated, -1 = opposite."""
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))

def top_k(query, index, k=3):
    """Exact nearest neighbours: score EVERY stored vector and keep the k best.
    Cost is O(N x d) per query, the "full table scan" that ANN indexes avoid."""
    q = normalize(query)                      # normalize the query once
    scored = ((sum(x * y for x, y in zip(q, v)), doc_id) for doc_id, v in index.items())
    return heapq.nlargest(k, scored)          # a heap keeps only k items in memory

# Toy 4-dimensional "embeddings". Real models emit 256 to 3,072 dimensions.
raw = {
    "refund policy":    [0.9, 0.1, 0.0, 0.2],
    "return a product": [0.8, 0.2, 0.1, 0.3],
    "shipping times":   [0.1, 0.9, 0.2, 0.0],
    "API error E-4012": [0.0, 0.1, 0.9, 0.4],
}
index = {doc_id: normalize(v) for doc_id, v in raw.items()}   # normalize at write time

print(round(cosine(raw["refund policy"], raw["shipping times"]), 3))  # 0.209: unrelated
query = [0.9, 0.15, 0.0, 0.1]      # pretend: embed("how do I get my money back?")
for score, doc_id in top_k(query, index, k=2):
    print(f"{score:.3f}  {doc_id}")   # refund policy, then return a product
```

Scores are not probabilities. A 0.8 from one model doesn't mean the same as a 0.8 from another. Rely on ranks, and calibrate any "answer only above X" threshold on your own labeled data.

### Dimensions and Matryoshka embeddings

Dimension drives cost. Ten million chunks × 1,024 dimensions × 4 bytes is about 41 GB of raw float32 before any index overhead, and each comparison costs `O(d)`. **Matryoshka Representation Learning** (Kusupati et al., 2022) trains the model so that the leading 64, 128, 256 and so on dimensions are each a usable embedding on their own, nested like Russian dolls. To shorten a vector, keep the leading dimensions and **re-normalize**. The APIs expose this as `dimensions` on OpenAI's `text-embedding-3` and `output_dimension` on Voyage **(GA)**. **Quantization** is the other lever: int8 is 4× smaller than float32, and binary is 32× smaller, at some cost in accuracy. Both enable a funnel: a cheap pass with short or quantized vectors, then a rescore of the survivors with full ones.

### Exact vs approximate nearest neighbor search

**Exact kNN** (k-nearest-neighbor) search is a full table scan with perfect recall, and pgvector does exactly this until you add an index. For small corpora it is often fast enough, so measure first. At scale, B-trees don't help: there is no useful sort order, and space-partitioning trees stop pruning in hundreds of dimensions. So vector indexes give up exactness. **Approximate nearest neighbor (ANN)** search returns *most* true neighbors much faster. The share it returns is the index's **recall**, and every ANN index has knobs that trade recall for speed. It is the same bargain as `approx_count_distinct`.

**HNSW** (Hierarchical Navigable Small World; Malkov & Yashunin, 2016) is the common default. It works like a skip list built from a graph:

```text
Layer 2 (few nodes, long links)   A ───────────────────────── F
                                  │                           │
Layer 1                           A ───────── C ───────────── F ───────── H
                                  │           │               │           │
Layer 0 (all nodes, short links)  A ── B ──── C ── D ── E ─── F ── G ──── H
                                                                   ▲ query
Enter at the top, hop greedily to whichever neighbor is closer to the query,
drop a layer when no neighbor is closer, repeat. Roughly logarithmic in N.
```

Each node links to about `m` neighbors, and its top layer is drawn at random with exponentially decaying probability, so the upper layers are sparse express lanes. The knobs, with pgvector's defaults, are `m` (16), `ef_construction` (64, build-time candidate list) and `hnsw.ef_search` (40, query-time candidate list). A larger `ef_search` gives higher recall and slower queries. HNSW is memory-hungry and slow to build.

**IVF** (inverted file) runs k-means to cluster the vectors into `lists` partitions. At query time it scans only the `probes` partitions whose centroids are closest. This is partition pruning, the same move as Delta data skipping or Snowflake micro-partition pruning, and it fails the same way: the true neighbor sits just across a boundary you didn't scan. IVF builds faster and uses less memory than HNSW, but it needs data to train its centroids, and they drift as the data changes.

**Product quantization** (PQ; Jégou et al., 2011) compresses the vectors themselves. It splits each vector into `m` sub-vectors and replaces each with a 1-byte ID of its nearest learned centroid. A 1,024-dimension float32 vector (4,096 bytes) with `m = 64` becomes 64 bytes. This is lossy dictionary encoding. FAISS-style "IVF-PQ" combines it with IVF and then rescores the top hits with the full vectors.

**Filters are the trap.** pgvector's docs say it plainly: with approximate indexes, the `WHERE` clause is applied *after* the index scan. If `tenant_id = 42` matches 10% of rows and `ef_search` is 40, you get about 4 rows back. Fixes include iterative index scans (pgvector 0.8.0+), partial indexes, partitioning, or an engine that filters during traversal. This matters for access control in [§09](09-rag.md).

### Vector databases vs extensions

- **Dedicated vector databases** (Pinecone, Weaviate, Qdrant, Milvus, Chroma and others) are built for ANN at scale. They are also one more stateful system to secure and keep in sync.
- **pgvector** adds a `vector` type to Postgres, with the operators `<->` (L2), `<#>` (negative inner product) and `<=>` (cosine distance) and with HNSW and IVFFlat indexes. In exchange you keep transactions, joins and your existing access control.
- **Lakehouse and warehouse search.** *Databricks AI Search* (formerly Vector Search) **(GA)** builds an HNSW index that syncs from a Delta table's change data feed, is governed by Unity Catalog, and supports hybrid keyword-similarity search. *Snowflake* has a `VECTOR(FLOAT, n)` type (up to 4,096 dimensions) with functions such as `VECTOR_COSINE_SIMILARITY`, and *Cortex Search* **(GA)** is a managed service that combines vector search, keyword search and reranking, with refresh behavior that matches Dynamic Tables (`TARGET_LAG`).

The frame that transfers from data engineering: **a vector index is a derived dataset**, a materialized view of your documents. It needs lineage (source rows plus embedding model version), a freshness SLA, delete propagation and a backfill plan. As for the hype, "vector database" looked like a new category in 2023, but most databases have since added vector types, so the choice is now mostly operational.

### Lexical search and BM25

**Lexical search** matches the words themselves, using an **inverted index** (term → list of documents), the structure behind Lucene, Elasticsearch and OpenSearch. Its standard ranking function is **BM25**:

```text
BM25(query, D) = Σ over query terms t:
                 IDF(t) · tf(t,D) · (k1 + 1)  /  ( tf(t,D) + k1 · (1 − b + b · |D| / avgdl) )

IDF(t)   large when t is rare in the corpus ("E-4012"), near 0 for "the"
tf(t,D)  occurrences of t in D, with diminishing returns set by k1 (typically 1.2 to 2.0)
b        length normalization (typically 0.75): long documents don't win by being long
```

Why does it still win on some queries? The mechanism explains it. A dense embedding squeezes a passage into one point, so an error code, SKU, ticket ID or new product name is a tiny, poorly learned part of that point. BM25 gives exactly those rare terms the *largest* weight, needs no training, handles new vocabulary on day one, and can be explained. The BEIR benchmark (Thakur et al., 2021) found that BM25 is "a robust baseline" that dense retrievers often fail to beat outside their training domain.

### Hybrid search with Reciprocal Rank Fusion

**Hybrid search** runs lexical and dense retrieval together and merges the results. You can't simply add the two scores, because BM25 scores are unbounded and cosine scores lie between −1 and 1. **Reciprocal Rank Fusion** (RRF; Cormack, Clarke & Büttcher, 2009) uses only ranks:

```python
def rrf(rankings, k=60):
    """Reciprocal Rank Fusion (Cormack, Clarke & Buettcher, SIGIR 2009).
    rankings: several ranked lists of doc ids, best first (e.g. BM25 and vector).
    A doc at position r in a list earns 1 / (k + r). Raw scores are ignored, so
    unbounded BM25 scores and cosine scores in [-1, 1] never need calibrating."""
    fused = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (k + rank)
    # k=60 damps the gap between rank 1 and rank 2, so agreement across lists
    # matters more than winning any single list outright.
    return sorted(fused.items(), key=lambda item: item[1], reverse=True)

query = "error E-4012 when calling the API"
bm25_hits = ["doc_E4012_runbook", "doc_error_codes", "doc_api_keys", "doc_billing"]
vector_hits = ["doc_api_keys", "doc_auth_overview", "doc_error_codes", "doc_key_rotation"]

for doc_id, score in rrf([bm25_hits, vector_hits])[:4]:
    print(f"{score:.4f}  {doc_id}")
# 0.0323 doc_api_keys, 0.0320 doc_error_codes, 0.0164 doc_E4012_runbook, 0.0161 doc_auth_overview
```

`k = 60` comes from the paper, and it is the value Databricks AI Search uses. Look at the output. The exact-match runbook, found only by BM25, comes *third*, because RRF rewards agreement over a single strong signal. That suits its real job, which is building a high-recall candidate set. Putting the runbook first is the reranker's job.

### Rerankers: bi-encoder vs cross-encoder

Everything so far is a **bi-encoder**: the query and the document are encoded separately and meet only in one dot product. That is scalable, because document vectors are computed once at ingest, but the model never reads the two together. A **cross-encoder** feeds the query and one document through a transformer *together* and outputs a relevance score. Every query token attends to every document token, so it can tell "refunds for digital goods" from "refunds for physical goods". Nothing can be precomputed, though. The Sentence-BERT paper estimates that finding the most similar pair among 10,000 sentences takes about 65 hours with BERT as a cross-encoder and about 5 seconds with SBERT embeddings. Hence the funnel:

```text
millions of chunks ─┬─ BM25 (inverted index) ─┐
                    └─ dense ANN (HNSW) ──────┴─▶ RRF ─▶ ~100-150 candidates  (cheap, for recall)
                                                   ─▶ cross-encoder ─▶ ~5-20  (costly, for precision)
                                                   ─▶ the LLM's context (§09)
```

Anthropic's contextual retrieval experiments ([§09](09-rag.md)) used this shape: the top 150, reranked down to 20.

### Late interaction: ColBERT

**ColBERT** (Khattab & Zaharia, 2020) is the middle ground. It stores one vector *per token* of each document and scores with **MaxSim**: each query token takes its best-matching document token, and the maxima are summed. Document vectors are precomputed, as in a bi-encoder, but matching is token by token, closer to a cross-encoder. The cost is storage that grows with document length. ColPali (2024) applies it to page images ([§07](07-multimodal.md)). BEIR found that reranking and late-interaction models had the best zero-shot quality, "at high computational costs".

### Retrieval metrics: recall@k, MRR, nDCG

You can't improve what you don't measure, and you measure on a sample (P4). Build a labeled set of real queries, each with its relevant document IDs, from logs, from experts, or from LLM-drafted labels checked by humans ([§26](26-evals.md)).

```text
recall@k  = |relevant ∩ top-k| / |relevant|        "is the right stuff in the top k at all?"
MRR       = mean over queries of 1 / rank_of_first_relevant      "how high is the first hit?"
nDCG@k    = Σ_i grade_i / log2(i + 1), divided by the same sum for the ideal ordering
            graded labels (0-3), and putting the BEST results first is rewarded
```

For RAG, **recall@k** on the first stage matters most, because the model can't use a passage it never sees, and a reranker can only reorder what it receives. Use **nDCG** to judge the final ordering after reranking, and **MRR** when one right answer is enough. Don't confuse retrieval recall with ANN index recall. An index can return 99% of the true nearest vectors and still feed you irrelevant passages if the embedding model is wrong for your domain.

## Comparison

**Retrieval methods**

| Method | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| BM25 (lexical) | Inverted index; weights from term rarity and frequency | Exact IDs, rare terms, new jargon; no training; explainable | Vocabulary mismatch | Codes, names, SKUs; always as a baseline |
| Dense bi-encoder | One vector per chunk; nearest neighbors by cosine | Paraphrase, natural-language questions, multilingual | Weak on IDs, negation, numbers; model-specific space | Questions worded differently from the documents |
| Hybrid + RRF | Run both, fuse by rank | Covers both failure modes; no calibration | Two indexes; rewards agreement, not strength | The production default |
| Cross-encoder reranker | Reads query and document together | Highest precision | Per-pair cost at query time | Reordering the top 50 to 150 |
| Late interaction (ColBERT) | One vector per token, MaxSim | Near-reranker quality, precomputed | Large storage, complex serving | Quality-critical with storage to spare |

**Vector index types**

| Index | Mechanism | Build and memory | Recall vs speed | Choose when |
|---|---|---|---|---|
| Flat (exact) | Scan everything | No build | Perfect recall; `O(N·d)` per query | Small corpora; ground truth for testing ANN |
| HNSW | Layered proximity graph, greedy descent | Slow build, memory-heavy | Best general tradeoff | The default |
| IVF | k-means partitions; probe the nearest few | Fast build; needs training data | Misses near boundaries | Large, fairly static data; less memory |
| PQ / IVF-PQ | Sub-vectors stored as 1-byte codes | Very small | Lower; needs a rescore | Billions of vectors; memory-bound |

## What it didn't solve

Search returns ranked *passages*, not answers. A user who asks "how long do refunds take?" wants "14 days, per the refund policy", not ten chunks to read. Someone still has to read the passages, reconcile them when they conflict, write the answer with a citation, and say "I don't know" when the passages don't contain it. That someone is the LLM, and the system that feeds it is retrieval-augmented generation.

→ Next: [§09 Retrieval-Augmented Generation (RAG)](09-rag.md)

## Check your understanding

**Q: Why can't you store embeddings from two different embedding models in the same index?**

Each model learns its own coordinate system, so distances mean something only between vectors from the same model version. A query from model B against documents from model A produces plausible-looking scores that are essentially random. So a model upgrade means re-embedding everything, which is a backfill. The exception is a family deliberately trained into one space, such as Voyage's 4-series, and even then you should verify recall on your own evaluation set.

**Q: Why does BM25 often beat a strong dense embedding model on a query like "E-4012 timeout"?**

A dense model compresses the whole passage into one vector, and a rare token such as an error code is a small, poorly learned part of it. BM25 gives rare terms the highest weight through IDF and requires an exact match, so the one runbook that contains "E-4012" rises to the top. The tradeoff is that BM25 can't handle paraphrase. That is why hybrid search, not either method alone, is the production default.

**Q: HNSW vs IVF: how does each prune the search, and when would you pick IVF?**

HNSW prunes by greedy hops through a layered neighbor graph, which gives an excellent recall/speed tradeoff at the cost of memory and slow builds. IVF prunes like partition pruning: it scans only the clusters closest to the query, and it misses neighbors just across cluster boundaries. Pick IVF, often combined with PQ, for large, fairly static data under memory pressure. Avoid it for fast-changing data, because the centroids go stale.

**Q: Why does Reciprocal Rank Fusion use ranks instead of the retrievers' scores?**

BM25 scores are unbounded and depend on the corpus, while cosine scores lie between −1 and 1, so adding them lets one retriever dominate arbitrarily. RRF sums `1/(k + rank)`, which needs no calibration. The cost is that it ignores how strong a match was and favors documents that both lists found, which is why a reranker usually follows it. A tuned weighted score fusion can beat RRF if you have labeled data to tune with.

**Q: Bi-encoder vs cross-encoder: why not just use the more accurate cross-encoder for everything?**

A cross-encoder reads the query and the document together, so it can't precompute anything and must run a full model pass per (query, document) pair. Over millions of documents that's infeasible: Sentence-BERT estimated about 65 hours versus 5 seconds for a 10,000-sentence search. So bi-encoders and BM25 narrow millions of documents to about 100, and the cross-encoder reorders those. Skip it when the latency budget is tiny or when first-stage ordering already scores well on your evaluation set.

**Q: What would happen if you add `WHERE tenant_id = 42` to an HNSW query in pgvector and that tenant owns 10% of the rows?**

pgvector applies the filter after the approximate index scan. With the default `ef_search` of 40 candidates, only about 4 belong to tenant 42, so you silently get fewer than k results and may miss the best ones. Iterative index scans, a higher `ef_search`, or per-tenant partitions or partial indexes fix it. The same mechanism decides whether access-control filters in RAG cost you answers or leak data.

## Takeaways

- An embedding maps text to a vector so that similar meaning means small distance; search becomes nearest-neighbor lookup.
- Contrastive training defines "similar" by its training pairs: embeddings capture topic, not truth, and they are weak on IDs, numbers and negation.
- Normalize at write time, and cosine, dot product and L2 rankings all agree.
- Vectors are comparable only within one model's space, so changing the model means re-embedding.
- ANN indexes trade a little recall for a lot of speed: HNSW is a graph-shaped skip list, IVF is partition pruning, PQ is lossy dictionary encoding.
- BM25 still wins on rare and exact terms; hybrid search with RRF, then a reranker, is the production default.
- A vector index is a derived dataset: give it lineage, freshness, delete propagation and recall@k evaluation.

## Sources

- Mikolov et al., "Efficient Estimation of Word Representations in Vector Space" (word2vec), Jan 2013: https://arxiv.org/abs/1301.3781
- Reimers & Gurevych, "Sentence-BERT", Aug 2019: https://arxiv.org/abs/1908.10084
- Karpukhin et al., "Dense Passage Retrieval for Open-Domain Question Answering", Apr 2020: https://arxiv.org/abs/2004.04906
- van den Oord, Li & Vinyals, "Representation Learning with Contrastive Predictive Coding" (InfoNCE), Jul 2018: https://arxiv.org/abs/1807.03748
- Kusupati et al., "Matryoshka Representation Learning", May 2022: https://arxiv.org/abs/2205.13147
- Muennighoff et al., "MTEB: Massive Text Embedding Benchmark", Oct 2022: https://arxiv.org/abs/2210.07316
- Malkov & Yashunin, "Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs", Mar 2016: https://arxiv.org/abs/1603.09320
- Jégou, Douze & Schmid, "Product Quantization for Nearest Neighbor Search", IEEE TPAMI 2011: https://ieeexplore.ieee.org/document/5432202
- Johnson, Douze & Jégou, "Billion-scale similarity search with GPUs" (FAISS), Feb 2017: https://arxiv.org/abs/1702.08734
- Robertson & Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond", 2009: https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf
- Thakur et al., "BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models", Apr 2021: https://arxiv.org/abs/2104.08663
- Cormack, Clarke & Büttcher, "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods", SIGIR 2009: https://doi.org/10.1145/1571941.1572114
- Khattab & Zaharia, "ColBERT", Apr 2020: https://arxiv.org/abs/2004.12832
- Faysse et al., "ColPali: Efficient Document Retrieval with Vision Language Models", Jun 2024: https://arxiv.org/abs/2407.01449
- Anthropic, Embeddings guide (Voyage models, `input_type`, Matryoshka, quantization): https://platform.claude.com/docs/en/build-with-claude/embeddings
- Voyage AI, "The Voyage 4 model family: shared embedding space with MoE architecture", Jan 15, 2026: https://blog.voyageai.com/2026/01/15/voyage-4/
- OpenAI, Embeddings guide (`dimensions` parameter): https://developers.openai.com/api/docs/guides/embeddings
- pgvector README (operators, HNSW/IVFFlat, filtering, iterative scans): https://github.com/pgvector/pgvector
- Databricks AI Search (formerly Vector Search), updated Sep 2026: https://docs.databricks.com/aws/en/vector-search/vector-search
- Snowflake Cortex Search: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview
- Snowflake VECTOR data type: https://docs.snowflake.com/en/sql-reference/data-types-vector
