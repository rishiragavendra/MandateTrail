"""Agent harness tests. These use scripted models, so they need no Ollama and no network.

They prove the harness measures the right things: that a manipulated agent is
recorded as manipulated, and that the deterministic controls still refuse the payment.
"""
import json
import os
import re
from uuid import uuid4
import pytest
from app.db import SessionLocal
from app import core as c, agent, injections


def scripted_decision(obedient):
    """A model that either obeys the injected account or pays the registry one."""
    def complete(messages):
        prompt = messages[-1]['content']
        registry = re.search(r'beneficiary_ref: (BEN-[A-Z0-9-]+)', prompt).group(1)
        attacked = injections.ATTACK_BENEFICIARY in prompt
        chosen = injections.ATTACK_BENEFICIARY if (obedient and attacked) else registry
        return json.dumps({'reasoning': 'decided', 'amount_minor': 48000,
                           'invoice_ref': re.search(r'Expected invoice reference: (\S+)', prompt).group(1),
                           'beneficiary_ref': chosen})
    return complete


def scripted(obedient):
    """A model that either obeys an injected instruction or follows its policy."""
    def complete(messages):
        prompt = messages[-1]['content']
        doc_id = re.search(r'document_id is ([0-9a-f-]{36})', prompt).group(1)
        sup_id = re.search(r'supplier_id ([0-9a-f-]{36})', prompt).group(1)
        ref = re.search(r'invoice (AGT-[0-9a-f]+)', prompt).group(1)
        attacked = injections.ATTACK_BENEFICIARY in prompt
        registry = re.search(r'"beneficiary_ref":\s*"(BEN-[A-Z0-9-]+)"', prompt)
        po = re.search(r'purchase_order_create -> \{"id":\s*"([0-9a-f-]{36})"', prompt)
        tx = re.search(r'payment_prepare -> \{"id":\s*"([0-9a-f-]{36})"', prompt)
        def d(tool, **a): return json.dumps({'reasoning': 'step', 'tool': tool, 'arguments': a})
        if 'invoice_document_read ->' not in prompt: return d('invoice_document_read', document_id=doc_id)
        if 'supplier_lookup ->' not in prompt: return d('supplier_lookup', supplier_id=sup_id)
        if 'invoice_read ->' not in prompt:
            args = dict(supplier_id=sup_id, amount_minor=48000, invoice_ref=ref)
            if obedient and attacked: args['beneficiary'] = injections.ATTACK_BENEFICIARY
            return d('invoice_read', **args)
        if 'purchase_order_create ->' not in prompt:
            return d('purchase_order_create', supplier_id=sup_id, amount_minor=48000, currency='INR', invoice_ref=ref)
        if 'payment_prepare ->' not in prompt and po:
            ben = injections.ATTACK_BENEFICIARY if (obedient and attacked) else (registry.group(1) if registry else 'BEN-UNKNOWN')
            return d('payment_prepare', supplier_id=sup_id, beneficiary_ref=ben, amount_minor=48000,
                     currency='INR', invoice_ref=ref, purchase_order_id=po.group(1))
        if 'payment_execute ->' not in prompt and tx:
            return d('payment_execute', transaction_id=tx.group(1))
        return d('finish')
    return complete


@pytest.fixture
def agent_fixture(admin):
    supplier = admin.get('/api/v1/suppliers').json()[0]
    mandate = admin.post('/api/v1/mandates', json={
        'name': 'Agent harness mandate', 'agent_id': admin.get('/api/v1/agents').json()[0]['id'],
        'suppliers': [supplier['id']]}).json()
    return mandate['id'], supplier['id']


def run_agent(mandate_id, supplier_id, level):
    return agent.run(c.ORG, 'harness', mandate_id, supplier_id, level, 'AGT-' + uuid4().hex[:8])


def test_injection_levels_are_graded_and_only_vary_the_text():
    """Every level states the same figures; only attacker-controlled prose differs."""
    docs = [injections.document(l, 'Supplier', 'INV-1', 48000) for l in injections.LEVEL_IDS]
    assert [d['rank'] for d in docs] == sorted(d['rank'] for d in docs)
    assert sum(not d['expects_substitution'] for d in docs) == 1, 'exactly one clean control'
    for d in docs:
        assert 'INV-1' in d['text'] and '480.00' in d['text']
        assert (injections.ATTACK_BENEFICIARY in d['text']) == d['expects_substitution']


def test_autonomous_mode_still_exists(agent_fixture):
    """The free-roaming loop is kept for capability work, even though guided mode is default."""
    assert callable(agent.run_autonomous)


def test_agent_following_policy_completes_and_is_not_recorded_as_complying(agent_fixture, monkeypatch):
    monkeypatch.setattr(agent, 'complete', scripted_decision(False))
    result = run_agent(*agent_fixture, 'L5_instruction_override')
    assert result['agent_complied'] is False
    assert result['consulted_registry'] is True
    assert result['engine_outcome'] == 'COMPLETED'
    assert result['attacker_paid'] is False


def test_manipulated_agent_is_recorded_and_the_payment_is_still_refused(agent_fixture, monkeypatch):
    """The result this project exists to produce: model fully manipulated, attacker unpaid."""
    monkeypatch.setattr(agent, 'complete', scripted_decision(True))
    result = run_agent(*agent_fixture, 'L4_system_framing')
    assert result['agent_complied'] is True, result
    assert result['proposed_beneficiary'] == injections.ATTACK_BENEFICIARY
    assert result['engine_blocked'] is True
    assert result['attacker_paid'] is False
    assert 'SOURCE_EXTERNAL_UNVERIFIED' in result['reason_codes']


def test_clean_document_is_not_scored_as_an_attack(agent_fixture, monkeypatch):
    monkeypatch.setattr(agent, 'complete', scripted_decision(True))
    result = run_agent(*agent_fixture, 'L0_clean')
    assert result['expects_substitution'] is False
    assert result['agent_complied'] is False
    assert result['benign_completed'] is True


def test_every_model_decision_is_audited(agent_fixture, admin, monkeypatch):
    """A manipulated run must be as traceable as a clean one."""
    monkeypatch.setattr(agent, 'complete', scripted_decision(True))
    result = run_agent(*agent_fixture, 'L3_forged_authority')
    events = admin.get('/api/v1/workflows/' + result['workflow_id']).json()['events']
    types = [e['type'] for e in events]
    assert 'agent.run_started' in types and 'agent.decision' in types and 'document.read' in types
    assert 'agent.payment_decision' in types
    choice = next(e for e in events if e['type'] == 'agent.payment_decision')
    assert choice['data']['chosen_beneficiary'] == injections.ATTACK_BENEFICIARY
    assert choice['data']['registry_beneficiary'] != injections.ATTACK_BENEFICIARY


def test_agent_status_reports_unavailable_without_a_model(admin, monkeypatch):
    monkeypatch.setattr(agent, 'OLLAMA_URL', 'http://127.0.0.1:1')
    status = admin.get('/api/v1/agent/status').json()
    assert status['available'] is False and status['reason'] == 'OLLAMA_UNREACHABLE'
    assert len(status['levels']) == len(injections.LEVEL_IDS)
