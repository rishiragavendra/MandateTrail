"""Domain services: all payment paths converge on ExecutionShield.execute."""
import re
import secrets
from datetime import datetime, timedelta, timezone
from time import perf_counter
from sqlalchemy import select, update
from .db import Record, Mandate, Approval, Reservation, Audit, Organization, now, uid
from .crypto import digest, sign, verify, KEY_ID
from .schemas import TOOLS, MandateInput, PaymentInput

POLICY_VERSION = 'TemporalGuard/1.0'
ORG = 'orbital-demo'

class DomainError(Exception):
    def __init__(self, code, status=400): self.code, self.status = code, status

def require(condition, code, status=400):
    if not condition: raise DomainError(code, status)
def future(minutes=15): return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
def expired(value):
    try: return datetime.fromisoformat(value) <= datetime.now(timezone.utc)
    except Exception: return True
def records(db, org, kind): return list(db.scalars(select(Record).where(Record.org == org, Record.kind == kind).order_by(Record.created.desc())))
def get(db, org, rid, kind=None):
    obj = db.get(Record, rid)
    require(obj is not None and obj.org == org and (kind is None or obj.kind == kind), 'RECORD_NOT_FOUND', 404)
    return obj
def mandate(db, org, mid):
    m = db.get(Mandate, mid)
    require(m is not None and m.org == org, 'MANDATE_NOT_FOUND', 404)
    return m
def add(db, org, kind, data, parent=None):
    r = Record(id=uid(), org=org, kind=kind, parent=parent, data=data, created=now())
    db.add(r); db.flush()
    return r
def wire(r): return {'id': r.id, 'kind': r.kind, 'created': r.created, 'parent': r.parent, **r.data}
def mandate_wire(m): return {'id': m.id, **m.payload, 'digest': m.digest, 'signature': m.signature, 'status': m.status, 'spent': m.spent, 'created': m.created, 'signature_valid': valid_mandate(m), 'key_id': KEY_ID}
def valid_mandate(m): return m.status == 'ACTIVE' and not expired(m.payload['expires']) and verify(m.payload, m.signature) and digest(m.payload) == m.digest

def audit(db, org, event_type, actor, workflow=None, session=None, data=None):
    # Organization row serializes audit append in PostgreSQL; SQLite uses BEGIN IMMEDIATE.
    db.execute(select(Organization).where(Organization.id == org).with_for_update())
    previous = db.scalar(select(Audit).where(Audit.org == org).order_by(Audit.seq.desc()).limit(1))
    eid = uid()
    def audit_numbers(v):
        if isinstance(v, float): return format(v, '.6f')
        if isinstance(v, dict): return {k: audit_numbers(x) for k,x in v.items()}
        if isinstance(v, list): return [audit_numbers(x) for x in v]
        return v
    content = {'event_id': eid, 'organization': org, 'workflow': workflow, 'session': session, 'actor': actor, 'type': event_type, 'timestamp': now(), 'policy_version': POLICY_VERSION, 'data': audit_numbers(data or {}), 'parent_events': [previous.id] if previous else []}
    prev = previous.digest if previous else '0' * 64
    h = digest({'content': content, 'previous': prev})
    e = Audit(id=eid, org=org, workflow=workflow, content=content, previous=prev, digest=h, signature=sign({'hash': h, 'key_id': KEY_ID}))
    db.add(e); db.flush()
    return e

def audit_verify(db, org):
    prev, failures, count = '0' * 64, [], 0
    for e in db.scalars(select(Audit).where(Audit.org == org).order_by(Audit.seq)):
        count += 1
        h = digest({'content': e.content, 'previous': e.previous})
        if e.previous != prev or e.digest != h or not verify({'hash': h, 'key_id': KEY_ID}, e.signature): failures.append(e.id)
        prev = e.digest
    return {'valid': not failures, 'events_checked': count, 'failures': failures, 'head_hash': prev, 'key_id': KEY_ID, 'checkpoint_signature': sign({'hash': prev, 'key_id': KEY_ID})}

