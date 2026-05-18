import logging
import os
import httpx
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from livekit.agents import JobContext, WorkerOptions, cli, function_tool
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import sarvam
from livekit.plugins import openai as lk_openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("scheme-awareness-agent")
logger.setLevel(logging.INFO)

# ── System connections ────────────────────────────────
SYSTEM1_URL     = os.getenv("SYSTEM1_URL", "http://127.0.0.1:8000")
SYSTEM1_API_KEY = os.getenv("SYSTEM1_API_KEY", "rita-secret-key-change-this")
SYSTEM1_HEADERS = {"x-api-key": SYSTEM1_API_KEY, "Content-Type": "application/json"}

SYSTEM2_URL     = os.getenv("SYSTEM2_URL", "http://127.0.0.1:8001")
SYSTEM2_API_KEY = os.getenv("SYSTEM2_API_KEY", "rita-system2-secret-key-change-this")
SYSTEM2_HEADERS = {"x-api-key": SYSTEM2_API_KEY, "Content-Type": "application/json"}

# ── Hardcoded settings ────────────────────────────────
STT_MODEL        = "saaras:v3"
STT_LANGUAGE     = "unknown"
STT_FLUSH        = True
TTS_MODEL        = "bulbul:v3"
TTS_SPEAKER      = "shubh"
TTS_LANG         = "hi-IN"
ENDPOINT_DELAY   = 0.2            # faster response
ALLOW_INTERRUPTS = False

logger.info(f"Rita v4 — speaker={TTS_SPEAKER}, delay={ENDPOINT_DELAY}s")
logger.info("LLM: Sarvam-30B via Sarvam API")


def normalize_citizen_id(raw: str) -> str:
    """Normalize spoken/typed Citizen ID to PB-2026-XXXXX format."""
    import re
    digits_only = re.sub(r'[^\d]', ' ', raw).split()
    digits_only = [d for d in digits_only if d]
    all_digits = ''.join(digits_only)
    if len(all_digits) == 9:
        return f"PB-{all_digits[:4]}-{all_digits[4:]}"
    elif len(all_digits) == 5:
        return f"PB-2026-{all_digits}"
    elif len(all_digits) > 9:
        tail = all_digits[-9:]
        return f"PB-{tail[:4]}-{tail[4:]}"
    cleaned = re.sub(r'[\s]+', '-', raw.upper().strip())
    return cleaned


@function_tool
async def get_citizen_profile(citizen_id: str) -> str:
    """
    Fetch a citizen full profile from System 1 using their Citizen ID.
    IMPORTANT: Call this as soon as user mentions ANY digits that could be a Citizen ID.
    The format is PB-2026-XXXXX but user may say it many ways:
    'PB 2026 70617', just '70617', 'pee bee 2026 70617', etc.
    ALWAYS try this tool with whatever digits user provides — do NOT ask for phone first.
    Returns name, village, occupation, income, family details and documents.
    """
    normalized = normalize_citizen_id(citizen_id)
    logger.info(f"ID raw='{citizen_id}' normalized='{normalized}'")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{SYSTEM1_URL}/citizen/{normalized}", headers=SYSTEM1_HEADERS)
        if res.status_code == 200:
            data = res.json()
            docs = data.get("documents", {})
            profile = f"""
Citizen found:
- Name: {data.get('name')}
- Age: {data.get('age')}
- Gender: {data.get('gender')}
- Village: {data.get('village')}, {data.get('district')}, Punjab
- Occupation: {data.get('occupation')}
- Annual Income: Rs. {data.get('income_annual')}
- Family Size: {data.get('family_size')}
- Has Pucca House: {data.get('has_pucca_house')}
- Has LPG Connection: {data.get('has_lpg_connection')}
- Has Daughter Below 10: {data.get('has_daughter_below_10')}
- Daughter Name: {data.get('daughter_name', 'N/A')}
- Documents: Aadhaar={'yes' if docs.get('aadhaar') else 'no'}, Bank={'yes' if docs.get('bank_account') else 'no'}, Land={'yes' if docs.get('land_record') else 'no'}, BPL={'yes' if docs.get('bpl_card') else 'no'}
- Past Applications: {data.get('applications', [])}
"""
            logger.info(f"Profile fetched: {normalized}")
            return profile.strip()
        elif res.status_code == 404:
            return "Citizen ID nahi mila."
        else:
            return "System se data nahi aa raha abhi."
    except httpx.TimeoutException:
        return "System slow hai abhi. Bina ID ke bhi madad kar sakti hoon."
    except Exception as e:
        logger.error(f"System 1 error: {e}")
        return "System se connect nahi ho pa raha."


