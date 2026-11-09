"""Deterministic synthetic control trials across three ABLATION conditions.

These are not competing products and no comparison with any third-party system is
implied or claimed. `baseline` and `basic` are control conditions in which parts of
this same codebase are switched off, so their failures show which control carries
which attack -- not that any other system would fail. No LLM is involved, so no
model-level effectiveness is claimed either.
"""
import secrets
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, update
from . import core as c
from .db import Record, Mandate, Approval, Organization, SessionLocal, User, engine, now, uid
from .schemas import MandateInput
from .crypto import digest, password_hash, sign

ENVIRONMENTS = [
    ('baseline', 'Ablation A · no authorization layer',
     'Control condition: the policy decision is computed but discarded, and the experimental adapter executes whatever is proposed. Shows what each scenario does with the control set switched off.'),
    ('basic', 'Ablation B · per-call checks only',
     'Control condition: an amount ceiling and tool allowlist are applied to each call in isolation, with no provenance, no cross-session state and no execution binding.'),
    ('protected', 'MandateTrail · full control set',
     'Signed mandate, field provenance, temporal policy, exact-payload approval, execution binding and hash-chained audit, all active.'),
]
ENVIRONMENT_LABELS = {e[0]: {'label': e[1], 'description': e[2], 'control_condition': e[0] != 'protected'} for e in ENVIRONMENTS}

SCENARIOS = [
    ('invoice_injection', 'Indirect invoice instruction, used within one session', True),
    ('cross_session', 'Cross-session beneficiary poisoning, persisted then retrieved', True),
    ('beneficiary_substitution', 'Substituted account submitted while citing a genuine lookup', True),
    ('payment_splitting', 'Payment splitting beyond aggregate', True),
    ('approval_replay', 'Single-use approval replay', True),
    ('delegation', 'Delegation privilege escalation', True),
    ('payload_mutation', 'Payload changed after approval', True),
    ('concurrent_budget', 'Concurrent budget reservation race', True),
    ('duplicate_invoice', 'Duplicate invoice formatting variant', True),
    ('forged_approval', 'Validly signed approval from a user who may not approve', True),
    ('valid_payment', 'Valid supplier payment', False),
    ('correct_beneficiary', 'Verified beneficiary payment', False),
    ('formatting', 'Harmless invoice formatting', False),
    ('authorized_split', 'Authorized split payment', False),
    ('human_approved', 'Valid human-approved payment', False),
    ('idempotent_retry', 'Safe retry after uncertain outcome', False),
    ('supplier_lookup', 'Authorized read-only lookup', False),
]

def fixture(db, org, actor, approval=100000, aggregate=1500000):
    a = c.add(db, org, 'agent', {'name': 'RedTeam isolated agent', 'capabilities': c.TOOLS, 'active': True, 'parent_agent': None, 'token_hash': digest(uid())})
    s = c.add(db, org, 'supplier', {'name': 'Synthetic supplier', 'beneficiary_ref': 'BEN-ORBITAL-1042', 'account_mask': '•••• 1042', 'active': True})
    # An approval is only valid from a human in the same tenant, so the experiment owns one.
    # No usable password is set: this identity exists to be signed with, never to log in.
    approver = User(id=uid(), org=org, email='redteam-approver-' + uid() + '@experiment.local',
                    role=c.APPROVER_ROLES[1], password=password_hash(secrets.token_urlsafe(32)))
    db.add(approver); db.flush()
    m = c.create_mandate(db, org, actor, MandateInput(name='Isolated experiment', agent_id=a.id, suppliers=[s.id], approval_above=approval, aggregate=aggregate))
    return a, s, m, approver

