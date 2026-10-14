# 02. How an LLM Works

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

This section starts the model thread. In 2017 the transformer made it possible to train on text in parallel at massive scale. In 2020 GPT-3 (175B parameters) showed that a model trained only to predict the next token could do new tasks from a few examples in the prompt. On November 30, 2022, ChatGPT paired InstructGPT's human-feedback training with a chat interface, and LLMs went mainstream. [§01](01-first-principles.md) stated the principles; this section shows the mechanism behind P1, P4 and P5.

## Why this exists

Every language task used to need its own model and its own labeled dataset. The way out was a **self-supervised** objective, where the text supplies its own labels: hide the next word and predict it. All written text becomes training data, and predicting it well forces a model to absorb grammar, facts, and the patterns of code and math.

**Recurrent neural networks (RNNs)**, the earlier design, read one word at a time. That wasted GPU parallelism and let distant context fade. The transformer processes all positions at once during training, so labs could spend far more compute on far more text, and compute turned out to matter most (P12).

## How it works (under the hood)

### The pipeline in one picture

```text
"How many r's in strawberry?"
   │ tokenizer (fixed, built before training)
   ▼
[4438, 1690, 436, 596, 304, 73700, 30]    ← token IDs (OpenAI cl100k_base)
   │ embedding table: one learned vector per ID
   ▼
x1 x2 x3 x4 x5 x6 x7                      ← one vector per token, plus position
   │ N stacked transformer layers (attention + MLP)
   ▼
h7 → unembedding → logits → softmax       ← P(next token): the whole output (P1)
   │ sampling picks one token
   ▼
append it and run the full stack again    ← one forward pass per generated token
```

### Tokens and tokenization

A **token** is a chunk of text from a fixed vocabulary: a word with its leading space, a fragment, a punctuation mark or a byte. The model sees only integer **token IDs**, never characters. Current vocabularies hold roughly 100k–200k entries (Llama 3: 128k). Most tokenizers use **byte-pair encoding (BPE)** (Sennrich et al., 2015), built once by counting, before model training:

1. Start from single bytes, so any string can be encoded.
2. Count every adjacent pair of symbols across a large corpus.
3. Merge the most frequent pair into a new vocabulary entry. Repeat until the vocabulary reaches its target size.

On a toy corpus of nine words, the first merges and the result look like this:

```text
merge 1: 'a' + 'w'     merge 2: 'r' + 'aw'     merge 3: 'e' + 'r'
merge 4: 's' + 't'     merge 5: 'st' + 'raw'   merge 6: 'b' + 'er'
strawberry  →  straw | ber | r | y
```

**Consequences:**
- **Letter questions are hard.** In OpenAI's `cl100k_base` and `o200k_base`, " strawberry" mid-sentence is one token (ID 73700 above). To count its r's, the model must have memorized that token's spelling, because the letters aren't in its input. Reversing strings fails for the same reason. Spelling the word out first puts the letters into the context and usually fixes it.
- **One word, several encodings.** With no leading space, `cl100k_base` splits "strawberry" into `str` `aw` `berry`, and "Strawberry" into `Str` `aw` `berry`. The model must learn that these unrelated ID sequences mean the same word.
- **Tokens are the unit of cost and limits (P10).** Ratios vary by tokenizer and language. Anthropic says 1M tokens is about 555k words on the tokenizer introduced with Claude Opus 4.7, versus about 750k before it. Count with the provider's endpoint (Anthropic `POST /v1/messages/count_tokens` **(GA)**) rather than guessing from word counts.

### Embeddings

The first layer is an **embedding table**, a learned matrix with one row per vocabulary entry, so token 73700 becomes a vector of a few thousand numbers (8,192 in Llama 3 70B). It works like a lookup join from a key to a dense feature vector whose features were learned, not designed. Training puts tokens used in similar contexts near each other (the word2vec effect, Mikolov et al. 2013), and each layer then rewrites the vectors in context, so "river bank" and "bank account" diverge. Search embedding models, which turn a whole passage into one vector, are a separate tool ([§08](08-embeddings-and-search.md)).

