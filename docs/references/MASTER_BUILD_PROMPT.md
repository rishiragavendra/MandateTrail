# MASTER BUILD PROMPT — MANDATETRAIL
## Orbital Intelligence Edition
### Full-Stack Cybersecurity × FinTech × AI Agent Security Platform

You are a senior full-stack engineer, security architect, UI/UX designer, database engineer, DevOps engineer, and QA engineer.

Your assignment is to **design, implement, integrate, test, and package a complete working application named MandateTrail**.

This is an implementation assignment, not a brainstorming exercise.

**Do not stop after generating a project plan, UI mockup, incomplete scaffold, or documentation. Build the application.**

You must read the attached document:

`MandateTrail_Complete_Project_Blueprint(1).pdf`

Treat the PDF as the authoritative product and technical specification. Preserve its security requirements, workflow logic, architecture, data model, threat model, and acceptance criteria.

Use this prompt to define the frontend aesthetic, developer experience, integration requirements, and final deliverables.

Where the PDF and this prompt conflict on security behavior, prioritize the PDF's security requirements.

---

# 1. PROJECT OVERVIEW

**Project:** MandateTrail

**Category:** Cybersecurity × Financial Technology × AI Agent Security

**Theme:** Orbital Intelligence

**Tagline:** Every action has an origin. Every transaction needs authority.

MandateTrail is a financial AI-agent integrity and runtime security platform.

The system sits between AI agents and sensitive financial tools to ensure that financial actions remain consistent with their original authorization.

It must monitor agent tool interactions, preserve financial field provenance, evaluate signed mandates, track multi-session workflows, require valid approvals when appropriate, and enforce security decisions before simulated financial execution.

## Core capabilities

Implement the following integrated subsystems:

1. Agent registration and identity management.
2. Signed financial mandates.
3. MCP-first tool gateway.
4. Supplier and invoice management.
5. Procurement agent workflow.
6. Field-level provenance tracking.
7. Cross-session data lineage.
8. TemporalGuard policy engine.
9. Human approval workflow.
10. ExecutionShield payment enforcement.
11. Simulated financial transactions.
12. ForensicLedger audit system.
13. RedTeamLab adversarial simulation.
14. Security analytics dashboard.
15. Workflow replay and investigation.
16. Evidence generation and export.

These must work together through real application logic, not disconnected frontend demonstrations.

**Critical scope restriction:** Use synthetic financial data and a simulated payment adapter only. Do not integrate real banks, UPI rails, payment processors, or live money movement.

---

# 2. DEVELOPMENT STACK

Use the following preferred stack.

## Frontend

- Next.js with App Router.
- React.
- TypeScript with strict mode.
- Tailwind CSS.
- shadcn/ui.
- Motion for animations.
- Lucide React icons.
- React Flow / XYFlow for provenance visualization.
- Recharts for analytics.
- TanStack Query for API state.
- React Hook Form and Zod for validated forms.

## Backend

- Python.
- FastAPI.
- Pydantic.
- SQLAlchemy.
- Alembic.
- PostgreSQL.
- Cryptography library for Ed25519 signing and verification.
- Pytest for automated testing.

## Integration

- MCP-compatible gateway/server using an appropriate maintained SDK.
- Versioned REST APIs.
- Server-Sent Events for live activity where useful.
- Typed frontend API client.
- Backend-driven state and metrics.

## Deployment

- Docker Compose for PostgreSQL and supporting services.
- Windows-compatible `run.bat`.
- Windows-compatible `stop.bat`.
- `.env.example`.
- Automatic local initialization.
- Documented development and production-like configurations.

Prefer a modular monolith over unnecessary microservices.

The project should be maintainable and easily extendable.

---

# 3. VISUAL THEME — ORBITAL INTELLIGENCE

The complete application must follow the **Orbital Intelligence** design language.

This is a professional, space-inspired cybersecurity and fintech interface.

