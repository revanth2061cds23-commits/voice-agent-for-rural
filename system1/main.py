"""
Rita System 1 — Citizen Data Repository
FastAPI backend with Firebase Firestore
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import firebase_admin
from firebase_admin import firestore
import random
import string
from dotenv import load_dotenv

from common.firebase_init import get_firebase_certificate

load_dotenv(_root / ".env")
load_dotenv()

# ── Firebase Init ─────────────────────────────────────────────
cred = get_firebase_certificate()
firebase_admin.initialize_app(cred)
db = firestore.client()

app = FastAPI(title="Rita Citizen Data Repository", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("SYSTEM1_API_KEY", "rita-secret-key-change-this")

def verify_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

def generate_citizen_id():
    """Generate unique Punjab citizen ID: PB-2026-XXXXX"""
    suffix = ''.join(random.choices(string.digits, k=5))
    return f"PB-2026-{suffix}"


# ── Data Models ───────────────────────────────────────────────

class Documents(BaseModel):
    aadhaar: Optional[str] = None
    bank_account: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bpl_card: Optional[str] = None
    land_record: Optional[str] = None
    land_acres: Optional[float] = None
    income_certificate: Optional[str] = None
    caste_certificate: Optional[str] = None
    voter_id: Optional[str] = None
    ration_card: Optional[str] = None

class FamilyMember(BaseModel):
    name: str
    age: int
    gender: str
    relation: str
    aadhaar: Optional[str] = None

class CitizenCreate(BaseModel):
    # Identity
    name: str
    age: int
    gender: str
    phone: str

    # Location
    village: str
    block: str
    district: str
    state: str = "Punjab"

    # Economic
    occupation: str           # farmer / labourer / small_business / housewife / student / other
    income_annual: int        # in rupees
    has_pucca_house: bool = False
    has_lpg_connection: bool = False

    # Family
    family_size: int
    has_daughter_below_10: bool = False
    daughter_name: Optional[str] = None
    daughter_age: Optional[int] = None
    family_members: Optional[list[FamilyMember]] = []

    # Documents
    documents: Documents


# ── Endpoints ─────────────────────────────────────────────────

@app.post("/citizen/enroll")
async def enroll_citizen(data: CitizenCreate):
    """
    CSC operator enrolls a new citizen.
    Returns a unique Citizen ID.
    """
    # Check if phone already registered
    existing = db.collection("citizens").where("phone", "==", data.phone).get()
    if existing:
        raise HTTPException(status_code=400, detail="Phone already registered")

    citizen_id = generate_citizen_id()
    citizen_data = {
        "citizen_id": citizen_id,
        **data.dict(),
        "documents": data.documents.dict(),
        "applications": [],
        "enrolled_at": firestore.SERVER_TIMESTAMP,
        "last_interaction": firestore.SERVER_TIMESTAMP,
    }

    db.collection("citizens").document(citizen_id).set(citizen_data)
    return {"citizen_id": citizen_id, "message": "Enrollment successful"}


@app.get("/citizen/{citizen_id}")
async def get_citizen(citizen_id: str, x_api_key: str = Header(...)):
    """Rita calls this to fetch full citizen profile"""
    verify_key(x_api_key)
    doc = db.collection("citizens").document(citizen_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Citizen not found")
    return doc.to_dict()


@app.get("/citizen/phone/{phone}")
async def get_citizen_by_phone(phone: str, x_api_key: str = Header(...)):
    """Rita calls this when user calls — looks up by phone number"""
    verify_key(x_api_key)
    results = db.collection("citizens").where("phone", "==", phone).get()
    if not results:
        raise HTTPException(status_code=404, detail="No citizen found with this phone")
    return results[0].to_dict()


@app.put("/citizen/{citizen_id}")
async def update_citizen(citizen_id: str, updates: dict, x_api_key: str = Header(...)):
    """Rita calls this to update profile after conversation"""
    verify_key(x_api_key)
    db.collection("citizens").document(citizen_id).update(updates)
    return {"message": "Updated successfully"}


@app.get("/citizen/{citizen_id}/applications")
async def get_applications(citizen_id: str, x_api_key: str = Header(...)):
    """Get all applications for a citizen"""
    verify_key(x_api_key)
    apps = db.collection("applications").where("citizen_id", "==", citizen_id).get()
    return [a.to_dict() for a in apps]

@app.get("/portal")
async def serve_portal():
    return FileResponse("../frontend/enrollment-portal.html")
@app.get("/health")
async def health():
    return {"status": "ok", "system": "Rita System 1"}
