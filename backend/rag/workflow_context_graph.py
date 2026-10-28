"""Publisher hierarchy and bounded source-context coverage for clinical retrieval.

No case families, outcome labels or recommendation identifiers define selection.
Source-derived context is not a diagnosis or proof of patient eligibility.
"""
import hashlib
import math
import re
from rag.clinical_scope import applicable
from rag.source_retrieval_views import topic_admission


def normalize(text):return re.sub(r'[\u2010-\u2015]','-',text).lower()


def roles(chunk):
    text=normalize(chunk['raw_text']);result=set()
    marker=bool(re.search(r'c[ -]reactive protein|\bcrp\b',text))
    if marker and re.search(r'\bbaseline\b',text) and re.search(r'\bsubsequent\b',text):result.add('serial_marker')
    if marker and re.search(r'do not use|cannot|can not',text) and re.search(r'\balone\b',text):result.add('marker_limit')
    if re.search(r'blood culture',text) and re.search(r'before giving the first dose|before the first.*dose',text):result.add('sampling_prerequisite')
    if re.search(r'reassess the clinical condition',text) and re.search(r'results of investigations',text):result.add('clinical_reassessment')
    if re.search(r'clinical management.*requires careful clinical judgement',text):result.add('general_clinical_context')
    return result


def summary_function(chunk):
    if chunk.get('chunk_type')!='summary_recommendation':return None
    text=normalize(chunk['raw_text'])
    if re.search(r'therapy should be discontinued|stop antibiotics|stopping antibiotics',text):return 'treatment_review'
    if re.search(r'empirical antibiotic regimen',text):return 'empirical_therapy'
    if re.search(r'diagnosis of.*made|cannot be diagnosed',text):return 'diagnostics'
    if re.search(r'risk stratification|risk assessment|stratified by.*risk',text):return 'assessment'
    return 'other'


def query_functions(query):
    q=normalize(query)
    heads=list(re.finditer(r'\b(?:explain|does|should|how|why|review|assess)\b',q))
    main=q[heads[-1].start():] if heads else q
    patterns={'diagnostics':r'crp|c-reactive|inflamm|culture|laborator|investigation|diagnos|tests?|uncertain',
              'treatment_review':r'stop|stopping|continu|duration|discontinu',
              'empirical_therapy':r'empiri|antibiotic (?:option|regimen|choice)|treatment choice',
              'assessment':r'assess|risk|history|examin|serial|signs of illness|develop.*illness'}
    ordered=[]
    for text in [main,q]:
        found=[]
        for tag,pattern in patterns.items():
            match=re.search(pattern,text)
            if match and tag not in ordered:found.append((match.start(),tag))
        ordered.extend(tag for _,tag in sorted(found))
    return ordered


def admission(chunk,query,patient):
    allowed,reason=topic_admission(chunk,query,patient)
    if not allowed:return allowed,reason
    text=normalize(chunk['raw_text']);q=normalize(query)
    age=patient.get('age_hours')
    clock=re.search(r'^when continuing intravenous antibiotics for longer than (\d+) hours',text)
    if clock and type(age) in (int,float) and age<float(clock[1]) and not re.search(r'antibiotic|treatment|stop|duration|continu',q):
        return False,'postnatal_treatment_clock_not_reached_or_requested'
    if re.search(r'^if group b streptococcus infection is identified.*after the baby',text) and not re.search(r'gbs|group b streptococc|postpartum',q):
        if patient.get('maternal_gbs_identified_postpartum') is not True:
            return False,'new_postpartum_maternal_infection_not_documented_or_requested'
    return True,'context_admitted'