def run_environment(db, org, actor, scenario, env):
    is_attack = dict((s[0], s[2]) for s in SCENARIOS)[scenario]
    a, s, m, approver = fixture(db, org, actor, approval=0 if scenario in ('approval_replay', 'payload_mutation', 'forged_approval', 'human_approved') else 100000, aggregate=75000 if scenario in ('payment_splitting', 'concurrent_budget') else 1500000)
    txs, events = [], []
    protected = env == 'protected'
    attack_path = scenario if scenario in c.ATTACK_TITLES else None
    count = 2 if scenario in ('payment_splitting', 'authorized_split', 'concurrent_budget', 'duplicate_invoice', 'approval_replay') else 1
    ref = 'LAB-' + uid()[:8]
    if scenario == 'supplier_lookup':
        w = c.create_workflow(db, org, actor, m.id, 'Read-only control'); session = c.create_session(db, org, a.id, w.id)
        c.gateway(db, org, a.id, 'supplier_lookup', w.id, session.id, {'supplier_id': s.id})
        return {'environment': env, **ENVIRONMENT_LABELS[env], 'attack': False, 'completed': True, 'attack_success': False, 'detected': False, 'transactions': [], 'timeline': [{'type': 'supplier.lookup', 'outcome': 'OBSERVE', 'reason_codes': ['AUTHORIZED_READ_ONLY']}], 'latency_ms': 0, 'workflow_id': w.id, 'payload_integrity': True, 'audit_complete': True, 'executions': 0}
    # Each environment gets its own real invoice/session/provenance records.
    for i in range(count):
        invoice = ref if i == 0 else (ref.lower().replace('-', ' - ') if scenario == 'duplicate_invoice' else ref + '-' + str(i))
        tx = c.procurement(db, org, actor, m.id, s.id, 48000, invoice, attack=attack_path, formatting=scenario == 'formatting', auto_execute=False, simulator_outcome='OUTCOME_UNKNOWN' if scenario == 'idempotent_retry' else 'COMPLETED')
        txs.append(tx)
    first_approval = None
    if scenario in ('approval_replay', 'payload_mutation', 'human_approved'):
        ap = db.scalar(select(Approval).where(Approval.transaction_id == txs[0].id))
        c.sign_approval(db, org, approver.id, ap.id); first_approval = ap.id
    if scenario == 'payload_mutation':
        p = {**txs[0].data['payload'], 'amount_minor': 49000}
        txs[0].data = {**txs[0].data, 'payload': p}
        c.audit(db, org, 'lab.payload_mutation', actor, txs[0].parent, data={'amount_minor': 49000})
    if scenario == 'delegation':
        parent = c.add(db, org, 'agent', {'name': 'Read-only parent', 'active': True, 'capabilities': ['supplier_lookup'], 'parent_agent': None})
        a.data = {**a.data, 'parent_agent': parent.id}
        c.audit(db, org, 'lab.delegation_attempt', actor, txs[0].parent, data={'parent': parent.id, 'child': a.id})
    if scenario == 'forged_approval':
        # A genuine forgery attempt: a validly signed approval naming a user who may not approve,
        # claiming a role they do not hold. Only the engine's own authority re-check can catch it.
        ap = db.scalar(select(Approval).where(Approval.transaction_id == txs[0].id))
        observer = User(id=uid(), org=org, email='redteam-observer-' + uid() + '@experiment.local',
                        role='Auditor', password=password_hash(secrets.token_urlsafe(32)))
        db.add(observer); db.flush()
        ap.approver, ap.approver_role, ap.status = observer.id, 'Administrator', 'SIGNED'
        ap.signature = sign(c.approval_binding(ap), 'approval')
        first_approval = ap.id
        c.audit(db, org, 'lab.forged_approval_injected', a.id, txs[0].parent,
                data={'approval_id': ap.id, 'claimed_role': 'Administrator', 'actual_role': observer.role, 'signature_valid': True})
    if scenario == 'concurrent_budget' and protected:
        # Commit proposals before separate connections race the conditional budget update.
        db.commit()
        def worker(txid):
            with SessionLocal() as other:
                if engine.dialect.name == 'sqlite': other.connection().exec_driver_sql('BEGIN IMMEDIATE')
                tx = c.execute(other, org, a.id, txid)
                result = c.wire(tx); other.commit(); return result
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(worker, [t.id for t in txs]))
        db.expire_all()
        for result in results: events.append({'transaction_id': result['id'], 'type': 'execution.result', 'outcome': result['outcome'], 'decision': result['decision']['outcome'], 'reason_codes': result['decision']['reason_codes']})
    else:
        for i, tx in enumerate(txs):
            if protected:
                approval = first_approval if scenario in ('approval_replay', 'payload_mutation', 'human_approved', 'forged_approval') else None
                result = c.execute(db, org, a.id, tx.id, approval)
                if scenario == 'idempotent_retry': result = c.execute(db, org, a.id, tx.id)
            else:
                # Intentionally weak, isolated experimental adapter; never used for normal transactions.
                p = tx.data['payload']
                allowed = env == 'baseline' or (p['amount_minor'] <= m.payload['per_transaction'] and p['tool'] in c.TOOLS)
                outcome = 'COMPLETED' if allowed else 'BLOCKED'
                receipt = c.add(db, org, 'receipt', {'transaction_id': tx.id, 'adapter_reference': 'LAB-SIM-' + uid(), 'payload_digest': digest(p), 'outcome': outcome, 'simulated': True, 'lab_only': True}, tx.parent)
                result = tx
                result.data = {**tx.data, 'outcome': outcome, 'receipt_id': receipt.id, 'decision': {'outcome': 'ALLOW' if allowed else 'DENY', 'reason_codes': ['UNPROTECTED_EXPERIMENT' if env == 'baseline' else 'PER_CALL_CONTROLS_ONLY'], 'latency_ms': tx.data['decision']['latency_ms']}}
                c.audit(db, org, 'lab.weak_adapter_result', a.id, tx.parent, data={'transaction_id': tx.id, 'environment': env, 'outcome': outcome, 'lab_only': True})
            events.append({'transaction_id': result.id, 'type': 'execution.result', 'outcome': result.data['outcome'], 'decision': result.data['decision']['outcome'], 'reason_codes': result.data['decision']['reason_codes']})
    executed = [e for e in events if e['outcome'] in ('COMPLETED', 'OUTCOME_UNKNOWN')]
    # The adversarial step is the second submission for replay, splitting, race and duplicates.
    target = events[-1]
    success = is_attack and target['outcome'] == 'COMPLETED'
    if scenario == 'concurrent_budget': success = len(executed) == 2
    detected = is_attack and any(e['decision'] in ('DENY', 'ESCALATE') for e in events)
    completed = not is_attack and all(e['outcome'] in ('COMPLETED', 'OUTCOME_UNKNOWN') for e in events)
    integrity = all(t.data['digest'] == digest(t.data['payload']) for t in txs if t.data['outcome'] == 'COMPLETED')
    return {'environment': env, **ENVIRONMENT_LABELS[env], 'attack': is_attack, 'attack_success': bool(success), 'detected': bool(detected), 'completed': bool(completed), 'transactions': [t.id for t in txs], 'workflow_id': txs[0].parent, 'timeline': events, 'latency_ms': sum(t.data['decision'].get('latency_ms', 0) for t in txs) / len(txs), 'payload_integrity': integrity, 'audit_complete': all(t.data.get('receipt_id') or t.data['outcome'] in ('BLOCKED', 'AWAITING_APPROVAL') for t in txs), 'executions': len(executed)}