It must not resemble a gaming dashboard, colorful cyberpunk website, or generic AI-generated admin template.

## Design inspiration

Combine:

- Space mission-control interfaces.
- Modern enterprise fintech dashboards.
- Premium cybersecurity monitoring platforms.
- Minimal SaaS interfaces.
- Subtle orbital telemetry visualization.

The desired impression is:

**A sophisticated financial security command center operating in a deep-space-inspired environment.**

## Color palette

Use these primary design tokens:

Background:
`#080D1B`

Sidebar:
`#0D1424`

Primary card surface:
`#141D30`

Elevated surface:
`#1B2740`

Primary blue:
`#3B82F6`

Orbital indigo:
`#6366F1`

Soft violet:
`#8B5CF6`

Cyan highlight:
`#38BDF8`

Primary text:
`#F8FAFC`

Secondary text:
`#94A3B8`

Border:
`#273449`

Success:
`#22C55E`

Warning:
`#F59E0B`

Danger:
`#EF4444`

Use blue as the dominant interaction color.

Use violet for AI-agent activity and provenance relationships.

Use cyan for active tracing and telemetry.

Reserve green, amber, and red for semantic security outcomes.

## Typography

Use Geist or Inter for interface typography.

Use JetBrains Mono for:

- Event identifiers.
- Cryptographic hashes.
- Transaction digests.
- Policy reason codes.
- Technical logs.
- Workflow references.

## UI styling

- Dark mode only.
- Professional visual hierarchy.
- Spacious layouts.
- Clean data tables.
- Subtle borders.
- Rounded corners between 8px and 12px.
- Restrained shadows.
- Consistent spacing.
- Clear readable typography.
- Minimal glass effects.
- No excessive neon.
- No distracting background effects.

## Space-inspired elements

Add restrained visual details such as:

- Subtle orbital rings in dashboard illustrations.
- Faint geometric telemetry grids.
- Soft blue-violet radial gradients.
- Occasional small moving telemetry indicators.
- Carefully controlled atmospheric lighting.

Do not put animated stars behind tables or financial forms.

The UI must remain highly readable.

---

# 4. ANIMATION REQUIREMENTS

Animations must feel smooth, professional, and meaningful.

Use Motion where appropriate.

## Global animations

Implement:

- Smooth route transitions.
- Staggered dashboard card entrances.
- Subtle hover effects.
- Animated sidebar expansion and collapse.
- Sliding detail drawers.
- Smooth modal transitions.
- Skeleton loading states.
- Animated chart updates.
- Smooth status transitions.
- Animated notification arrival.

## Signature animations

### Orbital Agent Monitor

Display registered agents as nodes in a restrained orbital visualization.

Show:

- Agent identity.
- Active/inactive state.
- Current workflow.
- Recent activity.
- Security status.

Use gentle orbital or pulse animations without sacrificing readability.

### Transaction Verification

Animate the sequence:

Payment Requested → Mandate Verification → Provenance Validation → Policy Evaluation → Execution Decision.

Show the actual result returned by the backend.

### Provenance Trace

Animate the recorded path of a financial value through:

Source Document → Extraction → Persistent Storage → Agent Session → Payment Proposal.

Highlight suspicious lineage.

### RedTeamLab

Animate the baseline and protected execution paths side by side.

Show events in chronological order.

Reveal actual simulator outcomes.

### Forensic Verification

Display progress while verifying audit-event integrity.

Show the final verification result only after backend verification completes.

## Accessibility

Respect `prefers-reduced-motion`.

Do not use perpetual flashing.

Animations must never prevent a user from interacting with the application.

---

# 5. APPLICATION NAVIGATION

Build a collapsible left sidebar.

Primary navigation:

1. Overview
2. Agents
3. Mandates
4. Transactions
5. Workflows
6. Provenance
7. Approvals
8. Security Lab
9. Evidence
10. Settings

The sidebar should support a compact icon-only state.

Use a consistent top navigation bar with:

