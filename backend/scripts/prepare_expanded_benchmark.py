"""Freeze a synthetic, source-checked evaluation without changing production code."""
from __future__ import annotations
import collections
import hashlib
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/research/expanded'
OLD = ROOT / 'output/research/rag_v2'
SEED = 31
FAMILIES = ['deterioration', 'crp_alone', 'incomplete_stop', 'initial_investigation', 'single_risk', 'missing_results']

def sha(value):
    return hashlib.sha256(value).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + '\n', encoding='utf8')

def clean(text):
    return ' '.join(text.replace('\u00ad', '').replace('\u00a0', ' ').split())

def prepare():
    import fitz
    if (OUT / 'manifest.json').exists():
        raise SystemExit('Frozen manifest already exists. Refusing to replace cases or references.')
    rng = random.Random(SEED)
    originals = json.loads((OLD / 'cases.json').read_text())
    nice = json.loads((OLD / 'corpus.json').read_text())
    pdf = ROOT / 'backend/guidelines/aap_management_of_neonates-1-7 (1).pdf'
    doc = fitz.open(pdf)
    aap = []
    for page_no, page in enumerate(doc, 1):
        if page_no == 7:
            continue
        for block_no, block in enumerate(page.get_text('blocks')):
            text = clean(block[4])
            if block[6] != 0 or len(text) < 200 or block[1] > 745:
                continue
            # Paragraph-level chunks retain source qualifiers. These are not
            # represented as numbered recommendations when the article has none.
            aap.append({'chunk_id': f'AAP2018-35PLUS-P{page_no}-B{block_no}', 'text': text,
                        'pdf_page': page_no, 'source': 'AAP 2018 >=35 weeks', 'version': '2018-12',
                        'chunk_type': 'article_paragraph'})
    summary = clean(doc[6].get_text())
    points = list(re.finditer(r'(?:^|\s)([2-6])\.\s', summary))
    assert len(points) == 5, 'AAP summary point extraction failed'
    for i, match in enumerate(points):
        text = summary[match.end():points[i+1].start() if i+1 < len(points) else len(summary)]
        text = re.sub(r'\s+7\s*$', '', text).strip()
        aap.append({'chunk_id': f'AAP2018-35PLUS-SP{match[1]}', 'text': text, 'pdf_page': 7,
                    'source': 'AAP 2018 >=35 weeks', 'version': '2018-12', 'chunk_type': 'summary_recommendation'})
    # Isolate a complete paragraph from a cross-column continuation. No new
    # wording is introduced; containment in the original extracted span is checked.
    p6 = next(c for c in aap if c['chunk_id'] == 'AAP2018-35PLUS-P6-B11')
    start = p6['text'].find('Among term infants')
    assert start >= 0
    paragraph = p6['text'][start:]
    assert paragraph in p6['text']
    aap.append({**p6, 'chunk_id': 'AAP2018-35PLUS-P6-STOP', 'text': paragraph,
                'chunk_type': 'complete_paragraph_span'})
    # Remove the overlapping parent so retrieval does not double-count it.
    aap = [c for c in aap if c['chunk_id'] != 'AAP2018-35PLUS-P6-B11']
    for guideline, chunks, digest in [('NICE', nice['chunks'], nice['pdf_sha256']), ('AAP', aap, sha(pdf.read_bytes()))]:
        for c in chunks:
            c.update({'guideline_id': guideline, 'text_sha256': sha(c['text'].encode()), 'pdf_sha256': digest,
                      'scope': {'gestational_age_weeks': [35, 42] if guideline == 'AAP' else [None, None],
                                'postnatal_age_hours': [0, 72], 'care_setting': ['hospital_birth', 'postnatal_ward', 'neonatal_unit']},
                      'clinical_review_status': 'pending', 'technical_identity_check': 'title_DOI_and_summary_checked' if guideline == 'AAP' else 'frozen_original_corpus'})
    byid = {c['chunk_id']: c for c in nice['chunks'] + aap}
    assert len(byid) == len(nice['chunks']) + len(aap), 'Duplicate corpus IDs'
    nice_gold = {c['family']: c['gold_chunk_ids'] for c in originals}
    aap_gold = {
        'deterioration': ['AAP2018-35PLUS-P4-B5', 'AAP2018-35PLUS-SP2'],
        'crp_alone': ['AAP2018-35PLUS-P6-B2', 'AAP2018-35PLUS-SP4'],
        'incomplete_stop': ['AAP2018-35PLUS-SP6', 'AAP2018-35PLUS-P6-STOP'],
        'initial_investigation': ['AAP2018-35PLUS-P5-B3', 'AAP2018-35PLUS-SP4'],
        'single_risk': ['AAP2018-35PLUS-SP2', 'AAP2018-35PLUS-SP3'],
        'missing_results': ['AAP2018-35PLUS-SP2', 'AAP2018-35PLUS-SP4']}
    added, review = [], []
    for guideline, count in [('NICE', 12), ('AAP', 4)]:
        for family in FAMILIES:
            for n in range(count):
                age = [6, 12, 24, 36][n % 4] if family != 'incomplete_stop' else [48, 54, 60, 71][n % 4]
                ga = rng.choice([35, 36, 37, 38, 40, 41] if guideline == 'AAP' else [28, 32, 35, 36, 37, 40, 41])
                if family in ['single_risk', 'incomplete_stop']:
                    ga = rng.choice([37, 38, 39, 40, 41])
                setting = ['hospital_birth', 'postnatal_ward', 'neonatal_unit'][n % 3]
                p = {'age_hours': age, 'gestational_age_weeks': ga, 'care_setting': setting,
                     'respiratory_rate': 76 if family in ['deterioration', 'incomplete_stop'] else 46,
                     'spo2': 89 if family == 'deterioration' else 97,
                     'crp': 3 + n % 4, 'culture_status': 'negative' if family == 'incomplete_stop' else 'unknown',
                     'maternal_gbs': 'positive' if family == 'single_risk' else 'unknown',
                     'red_flags': 'explicitly absent' if family == 'single_risk' else 'not fully documented'}
                history = [{'age_hours': age/3, 'respiratory_rate': 46, 'spo2': 98, 'crp': 18 + n % 5},
                           {'age_hours': age*2/3, 'respiratory_rate': 62 if family == 'deterioration' else 46,
                            'spo2': 94 if family == 'deterioration' else 98, 'crp': 9 + n % 3}]
                missing = ['spo2', 'crp', 'maternal_gbs', 'respiratory_rate'][n % 4]
                if family not in ['single_risk', 'incomplete_stop', 'deterioration']:
                    p[missing] = None
                if family == 'missing_results':
                    p.update({'maternal_gbs': 'unknown', 'crp': None, 'culture_status': 'unavailable', 'respiratory_rate': None, 'spo2': None})
                    history = history[:1] if n % 2 else []
                if family == 'single_risk':
                    p.update({'other_risk_factors': 'assessed absent', 'clinical_condition': 'well appearing', 'other_clinical_indicators': 'assessed absent'})
                if family == 'incomplete_stop':
                    p.update({'culture_incubation_hours': 36 if n % 2 == 0 else 48,
                              'antibiotic_duration_hours': 36 if n % 2 == 0 else 48,
                              'clinical_condition': 'persistent unexplained critical cardiorespiratory illness' if guideline == 'AAP' else 'persistent respiratory distress',
                              'initial_suspicion': 'strong' if n % 2 else 'not documented', 'site_specific_infection': 'not established'})
                base = next(c for c in originals if c['family'] == family)
                questions = {
                    'deterioration': 'Assess the rising respiratory rate and falling oxygen saturation during serial examinations; explain actions for an infant developing signs of illness.',
                    'crp_alone': 'Can a single or falling CRP result exclude early-onset sepsis or alone determine whether antibiotics stop? Explain the limits of inflammatory markers.',
                    'incomplete_stop': 'Blood culture is sterile after the recorded incubation, but respiratory illness persists. Explain antibiotic review and whether stopping conditions are established.',
                    'initial_investigation': 'Explain appropriate initial diagnostic investigations for suspected early-onset sepsis and the limitations of laboratory tests.',
                    'single_risk': 'A well-appearing infant has one confirmed maternal GBS risk factor. Explain risk stratification, examination and locally documented management options.',
                    'missing_results': 'Maternal history and culture results are unavailable and the latest examination is missing. Explain uncertainty and the assessment needed without assuming normal findings.'}
                query = questions[family] + f' Gestation {ga} weeks; age {age} hours; setting {setting.replace("_", " ")}.'
                if guideline == 'AAP':
                    reference = {
                      'deterioration': 'Serial observations show rising respiratory rate and falling oxygen saturation. Infants developing signs of illness require clinical evaluation; the AAP clinical-condition approach includes empirical treatment or further laboratory evaluation. Risk assessment must incorporate the infant examination and the local documented pathway. A reassuring birth examination does not establish that a currently ill infant is well.',
                      'crp_alone': 'A single CRP or procalcitonin value is neither sufficiently sensitive nor specific to guide EOS care. Inflammatory markers alone do not diagnose EOS; diagnosis uses blood or CSF culture. Serial abnormal markers alone should not determine antibiotic administration without culture-confirmed infection. Do not infer that a falling marker alone permits stopping treatment.',
                      'incomplete_stop': 'AAP guidance recommends discontinuation by 36 to 48 hours of sterile blood-culture incubation unless clear site-specific infection exists. The article also allows that unexplained critical cardiorespiratory illness in a term infant may justify an empirical course without culture-confirmed infection. Persistent critical illness requires clinician reassessment; a negative culture alone cannot be interpreted as automatic permission to stop. Laboratory abnormalities alone rarely justify continued empirical treatment in a well term infant.',
                      'initial_investigation': 'Blood culture remains the diagnostic standard for EOS. Blood or CSF cultures establish the diagnosis; CBC and CRP alone cannot diagnose EOS. Surface cultures and gastric aspirates do not diagnose EOS, and urine culture is not indicated in EOS evaluations before 72 hours. Obtain and interpret diagnostic specimens within the responsible clinician assessment and local pathway; no available culture result is established here.',
                      'single_risk': 'For infants born at 35 weeks or later, acceptable AAP risk-assessment approaches include categorical risk algorithms, multivariate assessment incorporating intrapartum factors and infant examination, and serial physical examinations. Use a locally documented birth-center pathway with ongoing surveillance. A single known maternal risk does not establish EOS or justify an invented individual probability.',
                      'missing_results': 'Unavailable maternal history, culture results and current observations remain unknown. AAP risk stratification includes risk factors and infant examinations or serial physical examinations. Obtain the missing clinical assessment and use the local pathway. Blood or CSF cultures establish EOS diagnosis; laboratory markers alone and missing results cannot establish absence of infection.'}[family]
                else:
                    reference = base['reference']
                    if family == 'initial_investigation':
                        reference = reference.replace('The supplied case has no culture result', 'The supplied case has no available culture result')
                    if family == 'crp_alone' and p['crp'] is None:
                        reference = reference.replace('The C-reactive protein concentration fell in the supplied history.', 'Earlier C-reactive protein readings fell, but the current result is unavailable.')
                    if family == 'incomplete_stop':
                        reference = reference.replace('at 36 hours', 'at the 36-hour review')
                case = {'id': f'{guideline.lower()}-expanded-{family}-{n+1:02}', 'family': family, 'synthetic': True,
                        'query': query, 'patient': p, 'history': history,
                        'gold_chunk_ids': nice_gold[family] if guideline == 'NICE' else aap_gold[family], 'reference': reference}
                assert set(case) == set(originals[0]), 'Case schema drift'
                assert all(h['age_hours'] < age for h in history)
                for key in case['gold_chunk_ids']:
                    assert key in byid, f'MISSING GOLD ID {key} in {case["id"]}'
                    assert byid[key]['guideline_id'] == guideline, 'Cross-guideline gold contamination'
                added.append(case)
                if family == 'incomplete_stop' or (guideline == 'NICE' and ga < 35) or family == 'missing_results':
                    review.append({'case_id': case['id'], 'priority': 'high', 'reason': 'Critical-illness stopping exception' if guideline == 'AAP' and family == 'incomplete_stop' else 'Missingness, stopping eligibility or preterm applicability requires clinician adjudication'})
    cases = originals + added
    assert len(cases) == 114 and len({c['id'] for c in cases}) == 114
    for c in cases:
        assert all(g in byid for g in c['gold_chunk_ids']), f'Missing gold in {c["id"]}'
    for name in ['cases.json', 'corpus.json', 'summary.json', 'protocol.json']:
        target = OUT / 'historical' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((OLD / name).read_bytes())
    paper = ROOT / 'docs/research/manuscript.md'
    (OUT / 'historical/manuscript.md').write_bytes(paper.read_bytes())
    save(OUT / 'cases.json', cases)
    save(OUT / 'additional_cases.json', added)
    save(OUT / 'corpus.json', {'purpose': 'evaluation_only_pending_clinician_review', 'chunks': list(byid.values()),
        'sources': {'NICE': {'url': nice['source_url'], 'pdf_sha256': nice['pdf_sha256']},
                    'AAP': {'url': 'https://publications.aap.org/pediatrics/article/142/6/e20182894/37522', 'doi': '10.1542/peds.2018-2894', 'pdf_sha256': sha(pdf.read_bytes())}}})
    code_files = ['backend/scripts/evaluate_generation.py', 'backend/rag/verification_graph.py', 'backend/rag/knowledge_graph.py', 'backend/services/groq_client.py']
    save(OUT / 'protocol.json', {'seed': SEED, 'bootstrap_resamples': 2000, 'top_k': 4, 'rrf_k': 60,
        'primary_model': 'openai/gpt-oss-120b', 'verifier_model': 'openai/gpt-oss-120b', 'temperature': 0,
        'api_sampling_seed': None, 'schema_enforcement': False, 'primary_max_repairs': 0,
        'backbone_models': ['openai/gpt-oss-20b', 'qwen/qwen3.8-27b'],
        'bounded_resolution': {'max_repairs': 1, 'budget_seconds': 120, 'design': 'paired initial draft and audits; cached initial wall time deducted from remaining budget; fresh post-revision audits'},
        'guideline_gating': 'Each guideline is evaluated against its complete source-only index. No pooled headline metrics.',
        'references': 'Engineering-authored before inference; not clinician adjudicated.',
        'review_status': 'AAP technical identity verified; all gold judgments and clinical applicability pending clinician review.',
        'historical_runtime_drift': 'Historical verifier SHA differs; original 18 are rerun using current frozen verifier. Historical numbers are not a bit-identical runtime comparison.',
        'transport': 'Provider failures excluded from quality and logged separately; semantic failures retained; checkpoint every completed role.',
        'faults': '12 original NICE faults and 12 AAP faults: negation, missing conditions, invented dose, false normal; three parameter variants each',
        'code_sha256': {f: sha((ROOT / f).read_bytes()) for f in code_files}})
    save(OUT / 'manifest.json', {'seed': SEED, 'original_cases_file_sha256': sha((OLD / 'cases.json').read_bytes()),
        'cases_file_sha256': sha((OUT / 'cases.json').read_bytes()), 'corpus_file_sha256': sha((OUT / 'corpus.json').read_bytes()),
        'protocol_sha256': sha((OUT / 'protocol.json').read_bytes()),
        'cases': [{'id': c['id'], 'sha256': sha(canonical(c)), 'guideline': 'AAP' if c['gold_chunk_ids'][0].startswith('AAP') else 'NICE',
                   'gold': [{'id': g, 'text_sha256': byid[g]['text_sha256'], 'pdf_sha256': byid[g]['pdf_sha256']} for g in c['gold_chunk_ids']]} for c in cases]})
    save(OUT / 'clinician_review_queue.json', review)
    counts = collections.Counter((('AAP' if c['gold_chunk_ids'][0].startswith('AAP') else 'NICE'), c['family']) for c in cases)
    lines = ['# Frozen expanded benchmark', '', '114 synthetic cases: 18 unchanged originals, 72 new NICE cases, 24 new AAP cases. Seed 31. No real patient records.', '', '|Family|NICE|AAP|Total|', '|---|---:|---:|---:|']
    lines += [f'|{f}|{counts["NICE",f]}|{counts["AAP",f]}|{counts["NICE",f]+counts["AAP",f]}|' for f in FAMILIES]
    lines += ['', f'Index: {len(nice["chunks"])} frozen NICE passages; {len(aap)} AAP paragraphs/recommendations. All gold IDs and source hashes validated.', '',
              'Clinical review remains pending. The production reviewed-source registry is unchanged. AAP >=35-week scope must not be extended to more premature infants.', '',
              'Priority review: all stopping/critical-illness cases, missing-result cases and NICE preterm cases (see clinician_review_queue.json). Original NICE box extraction and recommendation-boundary contamination also require source review. No uncertainty was resolved by changing original cases.', '',
              'AAP differs from NICE: no imported NICE 12-hour monitoring requirement, baseline CRP mandate or four-condition stopping rule. Term critical-illness exceptions are retained.', '',
              'AAP candidate passages include narrative paragraphs, which differ from numbered NICE recommendations; source-stratified results must disclose this asymmetry. AAP references remain source-derived and do not constitute independent clinical validation.']
    (OUT / 'benchmark_report.md').write_text('\n'.join(lines)+'\n', encoding='utf8')
    print({'cases': len(cases), 'new_NICE': 72, 'new_AAP': 24, 'AAP_chunks': len(aap), 'review_queue': len(review)})

if __name__ == '__main__':
    prepare()
