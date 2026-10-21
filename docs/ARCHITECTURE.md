# Architecture

Local demo: React + Vite on **5104**, FastAPI on **8104**, SQLite by default (PostgreSQL in CI/Compose).

## Topology

```text
UI (Import · Quality · Groups · Threshold · Report)
  → FastAPI HTTP
    → Domain (rates · fairness · AIR · bootstrap · compute)
      → Fairlearn MetricFrame dual-check
      → SQLAlchemy persistence
```

## Layering

| Layer | Responsibility |
| --- | --- |
| HTTP | Dataset/audit routes, threshold scenarios, HTML/JSON reports |
| Domain | Confusion matrix, selection rates, demographic parity / equalized odds style diffs, AIR, bootstrap CIs, Fisher exact where used |
| Persistence | Datasets, mappings, immutable-enough audit snapshots for the demo |
| UI | Workbench pages wired to live API; no fabricated chart series |

## Invariants

- Empty denominators → `null` + reason (never NaN / Infinity / fake zero in JSON).
- Score gate must pass before Threshold Lab mutates cutoffs.
- Dual-check: count-based rates must match Fairlearn `MetricFrame` on eligible groups.