### The transformer and self-attention

A transformer is a stack of identical **layers** (80 in Llama 3 70B). In each, **self-attention** lets every token gather information from other tokens, then a **feed-forward network (MLP)** processes each token separately and holds most of the weights (about four-fifths per layer, by Llama 3 70B's published dimensions). A **residual connection** adds each layer's result onto its input, so every position carries a running summary that each layer refines.

**Q, K, V.** For each token, attention multiplies its vector by three learned matrices:
- a **query (Q)**: what this token is looking for;
- a **key (K)**: what it offers to tokens that are searching;
- a **value (V)**: what it hands over when selected.

A token's query is dot-multiplied with other tokens' keys and scaled by √d, where d is the vector size. Softmax turns these scores into weights, and the output is the weighted average of the values:

```text
Attention(Q, K, V) = softmax(Q·Kᵀ / √d) · V          (Vaswani et al., 2017)
```

It is a soft join: every row matches every other row with a weight between 0 and 1. In "The trophy didn't fit in the suitcase because it was too big", the query at "it" can weight the key at "trophy" heavily. Many **heads** run in parallel (64 in Llama 3 70B), each learning its own pattern.

**The causal mask.** In a **decoder-only** model, the GPT-style design that open models such as Llama also use, a token can attend only to itself and earlier tokens. It can't see the future it is learning to predict. This is why earlier tokens' keys and values never change as new tokens arrive, which makes the KV cache possible ([§03](03-inference.md)).

**Why the square of the length.** Every token scores against every earlier token: about n²/2 scores per head per layer. That is half a million for 1,000 tokens and five billion for 100,000. Doubling a long context roughly quadruples attention work, while per-token MLP work only doubles. FlashAttention (Dao et al., 2022) cuts the memory traffic, but the n² arithmetic remains. This is the mechanism behind P3's "attention budget".

**Positional information.** A dot product doesn't know where its tokens sit, so without help "dog bites man" and "man bites dog" would look nearly alike. The original transformer added sine-wave patterns to the embeddings. Most open models now use **rotary position embeddings (RoPE)**, which rotate queries and keys by position so scores depend on relative distance (Llama 3 raised RoPE's base frequency to 500,000 for longer contexts). Models are reliable only at lengths they were trained on, so a longer window takes training; it isn't a config flag.

**The output.** After the last layer, the final vector is multiplied by an **unembedding** matrix. That gives a **logit**, a raw score, for every vocabulary entry, and softmax turns the logits into probabilities.

### Pretraining: next-token prediction (P1)

**Pretraining** is the first and costliest training stage. The model reads trillions of tokens. At every position, the loss is the **cross-entropy**: minus the log-probability it gave to the token that actually came next. Gradient descent nudges every weight to make that token slightly likelier. With the causal mask, one pass over a 2,048-token sequence gives 2,048 predictions to learn from in parallel.

Nothing here says "be truthful" or "answer questions", only "model how text continues". Capability is a side effect of compression: to predict "Paris" after "The capital of France is", the model must store the fact. Errors and confident nonsense are patterns of text too. GPT-3 showed the payoff of scale: it could do tasks described in the prompt, with no weight updates. This **in-context learning** is why prompting works ([§05](05-api-and-prompting.md)).

### Scaling laws, briefly

