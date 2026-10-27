"""User-requested 100-case amendment; selection does not use retrieval outcomes."""
import copy
import json
import random
import re
from pathlib import Path
from backend.scripts.prepare_expanded_benchmark import ROOT, canonical, clean, save, sha, FAMILIES

OUT = ROOT/'output/research/expanded100'

def prepare():
    import fitz
    if (OUT/'manifest.json').exists():
        raise SystemExit('100-case benchmark already frozen; refusing overwrite')
    previous = ROOT/'output/research/expanded'
    base = json.loads((previous/'cases.json').read_text())
    originals = json.loads((ROOT/'output/research/rag_v2/cases.json').read_text())
    cases = copy.deepcopy(originals)
    # Ordered counts were chosen to balance six families as closely as 40 allows.
    # No case selection depends on scores from the superseded 114-case pilot.
    for i, family in enumerate(FAMILIES):
        nice = [c for c in base if c['id'].startswith('nice-expanded-') and c['family']==family]
        cases.extend(copy.deepcopy(nice[:4 if i<4 else 3]))
        aap = [c for c in base if c['id'].startswith('aap-expanded-') and c['family']==family]
        cases.extend(copy.deepcopy(aap))
        fifth = copy.deepcopy(aap[0])
        fifth['id'] = f'aap-expanded-{family}-05'
        fifth['patient']['care_setting'] = 'neonatal_unit'
        fifth['patient']['gestational_age_weeks'] = 39
        fifth['query'] = re.sub(r'Gestation \d+ weeks;', 'Gestation 39 weeks;', fifth['query'])
        fifth['query'] = re.sub(r'setting [^.]+\.', 'setting neonatal unit.', fifth['query'])
        cases.append(fifth)
    corpus = json.loads((previous/'corpus.json').read_text())
    pdf = next((ROOT/'backend/guidelines').glob('WHO*.pdf'))
    doc = fitz.open(pdf)
    who = []
    for page_no, page in enumerate(doc,1):
        text = page.get_text()
        matches = list(re.finditer(r'Recommendation ([AB]\.\d+[ab]?)\s*(?:\((?:NEW|UPDATED)\))?\s*\n',text))
        for match in matches:
            end = text.find('\nRemarks',match.end())
            assert end > match.end(), f'Missing recommendation boundary on WHO page {page_no}'
            key = 'WHO2024-'+match[1]
            content = clean(text[match.end():end])
            if key == 'WHO2024-B.1':
                # Retain rationale for the explicit absence of a recommendation.
                content = clean(text[match.end():text.index('Background and definitions',end)])
            who.append({'chunk_id':key,'text':content,'pdf_page':page_no,'printed_page':page_no+16,
                        'chunk_type':'recommendation_and_qualifiers','section':match[1]})
        # Narrative paragraphs supply background and scope alongside complete
        # recommendations; fixed length rule is independent of relevance labels.
        for block_no, block in enumerate(page.get_text('blocks')):
            content = clean(block[4])
            if block[6] == 0 and 180 <= len(content) <= 2400 and block[1] < 745 and 'Recommendation ' not in content:
                who.append({'chunk_id':f'WHO2024-P{page_no}-B{block_no}','text':content,
                            'pdf_page':page_no,'printed_page':page_no+16,'chunk_type':'source_paragraph','section':None})
    special = [
        ('WHO2024-A.1-DEFINITION',1,'Possible serious bacterial infection (PSBI) is defined','In 2014,'),
        ('WHO2024-C-CLINICAL',42,'Clinical management','Links to key WHO resources'),
        ('WHO2024-C-REFERRAL',43,'Referral to hospital and what to do when','Risk groups'),
        ('WHO2024-C-RISK',43,'Risk groups','Settings with different antimicrobial')]
    for key, page_index, start, end in special:
        raw = clean(doc[page_index].get_text())
        # Layout extraction can insert a bullet between heading words only after
        # normalization; boundaries are required to exist exactly.
        a, b = raw.find(start), raw.find(end)
        assert 0 <= a < b, f'WHO scope-span extraction failed: {key}'
        who.append({'chunk_id':key,'text':raw[a:b].strip(),'pdf_page':page_index+1,
                    'printed_page':page_index+17,'chunk_type':'complete_scope_span','section':key.split('-')[-1]})
    # PDF text blocks can repeat an entire boxed recommendation. Keep the
    # numbered recommendation as the canonical passage, with explicit aliases.
    canonical_who, aliases, seen = [], {}, {}
    for c in who:
        key = sha(c['text'].encode())
        if key in seen:
            aliases[c['chunk_id']] = seen[key]
        else:
            seen[key] = c['chunk_id']
            canonical_who.append(c)
    who = canonical_who
    digest = sha(pdf.read_bytes())
    for c in who:
        section = c.get('section') or ''
        c.update({'guideline_id':'WHO','source':'WHO serious bacterial infections 2024','version':'2024-12-08',
                  'text_sha256':sha(c['text'].encode()),'pdf_sha256':digest,
                  'scope':{'gestational_age_weeks':[None,None],
                           'postnatal_age_hours':[168,1439] if section=='A.5' else [0,167] if section=='A.4' else [0,1439],
                           'care_setting':['non_hospital'] if section.startswith('A.') else ['hospital'] if section.startswith('B.') else ['hospital','non_hospital'],
                           'qualification':'No validated gestation/maternal-risk subgroup stratification is claimed; paragraph scope requires clinician review.'},
                  'clinical_review_status':'pending','technical_identity_check':'WHO2024_recommendation_numbers_and_pagination_checked'})
    # Scope of mixed NICE narrative paragraphs is not inferred from a source title.
    for c in corpus['chunks']:
        if c['guideline_id']=='AAP':
            c['scope']['gestational_age_weeks']=[35,None]
        if c['guideline_id']=='NICE':
            c['scope']['postnatal_age_hours']=[None,None]
            c['scope']['qualification']='Mixed early/late-onset source; individual recommendation applicability requires review. Benchmark cases are <72 hours.'
    corpus['chunks'].extend(who)
    corpus['sources']['WHO']={'url':'https://www.who.int/publications/i/item/9789240102903',
        'pdf_sha256':digest,'local_pdf_pages':49,'printed_page_offset':16,
        'title':'WHO recommendations for management of serious bacterial infections in infants aged 0-59 days',
        'scope_note':'Only the birth-to-<72-hour subset is tested; non-hospital/referral qualifiers are retained.',
        'exact_text_duplicate_aliases':aliases}
    rng=random.Random(31)
    for family in FAMILIES:
        for n in range(5):
            age=[6,12,24,48,60][n]
            p={'age_hours':age,'gestational_age_weeks':rng.choice([35,37,38,40,41]),
               'care_setting':'hospital' if family in ['incomplete_stop','initial_investigation'] else 'primary_health_clinic',
               'maternal_gbs':'unknown','respiratory_rate':48,'spo2':97,'crp':None,'culture_status':'unknown',
               'temperature_c':36.8,'feeding':'feeding well','movement':'spontaneous','convulsions':False,'severe_chest_indrawing':False,
               'referral_possible':True,'red_flags':'not fully documented'}
            history=[]
            if family=='deterioration':
                p.update({'respiratory_rate':70+n,'spo2':91,'feeding':'unable to feed at all' if n<2 else 'feeding well',
                          'movement':'only on stimulation' if n<2 else 'spontaneous','other_IMCI_signs':'absent on examination' if n>=2 else 'not fully documented'})
                history=[{'age_hours':age/2,'respiratory_rate':48,'spo2':98,'feeding':'feeding well'}]
                gold=['WHO2024-A.1','WHO2024-A.2' if n<2 else 'WHO2024-A.4']
                query='Review new inability to feed or isolated fast breathing in a newborn in a primary-care clinic. Explain assessment and referral with the recorded signs.'
                reference=('WHO recommends the seven-sign IMCI algorithm in non-hospital settings. The infant has new recorded signs of illness and requires clinical assessment. '+
                    ('Critical illness requires hospital referral; treatment outside hospital is conditional on referral not being possible.' if n<2 else
                     'For infants aged 0-6 days with fast breathing as the only IMCI sign, hospital referral is recommended. The oral-antibiotic alternative is conditional on referral being impossible. Hypoxia still requires clinician assessment and must not be ignored when determining whether illness is truly isolated.'))
            elif family=='crp_alone':
                p.update({'crp':4+n,'feeding':'not feeding well','temperature_c':38.2})
                history=[{'age_hours':age/2,'crp':18+n,'feeding':'feeding well','temperature_c':36.8}]
                gold=['WHO2024-A.1','WHO2024-A.1-DEFINITION']
                query='CRP fell but feeding worsened and temperature rose. What clinical signs should guide non-hospital assessment under WHO guidance?'
                reference='The recorded CRP fell while feeding worsened and fever developed. WHO non-hospital identification uses the seven-sign IMCI algorithm; not feeding well and high temperature are among the listed signs. The clinical findings require further evaluation or treatment. These passages do not establish a CRP-based exclusion or antibiotic-stopping rule; no such WHO threshold should be invented.'
            elif family=='incomplete_stop':
                p.update({'age_hours':60+n,'culture_status':'negative','culture_incubation_hours':36,
                          'antibiotic_duration_hours':36,'feeding':'not feeding well','temperature_c':38.2,
                          'clinical_condition':'hospitalized with suspected sepsis and persistent signs'})
                gold=['WHO2024-B.2','WHO2024-C-CLINICAL']
                query='Hospitalized suspected sepsis: a culture is negative at 36 hours but clinical signs persist. Does this WHO source provide a NICE-style 36-hour stopping pathway?'
                reference='The WHO hospital recommendation for suspected sepsis describes ampicillin plus gentamicin as first-choice management for at least ten days. Clinical management of an unwell young infant requires careful clinical judgement. These passages do not provide the NICE 36-hour stopping pathway. A negative culture must not be presented as satisfying an invented WHO early-stop rule. The responsible clinician must reassess the diagnosis and the applicable local protocol; this is discussion of source guidance rather than an automatic treatment order.'
            elif family=='initial_investigation':
                p.update({'feeding':'not feeding well','temperature_c':38.1,'clinical_condition':'suspected sepsis'})
                gold=['WHO2024-B.1','WHO2024-C-CLINICAL']
                query='Does WHO 2024 endorse a hospital laboratory or clinical prediction algorithm to diagnose neonatal sepsis? Explain initial assessment without inventing a CBC or CRP threshold.'
                reference='WHO made no recommendation for hospital-based clinical-sign diagnostic algorithms in section B.1. The stated reasons include feasibility limitations of laboratory-based algorithms and limited external validation. This is not a recommendation against all laboratory investigation. Clinical management of an unwell infant requires careful clinical judgement; no endorsed CRP or CBC cutoff or diagnostic score can be inferred from this source.'
            elif family=='single_risk':
                p.update({'maternal_gbs':'positive','clinical_condition':'well appearing','seven_IMCI_signs':'assessed absent'})
                gold=['WHO2024-A.1','WHO2024-C-RISK']
                query='A well newborn has maternal GBS history but no IMCI illness sign. Does WHO supply a validated maternal-risk or gestation-based score for this infant?'
                reference='WHO non-hospital identification uses the seven-sign IMCI algorithm. The cross-cutting remarks state that evidence was insufficient to recommend further stratification by gestation, birthweight or maternal risk factors. Maternal GBS history alone therefore does not yield a validated numerical WHO risk estimate. Do not infer absence of all infection or an automatic management order from the absence of recorded IMCI signs; use clinical judgement and the applicable local pathway.'
            else:
                p.update({'temperature_c':None,'respiratory_rate':None,'spo2':None,'feeding':'unknown','movement':'unknown',
                          'convulsions':None,'severe_chest_indrawing':None,'maternal_gbs':'unknown','culture_status':'unavailable'})
                gold=['WHO2024-A.1','WHO2024-C-CLINICAL']
                query='Current feeding, movement, temperature, breathing and culture results are missing. Explain what a WHO-based assessment can establish in the clinic.'
                reference='The seven-sign IMCI algorithm requires assessment of clinical signs in non-hospital settings. Missing feeding, movement, temperature and respiratory observations cannot establish an absence of those signs. WHO emphasizes careful clinical judgement because signs can be difficult to ascertain in young infants. Obtain the missing clinical assessment; do not invent normal measurements, a diagnosis or permission to stop antibiotics.'
            query+=f' Gestation {p["gestational_age_weeks"]} weeks; age {p["age_hours"]} hours; setting {p["care_setting"]}.'
            cases.append({'id':f'who-expanded-{family}-{n+1:02}','family':family,'synthetic':True,
                          'query':query,'patient':p,'history':history,'gold_chunk_ids':gold,'reference':reference})
    assert len(cases)==100 and len({c['id'] for c in cases})==100
    index={c['chunk_id']:c for c in corpus['chunks']}
    assert len(index)==len(corpus['chunks']), 'Duplicate source IDs'
    for case in cases:
        assert set(case)==set(originals[0]), f'Schema drift {case["id"]}'
        assert all(key in index for key in case['gold_chunk_ids']), f'MISSING GOLD ID: {case["id"]}'
        assert all(h['age_hours']<case['patient']['age_hours'] for h in case['history'])
    assert cases[:18]==originals, 'Original cases changed'
    save(OUT/'cases.json',cases)
    save(OUT/'additional_cases.json',cases[18:])
    save(OUT/'corpus.json',corpus)
    protocol=json.loads((previous/'protocol.json').read_text())
    protocol.update({'benchmark_size':100,'guideline_counts':{'NICE':40,'AAP':30,'WHO':30},
                     'scope_amendment':'User requested exactly 100 cases and inclusion of WHO before any generation. Earlier retrieval-only 114-case prototype is retained separately. No retrieval hyperparameters changed.',
                     'faults':'12 faults per guideline, 36 total; original four fault families and three variants',
                     'review_status':'All sources technically checked; gold relevance and clinical applicability pending clinician review.'})
    protocol.pop('orchestration_sha256',None)
    save(OUT/'protocol.json',protocol)
    save(OUT/'manifest.json',{'seed':31,'original_cases_file_sha256':sha((ROOT/'output/research/rag_v2/cases.json').read_bytes()),
        'cases_file_sha256':sha((OUT/'cases.json').read_bytes()),'corpus_file_sha256':sha((OUT/'corpus.json').read_bytes()),
        'protocol_sha256':sha((OUT/'protocol.json').read_bytes()),
        'cases':[{'id':c['id'],'sha256':sha(canonical(c)),
                  'guideline':index[c['gold_chunk_ids'][0]]['guideline_id'],
                  'gold':[{'id':g,'text_sha256':index[g]['text_sha256'],'pdf_sha256':index[g]['pdf_sha256']} for g in c['gold_chunk_ids']]} for c in cases]})
    review=[{'case_id':c['id'],'priority':'high' if c['id'].startswith('who-') or c['family'] in ['incomplete_stop','missing_results'] else 'standard',
             'reason':'WHO setting/referral constraints, absent subgroup evidence, evidence gaps and duration differences' if c['id'].startswith('who-') else 'Gold relevance and reference correctness not clinician adjudicated'} for c in cases]
    save(OUT/'clinician_review_queue.json',review)
    lines=['# 100-case three-guideline benchmark','', '40 NICE, 30 AAP and 30 WHO synthetic cases; 18 unchanged originals and 82 additions. Seed 31.', '', '|Family|NICE|AAP|WHO|Total|','|---|---:|---:|---:|---:|']
    for family in FAMILIES:
        counts=[sum(c['family']==family and index[c['gold_chunk_ids'][0]]['guideline_id']==g for c in cases) for g in ['NICE','AAP','WHO']]
        lines.append('|'+family+'|'+'|'.join(map(str,counts+[sum(counts)]))+'|')
    lines+=['',f'Corpus: NICE 132, AAP 43, WHO {len(who)} passages. Every gold ID and source hash is checked; references are engineering-authored and await clinician review.', '',
        'The former 114-case retrieval-only prototype remains in expanded/. Selection for this user-requested size change used predetermined family quotas and case order, not retrieval scores. The original 18 JSON objects and file are unchanged.', '',
        'WHO cases remain below 72 hours. WHO guidance covers a broader 0-59-day population and different resource settings. Its non-hospital recommendations retain referral conditions. No NICE stopping criteria, AAP risk tool or gestation-specific subgroup claim is attributed to WHO.', '',
        'Priority clinician review: all WHO cases, especially hospital diagnostic evidence-gap and stopping-duration cases; all AAP critical-illness exceptions; original NICE extraction boundaries. These are synthetic engineering tests, not independently validated clinical gold standards.']
    (OUT/'benchmark_report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print({'cases':len(cases),'counts':protocol['guideline_counts'],'WHO_chunks':len(who),'gold_validation':'passed'})

if __name__=='__main__':
    prepare()
