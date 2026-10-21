# Security boundaries

FairHire Audit is a **local auditing workstation demo**, not a production decisioning service.

## Assumptions

- Default bind is loopback. Non-loopback requires `FAIRHIRE_ALLOW_NETWORK_BIND=true`.
- No authentication in the MVP.
- Demo datasets are **synthetic**. Do not load real protected-attribute HR extracts by default.
- Dataset delete cascades audit artifacts; treat retention as operator-controlled local files.
- CORS is for the paired UI origin only — not an auth boundary.

## Governance posture

- `GET /api/meta` exposes `"decision_engine": false`.
- Threshold Lab simulates cutoffs for analysis; it does **not** approve, reject, hire, or promote anyone.
- Export reports are descriptive measurements with “cannot conclude” language where samples are insufficient.

## What this is not

- Not a claim of SOC2 / ISO / employment-law compliance.
- Not safe for multi-user hosting without authn/z, encryption, and retention redesign.