def create_agent(db, org, actor, data):
    require(set(data.capabilities) <= set(TOOLS), 'UNKNOWN_CAPABILITY')
    if data.parent_agent:
        p = get(db, org, data.parent_agent, 'agent')
        require(p.data['active'] and set(data.capabilities) <= set(p.data['capabilities']), 'DELEGATION_PRIVILEGE_ESCALATION')
    token = secrets.token_urlsafe(32)
    r = add(db, org, 'agent', {'name': data.name, 'capabilities': data.capabilities, 'parent_agent': data.parent_agent, 'active': True, 'token_hash': digest(token)})
    audit(db, org, 'agent.registered', actor, data={'agent_id': r.id})
    return r, token

def create_mandate(db, org, actor, spec: MandateInput, version=1, prior=None):
    a = get(db, org, spec.agent_id, 'agent')
    require(set(spec.allowed_tools) <= set(a.data['capabilities']), 'TOOL_NOT_AUTHORIZED')
    for sid in spec.suppliers: get(db, org, sid, 'supplier')
    mid = uid()
    payload = {'schema_version': 1, 'id': mid, 'organization': org, 'owner': actor, 'version': version, 'previous_version': prior, **spec.model_dump(exclude={'valid_days'}), 'issued': now(), 'expires': future(spec.valid_days * 1440), 'key_id': KEY_ID}
    m = Mandate(id=mid, org=org, payload=payload, signature=sign(payload), digest=digest(payload), spent=0, status='ACTIVE')
    db.add(m); db.flush()
    audit(db, org, 'mandate.signed', actor, data={'mandate_id': mid, 'digest': m.digest, 'version': version})
    return m

def create_workflow(db, org, actor, mid, title):
    m = mandate(db, org, mid)
    require(valid_mandate(m), 'INVALID_OR_INACTIVE_MANDATE')
    w = add(db, org, 'workflow', {'title': title, 'mandate_id': mid, 'agent_id': m.payload['agent_id'], 'state': 'ACTIVE'})
    audit(db, org, 'workflow.created', actor, w.id, data={'mandate_id': mid})
    return w

def create_session(db, org, actor, wid, parent=None):
    w = get(db, org, wid, 'workflow')
    if parent: require(get(db, org, parent, 'session').parent == wid, 'SESSION_WORKFLOW_MISMATCH')
    r = add(db, org, 'session', {'agent_id': w.data['agent_id'], 'parent_session_id': parent, 'label': 'Session B · payment preparation' if parent else 'Session A · invoice intake'}, wid)
    audit(db, org, 'session.started', actor, wid, r.id, {'parent_session': parent})
    return r

def provenance(db, org, wid, sid, field, value, source, trust, parent=None, stage='extraction', event_id=None):
    return add(db, org, 'provenance', {'workflow_id': wid, 'session_id': sid, 'field': field, 'value': value, 'source_id': source.id, 'source_hash': source.data['hash'], 'trust': trust, 'parent_provenance': parent, 'stage': stage, 'event_id': event_id}, wid)

def invoice_read(db, org, actor, wid, sid, supplier_id, amount_minor, invoice_ref, beneficiary=None, formatting=False):
    supplier = get(db, org, supplier_id, 'supplier')
    raw = {'supplier_id': supplier.id, 'beneficiary_ref': beneficiary or supplier.data['beneficiary_ref'], 'amount_minor': amount_minor, 'currency': 'INR', 'invoice_ref': invoice_ref}
    source = add(db, org, 'source', {'type': 'external_invoice', 'name': invoice_ref, 'hash': digest(raw), 'trust': 'EXTERNAL_UNVERIFIED', 'fields': raw, 'formatting_only': formatting}, wid)
    e = audit(db, org, 'invoice.extracted', actor, wid, sid, {'source_id': source.id, 'source_hash': source.data['hash']})
    refs = []
    for key, val in raw.items(): refs.append(provenance(db, org, wid, sid, key, val, source, 'EXTERNAL_UNVERIFIED', event_id=e.id).id)
    return {'source_id': source.id, 'fields': raw, 'provenance_refs': refs}

