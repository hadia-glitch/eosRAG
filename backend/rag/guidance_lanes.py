"""Keep normative guidance separate from research background in source indexes.

Role labels come from publisher structure, not benchmark relevance. Background
remains available for evidence searches; it must not masquerade as a clinical
recommendation merely because it repeats a biomarker or treatment keyword.
"""

def guidance_role(chunk):
    source=chunk.get('guideline_id')
    kind=chunk.get('chunk_type','')
    if source=='WHO':
        return kind in {'recommendation_and_qualifiers','complete_scope_span'}
    if source=='AAP':
        if kind in {'summary_recommendation','complete_paragraph_span'}:return True
        heading=(chunk.get('retrieval_headings') or {}).get('parent_heading','').upper()
        return heading in {'LABORATORY TESTING','RISK STRATIFICATION FOR TERM AND LATE-PRETERM INFANTS',
                           'TREATMENT OF EOS','PREVENTION STRATEGIES','SUMMARY POINTS'}
    return source=='NICE'
