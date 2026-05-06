"""Generation-quality eval: LLM-as-judge over (query, retrieved, generated).

For each eval record, captures the model's generated answer plus the
retrieved passages it was given, then asks Claude (the judge) to rate:

- Citation faithfulness  : every cite supports the claim it's attached to
- Coverage               : the answer addresses every key aspect of the query
- Hallucination rate     : claims with no supporting passage
- Refusal calibration    : correct refusal when context insufficient

Stub for Phase 1 — full implementation in Phase 3 once generation lands.

Usage:
    uv run python evals/runners/generation.py \\
        --dataset evals/datasets/office_actions_v1.jsonl \\
        --top-n 50 \\
        --judge-model claude-sonnet-4-6
"""
from __future__ import annotations


def main() -> None:
    raise NotImplementedError(
        "Phase 1 stub. Phase 3 wires this once Claude generation is live."
    )


if __name__ == "__main__":
    main()
