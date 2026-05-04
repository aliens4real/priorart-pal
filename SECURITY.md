# Security policy

## Reporting a vulnerability

If you discover a security issue, please email **michael.v.kerrigan@gmail.com** with:

- A description of the issue
- Steps to reproduce
- Affected components / versions

Do not open a public issue. I'll acknowledge within 48 hours and aim to publish a fix within 7 days for high-severity issues.

## Threat model — what this project protects

PriorArt Pal handles three categories of sensitive data:

1. **AI provider API keys** (Voyage, Cohere, Anthropic) — full access to paid accounts
2. **Database credentials** for the patent / user / log store
3. **User PII** — Cognito-managed email + IDs, plus query history written to the `llm_calls` table

## Secrets handling rules

These are non-negotiable. Violations should be flagged in PR review:

- **Never commit a key.** All API keys and DB credentials live in AWS Secrets Manager and are injected into App Runner via IAM role at runtime. Local `.env` files are gitignored and contain only dev-mode placeholder values.
- **Never paste a key into a chat, issue, or PR.** Even private channels — secrets get cached, screenshotted, and logged.
- **Never log a key.** Structured loggers should redact known-secret keys; a `redact_secrets` helper exists in `api/src/priorart_pal/logging_config.py`.
- **Rotate immediately** if a key is exposed. Voyage / Cohere / Anthropic dashboards all support rotation in <30 seconds.

## Authentication

- All API endpoints (except `/health`) require a valid Cognito-issued JWT, validated at the API Gateway edge before the request reaches the application.
- Admin endpoints (`/admin/*`) additionally require membership in the Cognito `admin` group, checked in middleware.
- Tokens are short-lived (1h access, 30d refresh).

## Cost / abuse protection

The same usage plans that bound LLM cost also bound abuse:

- API Gateway throttles to **10 requests/hour** per user and **100/day** total
- CloudWatch billing alarms at **$20** and **$50**
- The risk manager pattern from `api/src/priorart_pal/core/` (Phase 4) writes a halt-lock if anomalous spend is detected

## Deliberately out of scope for v1

Documented so they're tracked, not forgotten:

- AWS WAF / shield
- Web application firewall rules
- Bot detection / CAPTCHA on Cognito sign-up
- Field-level DB encryption
- Penetration testing
- SOC 2 / formal compliance posture

These are not gaps — they are choices made consciously to ship v1 within budget and scope.
