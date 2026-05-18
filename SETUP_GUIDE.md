# Rita Agent — Setup Guide (Beginner Friendly)

This guide will help you run Rita on your own computer. No coding experience needed — just follow each step carefully.

---

## STEP 1: Install Python

1. Go to https://www.python.org/downloads/
2. Download **Python 3.12** or newer
3. Run the installer
4. **IMPORTANT**: Check the box that says **"Add Python to PATH"** before clicking Install
5. After install, open **PowerShell** (search "PowerShell" in Start menu) and type:
   ```
   python --version
   ```
   You should see something like `Python 3.12.x` — that means it worked.

---

## STEP 2: Install Git

1. Go to https://git-scm.com/downloads
2. Download and install (keep all the default options, just click Next)
3. In PowerShell, type:
   ```
   git --version
   ```
   You should see a version number — that means it worked.

---

## STEP 3: Download the project

Open PowerShell and run these commands one by one:

```powershell
cd ~\Desktop
git clone https://github.com/revanth2061cds23-commits/voice-agent-for-rural.git
cd voice-agent-for-rural
```

This will create a folder called `voice-agent-for-rural` on your Desktop.

---

## STEP 4: Install dependencies

Run these 3 commands one by one in PowerShell. Wait for each one to finish before running the next:

```powershell
pip install -r system1\requirements.txt
```
```powershell
pip install -r system2\requirements.txt
```
```powershell
pip install -r agent\requirements.txt
```

Each one will download some packages. You'll see a lot of text scrolling — that's normal. Wait until you see the command prompt again before running the next one.

---

## STEP 5: Set up the secret keys

1. Open the `voice-agent-for-rural` folder on your Desktop
2. You might need to enable "Show hidden files" in File Explorer:
   - Click **View** at the top → check **Hidden items**
3. Find the file called `.env.example`
4. Right-click it → **Copy**, then **Paste** in the same folder
5. Rename the copy to `.env` (just a dot followed by env, nothing else)
   - Windows might warn you about changing the extension — click **Yes**
6. Right-click `.env` → **Open with** → **Notepad**
7. Fill in the API keys (LiveKit, Sarvam, OpenAI, Twilio, etc.)
8. Save (Ctrl+S) and close Notepad

### Firebase credentials (required)

System 1 and System 2 need a Firebase service account key. **Do not commit this file.**

**Option A — local file (easiest for development):**

1. In [Firebase Console](https://console.firebase.google.com/) → Project Settings → Service accounts → **Generate new private key**
2. Save the downloaded JSON as `system1\firebase-key.json` (same folder as `firebase-key.json.example`)

**Option B — base64 in `.env` (good for Railway):**

1. Encode your service account JSON as base64 and set `FIREBASE_KEY_BASE64=` in `.env`

---

## STEP 6: Start System 1 (Citizen Database)

Open a **new PowerShell window** and run:

```powershell
cd ~\Desktop\voice-agent-for-rural\system1
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this window open. Don't close it.**

---

## STEP 7: Start System 2 (Scheme Engine)

Open a **second PowerShell window** (right-click PowerShell in taskbar → "Windows PowerShell") and run:

```powershell
cd ~\Desktop\voice-agent-for-rural\system2
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
```

**Keep this window open too.**

---

## STEP 8: Start the Rita Agent

Open a **third PowerShell window** and run:

```powershell
cd ~\Desktop\voice-agent-for-rural\agent
python scheme_awareness_agent_v5.py console
```

You should see Rita start up and register with LiveKit.

---

## STEP 9: Test it

1. Open your browser and go to: https://agents-playground.livekit.io/
2. Enter the LiveKit URL, API Key, and API Secret from the `.env` file
3. Click Connect
4. Talk to Rita!

---

## To stop everything

Press **Ctrl + C** in each of the 3 PowerShell windows.

---

## Troubleshooting

**"python is not recognized"**
→ Python wasn't added to PATH. Uninstall Python, reinstall, and make sure to check "Add Python to PATH".

**"pip is not recognized"**
→ Try `python -m pip` instead of just `pip`. For example:
```powershell
python -m pip install -r system1\requirements.txt
```

**System 1 crashes immediately**
→ Add Firebase credentials: place your service account JSON at `system1\firebase-key.json`, or set `FIREBASE_KEY_BASE64` in `.env`. See STEP 5 above.

**Agent shows "AssertionError"**
→ Make sure System 1 and System 2 are running first, then start the agent.

**Can't see .env file**
→ Enable "Show hidden files" in File Explorer (View → Hidden items).
