"""Topic-specific source proposals; no gold input and no automatic approval."""
import re,copy
from rank_bm25 import BM25Plus
from rag.section_evidence_v20 import TOPICS

TOPIC_CUES={
'investigations':r'blood culture|CSF|cerebrospinal|IMCI|physical exam|vital signs|diagnos',
'antibiotic_review':r'antibiotic|antimicrobial|ampicillin|gentamicin|penicillin|amoxicillin',
'escalation_criteria':r'ill|clinical indicator|risk factor|critical|red.flag|deteriorat',
'monitoring_plan':r'reassess|serial.{0,20}examin|observ|monitor|clinical assessment',
'recommended_actions':r'assess|examin|refer|treat|review|investigat'}
ACTION_CUE=r'\b(?:should|must|perform|review|reassess|consider|refer|recommended|recommend|start|treat|evaluate|require|monitor|examine|assess)\w*\b'

def eligible_topic(text,section):
    if len(re.findall(r'\w+',text))<12:return False
    if not re.search(TOPIC_CUES[section],text,re.I):return False
    if not re.search(ACTION_CUE,text,re.I):return False
    # Model development/validation by itself is not a clinical action.
    return True

def propose(raw,packet,max_per_topic=1):
    if not isinstance(raw,dict)or set(raw)!={'claims'}or not isinstance(raw['claims'],list):return raw,[]
    result=copy.deepcopy(raw);claims=result['claims'];used={c.get('id')for c in claims if isinstance(c,dict)};trace=[]
    tokenize=lambda s:re.findall(r'\w+',s.lower())
    for topic in sorted(TOPIC_CUES):
        eligible=[e for e in packet['evidence']if e.get('kind')!='supplemental_publisher_definition'and eligible_topic(e['text'],topic)]
        if not eligible:continue
        query=TOPICS[topic]
        exposure=packet.get('patient',{}).get('antibiotic_exposure_hours',packet.get('patient',{}).get('antibiotic_duration_hours'))
        if topic=='recommended_actions'and isinstance(exposure,(int,float))and exposure>0:
            query='regularly reassess clinical condition review ongoing antibiotic treatment progress results investigations'
        bm=BM25Plus([tokenize(e['text'])for e in eligible]);scores=bm.get_scores(tokenize(query))
        added=0
        for i in sorted(range(len(eligible)),key=lambda i:(-scores[i],eligible[i]['id'])):
            e=eligible[i];support=[{'quote_id':e['id']+'Q1'}]
            if scores[i]<=0 or any(c.get('section')==topic and c.get('support')==support for c in claims if isinstance(c,dict)):continue
            empty=[c for c in claims if isinstance(c,dict)and c.get('section')==topic and c.get('support')==[]]
            for c in empty:claims.remove(c);used.discard(c.get('id'))
            cid=next((f'C{k}'for k in range(1,17)if f'C{k}'not in used),None)
            if not cid or len(claims)>=16:break
            claims.append({'id':cid,'section':topic,'support':support});used.add(cid);added+=1
            trace.append({'section':topic,'evidence_id':e['id'],'requires_fresh_dual_audit':True,'score':float(scores[i])})
            if added>=max_per_topic:break
    return result,trace