def supplier_lookup(db, org, actor, wid, sid, supplier_id):
    s = get(db, org, supplier_id, 'supplier')
    source = add(db, org, 'source', {'type': 'verified_registry', 'name': s.data['name'], 'hash': digest({'supplier': s.id, 'beneficiary': s.data['beneficiary_ref']}), 'trust': 'VERIFIED_REGISTRY'}, wid)
    e = audit(db, org, 'supplier.verified', actor, wid, sid, {'supplier_id': s.id, 'source_id': source.id})
    p = provenance(db, org, wid, sid, 'beneficiary_ref', s.data['beneficiary_ref'], source, 'VERIFIED_REGISTRY', event_id=e.id)
    return {'supplier_id': s.id, **s.data, 'provenance_ref': p.id}

def cross_session_copy(db, org, actor, wid, sid, refs):
    copied = []
    for ref in refs:
        p = get(db, org, ref, 'provenance'); require(p.parent == wid, 'PROVENANCE_WORKFLOW_MISMATCH')
        source = get(db, org, p.data['source_id'], 'source')
        e = audit(db, org, 'field.persisted_then_retrieved', actor, wid, sid, {'parent_provenance': p.id, 'field': p.data['field'], 'trust': p.data['trust']})
        stored = provenance(db, org, wid, p.data['session_id'], p.data['field'], p.data['value'], source, p.data['trust'], p.id, 'persistent_storage', e.id)
        copied.append(provenance(db, org, wid, sid, p.data['field'], p.data['value'], source, p.data['trust'], stored.id, 'session_retrieval', e.id).id)
    return copied

def invoice_key(supplier, ref): return supplier + ':' + re.sub(r'[^A-Z0-9]', '', ref.upper())

def proposal_payload(db, org, actor, spec: PaymentInput):
    w = get(db, org, spec.workflow_id, 'workflow')
    session = get(db, org, spec.session_id, 'session')
    require(session.parent == w.id, 'SESSION_WORKFLOW_MISMATCH')
    m = mandate(db, org, w.data['mandate_id'])
    return {'schema_version': 1, 'organization': org, 'mandate_id': m.id, 'mandate_version': m.payload['version'], 'agent_id': actor, 'tool': 'payment_execute', **spec.model_dump(exclude={'simulator_outcome'}), 'expires': future(), 'nonce': secrets.token_urlsafe(24)}

