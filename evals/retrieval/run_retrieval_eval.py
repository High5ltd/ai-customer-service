"""
Evaluate retrieval quality (precision, recall, MRR, NDCG) against a labeled dataset.

Usage:
    python -m evals.retrieval.run_retrieval_eval
    python -m evals.retrieval.run_retrieval_eval --dataset evals/datasets/sample_qa.json --top-k 5

The dataset must be a JSON array of objects with fields:
    - id: str
    - question: str
    - relevant_chunk_ids: list[str]  format: "{document_id}__{chunk_index}"

Reports are written to evals/reports/retrieval_<timestamp>.json
"""
import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from backend.ingestion.embedder import embed_text
from backend.retrieval import reranker, searcher
from evals.retrieval.metrics import chunk_id, compute_retrieval_metrics


async def run(dataset_path: str, top_k: int) -> None:
    dataset = json.loads(Path(dataset_path).read_text())
    if not dataset:
        print("Dataset is empty.")
        return

    rows = []
    for item in dataset:
        qid = item["id"]
        question = item["question"]
        relevant_ids = set(item["relevant_chunk_ids"])

        try:
            query_vector = await embed_text(question)
            search_results = await searcher.search(query_vector, top_k=top_k)
            ranked = reranker.rerank(search_results)

            metrics = compute_retrieval_metrics(ranked, relevant_ids, k=top_k)
            row = {
                "id": qid,
                "question": question,
                "retrieved_chunk_ids": [chunk_id(r) for r in ranked[:top_k]],
                "relevant_chunk_ids": list(relevant_ids),
                "metrics": metrics.as_dict(),
            }
        except Exception as exc:
            print(f"[{qid}] ERROR: {exc}")
            row = {"id": qid, "question": question, "error": str(exc)}

        rows.append(row)
        if "metrics" in row:
            print(f"[{qid}] {row['metrics']}")

    scored = [r for r in rows if "metrics" in r]
    if not scored:
        print("No questions scored successfully.")
        return

    agg_keys = ["precision_at_k", "recall_at_k", "hit_rate", "mrr", "ndcg"]
    aggregate = {
        k: round(sum(r["metrics"][k] for r in scored) / len(scored), 4)
        for k in agg_keys
    }
    aggregate["k"] = top_k
    aggregate["n"] = len(scored)

    print(f"\n=== Retrieval Aggregate (n={len(scored)}) ===")
    print(json.dumps(aggregate, indent=2))

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset": dataset_path,
        "top_k": top_k,
        "aggregate": aggregate,
        "per_question": rows,
    }

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_path = Path("evals/reports") / f"retrieval_{ts}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved → {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run retrieval evaluation")
    parser.add_argument("--dataset", default="evals/datasets/sample_qa.json")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(run(args.dataset, args.top_k))
