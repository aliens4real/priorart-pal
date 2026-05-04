# Contributing

This is currently a solo portfolio project, but it's open source under MIT and PRs are welcome. The conventions below also describe how I work on it day-to-day.

## Quick start

```bash
git clone https://github.com/aliens4real/priorart-pal.git
cd priorart-pal
make setup            # installs uv, runs uv sync in api/ and infra/, npm ci in web/
make test             # runs all test suites (api + infra + web)
```

Each subproject has its own README:

- [`infra/README.md`](infra/README.md) — AWS CDK app
- [`api/README.md`](api/README.md) — FastAPI backend
- [`web/README.md`](web/README.md) — React frontend

## Branch & commit conventions

- **Branches:** `feat/<short-name>`, `fix/<short-name>`, `chore/<short-name>`, `docs/<short-name>`
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) — `type(scope): subject`
  - `feat(api): add /search endpoint`
  - `fix(infra): correct security group ingress rule`
  - `chore(deps): bump fastapi to 0.116`
  - `docs(readme): clarify deploy steps`

## Pull request workflow

1. Branch from `main`
2. Commit early and often; squash-merge happens at PR time
3. Make sure `make test` passes locally
4. Open a PR — the template will prompt you for context, scope, test plan, and rollout
5. CI must pass (lint + tests + `cdk synth`)
6. PRs to `main` require **review** (this is the workflow rule baked into `CLAUDE.md`)
7. **No direct pushes to `main`** except the very first scaffolding commit (already shipped)

## Code style

- **Python:** `ruff` for lint + format, `mypy --strict` for types. Configured in each subproject's `pyproject.toml`.
- **TypeScript:** `eslint` + `prettier`. React 19 functional components only; no class components.
- **Docstrings:** Required on public modules, classes, and non-trivial functions. Lead with **why**, not what.
- **Comments:** Default to none. Add only when the *why* is non-obvious — a hidden constraint, a workaround, a subtle invariant. Don't narrate what the code does.

## Tests

- **Backend:** `pytest` + `httpx.AsyncClient` for API tests
- **Frontend:** `vitest` + React Testing Library
- **Infra:** CDK assertion tests (`Template.from_stack`)
- Tests live alongside code, not in a separate "tests we'll write later" backlog.

## Pre-commit

```bash
pip install pre-commit
pre-commit install
```

Hooks run on every commit: `ruff`, `prettier`, trailing-whitespace, end-of-file fixer, secrets scanner. See `.pre-commit-config.yaml`.

## Security

See [`SECURITY.md`](SECURITY.md). The short version: **never commit a key, never paste a key into chat, rotate immediately if exposed.**

## What this project values

- **Architectural restraint over feature breadth.** v1 ships with documented gaps; we don't accumulate half-finished systems.
- **Tests alongside code, not after.**
- **Infrastructure-as-code, always.** No console-clicking. Every AWS resource lives in `infra/`.
- **Cost discipline.** Target <$50/month; alarms at $20 and $50. Cost-affecting changes call it out in the PR.
- **Honest documentation.** `NOTES.md` records what we tried, what worked, what didn't, and what we deliberately deferred.
