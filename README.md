# MandateTrail · Orbital Intelligence

A working local financial-agent security sandbox: signed authority, cross-session field provenance, deterministic policy decisions, exact-payload human approvals, controlled simulated execution, and verifiable evidence.

**Synthetic data and simulated payments only. No bank credentials, live payment connections, or API/model keys are needed.**

## Start on Windows

1. Extract the ZIP completely into a writable folder (do not run inside the ZIP).
2. Install **Python 3.11+** and **Node.js 22 LTS** with npm. Enable Python on PATH. Internet access is required for the first launch.
3. Double-click **run.bat**. It creates a virtual environment, installs dependencies, applies Alembic migrations, generates a private local signing key and demo logins, seeds examples, builds Next.js, starts both services in hidden processes, and opens your browser.
4. Open **http://localhost:3000**. Email: **admin@mandatetrail.local**. Your unique generated password is in **backend/data/DEMO_CREDENTIALS.txt**. The launcher prints its full location. No fixed password is included in this archive.
5. Run **stop.bat** to stop this project's processes. Your data is retained. Re-running `run.bat` does not duplicate seed data.

The first launch takes several minutes. Keep the startup window open until it reports ready. Subsequent launches reuse dependencies and the production frontend build. Logs are written under `logs/`. Ports 3000 and 8000 must be free.

Other generated demo accounts use the same generated local password:

| Email | Role |
|---|---|
| owner@mandatetrail.local | Finance Owner |
| operator@mandatetrail.local | Finance Operator |
| analyst@mandatetrail.local | Security Analyst |
| auditor@mandatetrail.local | Auditor |

Backend: **http://127.0.0.1:8000**. Interactive API schemas: **http://127.0.0.1:8000/docs**. Health: `/api/v1/health`. Browser API requests use the frontend's same-origin proxy.

## PostgreSQL with Docker

Install Docker Desktop and start its Linux engine, then run:

```bat
run.bat -Docker
```

This generates a PostgreSQL password in `.env`, builds the frontend/backend images, starts PostgreSQL 16, waits for health checks, and initializes the application. Docker credentials are in `data/DEMO_CREDENTIALS.txt` instead of `backend/data/`. Data survives `stop.bat`. Never run local and Docker modes on the same ports simultaneously. Do not change `POSTGRES_PASSWORD` after database initialization without changing the DB password too.

Default native mode uses SQLite WAL with serialized write transactions. PostgreSQL is the primary deployment configuration; SQLite is the portable demo alternative. Native PostgreSQL is also supported by setting `DATABASE_URL` in `.env` and supplying a running database.

## Five-minute demonstration

1. **Overview**: seeded real records show one completed payment, one cross-session poisoning block, and one pending human approval.
2. **New workflow**: choose a mandate/supplier and use 48000 minor units (₹480). Execute a clean two-session invoice-to-payment flow.
3. Create another workflow with **Introduce a synthetic cross-session beneficiary attack** checked. It is blocked before the simulator is invoked.
4. **Provenance**: select that workflow, pan/zoom/fit the actual lineage graph, and inspect the external source and persistent-storage/session-retrieval nodes. Unverified data stays unverified.
5. **Approvals**: review the seeded ₹1,250 request, inspect its payload, sign it as admin/owner, then execute. The signature binds the exact digest and a single-use nonce.
6. **Security Lab**: run cross-session poisoning against Baseline, Basic Controls, and MandateTrail. Expand persisted trial evidence and compare raw numerators/denominators. Try the other nine attack and seven benign scenarios.
7. **Evidence**: verify the audit chain and export a workflow JSON package. Read-only replay is available in Workflows.

Amounts in creation forms are **integer minor units**: 100 = ₹1. Seed mandate: per transaction ₹5,000, aggregate ₹15,000, human approval above ₹1,000. Beneficiary changes are conservatively hard-denied in this prototype; human approval does not whitelist an untrusted beneficiary.

## Features

- Backend-enforced human roles, scrypt password hashes, HttpOnly sessions, same-origin CSRF token checks.
- Agent registration, one-time bearer tokens, capability allowlists, parent-capability subset checks, activation/revocation.
- Ed25519-signed versioned mandates, deterministic canonical serialization, expiry, revocation and verification.
- Actual MCP SDK stdio tools and authenticated REST gateway with request/response capture.
- Structured synthetic invoices, verified suppliers, draft POs, two-session procurement, persistent field lineage.
- TemporalGuard with hard denials, human escalation, supplier/beneficiary/currency/PO/invoice/provenance/budget checks.
- Signed exact-payload approvals, nonces, expiration, revocation and atomic one-time consumption.
- ExecutionShield revalidation, conditional budget updates, unique invoice/idempotency constraints and simulator receipts.
- Completed, failed, timed-out and unknown simulator outcomes; uncertain retries retrieve existing records.
- Individually signed, hash-chained append-only audit records with verification and evidence export.
- Ten attack and seven benign control trials across three isolated experiment environments, including an actual two-connection budget race.
- Responsive dark Orbital Intelligence interface, charts, React Flow lineage inspector, timeline replay and reduced-motion support.

## Development and tests

After `run.bat` has initialized dependencies:

```bat
cd backend
..\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm run typecheck
npm run build
```

See `docs/TESTING.md` and `PROJECT_STATUS.md` for verified paths and limitations. `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/MCP.md`, and `docs/THREAT_MODEL.md` explain integration and trust boundaries. `scripts/evaluate.py` performs a larger reproducible control evaluation. This is a local prototype, not a production-certified financial service.
