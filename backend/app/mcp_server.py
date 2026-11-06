"""Official MCP SDK stdio adapter. Agent token stays local to the client process.
Run: python -m app.mcp_server. Set MT_AGENT_TOKEN, MT_WORKFLOW_ID, MT_SESSION_ID.
The adapter cannot sign mandates/approvals or invoke an unprotected simulator.
"""
import os
import httpx
from mcp.server.mcpserver import MCPServer

mcp = MCPServer('MandateTrail Controlled Gateway')
def call(tool, arguments):
    with httpx.Client(timeout=60) as client:
        response = client.post(os.environ.get('MT_API_URL','http://127.0.0.1:8000') + '/api/v1/gateway/call', headers={'Authorization':'Bearer '+os.environ['MT_AGENT_TOKEN']}, json={'tool':tool,'workflow_id':os.environ['MT_WORKFLOW_ID'],'session_id':os.environ['MT_SESSION_ID'],'arguments':arguments})
        response.raise_for_status(); return response.json()

@mcp.tool()
def mandate_get(): return call('mandate_get', {})
@mcp.tool()
def supplier_lookup(supplier_id: str): return call('supplier_lookup', {'supplier_id':supplier_id})
@mcp.tool()
def invoice_read(supplier_id: str, amount_minor: int, invoice_ref: str): return call('invoice_read', {'supplier_id':supplier_id,'amount_minor':amount_minor,'invoice_ref':invoice_ref})
@mcp.tool()
def purchase_order_create(supplier_id: str, amount_minor: int, currency: str, invoice_ref: str): return call('purchase_order_create', {'supplier_id':supplier_id,'amount_minor':amount_minor,'currency':currency,'invoice_ref':invoice_ref})
@mcp.tool()
def payment_prepare(supplier_id: str, beneficiary_ref: str, amount_minor: int, currency: str, invoice_ref: str, purchase_order_id: str, provenance_refs: list[str], idempotency_key: str):
    return call('payment_prepare',dict(workflow_id=os.environ['MT_WORKFLOW_ID'],session_id=os.environ['MT_SESSION_ID'],supplier_id=supplier_id,beneficiary_ref=beneficiary_ref,amount_minor=amount_minor,currency=currency,invoice_ref=invoice_ref,purchase_order_id=purchase_order_id,provenance_refs=provenance_refs,idempotency_key=idempotency_key))
@mcp.tool()
def payment_authorize(transaction_id: str): return call('payment_authorize', {'transaction_id':transaction_id})
@mcp.tool()
def payment_execute(transaction_id: str, approval_id: str | None = None):
    args = {'transaction_id':transaction_id}
    if approval_id: args['approval_id'] = approval_id
    return call('payment_execute', args)
@mcp.tool()
def workflow_trace(): return call('workflow_trace', {})
if __name__ == '__main__': mcp.run(transport='stdio')
