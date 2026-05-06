# evals/

How we measure whether PriorArt Pal is any good. **The eval methodology is the project's strongest interview signal** — it shows we treat "does this work?" as the actual job.

## Six dimensions we measure

### 1. Retrieval quality

| Metric | Question it answers | Target |
|---|---|---|
| **Recall@10** | Is the relevant patent in the top 10? | > 70% |
| **Recall@50** | Is it in the top 50 (pre-rerank window)? | > 90% |
| **MRR** | If yes, how high up? | > 0.3 |
| **nDCG@10** | Relevance-weighted ranking quality | > 0.5 |

Implementation: `runners/retrieval.py`.

### 2. Generation quality

LLM-as-judge against retrieved passages.

| Metric | Question it answers |
|---|---|
| **Citation faithfulness** | Does each cite actually support the claim it's attached to? |
| **Coverage** | Did the answer address every key aspect of the query? |
| **Hallucination rate** | How often does it claim something not in retrieved text? |
| **Refusal calibration** | Does it correctly refuse when context is insufficient? |

Implementation: `runners/generation.py` + `judge/prompts.py`.

### 3. Structural matching (this project's differentiator)

Hand-crafted test cases verifying the BRI matcher rules fire correctly:

- **`parent_type` substitution**: query `PEDESTRIAN_DETECTOR` should match patent disclosing `OBSTACLE_DETECTOR` (specific reads on generic) — flagged as `bri_substitution`.
- **Agency abstraction**: query `TELEMATICS_CONTROLLER --SENDS_TO--> SERVER` should match patent disclosing `VEHICLE` performing the comms (compositional reads on container) — flagged as `agency_substituted`.
- **Sibling rejection**: query `PEDESTRIAN` should not match patent disclosing `ANIMAL` (both `ROAD_OBSTACLE` children but distinct).

Implementation: `runners/structural.py`.

### 4. Latency / cost

| Metric | Target |
|---|---|
| End-to-end p50 latency to first token | < 2 s |
| End-to-end p95 latency | < 5 s |
| Cost per query (Voyage + Cohere + Claude combined) | < $0.05 |
| Prompt-cache hit ratio (% input tokens cached) | > 70% |
| HNSW lookup p99 | < 100 ms |

Implementation: derived from `llm_calls` table + tracing on the FastAPI side.

### 5. End-to-end task success

Self-measurement on the project owner's actual examiner work. Time-to-relevant-cite vs. manual search baseline. Owner ratings on output usefulness.

### 6. Comparative ablation — *the killer interview slide*

Run the same eval set against four configurations to defend each layer's contribution:

| Configuration | What it adds |
|---|---|
| Baseline 1: BM25-only | keyword-search baseline |
| Baseline 2: + Voyage embeddings (vanilla RAG) | lift from semantic retrieval |
| Baseline 3: + Cohere rerank | lift from cross-encoder rerank |
| **PriorArt Pal full** | lift from the structural overlay |

Implementation: `runners/ablation.py`.

## Where ground truth comes from

Three sources, in order of strength:

### A. Examiner office actions (gold standard)

Every USPTO Office Action lists the prior art used in 102/103 rejections. Each rejection = `(applicant claim text, the patent the examiner cited)`. **This is the strongest possible eval signal for a patent search tool — examiners did the work; we just check whether our retrieval finds it.**

- **Source:** `patents-public-data.uspto_oce_office_actions.*` in BigQuery (USPTO OCE Office Actions Research Dataset)
- **Fully public.** Office actions are part of every published application's file wrapper. The OCE BigQuery dataset is anonymized at the examiner level.
- **Build query:** [`sql/office_actions_eval.sql`](sql/office_actions_eval.sql)
- **Coverage:** ~5M office actions across all art units. We filter to autonomy-relevant CPC subclasses.

#### Citation-anchor consistency

Office-action `cited_pub_no` values are **pre-grant publication numbers** (e.g., `US20180047289A1`), not granted-patent numbers — because that's what examiners admit as prior art. Our retrieval and generation respect the same convention. See [`docs/adr/0001-citation-anchor-consistency.md`](../docs/adr/0001-citation-anchor-consistency.md) for the why and the implementation rules.

### B. Backward-citation graph (synthetic)

For each patent X, the patents X cites in its backward references should appear in retrieval when X's claim is the query. Lower quality than office actions (X may cite for many reasons — not all relevance-equivalent) but trivial to bootstrap from `patents-public-data.patents.publications`.

### C. Hand-curated examiner set (high-quality, low-quantity)

50–100 queries built by the project owner from historical work. Each has a known-best-prior-art. Used for nuanced testing that automated sets miss (BRI substitution, agency abstraction, edge cases).

## CI integration

- **Smoke eval on every PR**: a small fast subset (~20 queries) checking recall@10 doesn't regress > 5% vs. the previous main. Runs in < 5 minutes.
- **Full nightly eval**: the comparative-ablation matrix on the full eval set. Results committed to `results/` with timestamps.

## Layout

```
evals/
├── datasets/           # eval data (JSONL); built by SQL queries + manual curation
├── runners/
│   ├── retrieval.py    # recall@K / MRR / nDCG
│   ├── generation.py   # LLM-judge faithfulness
│   ├── structural.py   # BRI matcher tests
│   └── ablation.py     # 4-config comparative
├── judge/
│   └── prompts.py      # LLM-as-judge rubrics
├── sql/
│   └── office_actions_eval.sql   # BigQuery -> office_actions_v1.jsonl
├── results/            # versioned eval output (gitignored except summaries)
└── README.md           # this file
```

## When this gets built

- **Phase 1 (now):** scaffolding — this directory + the SQL + the runner stubs.
- **Phase 2:** build `office_actions_v1.jsonl` (run the SQL) + first crude retrieval eval (recall@10 only).
- **Phase 3:** add generation + structural runners.
- **Phase 4:** wire CI smoke-eval; run the full ablation; produce the interview-slide summary.

## Eval ethics / data sourcing

- All data is **fully public** USPTO record. Office actions are part of the public file wrapper of every published patent application.
- The OCE BigQuery dataset is **anonymized at the examiner level** — no personal information about examiners or applicants beyond what's already in the public file wrapper.
- We do **not** use unpublished applications, internal examiner notes, or any non-public data.
- **No applicant PII** is logged or stored beyond what BigQuery already exposes publicly.
