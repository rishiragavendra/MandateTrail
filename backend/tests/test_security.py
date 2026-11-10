import os
from uuid import uuid4
import pytest
from sqlalchemy import select, text
from app.db import SessionLocal, Mandate, Record, Approval, Audit, Organization, Reservation, User
from app import core as c
from app.crypto import canonical, digest, sign, verify
from app.lab import SCENARIOS

def fresh(client, amount=48000, poison=False, execute=True):
    m = next(m for m in client.get('/api/v1/mandates').json() if m['status']=='ACTIVE')
    s = client.get('/api/v1/suppliers').json()[0]
    if execute:
        r = client.post('/api/v1/procurement/run',json={'mandate_id':m['id'],'supplier_id':s['id'],'amount_minor':amount,'invoice_ref':'TEST-'+str(uuid4()),'poison':poison})
        assert r.status_code == 200, r.text
        return r.json()
    with SessionLocal() as db:
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        t = c.procurement(db,c.ORG,'test-harness',m['id'],s['id'],amount,'TEST-'+str(uuid4()),poison,auto_execute=False)
        result=c.wire(t); db.commit(); return result

def test_canonicalization_and_signature():
    assert canonical({'b':2,'a':'e\u0301'})==canonical({'a':'é','b':2})
    with pytest.raises(ValueError): canonical({'amount':1.25})
    value={'amount':100,'version':1}; sig=sign(value)
    assert verify(value,sig)
    assert not verify({**value,'amount':101},sig)

def test_auth_and_csrf(client):
    client.cookies.clear(); client.headers.pop('X-CSRF-Token',None)
    assert client.get('/api/v1/agents').status_code==401
    assert client.post('/api/v1/auth/login',json={'email':'admin@mandatetrail.local','password':'wrong'}).status_code==401
    r=client.post('/api/v1/auth/login',json={'email':'auditor@mandatetrail.local','password':os.environ['DEMO_PASSWORD']})
    assert r.status_code==200
    assert client.post('/api/v1/agents',json={'name':'forbidden'}).status_code==403
    client.headers['X-CSRF-Token']=r.json()['csrf']
    assert client.post('/api/v1/agents',json={'name':'forbidden'}).status_code==403

def test_valid_payment_and_idempotency(admin):
    t=fresh(admin)
    assert t['outcome']=='COMPLETED'
    again=admin.post('/api/v1/executions',json={'transaction_id':t['id']}).json()
    assert again['receipt_id']==t['receipt_id']
    with SessionLocal() as db:
        assert len(list(db.scalars(select(Reservation).where(Reservation.transaction_id==t['id']))))==1

def test_cross_session_poison_never_promoted(admin):
    t=fresh(admin,poison=True)
    assert t['outcome']=='BLOCKED'
    assert 'SOURCE_EXTERNAL_UNVERIFIED' in t['decision']['reason_codes']
    assert 'BENEFICIARY_NOT_MATCHED' in t['decision']['reason_codes']
    graph=admin.get('/api/v1/provenance/'+t['parent']).json()
    copied=[n for n in graph['nodes'] if n['type']=='session_retrieval']
    assert copied and all(n['trust']=='EXTERNAL_UNVERIFIED' for n in copied)
    sessions=admin.get('/api/v1/workflows/'+t['parent']).json()['sessions']
    assert len(sessions)==2 and any(s['parent_session_id'] for s in sessions)

def test_approval_exact_payload_and_consumption(admin):
    t=fresh(admin,amount=125000)
    assert t['outcome']=='AWAITING_APPROVAL'
    a=next(a for a in admin.get('/api/v1/approvals').json() if a['transaction_id']==t['id'])
    signed=admin.post('/api/v1/approvals/'+a['id']+'/sign',json={})
    assert signed.status_code==200,signed.text
    done=admin.post('/api/v1/executions',json={'transaction_id':t['id'],'approval_id':a['id']})
    assert done.json()['outcome']=='COMPLETED',done.text
    assert admin.post('/api/v1/approvals/'+a['id']+'/sign',json={}).status_code==400

