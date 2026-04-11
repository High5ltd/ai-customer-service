# End-to-End Evaluation

Runs **retrieval + generation** in a single pass to assess the full RAG pipeline. The fastest way to get an overall picture of system quality.

---

## Running the Eval

```bash
# Use the default dataset
python -m evals.end_to_end.run_e2e_eval

# Specify a dataset and top-k
python -m evals.end_to_end.run_e2e_eval \
  --dataset evals/datasets/sample_qa.json \
  --top-k 5
```

Reports are written to `evals/reports/e2e_<timestamp>.json`.

---

## Dataset Format

Same format as the retrieval and generation evals:

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

---

## Metrics

The end-to-end eval computes all 8 metrics in one run:

### Retrieval metrics

| Metric | Description |
|--------|-------------|
| `precision_at_k` | Fraction of top-K results that are relevant |
| `recall_at_k` | Fraction of relevant chunks that were found |
| `hit_rate` | At least one relevant chunk in top-K (binary) |
| `mrr` | Reciprocal rank of the first relevant chunk |
| `ndcg` | Ranking quality, weighted by position |

See details: [EVAL_RETRIEVAL.md](./EVAL_RETRIEVAL.md)

### Generation metrics

| Metric | Description |
|--------|-------------|
| `faithfulness` | Does the answer hallucinate facts not in context? |
| `answer_relevance` | Does the answer stay on topic? |
| `citation_precision` | Are the cited sources actually relevant? |

See details: [EVAL_GENERATION.md](./EVAL_GENERATION.md)

---

## Output

### Console (real-time)

```
[q1] retrieval={'precision_at_k': 0.4, 'recall_at_k': 1.0, 'hit_rate': 1.0, 'mrr': 0.5, 'ndcg': 0.7654, 'k': 5} | generation={'faithfulness': 0.95, 'answer_relevance': 0.88, 'citation_precision': 1.0}
[q2] ...

=== End-to-End Aggregate (n=10) ===
{
  "retrieval": {
    "precision_at_k": 0.38,
    "recall_at_k": 0.92,
    "hit_rate": 0.95,
    "mrr": 0.67,
    "ndcg": 0.72,
    "k": 5
  },
  "generation": {
    "faithfulness": 0.865,
    "answer_relevance": 0.910,
    "citation_precision": 0.780
  },
  "n": 10
}

Report saved → evals/reports/e2e_20240112_144000.json
```

### Report JSON

```json
{
  "timestamp": "2024-01-12T14:40:00Z",
  "dataset": "evals/datasets/sample_qa.json",
  "top_k": 5,
  "aggregate": {
    "retrieval": {
      "precision_at_k": 0.38,
      "recall_at_k": 0.92,
      "hit_rate": 0.95,
      "mrr": 0.67,
      "ndcg": 0.72,
      "k": 5
    },
    "generation": {
      "faithfulness": 0.865,
      "answer_relevance": 0.910,
      "citation_precision": 0.780
    },
    "n": 10
  },
  "per_question": [
    {
      "id": "q1",
      "question": "...",
      "answer": "...",
      "retrieval": { "precision_at_k": 0.4, ... },
      "generation": { "faithfulness": 0.95, ... }
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
embed_text()                       ← OpenAI Embeddings
    │
    ▼
searcher.search(top_k)             ← Qdrant
    │
    ▼
reranker.rerank()                  ← filter + sort
    │
    ├── compute_retrieval_metrics() ← scored immediately
    │
    ▼
build_context()
    │
    ▼
prompts.build_messages()
    │
    ▼
llm_client.complete()              ← OpenAI Chat
    │
    ▼
response_parser.extract_used_citations()
    │
    ▼
compute_generation_metrics()       ← 2 LLM judge calls + 1 computed
```

**Cost per question:** 2 API calls (embedding + generation) + 2 judge calls = **4 OpenAI API calls**.

---

## Choosing the Right Eval

| | Retrieval Eval | Generation Eval | End-to-End Eval |
|--|----------------|-----------------|-----------------|
| Purpose | Search quality only | LLM answer quality only | Full pipeline snapshot |
| API calls / question | 1 (embedding) | 4 (embed + gen + 2 judge) | 4 (embed + gen + 2 judge) |
| Metrics | 5 retrieval | 3 generation | 8 total |
| When to use | Tuning chunking / embedding / top-k | Tuning prompts or chat model | Overall reporting, CI gate |

---

## Diagnosing Issues from Results

### Good retrieval, poor generation
```
hit_rate:     0.95   ← search is finding the right chunks
faithfulness: 0.60   ← LLM is still hallucinating
```
The problem is in the prompt or the model, not in the search.

### Poor retrieval dragging down generation
```
recall_at_k:      0.40   ← system misses relevant chunks
faithfulness:     0.85   ← LLM is honest with what it has
answer_relevance: 0.50   ← but the context is incomplete
```
Fix retrieval first (chunking, embedding model, top-k, min-score).

### Healthy system
```
hit_rate:           0.95
recall_at_k:        0.85
faithfulness:       0.92
answer_relevance:   0.90
citation_precision: 0.88
```