def build_graph(chunks):
    nodes=[]
    for c in chunks:
        tags=roles(c)
        if tags:
            nodes.append({'chunk_id':c['chunk_id'],'guideline':c['guideline_id'],'pdf_sha256':c['pdf_sha256'],
                          'text_sha256':hashlib.sha256(c['raw_text'].encode()).hexdigest(),'roles':sorted(tags),
                          'source_heading':c.get('retrieval_headings',{}),'clinical_review_status':'pending'})
    by_id={c['chunk_id']:c for c in chunks};edges=[]
    for a in nodes:
        for b in nodes:
            if a['chunk_id']==b['chunk_id'] or (a['guideline'],a['pdf_sha256'])!=(b['guideline'],b['pdf_sha256']):continue
            ar=set(a['roles']);br=set(b['roles']);relation=None
            if 'serial_marker' in ar and 'marker_limit' in br:relation='HAS_INTERPRETATION_LIMIT'
            if 'serial_marker' in ar and 'sampling_prerequisite' in br:
                if all('when starting antibiotic treatment' in normalize(by_id[n['chunk_id']]['raw_text']) for n in [a,b]):relation='SHARES_TREATMENT_START_CONTEXT'
            if 'marker_limit' in ar and 'clinical_reassessment' in br and a['source_heading']==b['source_heading']:
                relation='HAS_SAME_SECTION_REASSESSMENT_CONTEXT'
            if relation:edges.append({'from':a['chunk_id'],'to':b['chunk_id'],'relation':relation,'clinical_review_status':'pending'})
    return {'nodes':nodes,'edges':edges,'clinical_review_status':'pending',
            'semantics':'Publisher headings, explicit shared conditions and source roles; engineering context links, not causal or treatment assertions.'}


def marker_history(patient,history):
    current=patient.get('age_hours');times=[];values=[]
    for row in history:
        time=row.get('age_hours')
        if type(time) not in (int,float) or not math.isfinite(time) or type(current) not in (int,float) or not 0<=time<current:
            raise ValueError('History must contain recorded times strictly before the current assessment')
        if time in times:raise ValueError('Duplicate history time')
        times.append(time)
        value=row.get('crp',row.get('crp_level'))
        if type(value) in (int,float) and math.isfinite(value):values.append(value)
    value=patient.get('crp',patient.get('crp_level'))
    if type(value) in (int,float) and math.isfinite(value):values.append(value)
    return len(values)>=2


def validate_graph(graph,corpus):
    """Reject stale, cross-document or altered context links before selection."""
    nodes={}
    for node in graph['nodes']:
        cid=node['chunk_id']
        if cid in nodes or cid not in corpus:raise ValueError('Unknown or duplicate source context node')
        source=corpus[cid]
        if hashlib.sha256(source['raw_text'].encode()).hexdigest()!=node['text_sha256']:
            raise ValueError('Source context graph hash mismatch')
        if (node['guideline'],node['pdf_sha256'])!=(source['guideline_id'],source['pdf_sha256']):
            raise ValueError('Source context graph provenance mismatch')
        if set(node['roles'])!=roles(source) or node['source_heading']!=source.get('retrieval_headings',{}):
            raise ValueError('Source context graph role or heading mismatch')
        nodes[cid]=node
    seen=set()
    for edge in graph['edges']:
        a,b=edge['from'],edge['to'];relation=edge['relation']
        if a not in nodes or b not in nodes or a==b:raise ValueError('Unknown source context edge endpoint')
        key=(a,b,relation)
        if key in seen:raise ValueError('Duplicate source context edge')
        seen.add(key)
        na,nb=nodes[a],nodes[b]
        if (na['guideline'],na['pdf_sha256'])!=(nb['guideline'],nb['pdf_sha256']):
            raise ValueError('Cross-document source context edge')
        ar,br=set(na['roles']),set(nb['roles'])
        valid=(relation=='HAS_INTERPRETATION_LIMIT' and 'serial_marker' in ar and 'marker_limit' in br)
        valid|=(relation=='SHARES_TREATMENT_START_CONTEXT' and 'serial_marker' in ar and 'sampling_prerequisite' in br
            and all('when starting antibiotic treatment' in normalize(corpus[c]['raw_text']) for c in [a,b]))
        valid|=(relation=='HAS_SAME_SECTION_REASSESSMENT_CONTEXT' and 'marker_limit' in ar and 'clinical_reassessment' in br
                and na['source_heading']==nb['source_heading'])
        if not valid:raise ValueError('Unsupported source context relation')


