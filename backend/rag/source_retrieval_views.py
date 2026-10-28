"""Source-defined retrieval context and evidence genre; no clinical inference.

Original passages stay immutable. Publisher definitions can enrich the retrieval
view only when source identity, exact text hash and patient scope match.
"""
import hashlib
import re
from rag.clinical_scope import applicable
from rag.topic_scope import current_case_topic


def topic_admission(chunk, query, patient):
    accepted,reason=current_case_topic(chunk,query,patient)
    if not accepted:return accepted,reason
    text=chunk['raw_text'];q=query.lower()
    ga=patient.get('gestational_age_weeks')
    if type(ga) in (int,float):
        calculator=re.search(r'\bcalculator\b',text,re.I)
        lower=re.search(r'\bborn after\s+(\d+)\+(\d)\s*weeks',text,re.I) if calculator else None
        if lower and ga<=int(lower[1])+int(lower[2])/7 and not re.search(r'calculator|kaiser',q):
            return False,'calculator_outside_explicit_source_gestational_scope'
        lower=re.search(r'^For babies born from\s+(\d+)\+(\d)\s*weeks',text,re.I)
        if lower and ga<int(lower[1])+int(lower[2])/7 and not re.search(r'oral antibiotic|gestational.*(?:limit|eligib|scope)',q):
            return False,'outside_explicit_leading_gestational_population'
    csf_context=bool(re.search(r'\b(?:csf|cerebrospinal|lumbar puncture|meningitis)\b',q)) or any(
        patient.get(k) is not None for k in ['csf_results','csf_wbc','csf_glucose','csf_protein'])
    if not csf_context and re.search(r'^(?:When interpreting|Interpret|Use the results of)\b.{0,65}\b(?:CSF|cerebrospinal fluid)\b',text,re.I):
        return False,'unrequested_existing_csf_result_interpretation'
    # A disease-specific recommendation is not a general empirical regimen.
    # Explicit comparison questions retain the conditional alternatives.
    specific=re.search(r'who are hospitalized with suspected (staphylococcal sepsis|staphylococcal pneumonia|meningitis|pneumonia)',text,re.I)
    if specific:
        condition=specific[1].lower()
        terms=['staphylococc','staph'] if 'staphylococcal' in condition else [condition]
        context=q+' '+str(patient.get('clinical_condition','')).lower()+' '+str(patient.get('organism','')).lower()
        if not any(t in context for t in terms) and not re.search(r'\b(?:compare|alternatives|pathogen.specific)\b',q):
            return False,'unrequested_specific_diagnostic_pathway'
    return True,'topic_admitted'


def genre(chunk):
    text=chunk['raw_text']
    if chunk.get('chunk_type')=='summary_recommendation':return 'core_guidance'
    if re.search(r'^No recommendation\b|unable to (?:make|recommend)|lack of evidence',text,re.I):return 'scope_limitation'
    if chunk.get('chunk_type')=='recommendation_and_qualifiers':return 'core_guidance'
    if chunk['guideline_id']=='AAP':
        normative=re.search(r'\b(?:should|must|cannot|can not|not sufficient|not sensitive|not specific|acceptable approaches|diagnostic standard|under this approach|are either treated|not recommended|is defined|risk assessment includes|clinical utility|specificity is poor|absence of infection|low sensitivities|not associated with EOS)\b',text,re.I)
        empirical=re.search(r'\b(?:researchers|cohort|studies have|study of|study reported|compared the outcomes|infants were)\b',text,re.I)
        if empirical and not normative:return 'study_background'
    if chunk['guideline_id']=='WHO' and chunk.get('chunk_type')=='complete_scope_span':return 'implementation_context'
    return 'core_guidance'


def retrieval_view(chunk, graph, patient):
    nodes={n['chunk_id']:n for n in graph['nodes']}
    definitions=[];seen=set()
    for edge in graph['edges']:
        if edge['from']!=chunk['chunk_id']:continue
        node=nodes[edge['to']]
        if node['guideline_id']!=chunk['guideline_id'] or node['pdf_sha256']!=chunk['pdf_sha256']:
            raise ValueError('Cross-source definition edge')
        digest=hashlib.sha256(node['raw_text'].encode()).hexdigest()
        if digest!=node['text_sha256']:raise ValueError('Definition text hash mismatch')
        if not applicable(node['scope'],patient) or digest in seen:continue
        seen.add(digest);definitions.append(node)
    view=chunk['text']
    if definitions:
        view+=' / Publisher section definitions: '+' / '.join(n['raw_text'] for n in definitions)
    return view,definitions
