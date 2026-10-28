import hashlib
import pytest
from rag.workflow_context_graph import build_graph,marker_history,select_context


def c(cid,text,kind=None):
    return {'chunk_id':cid,'raw_text':text,'guideline_id':'NICE','pdf_sha256':'source',
            'retrieval_headings':{'section_heading':'Investigation principles'},'scope':{},'chunk_type':kind}


def test_sampling_and_interpretation_companions_are_source_derived_without_labels():
    chunks=[c('unrelated','A different investigation can be considered.'),
        c('marker','Measure baseline C-reactive protein when starting antibiotic treatment. Use subsequent readings.'),
        c('sample','When starting antibiotic treatment, perform a blood culture before giving the first dose.'),
        c('limit','Do not use C-reactive protein results alone to make decisions.')]
    corpus={x['chunk_id']:x for x in chunks};graph=build_graph(chunks)
    ranked,trace=select_context(list(corpus),corpus,graph,'Explain initial investigations.',{'age_hours':6},[])
    assert set(ranked[:4])==set(corpus)
    assert any(t['reason']=='source_qualification_graph' for t in trace)
    assert graph['clinical_review_status']=='pending'
    assert all('gold' not in str(e).lower() for e in graph['edges'])
    corpus['limit']['raw_text']='Altered source'
    with pytest.raises(ValueError,match='hash mismatch'):
        select_context(list(corpus),corpus,graph,'Explain initial investigations.',{'age_hours':6},[])


def test_publisher_summary_coverage_and_prefix_stability():
    chunks=[c('detail','A clinical detail.'),c('risk','Acceptable risk assessment approaches include serial examinations.','summary_recommendation'),
            c('culture','The diagnosis of infection is made by using cultures; it cannot be diagnosed by CRP.','summary_recommendation'),
            c('therapy','An empirical antibiotic regimen is described.','summary_recommendation')]
    corpus={x['chunk_id']:x for x in chunks}
    ranked,_=select_context(list(corpus),corpus,build_graph(chunks),'Explain uncertainty in maternal history and culture results.',{'age_hours':6},[])
    assert set(ranked[:2])=={'risk','culture'}
    assert ranked.index('therapy')>ranked.index('detail')


def test_serial_context_never_infers_an_unknown_value_or_uses_future_data():
    assert marker_history({'age_hours':6,'crp':None},[{'age_hours':2,'crp':4}]) is False
    assert marker_history({'age_hours':6,'crp':3},[{'age_hours':2,'crp':4}]) is True
    with pytest.raises(ValueError,match='strictly before'):
        marker_history({'age_hours':6},[{'age_hours':8,'crp':4}])


def test_graph_cannot_move_a_context_link_between_source_documents():
    chunks=[c('marker','Measure baseline C-reactive protein when starting antibiotic treatment. Use subsequent readings.'),
            c('limit','Do not use C-reactive protein results alone to make decisions.')]
    corpus={x['chunk_id']:x for x in chunks};graph=build_graph(chunks)
    graph['nodes'][0]['pdf_sha256']='other-document'
    with pytest.raises(ValueError,match='provenance'):
        select_context(list(corpus),corpus,graph,'Explain serial CRP.',{'age_hours':6},[])
    chunks[1]['pdf_sha256']='another-valid-source';graph=build_graph(chunks)
    graph['edges'].append({'from':'marker','to':'limit','relation':'HAS_INTERPRETATION_LIMIT'})
    with pytest.raises(ValueError,match='Cross-document'):
        select_context(list(corpus),corpus,graph,'Explain serial CRP.',{'age_hours':6},[])
