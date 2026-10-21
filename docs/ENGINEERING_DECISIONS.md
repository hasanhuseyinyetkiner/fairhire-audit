# Engineering decisions

Staff-level rationale for the statistical and product choices in FairHire Audit. Each decision follows **Context → Options → Decision → Trade-offs → Validation**.

Formulas, intended use, and interpretation limits: [`MODEL_CARD.md`](MODEL_CARD.md). Measured verification: [`METRICS.md`](METRICS.md).

---

## FHA-D1 — Undefined rates stay `null`, never silent zero

**Context.** Hiring evaluation tables often produce zero denominators (no predicted positives → precision undefined; no actual positives → recall undefined). Dashboards that coerce `NaN` to `0` invent a false clean bill of health.

**Options.** (a) Coerce to 0 for charting. (b) Drop the metric quietly. (c) Return `null` plus an explicit `undefined_reason` and human message.

**Decision.** Option (c). `app/domain/rates.py` returns `(None, "undefined_denominator")`. Fairlearn non-finite values become `"fairlearn_undefined"`. Small groups use `"small_group"`. UI and HTML/JSON reports render the message; charts omit the point rather than plotting zero.

**Trade-offs.** Callers must handle nulls. Some chart libraries need extra guards. The benefit is that a reviewer cannot mistake “no evidence” for “perfect rate.”

**Validation.** `tests/test_golden.py::test_undefined_denominator_is_not_zero`. Report copy in `CANNOT_CONCLUDE` states that suppressed cells are not zeros.

---

## FHA-D2 — Count-based rates dual-checked against Fairlearn MetricFrame

**Context.** Disparity summaries come from Fairlearn 0.15 (`demographic_parity_difference`, `equal_opportunity_difference`, `equalized_odds_difference` with `method='between_groups'`, EO with `agg='worst_case'`). Group rates must stay consistent with those summaries.

**Options.** (a) Trust Fairlearn alone for rates. (b) Hand-roll everything and skip Fairlearn. (c) Compute rates from confusion counts, then assert agreement with `MetricFrame` on eligible groups.

**Decision.** Option (c). `metric_frame_rates` + `assert_matches_metric_frame` in `app/domain/fairness.py`. A mismatch raises `FairlearnMismatch` and fails the audit run rather than shipping a quiet drift.

**Trade-offs.** Tight coupling to Fairlearn’s `pos_label` default (1 for `{0,1}` labels). Version pins and golden tests must track Fairlearn upgrades.

**Validation.** Golden hand counts in `tests/test_golden.py`; Fairlearn package version recorded in report provenance.

---

## FHA-D3 — Seeded percentile bootstrap with an explicit sampling unit

**Context.** Point disparities on *n* ≈ 200 without uncertainty invite over-interpretation. Parametric intervals need distributional assumptions that evaluation tables rarely justify.

**Options.** (a) No intervals. (b) Normal approximation on rates. (c) Row-level nonparametric bootstrap with documented seed, iterations, and percentile interval.

**Decision.** Option (c). `app/domain/bootstrap.py`: sampling unit = **row**; method = **percentile** (2.5 / 97.5 via `scipy.stats.scoreatpercentile`); one `numpy.random.Generator` shared across metrics in a run; iterations capped (`FAIRHIRE_BOOTSTRAP_MAX_ITERATIONS`, default 1000); intervals withheld when fewer than `MIN_FINITE_REPLICATES` (50) finite replicates remain.

**Trade-offs / statistical assumptions.**

| Assumption | Implication if violated |
| --- | --- |
| Rows are exchangeable | Clustered applicants / repeated interviews → intervals too narrow |
| Resamples share the same label noise process | Label bias is not corrected by bootstrap |
| Finite replicates after undefined denominators | Sparse positives → many NaN replicates → interval withheld |

The UI and report state: the interval is **resampling uncertainty under this procedure**, not proof that a disparity is real, absent, or acceptable.

**Validation.** Seeded reproducibility tests; provenance fields `seed`, `bootstrap_iterations`, `sampling_unit`, `method`; threadpool execution so `/health` stays responsive (`tests/test_health_during_audit.py`).

---

## FHA-D4 — Small-sample suppression before disparity summaries

**Context.** A four-row group can show FPR = 0 or 1 with no statistical meaning. Plotting it next to *n* = 100 groups misleads reviewers.

**Options.** (a) Plot everything. (b) Soften with error bars only. (c) Hard suppress rates below `FAIRHIRE_SMALL_GROUP_MIN_N` (default 30) and exclude those levels from Fairlearn disparity calls.

