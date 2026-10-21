# FairHire Audit — frontend

React + Vite + TypeScript UI for the local FairHire Audit workstation. The web app talks to the FastAPI backend on loopback (`8104`) via the Vite proxy.

## Prerequisites

- Node 24 and pnpm
- Backend running at `http://127.0.0.1:8104` (see root [README](../README.md))

## Scripts

| Command | Purpose |
| --- | --- |
| `pnpm install` | Install dependencies from the lockfile |
| `pnpm dev` | Dev server at `http://127.0.0.1:5104` (proxies `/api`, `/health`, `/ready`) |
| `pnpm lint` | ESLint on `src` |
| `pnpm typecheck` | `tsc --noEmit` |
| `pnpm test` | Vitest unit tests |
| `pnpm build` | Typecheck + production build |
| `pnpm test:e2e` | Playwright workflow (`e2e/workflow.spec.ts`) |
| `pnpm screenshots` | Capture light/dark PNGs into `docs/screenshots/` |

## Pages (audit flow)

Import → Map → Model quality → Group disparities → Threshold Lab → Audit report.

Threshold Lab stays locked until a score column is mapped and declared as `probability` or `ranking_score`. When open, the slider updates metrics (and AIR) live.

## Notes

- Accent `#2563EB`. Light and dark themes.
- This UI is part of a **single-operator local demo**. There is no authentication; do not expose the port beyond loopback without operator controls.
- Screenshots and e2e expect the API on `:8104` and the web app on `:5104`.
