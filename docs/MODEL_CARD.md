# Model card — FairHire Audit

Methodological card for the **audit tool** (version `0.1.0`), not a fairness certificate for any hiring model under evaluation. Companion verification commands live in [`METRICS.md`](METRICS.md). Code sources of truth: `app/domain/definitions.py`, `rates.py`, `fairness.py`, `bootstrap.py`, `compute.py`, `synthetic.py`.

---

## 1. Intended use

| Allowed | Excluded |
| --- | --- |
| Inspect **authorized or synthetic** hiring-model *evaluation* tables (`y_true`, `y_pred` and/or `score`, permitted group columns, optional weights) | Candidate ranking, scoring for hire/reject, production threshold deployment |
| Compute confusion counts, classification rates, Fairlearn group rates and DP / EO / EqOdds *differences* | Inferring protected attributes from names, photos, free text, or other proxies |
| Flag small cells, undefined denominators, and conflicting fairness criteria | Causal attribution of a disparity |
| Seeded bootstrap percentile intervals under documented assumptions | Legal/compliance certification or “bias-free” claims |
| Threshold Lab **simulations** after explicit `probability` or `ranking_score` declaration (FHA-1) | Treating simulated cutoffs as deployable policy |
| Local single-operator demo / workstation review | Multi-tenant SaaS; offline local demo ≠ multi-user secured (MVP has **no auth**) |

Primary users: ML / people-analytics engineers and reviewers with evaluation extracts they are authorized to hold.

---

## 2. Data assumptions

- Input is an **evaluation table**, not a live applicant stream. Rows are treated as exchangeable for bootstrap (see §7).
- Labels are binary after mapping; the positive class is the declared `positive_label` (demo fixtures use `1`).
- Group columns are operator-mapped **audit attributes**. Labels such as `group_a` / `group_b` in synthetic profiles are arbitrary ids, **not** real populations or protected classes.
- Optional `sample_weight` reweights counts; unmapped weights default to 1.
- Optional `timestamp` is stored in the mapping and **unused** in rates (no temporal drift analysis in MVP).
- Public demos and README screenshots use **deterministic synthetic** profiles only. Do not publish real candidate extracts, SQLite DBs, or reports.

---

## 3. Labels and score semantics

| Field | Meaning in this product |
| --- | --- |
| `y_true` | Observed binary outcome on the evaluation set |
| `y_pred` | Predicted class (or derived `score >= 0.5` only when score semantics are declared `probability`, with a warning) |
| `score` + `probability` | Numeric scores must lie in \[0, 1\]. Brier score and a reliability table are **descriptive** evidence. The system never auto-labels a score “calibrated.” |
| `score` + `ranking_score` | Opens Threshold Lab; skips Brier. Thresholds are arbitrary cutpoints on a ranking scale, not probabilities. |
| Undeclared score | Threshold Lab stays **locked** (FHA-1). |

`GET /api/meta` returns `"decision_engine": false`.

---

## 4. Confusion-matrix convention

Matches `sklearn.metrics.confusion_matrix(..., labels=[negative, positive])`:

- Rows = actual class; columns = predicted class, order `[negative, positive]`.
- Cell `(0,0)` = **TN**, `(0,1)` = **FP**, `(1,0)` = **FN**, `(1,1)` = **TP**.

Verified synthetic fixture `similar_accuracy_different_errors` (204 rows):

| TN | FP | FN | TP |
| --- | --- | --- | --- |
| 91 | 11 | 31 | 71 |

Overall accuracy = 162/204 ≈ 0.794. Source: `app/domain/synthetic.py`; asserted in `tests/test_golden.py`.

---

## 5. Rate formulas (point estimates)

Undefined when the denominator is zero → value `null` + reason `undefined_denominator` (**not** coerced to 0).

| Metric | Formula |
| --- | --- |
| Accuracy | (TP + TN) / N |
| Balanced accuracy | (TPR + TNR) / 2; undefined if TPR or TNR is undefined |
| Precision | TP / (TP + FP) |
| Recall (TPR) | TP / (TP + FN) |
| FPR | FP / (FP + TN) |
| FNR | FN / (FN + TP) |
| TNR | TN / (TN + FP) |
| Selection rate | (TP + FP) / N |

Every rate payload includes numerator, denominator, formula string, and sample size *n*.

---

## 6. Group rates and disparity formulas

