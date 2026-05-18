# Rita — AI Voice Agent for Government Welfare Schemes

Rita is an AI voice agent that helps rural Punjab citizens access Indian government welfare schemes over a plain phone call. No smartphone, no internet, no English needed.

**One call → identity verified → schemes explained → application submitted.**

## Monorepo Structure

```
rita/
├── .env                  ← single env file for all services
├── .env.example          ← safe-to-commit template
├── .gitignore
├── README.md
├── CLAUDE_CONTEXT.md     ← context file for Claude Code
├── agent/                ← Rita voice agent
│   ├── scheme_awareness_agent_v5.py
│   ├── requirements.txt
│   └── Procfile
├── common/               ← Shared helpers (Firebase credential loading)
├── system1/              ← Citizen profile database (FastAPI + Firebase)
│   ├── main.py
│   ├── requirements.txt
│   ├── firebase-key.json.example
│   └── Procfile
├── system2/              ← Scheme registry & eligibility engine (FastAPI)
│   ├── main.py
│   ├── eligibility.py
│   ├── schemes.json
│   ├── requirements.txt
│   └── Procfile
└── docs/                 ← Architecture docs and presentations
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Voice transport | LiveKit |
| STT | Sarvam AI (saaras:v3) |
| TTS | Sarvam AI (bulbul:v3) |
| LLM | GPT-4o-mini |
| Identity verification | DigiLocker (Aadhaar) |
| OTP & WhatsApp | Twilio |
| Citizen database | Firebase Firestore |
| Backend framework | FastAPI |
| Hosting | Railway |

## Local Development

### 1. Set up environment

```bash
cp .env.example .env
# Fill in your API keys in .env
```

**Firebase (required for System 1 and System 2):** Download a service account JSON from the [Firebase Console](https://console.firebase.google.com/), then either:

- Set `FIREBASE_KEY_BASE64` in `.env` to the base64-encoded JSON (recommended for Railway), or
- Copy the JSON to `system1/firebase-key.json` (gitignored; use `system1/firebase-key.json.example` as a template)

Never commit your real Firebase key file.

### 2. Run System 1 (Citizen Database)

```bash
cd system1
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Run System 2 (Scheme Registry)

```bash
cd system2
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Run the Agent

```bash
cd agent
pip install -r requirements.txt
python scheme_awareness_agent_v5.py start
```

## Deploy to Railway

Each service is deployed separately using Railway's monorepo support:

1. Create a new Railway project
2. Add three services, each pointing to this repo
3. Set the **Root Directory** for each service:
   - Service 1: `agent/` (worker process)
   - Service 2: `system1/` (web service)
   - Service 3: `system2/` (web service)
4. Add all environment variables from `.env` to each service as needed
5. Railway will auto-detect the `Procfile` in each root directory

The agent runs as a **worker** (no port), while system1 and system2 run as **web** services.
