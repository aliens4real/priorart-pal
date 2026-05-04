# PriorArt Pal

A RAG-powered prior-art patent search assistant for examiners and practitioners working in vehicle autonomy / navigation art.

**Status:** Phase 1 — scaffolding (no deploys yet)

## What it does

Given a patent claim or technical disclosure, PriorArt Pal:

1. Embeds the query and retrieves candidate references from a corpus of USPTO patents (vehicle autonomy / navigation art) using `pgvector` HNSW similarity search
2. Reranks the top-K candidates with Cohere Rerank v3 to push the strongest matches up
3. Generates a citation-faithful synthesis with Claude (streaming), grounding every claim in retrieved passages with source IDs

Built as a portfolio piece showing production-shaped multi-tenant RAG: auth, observability, cost guardrails, and infrastructure-as-code.

## Architecture

```
┌────────────────┐                      ┌─────────────────────┐
│ React + Vite   │                      │ AWS Cognito         │
│ S3 + CloudFront│ ─── Hosted UI ─────► │ User Pool           │
└──────┬─────────┘                      └─────────┬───────────┘
       │ JWT                                      │
       ▼                                          │
┌──────────────────┐  ─── JWT authorizer ────────┘
│ API Gateway      │
│ HTTP API         │
│ usage plans      │
└──────┬───────────┘
       ▼
┌──────────────────┐         ┌────────────────────┐
│ FastAPI on       │ ──────► │ Voyage AI (embed)  │
│ App Runner       │ ──────► │ Cohere (rerank)    │
│ (Docker / ECR)   │ ──────► │ Anthropic (gen)    │
└──────┬───────────┘         └────────────────────┘
       │
       ▼
┌──────────────────┐
│ RDS Postgres 16  │
│ + pgvector HNSW  │
│ patents,         │
│ embeddings,      │
│ users, llm_calls │
└──────────────────┘
```

## Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Vite + Tailwind + TypeScript | Industry-standard SPA; TS for production-grade types |
| Auth | Cognito Hosted UI + JWT | Managed auth, no rolling-our-own |
| API | FastAPI in Docker on App Runner | Async-friendly Python, simple managed compute |
| Gateway | API Gateway HTTP API + Cognito JWT authorizer | Per-user usage plans, JWT validation, cheap |
| DB | RDS Postgres 16 + pgvector (HNSW) | Single DB for relational + vector; `db.t4g.micro` |
| Embeddings | Voyage AI `voyage-3-large` | Best-in-class for technical/legal text |
| Reranker | Cohere Rerank v3 | Production-grade cross-encoder reranking |
| Generation | Anthropic Claude (direct API, prompt caching) | Citation fidelity, streaming, cache wins on long context |
| Infra | AWS CDK (Python) | Type-safe IaC, single language with backend |
| Observability | CloudWatch JSON logs + `llm_calls` table | Per-call cost / latency / token usage |
| CI/CD | GitHub Actions | Lint + test on PR; deploy stage TBD |

## Repo layout

```
priorart-pal/
├── infra/        AWS CDK app — networking, db, secrets, app-runner, api-gw, auth, frontend, monitoring
├── api/          FastAPI backend
├── web/          React + Vite + Tailwind frontend
├── scripts/      Ingest / utility scripts
├── CLAUDE.md     Persistent project context for Claude Code
├── NOTES.md      Running decisions, gotchas, costs
└── README.md
```

## Local dev

Each subproject has its own README. Start with `infra/README.md` — nothing deploys without your explicit `yes, deploy`.

## Deliberately skipped for v1

These are not gaps in the design — they are conscious deferrals so v1 ships:

- Multi-region (us-east-1 only)
- AWS WAF
- Batch ingestion pipeline (manual ingest script for now)
- Production-grade secret rotation
- VPC endpoints (App Runner uses internet egress for OpenAI / Cohere / Anthropic calls)

See `NOTES.md` for the running list.

## Cost target

≤ $50/mo. CloudWatch billing alarms at $20 and $50.

## Built by

Michael Kerrigan — USPTO Primary Patent Examiner (vehicle autonomy / navigation art), targeting AI engineering roles.