def test_payload_tamper_blocked(admin):
    t=fresh(admin,amount=125000,execute=False)
    a=next(a for a in admin.get('/api/v1/approvals').json() if a['transaction_id']==t['id'])
    assert admin.post('/api/v1/approvals/'+a['id']+'/sign',json={}).status_code==200
    with SessionLocal() as db:
        r=db.get(Record,t['id']); r.data={**r.data,'payload':{**r.data['payload'],'amount_minor':126000}}; db.commit()
    r=admin.post('/api/v1/executions',json={'transaction_id':t['id'],'approval_id':a['id']}).json()
    assert r['outcome']=='BLOCKED' and 'PAYLOAD_DIGEST_MISMATCH' in r['decision']['reason_codes']

def test_forged_approver_identity_rejected(admin):
    """A signed approval attributed to a role that may not approve must not execute."""
    t = fresh(admin, amount=125000, execute=False)
    a = next(x for x in admin.get('/api/v1/approvals').json() if x['transaction_id'] == t['id'])
    with SessionLocal() as db:
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        ap = db.get(Approval, a['id'])
        auditor = db.scalar(select(User).where(User.email == 'auditor@mandatetrail.local'))
        # Attacker holds the signing key and database write access.
        ap.approver, ap.approver_role, ap.status = auditor.id, auditor.role, 'SIGNED'
        ap.signature = sign(c.approval_binding(ap), 'approval')
        db.commit()
    result = admin.post('/api/v1/executions', json={'transaction_id': t['id'], 'approval_id': a['id']}).json()
    assert result['outcome'] == 'BLOCKED', result
    assert 'APPROVER_ROLE_NOT_AUTHORIZED' in result['decision']['reason_codes'], result


def test_forged_approver_role_claim_rejected(admin):
    """Claiming a privileged role the user does not hold must not execute either."""
    t = fresh(admin, amount=125000, execute=False)
    a = next(x for x in admin.get('/api/v1/approvals').json() if x['transaction_id'] == t['id'])
    with SessionLocal() as db:
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        ap = db.get(Approval, a['id'])
        auditor = db.scalar(select(User).where(User.email == 'auditor@mandatetrail.local'))
        ap.approver, ap.approver_role, ap.status = auditor.id, 'Administrator', 'SIGNED'
        ap.signature = sign(c.approval_binding(ap), 'approval')
        db.commit()
    result = admin.post('/api/v1/executions', json={'transaction_id': t['id'], 'approval_id': a['id']}).json()
    assert result['outcome'] == 'BLOCKED', result
    assert 'APPROVER_ROLE_NOT_AUTHORIZED' in result['decision']['reason_codes'], result


def test_auditor_cannot_sign_approval(client):
    """The API layer must refuse an unauthorized role at the door as well."""
    client.cookies.clear()
    r = client.post('/api/v1/auth/login', json={'email': 'auditor@mandatetrail.local', 'password': os.environ['DEMO_PASSWORD']})
    client.headers['X-CSRF-Token'] = r.json()['csrf']
    pending = [x for x in client.get('/api/v1/approvals').json() if x['status'] == 'PENDING']
    if pending:
        assert client.post('/api/v1/approvals/' + pending[0]['id'] + '/sign', json={}).status_code == 403


def test_hard_deny_cannot_be_human_approved(admin):
    t=fresh(admin,poison=True)
    assert not any(a['transaction_id']==t['id'] for a in admin.get('/api/v1/approvals').json())
    result=admin.post('/api/v1/executions',json={'transaction_id':t['id'],'user_confirmed':True})
    assert result.status_code==422

def test_dangling_reference_denies_with_a_record(admin):
    """An unresolvable reference must produce a decision and an audit trail, not a 500 or a bare 404."""
    t = fresh(admin, execute=False)
    with SessionLocal() as db:
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        rec = db.get(Record, t['id'])
        p = {**rec.data['payload'], 'purchase_order_id': str(uuid4())}
        rec.data = {**rec.data, 'payload': p, 'digest': digest(p)}
        db.commit()
    decision = admin.post('/api/v1/policy/evaluate', json={'transaction_id': t['id']})
    assert decision.status_code == 200, decision.text
    assert decision.json()['outcome'] == 'DENY', decision.text
    assert 'REFERENCE_NOT_RESOLVABLE' in decision.json()['reason_codes']
    assert decision.json()['execution_permitted'] is False
    result = admin.post('/api/v1/executions', json={'transaction_id': t['id']}).json()
    assert result['outcome'] == 'BLOCKED', result
    assert 'REFERENCE_NOT_RESOLVABLE' in result['decision']['reason_codes'], result
    events = admin.get('/api/v1/workflows/' + t['parent']).json()['events']
    assert any(e['type'] == 'execution.blocked' for e in events), 'denial left no audit trail'


