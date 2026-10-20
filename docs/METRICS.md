# Evaluation evidence

Recorded on **2026-10-20** (re-verified same day after documentation polish) against the native Windows path (`uv` + `pnpm` + SQLite). Docker Compose is written for CI `compose-smoke`; Docker is not available on this authoring machine.

**Methodology** (intended use, formulas, bootstrap, suppression, interpretation limits): [`MODEL_CARD.md`](MODEL_CARD.md).

This file records **what was measured** on the audit *tool*. It is not a fairness certificate for any hiring model. Observing a disparity is measurement — not causation, compliance, or certification.

---

## Synthetic fixture (verified against code)

Profile `similar_accuracy_different_errors` (`app/domain/synthetic.py`).

| Quantity | Verified value |
| --- | --- |
| Rows | 204 (`group_a` 100, `group_b` 100, `group_c` 4) |
| TN / FP / FN / TP | **91 / 11 / 31 / 71** |
| Overall accuracy | 162/204 ≈ 0.794 |
| `group_a` accuracy / FPR / FNR | 0.80 / 0.20 / 0.20 |
| `group_b` accuracy / FPR / FNR | 0.80 / 0.00 / 0.40 |
| `group_c` | *n* = 4 → suppressed at min *n* = 30 |
| DP / EO / EqOdds (eligible groups only) | ≈ 0.20; excludes `group_c` |

Hand-checked via `tests/test_golden.py::test_synthetic_profile_matches_hand_story` and a direct count from `similar_accuracy_different_errors()` (TN/FP/FN/TP = 91/11/31/71; group sizes 100/100/4).

**Separate** two-group Fairlearn golden **without** `group_c` (*n* = 200): TN/FP/FN/TP = **90/10/30/70**; DP/EO/EqOdds ≈ 0.20 (`test_hand_counted_two_group_rates_and_fairlearn`). Do not mix those CM cells with the 204-row demo profile.

Second profile `different_accuracy_similar_error_rates`: TPR/FPR matched (~0.90 / ~0.40) while accuracy diverges (~0.87 vs ~0.63); EO/EqOdds ≈ 0, DP ≈ 0.40.

---

## Environment

| Item | Value |
| --- | --- |
| Python | 3.12 (`uv python pin 3.12`) |
| fairlearn | 0.15.0 |
| API / web ports | 8104 / 5104 |
| Compose Postgres host port | 5404 |
| Bootstrap defaults | iterations 1000, seed 20261020, unit `row`, method `percentile` |
| Small-group minimum | `FAIRHIRE_SMALL_GROUP_MIN_N=30` |

---

## Backend verification

| Check | Result |
| --- | --- |
| `uv run ruff check app tests` | All checks passed |
| `uv run pytest -q` | **17 passed, 1 skipped** (`postgres` marker without `TEST_DATABASE_URL`) |

Covered locally: Fairlearn MetricFrame goldens, bootstrap CIs, FHA-1 score gate, FHA-2 cascade delete + retention purge, FHA-3 Parquet via pyarrow, HTML/JSON report (no bias-free certificate), bind policy, stale-run reaper, `/health` during audit.

---

## Frontend verification

| Check | Result |
| --- | --- |
| `pnpm lint` | Pass |
| `pnpm typecheck` | Pass |
| `pnpm test` (Vitest) | 3 passed |
| `pnpm build` | Pass |

---

## End-to-end

| Check | Result |
| --- | --- |
| Playwright `e2e/workflow.spec.ts` | Previously **1 passed** (import → map → quality → groups → HTML report). Re-run in the 2026-10-20 docs pass hit **Node OOM** on this machine before the worker finished — environmental blocker, not an assertion failure. Re-run when memory allows. |
| Screenshot capture `pnpm screenshots` | Light/dark PNGs under `docs/screenshots/` (authentic captures present) |

```powershell
uv run ruff check app tests
uv run pytest -q
cd frontend
pnpm lint; pnpm typecheck; pnpm test; pnpm build
pnpm test:e2e
```

CI (`.github/workflows/ci.yml`): backend Ruff + pytest against PostgreSQL; frontend ESLint + `tsc` + Vitest + build; `compose-smoke`.

---

## Amendments checklist

| ID | Status |
| --- | --- |
| FHA-1 Explicit score gate | Implemented + tested |
| FHA-2 Cascade delete / retention | Implemented + tested |
| FHA-3 Parquet + pyarrow | Dependency pinned; upload integration test green |
| C-1 Native path + compose for CI | Native verified; `compose.yaml` + `compose-smoke` present |
| C-2 Loopback bind | Enforced; Compose uses `127.0.0.1:` prefixes |
| C-3 Threadpool bootstrap + reaper | Implemented + tested |
| C-6 Ports 8104 / 5104 / 5404 | Wired in settings, Vite, compose, Playwright |

---

## Limitations of this evaluation

- Results characterize the **tool and synthetic fixtures**, not production hiring models or real applicant populations.
- Local pytest skips the Postgres-marked test unless `TEST_DATABASE_URL` is set; CI runs it.
- Compose smoke was not re-run on this Docker-less machine in the documentation pass; native path + unit/integration evidence above stands.
- Disparity figures are observational measurements — not causal findings, compliance proofs, or certifications.
