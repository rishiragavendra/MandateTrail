import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Depends, Request, Response, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from .db import SessionLocal, engine, Organization, User, Record, Mandate, Approval, Reservation, Audit, now, uid
from .crypto import password_hash, password_ok, digest, PUBLIC, KEY_ID
from . import core as c
from . import schemas as s
from . import lab

ADMIN = ('Administrator', 'Finance Owner')
OPERATORS = (*ADMIN, 'Finance Operator')
SECURITY = (*ADMIN, 'Security Analyst')

def seed():
    with SessionLocal() as db:
        if db.get(Organization, c.ORG): return
        password = os.environ.get('DEMO_PASSWORD') or secrets.token_urlsafe(16)
        db.add(Organization(id=c.ORG, name='Orbital Industries · Synthetic Sandbox')); db.flush()
        creds = []
        for email, role in [('admin@mandatetrail.local', 'Administrator'), ('owner@mandatetrail.local', 'Finance Owner'), ('operator@mandatetrail.local', 'Finance Operator'), ('analyst@mandatetrail.local', 'Security Analyst'), ('auditor@mandatetrail.local', 'Auditor')]:
            db.add(User(id=uid(), org=c.ORG, email=email, role=role, password=password_hash(password)))
            creds.append(email + ' | ' + role)
        db.flush(); admin = db.scalar(select(User).where(User.email == 'admin@mandatetrail.local'))
        agent, token = c.create_agent(db, c.ORG, admin.id, s.AgentInput(name='Atlas · Procurement Agent'))
        suppliers = [c.add(db, c.ORG, 'supplier', {'name': name, 'beneficiary_ref': ben, 'account_mask': mask, 'active': True}) for name, ben, mask in [('Northstar Cloud Systems', 'BEN-NORTHSTAR-1042', '•••• 1042'), ('Kepler Office Supply', 'BEN-KEPLER-2088', '•••• 2088'), ('Aster Infrastructure', 'BEN-ASTER-6601', '•••• 6601')]]
        mandate = c.create_mandate(db, c.ORG, admin.id, s.MandateInput(name='Orbital procurement · monthly', agent_id=agent.id, suppliers=[r.id for r in suppliers]))
        c.procurement(db, c.ORG, admin.id, mandate.id, suppliers[0].id, 48000, 'INV-NORTH-001')
        c.procurement(db, c.ORG, admin.id, mandate.id, suppliers[1].id, 24000, 'INV-KEPLER-002', poison=True)
        c.procurement(db, c.ORG, admin.id, mandate.id, suppliers[2].id, 125000, 'INV-ASTER-003')
        db.commit()
        path = Path(os.environ.get('DATA_DIR', 'data')) / 'DEMO_CREDENTIALS.txt'
        path.write_text('LOCAL SYNTHETIC DEMO ONLY\n\n' + '\n'.join(creds) + '\n\nPassword: ' + password + '\n\nInitial agent token: ' + token + '\nKeep this file private. It is generated on first initialization.\n', encoding='utf-8')
        print('Demo credentials written to ' + str(path.resolve()), flush=True)

@asynccontextmanager
async def lifespan(app):
    seed()
    yield