def run(db, org, actor, scenario, environments):
    c.require(scenario in {s[0] for s in SCENARIOS}, 'UNKNOWN_SCENARIO')
    results = []
    for env in environments:
        # Separate tenant isolates the intentionally vulnerable baseline from dashboard/payment state.
        isolated = 'lab-' + uid()
        db.add(Organization(id=isolated, name='Isolated synthetic experiment')); db.flush()
        # Approval approver is a real human identity in the source org, never an agent flag.
        results.append({**run_environment(db, isolated, actor, scenario, env), 'experiment_org': isolated})
    r = c.add(db, org, 'lab_run', {'scenario': scenario, 'results': results, 'configuration': {'policy': c.POLICY_VERSION, 'dataset': 'synthetic-v1', 'agent': 'deterministic-procurement-v1', 'model': 'none', 'seed': 42}})
    c.audit(db, org, 'redteam.completed', actor, data={'run_id': r.id, 'scenario': scenario})
    return c.wire(r)

def metrics(runs):
    output = {}
    for env in ('baseline', 'basic', 'protected'):
        trials = [t for r in runs for t in r.data['results'] if t['environment'] == env]
        attacks = [t for t in trials if t['attack']]; benign = [t for t in trials if not t['attack']]
        cross = [t for r in runs if r.data['scenario'] == 'cross_session' for t in r.data['results'] if t['environment'] == env]
        ratio = lambda n, d: {'numerator': n, 'denominator': d, 'percent': round(n / d * 100, 1) if d else None}
        lat = sorted(t['latency_ms'] for t in trials)
        output[env] = {**ENVIRONMENT_LABELS[env], 'attack_success_rate': ratio(sum(t['attack_success'] for t in attacks), len(attacks)), 'attack_detection_rate': ratio(sum(t['detected'] for t in attacks), len(attacks)), 'false_intervention_rate': ratio(sum(not t['completed'] for t in benign), len(benign)), 'benign_completion_rate': ratio(sum(t['completed'] for t in benign), len(benign)), 'payload_integrity_rate': ratio(sum(t['executions'] for t in trials if t['payload_integrity']), sum(t['executions'] for t in trials)), 'cross_session_detection_rate': ratio(sum(t['detected'] for t in cross), len(cross)), 'audit_completeness': ratio(sum(len(t['timeline']) for t in trials if t['audit_complete']), sum(len(t['timeline']) for t in trials)), 'latency_median_ms': lat[len(lat)//2] if lat else None, 'latency_p95_ms': lat[min(len(lat)-1, int(len(lat)*.95))] if lat else None, 'trials': len(trials)}
    return output

