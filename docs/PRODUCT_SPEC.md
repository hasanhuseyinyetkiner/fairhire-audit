# CURSOR AGENT PROMPT — FAIRHIRE AUDIT

Act as a senior responsible-ML engineer, statistical methodologist, Python API engineer, and open-source maintainer. Build **FairHire Audit**, an evidence-based model performance and group-disparity auditing web application. Implement real code, tests, report exports and a polished public GitHub README. Read `.cursor/rules/*.mdc` if present. This is an **audit tool**, not a hiring decision engine.

## Product value

Teams upload **authorized or synthetic** model evaluation data and inspect confusion matrices, group-specific error rates, fairness metrics, uncertainty and threshold sensitivity. Explain mathematical assumptions clearly so users do not mistake a single fairness score for a legal or ethical verdict.

**Differentiator:** confidence intervals + sample-size flags + sensitivity analysis + reproducible audit report, with a visually striking side-by-side comparison UI.

## Stack

- Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, PostgreSQL, pandas, NumPy, scikit-learn, Fairlearn, SciPy (or statsmodels where justified), pytest, Ruff.
- React + Vite + TypeScript, Tailwind, Recharts, TanStack Query, React Router, Lucide, Vitest, Playwright.
- Docker Compose and GitHub Actions.

## Data model

Dataset, ColumnMapping, AuditRun, AuditMetric, GroupMetric, ConfidenceInterval, ThresholdScenario, AuditReport and AuditSetting. Accept CSV/Parquet with user-selected columns: `y_true` (actual outcome), `y_pred` (predicted class) or `score` (optional probability), sensitive group column(s) **for permitted auditing**, optional sample weights, optional timestamp. Do not include actual names or personal identifiers in synthetic demo data.

## Core workflows

1. Dataset upload, column mapping and schema preview; validation detects missingness, invalid binary labels, class imbalance and non-numeric scores.
2. Audit overview: dataset sizes, class distributions, global confusion matrix, balanced accuracy, precision, recall, FPR, FNR and group rates.
3. Group disparity analysis with Fairlearn MetricFrame and correctly defined demographic parity difference, equal opportunity difference, equalized odds difference; ability to switch metric direction and show formula.
4. Confidence intervals via seeded bootstrap when conditions permit. Warn and withhold values for tiny groups, one-class groups and undefined denominators; never silently substitute zero.
5. Score threshold slider only when properly calibrated/interpretable probability or continuous score exists, showing resulting tradeoffs and group metrics. Clearly distinguish scoring threshold simulation from real deployment action.
6. Intersectional groups as a controlled optional view with small-cell suppression, privacy warnings and sample-size requirements.
7. Model comparison for two predictions on matched evaluation rows and common labels; error/cost differences and metric confidence intervals where applicable.
8. Reproducible report export to HTML + JSON with run metadata, metric definitions, threshold, code version, data provenance, assumptions and unresolved risks. No automatic bias-free certificate.

## Analytical correctness

- Explicit confusion matrix convention and formula definitions for each metric.
- Distinguish demographic parity, equalized odds, equal opportunity and calibration; note that fairness criteria can conflict.
- Fairlearn MetricFrame for group rates; verify package APIs against installed versions.
- Show both overall and per-group sample sizes next to all plotted rates.
- Use bootstrap CI responsibly: specify sampling unit, resampling method, iterations and seed. Report CI as uncertainty, not proof of fairness.
- Never infer the cause of disparity from these metrics alone; warn about selection effects, unobserved confounding, label bias and base-rate differences.
- A missing protected attribute can limit the audit; do not infer protected group from names, photos or other proxies.

## Design

Build a refined multi-panel interface: Import → Model Quality → Group Disparities → Threshold Lab → Audit Report. Provide accessible charts with readable tooltips, CSV/HTML export, context on every complex metric, provenance panel, loading/error/empty states. Responsive design; use actual app screenshots for README only.

## API suggestions

`POST /api/datasets`, `GET /api/datasets/{id}/quality`, `POST /api/audits`, `GET /api/audits/{id}`, `GET /api/audits/{id}/groups`, `POST /api/audits/{id}/threshold-scenarios`, `GET /api/audits/{id}/report.html`, `GET /health`. Document normalized schemas, optional fields and validation failures.

## Testing

- Golden fixtures with manually computed confusion matrices, precision/recall, differences and expected undefined cases.
- Tests for empty CSV, missing columns, missing group, negative or >1 probabilities, single-class input, imbalanced groups, small-cell suppression and reproducibility.
- Integration tests from upload to full report; browser E2E for dataset import -> group comparisons -> export.
- Include synthetic examples where overall accuracy is similar but group error rates differ, and vice versa; verify dashboard narrative doesn't mislead.

## Security / ethics

Sensitive audit data must be access-controlled, minimally retained and deletable. Public demo must contain synthetic data only. This tool is not a compliance certification, cannot replace expert review and must not feed group attributes into candidate ranking or automate employment outcomes. Security and privacy are mandatory in README.

## GitHub-quality README

English hero: "Audit the model. Understand the trade-offs. Show your evidence." Demonstrate a real disparity visualization screenshot, clear use case, reproducible synthetic dataset, Mermaid metrics pipeline, detailed mathematical definitions, fully verified Quick Start, report screenshots, actually measured test status, sample-size caveats, privacy safeguards, limitations, contributor guide and license. The README must compare what this app measures vs what it **cannot** conclude. Add `docs/GITHUB_METADATA.md`: description `Transparent audits for hiring ML models: group metrics, confidence intervals and threshold trade-offs.`; topics `responsible-ai`, `fairness`, `fairlearn`, `model-audit`, `machine-learning`, `statistics`, `fastapi`, `react`.

## Phases / definition of done

Phase 1: app shell, secure CSV import, deterministic synthetic datasets, clear schema and clean Docker start.
Phase 2: independently verified overall/group metrics and Fairlearn integration; known-value tests.
Phase 3: threshold sensitivity, seeded confidence intervals, comparison and downloadable truthful reports.
Phase 4: accessible UX, reproducible evaluations, E2E smoke test, real screenshot, detailed docs/README, CI and clean install verification.

Be proactive but do not invent unsupported claims, audit outcomes or benchmark metrics. Execute tests and report exact failures and successes. Never push code/deploy without explicit permission.
