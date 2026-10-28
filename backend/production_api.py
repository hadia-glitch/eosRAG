"""Authenticated EOS research API. Clinical release is an explicit gate."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field,ConfigDict

from config import get_settings
from db import get_supabase
from ml.features import PredictionRequest
from ml.inference import ModelUnavailable, model_status, predict
from ml.supplied_model import SuppliedPredictionRequest,load_supplied_model,supplied_status
from ml.longitudinal_inputs import LongitudinalInputs,contract as longitudinal_contract,preview as longitudinal_preview
from ml.research_selection import status as selected_research_status,longitudinal_contract as selected_longitudinal_contract,predict_pic
from rag.evidence_policy import load_manifest
from rag.patient_context_builder import build_patient_context
from rag.production_retrieval import retrieve
from schemas import (CarePlanRequest, ClinicalCarePlanResponse, EncounterEvidenceRequest,
                     EvidenceChunkResponse, EvidenceSearchRequest, ExplanationResponse,PatientSnapshot)
from services.clinical_pipeline import explanation_from_plan, produce
from services.security import require_admin, require_encounter, require_user
from services.decision_audit import record_decision

logger = logging.getLogger("neoguard")
settings = get_settings()
app = FastAPI(title="NeoGuard EOS Research API", version="2.0.0", redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=[s.strip() for s in settings.cors_origins.split(",") if s.strip() and s.strip() != "*"],
                   allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "X-Request-ID"])


class RequestBoundary:
    """Bound streamed bodies too; Content-Length alone is not a size limit."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id, total, messages = str(uuid.uuid4()), 0, []
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            total += len(message.get("body", b""))
            if total > get_settings().max_request_bytes:
                return await JSONResponse({"detail": "Request body too large", "request_id": request_id}, status_code=413)(scope, receive, send)
            messages.append(message)
            if not message.get("more_body"):
                break
        index = 0
        async def replay():
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return await receive()
        async def with_headers(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-request-id", request_id.encode()), (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"), (b"referrer-policy", b"no-referrer")]
            await send(message)
        await self.app(scope, replay, with_headers)


app.add_middleware(RequestBoundary)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.error("request_failed exception_type=%s", type(exc).__name__)
    return JSONResponse({"detail": "Service unavailable; retry or contact the administrator"}, status_code=503, headers={"Cache-Control": "no-store"})


@app.get("/health")
def health():
    return {"status": "ok", "service": "neoguard-eos", "version": "2.0.0", "clinical_use_enabled": get_settings().clinical_use_enabled}


@app.get("/ready")
def ready(user=Depends(require_admin)):
    current = get_settings()
    docs, version = load_manifest(current)
    reviewed = sum(bool(d.get("approved_for_generation")) for d in docs)
    try:
        get_supabase().table("guideline_documents").select("id").limit(1).execute()
        database = True
    except Exception:
        database = False
    model = model_status(current)
    providers={current.llm_provider,current.verifier_provider or current.llm_provider}
    requires_cloud=any(p!='ollama' for p in providers)
    provider_configured=(providers <= {'groq','ollama'} and
        ('ollama' not in providers or bool(current.local_llm_base_url and current.local_llm_model)) and
        ('groq' not in providers or bool(current.groq_api_key and not current.disable_cloud_llm_fallback)))
    ok = database and bool(reviewed) and provider_configured
    return JSONResponse({"status": "ready" if ok else "not_ready", "database": database,
                         "model": model, "reviewed_documents": reviewed, "corpus_version": version,
                         "clinical_ready": bool(ok and model["clinical_ready"] and (not requires_cloud or current.allow_clinical_cloud_processing))}, status_code=200 if ok else 503)


@app.get("/api/v1/mobile/config")
def mobile_config():
    current = get_settings()
    if not current.supabase_url or not current.supabase_anon_key:
        raise HTTPException(503, "Public client configuration unavailable")
    return {"supabase_url": current.supabase_url, "supabase_anon_key": current.supabase_anon_key}