def test_malformed_payload_denies(admin):
    """A payload missing a critical field denies rather than raising."""
    t = fresh(admin, execute=False)
    with SessionLocal() as db:
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        rec = db.get(Record, t['id'])
        p = {k: v for k, v in rec.data['payload'].items() if k != 'beneficiary_ref'}
        rec.data = {**rec.data, 'payload': p, 'digest': digest(p)}
        db.commit()
    decision = admin.post('/api/v1/policy/evaluate', json={'transaction_id': t['id']})
    assert decision.status_code == 200, decision.text
    assert decision.json()['outcome'] == 'DENY'
    assert 'MALFORMED_ACTION_PAYLOAD' in decision.json()['reason_codes']


def test_a_mandate_key_signature_is_not_an_approval(admin):
    """Keys are separated by purpose, so one stolen key cannot forge every artifact."""
    t = fresh(admin, amount=125000, execute=False)
    a = next(x for x in admin.get('/api/v1/approvals').json() if x['transaction_id'] == t['id'])
    with SessionLocal() as db:
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        ap = db.get(Approval, a['id'])
        owner = db.scalar(select(User).where(User.email == 'owner@mandatetrail.local'))
        ap.approver, ap.approver_role, ap.status = owner.id, owner.role, 'SIGNED'
        # Correct binding, correct role, but signed with the MANDATE key.
        ap.signature = sign(c.approval_binding(ap), 'mandate')
        db.commit()
    result = admin.post('/api/v1/executions', json={'transaction_id': t['id'], 'approval_id': a['id']}).json()
    assert result['outcome'] == 'BLOCKED', result
    assert 'INVALID_OR_CONSUMED_APPROVAL' in result['decision']['reason_codes'], result


def test_audit_heads_are_anchored_outside_the_database(admin):
    """The chain alone proves consistency; anchors prove history was not replaced."""
    first = admin.post('/api/v1/audit/verify', json={}).json()
    assert first['valid'] is True
    assert set(first['signing_keys']) == {'mandate', 'approval', 'audit'}
    assert len({first['signing_keys'][k] for k in first['signing_keys']}) == 3, 'keys must differ'
    anchors = c.read_anchors(c.ORG)
    assert anchors, 'verification should record an anchor'
    assert anchors[-1]['head'] == first['head_hash']
    again = admin.post('/api/v1/audit/verify', json={}).json()
    assert again['anchor_state'] == 'ANCHORS_CONSISTENT'


def test_anchor_detects_history_that_no_longer_contains_it(admin):
    """A head anchored earlier that is absent from the chain means a rewrite."""
    admin.post('/api/v1/audit/verify', json={})
    c.append_anchor(c.ORG, 'f' * 64, 999)
    result = admin.post('/api/v1/audit/verify', json={}).json()
    assert result['valid'] is False, result
    assert result['anchor_state'] == 'ANCHOR_NOT_IN_CHAIN'
    assert result['orphaned_anchors'] == ['f' * 16]
    # Remove the planted anchor so later tests see a clean ledger.
    path = c.anchor_file()
    kept = [l for l in path.read_text(encoding='utf-8').splitlines() if '"' + 'f' * 64 + '"' not in l]
    path.write_text('\n'.join(kept) + '\n', encoding='utf-8')
    assert admin.post('/api/v1/audit/verify', json={}).json()['valid'] is True


def test_revoked_mandate_denies(admin):
    t=fresh(admin,execute=False)
    with SessionLocal() as db:
        m=db.get(Mandate,t['payload']['mandate_id']); m.status='REVOKED'; db.commit()
    result=admin.post('/api/v1/executions',json={'transaction_id':t['id']}).json()
    assert result['outcome']=='BLOCKED'
    with SessionLocal() as db:
        m=db.get(Mandate,t['payload']['mandate_id']); m.status='ACTIVE'; db.commit()

