# MCP integration

The official Python MCP SDK exposes eight stdio tools in `backend/app/mcp_server.py`: mandate_get, supplier_lookup, invoice_read, purchase_order_create, payment_prepare, payment_authorize, payment_execute, workflow_trace.

Start the API. Register an agent using an administrator/owner, and copy its one-time token. Create an authorized mandate, workflow and session through the human API/UI. Configure your MCP client to launch:

```text
command: <absolute project folder>/.venv/Scripts/python.exe
args: ["-m", "app.mcp_server"]
cwd: <absolute project folder>/backend
env:
  MT_API_URL: http://127.0.0.1:8000
  MT_AGENT_TOKEN: <one-time registration token>
  MT_WORKFLOW_ID: <authorized workflow ID>
  MT_SESSION_ID: <workflow session ID>
```

The stdio process uses an agent bearer token to invoke `/api/v1/gateway/call`; no human signing/session credentials are present. The gateway validates caller, active mandate, capability, workflow/session ownership and tool arguments. It records request and response events and routes execution through the protected domain boundary. Unknown tools are denied and audited.

The local stdio adapter is not a public OAuth-protected MCP HTTP resource server. Internet-exposed MCP/OAuth deployment, token audience binding, TLS and enterprise identity integration are deferred. The SDK transport and REST gateway are separately testable; see TESTING.md for actual test coverage.
