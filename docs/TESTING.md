# Testing

Run `python -m pytest -q` from backend with dependencies installed. Tests create a disposable SQLite database and a fresh signing key in the OS temporary directory. They never modify your local demo data.

The suite covers canonical serialization, Ed25519 tamper rejection, authentication/CSRF/roles, valid execution and safe idempotent retry, cross-session provenance, exact approvals, payload modification, hard denials, revoked mandates, expiry, tenant boundaries, authenticated gateway/unknown-tool audit, ten attacks and seven benign scenarios in three environments, raw metric denominators, evidence export and audit immutability/integrity.

The concurrent-budget scenario uses two independent database connections and threads against the same mandate after proposals are committed. Both start with individually permitted values; their sum exceeds aggregate budget. The protected result must submit only one payment. This is a real database concurrency test, not a synthetic label.

Use `npm run typecheck` and `npm run build` in frontend for strict TypeScript and optimized build checks. `npm audit --omit=dev` reports known runtime advisories. Review them as dependencies evolve. Tests are finite synthetic control cases and do not establish production security.

`scripts/evaluate.py` uses a running backend and the generated admin login. It runs variations of all attacks plus at least 50 benign workflows, reports raw results and records trials in the application's database. It is intentionally separate from regular unit tests. See PROJECT_STATUS.md for exact execution results and launch verification.
