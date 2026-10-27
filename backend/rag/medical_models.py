"""NCBI MedCPT asymmetric encoders and reranker for development.

Use CLS representations and query/article input conventions from the model
authors. Models stay frozen. Biomedical pretraining does not validate clinical
recommendations; source admission and independent audits remain necessary.
"""
import numpy as np


class MedCPT:
    def __init__(self):
        from transformers import AutoModel,AutoTokenizer,AutoModelForSequenceClassification
        self.models={};self.tokenizers={};self.revisions={}
        for role,repo in [('query','ncbi/MedCPT-Query-Encoder'),('article','ncbi/MedCPT-Article-Encoder'),('cross','ncbi/MedCPT-Cross-Encoder')]:
            self.tokenizers[role]=AutoTokenizer.from_pretrained(repo)
            loader=AutoModelForSequenceClassification if role=='cross' else AutoModel
            self.models[role]=loader.from_pretrained(repo).eval()
            self.revisions[repo]=getattr(self.models[role].config,'_commit_hash',None)

    def _encode(self,items,role,max_length,batch_size=16):
        import torch
        rows=[]
        with torch.inference_mode():
            for start in range(0,len(items),batch_size):
                encoded=self.tokenizers[role](items[start:start+batch_size],padding=True,truncation=True,
                                             max_length=max_length,return_tensors='pt')
                rows.append(self.models[role](**encoded).last_hidden_state[:,0,:].cpu().numpy())
        return np.concatenate(rows) if rows else np.empty((0,768),dtype=np.float32)

    def query_vectors(self,queries):
        return self._encode(queries,'query',64)

    def article_vectors(self,title_text_pairs):
        return self._encode(title_text_pairs,'article',512)

    def predict(self,pairs,batch_size=16,show_progress_bar=False):
        import torch
        values=[]
        with torch.inference_mode():
            for start in range(0,len(pairs),batch_size):
                encoded=self.tokenizers['cross']([list(p) for p in pairs[start:start+batch_size]],padding=True,
                                                truncation=True,max_length=512,return_tensors='pt')
                values.extend(self.models['cross'](**encoded).logits[:,0].cpu().tolist())
        return values