@app.get("/api/v1/models/status")
def models_status(user=Depends(require_user)):
    return {**model_status(get_settings()),'research_model':selected_research_status(get_settings())}


@app.get('/api/v1/research/model/status')
def research_model_status(user=Depends(require_user)):
    return selected_research_status(get_settings())


@app.get('/api/v1/research/longitudinal/contract')
def longitudinal_input_contract(user=Depends(require_user)):
    return selected_longitudinal_contract(get_settings())


@app.post('/api/v1/research/longitudinal/preview')
def longitudinal_input_preview(body:LongitudinalInputs,user=Depends(require_user)):
    # Input alignment and observed trends only. The new PIC model fails its
    # quality gate and is deliberately absent from the clinical prediction path.
    return longitudinal_preview(body)


@app.post('/api/v1/research/model/predict')
def research_model_predict(body:SuppliedPredictionRequest,user=Depends(require_user)):
    if get_settings().research_ml_model!='kaggle':raise HTTPException(409,'PIC is selected; use the longitudinal input screen.')
    try:
        result=load_supplied_model(get_settings().supplied_model_dir).predict(body)
    except ModelUnavailable as exc:
        raise HTTPException(503,str(exc))
    try:
        record_decision(user,'research_model_inference',result)
        result['audit_status']='recorded'
    except HTTPException:
        if get_settings().research_prediction_requires_audit:raise
        # An isolated research estimate may be demonstrated without the clinical
        # audit dependency. Clinical inference/care plans remain fail closed.
        result['audit_status']='unavailable'
        result['warnings'].append('Research prediction was not saved to the server audit. Clinical use remains disabled.')
    return result


@app.post('/api/v1/research/model/explain')
def research_model_explain(body:SuppliedPredictionRequest,user=Depends(require_user)):
    if get_settings().research_ml_model!='kaggle':raise HTTPException(409,'PIC is selected; use the longitudinal research explanation.')
    from ml.explanations import explain
    try:
        result=explain(load_supplied_model(get_settings().supplied_model_dir),body)
    except (ImportError,RuntimeError,ValueError) as exc:
        raise HTTPException(503,'Local SHAP explanation unavailable; no substitute attribution is labeled as SHAP') from exc
    try:
        record_decision(user,'research_model_shap',result)
        result['audit_status']='recorded'
    except HTTPException:
        if get_settings().research_prediction_requires_audit:raise
        result['audit_status']='unavailable'
        result['warnings'].append('Research explanation was not saved to the server audit.')
    return result


@app.post('/api/v1/research/longitudinal/predict')
def longitudinal_research_predict(body:LongitudinalInputs,user=Depends(require_user)):
    try:result=predict_pic(body,get_settings())
    except ModelUnavailable as exc:raise HTTPException(503,str(exc))
    try:
        record_decision(user,'pic_research_inference',result)
        result['audit_status']='recorded'
    except HTTPException:
        if get_settings().research_prediction_requires_audit:raise
        result['audit_status']='unavailable'
    return result


@app.post("/api/v1/risk/predict")
def risk_predict(body: PredictionRequest, user=Depends(require_user)):
    try:
        result = predict(body, get_settings())
        record_decision(user, "model_inference", result)
        return result
    except ModelUnavailable as exc:
        raise HTTPException(503, str(exc))


def search(query, guideline, limit=8, *, patient=None):
    if guideline not in {"NICE", "AAP", "WHO"}:
        raise HTTPException(422, "Select NICE, AAP or WHO")
    return retrieve(query, guideline, limit, get_settings(),patient=patient)