- Page title.
- Global search.
- Environment indicator.
- Notifications.
- User profile.
- Theme branding.

The application must clearly indicate that it is operating in a **SIMULATED / SANDBOX ENVIRONMENT**.

---

# 6. OVERVIEW DASHBOARD

Build a functional security command center.

Display backend-derived metrics:

- Registered agents.
- Active workflows.
- Inspected actions.
- Allowed actions.
- Observed actions.
- Escalated actions.
- Denied actions.
- Pending approvals.
- Critical alerts.
- Simulated executions.
- Recent incidents.

Include:

- Metric cards.
- Policy decision distribution chart.
- Recent transaction table.
- Live security activity feed.
- Active agent summary.
- Recent alerts.
- Quick access to Security Lab.

All displayed metrics must come from backend records.

Do not hardcode fabricated operational metrics.

Seeded demo data is acceptable when clearly identified.

---

# 7. AGENT MANAGEMENT

Implement working agent management.

Required capabilities:

- List registered agents.
- View agent details.
- Register an agent.
- Assign agent capabilities.
- View agent workflows.
- View recent tool calls.
- View associated mandates.
- Activate or deactivate an agent.

Enforce authorization rules on the backend.

The frontend must not be able to grant an agent unrestricted financial execution authority.

---

# 8. MANDATE MANAGEMENT

Implement signed, versioned financial mandates.

Each mandate should support:

- Organization.
- Owner.
- Authorized agent.
- Allowed tools.
- Approved suppliers.
- Currency.
- Per-transaction limit.
- Aggregate spending limit.
- Validity period.
- Approval requirements.
- Version.
- Status.
- Cryptographic digest.
- Signature metadata.

Required actions:

- Create mandate.
- View mandate.
- Verify mandate.
- Revoke mandate.
- Expire mandate.
- Create a new mandate version.

Use deterministic canonical serialization.

Sign mandates using Ed25519.

Keep signing keys outside agent processes.

Any modification to signed mandate content must invalidate its signature.

Expired or revoked mandates must not authorize new executions.

---

# 9. PROCUREMENT WORKFLOW

Implement a working synthetic procurement workflow.

Include:

- Supplier registry.
- Synthetic invoices.
- Invoice field extraction.
- Purchase order creation.
- Payment preparation.
- Policy evaluation.
- Human approval when required.
- Simulated execution.
- Receipt generation.

The workflow must preserve important metadata across each stage.

Support at least two agent sessions in a single workflow.

Persist session relationships in the database.

The application must demonstrate that information introduced in Session A can be traced when reused in Session B.

---

# 10. MCP GATEWAY

Implement an MCP-first integration layer.

Expose controlled tools including:

- `mandate_get`
- `supplier_lookup`
- `invoice_read`
- `purchase_order_create`
- `payment_prepare`
- `payment_authorize`
- `payment_execute`
- `workflow_trace`

The gateway must:

- Authenticate the calling agent.
- Validate tool arguments.
- Check tool permissions.
- Record actual tool requests.
- Record tool responses.
- Preserve workflow and session references.
- Attach provenance references.
- Route sensitive operations through policy enforcement.

Unknown sensitive tools must be denied by default.

Agents must never receive simulator execution credentials.

Do not allow a direct execution route that bypasses ExecutionShield.

---

# 11. FIELD-LEVEL PROVENANCE ENGINE

Implement provenance tracking for payment-critical fields.

Track:

- Supplier identity.
- Beneficiary reference.
- Amount.
- Currency.
- Invoice reference.
- Purchase order reference.

Store:

- Source record.
- Source type.
- Source hash.
- Trust status.
- Extraction event.
- Transformation event.
- Parent provenance.
- Session.
- Workflow.
- Related tool event.

Use persistent relational records and lineage edges.

The system must distinguish verified registry values from unverified external document values.

Unverified external values must never silently become trusted merely because an agent copied them into persistent storage.

## Provenance UI

