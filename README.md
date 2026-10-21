<a id="readme-top"></a>

# FairHire Audit

Local workstation for auditing hiring-model **evaluation tables**: confusion counts, Fairlearn group disparities, adverse impact ratio (AIR / 4/5ths) with contingency tables, seeded bootstrap intervals, and a score-gated Threshold Lab. Accent `#2563EB`. Ports **8104** (API) / **5104** (web).

It is an audit tool, not a hiring decision engine. It does not claim bias-free status or legal certification.

[![CI](https://github.com/hasanhuseyinyetkiner/fairhire-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/hasanhuseyinyetkiner/fairhire-audit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/group-disparities-dark.png">
    <img alt="Group disparities with AIR contingency and Fairlearn differences" src="docs/screenshots/group-disparities-light.png" width="100%">
  </picture>
</p>

---

## Why it exists

Overall accuracy can look fine while group false-positive and false-negative rates diverge. Reviewers need transparent counts, defined rates (undefined when denominators are empty), and uncertainty — without a black-box “fairness score.”

**Users:** ML / people-analytics engineers with authorized or synthetic evaluation extracts.

---

## Capabilities

| Capability | Status |
| --- | --- |
| CSV / Parquet upload (size-capped; Parquet via `pyarrow`) | Shipped |
| Column mapping + score semantics gate | Shipped |
| Overall quality + Fairlearn group rates + DP / EO / EqOdds | Shipped |
| AIR (selection-rate ratio) / 4/5ths flag + 2×2 contingency + Fisher exact | Shipped |
| Small-*n* suppression + seeded bootstrap CIs (including AIR) | Shipped |
| Threshold Lab (live slider) + HTML/JSON report | Shipped |
| Intersection toggle (cell cap 200) | Shipped |
| Cascade delete + retention purge | Shipped |
| Cochran–Mantel–Haenszel across strata | Not implemented — see [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) |
| Side-by-side two-model comparison UI | Planned (domain deltas exist) |

---

## Architecture

```mermaid
flowchart TB
  subgraph client [Web :5104]
    UI[React · Import · Quality · Groups · Threshold · Report]
  end
  subgraph api [API :8104]
    HTTP[FastAPI]
    DOM[Domain: rates · fairness · air · bootstrap · compute]
    HTTP --> DOM
  end
  UI -->|JSON| HTTP
  DOM --> FL[Fairlearn 0.15]
```

React + Vite + TypeScript frontend; FastAPI + SQLAlchemy backend; Fairlearn / NumPy / SciPy / sklearn. SQLite demo or Postgres (CI). Details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Quick start

**Prerequisites:** Python 3.12 (`uv`), Node 24 + pnpm.

```powershell
# API → http://127.0.0.1:8104
uv sync
uv run python -m app

# Web → http://127.0.0.1:5104  (second terminal)
cd frontend
pnpm install
pnpm dev
```

| Service | URL |
| --- | --- |
| Web | http://127.0.0.1:5104 |
| OpenAPI | http://127.0.0.1:8104/docs |
| Health / ready | http://127.0.0.1:8104/health · `/ready` |

Copy [`.env.example`](.env.example) only for overrides. Defaults: loopback bind, SQLite `./data/fairhire.db`, bootstrap seed `20261020`. Non-loopback bind requires `FAIRHIRE_ALLOW_NETWORK_BIND=true`.

---

## 60-second demo

1. Start API + web; open http://127.0.0.1:5104.
2. **Import** → generate **Similar accuracy, different error rates** (204 synthetic rows).
3. Map columns (declare `score` as `probability` for Threshold Lab) → **Run audit**.
4. **Model quality** — CM TN/FP/FN/TP = **91 / 11 / 31 / 71**.
5. **Group disparities** — matched accuracy, diverging FPR/FNR; AIR for `group_b`/`group_a` ≈ **0.60** with contingency table; `group_c` suppressed.
6. **Threshold lab** — move the slider; metrics and AIR update live.
7. **Audit report** — download HTML/JSON (includes “cannot conclude”).

Playwright: `frontend/e2e/workflow.spec.ts`.

---

## Method notes

- **Undefined ≠ zero.** Empty denominators and small groups return `null` + reason; JSON never emits NaN for AIR.
- **Fairlearn dual-check.** Count-based selection / TPR / FPR / FNR must match `MetricFrame` on eligible groups.
- **AIR / 4/5ths.** Focal selection rate ÷ reference (highest eligible selection rate). The 0.80 flag is descriptive only.
- **Bootstrap.** Sampling unit = row; percentile 2.5 / 97.5; default *B* = 1000, seed `20261020`.
- **Score gate.** Threshold Lab opens only after `probability` (values in \[0, 1\]) or `ranking_score`.

Full formulas: [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md). Verified commands: [`docs/METRICS.md`](docs/METRICS.md).

---

## API (implemented)

| Method | Path |
| --- | --- |
| `GET` | `/health`, `/ready`, `/api/meta` |
| `GET` / `POST` | `/api/datasets`, `/api/datasets/synthetic` |
| `POST` | `/api/datasets/{id}/mapping`, `/api/audits` |
| `GET` | `/api/audits/{id}`, `/groups`, `/report.html`, `/report.json` |
| `POST` | `/api/audits/{id}/threshold-scenarios` |
| `DELETE` | `/api/datasets/{id}` (cascade) |

`GET /api/meta` returns `"decision_engine": false`.

---

## Testing

```powershell
uv run ruff check app tests
uv run pytest -q
cd frontend
pnpm lint; pnpm typecheck; pnpm test; pnpm build
```

See [`docs/METRICS.md`](docs/METRICS.md) for the latest verified results.

---

## Security and limitations

- Demo data is **synthetic**. Do not publish real evaluation extracts.
- Loopback by default; **no auth in MVP**.
- Fairness metrics may conflict; observed differences are measurements, not causal or legal conclusions.
- Never claims: bias-free, compliant, certified, or fit for automated employment decisions.

Details: [`docs/SECURITY.md`](docs/SECURITY.md), [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

---

## Documentation

| Doc | Contents |
| --- | --- |
| [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md) | Methodology: formulas, bootstrap, AIR, suppression |
| [`docs/METRICS.md`](docs/METRICS.md) | Verified commands and fixture numbers |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Runtime topology and layers |
| [`docs/ENGINEERING_DECISIONS.md`](docs/ENGINEERING_DECISIONS.md) | Design decisions |
| [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) | Gaps (including CMH) |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Threat boundary, cascade delete, purge |
| [`docs/GITHUB_METADATA.md`](docs/GITHUB_METADATA.md) | About blurb, topics |
| [`frontend/README.md`](frontend/README.md) | Web scripts and routes |

License: [MIT](LICENSE).

<p align="right"><a href="#readme-top">↑ back to top</a></p>
