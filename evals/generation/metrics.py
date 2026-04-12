"""
LLM-as-judge metrics for generation quality.

Uses the existing llm_client so no extra dependencies are needed.
"""
import json
from dataclasses import dataclass

from RAG.generation import llm_client


@dataclass
class GenerationMetrics:
    faithfulness: float       # 0-1: every claim in the answer is supported by the context
    answer_relevance: float   # 0-1: the answer actually addresses the question
    citation_precision: float # 0-1: fraction of cited chunks that are relevant

    def as_dict(self) -> dict:
        return {
            "faithfulness": round(self.faithfulness, 4),
            "answer_relevance": round(self.answer_relevance, 4),
            "citation_precision": round(self.citation_precision, 4),
        }


_FAITHFULNESS_PROMPT = """\
You are an evaluation assistant. Your job is to score how faithful an answer is to a given context.

A faithful answer contains ONLY claims that are directly supported by the context.
It does not introduce outside knowledge or hallucinate details.

Context:
{context}

Answer:
{answer}

Respond with a single JSON object and nothing else:
{{"score": <float between 0.0 and 1.0>}}

1.0 = every claim is fully supported by the context
0.0 = the answer contains claims not found in the context at all
"""

_RELEVANCE_PROMPT = """\
You are an evaluation assistant. Your job is to score how well an answer addresses a question.

Question: {question}
Answer: {answer}

Respond with a single JSON object and nothing else:
{{"score": <float between 0.0 and 1.0>}}

1.0 = the answer directly and completely addresses the question
0.0 = the answer is off-topic or does not address the question
"""


async def _judge_score(prompt: str) -> float:
    response = await llm_client.complete(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    try:
        data = json.loads(response.strip())
        return max(0.0, min(1.0, float(data["score"])))
    except (json.JSONDecodeError, KeyError, ValueError):
        return 0.0


async def compute_generation_metrics(
    question: str,
    context: str,
    answer: str,
    cited_chunk_ids: set[str],
    relevant_chunk_ids: set[str],
) -> GenerationMetrics:
    faithfulness = await _judge_score(
        _FAITHFULNESS_PROMPT.format(context=context, answer=answer)
    )
    answer_relevance = await _judge_score(
        _RELEVANCE_PROMPT.format(question=question, answer=answer)
    )

    if cited_chunk_ids:
        citation_precision = len(cited_chunk_ids & relevant_chunk_ids) / len(cited_chunk_ids)
    else:
        citation_precision = 0.0

    return GenerationMetrics(
        faithfulness=faithfulness,
        answer_relevance=answer_relevance,
        citation_precision=citation_precision,
    )
