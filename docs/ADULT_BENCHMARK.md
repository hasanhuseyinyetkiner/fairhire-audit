# Public-data exercise: UCI Adult

This experiment exercises the audit on historical census-derived observations, not hiring decisions. It is not a validation of the application for HR use or evidence that a hiring model is fair. The dataset is public, but contains demographic information about people; the script downloads it into memory and prints aggregate results only. It does not save individual records or predictions.

## Source and rights

Becker, B. and Kohavi, R. (1996), *Adult*, UCI Machine Learning Repository, [doi:10.24432/C5XW20](https://doi.org/10.24432/C5XW20). UCI describes extraction from the 1994 Census database and lists [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) as the dataset license on its [dataset page](https://archive.ics.uci.edu/dataset/2/adult). The benchmark adapts the source by selecting three features, transforming the income label and generating predictions; this repository does not redistribute the dataset. The project code's MIT license does not replace the dataset license.

UCI supplies separate `adult.data` and `adult.test` files. The script verifies the following SHA-256 hashes before parsing; a changed upstream file fails closed and requires an explicit provenance review:

| File | SHA-256 |
| --- | --- |
| adult.data | `5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d` |
| adult.test | `a2a9044bc167a35b2361efbabec64e89d69ce82d9790d2980119aac5fd7e9c05` |

## Procedure

Run `uv run python -m scripts.adult_benchmark` from the repository root; network access is required. The script trains scikit-learn's logistic regression (standardized age, education number and hours per week; default regularization; `max_iter=1000`, `random_state=0`) on all 32,561 training rows. It evaluates the 16,281 rows in the published test file, with income above $50,000 as the positive outcome and the model's default 0.5 classification cutoff. The test-file trailing label periods are removed. No rows are dropped, and the census `fnlwgt` field is not used: these are unweighted sample statistics, not population estimates. Sex is used for grouping, not as a training feature. Other features may still carry correlated information.

After normalizing labels, **23 test rows have identical values across all 15 fields to at least one training row**. The script prints this count; these rows remain in the published test split and in the results below. Identical values do not establish that the records describe the same people, but the experiment is not strictly separated by record values. The overlap can affect the reported metrics.

The script passes outcomes, predictions and sex into the application's `prepare_frame` and `compute_analysis` with a minimum group size of 30 and bootstrap disabled. It independently computes each group's confusion counts from the arrays and checks selection rate, false-negative rate and false-positive rate against the application output. The application's own Fairlearn checks also run. This is a check of these rates on this dataset and configuration, not an independent validation of every metric or the UI.

## Observed run

With the project's locked dependencies, the run on 2026-10-29 printed:

| UCI sex category | n | TN | FP | FN | TP | Predicted positive | FNR | FPR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Female | 5,421 | 4,556 | 275 | 431 | 159 | 0.0801 | 0.7305 | 0.0569 |
| Male | 10,860 | 7,061 | 543 | 2,161 | 1,095 | 0.1508 | 0.6637 | 0.0714 |

The female-to-male predicted-positive ratio is about 0.531 for this model and dataset. The observed rates depend on the features, label and threshold, and the historical dataset's binary sex categories do not represent all identities. Income is not a measure of candidate qualification, and historical income differences can reflect structural inequities. These are point estimates; the benchmark computes no confidence intervals. Sampling design, selection into the dataset, label quality, temporal shift, and multiple possible subgroup or model choices limit generalization. Differences alone do not establish causality or legal compliance.
