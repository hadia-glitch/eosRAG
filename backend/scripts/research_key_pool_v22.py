"""Use only explicitly user-supplied keys; bounded rotation on provider 429."""
import re,time,threading
from pathlib import Path
from dotenv import dotenv_values
from services.groq_client import GenerationUnavailable

class ResearchKeyPool:
    def __init__(self,base,env_file):
        self.base=base;v=dotenv_values(env_file);active=v.get('GROQ_API_KEY');self.slots=[]
        seen=set()
        for name,key in [('primary',active)]+[(n,k)for n,k in v.items()if re.fullmatch(r'gro[qk][1-5]',n,re.I)]:
            if key and key not in seen:self.slots.append((name,key));seen.add(key)
        self.index=0;self.blocked=set();self.cooldown={};self.events=[];self.lock=threading.Lock()
    def __call__(self,prompt,settings,**kw):
        last=None
        for _ in range(len(self.slots)):
            with self.lock:
                idx=self.index;self.index=(self.index+1)%len(self.slots)
            if idx in self.blocked or self.cooldown.get(idx,0)>time.monotonic():continue
            name,key=self.slots[idx]
            try:return self.base(prompt,settings.model_copy(update={'groq_api_key':key}),**kw)
            except GenerationUnavailable as exc:
                if exc.code!='http_429':raise
                last=exc;response=getattr(exc.__cause__,'response',None);message=''
                if response is not None:
                    try:message=str(response.json().get('error',{}).get('message','')).lower()
                    except ValueError:pass
                daily='tokens per day'in message or'(tpd)'in message
                if daily:self.blocked.add(idx)
                else:self.cooldown[idx]=time.monotonic()+(exc.retry_after_seconds or 30)
                self.events.append({'slot':name,'daily_exhausted':daily,'model':kw.get('model',settings.groq_model)})
                print('Key pool:',name,'daily quota exhausted'if daily else'minute cooldown',flush=True)
        if len(self.blocked)==len(self.slots):raise GenerationUnavailable('All authorized daily quotas exhausted','authorized_quota_exhausted')
        if last:raise last
        raise GenerationUnavailable('All authorized keys cooling down or exhausted','http_429',45)