def test_signature_tampering_and_expiry(admin):
    t=fresh(admin,execute=False)
    with SessionLocal() as db:
        m=db.get(Mandate,t['payload']['mandate_id']); original=m.signature; m.signature='tampered';db.commit()
    result=admin.post('/api/v1/executions',json={'transaction_id':t['id']}).json()
    assert result['outcome']=='BLOCKED'
    with SessionLocal() as db:
        m=db.get(Mandate,t['payload']['mandate_id']);m.signature=original;db.commit()
    with SessionLocal() as db:
        tx=db.get(Record,t['id']);p={**tx.data['payload'],'expires':'2000-01-01T00:00:00+00:00'};tx.data={**tx.data,'payload':p,'digest':digest(p)};db.commit()
    result=admin.post('/api/v1/executions',json={'transaction_id':t['id']}).json()
    assert 'TRANSACTION_EXPIRED' in result['decision']['reason_codes']

def login_as(client, email):
    """Swap the session to another demo user and return the client."""
    client.cookies.clear()
    r = client.post('/api/v1/auth/login', json={'email': email, 'password': os.environ['DEMO_PASSWORD']})
    assert r.status_code == 200, r.text
    client.headers['X-CSRF-Token'] = r.json()['csrf']
    return client


def test_beneficiary_change_requires_two_people_and_verification(client):
    """Propose, verify out of band, approve -- each by a different person."""
    admin = login_as(client, 'admin@mandatetrail.local')
    supplier = admin.get('/api/v1/suppliers').json()[-1]
    original = supplier['beneficiary_ref']

    operator = login_as(client, 'operator@mandatetrail.local')
    change = operator.post('/api/v1/beneficiary-changes', json={
        'supplier_id': supplier['id'], 'new_beneficiary_ref': 'BEN-NEWBANK-7788',
        'reason': 'Supplier migrated to a new bank'})
    assert change.status_code == 200, change.text
    cid = change.json()['id']
    assert change.json()['status'] == 'PROPOSED'

    # Unverified changes cannot be applied.
    admin = login_as(client, 'admin@mandatetrail.local')
    assert admin.post('/api/v1/beneficiary-changes/' + cid + '/approve', json={}).status_code == 400
    assert admin.get('/api/v1/suppliers').json()[-1]['beneficiary_ref'] == original

    analyst = login_as(client, 'analyst@mandatetrail.local')
    verified = analyst.post('/api/v1/beneficiary-changes/' + cid + '/verify',
                            json={'method': 'PHONE_CALLBACK', 'reference': 'Called known contact on file'})
    assert verified.status_code == 200, verified.text
    assert verified.json()['status'] == 'VERIFIED'

    admin = login_as(client, 'admin@mandatetrail.local')
    applied = admin.post('/api/v1/beneficiary-changes/' + cid + '/approve', json={})
    assert applied.status_code == 200, applied.text
    assert applied.json()['status'] == 'APPLIED'
    assert applied.json()['signature']
    assert admin.get('/api/v1/suppliers').json()[-1]['beneficiary_ref'] == 'BEN-NEWBANK-7788'
    events = [e['type'] for e in admin.get('/api/v1/audit').json()]
    assert 'supplier.beneficiary_changed' in events


def test_proposer_cannot_approve_own_beneficiary_change(client):
    """Segregation of duties: the proposer is never the sole approver."""
    admin = login_as(client, 'admin@mandatetrail.local')
    supplier = admin.get('/api/v1/suppliers').json()[0]
    change = admin.post('/api/v1/beneficiary-changes', json={
        'supplier_id': supplier['id'], 'new_beneficiary_ref': 'BEN-SELFSERVE-4242',
        'reason': 'Attempting a single-handed change'}).json()
    cid = change['id']
    # The proposer may not even verify their own proposal.
    assert admin.post('/api/v1/beneficiary-changes/' + cid + '/verify',
                      json={'method': 'IN_PERSON', 'reference': 'self'}).status_code == 403
    analyst = login_as(client, 'analyst@mandatetrail.local')
    assert analyst.post('/api/v1/beneficiary-changes/' + cid + '/verify',
                        json={'method': 'IN_PERSON', 'reference': 'met at office'}).status_code == 200
    admin = login_as(client, 'admin@mandatetrail.local')
    denied = admin.post('/api/v1/beneficiary-changes/' + cid + '/approve', json={})
    assert denied.status_code == 403, denied.text
    assert denied.json()['error'] == 'SEGREGATION_OF_DUTIES_REQUIRED'
    assert admin.get('/api/v1/suppliers').json()[0]['beneficiary_ref'] != 'BEN-SELFSERVE-4242'
    owner = login_as(client, 'owner@mandatetrail.local')
    assert owner.post('/api/v1/beneficiary-changes/' + cid + '/reject',
                      json={'reason': 'not needed'}).status_code == 200
    login_as(client, 'admin@mandatetrail.local')


