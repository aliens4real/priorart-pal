"""Retrieval-quality eval: recall@K, MRR, nDCG.

Reads an eval dataset (one record per query/answer pair), runs each query
through the PriorArt Pal retrieval pipeline, and reports standard IR
metrics. Used for both Phase 2 (no rerank) and Phase 3 (full pipeline)
to measure the lift from each layer.

Usage:
    uv run python evals/runners/retrieval.py \\
        --dataset evals/datasets/office_actions_v1.jsonl \\
        --pipeline full \\
        --top-k 50

Output: prints per-metric summary; writes JSON to evals/results/.

Stub for Phase 1 — full implementation in Phase 2 alongside the
retrieval pipeline itself.
"""
from __future__ import annotations


def recall_at_k(retrieved_ids: list[str], gold_id: str, k: int) -> int:
    """1 if the gold doc is in the top-k retrieved, else 0."""
    return 1 if gold_id in retrieved_ids[:k] else 0


def reciprocal_rank(retrieved_ids: list[str], gold_id: str) -> float:
    """1 / rank of the gold doc; 0 if not retrieved."""
    try:
        return 1.0 / (retrieved_ids.index(gold_id) + 1)
    except ValueError:
        return 0.0


def ndcg_at_k(retrieved_ids: list[str], gold_id: str, k: int) -> float:
    """Binary-relevance nDCG@k. With one gold doc per query this reduces to
    DCG = 1/log2(rank+1) if found in top-k, else 0; IDCG = 1 (best case
    rank 1)."""
    import math

    for i, rid in enumerate(retrieved_ids[:k]):
        if rid == gold_id:
            return 1.0 / math.log2(i + 2)
    return 0.0


def main() -> None:
    raise NotImplementedError(
        "Phase 1 stub. Phase 2 wires this to the retrieval pipeline once "
        "ingestion + pgvector ANN are running."
    )


if __name__ == "__main__":
    main()
