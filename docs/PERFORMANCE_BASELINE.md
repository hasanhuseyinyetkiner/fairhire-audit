# Performance baseline

Measured locally on this host. Not a fairness certificate. Numbers are wall-clock for one domain path only.

## Hardware / OS

| Item | Value |
| --- | --- |
| OS | Windows 11 (`Windows-11-10.0.26300-SP0`) |
| Arch | AMD64 |
| CPU | AMD Ryzen 5 5600H with Radeon Graphics |
| RAM | ≈16 GB (16 475 729 920 bytes reported) |
| Python | 3.12.10 |
| Docker | **Unavailable** on this host (Compose not measured here) |

## Path under test

`app.domain.compute.compute_analysis` on synthetic profile `similar_accuracy_different_errors` (204 rows), after `prepare_frame` with `min_n=30`.

| Parameter | Value |
| --- | --- |
| Seed | `20261020` |
| Bootstrap iterations | `200` (cap 1000) |
| Warmup | 1 discarded run |
| Repetitions | 7 |

## Command

```powershell
uv run python -c "<script timing compute_analysis with seed=20261020, iterations=200, reps=7>"
```

(Exact script used during Sprint 3–4: prepare fixture → warmup → `time.perf_counter()` around `compute_analysis`.)

## Results (seconds)

| Stat | Value |
| --- | --- |
| Samples | 0.4005, 0.2646, 0.3116, 0.2591, 0.2750, 0.2518, 0.2426 |
| Mean | **0.2865 s** |
| Stdev | 0.0549 s |
| Min | 0.2426 s |
| Max | 0.4005 s |

## Interpretation

- Baseline is for **metric recomputation including 200-row bootstrap**, not Threshold Lab point-estimate POSTs.
- First sample after process start can be slower (import/cache effects); mean includes that sample.
- Re-measure after changing bootstrap vectorization, Fairlearn calls, or default iteration count; update this file with new hardware/command/seed/reps.