def evaluate(db, org, payload, approval=None, exclude_tx=None):
    start = perf_counter(); reasons = []
    m = mandate(db, org, payload['mandate_id'])
    w = get(db, org, payload['workflow_id'], 'workflow')
    agent = get(db, org, w.data['agent_id'], 'agent')
    if not valid_mandate(m) or payload['mandate_version'] != m.payload['version'] or w.data['mandate_id'] != m.id: reasons.append('INVALID_OR_INACTIVE_MANDATE')
    if expired(payload['expires']): reasons.append('TRANSACTION_EXPIRED')
    if payload['agent_id'] != agent.id or m.payload['agent_id'] != agent.id or not agent.data['active']: reasons.append('AGENT_NOT_AUTHORIZED')
    if agent.data.get('parent_agent'):
        parent = get(db, org, agent.data['parent_agent'], 'agent')
        if not parent.data['active'] or not set(agent.data['capabilities']) <= set(parent.data['capabilities']): reasons.append('DELEGATION_PRIVILEGE_ESCALATION')
    if payload['tool'] not in TOOLS or payload['tool'] not in m.payload['allowed_tools'] or payload['tool'] not in agent.data['capabilities']: reasons.append('TOOL_NOT_AUTHORIZED')
    supplier = get(db, org, payload['supplier_id'], 'supplier')
    if supplier.id not in m.payload['suppliers'] or not supplier.data.get('active'): reasons.append('SUPPLIER_MISMATCH')
    if payload['beneficiary_ref'] != supplier.data['beneficiary_ref']: reasons.append('BENEFICIARY_NOT_MATCHED')
    if payload['currency'] != m.payload['currency']: reasons.append('CURRENCY_MISMATCH')
    if payload['amount_minor'] <= 0: reasons.append('INVALID_AMOUNT')
    if payload['amount_minor'] > m.payload['per_transaction']: reasons.append('PER_TRANSACTION_LIMIT_EXCEEDED')
    if m.spent + payload['amount_minor'] > m.payload['aggregate']: reasons.append('AGGREGATE_LIMIT_EXCEEDED')
    refs = []
    for rid in payload['provenance_refs']:
        p = get(db, org, rid, 'provenance')
        if p.parent != w.id: reasons.append('PROVENANCE_WORKFLOW_MISMATCH')
        refs.append(p)
    # Validate actual field values and entire ancestry; copied metadata cannot promote trust.
    for field in ('supplier_id', 'beneficiary_ref', 'amount_minor', 'currency', 'invoice_ref'):
        matching = [p for p in refs if p.data['field'] == field and p.data['value'] == payload[field]]
        if not matching: reasons.append('CRITICAL_PROVENANCE_MISSING'); continue
        if field == 'beneficiary_ref':
            trusted = False
            for p in matching:
                seen = set(); current = p; good = True
                while current:
                    if current.id in seen or current.parent != w.id or current.data['trust'] != 'VERIFIED_REGISTRY': good = False; break
                    seen.add(current.id)
                    src = get(db, org, current.data['source_id'], 'source')
                    if src.data['type'] != 'verified_registry' or src.data['hash'] != current.data['source_hash']: good = False; break
                    parent = current.data.get('parent_provenance')
                    current = get(db, org, parent, 'provenance') if parent else None
                trusted = trusted or good
            if not trusted: reasons.append('SOURCE_EXTERNAL_UNVERIFIED')
    po = get(db, org, payload['purchase_order_id'], 'purchase_order')
    if po.parent != w.id or any(po.data[k] != payload[k] for k in ['supplier_id', 'amount_minor', 'currency', 'invoice_ref']): reasons.append('PURCHASE_ORDER_MISMATCH')
    # Original invoice must substantiate every non-beneficiary field, even if agent supplies other refs.
    sources = [get(db, org, p.data['source_id'], 'source') for p in refs]
    if not any(s.data['type'] == 'external_invoice' and all(s.data['fields'][k] == payload[k] for k in ('supplier_id', 'amount_minor', 'currency', 'invoice_ref')) for s in sources): reasons.append('INVOICE_CONSTRAINT_MISMATCH')
    existing = db.scalar(select(Reservation).where(Reservation.org == org, Reservation.invoice_key == invoice_key(supplier.id, payload['invoice_ref'])))
    if existing and existing.transaction_id != exclude_tx: reasons.append('DUPLICATE_OR_REPLAY')
    needs_approval = payload['amount_minor'] > m.payload['approval_above']
    approved = False
    if approval:
        binding = {'digest': approval.digest, 'nonce': approval.nonce, 'expires': approval.expires, 'transaction_id': approval.transaction_id, 'approver': approval.approver}
        if approval.org != org or approval.transaction_id != exclude_tx or approval.digest != digest(payload): reasons.append('PAYLOAD_DIGEST_MISMATCH')
        elif approval.status != 'SIGNED' or expired(approval.expires) or not verify(binding, approval.signature): reasons.append('INVALID_OR_CONSUMED_APPROVAL')
        else: approved = True
    outcome = 'DENY' if reasons else ('ESCALATE' if needs_approval and not approved else 'ALLOW')
    if outcome == 'ESCALATE': reasons.append('APPROVAL_REQUIRED')
    if not reasons: reasons.append('ALL_REQUIRED_CONTROLS_PASSED')
    return {'outcome': outcome, 'reason_codes': list(dict.fromkeys(reasons)), 'policy_version': POLICY_VERSION, 'execution_permitted': outcome in ('ALLOW', 'OBSERVE'), 'latency_ms': round((perf_counter() - start) * 1000, 3)}

