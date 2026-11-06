"""Live HTTP integration check. Run from project root after run.bat."""
import json
from pathlib import Path
from uuid import uuid4
import httpx

password_file=Path('backend/data/DEMO_CREDENTIALS.txt')
if not password_file.exists(): password_file=Path('data/DEMO_CREDENTIALS.txt')
password=next(line.partition(': ')[2] for line in password_file.read_text(encoding='utf-8').splitlines() if line.startswith('Password: '))
checks={}
with httpx.Client(base_url='http://localhost:3000/api/v1',timeout=60) as client:
    result=client.post('/auth/login',json={'email':'admin@mandatetrail.local','password':password});result.raise_for_status()
    client.headers['X-CSRF-Token']=result.json()['csrf']
    for path in ['/health','/dashboard','/agents','/mandates','/suppliers','/settings','/transactions','/redteam/scenarios']:
        r=client.get(path);r.raise_for_status();checks[path]='PASS'
    m=next(m for m in client.get('/mandates').json() if m['status']=='ACTIVE')
    supplier=client.get('/suppliers').json()[0]
    for poison,amount in [(False,1200),(True,1200),(False,120000)]:
        r=client.post('/procurement/run',json={'mandate_id':m['id'],'supplier_id':supplier['id'],'amount_minor':amount,'invoice_ref':'SMOKE-'+str(uuid4()),'poison':poison});r.raise_for_status();tx=r.json()
        expected='BLOCKED' if poison else 'AWAITING_APPROVAL' if amount>m['approval_above'] else 'COMPLETED'
        assert tx['outcome']==expected,tx
        checks['poisoned_workflow' if poison else 'approval_workflow' if amount>m['approval_above'] else 'valid_workflow']='PASS'
        if expected=='AWAITING_APPROVAL':
            a=next(a for a in client.get('/approvals').json() if a['transaction_id']==tx['id'])
            client.post('/approvals/'+a['id']+'/sign',json={}).raise_for_status()
            completed=client.post('/executions',json={'transaction_id':tx['id'],'approval_id':a['id']});completed.raise_for_status()
            assert completed.json()['outcome']=='COMPLETED'
            checks['human_sign_and_execute']='PASS'
        graph=client.get('/provenance/'+tx['parent']);graph.raise_for_status();assert graph.json()['edges']
        evidence=client.get('/evidence/'+tx['parent']);evidence.raise_for_status();assert evidence.json()['integrity']['valid']
    checks['provenance_and_evidence']='PASS'
    run=client.post('/redteam/runs',json={'scenario':'cross_session'});run.raise_for_status()
    trial=client.get('/redteam/runs/'+run.json()['id']+'/evidence?environment=protected');trial.raise_for_status()
    assert trial.json()['integrity']['valid'] and trial.json()['events']
    checks['lab_trial_evidence']='PASS'
    assert client.post('/audit/verify',json={}).json()['valid']
    checks['audit_verify']='PASS'
    assert client.post('/auth/logout',json={}).status_code==200
    assert client.get('/dashboard').status_code==401
    checks['logout_invalidates_session']='PASS'
report={'transport':'http://localhost:3000 same-origin proxy to FastAPI','checks':checks,'all_passed':all(v=='PASS' for v in checks.values())}
Path('docs/http-smoke-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