def encounter_scope(patient,encounter):
    """Stored encounter facts take precedence over client population claims."""
    patient=dict(patient)
    birth=encounter.get('birth_date_time')
    if birth:
        try:
            born=datetime.fromisoformat(str(birth).replace('Z','+00:00'))
            patient['age_hours']=(datetime.now(timezone.utc)-born).total_seconds()/3600
        except (ValueError,TypeError):patient.pop('age_hours',None)
    for stored,key,factor in [('gestational_age_days','gestational_age_weeks',1/7),('birth_weight_g','birth_weight_g',1)]:
        if encounter.get(stored) is not None:
            try:
                import math
                value=float(encounter[stored])*factor
                if not math.isfinite(value) or value<=0:raise ValueError()
                patient[key]=value
            except (TypeError,ValueError):patient.pop(key,None)
    return patient


@app.post("/api/v1/evidence/search", response_model=list[EvidenceChunkResponse])
def evidence_search(body: EvidenceSearchRequest, user=Depends(require_user)):
    query = body.query
    patient=None
    if body.encounter_id:
        encounter=require_encounter(body.encounter_id, user)
        context = build_patient_context(body.encounter_id)
        if context.load_error:raise HTTPException(503,'Patient history unavailable; patient-specific retrieval withheld')
        patient=encounter_scope(context.current_snapshot,encounter)
        query += " " + " ".join(context.query_context_terms())
    if body.source_filters and body.active_guideline not in body.source_filters and "ALL" not in body.source_filters:
        return []
    return [EvidenceChunkResponse(**c.to_dict()) for c in search(query, body.active_guideline, body.limit,patient=patient).chunks]


class EvidenceAiRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query: str = Field(min_length=2, max_length=2000)
    active_guideline: str = "NICE"
    # Client passages are ignored. Retrieve sources on the server.
    chunks: list[dict] = Field(default_factory=list, max_length=40)
    patient_context: PatientSnapshot | None = None


@app.post("/api/v1/evidence/overview")
def evidence_overview(body: EvidenceAiRequest, user=Depends(require_user)):
    return {"overview": "", "generated_by_ai": False, "verification_status": "source_excerpts_only"}


@app.post("/api/v1/evidence/cards")
def evidence_cards(body: EvidenceAiRequest, user=Depends(require_user)):
    retrieval = search(body.query, body.active_guideline)
    docs, _ = load_manifest(get_settings())
    urls = {d["file_name"]: d.get("url", "") for d in docs}
    return {"cards": [{"index": i, "headline": c.section, "processed_answer": "", "exact_excerpt": c.chunk_text,
                        "source": c.source_name, "section": c.section, "document_url": urls.get(c.file_name, "")}
                       for i, c in enumerate(retrieval.chunks)], "generated_by_ai": False}


@app.post("/api/v1/evidence/sections")
def evidence_sections(body: EvidenceAiRequest, user=Depends(require_user)):
    retrieval = search(body.query, body.active_guideline, 12)
    groups = {}
    for c in retrieval.chunks:
        groups.setdefault((c.source_name, c.file_name, c.section), []).append(c)
    return {"sections": [{"source": cs[0].source, "source_name": name, "section": section, "file_name": filename,
                           "page_number": cs[0].page_number, "region_tag": cs[0].region_tag, "version": cs[0].version,
                           "similarity_score": cs[0].similarity_score, "chunks": [{"chunk_id": c.chunk_id, "chunk_text": c.chunk_text, "page_number": c.page_number, "highlighted": True} for c in cs],
                           "full_text": "\n\n".join(c.chunk_text for c in cs), "truncated": True, "ai_summary": ""}
                          for (name, filename, section), cs in groups.items()], "generated_by_ai": False,
            "retrieval_mode": retrieval.mode, "warnings": retrieval.warnings}


def encounter_payload(encounter_id, body, user):
    encounter = require_encounter(encounter_id, user)
    if body.active_guideline not in {"NICE", "AAP", "WHO"}:
        raise HTTPException(422, "Select NICE, AAP or WHO")
    payload = body.risk_result.model_dump()
    context = build_patient_context(encounter_id)
    if context.load_error:
        raise HTTPException(503, "Patient history unavailable; automated care plan withheld")
    payload["patient"] = encounter_scope(payload.get('patient',{}),encounter)
    return payload, context


