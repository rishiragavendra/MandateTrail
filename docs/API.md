# API guide

Full machine-readable schemas are available at `/openapi.json`; interactive docs at `/docs`. Domain endpoints are under `/api/v1`. Responses include X-Correlation-ID, and domain errors include a stable `error` code and `correlation_id`.

## Human authentication

POST `/auth/login` with `{ "email": "admin@mandatetrail.local", "password": "generated local password" }`. This sets an HttpOnly SameSite=Strict cookie and returns `csrf`. Send that token as `X-CSRF-Token` on mutation requests. GET `/auth/me` restores identity and the token; POST `/auth/logout` expires the session. Development HTTP cookies are not secure cookies; production TLS would require COOKIE_SECURE=1.

| Endpoint | Operations |
|---|---|
| `/health` | Public DB readiness |
| `/dashboard` | Backend-derived metrics and recent activity |
| `/agents` | GET list, POST register (admin/owner); token displayed once |
| `/agents/{id}` and `/{id}/toggle` | Details/workflows/mandates/tool events; activation toggle |
| `/suppliers` | List; admin/owner can register synthetic verified beneficiary |
| `/mandates` | List and signed creation |
| `/mandates/{id}` | Metadata |
| `/mandates/{id}/verify`, `/revoke`, `/expire`, `/version` | Verify or administrative lifecycle |
| `/workflows` | List/create; `/workflows/{id}` returns events and sessions |
| `/workflows/{id}/sessions` | Start continuation session |
| `/procurement/run` | Controlled two-session invoice-to-execution workflow |
| `/transactions` | Search `q`, `status`, `agent`, `supplier`, `workflow`, ISO `date`, `offset`, `limit` |
| `/transactions/{id}` | Payload, findings, approvals, receipts |
| `/policy/evaluate` | Reevaluate existing transaction ID |
| `/approvals` | List exact-payload requests automatically created by policy |
| `/approvals/{id}/sign`, `/revoke` | Authorized human signs/revokes |
| `/executions` | `{transaction_id, approval_id?}` through ExecutionShield |
| `/provenance/{workflow}` | Actual source and field-lineage graph |
| `/audit?workflow=...&offset=...` | Last 100 hash-chained events |
| `/audit/verify` | POST full organization-chain verification |
| `/evidence/{workflow}` | Redacted JSON attachment with real evidence |
| `/alerts`, `/alerts/{id}/resolve` | List and resolve security alerts |
| `/redteam/scenarios`, `/redteam/runs`, `/redteam/metrics` | Scenario catalogue, trial execution/history, raw metrics |
| `/redteam/reset` | Archive current trial view; retain prior evidence |
| `/settings` | Current policy, database, public key and limitations |
| `/gateway/call` | Authenticated agent tool transport |

Admin/owner: mandate and agent administration, suppliers, approvals, payments, experiments. Operator: workflows/payment preparation and execution, no human signing or administrative changes. Analyst: read and run security experiments/resolve alerts. Auditor: read-only evidence. All queries scope records to the authenticated organization. HTTP 401 indicates missing identity, 403 insufficient permission or denied agent call, 404 inaccessible object, 409 duplicate/replay constraints, and 422 schema errors.

Provenance ingestion is connector-owned. There is deliberately no endpoint for agents to submit arbitrary trusted-source labels, rewrite a signed transaction, or set human approval booleans. Approval creation is automatic from persisted ESCALATE decisions, rather than a separate unrestricted POST approval endpoint.
