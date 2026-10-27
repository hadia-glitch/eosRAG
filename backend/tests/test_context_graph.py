import hashlib
from rag.context_graph import build_context_graph,context_for,definition_spans


def fixture():
    shared={'guideline_id':'WHO','pdf_sha256':'source-fixture','pdf_page':1,
            'scope':{'care_setting':['non_hospital'],'postnatal_age_hours':[0,1439]},
            'retrieval_headings':{'section_id':'A.2'}}
    return [{**shared,'chunk_id':'recommendation','chunk_type':'recommendation_and_qualifiers',
             'raw_text':'Infants with critical illness should be referred.'},
            {**shared,'chunk_id':'definition','chunk_type':'source_paragraph',
             'raw_text':'Critical illness is defined as inability to feed or convulsions. A truncated remainder'}]


def test_exact_complete_definition_and_traceable_section_edge():
    data=fixture();graph=build_context_graph(data)
    assert len(graph['nodes'])==len(graph['edges'])==1
    n=graph['nodes'][0];s=n['source_span']
    assert n['raw_text']==data[1]['raw_text'][s['start']:s['end']]
    assert n['raw_text'].endswith('convulsions.')
    assert n['text_sha256']==hashlib.sha256(n['raw_text'].encode()).hexdigest()
    assert graph['edges'][0]['from']=='recommendation'
    assert n['clinical_review_status']=='pending'


def test_context_cannot_cross_setting_or_be_counted_as_an_original_rank():
    graph=build_context_graph(fixture());selected=['recommendation']
    assert len(context_for(selected,graph,{'care_setting':'non_hospital','age_hours':12}))==1
    assert context_for(selected,graph,{'care_setting':'hospital','age_hours':12})==[]
    assert selected==['recommendation']
    assert context_for(selected,graph,{'care_setting':'non_hospital','age_hours':12},max_nodes=0)==[]


def test_truncated_definition_is_not_accepted_and_decimal_is_preserved():
    assert list(definition_spans('Critical illness is defined as inability to'))==[]
    spans=list(definition_spans('Low temperature is defined as below 35.5 degrees. Other text'))
    assert spans[0]['text']=='Low temperature is defined as below 35.5 degrees.'


def test_background_heading_is_not_a_second_definition_and_span_stays_exact():
    text='Background and definitions Critical illness is defined as inability to feed.'
    span=list(definition_spans(text))[0]
    assert span['text']=='Critical illness is defined as inability to feed.'
    assert text[span['start']:span['end']]==span['text']