def prepare(db, org, actor, spec):
    payload = proposal_payload(db, org, actor, spec)
    decision = evaluate(db, org, payload)
    tx = add(db, org, 'transaction', {'payload': payload, 'digest': digest(payload), 'decision': decision, 'outcome': 'ATTEMPTED', 'simulator_outcome': spec.simulator_outcome}, spec.workflow_id)
    e = audit(db, org, 'payment.proposed', actor, spec.workflow_id, spec.session_id, {'transaction_id': tx.id, 'mandate_id': payload['mandate_id'], 'digest': tx.data['digest'], 'decision': decision})
    add(db, org, 'decision', {**decision, 'transaction_id': tx.id, 'event_id': e.id}, spec.workflow_id)
    if decision['outcome'] == 'ESCALATE':
        a = Approval(id=uid(), org=org, transaction_id=tx.id, digest=tx.data['digest'], nonce=secrets.token_urlsafe(24), expires=payload['expires'], status='PENDING')
        db.add(a); db.flush()
        audit(db, org, 'approval.requested', actor, spec.workflow_id, spec.session_id, {'approval_id': a.id, 'digest': a.digest})
    if decision['outcome'] == 'DENY':
        add(db, org, 'alert', {'severity': 'CRITICAL', 'title': 'Financial action denied', 'reasons': decision['reason_codes'], 'transaction_id': tx.id, 'status': 'OPEN'}, spec.workflow_id)
    return tx

def sign_approval(db, org, actor, aid):
    a = db.get(Approval, aid)
    require(a is not None and a.org == org, 'APPROVAL_NOT_FOUND', 404)
    require(a.status == 'PENDING' and not expired(a.expires), 'INVALID_OR_CONSUMED_APPROVAL')
    tx = get(db, org, a.transaction_id, 'transaction')
    require(digest(tx.data['payload']) == a.digest, 'PAYLOAD_DIGEST_MISMATCH')
    d = evaluate(db, org, tx.data['payload'], exclude_tx=tx.id)
    require(d['outcome'] == 'ESCALATE', 'APPROVAL_CANNOT_OVERRIDE_POLICY')
    a.approver = actor
    a.signature = sign({'digest': a.digest, 'nonce': a.nonce, 'expires': a.expires, 'transaction_id': a.transaction_id, 'approver': actor})
    a.status = 'SIGNED'
    audit(db, org, 'approval.signed', actor, tx.parent, data={'approval_id': a.id, 'transaction_id': tx.id, 'digest': a.digest})
    return a

