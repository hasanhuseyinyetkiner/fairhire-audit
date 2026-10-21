# Model card — FairHire Audit

Methodology for the audit tool (version `0.1.0`). Verification commands: [`METRICS.md`](METRICS.md). Sources of truth: `app/domain/definitions.py`, `rates.py`, `fairness.py`, `air.py`, `bootstrap.py`, `compute.py`, `synthetic.py`.

---

## 1. Intended use

| In scope | Out of scope |
| --- | --- |
| Inspect authorized or synthetic hiring-model *evaluation* tables (`y_true`, `y_pred` and/or `score`, group columns, optional weights) | Candidate ranking, hire/reject scoring, production threshold deployment |
| Confusion counts, classification rates, Fairlearn DP / EO / EqOdds, AIR / 4/5ths, contingency tables | Inferring protected attributes from proxies |
| Small-cell flags, undefined denominators, conflicting-criteria warnings | Causal attribution |
| Seeded bootstrap percentile intervals under documented assumptions | Legal/compliance certification or “bias-free” claims |
| Threshold Lab simulations after explicit `probability` or `ranking_score` | Treating simulated cutoffs as deployable policy |
| Local single-operator demo | Multi-tenant SaaS (MVP has no auth) |

---

## 2. Data assumptions

- Input is an evaluation table. Rows are treated as exchangeable for bootstrap (§7).
- Labels are binary after mapping; positive class = declared `positive_label`.
- Group columns are operator-mapped audit attributes. Synthetic labels (`group_a`, …) are arbitrary ids.
- Optional `sample_weight` reweights counts; default weight = 1.
- Optional `timestamp` is stored and unused in rates.
- Public demos use deterministic synthetic profiles only.

---

## 3. Labels and score semantics

| Field | Meaning |
| --- | --- |
| `y_true` | Observed binary outcome |
| `y_pred` | Predicted class (or derived from score when semantics allow) |
| `score` + `probability` | Values in \[0, 1\]; Brier + reliability table are descriptive; never auto-labeled “calibrated” |
| `score` + `ranking_score` | Opens Threshold Lab; skips Brier |
| Undeclared score | Threshold Lab locked |

`GET /api/meta` → `"decision_engine": false`.

---

## 4. Confusion-matrix convention

Matches `sklearn.metrics.confusion_matrix(..., labels=[negative, positive])`:

- Rows = actual; columns = predicted, order `[negative, positive]`.
- `(0,0)` TN, `(0,1)` FP, `(1,0)` FN, `(1,1)` TP.

Fixture `similar_accuracy_different_errors` (204 rows): TN/FP/FN/TP = **91 / 11 / 31 / 71**.

---

## 5. Rate formulas

Undefined when denominator is zero → `null` + `undefined_denominator` (not coerced to 0; never NaN).

| Metric | Formula |
| --- | --- |
| Accuracy | (TP + TN) / N |
| Balanced accuracy | (TPR + TNR) / 2 |
| Precision | TP / (TP + FP) |
| Recall (TPR) | TP / (TP + FN) |
| FPR | FP / (FP + TN) |
| FNR | FN / (FN + TP) |
| TNR | TN / (TN + FP) |
| Selection rate | (TP + FP) / N |

---

## 6. Group rates, Fairlearn, AIR

**Group rates.** Explicit confusion counts per level, dual-checked against Fairlearn 0.15 `MetricFrame` (`selection_rate`, TPR, FPR, FNR). Mismatch raises `FairlearnMismatch`.

**Small-cell suppression.** Default `FAIRHIRE_SMALL_GROUP_MIN_N=30`. Below-minimum groups: rates withheld, excluded from disparities and AIR, still in overall totals.

**Fairlearn disparities** (eligible groups only): demographic parity difference, equal opportunity difference, equalized odds difference (`method='between_groups'`; EqOdds `agg='worst_case'`).

**AIR (adverse impact ratio).** Focal selection rate ÷ reference selection rate. Reference = eligible group with highest selection rate (ties → lexicographic). The 0.80 (4/5ths) threshold is a **descriptive flag** only.

Zero handling:

| Case | Result |
| --- | --- |
| Focal selections = 0, reference rate > 0 | AIR = 0.0 |
| Reference selection rate = 0 | undefined |
| Both rates = 0 | undefined |
| Non-finite inputs | undefined |

**Contingency.** 2×2 selected × group counts for each focal/reference pair.

**Fisher exact.** `scipy.stats.fisher_exact` two-sided on integer cells; skipped for non-integer weighted cells. Descriptive association test — not a legal finding.

**CMH.** Not implemented (no multi-stratum design input). See [`LIMITATIONS.md`](LIMITATIONS.md).

Fixture: `group_a` / `group_b` selection rates 0.50 / 0.30 → AIR ≈ 0.60 (below 0.80 flag); `group_c` suppressed.

---

## 7. Bootstrap

| Setting | Default |
| --- | --- |
| Sampling unit | Row |
| Method | Percentile 2.5 / 97.5 |
| Iterations | Capped by `FAIRHIRE_BOOTSTRAP_MAX_ITERATIONS` (1000) |
| Seed | Shared Generator (default `20261020`) |
| Min finite replicates | 50 |

AIR CIs use the same point-estimate reference group. Assumption: exchangeable rows. Clustered applicants typically make intervals too narrow.

---

## 8. Undefined / withheld summary

| Situation | Behavior |
| --- | --- |
| Zero denominator | `null` + reason |
| Small group | `null` + `small_group` |
| Fairlearn non-finite | `null` + `fairlearn_undefined` |
| &lt; 2 eligible groups | disparity / AIR withheld |
| &lt; 50 finite bootstrap replicates | CI bounds `null` |

---

## 9. Interpretation limits

Reports include a fixed **cannot conclude** block. Observational differences ≠ causation; metric pass ≠ compliance; CIs ≠ proof; suppressed ≠ zero. Human review remains required. The product never claims bias-free, compliant, or certified status.

---

## 10. Evaluation fixtures

| Profile | Intent | Verified |
| --- | --- | --- |
| `similar_accuracy_different_errors` | Same accuracy, different errors; tiny group | 204 rows; CM 91/11/31/71; AIR ≈ 0.60 |
| `different_accuracy_similar_error_rates` | Matched TPR/FPR, different accuracy / DP | EO/EqOdds ≈ 0; DP ≈ 0.40 |

Commands: [`METRICS.md`](METRICS.md). Privacy: [`SECURITY.md`](SECURITY.md).
