from rag.source_selection_v11 import validate_claims


def entry(cid='C1',refs=None):
    return {'id':cid,'section':'investigations','support':[{'quote_id':q} for q in (refs if refs is not None else ['E1Q1'])]}


def test_invalid_sibling_does_not_block_valid_claim_or_invent_missing_content():
    good,bad,empty=validate_claims({'claims':[entry(),entry('C2',['E99Q1']),entry('C3',[])]},{'E1Q1'})
    assert [g.id for g in good]==['C1'] and [b['id']for b in bad]==['C2']
    assert empty==['investigations']


def test_oversized_reference_list_is_rejected_not_silently_truncated():
    refs=[f'E{i}Q1' for i in range(1,6)]
    good,bad,_=validate_claims({'claims':[entry(),entry('C2',refs)]},set(refs))
    assert [g.id for g in good]==['C1'] and bad[0]['id']=='C2'


def test_duplicate_ids_reject_ambiguous_claims_but_preserve_unique_sibling():
    good,bad,_=validate_claims({'claims':[entry(),entry(),entry('C3')]},{'E1Q1'})
    assert [g.id for g in good]==['C3'] and len(bad)==2


def test_authored_treatment_prose_cannot_enter_the_source_contract():
    bad_claim={**entry('C2'),'text':'Invented regimen'}
    good,bad,_=validate_claims({'claims':[entry(),bad_claim]},{'E1Q1'})
    assert [g.id for g in good]==['C1'] and bad[0]['id']=='C2'