def test_agent_has_no_beneficiary_change_capability(admin):
    """No MCP tool reaches the change path; the hard deny still stands for agents."""
    from app.schemas import TOOLS
    assert not [t for t in TOOLS if 'beneficiary' in t or 'supplier_update' in t]
    t = fresh(admin, poison=True)
    assert t['outcome'] == 'BLOCKED'
    assert 'SOURCE_EXTERNAL_UNVERIFIED' in t['decision']['reason_codes']


def test_login_rate_limited_then_cleared(client):
    """Repeated failures throttle the account; a correct password clears the counter."""
    client.cookies.clear()
    email = 'operator@mandatetrail.local'
    for _ in range(5):
        assert client.post('/api/v1/auth/login', json={'email': email, 'password': 'wrong'}).status_code == 401
    blocked = client.post('/api/v1/auth/login', json={'email': email, 'password': 'wrong'})
    assert blocked.status_code == 429, blocked.text
    assert blocked.json()['error'] == 'TOO_MANY_ATTEMPTS'
    # Even the correct password is refused while the account is throttled.
    assert client.post('/api/v1/auth/login', json={'email': email, 'password': os.environ['DEMO_PASSWORD']}).status_code == 429
    with SessionLocal() as db:
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        for r in c.records(db, c.ORG, 'login_failure'):
            if r.data.get('email') == email: db.delete(r)
        db.commit()
    assert client.post('/api/v1/auth/login', json={'email': email, 'password': os.environ['DEMO_PASSWORD']}).status_code == 200
    login_as(client, 'admin@mandatetrail.local')


def test_workflow_follows_mandate_version_chain(admin):
    """Versioning a mandate must not strand new work on the superseded authority."""
    original = admin.post('/api/v1/mandates', json={
        'name': 'Version chain mandate',
        'agent_id': admin.get('/api/v1/agents').json()[0]['id'],
        'suppliers': [admin.get('/api/v1/suppliers').json()[0]['id']]}).json()
    w = admin.post('/api/v1/workflows', json={'mandate_id': original['id'], 'title': 'before versioning'}).json()
    new = admin.post('/api/v1/mandates/' + original['id'] + '/version', json={}).json()
    assert new['version'] == 2 and new['spent'] == original['spent']
    assert admin.get('/api/v1/mandates/' + original['id']).json()['status'] == 'SUPERSEDED'
    # A workflow created against the superseded id binds to the live successor.
    later = admin.post('/api/v1/workflows', json={'mandate_id': original['id'], 'title': 'after versioning'}).json()
    assert later['mandate_id'] == new['id'], later
    # The pre-existing workflow resolves forward too, so new proposals in it still evaluate.
    assert admin.get('/api/v1/workflows/' + w['id']).json()['mandate_id'] == original['id']
    session = admin.post('/api/v1/workflows/' + w['id'] + '/sessions', json={}).json()
    assert session['id']


def test_evidence_export_uses_the_redaction_helper(admin):
    """Redaction must come from safe_record, not from luck about which records have parents."""
    import inspect
    from app import main
    source = inspect.getsource(main.evidence)
    assert 'safe_record(r)' in source, 'evidence export must redact via safe_record'
    w = admin.get('/api/v1/workflows').json()[0]
    assert 'token_hash' not in admin.get('/api/v1/evidence/' + w['id']).text


def test_tenant_isolation(admin):
    with SessionLocal() as db:
        org=Organization(id='other-'+str(uuid4()),name='Other tenant');db.add(org);db.flush()
        r=c.add(db,org.id,'agent',{'name':'isolated'});rid=r.id;db.commit()
    assert admin.get('/api/v1/agents/'+rid).status_code==404

