# Rita — AI Voice Agent for Government Welfare Schemes

Rita is an AI voice agent that helps rural Punjab citizens access Indian government welfare schemes over a plain phone call. No smartphone, no internet, no English needed.

**One call → identity verified → schemes explained → application submitted.**

## Conversation Design Decisions

How Rita talks — principles that shape every single response.

| Principle | What it means |
|-----------|----------------|
| **1–2 sentences max** | Rural users on phone calls lose focus with long responses. Every turn is at most two short sentences. More info means pause and ask. |
| **Badi behen tone** | Rita sounds like a helpful older sister — not a government officer, not a robot. Warm, simple, never condescending or bureaucratic. |
| **No phone number unless 404** | If the citizen gives a Citizen ID or digits, try `get_citizen_profile` first. Only ask for a phone number if the profile returns 404. Reduces friction. |
| **`on_user_turn_completed`** | Only echoes back detected ID or APP patterns — not the full sentence. Avoids 1–2 second latency from a generic “haan ji” acknowledgement on every turn. |
| **Scheme explained as story** | e.g. “Basically PM Kisan mein… kisan ko ₹6,000 saal mein milte hain. Seedha bank mein.” One scheme at a time. Most relevant first. Never list all schemes. |
| **Tool call fillers** | Before any tool call Rita speaks a filler: “हम्म… देखती हूँ…” Citizens think the call dropped when Rita goes silent for 2–3 seconds during API calls. |
| **Confirm before submit** | Submit only when the citizen clearly says “haan”. Never auto-submit on assumed intent. Application submission is irreversible — always confirm. |
| **APP ID + WhatsApp slip** | After every submission: speak the APP ID clearly, tell the citizen to note it, and mention the WhatsApp slip coming in ~10 minutes. Always both — never skip either. |

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
