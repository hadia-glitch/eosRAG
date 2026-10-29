"""Research-only source/topic coverage supplement; no gold/reference inputs."""
import re
import numpy as np
from rank_bm25 import BM25Plus
from rag.clinical_scope import applicable
from rag.guidance_lanes import guidance_role
from rag.source_scope import late_only
from rag.topic_scope import current_case_topic

TOPICS={
 'recommended_actions':'perform immediate clinical assessment review history physical examination vital signs referral hospital',
 'investigations':'blood culture diagnosis infection bedside assessment examination clinical signs IMCI identification further evaluation',
 'antibiotic_review':'review antibiotics continuing beyond 36 hours negative culture clinical condition reassuring CRP trends exceptions',
 'monitoring_plan':'regularly reassess clinical condition observations investigations clinical progress',
 'escalation_criteria':'clinical indicators red flag risk factors framework antibiotic management start treatment urgent referral hospital critical illness',
 'nutrition_fluids':'breastfeeding expressing breast milk feeding support',
 'parent_communication_notes':'discuss parents carers caregiver reasons treatment risks benefits observations investigations',
 'follow_up':'follow up discharge pending results handover review after treatment'}


def augment(packet,corpus,guideline,max_additional=6):
    patient=packet['patient'];eligible=[]
    for c in corpus:
        if c.get('guideline_id')!=guideline or not guidance_role(c) or not applicable(c.get('scope',{}),patient):continue
        text=c.get('raw_text',c['text']);head=c.get('retrieval_headings') or {}
        if late_only(text,head.get('parent_heading','')):continue
        ok,_=current_case_topic({**c,'raw_text':text},' '.join(TOPICS.values()),patient)
        if not ok:continue
        if patient.get('referral_possible') is True and re.search(r'referral.{0,35}(?:not possible|not feasible)',text,re.I):continue
        exposure=patient.get('antibiotic_exposure_hours',patient.get('antibiotic_duration_hours'))
        if exposure is not None and exposure>0 and re.search(r'before\s+(?:giving\s+)?(?:the\s+)?first\s+(?:antibiotic\s+)?dose',text,re.I):continue
        eligible.append(c)
    if not eligible:return packet,{'added':[],'reason':'No eligible source/topic supplements'}
    tokens=lambda s:re.findall(r'\w+',s.lower())
    bm=BM25Plus([tokens(c.get('raw_text',c['text'])) for c in eligible]);votes=np.zeros(len(eligible));anchors=[]
    for topic,query in TOPICS.items():
        scores=bm.get_scores(tokens(query));order=np.argsort(-scores)
        # Fixed RRF60 ranks; the source text and entire recommendation stay intact.
        for rank,i in enumerate(order):
            if scores[i]>0:votes[i]+=1/(60+rank+1)
        if len(order) and scores[order[0]]>0:anchors.append((topic,int(order[0])))
    known={e['chunk_id'] for e in packet['evidence']};selected=[];trace=[]
    for topic,i in anchors:
        c=eligible[i]
        if c['chunk_id'] not in known and len(selected)<max_additional:
            selected.append(c);known.add(c['chunk_id']);trace.append({'section_query':topic,'chunk_id':c['chunk_id'],'selection':'section_anchor'})
    if len(selected)<max_additional:
        for i in np.argsort(-votes):
            if votes[i]<=0 or len(selected)>=max_additional:break
            c=eligible[i]
            if c['chunk_id'] not in known:selected.append(c);known.add(c['chunk_id']);trace.append({'chunk_id':c['chunk_id'],'selection':'RRF60_supplement'})
    evidence=list(packet['evidence'])
    for c in selected:
        evidence.append({'id':f'E{len(evidence)+1}','chunk_id':c['chunk_id'],'text':c.get('raw_text',c['text']),
            'source':c['source'],'version':c['version'],'section':(c.get('retrieval_headings') or {}).get('section_heading',''),
            'page_number':c.get('pdf_page'),'kind':'section_coverage_supplement'})
    return {**packet,'evidence':evidence},{'added':trace,'original_evidence_count':len(packet['evidence']),'supplement_count':len(selected),'max_additional':max_additional,'rrf_k':60,'gold_inputs_used':False,'clinical_approval':False}
