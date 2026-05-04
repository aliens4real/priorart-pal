# CLAUDE.md

Persistent context for Claude Code working in this repo.

## Project

**PriorArt Pal** — A RAG-powered prior-art patent search assistant for vehicle autonomy / navigation art. Built as a portfolio piece for AI engineering roles (target: AHEAD, Chicago).

Owner: Michael Kerrigan — USPTO Primary Patent Examiner (FSA), 25% owner of Canopy Solar.

## Why this exists

Show production-shaped RAG end-to-end: vector retrieval, reranking, citation-faithful streaming generation, multi-tenant auth, observability, cost guardrails, infrastructure-as-code.

## Locked-in architecture

- **Frontend:** React + Vite + TypeScript + Tailwind, hosted on S3 + CloudFront, Cognito Hosted UI for auth
- **API:** FastAPI in Docker on AWS App Runner, fronted by API Gateway HTTP API with Cognito JWT authorizer; streaming responses
- **Data:** PostgreSQL 16 on RDS `db.t4g.micro` with pgvector (HNSW index) — single DB for patents, embeddings, users, request logs
- **AI:** Voyage AI `voyage-3-large` for embeddings, Cohere Rerank v3 for reranking, Anthropic Claude (direct API, prompt caching enabled) for generation. Architecture leaves Bedrock-swap available via config flag.
- **Infra:** AWS CDK in Python; us-east-1 only
- **Observability:** Structured JSON to CloudWatch + per-LLM-call rows in Postgres `llm_calls` table; `/admin/metrics` endpoint (Cognito admin group) showing tokens, latency, cost, errors
- **Cost protection:** API Gateway per-user usage plans (10/hr, 100/day total cap); CloudWatch billing alarms at $20 and $50

## Workflow rules — READ EVERY SESSION

1. **Build infrastructure-as-code (CDK) BEFORE application code.**
2. **NEVER run `cdk deploy` or any AWS-mutating command without Michael's explicit "yes, deploy".** Show `cdk synth` output first, every time. This includes: `cdk bootstrap`, `cdk deploy`, `cdk destroy`, `aws ec2`/`s3`/`rds`/etc. mutating commands. Read-only AWS commands (`aws sts get-caller-identity`, `aws s3 ls`) are fine without confirmation.
3. **NEVER commit secrets.** Use Secrets Manager + IAM roles from day one. Never put API keys in `.env` files that get committed; `.env` is gitignored.
4. **Conventional commits, feature branches, PRs for every change.** Michael reviews. No direct pushes to `main` except the very first scaffolding commit.
5. **Tests alongside code, not after.** `pytest` for backend, `vitest` for frontend, `cdk` assertion tests for infra.
6. **Keep `NOTES.md` updated** with decisions, gotchas, and costs incurred. Append, don't rewrite history.
7. **If you're uncertain about an AWS service or pattern, say so — don't guess.**

## Skill levels (for explanation tone)

- **Strong:** JS/React, conventional Git, software engineering fundamentals, USPTO domain
- **Intermediate:** Python (3.12 installed)
- **Light:** FastAPI, Docker, AWS, CDK, pgvector internals
- **Approach:** When introducing a new pattern (e.g., CDK constructs, FastAPI dependency injection, App Runner VPC connectors), give a 2–4 sentence "here's why this exists" before diving into code.

## Constraints

- Personal AWS account, ~$50/mo budget
- Architectural restraint > feature breadth
- Document deliberate gaps (multi-region, WAF, batch ingestion = skipped for v1)

## Phase plan

- **Phase 1 (weeks 1–2):** Scaffolding ← we are here
- **Phase 2 (weeks 3–5):** Data ingestion + first crude RAG (single-shot, no rerank)
- **Phase 3 (weeks 6–8):** Reranking + streaming generation + auth
- **Phase 4 (weeks 9–10):** Observability + cost guardrails + admin metrics
- **Phase 5 (weeks 11–12):** Polish, demo recording, documentation pass

## File / package conventions

- Folder name: `priorart-pal` (kebab)
- Python package: `priorart_pal` (snake)
- Repo: `github.com/aliens4real/priorart-pal` (public)
- Branch strategy: `main` (protected after first commit), feature branches like `feat/db-stack`, `feat/health-endpoint`
- Cognito Hosted UI domain prefix: `priorart-pal-mk-auth`

## Patent corpus (Phase 2)

- **Source:** USPTO bulk data (Patent Full-Text and Image Database / Open Data Portal)
- **Subset:** Vehicle autonomy / navigation art — CPC subclasses to be finalized in Phase 2 (likely B60W, G05D 1/00, G01C 21/00, G08G)
- **Decision deferred:** Sample size (target ~10K patents to start) and field selection (claims + abstract + first detailed-description paragraph?)

## Out of scope for v1

- Multi-region failover
- AWS WAF
- Automated batch ingestion (manual script only for now)
- VPC endpoints for AI provider calls (App Runner egresses to internet)
- Production secret rotation
- Per-user fine-grained authorization beyond admin / non-admin
