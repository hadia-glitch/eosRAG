"""Durable decision provenance, without storing prompts or clinical values.
This is an append-only database record, not a claimed tamper-proof hash chain.
"""
import hashlib
import json
from fastapi import HTTPException
from db import get_supabase


def record_decision(user, operation, result, encounter_id=None):
    summary = {"actor_id": user.user_id, "encounter_id": encounter_id, "operation": operation,
               "model_version": result.get("model_version", ""), "corpus_version": result.get("corpus_version", ""),
               "status": result.get("verification_status", result.get("status", "unknown")),
               "response_sha256": hashlib.sha256(json.dumps(result, sort_keys=True, default=str).encode()).hexdigest()}
    try:
        response = get_supabase().table("decision_audits").insert(summary).execute()
        if not response.data:
            raise RuntimeError("Audit not acknowledged")
    except Exception as exc:
        raise HTTPException(503, "Decision audit unavailable; automated response withheld") from exc
