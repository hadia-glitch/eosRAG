import numpy as np
from rag.guidance_lanes import guidance_role
from rag.faceted_selection import select_facets
from rag.query_plan_validation import validate_questions


def test_research_background_cannot_become_normative_who_guidance():
    assert not guidance_role({'guideline_id':'WHO','chunk_type':'source_paragraph'})
    assert guidance_role({'guideline_id':'WHO','chunk_type':'recommendation_and_qualifiers'})
    assert guidance_role({'guideline_id':'WHO','chunk_type':'complete_scope_span'})


def test_aap_diagnostic_guidance_and_epidemiology_are_separate_roles():
    assert guidance_role({'guideline_id':'AAP','chunk_type':'article_paragraph',
                         'retrieval_headings':{'parent_heading':'LABORATORY TESTING'}})
    assert not guidance_role({'guideline_id':'AAP','chunk_type':'article_paragraph',
                             'retrieval_headings':{'parent_heading':'PATHOGENESIS AND CURRENT EPIDEMIOLOGY OF NEONATAL EOS'}})


def test_mmr_actually_avoids_a_redundant_neighbour_without_promoting_the_tail():
    vectors=np.array([[1.,0],[1.,0],[0.,1],[-1.,0],[1.,0],[1.,0],[1.,0],[1.,0],[0.,1]])
    selected=select_facets(list(range(9)),vectors,4)
    assert selected[:2]==[0,2]
    assert set(selected)<=set(range(8))
    assert len(set(selected))==4


def test_complementary_facet_anchors_are_retained_and_deduplicated():
    selected=select_facets(list(range(12)),np.eye(12),4,anchors=[0,3,3])
    assert selected[:2]==[0,3]
    assert len(set(selected))==4


def test_system_eos_age_scope_is_not_a_new_treatment_duration():
    ok,_=validate_questions(['Which investigations are used in neonates 0-72 hours with suspected sepsis?'],'Explain initial investigations.')
    assert ok
    assert not validate_questions(['Should antibiotics be stopped at 72 hours?'],'Explain treatment review.')[0]
    assert not validate_questions(['Should gentamicin 99 mg/kg be given?'],'Explain treatment review.')[0]