Kaplan et al. (2020) found that loss falls along a smooth **power law** as parameters, data and compute grow, over more than seven orders of magnitude. Chinchilla (Hoffmann et al., 2022) refined the recipe: for a fixed compute budget, scale model size and training tokens together. Their 70B model, trained on about 1.4T tokens (four times Gopher's data), beat the 280B Gopher and the 175B GPT-3.

Predictable gains justified enormous training runs (P12). A power law also means diminishing returns. Because small models are cheaper to serve ([§03](03-inference.md)), labs now often train well past the Chinchilla ratio, and since 2024 scaling has also moved to post-training and to answer-time compute ([§04](04-reasoning-models.md)).

### Base models vs chat models

A **base model** is the raw pretrained model, and it continues documents: asked "What is the capital of France?", it may answer or may write three more quiz questions. A **chat model** (instruct model) has been post-trained to follow a conversation format. The conversation is still one sequence: the server renders your messages into a template with turn markers, and the model continues after the assistant marker.

```text
<|system|>You are a concise assistant.<|end|>
<|user|>What is the capital of France?<|end|>
<|assistant|>        ← generation starts here, one token at a time
```

The markers are illustrative; each family has its own template, hidden behind the API's `messages` list. System prompts, tool calls and agents are all choices about what goes into this sequence (P1). Hosted APIs serve chat models; base models appear mainly in open-weights releases, as starting points for fine-tuning ([§29](29-adapting-models.md)).

### Post-training

**Post-training** uses a small fraction of the compute but decides most of the behavior you see.

- **SFT (supervised fine-tuning), or instruction tuning:** the same next-token loss on curated (prompt, ideal response) pairs. It teaches format and tone, but it can only imitate, and expert demonstrations are expensive.
- **RLHF (reinforcement learning from human feedback):** the InstructGPT recipe (Ouyang et al., 2022). After SFT, humans rank outputs, a **reward model** learns to predict those rankings, and RL (PPO) pushes the model toward higher reward while keeping it close to the SFT model. Labelers preferred the 1.3B InstructGPT to the 175B GPT-3. ChatGPT applied the method to a GPT-3.5 base.
- **DPO (Direct Preference Optimization)** (Rafailov et al., 2023): a classification-style loss on (chosen, rejected) pairs. There is no reward model and no RL loop, so it is stable and cheap.
- **Constitutional AI / RLAIF (RL from AI feedback)** (Anthropic, Bai et al., 2022): written principles replace human harm labels. The model critiques and revises its own answers, then AI preference labels train the reward signal for RL.
- **RL with verifiable rewards** (unit tests, answer keys) drives reasoning models. See [§04](04-reasoning-models.md).

Post-training shapes behavior (format, tone, refusals, tool-call syntax) and adds little knowledge (P5: "fine-tune for behavior"). It has side effects. Sharma et al. (Anthropic, 2023) found that humans and preference models sometimes prefer convincing, agreeable answers over correct ones, which produces **sycophancy**. OpenAI reported that the pretrained GPT-4 was well calibrated on an MMLU subset and that post-training "hurts calibration significantly".

### Sampling (P4)

Something has to turn the distribution into a token. That rule is the **decoding strategy**:
- **Greedy** always takes the top token. It is deterministic in principle, but bland and prone to loops.
- **Temperature** divides the logits by T before softmax. T < 1 sharpens the distribution, T > 1 flattens it, and T → 0 is greedy.
- **Top-k** (Fan et al., 2018) keeps the k likeliest tokens. A fixed k ignores how peaked the distribution is.
- **Top-p (nucleus)** (Holtzman et al., 2019) keeps the smallest set of tokens whose probabilities reach p, so the candidate set adapts to the model's confidence.

```python
import math
import random

def softmax(logits, temperature=1.0):
    """Turn raw scores (logits) into probabilities that sum to 1."""
    scaled = [x / temperature for x in logits]  # temperature rescales before exp()
    m = max(scaled)                             # subtract the max for numerical stability
    exps = [math.exp(x - m) for x in scaled]
    total = sum(exps)
    return [e / total for e in exps]

def sample(tokens, logits, temperature=1.0, top_k=None, top_p=None, rng=random):
    if temperature == 0:                        # greedy: always take the argmax
        return tokens[logits.index(max(logits))]
    ranked = sorted(zip(tokens, softmax(logits, temperature)),
                    key=lambda tp: tp[1], reverse=True)
    if top_k:                                   # top-k: keep only the k likeliest tokens
        ranked = ranked[:top_k]
    if top_p:                                   # top-p: smallest set whose mass reaches p
        kept, mass = [], 0.0
        for tok, p in ranked:
            kept.append((tok, p))
            mass += p
            if mass >= top_p:
                break
        ranked = kept
    toks, probs = zip(*ranked)
    return rng.choices(toks, weights=probs)[0]  # weights are renormalized automatically

# Toy logits for the token after "The capital of France is"
tokens = [" Paris", " a", " the", " located", " Lyon"]
logits = [6.0, 3.5, 3.0, 2.0, 0.5]
for t in (0.5, 1.0, 2.0):
    print(f"T={t}:", [round(p, 3) for p in softmax(logits, t)])
rng = random.Random(0)
print("greedy:", sample(tokens, logits, temperature=0))
print("T=1.5, top_p=0.9:", [sample(tokens, logits, 1.5, top_p=0.9, rng=rng) for _ in range(8)])
```

At T=0.5, " Paris" gets 0.991 of the probability; at T=2.0, only 0.585. Eight samples at T=1.5, top-p 0.9 return " a" three times. Same logits, different decoding rule.

**What hosted APIs let you change (Oct 2026).** Frontier APIs increasingly own these knobs:
- **Anthropic** returns a 400 error for non-default `temperature`, `top_p` or `top_k` on every model released since Claude Opus 4.7, which covers all current model IDs.
- **OpenAI**'s guide for its latest models says to remove `temperature` and `top_p` when reasoning effort is not `none`.
- **Gemini** silently ignores all three on Gemini 3.6 Flash and newer.
- **Open-weights servers** such as vLLM still expose them.

`temperature = 0` never guaranteed identical outputs either: batching changes the floating-point arithmetic ([§03](03-inference.md)). Steer with prompts and test with evals ([§26](26-evals.md)).

### The context window

The **context window** is the most tokens one call can hold: input plus generated output. GPT-3 had 2,048. As of Oct 2026, Claude Opus 5.5, Sonnet 5.5 and Haiku 5.5 have 1M tokens with up to 128K output **(GA)**. It is finite for three reasons: attention grows with n², cached keys and values grow with n ([§03](03-inference.md)), and models are reliable only at trained lengths. It is the model's only working memory, and every turn re-sends the conversation (P2).

Bigger isn't free (P3). "Lost in the Middle" (Liu et al., 2023) found accuracy highest when relevant information sits at the start or end of the context, and significantly lower in the middle. Chroma's "Context Rot" (2025) tested 18 models and found that performance degrades as input grows, even on simple tasks. The advertised window is a hard limit; the useful window is smaller.

### Why hallucination happens (P1, P5)

A **hallucination** is fluent, confident output that is false or unsupported. It follows from the mechanism:
1. **There is no "unknown" state.** The model always emits a distribution, and sampling always emits a token. Nothing checks claims against the world.
2. **Rare facts can't be learned statistically.** Kalai et al. (OpenAI, 2025) show that for patternless facts such as birthdays, the post-pretraining hallucination rate is at least the share of facts seen exactly once in training. If 20% of birthdays appear once, expect at least 20% errors.
3. **Benchmarks reward guessing.** Most evaluations score "I don't know" like a wrong answer, so models learn to guess.
4. **Weights are lossy and unsourced (P5).** The model can't tell a remembered fact from a reconstructed one.
5. **Generation commits.** Once a wrong token is sampled, the rest of the answer is conditioned on it and fluently justifies it.

The fixes live outside the model: ground facts in context with citations ([§09](09-rag.md)), allow abstention, verify with a separate checker (P8), and measure with evals (P4). In fiction or brainstorming, invention is the job.

### The knowledge cutoff

The weights know nothing after the training data ends (P5). Anthropic publishes two dates per model:
- the **reliable knowledge cutoff**: the date through which knowledge is most extensive and reliable;
- the broader **training data cutoff**.

Both are June 2026 for the current Opus, Sonnet and Haiku. They can differ because the web takes time to write about events, so the last months before a cutoff are thinly covered. Models ship months after their cutoff and stay in service long after, and they don't know today's date unless the context says so (P2). For anything recent or private, ground at runtime ([§09](09-rag.md), [§10](10-tool-use.md)).

## Comparison

| Training stage | How it works | Strength | Weakness | When used |
|---|---|---|---|---|
| Pretraining | Next-token loss on trillions of tokens | Broad knowledge; no labels | Hugely expensive; a continuer, not an assistant | Once per model |
| SFT | Next-token loss on prompt → ideal response pairs | Simple; teaches format fast | Only imitates demonstrations | First post-training step; custom fine-tunes |
| RLHF | Reward model from human rankings, then PPO | Learns from cheap comparisons | Complex; reward hacking, sycophancy | Frontier chat models |
| DPO | Loss directly on chosen/rejected pairs | No reward model or RL loop | Fixed offline preference data | Open models, fine-tuning services |
| RLAIF / Constitutional AI | AI critiques and preferences from written principles | Scales feedback; explicit rules | Inherits the judge's blind spots | Harmlessness, scalable feedback |

| Decoding | How it works | Strength | Weakness | When to choose |
|---|---|---|---|---|
| Greedy | Argmax token | Simple; repeatable in principle | Bland; loops | Short extraction, where allowed |
| Temperature | Logits scaled by 1/T | One focus/variety dial | High T admits tail nonsense | Creative vs focused output |
| Top-k | Keep the k likeliest | Cuts the tail cheaply | Ignores distribution shape | Simple self-hosted setups |
| Top-p | Keep mass ≥ p | Adapts to confidence | Still varies | General sampling on self-hosted models |
| Vendor-fixed | Provider sets sampling | Tuned for the model | No knob | Frontier reasoning APIs (Oct 2026) |

## What it didn't solve

The model writes fluently and follows instructions, but every generated token costs a full pass through billions of weights plus attention over the whole context, and tokens come out one at a time. That makes latency and price first-class engineering problems (P10): output is slower and pricier than input, long contexts cost more, and caching helps, all for mechanical reasons.

→ Next: [§03 Inference Under the Hood](03-inference.md)

## Check your understanding

**Q: Why does an LLM struggle to count the r's in "strawberry" when it can write a sonnet about strawberries?**

The tokenizer turns " strawberry" into one or a few IDs, so the letters never reach the model, and it must recall the spelling of a token as a memorized fact. So character-level tasks are unreliable. Subword tokens are a deliberate tradeoff: they keep sequences short, which matters under n² attention. The problem goes away once the letters are in context, for example when the model spells the word out or uses a code tool.

**Q: What would happen if you doubled an already long prompt?**

Attention work grows with the square of the length, so it roughly quadruples while MLP work doubles. You pay more, wait longer and dilute attention (P3). FlashAttention reduces memory traffic but not the n² math. For short prompts the MLP dominates, so the square law matters mainly at tens of thousands of tokens.

**Q: Base model vs chat model: which would you call to classify support tickets?**

A chat model. It is post-trained to follow instructions and formats, while a base model just continues documents and needs careful few-shot framing. The tradeoff is post-training side effects such as sycophancy and weaker calibration. Use a base model when you plan to fine-tune it yourself.

**Q: Why might an RLHF-trained model agree with a user's incorrect claim?**

Its reward model learned from human preferences, and people often prefer agreement. RL then optimizes for whatever scores well, including agreeableness. The same optimization produces the helpfulness you want, so you can't simply remove it. Don't treat the model's agreement as verification: use a separate checker (P8) and evals.

**Q: What would happen if you set temperature to 0 and expected identical outputs?**

Greedy decoding is deterministic only if the logits are bit-identical, and shared servers batch requests in ways that change the floating-point math, so near-ties can flip. Many current hosted models also reject non-default temperature. Write statistical evals, not exact-match tests (P4). Exact reproducibility requires infrastructure you control.

**Q: Fine-tuning vs putting facts in the prompt: which should you use to give the model your product catalog?**

Put the facts in context. Fine-tuning stores facts lossily, without sources, and goes stale when the catalog changes (P5). Retrieval keeps facts fresh and citable, at the cost of input tokens per call. Fine-tune for consistent format or behavior, not as a database.

## Takeaways

- An LLM maps tokens to a next-token distribution; everything else is what you feed it and what you do with the output (P1).
- Models see token IDs, not characters, and tokens are the unit of price and limits.
- Attention lets each token pull from earlier tokens, and its cost grows with the square of the length.
- Pretraining yields knowledge through compression; post-training (SFT, RLHF, DPO, RLAIF) shapes behavior.
- Output is sampled, and frontier APIs increasingly fix sampling settings; measure with evals (P4).
- The context window is the only working memory, and quality degrades before it fills (P2, P3).
- Hallucination follows from the objective and its incentives; reduce it with grounding and verification (P5, P8).
- The weights stop at the cutoff, and the model doesn't know today's date unless you tell it.

## Sources

- Vaswani et al., "Attention Is All You Need" (2017): https://arxiv.org/abs/1706.03762
- Brown et al., GPT-3 (2020): https://arxiv.org/abs/2005.14165
- Ouyang et al., InstructGPT (2022): https://arxiv.org/abs/2203.02155
- OpenAI, "Introducing ChatGPT" (2022): https://openai.com/index/chatgpt/
- Rafailov et al., DPO (2023): https://arxiv.org/abs/2305.18290
- Bai et al., Constitutional AI (2022): https://arxiv.org/abs/2212.08073
- Kaplan et al., scaling laws (2020): https://arxiv.org/abs/2001.08361
- Hoffmann et al., Chinchilla (2022): https://arxiv.org/abs/2203.15556
- Sennrich et al., BPE for NMT (2015): https://arxiv.org/abs/1508.07909
- OpenAI tiktoken (token examples): https://github.com/openai/tiktoken
- Mikolov et al., word2vec (2013): https://arxiv.org/abs/1301.3781
- Su et al., RoPE (2021): https://arxiv.org/abs/2104.09864
- Dao et al., FlashAttention (2022): https://arxiv.org/abs/2205.14135
- Llama Team, "The Llama 3 Herd of Models" (2024): https://arxiv.org/abs/2407.21783
- Fan et al., top-k sampling (2018): https://arxiv.org/abs/1805.04833
- Holtzman et al., nucleus sampling (2019): https://arxiv.org/abs/1904.09751
- Sharma et al., sycophancy (2023): https://arxiv.org/abs/2310.13548
- OpenAI, GPT-4 Technical Report (2023): https://arxiv.org/abs/2303.08774
- Kalai et al., "Why Language Models Hallucinate" (2025): https://arxiv.org/abs/2509.04664
- Liu et al., "Lost in the Middle" (2023): https://arxiv.org/abs/2307.03172
- Chroma, "Context Rot" (2025): https://research.trychroma.com/context-rot
- Thinking Machines Lab, "Defeating Nondeterminism in LLM Inference" (2025): https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
- Anthropic, Models overview: https://platform.claude.com/docs/en/about-claude/models/overview
- Anthropic, Opus 5.5 migration guide: https://platform.claude.com/docs/en/models/opus-5-5/migration-guide
- Anthropic, Sonnet 5.5 migration guide: https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide
- Anthropic, Token counting: https://platform.claude.com/docs/en/build-with-claude/token-counting
- OpenAI, latest-model guide: https://developers.openai.com/api/docs/guides/latest-model
- Google, Gemini `generateContent` reference: https://ai.google.dev/api/generate-content