def select_context(order,corpus,graph,query,patient,history,*,use_graph=True,include_history=True):
    """Return one stable order (prefixes at 4 and 8), with a source-only trace."""
    validate_graph(graph,corpus)
    allowed=[i for i in dict.fromkeys(order) if applicable(corpus[i]['scope'],patient) and admission(corpus[i],query,patient)[0]]
    trace=[];selected=[];deferred=[]
    q=normalize(query)
    initial=bool(re.search(r'initial|baseline|before.*antibiotic',q)) and bool(re.search(r'investigation|diagnostic|test|culture|marker|crp|inflamm',q))
    def add(cid,reason):
        if cid in allowed and cid not in selected:
            selected.append(cid);trace.append({'chunk_id':cid,'reason':reason})
    def context(cid,reason):
        if len(selected)<4:add(cid,reason)
        elif cid in allowed and cid not in selected and not any(i==cid for i,_ in deferred):deferred.append((cid,reason))
    functions=query_functions(query)
    summaries=[i for i in allowed if summary_function(corpus[i]) in functions]
    # Explicit publisher conclusions anchor the case discussion; details retain
    # separate slots. Unrequested treatment summaries are not auto-promoted.
    for function in functions:
        options=[i for i in summaries if summary_function(corpus[i])==function]
        if options and len(selected)<2:add(options[0],'publisher_summary:'+function)
    for cid in summaries:
        if len(selected)<2:add(cid,'additional_requested_publisher_summary')
    if selected:
        for cid in allowed:
            if summary_function(corpus[cid]) is None and len(selected)<4:add(cid,'supporting_source_detail')
    else:
        for cid in allowed[:2 if initial else 3]:add(cid,'question_relevance_head')
    # A publisher's general clinical-judgement paragraph is contextual safety
    # information, not an assertion that the current infant is unwell.
    general=[i for i in allowed if 'general_clinical_context' in roles(corpus[i])]
    if general and general[0] not in selected:
        if len(selected)>=4:selected.pop();trace.pop()
        add(general[0],'publisher_general_clinical_context')
    if use_graph and not summaries:
        # Expand from the original relevance head, never from gold annotations.
        seeds=list(selected[:2]);pending=[]
        for _ in range(2):
            for edge in graph['edges']:
                if edge['from'] not in seeds:continue
                if edge['relation']=='SHARES_TREATMENT_START_CONTEXT' and not initial:continue
                if edge['to'] not in seeds and edge['to'] not in pending:pending.append(edge['to'])
            seeds+=pending
        priority={'marker_limit':0,'sampling_prerequisite':1,'clinical_reassessment':2}
        pending.sort(key=lambda i:min([priority[r] for r in roles(corpus[i]) if r in priority] or [9]))
        for cid in pending:
            context(cid,'source_qualification_graph')
        history_needed=bool(re.search(r'uncertain|unavailable|missing|serial|trend|subsequent|falling|rising|crp|inflamm',q))
        if include_history and history_needed and not initial and marker_history(patient,history):
            for role in ['clinical_reassessment','serial_marker']:
                for cid in allowed:
                    if role in roles(corpus[cid]):context(cid,'recorded_serial_marker_context:'+role)
    # Extension is prefix-stable: requesting eight never rearranges the first
    # four discussion priorities. No source or observation is invented.
    for cid,reason in deferred:
        if len(selected)<8:add(cid,reason)
    for cid in allowed:
        if len(selected)<8:add(cid,'remaining_relevant_context')
    return selected,trace
