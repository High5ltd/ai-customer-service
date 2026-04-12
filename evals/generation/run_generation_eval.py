"""
Evaluate generation quality (faithfulness, answer relevance, citation precision).
Runs the full pipeline but only scores the generation step.

Usage:
    python -m evals.generation.run_generation_eval
    python -m evals.generation.run_generation_eval --dataset evals/datasets/sample_qa.json

The dataset must be a JSON array of objects with fields:
    - id: str
    - question: str
    - relevant_chunk_ids: list[str]  format: "{document_id}__{chunk_index}"

Reports are written to evals/reports/generation_<timestamp>.json
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
from evals.utils import make_chunk_id


async def run(dataset_path: str) -> None:
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
            search_results = await searcher.search(query_vector)
            ranked = reranker.rerank(search_results)
            ctx = build_context(ranked)

            messages = prompts.build_messages(question, ctx.context_text, history=None)
            answer = await llm_client.complete(messages)
            used_citations = response_parser.extract_used_citations(answer, ctx.citations)
            cited_ids = {make_chunk_id(c.document_id, c.chunk_index) for c in used_citations}

            metrics = await compute_generation_metrics(
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
                "cited_chunk_ids": list(cited_ids),
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

    agg_keys = ["faithfulness", "answer_relevance", "citation_precision"]
    aggregate = {
        k: round(sum(r["metrics"][k] for r in scored) / len(scored), 4)
        for k in agg_keys
    }
    aggregate["n"] = len(scored)

    print(f"\n=== Generation Aggregate (n={len(scored)}) ===")
    print(json.dumps(aggregate, indent=2))

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset": dataset_path,
        "aggregate": aggregate,
        "per_question": rows,
    }

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_path = Path("evals/reports") / f"generation_{ts}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved → {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run generation evaluation")
    parser.add_argument("--dataset", default="evals/datasets/sample_qa.json")
    args = parser.parse_args()
    asyncio.run(run(args.dataset))