app = FastAPI(title='MandateTrail · Orbital Intelligence', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000'], allow_credentials=True, allow_methods=['GET', 'POST', 'PATCH'], allow_headers=['Content-Type', 'Authorization', 'X-CSRF-Token'])

@app.middleware('http')
async def correlation(request, call_next):
    request.state.correlation = uid()
    response = await call_next(request)
    response.headers['X-Correlation-ID'] = request.state.correlation
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.exception_handler(c.DomainError)
async def domain_error(req, exc): return JSONResponse({'error': exc.code, 'correlation_id': getattr(req.state, 'correlation', None)}, status_code=exc.status)
@app.exception_handler(IntegrityError)
async def conflict(req, exc): return JSONResponse({'error': 'DUPLICATE_OR_REPLAY', 'correlation_id': getattr(req.state, 'correlation', None)}, status_code=409)

def database():
    with SessionLocal() as db:
        try:
            # SQLite has no FOR UPDATE: serialize mutations before reading security state.
            if engine.dialect.name == 'sqlite': db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback(); raise

def identity(request: Request, db=Depends(database)):
    token = request.cookies.get('mt_session')
    auth = db.scalar(select(Record).where(Record.kind == 'auth', Record.data['token_hash'].as_string() == digest(token or '')))
    c.require(auth is not None and not c.expired(auth.data['expires']), 'AUTHENTICATION_REQUIRED', 401)
    user = db.get(User, auth.data['user_id'])
    c.require(user is not None, 'AUTHENTICATION_REQUIRED', 401)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        c.require(secrets.compare_digest(request.headers.get('X-CSRF-Token', ''), auth.data['csrf']), 'CSRF_VALIDATION_FAILED', 403)
    return user

def roles(user, allowed): c.require(user.role in allowed, 'ROLE_NOT_AUTHORIZED', 403)
def safe_record(r):
    data = c.wire(r)
    data.pop('token_hash', None)
    return data
def audit_wire(e): return {**e.content, 'id': e.id, 'previous_hash': e.previous, 'hash': e.digest, 'signature': e.signature}

@app.get('/api/v1/health')
def health(db=Depends(database)):
    db.execute(select(1)); return {'status': 'ready', 'environment': 'SIMULATED', 'database': engine.dialect.name}

@app.post('/api/v1/auth/login')
def login(body: s.Login, response: Response, db=Depends(database)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    c.require(user is not None and password_ok(body.password, user.password), 'INVALID_CREDENTIALS', 401)
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    c.add(db, user.org, 'auth', {'token_hash': digest(token), 'user_id': user.id, 'expires': c.future(480), 'csrf': csrf})
    c.audit(db, user.org, 'auth.login', user.id)
    response.set_cookie('mt_session', token, httponly=True, samesite='strict', secure=os.environ.get('COOKIE_SECURE') == '1', max_age=28800)
    return {'id': user.id, 'email': user.email, 'role': user.role, 'csrf': csrf}

@app.get('/api/v1/auth/me')
def me(request: Request, user=Depends(identity), db=Depends(database)):
    auth = db.scalar(select(Record).where(Record.kind == 'auth', Record.data['token_hash'].as_string() == digest(request.cookies.get('mt_session', ''))))
    return {'id': user.id, 'email': user.email, 'role': user.role, 'csrf': auth.data['csrf']}

@app.post('/api/v1/auth/logout')
def logout(request: Request, response: Response, user=Depends(identity), db=Depends(database)):
    auth = db.scalar(select(Record).where(Record.kind == 'auth', Record.data['token_hash'].as_string() == digest(request.cookies.get('mt_session', ''))))
    auth.data = {**auth.data, 'expires': now()}; response.delete_cookie('mt_session'); return {'ok': True}

@app.get('/api/v1/dashboard')
def dashboard(user=Depends(identity), db=Depends(database)):
    txs = c.records(db, user.org, 'transaction'); decisions = [t.data['decision']['outcome'] for t in txs]
    approvals = list(db.scalars(select(Approval).where(Approval.org == user.org)))
    return {'agents': len(c.records(db, user.org, 'agent')), 'active_workflows': sum(w.data['state'] == 'ACTIVE' for w in c.records(db, user.org, 'workflow')), 'inspected': len(txs), 'decisions': {k: decisions.count(k) for k in ('ALLOW', 'OBSERVE', 'ESCALATE', 'DENY')}, 'pending_approvals': sum(a.status == 'PENDING' and not c.expired(a.expires) for a in approvals), 'critical_alerts': sum(a.data['status'] == 'OPEN' for a in c.records(db, user.org, 'alert')), 'simulated_executions': sum(t.data['outcome'] == 'COMPLETED' for t in txs), 'recent_transactions': [c.wire(t) for t in txs[:8]], 'activity': [audit_wire(e) for e in db.scalars(select(Audit).where(Audit.org == user.org).order_by(Audit.seq.desc()).limit(15))], 'seeded_demo': True}

@app.get('/api/v1/agents')
def agents(user=Depends(identity), db=Depends(database)): return [safe_record(r) for r in c.records(db, user.org, 'agent')]
@app.post('/api/v1/agents')
def register_agent(body: s.AgentInput, user=Depends(identity), db=Depends(database)):
    roles(user, ADMIN); r, token = c.create_agent(db, user.org, user.id, body); return {**safe_record(r), 'token_once': token}
@app.post('/api/v1/agents/{rid}/toggle')
def toggle_agent(rid: str, user=Depends(identity), db=Depends(database)):
    roles(user, ADMIN); r = c.get(db, user.org, rid, 'agent'); r.data = {**r.data, 'active': not r.data['active']}; c.audit(db, user.org, 'agent.status_changed', user.id, data={'agent_id': rid, 'active': r.data['active']}); return safe_record(r)
@app.get('/api/v1/agents/{rid}')
def agent_detail(rid: str, user=Depends(identity), db=Depends(database)):
    r = c.get(db, user.org, rid, 'agent')
    return {**safe_record(r), 'workflows': [c.wire(w) for w in c.records(db, user.org, 'workflow') if w.data['agent_id'] == rid], 'mandates': [c.mandate_wire(m) for m in db.scalars(select(Mandate).where(Mandate.org == user.org)) if m.payload['agent_id'] == rid], 'tool_events': [audit_wire(e) for e in db.scalars(select(Audit).where(Audit.org == user.org).order_by(Audit.seq.desc()).limit(500)) if e.content['actor'] == rid and e.content['type'].startswith('tool.')]}

@app.get('/api/v1/suppliers')
def suppliers(user=Depends(identity), db=Depends(database)): return [c.wire(r) for r in c.records(db, user.org, 'supplier')]
@app.post('/api/v1/suppliers')
def supplier_create(body: s.SupplierInput, user=Depends(identity), db=Depends(database)):
    roles(user, ADMIN); r = c.add(db, user.org, 'supplier', {**body.model_dump(), 'account_mask': '•••• ' + body.beneficiary_ref[-4:], 'active': True}); c.audit(db, user.org, 'supplier.registered', user.id, data={'supplier_id': r.id}); return c.wire(r)

@app.get('/api/v1/mandates')
def mandates(user=Depends(identity), db=Depends(database)): return [c.mandate_wire(m) for m in db.scalars(select(Mandate).where(Mandate.org == user.org).order_by(Mandate.created.desc()))]
@app.post('/api/v1/mandates')
def mandate_create(body: s.MandateInput, user=Depends(identity), db=Depends(database)):
    roles(user, ADMIN); return c.mandate_wire(c.create_mandate(db, user.org, user.id, body))
@app.get('/api/v1/mandates/{mid}')
def mandate_get(mid: str, user=Depends(identity), db=Depends(database)): return c.mandate_wire(c.mandate(db, user.org, mid))
@app.post('/api/v1/mandates/{mid}/verify')
def mandate_verify(mid: str, user=Depends(identity), db=Depends(database)):
    m = c.mandate(db, user.org, mid); return {'valid': c.valid_mandate(m), 'digest': m.digest, 'public_key': PUBLIC, 'key_id': KEY_ID}
@app.post('/api/v1/mandates/{mid}/{action}')
def mandate_action(mid: str, action: str, user=Depends(identity), db=Depends(database)):
    roles(user, ADMIN); m = c.mandate(db, user.org, mid)
    c.require(action in ('revoke', 'expire', 'version'), 'UNKNOWN_ACTION')
    if action == 'version':
        spec = s.MandateInput(**{k: v for k, v in m.payload.items() if k in s.MandateInput.model_fields})
        m.status = 'SUPERSEDED'
        new = c.create_mandate(db, user.org, user.id, spec, m.payload['version'] + 1, mid)
        # Carry committed spend into the new authority to prevent budget-reset laundering.
        new.spent = m.spent
        return c.mandate_wire(new)
    m.status = 'REVOKED' if action == 'revoke' else 'EXPIRED'
    c.audit(db, user.org, 'mandate.' + action, user.id, data={'mandate_id': mid}); return c.mandate_wire(m)

@app.get('/api/v1/workflows')
def workflows(user=Depends(identity), db=Depends(database)): return [c.wire(r) for r in c.records(db, user.org, 'workflow')]
@app.post('/api/v1/workflows')
def workflow_create(body: s.WorkflowInput, user=Depends(identity), db=Depends(database)):
    roles(user, OPERATORS); return c.wire(c.create_workflow(db, user.org, user.id, body.mandate_id, body.title))
@app.post('/api/v1/workflows/{wid}/sessions')
def session_create(wid: str, user=Depends(identity), db=Depends(database)):
    roles(user, OPERATORS); previous = [r for r in c.records(db, user.org, 'session') if r.parent == wid]; return c.wire(c.create_session(db, user.org, user.id, wid, previous[0].id if previous else None))
@app.get('/api/v1/workflows/{wid}')
def workflow_get(wid: str, user=Depends(identity), db=Depends(database)):
    w = c.get(db, user.org, wid, 'workflow')
    return {**c.wire(w), 'events': [audit_wire(e) for e in db.scalars(select(Audit).where(Audit.org == user.org, Audit.workflow == wid).order_by(Audit.seq))], 'sessions': [c.wire(r) for r in c.records(db, user.org, 'session') if r.parent == wid]}
@app.post('/api/v1/procurement/run')
def procurement_run(body: s.ProcurementInput, user=Depends(identity), db=Depends(database)):
    roles(user, OPERATORS); return c.wire(c.procurement(db, user.org, user.id, body.mandate_id, body.supplier_id, body.amount_minor, body.invoice_ref, body.poison, simulator_outcome=body.simulator_outcome))

@app.get('/api/v1/transactions')
def transactions(q: str = '', status: str = '', agent: str = '', supplier: str = '', workflow: str = '', date: str = '', offset: int = 0, limit: int = 50, user=Depends(identity), db=Depends(database)):
    txs = c.records(db, user.org, 'transaction')
    filtered = [t for t in txs if q.lower() in str(c.wire(t)).lower() and (not status or t.data['outcome'] == status or t.data['decision']['outcome'] == status) and (not agent or t.data['payload']['agent_id'] == agent) and (not supplier or t.data['payload']['supplier_id'] == supplier) and (not workflow or t.parent == workflow) and (not date or t.created.startswith(date))]
    return {'total': len(filtered), 'items': [c.wire(t) for t in filtered[max(0,offset):max(0,offset)+min(max(limit,1),100)]]}
@app.get('/api/v1/transactions/{txid}')
def transaction_detail(txid: str, user=Depends(identity), db=Depends(database)):
    tx = c.get(db, user.org, txid, 'transaction'); return {**c.wire(tx), 'approvals': [approval_wire(a, db) for a in db.scalars(select(Approval).where(Approval.org == user.org, Approval.transaction_id == txid))], 'receipts': [c.wire(r) for r in c.records(db, user.org, 'receipt') if r.data['transaction_id'] == txid]}
@app.post('/api/v1/policy/evaluate')
def policy_evaluate(body: s.ExecuteInput, user=Depends(identity), db=Depends(database)):
    tx = c.get(db, user.org, body.transaction_id, 'transaction'); return c.evaluate(db, user.org, tx.data['payload'], db.get(Approval, body.approval_id) if body.approval_id else None, tx.id)
@app.post('/api/v1/executions')
def executions(body: s.ExecuteInput, user=Depends(identity), db=Depends(database)):
    roles(user, OPERATORS); return c.wire(c.execute(db, user.org, user.id, body.transaction_id, body.approval_id))

def approval_wire(a, db):
    tx = c.get(db, a.org, a.transaction_id, 'transaction')
    return {'id': a.id, 'transaction_id': a.transaction_id, 'digest': a.digest, 'nonce': a.nonce, 'expires': a.expires, 'status': 'EXPIRED' if c.expired(a.expires) and a.status in ('PENDING', 'SIGNED') else a.status, 'approver': a.approver, 'signature': a.signature, 'payload': tx.data['payload'], 'policy': tx.data['decision']}
@app.get('/api/v1/approvals')
def approvals(user=Depends(identity), db=Depends(database)): return [approval_wire(a, db) for a in db.scalars(select(Approval).where(Approval.org == user.org))]
@app.post('/api/v1/approvals/{aid}/sign')
def approve(aid: str, user=Depends(identity), db=Depends(database)):
    roles(user, ADMIN); return approval_wire(c.sign_approval(db, user.org, user.id, aid), db)
@app.post('/api/v1/approvals/{aid}/revoke')
def approval_revoke(aid: str, user=Depends(identity), db=Depends(database)):
    roles(user, ADMIN); a = db.get(Approval, aid); c.require(a is not None and a.org == user.org, 'APPROVAL_NOT_FOUND', 404); c.require(a.status in ('SIGNED', 'PENDING'), 'INVALID_OR_CONSUMED_APPROVAL'); a.status = 'REVOKED'; c.audit(db, user.org, 'approval.revoked', user.id, data={'approval_id': aid}); return approval_wire(a, db)

@app.get('/api/v1/provenance/{wid}')
def trace(wid: str, user=Depends(identity), db=Depends(database)):
    c.get(db, user.org, wid, 'workflow')
    prov = [c.wire(r) for r in c.records(db, user.org, 'provenance') if r.parent == wid]
    sources = [c.wire(r) for r in c.records(db, user.org, 'source') if r.parent == wid]
    txs = [c.wire(r) for r in c.records(db, user.org, 'transaction') if r.parent == wid]
    nodes = [{'id': r['id'], 'type': 'source', 'label': r['name'], 'trust': r['trust'], 'meta': r} for r in sources]
    edges = []
    for p in prov:
        nodes.append({'id': p['id'], 'type': p['stage'], 'label': p['field'], 'trust': p['trust'], 'meta': p})
        edges.append({'source': p['parent_provenance'] or p['source_id'], 'target': p['id']})
    for t in txs:
        nodes.append({'id': t['id'], 'type': 'payment', 'label': t['decision']['outcome'] + ' · payment', 'trust': t['decision']['outcome'], 'meta': t})
        edges.extend({'source': p, 'target': t['id']} for p in t['payload']['provenance_refs'])
    return {'nodes': nodes, 'edges': edges}

@app.get('/api/v1/audit')
def audit_list(workflow: str = '', offset: int = 0, user=Depends(identity), db=Depends(database)):
    query = select(Audit).where(Audit.org == user.org)
    if workflow: c.get(db, user.org, workflow, 'workflow'); query = query.where(Audit.workflow == workflow)
    return [audit_wire(e) for e in db.scalars(query.order_by(Audit.seq.desc()).offset(max(offset,0)).limit(100))]
@app.post('/api/v1/audit/verify')
def verify_audit(user=Depends(identity), db=Depends(database)): return c.audit_verify(db, user.org)
@app.get('/api/v1/evidence/{wid}')
def evidence(wid: str, user=Depends(identity), db=Depends(database)):
    w = c.get(db, user.org, wid, 'workflow'); m = c.mandate(db, user.org, w.data['mandate_id'])
    c.audit(db, user.org, 'evidence.exported', user.id, wid)
    return JSONResponse({'environment': 'SYNTHETIC_SANDBOX', 'generated': now(), 'workflow': c.wire(w), 'mandate': c.mandate_wire(m), 'policy_version': c.POLICY_VERSION, 'records': [c.wire(r) for r in db.scalars(select(Record).where(Record.org == user.org, Record.parent == wid))], 'approvals': [approval_wire(a, db) for a in db.scalars(select(Approval).where(Approval.org == user.org)) if c.get(db,user.org,a.transaction_id).parent == wid], 'events': [audit_wire(e) for e in db.scalars(select(Audit).where(Audit.org == user.org, Audit.workflow == wid).order_by(Audit.seq))], 'integrity': c.audit_verify(db, user.org)}, headers={'Content-Disposition': f'attachment; filename="MandateTrail-evidence-{wid}.json"'})

@app.get('/api/v1/alerts')
def alerts(user=Depends(identity), db=Depends(database)): return [c.wire(r) for r in c.records(db, user.org, 'alert')]
@app.post('/api/v1/alerts/{rid}/resolve')
def alert_resolve(rid: str, user=Depends(identity), db=Depends(database)):
    roles(user, SECURITY); r = c.get(db, user.org, rid, 'alert'); r.data = {**r.data, 'status': 'RESOLVED'}; c.audit(db,user.org,'alert.resolved',user.id,data={'alert_id':rid}); return c.wire(r)

@app.get('/api/v1/redteam/scenarios')
def scenarios(user=Depends(identity)): return [{'id': i, 'name': name, 'attack': attack} for i,name,attack in lab.SCENARIOS]
@app.post('/api/v1/redteam/runs')
def lab_run(body: s.LabInput, user=Depends(identity), db=Depends(database)):
    roles(user, SECURITY); return lab.run(db, user.org, user.id, body.scenario, body.environments)
@app.get('/api/v1/redteam/runs')
def lab_runs(user=Depends(identity), db=Depends(database)): return [c.wire(r) for r in c.records(db, user.org, 'lab_run')]
@app.get('/api/v1/redteam/runs/{rid}/evidence')
def trial_evidence(rid: str, environment: str, user=Depends(identity), db=Depends(database)):
    run = c.get(db, user.org, rid)
    c.require(run.kind in ('lab_run','lab_run_archived'), 'RECORD_NOT_FOUND', 404)
    result = next((r for r in run.data['results'] if r['environment'] == environment), None)
    c.require(result is not None, 'ENVIRONMENT_NOT_FOUND', 404)
    org = result.get('experiment_org')
    if not org:
        anchor = db.get(Record, result['workflow_id'])
        c.require(anchor is not None, 'EXPERIMENT_NOT_FOUND', 404)
        org = anchor.org
    events = [audit_wire(e) for e in db.scalars(select(Audit).where(Audit.org == org).order_by(Audit.seq))]
    records = [safe_record(r) for r in db.scalars(select(Record).where(Record.org == org, Record.kind != 'auth'))]
    c.audit(db,user.org,'redteam.evidence_viewed',user.id,data={'run_id':rid,'environment':environment})
    return {'run_id':rid,'configuration':run.data['configuration'],'result':result,'events':events,'records':records,'integrity':c.audit_verify(db,org)}
@app.get('/api/v1/redteam/metrics')
def lab_metrics(user=Depends(identity), db=Depends(database)): return lab.metrics(c.records(db, user.org, 'lab_run'))
@app.post('/api/v1/redteam/reset')
def lab_reset(user=Depends(identity), db=Depends(database)):
    roles(user, SECURITY)
    # Preserve audit and previous evidence; start a clean experiment view.
    for r in c.records(db,user.org,'lab_run'): r.kind = 'lab_run_archived'
    c.audit(db,user.org,'redteam.view_reset',user.id); return {'ok':True,'note':'Prior trial evidence retained; next run creates fresh isolated fixtures.'}

@app.get('/api/v1/settings')
def settings(user=Depends(identity)): return {'environment': 'SIMULATED / SANDBOX', 'policy_version': c.POLICY_VERSION, 'database': engine.dialect.name, 'public_key': PUBLIC, 'key_id': KEY_ID, 'canonicalization': 'NFC UTF-8 sorted JSON; integer money; schema v1', 'roles': list((*OPERATORS,'Security Analyst','Auditor')), 'tools': s.TOOLS, 'limitations': ['Local development authentication; no SSO/MFA', 'Local Ed25519 key custody; no HSM or key rotation', 'No real payment rails or LLM provider', 'Deterministic structured-invoice agent; no OCR', 'External audit checkpointing requires separate infrastructure']}

@app.post('/api/v1/gateway/call')
def gateway_call(body: s.GatewayInput, request: Request, db=Depends(database)):
    auth = request.headers.get('Authorization', '')
    c.require(auth.startswith('Bearer '), 'AGENT_AUTHENTICATION_REQUIRED', 401)
    agent = db.scalar(select(Record).where(Record.kind == 'agent', Record.data['token_hash'].as_string() == digest(auth[7:])))
    c.require(agent is not None, 'AGENT_AUTHENTICATION_REQUIRED', 401)
    try: return c.gateway(db, agent.org, agent.id, body.tool, body.workflow_id, body.session_id, body.arguments)
    except (c.DomainError, ValidationError) as exc:
        code = exc.code if isinstance(exc,c.DomainError) else 'INVALID_TOOL_ARGUMENTS'
        c.audit(db,agent.org,'tool.denied',agent.id,body.workflow_id,body.session_id,{'tool':body.tool,'reason':code}); db.commit()
        raise c.DomainError(code,403)