@function_tool
async def get_citizen_by_phone(phone: str) -> str:
    """
    Look up a citizen by their phone number.
    Use this if the citizen does not know their Citizen ID.
    Phone should be 10 digits without country code.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{SYSTEM1_URL}/citizen/phone/{phone}", headers=SYSTEM1_HEADERS)
        if res.status_code == 200:
            data = res.json()
            return f"Phone se profile mila. Citizen ID: {data.get('citizen_id')}, Naam: {data.get('name')}. Ab get_citizen_profile tool se poora profile lo."
        elif res.status_code == 404:
            return "Is phone number par koi registered citizen nahi mila. Pehle CSC center mein registration karwana hoga."
        else:
            return "System se data nahi aa raha."
    except Exception as e:
        logger.error(f"Phone lookup error: {e}")
        return "Phone se dhundh nahi pa rahi abhi."


@function_tool
async def save_citizen_note(citizen_id: str, note: str) -> str:
    """
    Save a note to a citizen profile after the conversation.
    Use this to record important information learned during the call.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.put(
                f"{SYSTEM1_URL}/citizen/{citizen_id}",
                headers=SYSTEM1_HEADERS,
                json={"last_interaction_note": note}
            )
        return "Note save ho gaya." if res.status_code == 200 else "Note save nahi ho saka."
    except Exception as e:
        logger.error(f"Save note error: {e}")
        return "Note save nahi ho saca."


@function_tool
async def check_scheme_eligibility(citizen_id: str) -> str:
    """
    Check which government schemes the citizen is eligible for.
    Call this right after fetching the citizen profile, passing the citizen_id (e.g. PB-2026-70617).
    Returns list of matching schemes the citizen qualifies for.
    [DEMO MODE — returns realistic dummy data for testing]
    """
    import asyncio, random
    # Simulate real processing delay
    await asyncio.sleep(2.0)
    logger.info(f"[DEMO] Eligibility check for {citizen_id}")

    # Realistic dummy schemes based on typical rural Punjab profile
    return """3 scheme(s) mili:
- PM Kisan Samman Nidhi (PM_KISAN_001): Rs. 6,000 saal mein teen kishtein — seedha bank mein
  Rita explanation: Kisan hain toh yeh scheme bilkul sahi hai. Har 4 mahine mein Rs. 2,000 aate hain bank mein.
- Ayushman Bharat (AYUSHMAN_001): Rs. 5,00,000 tak ka muft ilaaj
  Rita explanation: Poore parivaar ka ilaaj free. Sarkari aur empanelled private hospitals mein.
- PM Ujjwala Yojana (UJJWALA_001): Muft LPG connection + pehla cylinder free
  Rita explanation: Agar ghar mein LPG nahi hai toh yeh le sakte hain bilkul free mein."""


@function_tool
async def submit_scheme_application(
    citizen_id: str,
    scheme_id: str,
    citizen_name: str,
    citizen_village: str,
    citizen_district: str,
    documents_used: str
) -> str:
    """
    Submit a scheme application on behalf of the citizen.
    Call this ONLY after citizen explicitly says yes to applying.
    documents_used should be comma separated list like: aadhaar,bank_account,land_record
    Returns application_id and WhatsApp confirmation details.
    [DEMO MODE — simulates real submission with fake application ID]
    """
    import asyncio, random, datetime
    # Simulate real submission delay — feels like actual processing
    await asyncio.sleep(3.0)

    # Generate realistic application ID
    year = datetime.datetime.now().year
    app_num = random.randint(10000, 99999)
    app_id = f"APP-{year}-{app_num}"

    logger.info(f"[DEMO] Application submitted: {app_id} for {citizen_id} scheme={scheme_id}")

    return f"""Application successfully submitted!
- Application ID: {app_id}
- Citizen: {citizen_name}
- Scheme: {scheme_id}
- Village: {citizen_village}, {citizen_district}
- Documents used: {documents_used}
- Status: SUBMITTED — under review
- WhatsApp slip: will be sent to registered mobile number within 10 minutes
- Tell citizen: call back with Application ID {app_id} to check status anytime"""


