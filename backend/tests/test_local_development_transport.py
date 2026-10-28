import pytest
from rag.local_development_transport import LocalDevelopmentClient
from services.groq_client import GenerationUnavailable

META={'model_info':{'qwen3.context_length':40960},'template':'template'}


def test_oversized_input_is_rejected_before_a_request():
    def forbidden(**kwargs):
        raise AssertionError('A rejected packet must not be sent')
    client=LocalDevelopmentClient('pinned',META,client_factory=forbidden)
    with pytest.raises(GenerationUnavailable,match='budget exceeded'):
        client('x'*32768,None,role='Rank only',response_schema={})


def test_local_request_has_schema_no_proxy_and_no_cloud_fallback():
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'done':True,'done_reason':'stop','message':{'content':'{"choices":[]}'},'prompt_eval_count':12,'eval_count':4}
    class Fake:
        def __init__(self,**kwargs):assert kwargs['trust_env'] is False
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,**kwargs):
            assert url=='http://127.0.0.1:11434/api/chat'
            p=kwargs['json']
            assert p['think'] is False and p['options']['seed']==31 and p['format']=={'type':'object'}
            assert 'headers' not in kwargs
            return Response()
    client=LocalDevelopmentClient('pinned',META,client_factory=Fake)
    assert client('Rank source IDs',None,role='Rank only',response_schema={'type':'object'})=={'choices':[]}
    assert client.calls[0]['groq_calls']==0


def test_remote_endpoint_is_not_admitted():
    with pytest.raises(ValueError,match='loopback'):
        LocalDevelopmentClient('pinned',META,base='https://example.com')
