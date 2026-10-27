"""Supabase token validation and explicit encounter ownership (service client
bypasses RLS, so every patient read must prove ownership before fetching data).
"""
from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import get_settings
from db import get_supabase

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: str
    admin: bool = False


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "A signed-in clinician session is required", headers={"WWW-Authenticate": "Bearer"})
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(503, "Authentication is not configured")
    try:
        with httpx.Client(timeout=8) as client:
            response = client.get(f"{settings.supabase_url.rstrip('/')}/auth/v1/user", headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {credentials.credentials}"})
        if response.status_code in (401, 403):
            raise HTTPException(401, "Session expired or invalid", headers={"WWW-Authenticate": "Bearer"})
        response.raise_for_status()
        data = response.json()
        user_id = str(UUID(data["id"]))
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "Authentication service unavailable")
    # app_metadata is server managed; user_metadata is never authorization.
    return Principal(user_id, data.get("app_metadata", {}).get("role") == "admin")


def require_admin(user=Depends(require_user)):
    if not user.admin:
        raise HTTPException(403, "Administrator role required")
    return user


def require_encounter(encounter_id: str, user: Principal):
    try:
        UUID(encounter_id)
    except ValueError:
        raise HTTPException(422, "Invalid encounter identifier")
    try:
        rows = get_supabase().table("patient_encounters").select("id,birth_date_time,gestational_age_days,birth_weight_g").eq("id", encounter_id).eq("owner_user_id", user.user_id).limit(1).execute().data or []
    except Exception:
        raise HTTPException(503, "Patient data service unavailable")
    if not rows:
        raise HTTPException(404, "Encounter not found")
    return rows[0]
