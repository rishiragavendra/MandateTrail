"""Run an explicit larger control evaluation against a running local backend.
python scripts/evaluate.py --output work/evaluation.json
Uses generated demo admin credentials; never prints passwords.
"""
import argparse
import json
from pathlib import Path
import httpx

parser=argparse.ArgumentParser()
parser.add_argument('--api',default='http://127.0.0.1:8000/api/v1')
parser.add_argument('--password-file',default='backend/data/DEMO_CREDENTIALS.txt')
parser.add_argument('--output',default='evaluation.json')
parser.add_argument('--attack-variations',type=int,default=3)
parser.add_argument('--benign-trials',type=int,default=50)
args=parser.parse_args()
password=next(line.partition(': ')[2] for line in Path(args.password_file).read_text(encoding='utf-8').splitlines() if line.startswith('Password: '))
with httpx.Client(base_url=args.api,timeout=120) as client:
    r=client.post('/auth/login',json={'email':'admin@mandatetrail.local','password':password});r.raise_for_status()
    client.headers['X-CSRF-Token']=r.json()['csrf']
    scenarios=client.get('/redteam/scenarios').json()
    attacks=[s for s in scenarios if s['attack']];benign=[s for s in scenarios if not s['attack']]
    runs=[]
    # Variations use fresh IDs, source hashes, nonces and invoice references with fixed amounts.
    for variation in range(args.attack_variations):
        for scenario in attacks:
            result=client.post('/redteam/runs',json={'scenario':scenario['id']});result.raise_for_status();runs.append(result.json())
            print('Attack variation',variation+1,scenario['id'],'recorded')
    for i in range(args.benign_trials):
        scenario=benign[i%len(benign)]
        result=client.post('/redteam/runs',json={'scenario':scenario['id']});result.raise_for_status();runs.append(result.json())
        print('Benign trial',i+1,scenario['id'],'recorded')
    from collections import Counter
    summary={}
    for environment in ('baseline','basic','protected'):
        trials=[t for r in runs for t in r['results'] if t['environment']==environment]
        att=[t for t in trials if t['attack']];ben=[t for t in trials if not t['attack']]
        summary[environment]={'attack_success':[sum(t['attack_success'] for t in att),len(att)],'attack_detection':[sum(t['detected'] for t in att),len(att)],'benign_completion':[sum(t['completed'] for t in ben),len(ben)],'false_intervention':[sum(not t['completed'] for t in ben),len(ben)]}
    report={'configuration':{'agent':'deterministic-v1','LLM':None,'dataset':'synthetic-v1','attack_variations':'fresh IDs/nonces/refs; fixed financial amounts'},'summary':summary,'runs':runs}
    Path(args.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2));print('Saved',args.output)
