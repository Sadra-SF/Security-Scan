# Security Scanner Frontend (Vite + React + TS)

Minimal-but-functional React frontend for the Security Scanner Django API.

## Prerequisites

- Node.js v18+ (recommended LTS) and npm (or yarn/pnpm)
- Running backend API with CORS allowing this app's origin (e.g., http://localhost:5173)

## Setup

1) Install dependencies
```bash
cd security-scanner/frontend
npm install
# or: yarn install
# or: pnpm install
```

2) Configure environment
```bash
cp .env.example .env
# Adjust if needed:
# VITE_API_BASE_URL=http://localhost:8000
```

3) Dev server
```bash
npm run dev
# open http://localhost:5173
```

4) Build / Preview
```bash
npm run build
npm run preview
```

## Project Structure

- src/main.tsx — app bootstrap
- src/App.tsx — temporary shell
- src/index.css — Tailwind directives and fallback base styles
- src/env.ts — Vite env bridge
- src/api/client.ts — Axios instance with JWT/refresh handling
- src/api/hooks/auth.ts — useAuth login/logout hook
- src/state/auth.ts — zustand auth store (tokens + user)
- src/router/index.tsx — routes definition
- src/router/requireAuth.tsx — route guard wrapper
- pages under src/pages/ — Login/Dashboard/Targets/Scans/Findings/Reports/Settings (to be filled)

## Routing

- /login
- /dashboard
- /targets, /targets/:id
- /scans/new, /scans/:id
- /findings
- /schedules (placeholder)
- /reports
- /settings/integrations

Protected routes use a RequireAuth guard.

## Auth

- Login POST /api/auth/jwt/create/ with { username, password }
- Tokens are stored in zustand + localStorage
- Axios attaches Bearer token and attempts refresh via /api/auth/jwt/refresh/ on 401

Note: Ensure backend endpoints match (see api_server/settings.py).

## CORS/CSRF

Configure Django to allow CORS from the dev origin (default http://localhost:5173).
CSRF is not used for JWT endpoints. Add your domain to CORS_ALLOWED_ORIGINS or use a permissive local dev setting.

## Lint/Format

```bash
npm run lint
npm run format
```

## End-to-end smoke test

1) Start backend API on http://localhost:8000 and ensure CORS allows http://localhost:5173
2) In this frontend:
   - npm install
   - cp .env.example .env
   - npm run dev
3) Visit http://localhost:5173
4) Login with a valid Django user to obtain JWT
5) After auth:
   - Dashboard should load and later display KPIs
   - Targets list should fetch and render
   - Test Connection and Trigger Scan buttons will call endpoints and show toasts (coming as pages are filled)
6) Reports list should show items and allow downloading when implemented.

## Notes

- Tailwind config included; installing deps will remove TypeScript errors.
- If you change base URL, update .env and restart dev server.