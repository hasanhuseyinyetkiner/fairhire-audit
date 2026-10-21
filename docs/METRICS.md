# Evaluation evidence

Recorded against the native Windows path (`uv` + `pnpm` + SQLite). Methodology: [`MODEL_CARD.md`](MODEL_CARD.md).

This file records what was measured on the **audit tool**. It is not a fairness certificate for any hiring model.

---

## Synthetic fixture

Profile `similar_accuracy_different_errors` (`app/domain/synthetic.py`).

| Quantity | Verified value |
| --- | --- |
| Rows | 204 (`group_a` 100, `group_b` 100, `group_c` 4) |
| TN / FP / FN / TP | **91 / 11 / 31 / 71** |
| Overall accuracy | 162/204 ≈ 0.794 |
| `group_a` accuracy / FPR / FNR / selection | 0.80 / 0.20 / 0.20 / 0.50 |
| `group_b` accuracy / FPR / FNR / selection | 0.80 / 0.00 / 0.40 / 0.30 |
| `group_c` | *n* = 4 → suppressed (min *n* = 30) |
| DP / EO / EqOdds (eligible) | ≈ 0.20 |
| AIR (`group_b` / `group_a`) | ≈ 0.60; below 0.80 descriptive flag |

Two-group Fairlearn golden without `group_c` (*n* = 200): TN/FP/FN/TP = **90/10/30/70**; DP/EO/EqOdds ≈ 0.20.

Second profile `different_accuracy_similar_error_rates`: TPR/FPR matched; EO/EqOdds ≈ 0; DP ≈ 0.40.

---

## Environment

| Item | Value |
| --- | --- |
| Python | 3.12 |
| fairlearn | 0.15.0 |
| API / web ports | 8104 / 5104 |
| Bootstrap | iterations 1000, seed 20261020, unit `row` |
| Small-group minimum | `FAIRHIRE_SMALL_GROUP_MIN_N=30` |

---

## Backend verification

| Check | Result |
| --- | --- |
| `uv run ruff check app tests` | Pass |
| `uv run pytest -q` | **43 passed, 1 skipped** (Sprint 3–4 local; includes edge + fault injection) |

Covered: Fairlearn MetricFrame goldens, AIR / contingency / Fisher, bootstrap CIs (incl. AIR), score gate, cascade delete, Parquet, HTML/JSON report, bind policy, `/health` during audit, fault injection, tiny-sample honesty.

---

## Frontend verification

| Check | Result |
| --- | --- |
| `pnpm lint` / `typecheck` / `test` / `build` | Pass (**13** Vitest incl. ThresholdPage RTL); build OK |
| `pnpm test:e2e` | **3 passed** (workflow + threshold network-fail + a11y smoke) |
| `pnpm screenshots` | **1 passed**; PNGs refreshed under `docs/screenshots/` (2026-10-21) |

---

## Commands

```powershell
uv run ruff check app tests
uv run pytest -q
cd frontend
pnpm lint; pnpm typecheck; pnpm test; pnpm build
pnpm test:e2e
```

CI: `.github/workflows/ci.yml` (Postgres pytest, frontend build, Playwright `e2e`, `compose-smoke`).

---

## Limitations of this evaluation

- Results characterize the tool and synthetic fixtures, not production hiring models.
- Postgres-marked pytest skips unless `TEST_DATABASE_URL` is set.
- CMH is not implemented — see [`LIMITATIONS.md`](LIMITATIONS.md).
