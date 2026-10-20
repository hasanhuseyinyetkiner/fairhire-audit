# FairHire Audit

Audit the model. Understand the trade-offs. Show your evidence.

Group metrics, Fairlearn MetricFrame, sample-size warnings, and an explicit “what this cannot conclude” stance. Synthetic evaluation data only — not a hiring decision engine.

## Verified local run (Windows)

```powershell
# Terminal 1 — API (127.0.0.1:8104)
uv sync
uv run python -m app

# Terminal 2 — Web (127.0.0.1:5104)
cd frontend
pnpm install
pnpm dev
```

| Service | URL |
| --- | --- |
| Web | http://127.0.0.1:5104 |
| API docs | http://127.0.0.1:8104/docs |

Synthetic datasets seed on startup. Map columns → run audit → inspect Model Quality / Group Disparities.

```powershell
uv run pytest -q
```

## Status

Backend + frontend MVP runnable. License pending owner decision.
