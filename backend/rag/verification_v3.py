"""Lossless audit-prompt deduplication around the unchanged fail-closed gate."""
import json
from rag.verification_v2 import run_verification as contracted_verification, evidence_packet
from services.groq_client import complete_json


def compact_auditor(llm):
    def call(prompt,settings,**kwargs):
        if 'auditor' not in kwargs.get('role',''):
            return llm(prompt,settings,**kwargs)
        p=json.loads(prompt)
        sources={e['id']:e['text'] for e in p['source_packet']['evidence']}
        changed=False
        for claim in p['claims']:
            support=claim.get('support',[])
            if len(support)!=1:continue
            eid=support[0].get('evidence_id')
            if eid in sources and ' '.join(claim.get('text','').split())==' '.join(sources[eid].split()):
                # The complete claim is already present verbatim once. No
                # source, condition, patient fact or clinical assertion is cut.
                claim.pop('text')
                claim['text_ref']={'evidence_id':eid,'span':'COMPLETE_PASSAGE_VERBATIM'}
                changed=True
        if changed:
            p['lossless_text_reference_contract']=(
                'For each claim with text_ref, its complete statement is exactly '
                'the full text of source_packet.evidence with that evidence_id. '
                'Read that full passage as the claim, including every condition, '
                'and audit its patient applicability. This is an exact-text '
                'reference, not permission to skip a claim. All source passages '
                'and all patient/history facts remain supplied.'
            )
            if len(p['claims'])<=6:kwargs['completion_tokens']=1600
            prompt=json.dumps(p)
        return llm(prompt,settings,**kwargs)
    return call


def run_verification(packet,settings,llm=complete_json):
    result=contracted_verification(packet,settings,compact_auditor(llm))
    result['verification_version']='lossless-full-passage-references-v3'
    return result
