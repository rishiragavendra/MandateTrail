# Project status · 6 November 2026

Delivered as a runnable **local synthetic prototype**, with source and Windows launcher. This file distinguishes verified behavior from specification gaps.

## Verification performed

| Check | Observed result |
|---|---|
| Python security/integration tests, final source | **35 passed in 15.47 seconds** |
| Strict TypeScript and optimized Next.js 16.4.5 build | Passed |
| Windows `cmd.exe /c run.bat -NoBrowser` | Started both services; health and frontend ready |
| Windows `stop.bat` | Stopped owned process trees; ports 3000/8000 released |
| Repeat launch with existing DB | Retained data and reused dependencies; no duplicate seed |
| Alembic fresh SQLite initialization | Passed in disposable test database |
| Live HTTP via Next.js proxy | **16 checks passed**, see docs/http-smoke-results.json |
| Browser UI | Login, dashboard, provenance graph, procurement creation, approval signing, simulated execution and audit verification observed |
| Official MCP SDK | Stdio initialize handshake and all eight tool schemas tested; authenticated REST gateway tested |
| npm runtime advisory audit | 0 known vulnerabilities at build time |
| pip-audit of direct pinned Python requirements | No known vulnerabilities found; this was not a complete transitive supply-chain assessment |
| Docker Compose configuration | `docker compose config --quiet` passed |
| Docker/PostgreSQL runtime | **Not verified**: installed Docker client has no running Linux daemon |
| Windows browser auto-open | Launcher call included, but automated launcher checks used `-NoBrowser` |
| Path containing spaces | Quoted throughout launcher; not separately exercised with a fresh installation |

## Reproducible control evaluation

`docs/evaluation-results.json` contains 80 scenario runs × 3 environments = **240 environment trials**: three repetitions of ten attack families and 50 benign workflows per environment. Fresh identifiers/nonces/invoices vary across repetitions; financial amounts and control configuration are fixed. This is a deterministic structured-data agent, not an LLM test.

| Environment | Unauthorized attack successes | Attacks blocked/held | Benign completions | False interventions |
|---|---:|---:|---:|---:|
| Baseline | 30/30 | 0/30 | 50/50 | 0/50 |
| Basic per-call controls | 30/30 | 0/30 | 50/50 | 0/50 |
| MandateTrail protected | 0/30 | 30/30 | 50/50 | 0/50 |

These finite adversarial fixtures intentionally target the controls missing in baseline/basic. They do not prove universal security, independent attack coverage, or effectiveness against arbitrary models. Additional browser/smoke runs may produce different dashboard trial counts. Screenshots capture actual development-session records rather than the fresh seed shown on your first launch.

## Implemented core

Human RBAC and CSRF; agent tokens and delegation subsets; signed/versioned mandates; verified supplier registry; structured invoices and draft POs; monitored gateway and MCP tools; persistent field provenance across two sessions; deterministic policy decisions; exact signed approvals; expiry/revocation/replay checks; protected simulator execution; concurrency-safe budgets; idempotency and duplicate invoices; failure/unknown-outcome handling; append-only individually signed hash-chain audit; evidence exports; ten attack/seven benign scenarios; charts, recorded graphs, timelines and inspection panels.

## Differences and incomplete specification items

- PostgreSQL/Compose source is included and configuration-validated, but the runtime path was not tested here. Native SQLite mode was tested end to end.
- Procurement uses a deterministic state machine and structured synthetic invoice fields. There is no LLM provider, OCR, LangGraph orchestration, or real PDF invoice extraction.
- MCP integration is local stdio → authenticated REST, not a public OAuth-protected MCP HTTP server. No external MCP desktop client was configured.
- UI uses custom primitives and CSS design tokens with Tailwind available; it does not use generated shadcn components. Screens are client panels on a single App Router route.
- Current operational feed polls instead of SSE; sophisticated telemetry animations, playback controls, skeleton states and full accessibility focus trapping are limited.
- Transaction API supports search/filter/pagination; UI provides search/outcome filtering and the first 50 matches, without dedicated controls for every API filter or page.
- Beneficiary exceptions are conservatively hard-denied. There is no out-of-band beneficiary change verification or dual-control supplier-change process.
- Major security tables are relational; secondary entities use typed JSON records with application-validated references instead of separate tables/FKs for every entity.
- Read-only authorized lookup is shown as an OBSERVE event in the lab. Payment decisions normally use ALLOW, ESCALATE or DENY; there is no configurable general OBSERVE payment policy.
- No production SSO/MFA/rate limiting, HSM/key rotation, external audit anchoring, telemetry export, durable remote-payment outbox, enterprise IAM provisioning, production TLS, commercial validation, or compliance certification.
- Lab reset archives the current trial view and creates fresh fixtures on the next run. It preserves historical evidence; it does not erase the ledger or reset normal-tenant finances.

See docs/THREAT_MODEL.md for operational limitations. The archive omits all generated credentials, keys, local database files, dependencies, and caches. First launch requires Python, Node.js and internet access.