@app.post("/api/v1/encounters/{encounter_id}/evidence", response_model=list[EvidenceChunkResponse])
def encounter_evidence(encounter_id: str, body: EncounterEvidenceRequest, user=Depends(require_user)):
    payload, context = encounter_payload(encounter_id, body, user)
    query = "early onset neonatal sepsis " + " ".join(context.query_context_terms())
    return [EvidenceChunkResponse(**c.to_dict()) for c in search(query, body.active_guideline,patient=payload['patient']).chunks]


@app.post("/api/v1/encounters/{encounter_id}/care-plan", response_model=ClinicalCarePlanResponse)
def encounter_care_plan(encounter_id: str, body: CarePlanRequest, user=Depends(require_user)):
    if body.care_setting != "hospital":
        raise HTTPException(422, "This EOS workflow supports the hospital setting only")
    payload, context = encounter_payload(encounter_id, body, user)
    result = produce(payload, body.active_guideline, get_settings(), context)
    record_decision(user, "care_plan", result.model_dump(), encounter_id)
    return result


@app.post("/api/v1/encounters/{encounter_id}/explanation", response_model=ExplanationResponse)
def encounter_explanation(encounter_id: str, body: EncounterEvidenceRequest, user=Depends(require_user)):
    payload, context = encounter_payload(encounter_id, body, user)
    result = explanation_from_plan(produce(payload, body.active_guideline, get_settings(), context))
    record_decision(user, "explanation", result.model_dump(), encounter_id)
    return result


@app.get("/api/v1/guidelines/documents")
def guideline_documents(user=Depends(require_user)):
    rows = get_supabase().table("guideline_documents").select("id,name,source,version,region_tag,storage_path,storage_url,active,ingested_at").eq("active", True).eq("approved_for_generation", True).execute().data or []
    return {"documents": rows}


@app.get("/api/v1/guideline-cache/sync")
def guideline_sync(since: str | None = None, user=Depends(require_user)):
    return {"entries": [], "synced_at": datetime.now(timezone.utc).isoformat()}


@app.get("/api/v1/admin/rag/health")
def rag_health(user=Depends(require_admin)):
    docs, version = load_manifest(get_settings())
    return {"status": "configured" if any(d.get("approved_for_generation") for d in docs) else "review_required",
            "total_chunks": 0, "last_ingestion": None, "embedding_model": get_settings().embedding_model,
            "reranker_model": get_settings().reranker_model, "vector_index": "Supabase pgvector", "corpus_version": version}


@app.get("/api/v1/admin/config/health")
def config_health(user=Depends(require_admin)):
    return {"supabase_configured": bool(settings.supabase_url), "gemini_configured": False, "gemini_model": "unused",
            "guidelines_dir": "managed corpus", "rag_status": rag_health(user)["status"], "groq_configured": bool(settings.groq_api_key)}


@app.get("/api/v1/admin/audit")
def decision_audits(user=Depends(require_admin)):
    rows = get_supabase().table("decision_audits").select("operation,status,model_version,corpus_version,response_sha256,created_at").order("created_at", desc=True).limit(100).execute().data or []
    return {"events": rows, "integrity_claim": "Append-only records; no cryptographic chain verification is claimed"}


@app.post("/api/v1/admin/guidelines/ingest")
def ingestion_disabled(user=Depends(require_admin)):
    raise HTTPException(409, "Run reviewed ingestion as an offline deployment job: python -m rag.ingest")


@app.post("/api/v1/admin/guidelines")
def upload_disabled(user=Depends(require_admin)):
    raise HTTPException(409, "Source review and hash registration are required before offline ingestion")


@app.post("/api/v1/admin/guidelines/rebuild-cache")
def cache_disabled(user=Depends(require_admin)):
    raise HTTPException(409, "Legacy unverified care-plan caches are retired")
