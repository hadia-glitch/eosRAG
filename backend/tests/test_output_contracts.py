import json
import httpx
from config import Settings
from rag.output_contracts import constrained_schema
from rag.verification_graph import IndexedDraft,Verdict
from services.groq_client import complete_json

def test_constrained_quote_and_claim_id_enums_use_only_packet_ids():
    schema=constrained_schema(IndexedDraft,quote_ids={'E1Q1','E2Q3'})
    assert schema['$defs']['QuoteReference']['properties']['quote_id']['enum']==['E1Q1','E2Q3']
    verdict=constrained_schema(Verdict,claim_ids={'C1','C3'})
    assert verdict['properties']['rejected_claim_ids']['items']['enum']==['C1','C3']
    def check(node):
        if isinstance(node,dict):
            if node.get('type')=='object':
                assert node.get('additionalProperties') is False
                assert set(node['required'])==set(node['properties'])
            for child in node.values():check(child)
        elif isinstance(node,list):
            for child in node:check(child)
    check(schema);check(verdict)

def test_strict_schema_is_sent_to_provider_without_silent_mode_fallback(monkeypatch):
    requests=[]
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{"ok":true}'}}]})
    original=httpx.Client
    monkeypatch.setattr(httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(handler)))
    schema={'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok'],'additionalProperties':False}
    complete_json('Synthetic fixture',Settings(_env_file=None,groq_api_key='synthetic'),role='Transport fixture',response_schema=schema)
    assert requests[0]['response_format']=={'type':'json_schema','json_schema':{'name':'neoguard_response','strict':True,'schema':schema}}
