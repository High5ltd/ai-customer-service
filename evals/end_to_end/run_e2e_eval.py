"""
End-to-end evaluation: retrieval + generation metrics in a single pass.

Usage:
    python -m evals.end_to_end.run_e2e_eval
    python -m evals.end_to_end.run_e2e_eval --dataset evals/datasets/sample_qa.json --top-k 5

The dataset must be a JSON array of objects with fields:
    - id: str
    - question: str
    - relevant_chunk_ids: list[str]  format: "{document_id}__{chunk_index}"

Reports are written to evals/reports/e2e_<timestamp>.json
"""
import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from RAG.generation import llm_client, prompts, response_parser
from RAG.ingestion.embedder import embed_text
from RAG.retrieval import reranker, searcher
from RAG.retrieval.context_builder import build_context
from evals.generation.metrics import compute_generation_metrics
from evals.retrieval.metrics import compute_retrieval_metrics
from evals.utils import make_chunk_id


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
            # --- Retrieval ---
            query_vector = await embed_text(question)
            search_results = await searcher.search(query_vector, top_k=top_k)
            ranked = reranker.rerank(search_results)
            retrieval_metrics = compute_retrieval_metrics(ranked, relevant_ids, k=top_k)
            ctx = build_context(ranked)

            # --- Generation ---
            messages = prompts.build_messages(question, ctx.context_text, history=None)
            answer = await llm_client.complete(messages)
            used_citations = response_parser.extract_used_citations(answer, ctx.citations)
            cited_ids = {make_chunk_id(c.document_id, c.chunk_index) for c in used_citations}
            generation_metrics = await compute_generation_metrics(
                question=question,
                context=ctx.context_text,
                answer=answer,
                cited_chunk_ids=cited_ids,
                relevant_chunk_ids=relevant_ids,
            )

            row = {
                "id": qid,
                "question": question,
                "answer": answer,
                "retrieval": retrieval_metrics.as_dict(),
                "generation": generation_metrics.as_dict(),
            }
        except Exception as exc:
            print(f"[{qid}] ERROR: {exc}")
            row = {"id": qid, "question": question, "error": str(exc)}

        rows.append(row)
        if "retrieval" in row:
            print(f"[{qid}] retrieval={row['retrieval']} | generation={row['generation']}")

    scored = [r for r in rows if "retrieval" in r]
    if not scored:
        print("No questions scored successfully.")
        return

    def avg(section: str, key: str) -> float:
        return round(sum(r[section][key] for r in scored) / len(scored), 4)

    aggregate = {
        "retrieval": {k: avg("retrieval", k) for k in ["precision_at_k", "recall_at_k", "hit_rate", "mrr", "ndcg"]},
        "generation": {k: avg("generation", k) for k in ["faithfulness", "answer_relevance", "citation_precision"]},
        "n": len(scored),
    }
    aggregate["retrieval"]["k"] = top_k

    print(f"\n=== End-to-End Aggregate (n={len(scored)}) ===")
    print(json.dumps(aggregate, indent=2))

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset": dataset_path,
        "top_k": top_k,
        "aggregate": aggregate,
        "per_question": rows,
    }

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_path = Path("evals/reports") / f"e2e_{ts}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved → {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run end-to-end evaluation")
    parser.add_argument("--dataset", default="evals/datasets/sample_qa.json")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(run(args.dataset, args.top_k))