def execute(db, org, actor, txid, aid=None):
    """Within a DB transaction. Conditional budget update + unique replay constraints."""
    tx = get(db, org, txid, 'transaction'); p = tx.data['payload']
    audit(db, org, 'execution.attempted', actor, tx.parent, p['session_id'], {'transaction_id': tx.id, 'mandate_id': p['mandate_id']})
    existing = db.scalar(select(Reservation).where(Reservation.idempotency == p['idempotency_key']))
    if existing:
        require(existing.org == org and existing.transaction_id == tx.id and digest(p) == tx.data['digest'], 'DUPLICATE_OR_REPLAY')
        # Never invoke adapter again, including unknown/time-out states.
        audit(db, org, 'execution.idempotent_retrieval', actor, tx.parent, data={'transaction_id': tx.id, 'outcome': tx.data['outcome']})
        return tx
    a = db.get(Approval, aid) if aid else None
    require(not aid or a is not None, 'APPROVAL_NOT_FOUND')
    if digest(p) != tx.data['digest']:
        decision = {'outcome': 'DENY', 'reason_codes': ['PAYLOAD_DIGEST_MISMATCH'], 'policy_version': POLICY_VERSION, 'execution_permitted': False}
    else: decision = evaluate(db, org, p, a, tx.id)
    if decision['outcome'] not in ('ALLOW', 'OBSERVE'):
        tx.data = {**tx.data, 'decision': decision, 'outcome': 'BLOCKED' if decision['outcome'] == 'DENY' else 'AWAITING_APPROVAL'}
        audit(db, org, 'execution.blocked', actor, tx.parent, p['session_id'], {'transaction_id': tx.id, 'decision': decision, 'outcome': tx.data['outcome']})
        return tx
    m = mandate(db, org, p['mandate_id'])
    result = db.execute(update(Mandate).where(Mandate.id == m.id, Mandate.status == 'ACTIVE', Mandate.spent + p['amount_minor'] <= m.payload['aggregate']).values(spent=Mandate.spent + p['amount_minor']).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        tx.data = {**tx.data, 'outcome': 'BLOCKED', 'decision': {**decision, 'outcome': 'DENY', 'execution_permitted': False, 'reason_codes': ['AGGREGATE_LIMIT_EXCEEDED']}}
        audit(db, org, 'execution.blocked', actor, tx.parent, data={'transaction_id': tx.id, 'decision': tx.data['decision']})
        return tx
    if a:
        consumed = db.execute(update(Approval).where(Approval.id == a.id, Approval.status == 'SIGNED').values(status='CONSUMED').execution_options(synchronize_session=False))
        require(consumed.rowcount == 1, 'INVALID_OR_CONSUMED_APPROVAL')
    db.add(Reservation(org=org, mandate_id=m.id, transaction_id=tx.id, idempotency=p['idempotency_key'], invoice_key=invoice_key(p['supplier_id'], p['invoice_ref']), amount=p['amount_minor']))
    db.flush()
    for stage in ('AUTHORIZED', 'SUBMITTED'):
        audit(db, org, 'execution.' + stage.lower(), actor, tx.parent, p['session_id'], {'transaction_id': tx.id, 'outcome': stage})
    # Private synthetic adapter. There is deliberately no standalone adapter HTTP route.
    outcome = tx.data['simulator_outcome']
    if outcome == 'COMPLETED': audit(db, org, 'execution.accepted', 'ExecutionShield', tx.parent, data={'transaction_id': tx.id, 'outcome': 'ACCEPTED'})
    receipt = add(db, org, 'receipt', {'transaction_id': tx.id, 'payload_digest': digest(p), 'adapter_reference': 'SIM-' + uid(), 'outcome': outcome, 'amount_minor': p['amount_minor'], 'currency': p['currency'], 'simulated': True}, tx.parent)
    tx.data = {**tx.data, 'decision': decision, 'outcome': outcome, 'receipt_id': receipt.id}
    audit(db, org, 'execution.result', 'ExecutionShield', tx.parent, p['session_id'], {'transaction_id': tx.id, 'mandate_id': m.id, 'receipt_id': receipt.id, 'outcome': outcome, 'digest': digest(p)})
    if outcome == 'FAILED':
        # Definitive simulator failure releases money, but invoice/idempotency remain reserved.
        db.execute(update(Mandate).where(Mandate.id == m.id).values(spent=Mandate.spent - p['amount_minor']).execution_options(synchronize_session=False))
    return tx

def gateway(db, org, agent_id, tool, wid, sid, args):
    agent = get(db, org, agent_id, 'agent'); w = get(db, org, wid, 'workflow'); s = get(db, org, sid, 'session')
    request_event = audit(db, org, 'tool.request', agent_id, wid, sid, {'tool': tool, 'arguments': args})
    m = mandate(db, org, w.data['mandate_id'])
    require(agent.data['active'] and w.data['agent_id'] == agent_id and s.parent == wid, 'AGENT_NOT_AUTHORIZED', 403)
    require(valid_mandate(m), 'INVALID_OR_INACTIVE_MANDATE', 403)
    require(tool in TOOLS and tool in agent.data['capabilities'] and tool in m.payload['allowed_tools'], 'TOOL_NOT_AUTHORIZED', 403)
    if tool == 'mandate_get':
        require(not args or args == {'mandate_id': m.id}, 'INVALID_TOOL_ARGUMENTS'); result = mandate_wire(m)
    elif tool == 'supplier_lookup':
        require(set(args) == {'supplier_id'}, 'INVALID_TOOL_ARGUMENTS')
        require(args['supplier_id'] in m.payload['suppliers'], 'SUPPLIER_MISMATCH')
        result = supplier_lookup(db, org, agent_id, wid, sid, args['supplier_id'])
    elif tool == 'invoice_read':
        require(set(args) <= {'supplier_id', 'amount_minor', 'invoice_ref', 'beneficiary', 'formatting'} and {'supplier_id', 'amount_minor', 'invoice_ref'} <= set(args), 'INVALID_TOOL_ARGUMENTS')
        require(type(args['amount_minor']) is int and args['amount_minor'] > 0 and isinstance(args['invoice_ref'], str) and len(args['invoice_ref']) <= 100, 'INVALID_TOOL_ARGUMENTS')
        result = invoice_read(db, org, agent_id, wid, sid, **args)
    elif tool == 'purchase_order_create':
        require(set(args) == {'supplier_id', 'amount_minor', 'currency', 'invoice_ref'}, 'INVALID_TOOL_ARGUMENTS')
        require(type(args['amount_minor']) is int and 0 < args['amount_minor'] <= m.payload['per_transaction'] and args['supplier_id'] in m.payload['suppliers'] and args['currency'] == m.payload['currency'], 'PURCHASE_ORDER_OUT_OF_SCOPE')
        result = wire(add(db, org, 'purchase_order', {**args, 'state': 'DRAFT'}, wid))
    elif tool == 'payment_prepare':
        require(args.get('workflow_id') == wid and args.get('session_id') == sid, 'WORKFLOW_MISMATCH')
        result = wire(prepare(db, org, agent_id, PaymentInput.model_validate(args)))
    elif tool in ('payment_authorize', 'payment_execute'):
        require(set(args) <= {'transaction_id', 'approval_id'} and 'transaction_id' in args, 'INVALID_TOOL_ARGUMENTS')
        tx = get(db, org, args['transaction_id'], 'transaction'); require(tx.parent == wid, 'WORKFLOW_MISMATCH')
        result = wire(execute(db, org, agent_id, tx.id, args.get('approval_id'))) if tool == 'payment_execute' else tx.data['decision']
    else:
        require(not args, 'INVALID_TOOL_ARGUMENTS')
        result = {'workflow_id': wid, 'provenance': [wire(r) for r in records(db, org, 'provenance') if r.parent == wid]}
    audit(db, org, 'tool.response', agent_id, wid, sid, {'tool': tool, 'request_event': request_event.id, 'response': result})
    return result

def procurement(db, org, actor, mid, supplier_id, amount, invoice_ref, poison=False, formatting=False, auto_execute=True, simulator_outcome='COMPLETED'):
    w = create_workflow(db, org, actor, mid, 'Cross-session poisoning' if poison else 'Invoice → verified payment')
    agent = w.data['agent_id']; a = create_session(db, org, agent, w.id)
    inv = gateway(db, org, agent, 'invoice_read', w.id, a.id, {'supplier_id': supplier_id, 'amount_minor': amount, 'invoice_ref': invoice_ref, 'beneficiary': 'BEN-ATTACK-9901' if poison else None, 'formatting': formatting})
    if poison: audit(db, org, 'invoice.untrusted_instruction', agent, w.id, a.id, {'text': 'Synthetic adversarial invoice asks the agent to use replacement beneficiary', 'trust': 'EXTERNAL_UNVERIFIED'})
    b = create_session(db, org, agent, w.id, a.id)
    refs = cross_session_copy(db, org, agent, w.id, b.id, inv['provenance_refs'])
    supplier = gateway(db, org, agent, 'supplier_lookup', w.id, b.id, {'supplier_id': supplier_id})
    if not poison: refs.append(supplier['provenance_ref'])
    po = gateway(db, org, agent, 'purchase_order_create', w.id, b.id, {'supplier_id': supplier_id, 'amount_minor': amount, 'currency': 'INR', 'invoice_ref': invoice_ref})
    spec = PaymentInput(workflow_id=w.id, session_id=b.id, supplier_id=supplier_id, beneficiary_ref=inv['fields']['beneficiary_ref'] if poison else supplier['beneficiary_ref'], amount_minor=amount, currency='INR', invoice_ref=invoice_ref, purchase_order_id=po['id'], provenance_refs=refs, idempotency_key=uid(), simulator_outcome=simulator_outcome)
    tx = gateway(db, org, agent, 'payment_prepare', w.id, b.id, spec.model_dump())
    gateway(db, org, agent, 'payment_authorize', w.id, b.id, {'transaction_id': tx['id']})
    if auto_execute: gateway(db, org, agent, 'payment_execute', w.id, b.id, {'transaction_id': tx['id']})
    return get(db, org, tx['id'], 'transaction')