Use React Flow.

Display:

- Source document nodes.
- Extraction nodes.
- Field nodes.
- Storage nodes.
- Session nodes.
- Payment proposal nodes.
- Decision nodes.

Clicking a node opens an inspector.

The inspector should display:

- Node type.
- Event ID.
- Session ID.
- Source reference.
- Trust label.
- Related policy findings.
- Masked financial value.

Support:

- Zoom.
- Pan.
- Fit to view.
- Trace origin.
- Highlight suspicious paths.
- Read-only workflow replay.

Do not invent lineage edges. Render only recorded relationships.

---

# 12. TEMPORALGUARD POLICY ENGINE

Implement a deterministic, backend-enforced policy engine.

Support the following decisions:

- `ALLOW`
- `OBSERVE`
- `ESCALATE`
- `DENY`

Evaluate:

- Caller identity.
- Agent authorization.
- Mandate validity.
- Mandate signature.
- Allowed tools.
- Supplier restrictions.
- Beneficiary restrictions.
- Currency.
- Transaction amount.
- Aggregate spending limits.
- Invoice constraints.
- Provenance trust.
- Previous workflow events.
- Cross-session changes.
- Duplicate requests.
- Approval requirements.
- Delegation constraints.

Return stable reason codes.

Examples:

- `INVALID_OR_INACTIVE_MANDATE`
- `TOOL_NOT_AUTHORIZED`
- `SUPPLIER_MISMATCH`
- `BENEFICIARY_NOT_MATCHED`
- `SOURCE_EXTERNAL_UNVERIFIED`
- `PER_TRANSACTION_LIMIT_EXCEEDED`
- `AGGREGATE_LIMIT_EXCEEDED`
- `DUPLICATE_OR_REPLAY`
- `APPROVAL_REQUIRED`
- `PAYLOAD_DIGEST_MISMATCH`

Hard-deny conditions must not be bypassable through human approval.

The system must fail closed when mandatory authorization information is missing or unverifiable.

---

# 13. APPROVAL CENTER

Implement a real approval workflow.

An approval request must contain:

- Exact transaction payload.
- Supplier.
- Beneficiary reference.
- Masked account reference.
- Amount.
- Currency.
- Invoice reference.
- Mandate.
- Payload digest.
- Expiration.
- One-time nonce.
- Policy findings.
- Provenance references.

Only authorized human users can approve.

Agent-supplied flags such as `user_confirmed=true` must never count as approval.

Approval must be bound cryptographically to the exact canonical transaction payload.

A material payload change must invalidate the approval.

Approval must be single-use.

Expired, revoked, consumed, or mismatched approvals must be rejected.

Implement appropriate role checks and signing behavior.

---

# 14. EXECUTIONSHIELD

Implement a controlled execution boundary.

ExecutionShield must:

1. Authenticate the execution request.
2. Resolve the mandate.
3. Verify mandate validity and signature.
4. Verify the current policy decision.
5. Revalidate critical provenance.
6. Recompute the canonical payload digest.
7. Verify required approval.
8. Validate expiry and nonce.
9. Reserve budget atomically.
10. Enforce idempotency.
11. Invoke the simulated payment adapter.
12. Record the actual execution outcome.

A decision of `ALLOW` is not proof of successful execution.

Distinguish:

- Attempted.
- Authorized.
- Submitted.
- Accepted.
- Completed.
- Failed.
- Timed out.
- Outcome unknown.

Never blindly retry a payment after an uncertain outcome.

Use idempotency keys and existing execution references.

Prevent concurrent requests from exceeding aggregate budgets.

---

# 15. FORENSICLEDGER

Implement a tamper-evident audit system.

Every sensitive action must create an attributable event.

Store:

- Event ID.
- Organization.
- Workflow.
- Session.
- Agent or user.
- Event type.
- Timestamp.
- Parent event references.
- Mandate reference.
- Policy version.
- Decision.
- Execution outcome.
- Previous event hash.
- Current event hash.

