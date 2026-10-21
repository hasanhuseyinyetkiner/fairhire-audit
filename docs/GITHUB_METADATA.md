# GitHub repository metadata

Use these values when configuring the public GitHub repository settings (About sidebar, topics, social preview).

## About description

GitHub limit: 350 characters. Suggested:

```text
Local audit workstation for hiring-model evaluation tables: Fairlearn disparities, AIR/4/5ths, bootstrap CIs, score-gated thresholds. Not a decision engine.
```

## Topics

```text
responsible-ai
fairness
fairlearn
model-audit
machine-learning
statistics
fastapi
react
```

## Homepage URL

Leave empty unless a public demo URL is published later. Do not invent a live-demo link.

## Social preview

Prefer `docs/screenshots/group-disparities-light.png` or `docs/assets/banner-light.svg`.

## Visibility and release notes

- Public demo data must remain **synthetic only**.
- Do not publish uploaded evaluation files, SQLite databases, or report exports with real candidate data.
- License: **MIT** ([`LICENSE`](../LICENSE)).
- Document ports **8104** / **5104** and accent `#2563EB` when attaching screenshots.
- Do not claim bias-free, compliant, certified, or multi-user security.

## Documentation map

| Path | Purpose |
| --- | --- |
| `README.md` | Overview + quick start |
| `docs/MODEL_CARD.md` | Methodology |
| `docs/METRICS.md` | Verified commands and fixture numbers |
| `docs/ARCHITECTURE.md` | Runtime topology |
| `docs/LIMITATIONS.md` | Gaps (including CMH) |
| `docs/SECURITY.md` | Threat boundary + purge CLI |
| `frontend/README.md` | Web app scripts and routes |

## Pin / portfolio rationale

FairHire Audit demonstrates evaluation engineering: explicit statistical assumptions, conflicting fairness criteria, AIR with contingency tables, uncertainty quantification, and documented “cannot conclude” boundaries.
