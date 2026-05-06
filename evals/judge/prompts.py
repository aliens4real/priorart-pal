"""LLM-as-judge prompts for eval runners.

Each prompt is structured as a strict rubric: input is (query, retrieved
passages, generated answer), output is a JSON object with per-criterion
scores + a free-text rationale. Designed for batched calls so we can
evaluate hundreds of records cheaply.

Phase 1 stub — Phase 3 wires these to the actual generation eval runner.
"""
from __future__ import annotations

CITATION_FAITHFULNESS_PROMPT = """\
You are evaluating a generated patent-search synthesis for citation
faithfulness. For each cite in the generated answer, determine whether
the cited passage actually supports the claim the cite is attached to.

Inputs:
  query: {query}
  retrieved passages (each prefixed with its anchor):
{passages}
  generated answer (with inline cites):
{answer}

Output JSON only:
{{
  "per_cite": [
    {{
      "claim": "<the assertion in the answer>",
      "anchor": "<the cite anchor, e.g. Smith ¶0042>",
      "supported": true | false,
      "rationale": "<one sentence>"
    }}
  ],
  "faithfulness_score": 0.0,    // fraction of cites supported
  "hallucinations": [
    "<assertion in the answer with no supporting passage>"
  ]
}}
"""

COVERAGE_PROMPT = """\
You are evaluating whether a generated patent-search synthesis covers
every key aspect of the user's query.

Inputs:
  query: {query}
  generated answer:
{answer}

Output JSON only:
{{
  "key_aspects_extracted_from_query": ["<aspect 1>", "<aspect 2>", ...],
  "aspect_coverage": [
    {{ "aspect": "<aspect>", "addressed": true | false }}
  ],
  "coverage_score": 0.0    // fraction of aspects addressed
}}
"""

REFUSAL_CALIBRATION_PROMPT = """\
You are evaluating whether a generated synthesis correctly refused (or
correctly did not refuse) given the retrieved context.

Inputs:
  query: {query}
  retrieved passages:
{passages}
  generated answer (or refusal message):
{answer}

A correct refusal: the retrieved passages do not actually support an
answer to the query, AND the generated output declines to answer.
A correct non-refusal: the retrieved passages do support an answer, AND
the output provides one.
An incorrect refusal: passages support an answer, but the model
refused.
An incorrect non-refusal: passages don't support an answer, but the
model produced one (hallucination risk).

Output JSON only:
{{
  "context_sufficient": true | false,
  "model_refused": true | false,
  "calibration": "correct_refusal" | "correct_answer" | "incorrect_refusal" | "incorrect_answer"
}}
"""