Use canonical event serialization and hash chaining.

Provide a backend verification function that recomputes and validates the chain.

The UI must display verification status based on real backend results.

Audit records must not be silently overwritten.

Provide redacted evidence export.

Do not expose private keys, credentials, or unmasked account information.

---

# 16. REDTEAMLAB

Build a fully working security simulation laboratory.

This is one of the most important hackathon features.

Support three environments:

1. Baseline.
2. Basic Controls.
3. MandateTrail Protected.

Run identical synthetic scenarios against each environment.

## Required attack scenarios

Implement at least:

1. Indirect prompt injection in an invoice.
2. Cross-session beneficiary poisoning.
3. Supplier beneficiary substitution.
4. Payment splitting to exceed aggregate budget.
5. Approval replay.
6. Delegation privilege escalation.
7. Payload modification after approval.
8. Concurrent budget reservation race.
9. Duplicate invoice submission.
10. Forged approval metadata.

## Benign scenarios

Include:

- Valid supplier payment.
- Correct beneficiary.
- Harmless invoice formatting changes.
- Authorized split payment.
- Valid human-approved transaction.
- Safe idempotent retry.
- Authorized read-only supplier lookup.

## RedTeamLab UI

Create:

- Scenario selector.
- Environment selector.
- Run button.
- Reset button.
- Side-by-side comparison.
- Animated execution timeline.
- Policy decision display.
- Final outcome.
- Reason codes.
- Evidence links.
- Metrics comparison.

The UI must run actual backend scenarios.

Do not implement a fake timer that merely changes a label to BLOCKED.

The simulation must generate real records in the database.

## Evaluation metrics

Calculate:

- Attack Success Rate.
- Attack Detection Rate.
- False Intervention Rate.
- Benign Completion Rate.
- Payload Integrity Rate.
- Cross-Session Detection Rate.
- Decision Latency.
- Audit Completeness.

Report raw trial counts and denominators.

Do not claim security effectiveness from fabricated numbers.

---

# 17. TRANSACTIONS PAGE

Implement a searchable, filterable transaction table.

Columns:

- Transaction ID.
- Supplier.
- Amount.
- Currency.
- Agent.
- Workflow.
- Policy decision.
- Execution outcome.
- Timestamp.

Support filters by:

- Status.
- Agent.
- Supplier.
- Date.
- Workflow.

Clicking a transaction must open a detail drawer.

The drawer should contain tabs:

- Overview.
- Policy Checks.
- Provenance.
- Approval.
- Execution.
- Evidence.

Use readable explanations alongside technical reason codes.

Example:

**Payment blocked because the beneficiary does not match the verified supplier record.**

Display the technical reason code below the explanation.

---

# 18. WORKFLOW EXPLORER

Implement a chronological workflow viewer.

Show:

- Workflow creation.
- Session boundaries.
- Agent tool calls.
- Invoice processing.
- Supplier lookup.
- Data modifications.
- Policy decisions.
- Approval requests.
- Execution attempts.
- Simulator outcomes.

Add an animated read-only replay mode.

The replay must reconstruct persisted events.

It must not modify financial state.

Allow selecting events to inspect metadata and provenance.

---

# 19. EVIDENCE CENTER

Implement an evidence explorer.

Support:

- Workflow selection.
- Audit event listing.
- Hash-chain verification.
- Mandate signature verification.
- Policy decision inspection.
- Approval metadata inspection.
- Execution receipt inspection.
- Redacted evidence export.

Generate a downloadable JSON evidence package.

Include a human-readable report if practical.

Evidence must come from persisted records.

---

# 20. AUTHENTICATION AND AUTHORIZATION

Implement backend-enforced authentication and role-based access control.

Support roles such as:

- Administrator.
- Finance Owner.
- Finance Operator.
- Security Analyst.
- Auditor.

Restrict sensitive operations by role.

Do not rely on frontend visibility to enforce permissions.