**Group rates.** Computed from explicit confusion counts per group level, then dual-checked against Fairlearn 0.15 `MetricFrame` (`selection_rate`, `true_positive_rate`, `false_positive_rate`, `false_negative_rate`) on groups with a positive denominator. Disagreement raises `FairlearnMismatch` and fails the audit.

**Small-cell suppression.** Default `FAIRHIRE_SMALL_GROUP_MIN_N=30`. Groups below the minimum:

- Appear with an amber withhold card (`undefined_reason: small_group`).
- Have rates and numerators withheld (cannot rebuild a rate from the payload).
- Are listed under `groups_excluded` and **excluded** from disparity summaries.
- Still contribute to **overall** totals.

**Disparity summaries** (Fairlearn 0.15, eligible groups only):

| Name | Definition in this product |
| --- | --- |
| Demographic parity difference | Max − min group selection rate; `demographic_parity_difference(method='between_groups')` |
| Equal opportunity difference | Max − min group TPR; `equal_opportunity_difference(method='between_groups')` |
| Equalized odds difference | Greater of TPR and FPR differences; `equalized_odds_difference(method='between_groups', agg='worst_case')` |

Fewer than two eligible groups → difference withheld (`fewer_than_two_eligible_groups`). Non-finite Fairlearn values → `fairlearn_undefined`, not zero.

**Fixture story (verified).** `group_a` and `group_b`: *n* = 100 each, accuracy 0.80, different FPR/FNR. `group_c`: *n* = 4, suppressed. Two-group DP / EO / EqOdds differences ≈ 0.20. This is **disparity measurement** on a synthetic table — not causation, legal findings, or proof of bias or fairness.

When at least one disparity is ~0 and another is not, the run emits a conflict warning. Meeting one criterion says nothing about the others.

---

## 7. Sampling unit and bootstrap assumptions

| Setting | Default / behavior |
| --- | --- |
| Sampling unit | **Row** |
| Method | Percentile (2.5 / 97.5 via `scipy.stats.scoreatpercentile`) |
| Iterations | Requested capped by `FAIRHIRE_BOOTSTRAP_MAX_ITERATIONS` (default 1000) |
| Seed | Shared `numpy.random.Generator` per run (default seed `20261020`) |
| Min finite replicates | 50; otherwise interval withheld (`too_few_finite_replicates`) |

**Assumptions.** Rows are exchangeable; resamples share the same label-noise process. **If violated** (clustered applicants, repeated interviews, selection into the evaluation set not modeled): intervals are typically **too narrow**. Bootstrap uncertainty is **not** proof that a disparity is real, absent, or acceptable.

---

## 8. Undefined and withheld metrics (summary)

| Situation | Payload behavior |
| --- | --- |
| Zero denominator | `null` + `undefined_denominator` |
| Group *n* &lt; min | `null` + `small_group`; numerators hidden |
| Fairlearn non-finite | `null` + `fairlearn_undefined` |
| &lt; 2 eligible groups for a difference | withheld + reason |
| &lt; 50 finite bootstrap replicates | CI lower/upper `null` |
| Difference of two undefined rates | `comparison_undefined` |

Charts and disparity formulas skip withheld values; they do **not** plot zeros.

---

## 9. Interpretation limits and human review

Reports always include a fixed **What this cannot conclude** section (`CANNOT_CONCLUDE` in code). In particular:

- Observational rate differences ≠ causal diagnosis (selection, label bias, confounding, base-rate differences can produce the same numbers).
- Passing selected fairness metrics ≠ fairness, compliance, or fitness for employment decisions.
- Confidence intervals ≠ legal or scientific proof.
- Suppressed cells ≠ zeros.
- This tool does not rank people or automate hiring outcomes.
- Results require **human review** by someone accountable for the evaluation context; the product is not a substitute for counsel or a formal model-risk program.

**Never claimed by this product:** bias-free, compliant, certified, production-ready SaaS, or fit for automated employment decisions.

---

## 10. Evaluation data provenance (tool verification)

| Profile | Design intent | Verified counts |
| --- | --- | --- |
| `similar_accuracy_different_errors` | Same accuracy, different error structure; tiny group for suppression | 204 rows; CM 91/11/31/71; groups 100/100/4 |
| `different_accuracy_similar_error_rates` | Similar TPR/FPR, different accuracy / DP | EO & EqOdds ≈ 0; DP ≈ 0.40; conflict warning |

Full command log: [`METRICS.md`](METRICS.md). Privacy boundary: [`SECURITY.md`](SECURITY.md).
