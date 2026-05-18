"""
Rita System 2 — Scheme Registry
FastAPI backend with Firebase Firestore (applications collection)
"""

from __future__ import annotations

import json
import os
import random
import string
import sys
from datetime import datetime, timezone
from pathlib import Path as FilePath
from typing import Literal

import firebase_admin
from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import firestore
from pydantic import BaseModel, Field

from eligibility import check_eligibility

_root = FilePath(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from common.firebase_init import get_firebase_certificate

load_dotenv(_root / ".env")
load_dotenv()


SYSTEM2_API_KEY = os.getenv("SYSTEM2_API_KEY") or "rita-system2-secret-key-change-this"
SYSTEM1_URL = os.getenv("SYSTEM1_URL") or ""
SYSTEM1_API_KEY = os.getenv("SYSTEM1_API_KEY") or ""


def verify_key(x_api_key: str = Header(...)) -> None:
    if x_api_key != SYSTEM2_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _load_schemes() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    schemes_path = os.path.join(here, "schemes.json")
    try:
        with open(schemes_path, "r", encoding="utf-8") as f:
            schemes = json.load(f)
    except FileNotFoundError:
        raise RuntimeError("schemes.json not found")
    if not isinstance(schemes, list):
        raise RuntimeError("schemes.json must be a list of schemes")
    return schemes


SCHEMES: list[dict] = _load_schemes()
SCHEMES_BY_ID: dict[str, dict] = {s["scheme_id"]: s for s in SCHEMES}


def generate_application_id() -> str:
    suffix = "".join(random.choices(string.digits, k=5))
    return f"APP-2026-{suffix}"


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _init_firestore():
    try:
        if not firebase_admin._apps:
            cred = get_firebase_certificate()
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception:
        return None


db = _init_firestore()


def _get_db():
    global db
    if db is None:
        db = _init_firestore()
    if db is None:
        raise HTTPException(
            status_code=500,
            detail="Firebase init failed. Set FIREBASE_KEY_BASE64 or place firebase-key.json in system1/ (see SETUP_GUIDE.md).",
        )
    return db


app = FastAPI(title="Rita Scheme Registry (System 2)", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApplicationCreateRequest(BaseModel):
    citizen_id: str
    scheme_id: str
    citizen_profile: dict = Field(..., description="Full citizen profile from System 1")
    documents_used: list[str] | None = None


class ApplicationStatusUpdate(BaseModel):
    status: Literal["submitted", "in_review", "approved", "rejected", "needs_more_info"]


@app.get("/health")
async def health():
    return {"status": "ok", "system": "Rita System 2"}


@app.get("/schemes", dependencies=[Depends(verify_key)])
async def list_schemes():
    return SCHEMES


@app.get("/schemes/{scheme_id}", dependencies=[Depends(verify_key)])
async def get_scheme(scheme_id: str = Path(...)):
    scheme = SCHEMES_BY_ID.get(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return scheme


@app.post("/schemes/eligible", dependencies=[Depends(verify_key)])
async def eligible_schemes(citizen_profile: dict = Body(...)):
    matches = [s for s in SCHEMES if check_eligibility(citizen_profile, s)]
    return {"eligible_schemes": matches, "count": len(matches)}


@app.post("/applications", dependencies=[Depends(verify_key)])
async def submit_application(payload: ApplicationCreateRequest):
    scheme = SCHEMES_BY_ID.get(payload.scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    if not check_eligibility(payload.citizen_profile, scheme):
        raise HTTPException(status_code=400, detail="Citizen not eligible for this scheme")

    application_id = generate_application_id()
    now_iso = _utc_iso_now()

    citizen_name = payload.citizen_profile.get("name")
    citizen_village = payload.citizen_profile.get("village")
    citizen_district = payload.citizen_profile.get("district")

    documents_used = payload.documents_used
    if documents_used is None:
        documents_used = list(scheme.get("required_documents") or [])

    doc = {
        "application_id": application_id,
        "citizen_id": payload.citizen_id,
        "scheme_id": payload.scheme_id,
        "scheme_name": scheme.get("name"),
        "status": "submitted",
        "submitted_at": now_iso,
        "updated_at": now_iso,
        "citizen_name": citizen_name,
        "citizen_village": citizen_village,
        "citizen_district": citizen_district,
        "documents_used": documents_used,
        "fraud_score": 0,
    }

    _get_db().collection("applications").document(application_id).set(doc)
    return {"application_id": application_id, "status": doc["status"]}


@app.get("/applications/{app_id}", dependencies=[Depends(verify_key)])
async def get_application(app_id: str = Path(...)):
    snap = _get_db().collection("applications").document(app_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Application not found")
    return snap.to_dict()


@app.put("/applications/{app_id}/status", dependencies=[Depends(verify_key)])
async def update_application_status(app_id: str, payload: ApplicationStatusUpdate):
    ref = _get_db().collection("applications").document(app_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Application not found")

    now_iso = _utc_iso_now()
    ref.update({"status": payload.status, "updated_at": now_iso})
    return {"application_id": app_id, "status": payload.status, "updated_at": now_iso}


@app.get("/applications", dependencies=[Depends(verify_key)])
async def list_applications():
    snaps = (
        _get_db()
        .collection("applications")
        .order_by("submitted_at", direction=firestore.Query.DESCENDING)
        .stream()
    )
    return [s.to_dict() for s in snaps]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)

