# web/ — React + Vite + TypeScript + Tailwind

The single-page app. Cognito Hosted UI handles auth — we bounce the user out for sign-in and back with a JWT, which we attach to every API call.

## Local dev

```bash
cd web
npm install
npm run dev          # http://localhost:5173
```

## Test / lint / build

```bash
npm run lint         # ESLint
npm run test         # vitest in watch mode
npm run test -- --run # vitest single-pass (CI)
npm run build        # production build → dist/
npm run preview      # serve the production build locally
```

## Why this stack

- **Vite** — instant dev server, native ESM, fast builds. Vite > CRA for any new React project.
- **TypeScript** — production-grade type safety. Catches contract drift between frontend and the API's Pydantic models.
- **Tailwind v3** — utility-first CSS that scales without the per-component-stylesheet sprawl.
- **vitest** — Jest-compatible API on top of Vite's transform pipeline. One config to maintain instead of separate Jest setup.
- **React Testing Library** — encourages tests that mirror user behavior, not implementation details.

## Configuration

`.env` files for Vite — variables prefixed `VITE_` are exposed to the client bundle. Anything sensitive does NOT belong here (it's shipped to the browser). The Cognito client_id is fine; an API key is not.

## Auth flow (Phase 3)

```
[user] → click "Sign in" → redirect to Cognito Hosted UI
       ← redirect back to /callback?code=XXX
       → exchange code for JWT (id, access, refresh tokens)
       → store in memory (refresh in localStorage with care)
       → attach access token to every API request as `Authorization: Bearer <jwt>`
       → API Gateway validates the JWT against the Cognito issuer/audience
       → request proxied to App Runner with `x-amzn-cognito-*` headers
```

Phase 1 wires the skeleton. Auth integration lands in Phase 3.