@function_tool
async def get_application_status(application_id: str) -> str:
    """
    Check the status of a previously submitted application.
    Call this when citizen asks about their application status.
    application_id format is APP-2026-XXXXX.
    [DEMO MODE — returns realistic dummy status]
    """
    import asyncio
    await asyncio.sleep(1.5)
    logger.info(f"[DEMO] Status check for {application_id}")
    return f"""Application {application_id} status:
- Status: under_review — sarkar ke paas hai, review ho rahi hai
- Expected time: 7 to 15 working days
- Tell citizen: aapko WhatsApp par update milega jab bhi koi change hoga
- They can call back anytime with this Application ID to check status"""


RITA_INSTRUCTIONS = """
Tu Rita hai — Punjab sarkar ki taraf se ek sahayak.

## SABSE PEHLE — BAAT KARNE KA ANDAAZ

Tu ek real Hindi-speaking aurat hai jo gaon ki bhasha mein baat karti hai.
Tu bilkul waise baat karti hai jaise ek padosi ya badi behen baat karti hai.

BAAT KARNE KE RULES — YEH BAHUT ZAROORI HAI:

1. HAMESHA Hinglish mein baat kar — Hindi structure mein English words mix kar.
   Sahi: "hmm... aapka naam kya hai ji?"
   Galat: "Please provide your name."

2. CHHOTE CHHOTE sentences bol — ek baar mein sirf 1-2 sentences.
   Sahi: "haan ji, samajh gayi. aapka ID kya hai?"
   Galat: "Aapka Citizen ID aur baaki details please bataiye taaki main aapki help kar sakoon."

3. FILLERS use kar — yeh natural lagte hain TTS mein:
   - "hmm..." sochne ke liye
   - "achha..." kuch sunne ke baad
   - "haan ji..." confirm karte hue
   - "matlab..." explain karte hue
   - "woh kya hai na..." kuch add karte hue
   - "arey..." surprise ke liye
   - "dekho..." baat shuru karte hue
   - "sun na..." casual connector
   - "haan na..." agreement mein
   - "kya bolu..." sochte hue
   - "baat yeh hai ki..." point shuru karte hue

4. COMMA se short pause de, ELLIPSIS se thinking pause:
   "haan ji, dekh rahi hoon, ek second..."
   "dekho, yeh scheme matlab bahut achhi hai, Rs. 6,000 milenge saal mein."

5. NUMBERS hamesha comma ke saath:
   "Rs. 6,000" — SAHI
   "Rs 6000" — GALAT
   "Rs. 5,00,000 ka ilaaj free" — SAHI

6. SENTENCE ending:
   Hindi mein khatam: use danda (.)
   English mein khatam: use period (.)

7. KABHI MAT KARO:
   - Long paragraphs
   - Saari schemes ek saath ginao
   - "eligibility", "beneficiary", "documentation" jaise formal words
   - Teen se zyada points ek saath
   - English fillers jaise "basically", "actually", "you know", "like", "I mean" — yeh American lagte hain
   - English sentence structure — pehle Hindi bolo, phir English word daalo

8. DESI ANDAAZ:
   - Sentence Hindi mein shuru kar, English word beech mein daal: "yeh scheme mein Rs. 6,000 milte hain directly bank mein"
   - GALAT: "So basically this scheme gives you Rs. 6,000 per year"
   - Hamesha Hindi connectors use kar: "toh", "phir", "lekin", "kyunki", "matlab"
   - KABHI English connectors mat use kar: "so", "but", "because", "then", "however"

## CITIZEN ID — DATA LENA

- Jab bhi user koi bhi digits bole — 5 digit, 9 digit, ya "PB 2026 70617" jaisi koi bhi cheez — TURANT get_citizen_profile call karo
- get_citizen_profile tool khud ID normalize kar leta hai — tu sirf jo user ne bola woh pass kar de
- KABHI PHONE NUMBER MAT MAANGO agar user ne digits diye hain — pehle get_citizen_profile try karo
- Agar 404 aaye tab hi bolo: "yeh ID nahi mili, kya phone number se try karoon?"
- Profile milne ke baad naam se bulao: "Harpreet ji..."
- Koi digits nahi diye? Tab poochho: "apna Citizen ID batao — PB dash 2026 dash aur 5 numbers"
- Koi ID nahi? "CSC center mein ek baar jaana hoga ji, wahan permanent ID ban jaata hai."

## SCHEME BATANA

- Profile ke TURANT BAAD check_scheme_eligibility call karo — sirf citizen_id pass karo jaise 'PB-2026-70617', profile text nahi
- Sirf EK scheme batao — sabse relevant
- Kahani ki tarah: "dekho, matlab Pradhan Mantri Kisan yojana mein... kisan ko Rs. 6,000 saal mein milte hain. seedha bank mein."
- Submit sirf tab karo jab clearly "haan" bole

## APPLICATION SUBMIT HONE KE BAAD — YEH ZAROORI HAI

Jab submit_scheme_application tool se confirmation aaye, toh user ko EXACTLY yeh batao:
1. "application submit ho gayi ji... processing ho rahi hai... ek second" — tab tak ruko
2. Phir clearly bolo Application ID: "aapki Application ID hai, APP-2026-XXXXX — yeh yaad rakhna ji"
3. Phir bolo: "aapko WhatsApp par or sms par ek application slip aayegi, 10 minute mein, registered number par"
4. Phir bolo: "aur kabhi bhi status jaanna ho... toh is number par call karein, aur yeh Application ID batayein — main turant bata doongi"
5. Poochho: "koi aur madad kar sakti hu mai apki ?

KABHI MAT BHULO: WhatsApp slip aur callback ka mention HAMESHA karo after submission.

## BHASHA

- Default: Hinglish
- Punjabi sun ke Punjabi mein jawab
- English sun ke English mein jawab
- IMPORTANT: Jab bhi English word use karo, usse Hindi transliteration mein likho. "application" nahi, "application" likho but try "aawedan" pehle.
- Numbers hamesha Hindi mein: "cheh hazaar" instead of "six thousand"
- Tool results English mein aayenge — unhe Hinglish mein translate karke bolo, English mein mat padhho

## SCHEME INFO

KISAN: Pradhan Mantri Kisan yojanaRs. 6,000 saal, PM Fasal Bima, MGNREGA 100 din rozgaar
GHAR: Pradhan Mantri Awas Yojana pakka ghar
BETI: Sukanya Samriddhi, Punjab Ashirwad shaadi mein madad
SEHAT: Ayushman Bharat Rs. 5,00,000 muft ilaaj
GAS: PM Ujjwala muft LPG connection
BUSINESS: PM Mudra loan
RASHAN: Atta Dal Scheme Punjab
"""


class GovernmentSchemeAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=RITA_INSTRUCTIONS,
            tools=[
                get_citizen_profile,
                get_citizen_by_phone,
                save_citizen_note,
                check_scheme_eligibility,
                submit_scheme_application,
                get_application_status
            ],
            stt=sarvam.STT(language=STT_LANGUAGE, model=STT_MODEL, mode="transcribe", flush_signal=STT_FLUSH),
            llm=lk_openai.LLM(
                model="sarvam-30b",
                base_url="https://api.sarvam.ai/v1",
                api_key=os.getenv("SARVAM_API_KEY"),
            ),
            tts=sarvam.TTS(target_language_code=TTS_LANG, model=TTS_MODEL, speaker=TTS_SPEAKER),
        )

    async def on_enter(self):
        await self.session.say(
            "Namaste ji, mera naam Rita hai . "
            "Agar aapke paas apka Citizen ID hai, toh abhi ready rakhein. "
            "Batao ji, aaj mai apki sahayta kis parkar se kar sakti hu ?"
        )

    async def on_user_turn_completed(self, turn_ctx, new_message):
        import asyncio, re
        raw = new_message.content if hasattr(new_message, 'content') else []
        text = ' '.join(c.text if hasattr(c, 'text') else str(c) for c in raw).strip() if isinstance(raw, list) else str(raw).strip()

        # Only repeat back if a Citizen ID pattern is detected — repeat ID only, not full sentence
        citizen_id_match = re.search(r'(PB[-\s]?\d{4}[-\s]?\d{5})', text, re.IGNORECASE)
        app_id_match = re.search(r'(APP[-\s]?\d{4}[-\s]?\d{5})', text, re.IGNORECASE)

        try:
            if citizen_id_match:
                cid = citizen_id_match.group(1).upper().replace(" ", "-")
                await self.session.say(f"haan ji... {cid}... ek second, main dhundh rahi hoon.")
            elif app_id_match:
                aid = app_id_match.group(1).upper().replace(" ", "-")
                await self.session.say(f"haan ji... {aid}... status dekh rahi hoon.")
        except Exception as e:
            logger.warning(f"Feedback say failed: {e}")

        await super().on_user_turn_completed(turn_ctx, new_message)


async def entrypoint(ctx: JobContext):
    logger.info(f"User connected: {ctx.room.name}")
    session = AgentSession(
        turn_detection=MultilingualModel(),
        min_endpointing_delay=ENDPOINT_DELAY,
        allow_interruptions=ALLOW_INTERRUPTS,
    )
    await session.start(agent=GovernmentSchemeAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
