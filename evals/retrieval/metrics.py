import math
from dataclasses import dataclass

from RAG.retrieval.searcher import SearchResult
from evals.utils import make_chunk_id


def chunk_id(result: SearchResult) -> str:
    return make_chunk_id(result.document_id, result.chunk_index)


@dataclass
class RetrievalMetrics:
    precision_at_k: float  # fraction of top-k that are relevant
    recall_at_k: float     # fraction of relevant chunks found in top-k
    hit_rate: float        # 1.0 if any relevant chunk appears in top-k
    mrr: float             # reciprocal rank of first relevant result
    ndcg: float            # normalized discounted cumulative gain
    k: int

    def as_dict(self) -> dict:
        return {
            "precision_at_k": round(self.precision_at_k, 4),
            "recall_at_k": round(self.recall_at_k, 4),
            "hit_rate": round(self.hit_rate, 4),
            "mrr": round(self.mrr, 4),
            "ndcg": round(self.ndcg, 4),
            "k": self.k,
        }


def compute_retrieval_metrics(
    retrieved: list[SearchResult],
    relevant_ids: set[str],
    k: int,
) -> RetrievalMetrics:
    top_k = retrieved[:k]
    top_k_ids = [chunk_id(r) for r in top_k]

    hits = sum(1 for cid in top_k_ids if cid in relevant_ids)

    precision = hits / k if k > 0 else 0.0
    recall = hits / len(relevant_ids) if relevant_ids else 0.0
    hit_rate = 1.0 if any(cid in relevant_ids for cid in top_k_ids) else 0.0

    mrr = 0.0
    for rank, cid in enumerate(top_k_ids, start=1):
        if cid in relevant_ids:
            mrr = 1.0 / rank
            break

    dcg = sum(
        (1.0 if cid in relevant_ids else 0.0) / math.log2(rank + 1)
        for rank, cid in enumerate(top_k_ids, start=1)
    )
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    ndcg = dcg / idcg if idcg > 0 else 0.0

    return RetrievalMetrics(
        precision_at_k=precision,
        recall_at_k=recall,
        hit_rate=hit_rate,
        mrr=mrr,
        ndcg=ndcg,
        k=k,
    )
