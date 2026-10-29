# FairHire Audit

FairHire Audit is a local workbench for inspecting group-level outcomes in a binary model evaluation. It starts with counts rather than a single fairness score: selection rates, false-positive and false-negative rates, uncertainty, and threshold scenarios can tell different stories about the same predictions. It does not make hiring decisions.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/group-disparities-dark.png">
  <img src="docs/screenshots/group-disparities-light.png" alt="Group disparity results for a synthetic model evaluation" width="100%">
</picture>

The included synthetic example makes the problem concrete: two groups each have 80% accuracy, yet their false-negative rates are 20% and 40%. A four-person group is withheld under the default minimum of 30, not reported as zero. The fixture and its counts are documented in [evaluation evidence](docs/METRICS.md).

## What was tested on public data

A reproducible [UCI Adult census experiment](docs/ADULT_BENCHMARK.md) trains a small income classifier on the published training file and audits the published test file. In the recorded run, predicted-positive rates were 8.01% for the 5,421 records labelled female and 15.08% for the 10,860 labelled male; false-negative rates were 73.05% and 66.37%, respectively. The script checks these and false-positive rates against independently calculated confusion counts. The two files include 23 test rows with values identical to training rows, so they are not strictly separated by record values. This is historical income data, **not hiring data**; these observations cannot establish fairness, causation, or legal compliance in hiring. Dataset attribution, CC BY 4.0 license, source hashes, method, and limitations are in the experiment documentation.

```powershell
uv sync
uv run python -m scripts.adult_benchmark  # downloads public data into memory
```

## How the audit works

Import a CSV or Parquet evaluation table, map actual and predicted outcomes and group columns, and inspect the resulting confusion counts and rates. The API checks eligible group rates against Fairlearn `MetricFrame`. The adverse impact ratio compares each group's selection rate with the highest eligible rate; undefined denominators and small groups are withheld with reasons. The four-fifths flag is descriptive, not a legal conclusion.

Seeded percentile intervals resample rows and assume exchangeable observations; clustering or sampling design can make them misleading. The Threshold Lab requires a declared probability or ranking score and produces point estimates for scenarios, not deployed decisions or new confidence intervals. [Model card](docs/MODEL_CARD.md) explains formulas, weights and assumptions; [evaluation provenance](docs/EVALUATION.md) explains versioning and scope.

React, Vite and TypeScript provide the interface; FastAPI, SQLAlchemy and SQLite provide the local API and storage. The domain uses Fairlearn, NumPy, SciPy and scikit-learn. PostgreSQL is supported for CI and Compose. See [architecture](docs/ARCHITECTURE.md) for details.

## Run locally

Prerequisites: Python 3.12, `uv`, Node 24 and `pnpm`. In one terminal:

```powershell
uv sync
uv run python -m app
```

In another:

```powershell
cd frontend
pnpm install
pnpm dev
```

Open [the web app](http://127.0.0.1:5104) or [API documentation](http://127.0.0.1:8104/docs). The API defaults to loopback and SQLite at `./data/fairhire.db`; [configuration](.env.example) lists overrides. To reproduce the synthetic example, choose **Import → Similar accuracy, different error rates**, map the columns, declare the score as `probability`, and run the audit. A [recorded workflow](docs/assets/demo.gif) shows the interface.

## Verification

```powershell
uv run ruff check app tests scripts/adult_benchmark.py
uv run pytest -q
cd frontend
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm exec playwright install chromium  # once
pnpm test:e2e
```

The [CI workflow](.github/workflows/ci.yml) includes PostgreSQL, Playwright and Compose jobs. PostgreSQL tests require `TEST_DATABASE_URL`.

## Boundaries

This is a local, single-operator MVP with no authentication. Do not load sensitive HR extracts without assessing the environment and privacy obligations. Small-group suppression does not eliminate privacy risk. Observed disparities depend on labels, sampling, group definitions and thresholds; they do not establish causes or legal compliance. CMH and a side-by-side two-model comparison UI are not implemented. See [security](docs/SECURITY.md), [limitations](docs/LIMITATIONS.md), [changelog](CHANGELOG.md), and the [MIT license](LICENSE).
