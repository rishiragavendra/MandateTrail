# Threat model and limitations

Assume malicious invoices, poisoned agent memory, untrusted tool arguments, replay attempts, concurrent spending and delegated capability abuse. Do not assume compromise of the host, API process, local signing key or a finance owner.

The final execution boundary uses deterministic authorization rather than an LLM classification. An invoice cannot grant authority, a persisted value cannot promote its own trust, and a human approval cannot override hard policy denial. No route accepts bank credentials or sends money.

Controls tested include cross-session beneficiary substitution, per-tool authorization, delegation subsets, exact-payload signatures, approval consumption, expiry, mandate revocation, canonical invoice duplicates, idempotency, concurrent conditional budget reservations, tenant scoping and audit triggers/signatures.

Residual limitations:

- Local scrypt/password sessions have no enterprise SSO, MFA, account recovery, brute-force rate limiting or external identity lifecycle. Use only on loopback.
- Signing keys are protected by local filesystem custody, not an HSM. Rotation, revocation of historical public keys and external audit anchoring need production work. Keep the data directory private and backed up together with the DB.
- Bank identifiers are synthetic vault references and account suffix masks. The application has no raw bank account data; there is no bank vault or encryption service to protect real financial identifiers.
- Beneficiary changes are hard-denied; no out-of-band supplier verification and dual-control change-management process is implemented.
- Invoice extraction is structured synthetic JSON. The injected sentence is an adversarial fixture, not real OCR or a model interpreting a PDF. No LLM, LangGraph planner or external provider integration is included.
- JSON document references rely partly on application validation rather than separate relational foreign keys for each field.
- Baseline/basic trials deliberately omit controls in isolated synthetic tenants; their results do not establish performance against arbitrary attacks or a live model. Default UI metrics are measured only from the trials actually run.
- The local audit chain and signatures detect modification. A malicious DBA/host administrator can delete an entire stream or replace the DB/key together; external anchoring/checkpoint retention is required for stronger guarantees.
- All sensitive simulator writes are within a database transaction. A real remote payment system needs a durable intent/outbox, adapter isolation, reconciliation and crash/unknown-outcome handling beyond this simulator.
- The frontend uses custom accessible primitives rather than the shadcn component generator. Navigation screens are client-side panels on one App Router route; deep links per screen and full screen-reader focus trapping are not yet implemented.
- Live feed uses polling, not SSE. Lists are intentionally small local demo datasets; transaction API exposes pagination but UI shows the first 50 matches.
- Docker/PostgreSQL runtime verification depends on an active Docker daemon; see the final test report for whether that path was exercised.

No regulatory certification, universal prompt-injection prevention, commercial validation or production readiness is claimed.
