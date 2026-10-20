# GitHub repository metadata

Use these values when configuring the public GitHub repository settings (About sidebar, topics, social preview).

## About description

GitHub limit: 350 characters. Suggested:

```text
Transparent audits for hiring ML models: group metrics, confidence intervals and threshold trade-offs.
```

Alternate (if you want the audit-tool framing explicit):

```text
Local audit workstation for hiring-model evaluation tables — Fairlearn disparities, bootstrap CIs, score-gated thresholds. Not a decision engine.
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

Prefer a light screenshot from `docs/screenshots/group-disparities-light.png` (shows matched accuracy with diverging error rates + small-*n* suppression) or the banner `docs/assets/banner-light.svg`.

## Visibility and release notes

- Public demo data must remain **synthetic only**.
- Do not publish uploaded evaluation files, SQLite databases, or report exports that contain real candidate data.
- License: **pending owner decision** (no `LICENSE` file in-repo until decided).
- Pin releases only after CI is green on the tagged commit; follow [`RELEASE_READINESS.md`](RELEASE_READINESS.md).
- Document ports **8104** / **5104** and accent `#2563EB` in release notes if UI screenshots are attached.
- Suggested first release tag narrative: “Local demo MVP — evaluation-table audits with Fairlearn + bootstrap; not a hiring decision engine.”
- Do not claim bias-free, compliant, certified, or multi-user security. Offline local demo ≠ secured SaaS.

## Documentation map (for About / wiki links)

| Path | Purpose |
| --- | --- |
| `README.md` | Product overview + quick start |
| `docs/MODEL_CARD.md` | Methodology / intended use |
| `docs/METRICS.md` | Verified commands and fixture numbers |
| `docs/ARCHITECTURE.md` | Runtime topology |
| `docs/SECURITY.md` | Threat boundary + purge CLI |
| `docs/RELEASE_READINESS.md` | Pre-tag checklist |
| `frontend/README.md` | Web app scripts and routes |
| `docs/PRODUCT_SPEC.md` | Historical brief only |

## Pin / portfolio rationale

FairHire Audit demonstrates **responsible-ML evaluation engineering**: explicit statistical assumptions, conflicting fairness criteria, uncertainty quantification, and honest “cannot conclude” boundaries — complementary to retrieval (Policy Copilot), process mining, scheduling, and skill-graph projects in the same portfolio.