Use secure password hashing or an appropriate development authentication mechanism.

Document the limitations of local demo authentication.

Never ship real credentials or secrets in source control.

---

# 21. DATABASE DESIGN

Use PostgreSQL with SQLAlchemy and Alembic.

Implement the core entities described in the PDF, including:

- Organization.
- User.
- Agent.
- Mandate.
- Workflow.
- Session.
- WorkflowEvent.
- SourceRecord.
- FieldProvenance.
- PolicyDecision.
- Approval.
- BudgetReservation.
- ExecutionReceipt.
- SecurityAlert.

Add supporting entities where necessary.

Requirements:

- UUID identifiers where appropriate.
- Foreign keys.
- Tenant-scoped queries.
- Unique nonce constraints.
- Unique idempotency keys.
- Transactional budget reservations.
- Integer minor-unit money representation.
- Versioned policies.
- Masked financial identifiers.
- Appropriate database indexes.

Use migrations rather than ad hoc production schema creation.

---

# 22. REST API

Implement versioned endpoints under:

`/api/v1`

At minimum, support the relevant operations from the blueprint:

- Mandate creation and retrieval.
- Workflow creation.
- Event ingestion.
- Provenance tracing.
- Policy evaluation.
- Approval creation.
- Approval signing.
- Controlled execution.
- Audit retrieval.
- RedTeamLab runs.

Add the necessary endpoints for:

- Authentication.
- Dashboard metrics.
- Agent management.
- Supplier management.
- Transactions.
- Alerts.
- Workflow replay.
- Evidence export.
- Health checks.

Use Pydantic schemas.

Return stable error codes and correlation IDs.

Generate OpenAPI documentation.

Protect non-public endpoints.

---

# 23. PROJECT STRUCTURE

Use a maintainable monorepo.

Suggested structure:

```text
MandateTrail/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── hooks/
│   ├── lib/
│   ├── types/
│   └── public/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── security/
│   │   ├── provenance/
│   │   ├── policy/
│   │   ├── execution/
│   │   ├── mcp/
│   │   ├── redteam/
│   │   └── audit/
│   ├── alembic/
│   └── tests/
├── scripts/
├── docs/
├── docker-compose.yml
├── run.bat
├── stop.bat
├── .env.example
├── README.md
└── PROJECT_STATUS.md
```

You may improve this structure if necessary.

Keep security-sensitive business logic in the backend.

Do not duplicate policy enforcement in frontend code.

---

# 24. WINDOWS ONE-CLICK STARTUP

The final project must run on Windows.

Create a working:

`run.bat`

The script must:

1. Check required dependencies.
2. Verify Docker availability if Docker is required.
3. Display clear instructions if prerequisites are missing.
4. Initialize local configuration safely.
5. Start PostgreSQL.
6. Wait for database readiness.
7. Run database migrations.
8. Seed the demo environment if it has not already been seeded.
9. Start the FastAPI backend.
10. Start the Next.js frontend.
11. Display the local URLs.
12. Open the frontend in the default browser when ready.

The script must not silently fail.

It must handle paths containing spaces.

It must not overwrite existing environment settings.

It must not duplicate seed data on repeated launches.

Create:

`stop.bat`

This should stop project services without terminating unrelated processes.

If Docker Compose is the most reliable implementation, use it to orchestrate the services while retaining `run.bat` as the one-click Windows entry point.

Do not claim that `run.bat` is verified unless it has actually been tested in a compatible environment.

---

# 25. DEMO DATA

Create realistic synthetic data.

Include:

- Demo organization.
- Demo users with different roles.
- Registered procurement agent.
- Signed active mandate.
- Verified suppliers.
- Synthetic invoices.
- Purchase orders.
- Approved transactions.
- Blocked transactions.
- Escalated transactions.
- Cross-session attack workflow.
- Provenance records.
- Audit events.
- Execution receipts.

Use fake account references and fake supplier information.

