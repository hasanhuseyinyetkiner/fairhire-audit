# Limitations

- Metrics on tiny groups may be undefined (`null` + reason). Undefined is not zero.
- AIR / four-fifths flags are **descriptive**; they are not legal certification or proof of discrimination.
- Bootstrap intervals widen or degenerate with small *n*; uncertainty must remain visible. CI width = upper − lower under row resampling only.
- Fairness metrics can disagree; conflicting signals are expected, not a UI bug.
- Threshold Lab requires a score gate (`probability` or `ranking_score`); without scores the lab stays closed. Live threshold metrics are **point estimates only** (no bootstrap CI on the slider path).
- Cochran–Mantel–Haenszel (CMH) is **not implemented** — no multi-stratum design input.
- Docker Compose smoke is CI-only; this workstation may not have Docker (local Compose = blocked).
- No automated employment decisions are produced or recommended.
- Performance numbers in [`PERFORMANCE_BASELINE.md`](PERFORMANCE_BASELINE.md) characterize one measured path on one machine — not SLOs.
