# Security, privacy, and limitations

FairHire Audit is a **local demo / single-operator audit workstation**, not a multi-tenant SaaS. Running offline on loopback does **not** equal a multi-user secured deployment: there is **no authentication** in MVP. Anyone who can reach the HTTP port can call the API.

This document states what is enforced in code and what remains out of scope.

## Threat boundary (MVP)

| Control | Status |
| --- | --- |
| Default bind `127.0.0.1` | Enforced in `app/settings.py` via `enforce_bind` |
| Non-loopback bind | Requires explicit `FAIRHIRE_ALLOW_NETWORK_BIND=true` |
| Authentication / authorization | **Not implemented** |
| TLS termination | Not provided by the app; use a reverse proxy if you expose beyond loopback |
| Secrets in repo | `.env` is gitignored; `.env.example` has no credentials |

Compose maps ports as `127.0.0.1:8104`, `127.0.0.1:5104`, `127.0.0.1:5404` even when the container process listens on `0.0.0.0` inside the network namespace.

## Data handling

- Uploads are size-capped (`FAIRHIRE_MAX_UPLOAD_BYTES`, default 20 MiB) and row-capped (`max_rows` 50_000).
- Allowed tabular formats: CSV and Parquet (Parquet via pinned `pyarrow`).
- Stored files use application-managed paths under `FAIRHIRE_UPLOAD_DIR` / `FAIRHIRE_REPORT_DIR` — not user-supplied paths.
- **Cascade delete:** `DELETE /api/datasets/{id}` removes the dataset row, derived audit runs, metrics, intervals, threshold scenarios, reports, and on-disk upload/report files (`app/services/datasets.py::delete_dataset`). Covered by API tests (FHA-2).
- **Retention purge:** `FAIRHIRE_DATA_RETENTION_DAYS` (default **30**) is mirrored into `AuditSetting.data_retention_days`. Operator command:

  ```powershell
  uv run python -m app.cli purge
  ```

  Implementation: `purge_expired` deletes datasets whose `created_at` is older than the retention window (same cascade as manual delete). Prints `purged <n>`. This is **age-based cleanup**, not a GDPR-style subject-access workflow. **Startup does not purge** — `app/main.py` runs `ensure_settings` and the stale-run reaper only; the operator must schedule the CLI.
- Logging must not include raw evaluation rows or sensitive attribute values (operator discipline + code paths avoid dumping frames).

## Sensitive attributes

- Group columns are used **only when the operator maps them** for an authorized audit.
- The system does **not** infer protected characteristics from names, photos, free text, or other proxies.
- Synthetic demo profiles use arbitrary labels (`group_a`, `group_b`, `group_c`) — not real populations.
- Small-cell suppression (`FAIRHIRE_SMALL_GROUP_MIN_N`, default 30) reduces accidental publication of tiny cells; it is a statistical and privacy hygiene control, **not** a legal safe harbor.

## What this is not

- Not a compliance certification, bias-free certificate, or employment-law opinion.
- Not an automated hiring, ranking, or rejection engine (`GET /api/meta` → `"decision_engine": false`).
- Not a substitute for human review, counsel, or a formal model risk program.
- Not multi-user access control: local offline use still trusts the OS user account and filesystem ACLs.
- Public demo data must remain **synthetic**. Do not publish uploaded evaluation files, SQLite databases, or report exports that contain real candidate data.

## Known limitations (honesty)

- No multi-user auth, operator audit logging, or field-level encryption at rest beyond OS filesystem controls.
- Bootstrap intervals assume exchangeable rows; clustering and selection into the evaluation set are not modeled.
- Fairness criteria can conflict; the product surfaces that conflict rather than resolving it. Observed disparities are **measurements**, not causal or legal conclusions.
- Timestamp columns are stored in the mapping and are unused in rates (no temporal drift analysis in MVP).
- Intersectional views can explode cell counts; the API rejects intersections with more than 200 cells.

## Operator checklist before any non-demo use

1. Keep the bind on loopback or put the service behind authenticated reverse proxy + TLS.
2. Use only authorized evaluation extracts; minimize columns.
3. Delete datasets after the review (`DELETE /api/datasets/{id}`); schedule `uv run python -m app.cli purge` yourself for age-based cleanup (nothing auto-purges on a timer).
4. Treat HTML/JSON reports as sensitive artifacts with the same retention as the source table.
5. Do not paste protected-attribute values into tickets, screenshots, or public READMEs.
6. Do not equate “runs offline on my laptop” with multi-user security.
