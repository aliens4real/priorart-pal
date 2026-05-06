"""Ablation eval: compare four pipeline configurations on the same set.

Configurations:

  1. BM25-only                          (keyword baseline)
  2. + Voyage embeddings (vanilla RAG)  (semantic retrieval lift)
  3. + Cohere rerank                    (cross-encoder rerank lift)
  4. PriorArt Pal full                  (+ structural overlay)

Reports recall@10 / @50, MRR, nDCG@10 for each configuration so each
layer's contribution to retrieval quality is defensible.

This is the killer interview slide. Implementation in Phase 4 once all
four configurations exist.
"""
from __future__ import annotations


def main() -> None:
    raise NotImplementedError(
        "Phase 1 stub. Phase 4 wires this once all four configurations "
        "(BM25, Voyage, Voyage+rerank, full) are implementable."
    )


if __name__ == "__main__":
    main()
