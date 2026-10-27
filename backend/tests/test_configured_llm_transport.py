import httpx
from types import SimpleNamespace
from config import Settings
from services.groq_client import complete_json,GenerationUnavailable
import pytest


def test_ollama_never_receives_groq_credentials_or_falls_back(monkeypatch):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{"ok":true}'}}]})
    original=httpx.Client
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler)))
    settings=Settings(_env_file=None,llm_provider='ollama',disable_cloud_llm_fallback=True,
                      groq_api_key='synthetic-never-send',local_llm_model='synthetic-local-model')
    assert complete_json('Synthetic fixture',settings,role='Research fixture')=={'ok':True}
    assert str(calls[0].url)=='http://localhost:11434/v1/chat/completions'
    assert 'authorization' not in calls[0].headers
    assert b'synthetic-never-send' not in calls[0].content


def test_disabled_cloud_does_not_call_transport(monkeypatch):
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:(_ for _ in ()).throw(AssertionError('No transport permitted')))
    with pytest.raises(GenerationUnavailable):
        complete_json('Synthetic fixture',Settings(_env_file=None,llm_provider='groq',disable_cloud_llm_fallback=True),role='fixture')
