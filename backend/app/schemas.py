from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

TOOLS = ['mandate_get', 'supplier_lookup', 'invoice_read', 'purchase_order_create', 'payment_prepare', 'payment_authorize', 'payment_execute', 'workflow_trace']
class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
class Login(Strict):
    email: str
    password: str
class AgentInput(Strict):
    name: str = Field(min_length=2, max_length=100)
    capabilities: list[str] = Field(default_factory=lambda: list(TOOLS))
    parent_agent: str | None = None
class MandateInput(Strict):
    name: str = Field(min_length=2, max_length=100)
    agent_id: str
    suppliers: list[str] = Field(min_length=1)
    allowed_tools: list[str] = Field(default_factory=lambda: list(TOOLS))
    currency: str = Field(default='INR', pattern='^[A-Z]{3}$')
    per_transaction: int = Field(default=500000, gt=0, le=1000000000)
    aggregate: int = Field(default=1500000, gt=0, le=1000000000)
    approval_above: int = Field(default=100000, ge=0)
    valid_days: int = Field(default=30, ge=1, le=365)
class SupplierInput(Strict):
    name: str = Field(min_length=2, max_length=100)
    beneficiary_ref: str = Field(pattern='^BEN-[A-Z0-9-]{3,40}$')
class WorkflowInput(Strict):
    mandate_id: str
    title: str = Field(default='Procurement workflow', max_length=100)
class ProcurementInput(Strict):
    mandate_id: str
    supplier_id: str
    amount_minor: int = Field(default=48000, gt=0, le=1000000000)
    invoice_ref: str = Field(default='INV-DEMO', min_length=1, max_length=100)
    poison: bool = False
    simulator_outcome: Literal['COMPLETED', 'FAILED', 'TIMED_OUT', 'OUTCOME_UNKNOWN'] = 'COMPLETED'
class PaymentInput(Strict):
    workflow_id: str
    session_id: str
    supplier_id: str
    beneficiary_ref: str = Field(max_length=80)
    amount_minor: int = Field(gt=0, le=1000000000)
    currency: str = Field(default='INR', pattern='^[A-Z]{3}$')
    invoice_ref: str = Field(min_length=1, max_length=100)
    purchase_order_id: str
    provenance_refs: list[str] = Field(min_length=1)
    idempotency_key: str = Field(min_length=5, max_length=100)
    simulator_outcome: Literal['COMPLETED', 'FAILED', 'TIMED_OUT', 'OUTCOME_UNKNOWN'] = 'COMPLETED'
class ExecuteInput(Strict):
    transaction_id: str
    approval_id: str | None = None
class GatewayInput(Strict):
    tool: str
    workflow_id: str
    session_id: str
    arguments: dict = Field(default_factory=dict)
class LabInput(Strict):
    scenario: str
    environments: list[Literal['baseline', 'basic', 'protected']] = Field(default_factory=lambda: ['baseline', 'basic', 'protected'])
