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

- Run `aws configure` (Michael's hands)
- Run `cdk bootstrap` after credentials are set (requires "yes, deploy")
- Sign up for Cohere + Voyage AI accounts
- Decide CPC subclass list for patent corpus (Phase 2)
- Add `.github/workflows/ci.yml` via GitHub web UI (gh CLI OAuth lacks
  `workflow` scope; refresh attempt didn't take. File exists locally,
  ready to paste into the GitHub Actions UI when convenient.)
