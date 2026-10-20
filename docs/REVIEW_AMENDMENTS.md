# Design review amendments (binding)

These amendments come from the pre-implementation design review (2026-10-20). They **override** any conflicting text in `docs/PRODUCT_SPEC.md`. IDs refer to review findings.

## Environment and delivery (all products)

- **[C-1] No Docker, no local PostgreSQL.** The dev machine is Windows 11 with `uv` (use Python 3.12: `uv python pin 3.12`), Node 24 and pnpm. Provide a **native dev path that is verified locally** (`uv run ...` backend, `pnpm dev` frontend). Local tests may use SQLite through the same SQLAlchemy models; PostgreSQL-only behavior gets a SQLite-safe fallback or a `@pytest.mark.postgres` marker that runs in CI. Write `compose.yaml` and Dockerfiles, but they are verified **only in CI** by a `compose-smoke` job; the README must say so until that job passes.
- **CI** (GitHub Actions, `ubuntu-latest`): backend Ruff + pytest against a PostgreSQL service container; frontend ESLint + `tsc` + Vitest + build; `compose-smoke` (`docker compose up --build -d`, wait for `/ready`, then `docker compose down -v`).
- **[C-6] Ports:** API `8104`, web `5104`, PostgreSQL host port `5404`.
- **[C-2] Loopback by default.** Uvicorn binds `127.0.0.1`; Compose port mappings use `127.0.0.1:` prefixes. No auth in the MVP, so startup refuses a non-loopback host unless `ALLOW_NETWORK_BIND=true` is set explicitly. `APP_ENV=demo` shows a persistent "Local demo · synthetic data" banner.
- **[C-3] No CPU-heavy work on the event loop.** Bootstrap CIs and threshold scenarios run via `run_in_threadpool` or a process pool; bootstrap iterations are capped (default 1000) and seeded. Long audit runs are persisted rows with `status` and `heartbeat_at`; a startup reaper marks stale `RUNNING` runs `FAILED` with a reason. Add a test proving `/health` stays responsive during an audit.
- **[C-4] Licensing and git.** Do **not** add a `LICENSE` file; the README states "License: pending owner decision". Do not create remotes or push. Commit locally in small conventional commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`, `ci:`).
- **Brand:** accent color `#2563EB` (blue). Light and dark themes.

## Product-specific

- **[FHA-1] Explicit score gate.** The Threshold Lab is enabled only when the score column is numeric and the user declares its semantics (`probability` or `ranking_score`); declared probabilities must lie in [0, 1]. For probabilities, show the Brier score and a reliability table/plot. The system never labels a score "calibrated" by itself; it shows evidence and states why the lab is enabled or disabled.
- **[FHA-2] Real deletion and retention.** Deleting a dataset cascades to every derived row (runs, metrics, intervals, scenarios, reports) and to stored files and exports; a test asserts nothing remains. `DATA_RETENTION_DAYS` plus a purge command. Never log raw rows or sensitive attribute values.
- **[FHA-3] Parquet needs an engine.** If Parquet is supported, add `pyarrow` explicitly and an integration test that uploads a Parquet file in a clean environment.
- **Verify Fairlearn APIs** (`MetricFrame`, `demographic_parity_difference`, `equalized_odds_difference`, and an equal-opportunity calculation) against the installed version; golden tests compare them with hand-computed values.
