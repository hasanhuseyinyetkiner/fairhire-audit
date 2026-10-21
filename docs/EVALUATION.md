# Evaluation / methodology provenance

Versioned notes for how FairHire Audit evidence is produced and checked. Methodology source of truth: [`MODEL_CARD.md`](MODEL_CARD.md) (`METHODOLOGY_VERSION` in `app/domain/definitions.py`).

| Field | Current |
| --- | --- |
| Methodology version | `0.1.0` |
| Code version | `0.1.0` (`app.__version__`) |
| Exposed via | `GET /api/meta` → `methodology_version`; audit `provenance.methodology_version` |
| CMH | **Not implemented** (`cmh_available: false`) — no multi-stratum design input |
| Null semantics | JSON `null` = undefined/withheld; **not** a zero rate |

## What “pass” means here

- Synthetic fixture rates and Fairlearn dual-checks match [`METRICS.md`](METRICS.md).
- Bootstrap percentile intervals use row resampling; width = upper − lower under that procedure only.
- Threshold Lab scenarios are **point estimates only** (no live CI) and do not change a deployed model.

## Bump rules

Increment `METHODOLOGY_VERSION` when any of these change: rate formulas, AIR/reference rule, small-*n* suppression, bootstrap sampling unit/percentiles/min finite replicates, or Fairlearn disparity method args.

## Related

- Measured timing (separate from correctness): [`PERFORMANCE_BASELINE.md`](PERFORMANCE_BASELINE.md)
- Limits: [`LIMITATIONS.md`](LIMITATIONS.md)
