# Measured verification (FairHire Audit)

Recorded on 2026-10-20 against the native Windows path (`uv` + `pnpm` + SQLite). Docker Compose is written for CI `compose-smoke` only; Docker is not available on this machine.

## Environment

| Item | Value |
| --- | --- |
| Python | 3.12 (`uv python pin 3.12`) |
| fairlearn | 0.15.0 |
| pyarrow | 26.0.0 |
| API port | 8104 |
| Web port | 5104 |
| Compose Postgres host port | 5404 |

## Backend

| Check | Result |
| --- | --- |
| `uv run ruff check app tests` | All checks passed |
| `uv run pytest -q` | 17 passed, 1 skipped (`postgres` marker without `TEST_DATABASE_URL`) |

Covered locally: Fairlearn MetricFrame golden values, bootstrap CIs, FHA-1 score gate / Threshold Lab, FHA-2 cascade delete + retention purge, FHA-3 Parquet upload via pyarrow, HTML/JSON report (no bias-free certificate), bind policy, stale-run reaper, `/health` during audit.

## Frontend

| Check | Result |
| --- | --- |
| `pnpm lint` | Pass |
| `pnpm typecheck` | Pass |
| `pnpm test` (Vitest) | 3 passed |
| `pnpm build` | Pass |

## End-to-end

| Check | Result |
| --- | --- |
| Playwright `e2e/workflow.spec.ts` | **1 passed** (import → map → quality → groups → HTML report export) |

## Amendments checklist

| ID | Status |
| --- | --- |
| FHA-1 Explicit score gate | Implemented + tested |
| FHA-2 Cascade delete / retention | Implemented + tested |
| FHA-3 Parquet + pyarrow | Dependency pinned; upload integration test green |
| C-1 Native path + compose for CI | Native verified; `compose.yaml` + `compose-smoke` job present |
| C-2 Loopback bind | Enforced; Compose uses `127.0.0.1:` prefixes |
| C-3 Threadpool bootstrap + reaper | Implemented + tested |
| C-6 Ports 8104 / 5104 / 5404 | Wired in settings, Vite, compose, Playwright |
