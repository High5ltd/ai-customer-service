# Retrieval Evaluation

Measures the quality of the **search step** in the RAG pipeline: given a question, does the system retrieve the correct chunks?

---

## Running the Eval

```bash
# Use the default dataset
python -m evals.retrieval.run_retrieval_eval

# Specify a dataset and top-k
python -m evals.retrieval.run_retrieval_eval \
  --dataset evals/datasets/sample_qa.json \
  --top-k 5
```

Reports are written to `evals/reports/retrieval_<timestamp>.json`.

---

## Dataset Format

A JSON array of objects:

```json
[
  {
    "id": "q1",
    "question": "What is the refund policy?",
    "relevant_chunk_ids": [
      "3f2a1b00-...__2",
      "3f2a1b00-...__3"
    ]
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier for the question |
| `question` | `str` | The user question |
| `relevant_chunk_ids` | `list[str]` | Ground-truth chunk IDs, format: `{document_id}__{chunk_index}` |

> **Note:** The separator in `chunk_id` is `__` (double underscore), distinct from the Qdrant point ID format `{doc_id}_{chunk_index}` (single underscore). See `evals/utils.py:make_chunk_id`.

---

## Metrics

### Precision@K
> Of the top-K results returned, what fraction are relevant?

```
Precision@K = (relevant chunks in top-K) / K
```

- `1.0` — every result is relevant
- `0.0` — no relevant results

### Recall@K
> Of all relevant chunks, what fraction did the system find?

```
Recall@K = (relevant chunks in top-K) / (total relevant chunks)
```

- `1.0` — all relevant chunks were retrieved
- `0.0` — none were found

### Hit Rate
> Did at least one relevant chunk appear in the top-K?

```
Hit Rate = 1.0 if any relevant chunk is in top-K, else 0.0
```

Binary metric. The minimum bar for a useful retrieval.

### MRR (Mean Reciprocal Rank)
> How high up is the first relevant chunk ranked?

```
MRR = 1 / (rank of the first relevant chunk)
```

| First relevant chunk at rank | MRR |
|-----------------------------|-----|
| 1 | 1.000 |
| 2 | 0.500 |
| 3 | 0.333 |
| Not found | 0.000 |

### NDCG (Normalized Discounted Cumulative Gain)
> Are the relevant chunks ranked near the top?

Compares the actual ranking to the ideal ranking (all relevant chunks first).

```
DCG  = Σ relevance(i) / log2(rank + 1)
IDCG = maximum achievable DCG
NDCG = DCG / IDCG
```

- `1.0` — perfect ranking
- `0.0` — worst possible ranking

---

## Output

### Console (real-time)

```
[q1] {'precision_at_k': 0.4, 'recall_at_k': 1.0, 'hit_rate': 1.0, 'mrr': 0.5, 'ndcg': 0.7654, 'k': 5}
[q2] {'precision_at_k': 0.2, ...}

=== Retrieval Aggregate (n=10) ===
{
  "precision_at_k": 0.3800,
  "recall_at_k": 0.9200,
  "hit_rate": 0.9500,
  "mrr": 0.6700,
  "ndcg": 0.7200,
  "k": 5,
  "n": 10
}

Report saved → evals/reports/retrieval_20240112_143022.json
```

### Report JSON

```json
{
  "timestamp": "2024-01-12T14:30:22Z",
  "dataset": "evals/datasets/sample_qa.json",
  "top_k": 5,
  "aggregate": {
    "precision_at_k": 0.38,
    "recall_at_k": 0.92,
    "hit_rate": 0.95,
    "mrr": 0.67,
    "ndcg": 0.72,
    "k": 5,
    "n": 10
  },
  "per_question": [
    {
      "id": "q1",
      "question": "...",
      "retrieved_chunk_ids": ["doc1__2", "doc1__3"],
      "relevant_chunk_ids": ["doc1__2"],
      "metrics": { "precision_at_k": 0.4, ... }
    }
  ]
}
```

---

## Internal Pipeline

```
question
    │
    ▼
embed_text()         ← OpenAI Embeddings API
    │
    ▼
searcher.search()    ← Qdrant vector search (top_k)
    │
    ▼
reranker.rerank()    ← filter by min_score, deduplicate, sort
    │
    ▼
compute_retrieval_metrics()
```

**Settings that affect retrieval:**

| Variable | Default | Effect |
|----------|---------|--------|
| `RETRIEVAL_TOP_K` | `5` | Number of results fetched from Qdrant |
| `RETRIEVAL_MIN_SCORE` | `0.4` | Minimum similarity score; chunks below this are dropped |

---

## Score Benchmarks

| Metric | Good | Acceptable | Needs work |
|--------|------|------------|------------|
| Hit Rate | > 0.90 | 0.70 – 0.90 | < 0.70 |
| Recall@K | > 0.80 | 0.60 – 0.80 | < 0.60 |
| MRR | > 0.70 | 0.50 – 0.70 | < 0.50 |
| NDCG | > 0.75 | 0.55 – 0.75 | < 0.55 |

---

## Improving Retrieval

| Symptom | What to try |
|---------|-------------|
| Low recall | Increase `RETRIEVAL_TOP_K` |
| Good recall, low precision | Raise `RETRIEVAL_MIN_SCORE` |
| Low scores across the board | Reduce `CHUNK_SIZE` for more granular chunks |
| Context cut off at boundaries | Increase `CHUNK_OVERLAP` |
| Weak semantic matching | Switch to `text-embedding-3-large` (3072 dimensions) |
