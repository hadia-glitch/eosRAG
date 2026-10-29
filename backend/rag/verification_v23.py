"""Next candidate; fresh generation/audits required, no previous metric promotion."""
from rag.verification_core_v23 import run_verification as core
from rag.section_proposals_v23 import propose
from rag.offline_repairs_v23 import repair_rendering
from services.groq_client import complete_json

def run_verification(packet,settings,llm=complete_json):
    proposals=[]
    def proposing(prompt,settings,**kw):
        raw=llm(prompt,settings,**kw)
        if 'synthesis'in kw.get('role',''):
            raw,trace=propose(raw,packet);proposals.extend(trace)
        return raw
    result=core(packet,settings,proposing)
    result=repair_rendering(result,packet)
    result['section_coverage_proposals']=proposals
    result['verification_version']='offline-fixes-v23-pending-fresh-evaluation'
    return result
