"""Fresh reference metrics for saved Dense/Hybrid plans, with resumable output."""
import argparse,hashlib,importlib.metadata,json,os
from pathlib import Path
os.environ.setdefault('HF_HUB_OFFLINE','1')
os.environ.setdefault('TRANSFORMERS_OFFLINE','1')

def save(path,x):
    tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(x,indent=2)+'\n');tmp.replace(path)

def main(source,target):
    import torch
    torch.set_num_threads(2)
    import sacrebleu
    from nltk.tokenize import wordpunct_tokenize
    from nltk.translate.meteor_score import meteor_score
    from rouge_score import rouge_scorer
    from bert_score import BERTScorer
    x=json.loads(source.read_text());cases={c['case_id']:c for c in x['cases']}
    state=json.loads(target.read_text()) if target.exists() else {'records':[]}
    state['input_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    state['config']={'bleu':'sacreBLEU sentence BLEU-4 /100; 13a tokenizer; exp smoothing; effective_order=False',
        'meteor':'NLTK WordPunct lowercased; Porter and WordNet default matching',
        'bertscore':'DistilBERT base uncased, layer5, no IDF or baseline rescaling; standard 512-token truncation disclosed per pair',
        'clinical_interpretation':'Similarity to a template is not clinical correctness; full text assessed separately by LLM judge',
        'packages':{k:importlib.metadata.version(k) for k in ['torch','transformers','bert-score','nltk','sacrebleu','rouge-score']}}
    rouge=rouge_scorer.RougeScorer(['rougeL'],use_stemmer=True)
    for row in x['generation']:
        if any(r['case_id']==row['case_id'] and r['arm']==row['arm'] for r in state['records']):continue
        text=row['generated_text'];reference=cases[row['case_id']]['reference_text']
        state['records'].append({'case_id':row['case_id'],'arm':row['arm'],
            'candidate_sha256':hashlib.sha256(text.encode()).hexdigest(),
            'reference_sha256':hashlib.sha256(reference.encode()).hexdigest(),
            'bleu':float(sacrebleu.sentence_bleu(text,[reference],tokenize='13a',smooth_method='exp',use_effective_order=False).score/100),
            'meteor':float(meteor_score([wordpunct_tokenize(reference.lower())],wordpunct_tokenize(text.lower()))),
            'rouge_l':float(rouge.score(reference,text)['rougeL'].fmeasure)})
        save(target,state)
    print('Fresh BLEU/METEOR/ROUGE complete: '+str(len(state['records'])),flush=True)
    bert=BERTScorer(model_type='distilbert-base-uncased',num_layers=5,device='cpu',idf=False,rescale_with_baseline=False,batch_size=1)
    state['config']['bertscore_hash']=bert.hash
    for record in state['records']:
        if 'bertscore_f1' in record:continue
        row=next(r for r in x['generation'] if r['case_id']==record['case_id'] and r['arm']==record['arm'])
        text=row['generated_text'];reference=cases[row['case_id']]['reference_text']
        ct=len(bert._tokenizer.encode(text,truncation=False));rt=len(bert._tokenizer.encode(reference,truncation=False))
        p,r,f=bert.score([text],[reference])
        record.update(bertscore_precision=float(p[0]),bertscore_recall=float(r[0]),bertscore_f1=float(f[0]),
            candidate_tokens=ct,reference_tokens=rt,standard_bertscore_truncated=ct>512 or rt>512)
        save(target,state);print('BERTScore saved '+record['case_id']+' '+record['arm'],flush=True)
    state['complete']=len(state['records'])==20 and all('bertscore_f1' in r for r in state['records'])
    state['truncated_pairs']=sum(r['standard_bertscore_truncated'] for r in state['records'])
    save(target,state)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();main(a.input,a.output)
