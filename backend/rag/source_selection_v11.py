"""Validate source selections per claim without approving malformed siblings."""
from collections import Counter
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from rag.verification_graph import QuoteReference


class SourceSelectedClaim(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(pattern=r'^C(?:[1-9]|1[0-6])$')
    section:Literal['risk_analysis','recommended_actions','investigations','antibiotic_review','monitoring_plan','escalation_criteria','nutrition_fluids','parent_communication_notes','follow_up']
    support:list[QuoteReference]=Field(min_length=0,max_length=4)


class SourceSelection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    claims:list[SourceSelectedClaim]=Field(min_length=0,max_length=16)


def validate_claims(raw,quotes):
    if not isinstance(raw,dict) or set(raw)!={'claims'} or not isinstance(raw['claims'],list) or len(raw['claims'])>16:
        return [],[{'id':None,'reason':'Invalid top-level source-selection contract'}],[]
    counts=Counter(c.get('id') for c in raw['claims'] if isinstance(c,dict) and isinstance(c.get('id'),str))
    kept=[];bad=[];unsupported=[]
    for value in raw['claims']:
        cid=value.get('id') if isinstance(value,dict) else None
        try:
            c=SourceSelectedClaim.model_validate(value)
            if counts[c.id]!=1:raise ValueError('Duplicate claim ID')
            ids=[s.quote_id for s in c.support]
            if len(ids)!=len(set(ids)) or not set(ids)<=set(quotes):raise ValueError('Unknown or duplicate source reference')
            if not ids:unsupported.append(c.section)
            else:kept.append(c)
        except (ValueError,TypeError):
            bad.append({'id':cid,'reason':'Invalid claim contract, unknown/duplicate reference or reference budget exceeded'})
    return kept,bad,unsupported