The demo should be understandable immediately after startup.

Provide a documented demo login or local development authentication flow.

---

# 26. AUTOMATED TESTING

Write real automated tests.

At minimum, test:

- Mandate signing and verification.
- Mandate tampering.
- Expired mandates.
- Revoked mandates.
- Unknown tools.
- Supplier mismatch.
- Beneficiary mismatch.
- Unverified provenance.
- Cross-session persistence.
- Per-transaction limit.
- Aggregate budget limit.
- Concurrent reservation race.
- Approval payload modification.
- Approval expiry.
- Approval replay.
- Duplicate execution.
- Idempotent retries.
- Audit hash-chain integrity.
- Tenant isolation.
- Role authorization.
- Benign transaction completion.
- RedTeamLab scenario execution.

Add API integration tests.

Add frontend smoke tests where practical.

Test the complete workflow from invoice processing through simulated execution and audit receipt.

Never replace failing tests with fabricated passing results.

---

# 27. HACKATHON DEMO MODE

Implement a guided demonstration mode.

The demo should explain MandateTrail in approximately three to five minutes.

## Scene 1 — Authority

Show the signed mandate and the procurement agent's permitted actions.

## Scene 2 — Attack Introduction

Process a synthetic invoice containing an unauthorized beneficiary substitution.

## Scene 3 — Cross-Session Persistence

Show how the suspicious value enters persistent storage in Session A and is retrieved in Session B.

## Scene 4 — Security Enforcement

Show TemporalGuard detecting the violation and ExecutionShield preventing unauthorized simulated execution.

## Scene 5 — Evidence

Open the provenance graph and forensic audit record.

## Scene 6 — Comparison

Run the same scenario against the baseline and protected environments.

Show the actual difference in outcomes.

The demo must be reproducible.

Provide a reset function that restores the sandbox to a known state.

---

# 28. PERFORMANCE AND USABILITY

The frontend must be responsive and easy to understand.

Requirements:

- Desktop-first professional layout.
- Usable tablet layout.
- Reasonable mobile behavior.
- Clear loading states.
- Helpful error messages.
- Search and filtering.
- Empty states.
- Accessible contrast.
- Keyboard navigation.
- Reduced-motion support.
- Consistent terminology.

Avoid excessive animations or unnecessarily complex components.

Prefer reusable tables, cards, dialogs, drawers, and timelines.

Use pagination or server-side filtering for potentially large datasets.

---

# 29. SECURITY REQUIREMENTS

Apply secure engineering practices throughout the prototype.

Mandatory invariants:

- No real payment execution.
- No payment credentials in agents.
- No sensitive execution bypass around ExecutionShield.
- No approval valid for a different payload.
- No silent promotion of unverified beneficiary data.
- No aggregate overspending through concurrent requests.
- No unrestricted unknown sensitive tools.
- No unauthenticated mandate administration.
- No agent-generated human approval.
- No silently overwritten audit events.
- No fabricated provenance or execution receipts.
- No hardcoded private keys committed to the repository.

Do not claim the prototype is production-certified or regulator-approved.

Document remaining security limitations.

---

# 30. IMPLEMENTATION PROCESS

Work in the following order.

## Phase 1 — Repository and infrastructure

Create the project structure, database, backend, frontend, Docker configuration, and startup scripts.

Verify basic startup.

## Phase 2 — Backend foundations

Implement authentication, database models, migrations, agent registration, supplier registry, and mandates.

## Phase 3 — Security core

Implement mandate signing, provenance tracking, TemporalGuard, approval binding, ExecutionShield, and ForensicLedger.

## Phase 4 — Procurement and MCP integration

Implement the synthetic procurement agent, controlled MCP tools, invoice processing, and end-to-end workflow.

## Phase 5 — Orbital Intelligence frontend

Build the complete responsive design system, navigation, dashboard, forms, tables, graphs, and animations.

## Phase 6 — RedTeamLab