**Decision.** Option (c). Suppressed groups appear with an amber card and message; they are listed under `groups_excluded`; disparity formulas run only on eligible levels. Overall metrics still include every row.

**Trade-offs.** Changing `min_n` changes which stories the dashboard tells. Very fine-grained intersections will suppress heavily — intentional for privacy and variance control.

**Validation.** Synthetic profile `similar_accuracy_different_errors` embeds `group_c` with *n* = 4; Playwright and golden paths assert suppression rather than a drawn zero.

---

## FHA-D5 — Explicit score semantics gate for Threshold Lab (FHA-1)

**Context.** A continuous “score” column might be a calibrated probability, an uncalibrated logit transform, or a ranking score with arbitrary scale. Sliding a threshold without that declaration invents a decision policy.

**Options.** (a) Always enable the lab if a numeric column exists. (b) Auto-detect calibration and unlock. (c) Require the user to declare `probability` or `ranking_score`; for probabilities enforce \[0, 1\] and show Brier + reliability table as **descriptive** evidence only — never auto-label “calibrated.”

**Decision.** Option (c). `score_gate()` in `app/domain/compute.py`. Ranking scores open the lab but skip Brier. Probabilities outside \[0, 1\] fail mapping. Derived `y_pred = score >= 0.5` is allowed only for declared probabilities and is warned in the payload.

**Trade-offs.** Extra mapping friction. Prevents the common failure mode of treating ranking scores as probabilities.

**Validation.** `tests/test_api.py` score-gate cases; report never emits a calibration certificate.

---

## FHA-D6 — Surface conflicting fairness criteria instead of picking a winner

**Context.** Demographic parity (selection-rate equality), equal opportunity (TPR equality), and equalized odds (TPR and FPR) are mathematically incompatible in general when base rates differ (classic impossibility results). An audit that highlights only the metric that “passes” is advocacy, not evaluation.

**Options.** (a) Ship a single composite “fairness score.” (b) Let the user pick one metric and hide the others. (c) Always compute DP / EO / EqOdds differences on eligible groups and emit a warning when some are ~0 while others are not.

**Decision.** Option (c). `_conflict_warning` in `compute.py` when at least one disparity is ~0 and another is not. Report assumptions state that meeting one criterion says nothing about the others. Synthetic profile **Similar accuracy, different error rates** keeps accuracy matched while FPR/FNR diverge — so overall quality looks fine while group error structure does not.

**Trade-offs.** Reviewers must interpret multiple numbers. There is no single green/red traffic light by design.

**Validation.** Hand-computed disparities in golden tests (e.g. DP ≈ 0.20, EO ≈ 0.20, EqOdds ≈ 0.20 on the two-group fixture); UI copy on Group disparities and Audit report.

---

## FHA-D7 — Audit tool, not a decision engine

**Context.** HR tooling that ranks candidates or auto-rejects is a different product class with different legal and ethical exposure.

**Options.** (a) Add ranking endpoints later. (b) Keep evaluation-table scope and advertise `decision_engine: false` in `/api/meta`.

**Decision.** Option (b). No candidate ranking, no production threshold deployment, no inference of protected attributes from proxies. Cascade delete + retention purge for uploaded evaluation files.

**Trade-offs.** Narrower product surface. Clearer honesty in README and reports.

**Validation.** `test_meta_is_not_a_decision_engine`; HTML report includes the full `CANNOT_CONCLUDE` list and contains no “bias-free” certificate language.

---

## FHA-D8 — AIR / 4/5ths as descriptive measurement; CMH deferred

**Context.** Selection-rate ratios (adverse impact ratio) and 2×2 contingency tables are standard audit artifacts. Cochran–Mantel–Haenszel requires a stratified design the MVP does not accept.

**Options.** (a) Ship AIR + contingency + Fisher exact with explicit zero handling and bootstrap CIs; document CMH as a gap. (b) Claim CMH without strata. (c) Omit AIR entirely.

**Decision.** Option (a). `app/domain/air.py`: reference = highest eligible selection rate; AIR = focal / reference; 0.80 flag is descriptive only; Fisher exact on integer cells; never emit NaN. CMH documented in [`LIMITATIONS.md`](LIMITATIONS.md).

**Trade-offs.** Reviewers see AIR beside Fairlearn DP without a legal overlay. Multi-stratum CMH remains future work.

**Validation.** `tests/test_air.py` (zero focal → 0.0; zero reference → undefined; synthetic AIR ≈ 0.60 with CI).
