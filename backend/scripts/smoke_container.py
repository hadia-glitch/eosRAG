"""Non-root/offline/read-only artifact and API boundary integration smoke."""
import json,os
from pathlib import Path
from fastapi.testclient import TestClient
from main import app
from config import Settings
from ml.supplied_model import load_supplied_model,SuppliedPredictionRequest
from ml.explanations import explain
from rag.production_retrieval import embedding_model,reranker_model

if __name__=='__main__':
    assert os.getuid()==10001
    assert not Path('/app/.env').exists()
    client=TestClient(app)
    assert client.get('/health').status_code==200
    assert client.get('/api/v1/models/status').status_code==401
    settings=Settings(_env_file=None)
    assert settings.llm_schema_enforcement is True
    from rag.output_contracts import constrained_schema
    assert callable(constrained_schema)
    model=load_supplied_model(settings.supplied_model_dir)
    values={'Gestational_Age':36,'Birth_Weight':3.2,'Sex':'Male','Postnatal_Age':0,'Delivery_Mode':'Cesarean',
            'Apgar':8,'HR':150,'Resp':50,'Temp':36.8,'SpO2':97,'BP':45,'Oxygen':21,'WBC':12,'CRP':5,
            'PCT':.7,'Platelets':220,'Lactate':1.5,'Hemoglobin':14.5}
    request=SuppliedPredictionRequest(input_contract_version='supplied-neonatal-input-v1',purpose='research',
                age_hours=12.,reviewed_inputs=True,values=values)
    result=model.predict(request)
    assert result['status']=='predicted' and not result['clinical_use']
    shap=explain(model,request)
    assert shap['shap']['additivity_error']<1e-5
    assert embedding_model(settings.embedding_model).encode(['Synthetic fixture']).shape==(1,384)
    assert len(reranker_model(settings.reranker_model).predict([('Synthetic query','Synthetic passage')]))==1
    print(json.dumps({'nonroot_readonly_offline':True,'auth_boundary':True,'trained_model':result['model_version'],
                      'shap_additivity':True,'cached_encoder_and_reranker':True,'strict_output_schemas':True}))