Implement attack scenarios, benign scenarios, baseline comparison, reproducible runs, and metrics.

## Phase 7 — Integration

Connect every frontend screen to working backend endpoints.

Remove placeholder actions.

Ensure that displayed decisions reflect persisted backend results.

## Phase 8 — Testing

Run migrations, backend tests, frontend checks, and end-to-end smoke tests.

Fix failures.

## Phase 9 — Packaging

Create the final project ZIP.

Include all required source code, scripts, documentation, migrations, and configuration templates.

---

# 31. DEFINITION OF DONE

The project is complete only when:

- The frontend starts.
- The backend starts.
- PostgreSQL connects.
- Migrations run.
- Demo data loads.
- Authentication works.
- Agents can be viewed and managed.
- Mandates can be created, signed, and verified.
- Procurement workflows execute.
- MCP tool calls are captured.
- Provenance persists across sessions.
- TemporalGuard returns real policy decisions.
- Approvals are bound to exact transaction payloads.
- ExecutionShield controls the simulator.
- Audit events are stored and verifiable.
- RedTeamLab runs actual scenarios.
- The dashboard displays real backend-derived data.
- The provenance graph displays recorded relationships.
- The Orbital Intelligence theme is applied consistently.
- Important buttons and controls work.
- Automated tests pass.
- The Windows startup procedure is documented.
- The final ZIP is generated.

If any requirement remains incomplete, explicitly identify it.

Do not falsely report completion.

---

# 32. FINAL DELIVERABLE

Produce:

`MandateTrail_Orbital_Intelligence.zip`

The ZIP must contain the complete project.

It must include:

- Frontend source code.
- Backend source code.
- Database migrations.
- MCP integration.
- Security modules.
- Simulation modules.
- Automated tests.
- Demo seed data.
- Docker Compose configuration.
- `run.bat`.
- `stop.bat`.
- `.env.example`.
- README.
- Architecture documentation.
- API documentation.
- Testing instructions.
- Known limitations.

Do not include unnecessary generated dependency folders such as `node_modules`, Python virtual environments, or build caches.

## Final response format

After implementation, report:

1. Project ZIP location.
2. Implemented features.
3. How to start the application.
4. Frontend and backend URLs.
5. Demo login instructions.
6. Automated test results.
7. Verified and unverified functionality.
8. Known limitations.

If your environment cannot run Windows batch files, clearly state that Windows execution was not directly verified.

---

# 33. CRITICAL INSTRUCTIONS

**Do not build a static frontend prototype and call it a complete project.**

**Do not fake backend responses or security decisions.**

**Do not substitute an animated mockup for the provenance engine.**

**Do not replace cryptographic approval validation with a boolean.**

**Do not make RedTeamLab a hardcoded animation.**

**Do not bypass the policy engine to make demo transactions succeed.**

**Do not use real financial credentials or live banking integrations.**

**Do not invent test results.**

If a requirement is technically difficult, implement the smallest secure, functional version rather than replacing it with a placeholder.

Prioritize correctness, integration, maintainability, and demonstrability.

The finished project should feel like a serious, polished fintech cybersecurity platform.

Its visual identity must be unmistakably **Orbital Intelligence**:

Deep navy-black surfaces, refined sapphire-blue interactions, subtle violet intelligence indicators, restrained orbital telemetry graphics, and smooth purposeful animations.

Its technical identity must be unmistakably **MandateTrail**:

Every financial action is linked to its authority, provenance, policy decision, and actual execution outcome.

---

# FINAL EXECUTION COMMAND

Read the entire attached MandateTrail blueprint.

Inspect the available development environment.

Create an implementation checklist.

Then begin building immediately.

Continue through implementation, integration, testing, and packaging.

Do not stop at the planning stage.

Deliver the complete runnable MandateTrail application as:

**MandateTrail_Orbital_Intelligence.zip**

with a documented Windows `run.bat` startup process and a fully integrated synthetic financial security backend.
