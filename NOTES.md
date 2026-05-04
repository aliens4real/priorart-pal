# NOTES

Append-only log of decisions, gotchas, and costs. Newest at the top.

---

## 2026-05-03 — Project bootstrapped

**Decisions made**

- Embeddings: **Voyage AI `voyage-3-large`** over OpenAI `text-embedding-3-small`. Voyage outperforms on technical/legal text and is Anthropic's recommended embedding partner — the better narrative for the AHEAD interview.
- Reranker: **Cohere Rerank v3**. Industry leader; no alternative without self-hosting.
- Generation: **Anthropic Claude** (direct API, prompt caching). Already have an account; prompt caching is the cost lever for repeated long retrieval contexts.
- Frontend: **TypeScript** (not JS). Stronger production signal for portfolio reviewers.
- Python deps: **`uv`**. Fast, modern, lockfile-based; less boilerplate than Poetry.
- CDK stack split: networking / secrets / database / auth / app_runner / api_gateway / frontend / monitoring. Auth and api_gateway broken out from the original spec because they have distinct lifecycles from compute.
- Patent corpus: **fresh start**, no reuse from existing `~/Desktop/patent-analyzer/`. Owning the architecture top-to-bottom is the point.
- Names locked: `priorart-pal` (repo + folder) / `priorart_pal` (Python pkg) / `priorart-pal-mk-auth` (Cognito Hosted UI prefix).

**Tooling installed**

- AWS CLI 2.34.41
- AWS CDK CLI 2.1120
- uv 0.11.8

**Tooling pending**

- Docker Desktop — deferred until we need to build/push images (Phase 2 or 3)

**Costs incurred**

- $0 — nothing deployed yet.

**Open items**

- Run `aws configure` (Michael's hands) — pending AWS account reactivation
- Run `cdk bootstrap` after credentials are set (requires "yes, deploy")
- Sign up for Cohere + Voyage AI accounts

**Closed**

- ~~Add `.github/workflows/ci.yml` via GitHub web UI~~ — done 2026-05-03
- ~~Decide corpus scope~~ — **autonomous passenger vehicles**, seed list of
  10 foundational patents confirmed (see [`docs/seed-corpus.md`](docs/seed-corpus.md))

---

## 2026-05-03 — Phase 2 design: structural retrieval (post-scaffold)

**Decision: visual claim builder + structural RAG, not vanilla text RAG.**

Two patents in this art can use entirely different vocabulary for the same
architecture, or identical vocabulary for completely different architectures.
Keyword/embedding-only retrieval misses both. Examiners think structurally
first (system topology), then check functional limitations against that
topology — the tool should mirror that.

**Approach:**

- **Constrained ontology** (Option A from design discussion): a fixed set
  of node types (Sensor, Controller, Server, Vehicle, Network, Actuator, …)
  and edge types (sends, controls, comprises, mounted_on, …) tuned for AV.
  Living spec — we iterate as we ingest real patents.
- **Pre-processing pipeline:** for each patent, Claude reads claims + spec,
  extracts a JSON graph in the ontology, stores alongside text chunks.
- **Visual claim builder** (frontend): React Flow canvas, drag-drop nodes,
  snap-connect typed edges, optional functional text per node.
- **Hybrid retrieval:** structural similarity + embedding similarity over
  node/edge labels + bonus weight for "must have" nodes.
- **Output:** top-N patents with side-by-side graph visualization and
  Claude-generated paragraph cites for matched elements.

**Why this is a stronger AHEAD story than vanilla RAG:** demonstrates
domain-specific ontology design, structural / multi-vector retrieval,
and a bespoke UX for the actual user (examiners), not just "I bolted
embeddings to Postgres".

**Skipped from spec, kept on the table:** Option C (hybrid free-form +
ontology) is the v2 evolution if Option A's edge cases bite.
