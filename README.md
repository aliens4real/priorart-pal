# PriorArt Pal

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![TypeScript](https://img.shields.io/badge/typescript-5.7-3178c6.svg)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![AWS CDK](https://img.shields.io/badge/AWS_CDK-2.180-ff9900.svg)](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
[![Status: Phase 1](https://img.shields.io/badge/status-phase_1_scaffold-yellow.svg)](#status)

A RAG-powered prior-art patent search assistant for examiners and practitioners working in vehicle autonomy / navigation art.

> Given a patent claim or technical disclosure, PriorArt Pal retrieves the strongest candidate references from a USPTO corpus and generates a citation-faithful synthesis with grounded source IDs.

---

## Status

**Phase 1 — scaffolding (no deploys).** The CDK infrastructure, FastAPI backend skeleton, and React frontend are in place. AWS provisioning is paused pending account reactivation; in the meantime the RAG pipeline is being built locally.

| Phase | Scope | Status |
|---|---|---|
| 1. Scaffolding | Project skeleton, IaC, CI, governance docs | ✅ done |
| 2. Data + retrieval | Patent ingest, embeddings, pgvector retrieval | in progress |
| 3. Rerank + generation | Cohere rerank, Claude streaming, Cognito auth | planned |
| 4. Observability | `llm_calls` table, admin metrics, cost guardrails | planned |
| 5. Polish | Demo recording, end-to-end docs | planned |

See [`NOTES.md`](NOTES.md) for the running decision log and [`CHANGELOG.md`](CHANGELOG.md) for released changes.

---

## How it works

```
[user browser]
     │ HTTPS
     ▼
┌────────────────────────────┐
│ CloudFront → S3            │  React + Vite + TS + Tailwind
└────────────────────────────┘
     │  user signs in via Cognito Hosted UI → JWT
     ▼
┌────────────────────────────┐
│ API Gateway (HTTP API)     │  validates JWT, throttles per-user
└────────────────────────────┘
     │
     ▼
┌────────────────────────────┐
│ FastAPI on App Runner      │  async Python, streaming responses
└────────────────────────────┘
     │       │       │       │
     ▼       ▼       ▼       ▼
   Voyage Cohere  Claude  RDS Postgres 16
   embed   rerank  stream  + pgvector HNSW
```

On a search request:

1. **Embed** the query with Voyage `voyage-3-large` → 1024-dim vector
2. **Retrieve** the top 50 candidate passages from `pgvector` (HNSW, cosine similarity)
3. **Rerank** those 50 with Cohere Rerank v3 → top 10
4. **Generate** a citation-faithful synthesis with Claude (direct API, prompt caching), streaming back through API Gateway
5. **Log** the call (tokens, latency, cost) to the `llm_calls` table; surface at `/admin/metrics`

---

## Stack at a glance

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 19 · Vite · TypeScript · Tailwind v3 | Production-grade SPA stack |
| Auth | AWS Cognito Hosted UI · JWT | Managed auth — no rolling our own |
| API | FastAPI in Docker on AWS App Runner | Async Python; managed compute |
| Edge | API Gateway HTTP API + JWT authorizer | Per-user usage plans, JWT at the edge |
| DB | RDS Postgres 16 + pgvector (HNSW) | One DB for relational + vector |
| Embeddings | Voyage AI `voyage-3-large` | Best-in-class for technical/legal text |
| Reranker | Cohere Rerank v3 | Production-grade cross-encoder |
| Generation | Anthropic Claude (direct API, prompt caching) | Citation fidelity, streaming |
| Infra | AWS CDK (Python) | Type-safe IaC, same language as backend |
| Observability | CloudWatch JSON + `llm_calls` table | Logs + per-call cost / latency |
| CI | GitHub Actions | Lint + test + `cdk synth` on PR |

---

## Repo layout

```
priorart-pal/
├── infra/        AWS CDK app — networking, db, secrets, app-runner, api-gw, auth, frontend, monitoring
├── api/          FastAPI backend
├── web/          React + Vite + Tailwind frontend
├── scripts/      Ingest / utility scripts (Phase 2+)
├── CLAUDE.md     Persistent project context for Claude Code
├── NOTES.md      Running decisions, gotchas, costs
└── CHANGELOG.md  Released changes (Keep a Changelog)
```

---

## Quick start

```bash
git clone https://github.com/aliens4real/priorart-pal.git
cd priorart-pal
make setup     # installs api/infra Python deps via uv, web deps via npm
make test      # runs all test suites
```

Per-subproject docs:

- [`infra/README.md`](infra/README.md) — CDK stacks and the deploy model
- [`api/README.md`](api/README.md) — FastAPI dev loop
- [`web/README.md`](web/README.md) — Vite dev server, auth flow

`make help` lists every available target.

---

## Cost target

≤ **$50 / month**. CloudWatch billing alarms at $20 and $50. Per-user API Gateway throttling caps abuse-driven LLM spend.

---

## Deliberately skipped for v1

These are conscious deferrals so v1 ships, not gaps:

- Multi-region failover (us-east-1 only)
- AWS WAF / shield
- Automated batch ingestion pipeline (manual ingest script for now)
- Production secret rotation
- VPC endpoints (App Runner egresses to internet for AI provider calls)
- SOC 2 / formal compliance posture

The full living list lives in [`NOTES.md`](NOTES.md).

---

## Contributing

PRs welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md). Security disclosures go through [`SECURITY.md`](SECURITY.md).

## License

MIT — see [`LICENSE`](LICENSE).

## Built by

**Michael Kerrigan** — USPTO Primary Patent Examiner (vehicle autonomy / navigation art), targeting AI engineering roles. Reach me at michael.v.kerrigan@gmail.com.
