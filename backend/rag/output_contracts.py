"""Provider-compatible constrained schemas plus application validation.

Shape constraints never establish semantic or clinical support.
"""
from copy import deepcopy

def constrained_schema(model,*,quote_ids=None,claim_ids=None):
    schema=deepcopy(model.model_json_schema())
    # Keep the portable strict subset; Pydantic checks bounds/patterns again.
    def clean(value):
        if isinstance(value,dict):
            for key in ['title','description','default','minLength','maxLength','pattern','minimum','maximum','minItems','maxItems']:
                value.pop(key,None)
            for child in value.values():clean(child)
        elif isinstance(value,list):
            for child in value:clean(child)
    clean(schema)
    if quote_ids is not None:
        schema['$defs']['QuoteReference']['properties']['quote_id']={'type':'string','enum':sorted(quote_ids)}
        claim_type='IndexedClaim' if 'IndexedClaim' in schema['$defs'] else 'SourceSelectedClaim'
        schema['$defs'][claim_type]['properties']['id']={'type':'string','enum':[f'C{i}' for i in range(1,17)]}
    if claim_ids is not None:
        for key in ['checked_claim_ids','rejected_claim_ids']:
            schema['properties'][key]['items']={'type':'string','enum':sorted(claim_ids)}
    return schema
