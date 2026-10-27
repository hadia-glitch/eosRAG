import json
from rag.patient_passage_ranker import select_patient_passages


def test_ranking_receives_exact_facts_and_trends_without_answer_labels():
    patient={'culture_status':'unknown','respiratory_rate':74,'maternal_gbs':'unknown'}
    history=[{'hours_ago':4,'respiratory_rate':48}]
    chunks=[{'chunk_id':'source','raw_text':'Perform a clinical assessment.'}]
    def llm(prompt,settings,**kw):
        p=json.loads(prompt)
        assert p['clinical_case_context']=={'patient':patient,'history':history}
        assert p['original_information_need']=='Explain the assessment.'
        assert p['candidates'][0]['text']==chunks[0]['raw_text']
        assert 'gold_chunk_ids' not in p and 'reference_answer' not in p
        assert 'Do not diagnose' in p['task']
        return {'ordered_ids':['source']}
    assert select_patient_passages('Explain the assessment.',chunks,patient,history,None,llm=llm)==['source']
    assert patient['culture_status']=='unknown' and history[0]['respiratory_rate']==48
