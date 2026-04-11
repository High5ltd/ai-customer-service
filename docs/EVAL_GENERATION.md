# Generation Evaluation

Measures the quality of the **answer generation step** in the RAG pipeline: does the LLM answer faithfully, stay on topic, and cite the right sources?

---

## Running the Eval

```bash
# Use the default dataset
python -m evals.generation.run_generation_eval

# Specify a dataset
python -m evals.generation.run_generation_eval \
  --dataset evals/datasets/sample_qa.json
```

Reports are written to `evals/reports/generation_<timestamp>.json`.

---

## Dataset Format

Same format as the retrieval eval:

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

`relevant_chunk_ids` is used to compute `citation_precision` — checking whether the LLM cited the correct sources.

---

## Metrics

All three metrics use **LLM-as-judge** (an additional OpenAI call scores each answer), returning a value between `0.0` and `1.0`.

### Faithfulness
> Is every claim in the answer supported by the retrieved context?

The judge is asked: "Does this answer contain only information from the context, or does it introduce facts not present there?"

```
1.0 — every statement in the answer is grounded in the context
0.0 — the answer introduces information not in the context (hallucination)
```

This is the most critical metric for detecting hallucination.

### Answer Relevance
> Does the answer actually address the question?

The judge is asked: "Does this answer directly and completely address the question?"

```
1.0 — the answer is directly on-topic and complete
0.0 — the answer is off-topic or doesn't address the question
```

### Citation Precision
> Are the chunks cited in the answer actually relevant?

Computed statistically (no LLM call needed):

```
Citation Precision = |cited_chunks ∩ relevant_chunks| / |cited_chunks|
```

- `1.0` — every cited chunk is a ground-truth relevant chunk
- `0.0` — no cited chunk is relevant, or nothing was cited

Citations are detected by `response_parser.extract_used_citations()`, which looks for `[N]` patterns in the answer and maps them back to context citations.

---

## Output

### Console (real-time)

```
[q1] {'faithfulness': 0.95, 'answer_relevance': 0.88, 'citation_precision': 1.0}
[q2] {'faithfulness': 0.72, 'answer_relevance': 0.91, 'citation_precision': 0.5}

=== Generation Aggregate (n=10) ===
{
  "faithfulness": 0.8650,
  "answer_relevance": 0.9100,
  "citation_precision": 0.7800,
  "n": 10
}

Report saved → evals/reports/generation_20240112_143500.json
```

### Report JSON

```json
{
  "timestamp": "2024-01-12T14:35:00Z",
  "dataset": "evals/datasets/sample_qa.json",
  "aggregate": {
    "faithfulness": 0.865,
    "answer_relevance": 0.910,
    "citation_precision": 0.780,
    "n": 10
  },
  "per_question": [
    {
      "id": "q1",
      "question": "...",
      "answer": "The LLM answer...",
      "cited_chunk_ids": ["doc1__2", "doc1__3"],
      "metrics": {
        "faithfulness": 0.95,
        "answer_relevance": 0.88,
        "citation_precision": 1.0
      }
    }
  ]
}
```

---

## Internal Pipeline

```
question
    │
    ├── embed_text() → vector
    │       │
    │       ▼
    │   searcher.search() → list[SearchResult]
    │       │
    │       ▼
    │   reranker.rerank() → list[SearchResult]
    │       │
    │       ▼
    │   build_context() → RetrievalContext
    │
    ├── prompts.build_messages(question, context)
    │       │
    │       ▼
    │   llm_client.complete() → answer
    │       │
    │       ▼
    │   response_parser.extract_used_citations() → cited chunks
    │
    └── compute_generation_metrics()
            ├── _judge_score(FAITHFULNESS_PROMPT)   [LLM call]
            ├── _judge_score(RELEVANCE_PROMPT)      [LLM call]
            └── citation_precision                  [computed]
```

**Cost note:** Each question requires **3 LLM calls** (1 generate + 2 judge). A 100-question dataset costs ~300 LLM calls.

---

## Relevant Configuration

| Variable | Default | Effect |
|----------|---------|--------|
| `OPENAI_CHAT_MODEL` | `gpt-4o` | Model used to generate answers |
| `RETRIEVAL_TOP_K` | `5` | Number of chunks passed as context |
| `RETRIEVAL_MIN_SCORE` | `0.4` | Chunks below this score are excluded from context |

---

## Score Benchmarks

| Metric | Good | Acceptable | Needs work |
|--------|------|------------|------------|
| Faithfulness | > 0.90 | 0.75 – 0.90 | < 0.75 |
| Answer Relevance | > 0.85 | 0.70 – 0.85 | < 0.70 |
| Citation Precision | > 0.80 | 0.60 – 0.80 | < 0.60 |

---

## Improving Generation

| Symptom | What to try |
|---------|-------------|
| Low faithfulness (hallucination) | Strengthen the system prompt — emphasize "answer only from context"; use a more capable model |
| Low answer relevance | Revise the prompt template in `backend/generation/prompts.py`; check that retrieval is returning relevant context |
| Low citation precision | Verify `response_parser` is extracting citations correctly; improve reranking so relevant chunks rank higher |