def test_unknown_tool_denied_and_logged(admin):
    a=admin.post('/api/v1/agents',json={'name':'MCP test agent'}).json()
    supplier=admin.get('/api/v1/suppliers').json()[0]
    m=admin.post('/api/v1/mandates',json={'name':'MCP test mandate','agent_id':a['id'],'suppliers':[supplier['id']]}).json()
    w=admin.post('/api/v1/workflows',json={'mandate_id':m['id']}).json()
    session=admin.post('/api/v1/workflows/'+w['id']+'/sessions',json={}).json()
    request={'tool':'transfer_money_directly','workflow_id':w['id'],'session_id':session['id'],'arguments':{}}
    result=admin.post('/api/v1/gateway/call',headers={'Authorization':'Bearer '+a['token_once']},json=request)
    assert result.status_code==403,result.text
    events=admin.get('/api/v1/workflows/'+w['id']).json()['events']
    assert any(e['type']=='tool.denied' for e in events)
    request['tool']='supplier_lookup';request['arguments']={'supplier_id':supplier['id']}
    assert admin.post('/api/v1/gateway/call',headers={'Authorization':'Bearer '+a['token_once']},json=request).status_code==200

@pytest.mark.parametrize('scenario,name,attack',SCENARIOS)
def test_redteam_scenarios(admin,scenario,name,attack):
    response=admin.post('/api/v1/redteam/runs',json={'scenario':scenario})
    assert response.status_code==200,response.text
    results={r['environment']:r for r in response.json()['results']}
    if attack:
        assert not results['protected']['attack_success'],results['protected']
        assert results['protected']['detected'],results['protected']
        assert results['baseline']['attack_success'],results['baseline']
    else: assert results['protected']['completed'],results['protected']

def test_evidence_export_and_hash_chain(admin):
    result=admin.post('/api/v1/audit/verify',json={})
    assert result.status_code==200 and result.json()['valid'],result.text
    w=admin.get('/api/v1/workflows').json()[0]
    ev=admin.get('/api/v1/evidence/'+w['id'])
    assert ev.status_code==200 and ev.json()['integrity']['valid']
    assert 'token_hash' not in ev.text and 'signing.key' not in ev.text
    with SessionLocal() as db:
        with pytest.raises(Exception):
            db.execute(text("UPDATE audit_events SET digest='tampered' WHERE seq=1"));db.commit()
        db.rollback()
        event=db.scalar(select(Audit).where(Audit.org==c.ORG))
        mutated={**event.content,'type':'altered'}
        assert digest({'content':mutated,'previous':event.previous})!=event.digest

def test_metrics_raw_denominators(admin):
    result=admin.get('/api/v1/redteam/metrics').json()
    assert result['protected']['attack_success_rate']['denominator']>=10
    assert result['protected']['attack_success_rate']['numerator']==0
    assert result['protected']['benign_completion_rate']['numerator']>=7

def test_trial_evidence_scoped_to_owned_run(admin):
    r=admin.get('/api/v1/redteam/runs').json()[0]
    evidence=admin.get('/api/v1/redteam/runs/'+r['id']+'/evidence?environment=protected')
    assert evidence.status_code==200,evidence.text
    data=evidence.json()
    assert data['events'] and data['records'] and data['integrity']['valid']
    assert 'token_hash' not in evidence.text
    assert admin.get('/api/v1/redteam/runs/'+str(uuid4())+'/evidence?environment=protected').status_code==404

@pytest.mark.parametrize('outcome',['FAILED','TIMED_OUT','OUTCOME_UNKNOWN'])
def test_simulator_outcomes_and_safe_retrieval(admin,outcome):
    m=next(m for m in admin.get('/api/v1/mandates').json() if m['status']=='ACTIVE')
    supplier=admin.get('/api/v1/suppliers').json()[0]
    response=admin.post('/api/v1/procurement/run',json={'mandate_id':m['id'],'supplier_id':supplier['id'],'amount_minor':1200,'invoice_ref':'OUTCOME-'+str(uuid4()),'simulator_outcome':outcome})
    assert response.status_code==200,response.text
    tx=response.json()
    assert tx['outcome']==outcome
    retry=admin.post('/api/v1/executions',json={'transaction_id':tx['id']}).json()
    assert retry['receipt_id']==tx['receipt_id'] and retry['outcome']==outcome


# --- Provenance edge enforcement (revision 0003) -----------------------------

