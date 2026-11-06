import os
from uuid import uuid4
import pytest
from sqlalchemy import select, text
from app.db import SessionLocal, Mandate, Record, Approval, Audit, Organization, Reservation
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

def test_hard_deny_cannot_be_human_approved(admin):
    t=fresh(admin,poison=True)
    assert not any(a['transaction_id']==t['id'] for a in admin.get('/api/v1/approvals').json())
    result=admin.post('/api/v1/executions',json={'transaction_id':t['id'],'user_confirmed':True})
    assert result.status_code==422

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
