"""Source-text dependency candidates, without clinical inference or label input.

Edges connect shared diagnostic concepts to explicit interpretation limits or
sampling prerequisites. These are retrieval hints requiring source review, not
inferred medical knowledge or permission to make a treatment decision.
"""
import hashlib
import re
from rag.clinical_scope import applicable

CONCEPTS = {
    'inflammatory_markers': r'\b(?:crp|c[ -]reactive protein|procalcitonin|inflammatory[ -]markers?|biomarkers?)\b',
    'culture': r'\b(?:cultures?|microbiolog\w*)\b',
    'laboratory': r'\b(?:laboratory|laboratories|lab results?|investigations?|blood tests?|blood cell count)\b',
}


def concepts(text):
    return {name for name, pattern in CONCEPTS.items() if re.search(pattern, text, re.I)}


def dependency_kind(text):
    if re.search(r'\b(?:do not|cannot|can not|should not|not sufficient|insufficient)\b', text, re.I):
        return 'interpretation_limit'
    if re.search(r'\b(?:before|prior to)\b.{0,65}\b(?:first dose|antibiotic)', text, re.I):
        return 'sampling_prerequisite'
    if re.search(r'\bbaseline\b', text, re.I) and re.search(r'\bsubsequent\b', text, re.I):
        return 'serial_measurement_context'
    return None


def build_graph(chunks):
    nodes = []
    for c in chunks:
        text = c['raw_text']
        kind = dependency_kind(text)
        matched = concepts(text)
        if kind and matched:
            nodes.append({'chunk_id': c['chunk_id'], 'guideline': c['guideline_id'],
                          'kind': kind, 'concepts': sorted(matched),
                          'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                          'scope': c['scope'], 'clinical_review_status': 'pending'})
    edges = []
    for c in chunks:
        matched = concepts(c['raw_text'])
        for n in nodes:
            shared = matched & set(n['concepts'])
            if c['chunk_id'] != n['chunk_id'] and c['guideline_id'] == n['guideline'] and shared:
                edges.append({'from': c['chunk_id'], 'to': n['chunk_id'],
                              'relation': n['kind'], 'shared_concepts': sorted(shared)})
    return {'schema_version': 1, 'nodes': nodes, 'edges': edges,
            'clinical_review_status': 'pending',
            'semantics': 'Lexical source dependencies; no causality, diagnosis or source approval asserted.'}


def expand_candidates(query, order, corpus, graph, patient, guideline, *, budget=24, dependency_budget=4):
    if not 1 <= budget <= 24 or not 0 <= dependency_budget <= 4:
        raise ValueError('Invalid dependency candidate budget')
    matched = concepts(query)
    if not matched or dependency_budget == 0:
        return list(dict.fromkeys(order))[:budget], []
    linked = {e['to'] for e in graph['edges'] if e['from'] in order and matched & set(e['shared_concepts'])}
    nodes = [n for n in graph['nodes'] if n['chunk_id'] in linked and n['guideline'] == guideline
             and matched & set(n['concepts']) and applicable(n['scope'], patient)]
    # Compact explicit limits and prerequisites precede sprawling paragraphs.
    # This is a candidate-pool intervention, never a final relevance vote.
    priority = {'interpretation_limit': 0, 'sampling_prerequisite': 1, 'serial_measurement_context': 2}
    nodes.sort(key=lambda n: (priority[n['kind']], -len(matched & set(n['concepts'])),
                             len(corpus[n['chunk_id']]['raw_text'].split()), n['chunk_id']))
    additions = []
    for n in nodes:
        cid = n['chunk_id']
        actual = hashlib.sha256(corpus[cid]['raw_text'].encode()).hexdigest()
        if actual != n['text_sha256']:
            raise ValueError('Dependency graph source hash mismatch')
        if cid not in order:
            additions.append(cid)
        if len(additions) == dependency_budget:
            break
    # Preserve the original order of retained candidates; appended nodes are
    # unranked expansion, not promoted clinical recommendations.
    keep = list(dict.fromkeys(order))[:max(0, budget - len(additions))]
    return keep + additions, additions
