from demo.source_boundaries import HEADINGS,clean_boundary
from demo.retrieval import in_scope


def test_only_verified_following_headings_are_removed():
    body='Review only if the culture is negative and every condition is satisfied. [2012]'
    for key,heading in HEADINGS.items():
        assert clean_boundary(key,body+' '+heading)==(body,heading)
    clinical_note=body+' Note: retain special precautions for renal impairment.'
    assert clean_boundary('NICE-1.21.4',clinical_note)==(clinical_note,'')
    assert clean_boundary('NICE-1.6.2',body+' '+HEADINGS['NICE-1.21.4'])==(body+' '+HEADINGS['NICE-1.21.4'],'')


def test_unknown_antibiotic_exposure_excludes_observation_only_followup_pathway():
    assert not in_scope({'chunk_id':'NICE-1.5.1'})
    assert in_scope({'chunk_id':'NICE-1.1.4'})
