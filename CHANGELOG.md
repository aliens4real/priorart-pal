# Changelog

All notable changes to this project will be documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `chore/repo-polish`: project governance + tooling polish — `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `CODEOWNERS`, PR + issue templates, Dependabot config, `.editorconfig`, `.pre-commit-config.yaml`, top-level `Makefile`, this changelog.

## [0.1.0] — 2026-05-03

Phase 1 scaffolding — no deploys.

### Added

- AWS CDK app (`infra/`) with 8 stacks: networking, secrets, database, auth, app-runner, api-gateway, frontend, monitoring. CDK assertion tests pass; `cdk synth` succeeds without AWS credentials.
- FastAPI backend (`api/`) with `/health` endpoint, structured JSON logging via `structlog`, `pydantic-settings` config, multi-stage Dockerfile for App Runner, smoke tests via `httpx.AsyncClient`.
- React + Vite + TypeScript + Tailwind frontend (`web/`) with `vitest` + Testing Library smoke tests.
- Documentation: top-level `README`, `CLAUDE.md` (Claude Code persistent context + workflow rules), `NOTES.md` (decision log).

### Notes

- `.github/workflows/ci.yml` exists locally but is not yet committed — pending GitHub OAuth `workflow` scope refresh.
- AWS deploy paused pending account reactivation.

[Unreleased]: https://github.com/aliens4real/priorart-pal/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/aliens4real/priorart-pal/releases/tag/v0.1.0
