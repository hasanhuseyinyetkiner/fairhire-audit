# Limitations

Engineering boundaries of FairHire Audit. Companion methodology: [`MODEL_CARD.md`](MODEL_CARD.md).

## Scope

- Local single-operator demo / workstation. MVP has **no authentication**.
- Evaluation-table audits only. Not a hiring decision engine, ranking service, or production threshold deployer.
- Does not claim bias-free status, legal compliance, or certification for any model under review.

## Statistical gaps

| Topic | Status |
| --- | --- |
| Fairlearn DP / EO / EqOdds | Implemented; dual-checked against count-based rates |
| AIR (selection-rate ratio) / 4/5ths descriptive flag | Implemented with bootstrap CIs |
| 2×2 selection contingency + Fisher exact (two-sided) | Implemented when cell counts are integers |
| Cochran–Mantel–Haenszel (CMH) | **Not implemented** — requires a multi-stratum design (e.g. job family × group) the product does not yet accept. Absence is not a zero association. |
| Causal attribution | Out of scope |
| Protected-attribute inference | Out of scope |

## Rate and sample-size behavior

- Zero denominators → `null` + reason (never coerced to 0; never NaN in JSON).
- Groups below `FAIRHIRE_SMALL_GROUP_MIN_N` (default 30) are suppressed from rates and disparity / AIR summaries.
- Bootstrap assumes exchangeable rows; clustered applicants typically make intervals too narrow.

## Data

- Public demos and screenshots use deterministic **synthetic** profiles only.
- Do not publish real evaluation extracts, databases, or reports.
