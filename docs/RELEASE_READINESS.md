# Release readiness checklist

Local demo MVP readiness for a tagged release. **Not** a claim of production SaaS readiness.

Last documentation pass: **2026-10-20**.

### Verification this pass

| Check | Result |
| --- | --- |
| Fixture CM vs `synthetic.py` | TN/FP/FN/TP = 91/11/31/71; groups 100/100/4; DP/EO/EqOdds ≈ 0.20 |
| `uv run ruff check app tests` | Pass |
| `uv run pytest -q` | 17 passed, 1 skipped |
| `pnpm lint` / `typecheck` / `test` / `build` | Pass (3 Vitest) |
| Playwright e2e | Blocked by Node OOM on this host; prior green run documented |
| Relative markdown links | 41 checked, 0 broken |

## Must be true before tagging

| Gate | Status | Evidence |
| --- | --- | --- |
| CI workflow present | Yes | `.github/workflows/ci.yml` (Ruff, pytest+Postgres, frontend lint/tsc/vitest/build, compose-smoke) |
| Native path documented | Yes | README Getting started; ports 8104 / 5104 / 5404 |
| Fairness honesty | Yes | `CANNOT_CONCLUDE` in reports; `decision_engine: false`; no bias-free certificate language |
| Synthetic demo only in public materials | Yes | Seed profiles; README / SECURITY warnings |
| Cascade delete + retention purge | Yes | FHA-2; `DELETE /api/datasets/{id}`; `python -m app.cli purge` |
| Loopback bind default | Yes | `enforce_bind`; Compose `127.0.0.1:` prefixes |
| Golden fixture matches docs | Yes | CM TN/FP/FN/TP = 91/11/31/71; group *n* 100/100/4 |
| Model card published | Yes | [`MODEL_CARD.md`](MODEL_CARD.md) |
| Screenshots authentic | Yes | `docs/screenshots/*` from `pnpm screenshots` |
| License | Pending | README: “License: pending owner decision”; do **not** invent a LICENSE file |
| Push / visibility | Owner decision | Do not change remote visibility or push without explicit authorization |

## Pre-tag verification commands

```powershell
uv run ruff check app tests
uv run pytest -q
cd frontend
pnpm lint; pnpm typecheck; pnpm test; pnpm build
pnpm test:e2e
```

Optional: `pnpm screenshots` with API on `:8104` and web on `:5104` if README captures need refresh.

## Release notes skeleton

1. Scope: local audit workstation for evaluation tables (Fairlearn disparities, bootstrap CIs, score-gated Threshold Lab).
2. Explicit non-goals: not a decision engine; not compliance certification.
3. Ports and accent: API `8104`, web `5104`, accent `#2563EB`.
4. Link `docs/MODEL_CARD.md` and `docs/METRICS.md` for method and measured results.
5. Attach light-theme screenshots only if they were re-captured on the tagged commit.

## Explicitly out of scope for v0.1

- Multi-user authentication / authorization
- TLS termination inside the app
- Side-by-side two-model comparison UI (domain deltas may exist; dedicated UI not shipped)
- Causal inference or protected-attribute inference
- Invented live-demo homepage URLs, coverage percentages, or “bias-free” / “compliant” claims

See also [`GITHUB_METADATA.md`](GITHUB_METADATA.md) for About / topics.