def test_dangling_provenance_edge_rejected_by_database(admin):
    """A chain pointer to a nonexistent record must fail at write time, not mid-decision."""
    from sqlalchemy.exc import IntegrityError
    with SessionLocal() as db:
        org = db.scalars(select(Organization)).first().id
        db.add(Record(id=c.uid(), org=org, kind='provenance', data={}, prior_ref='no-such-record'))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

def test_provenance_verify_passes_on_real_workflow(admin):
    """Every edge written by a genuine run resolves, in-org, to the right kind of record."""
    fresh(admin, poison=True)
    report = admin.post('/api/v1/provenance/verify', json={}).json()
    assert report['valid'] is True, report['failures']
    assert report['provenance_records'] > 0
    assert report['edges_enforced'] > 0
    assert report['failures'] == []

def test_provenance_verify_catches_what_foreign_keys_cannot(admin):
    """A same-table reference a foreign key accepts but provenance semantics reject."""
    fresh(admin)
    with SessionLocal() as db:
        org = db.scalars(select(Organization)).first().id
        target = db.scalars(select(Record).where(Record.org == org, Record.kind == 'provenance')).first()
        workflow = db.scalars(select(Record).where(Record.org == org, Record.kind == 'workflow')).first()
        target.source_ref = workflow.id                                  # valid records.id: FK satisfied
        target.data = {**target.data, 'source_id': workflow.id}
        db.flush()
        report = c.provenance_verify(db, org)
        assert report['valid'] is False
        assert 'WRONG_RECORD_KIND' in {f['issue'] for f in report['failures']}, report['failures']
        db.rollback()

def test_diverged_edge_denies_instead_of_resolving_silently(admin):
    """If the enforced column and the JSON disagree, the read fails closed."""
    fresh(admin)
    with SessionLocal() as db:
        org = db.scalars(select(Organization)).first().id
        target = db.scalars(select(Record).where(
            Record.org == org, Record.kind == 'provenance', Record.source_ref.isnot(None))).first()
        other = [r for r in db.scalars(select(Record).where(Record.org == org, Record.kind == 'source'))
                 if r.id != target.source_ref][0]
        target.data = {**target.data, 'source_id': other.id}             # column still points elsewhere
        db.flush()
        with pytest.raises(c.DomainError) as err:
            c.edge(target, 'source_ref', 'source_id')
        assert err.value.code == 'PROVENANCE_EDGE_DIVERGED'
        report = c.provenance_verify(db, org)
        assert report['valid'] is False
        assert 'COLUMN_JSON_DIVERGED' in {f['issue'] for f in report['failures']}
        db.rollback()


# --- Tenant isolation of idempotency keys (revision 0004) --------------------

def _reservation(db, org, mandate_id, key):
    from app.db import Reservation
    return Reservation(id=c.uid(), org=org, mandate_id=mandate_id,
                       transaction_id=c.add(db, org, 'transaction', {}).id,
                       idempotency=key, invoice_key='K:' + c.uid()[:8], amount=1)

def test_tenant_cannot_squat_another_tenants_idempotency_key(admin):
    """A client-supplied key is free-form and guessable. One tenant claiming
    'INV-2026-001' must not block every other tenant from ever using it."""
    from app.db import Organization
    fresh(admin)
    with SessionLocal() as db:
        a = db.scalars(select(Organization)).first().id
        m = db.scalars(select(Mandate).where(Mandate.org == a)).first()
        other = Organization(id=c.uid(), name='Second tenant')
        db.add(other); db.flush()
        m2 = db.scalars(select(Mandate).where(Mandate.org == a)).first()

        db.add(_reservation(db, a, m.id, 'INV-2026-001'))
        db.flush()
        # Same key, different organization: must be accepted.
        r = _reservation(db, other.id, m2.id, 'INV-2026-001')
        r.mandate_id = m.id
        db.add(r)
        db.flush()
        assert True
        db.rollback()

def test_replay_within_one_tenant_still_blocked(admin):
    """Narrowing the constraint must not weaken what it was there to do."""
    from sqlalchemy.exc import IntegrityError
    fresh(admin)
    with SessionLocal() as db:
        org = db.scalars(select(Organization)).first().id
        m = db.scalars(select(Mandate).where(Mandate.org == org)).first()
        db.add(_reservation(db, org, m.id, 'SAME-TENANT-KEY')); db.flush()
        db.add(_reservation(db, org, m.id, 'SAME-TENANT-KEY'))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
