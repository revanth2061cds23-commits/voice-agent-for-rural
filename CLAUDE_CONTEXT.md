# Rita — Claude Code Context

## What This Project Is
Rita is an AI voice agent for rural Punjab citizens to access Indian government welfare schemes over a plain phone call. No smartphone, no internet, no English needed. One call → identity verified → schemes explained → application submitted.

## Monorepo Structure
- agent/ — Rita voice agent (LiveKit + Sarvam + GPT-4o-mini). Runs as Railway worker.
- system1/ — FastAPI + Firebase Firestore. Citizen profile database. Runs as Railway web service.
- system2/ — FastAPI scheme registry. 9 Punjab schemes. Eligibility engine. Runs as Railway web service.
- docs/ — All architecture docs and presentations.
- .env — Single env file for all services at root level.

## Current Agent Version
File: agent/scheme_awareness_agent_v5.py
Status: v4 is live and tested. v5 adds DigiLocker replacing System 1 (pending partner approval).

## Voice Pipeline
- STT: Sarvam saaras:v3 — flush_signal=True is REQUIRED or transcription breaks
- TTS: Sarvam bulbul:v3, speaker=shubh, hi-IN
- LLM: GPT-4o-mini via openai/
- Turn detection: MultilingualModel() object — NEVER pass as string "stt"
- allow_interruptions=False — NEVER change this or voice cuts mid-sentence
- min_endpointing_delay=0.2

## All Agent Tools
1. normalize_aadhaar(raw) — converts spoken Aadhaar to 12 digits, internal utility
2. send_digilocker_otp(aadhaar) — triggers UIDAI OTP to citizen Aadhaar-linked mobile
3. fetch_citizen_profile(aadhaar, otp) — verifies OTP, gets Aadhaar eKYC XML from DigiLocker
4. fetch_land_records(token) — Jamabandi land records, used for PM-KISAN
5. fetch_caste_certificate(token) — SC/ST/OBC/EWS, used for Aashirwad + scholarships
6. fetch_ration_card(token) — Smart card type, used for Ayushman eligibility
7. check_scheme_eligibility(citizen_id) — System 2, returns matched schemes
8. submit_scheme_application(...) — System 2, returns APP-2026-XXXXX
9. get_application_status(app_id) — citizen calls back with APP ID
10. save_citizen_note(aadhaar, note) — System 2, saves notes on citizen record

## Identity & Security Flow
Citizen speaks Aadhaar → send_digilocker_otp() → UIDAI sends OTP to Aadhaar-linked mobile → citizen speaks OTP → fetch_citizen_profile() verifies → DigiLocker access token obtained → documents fetched → eligibility checked → submit only after verified.

## System 2 Demo Mode
System 2 tools are currently dummy implementations inside the agent with realistic delays and fake APP IDs. When SYSTEM2_URL env var is set, agent auto-switches to real System 2.

## Known Fixes — Never Revert These
- normalize_aadhaar() and normalize_citizen_id() — converts spoken IDs like "pee bee 2026 70617" to PB-2026-70617 and spoken Aadhaar to 12 digits
- on_user_turn_completed only echoes detected ID/APP patterns, not full sentences
- check_scheme_eligibility fetches its own JSON from System 1 directly — do not pass profile string
- flush_signal=True is non-negotiable for Sarvam STT
- MultilingualModel() must be object not string

## Rita's Language & Personality
- Hinglish by default (Hindi structure + English words)
- 1-2 sentences per turn maximum — never long responses
- Fillers: hmm, achha, basically, arey, you know
- Commas = breathing pauses for TTS. Ellipsis = thinking pause.
- Switches to Punjabi if citizen speaks Punjabi, English if English
- Never ask for phone number if Aadhaar given
- Numbers always formatted: Rs. 6,000 not Rs 6000

## LiveKit
Project: firstproto-p68gx7fz (India South)
WSS: wss://firstproto-p68gx7fz.livekit.cloud
Sandbox: ritaagent-hhu8hm

## Deployment
Both services go to Railway. Agent runs as worker process, not web server.
Railway handles monorepo — set Root Directory per service in Railway dashboard.
