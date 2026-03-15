# 🪷 Aadhya – AI Interior Design Consultant
**TatvaOps Internal AI System · v1.0**

Aadhya is a dual-channel AI consulting system — WhatsApp + Voice — sharing a single Gemini intelligence layer. It conducts dynamic interior design enquiries and generates structured project summaries.

---

## Architecture

```
User (WhatsApp / Phone Call)
        ↓
Agent Interface (Twilio / Vapi)
        ↓
ConversationController
        ↓
GeminiEngine (gemini-2.0-flash)
        ↓
StructuredExtractor → EnquiryEngine (Priority-Based)
        ↓
SummaryGenerator
        ↓
Project Summary → Supabase / Admin Panel
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Google Gemini API key
- (Optional for full live testing): Twilio, Vapi, ElevenLabs, Upstash, Supabase accounts

---

## Quick Start

### 1. Clone & Setup

```bash
cd aadhya
cp .env.example .env
# Edit .env with your API keys
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Backend runs at: `http://localhost:8000`  
API docs at: `http://localhost:8000/docs`

### 4. Build & run the admin UI

```bash
cd admin-ui
npm install
npm run dev        # Development: http://localhost:5173/krsna
# OR
npm run build      # Production build → backend serves at /krsna
```

---

## Configuration

Copy `.env.example` to `.env` and fill in:

| Variable | Description | Required |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | ✅ |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | WhatsApp |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | WhatsApp |
| `TWILIO_WHATSAPP_FROM` | Twilio sandbox number | WhatsApp |
| `VAPI_API_KEY` | Vapi API key | Voice |
| `ELEVENLABS_VOICE_ID` | ElevenLabs voice ID | Voice |
| `UPSTASH_REDIS_REST_URL` | Upstash REST URL | Recommended |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash token | Recommended |
| `SUPABASE_URL` | Supabase project URL | Recommended |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Recommended |
| `ADMIN_PASSWORD` | Admin panel password | ✅ |
| `ADMIN_API_KEY` | Admin API key header | ✅ |

> **Without Redis/Supabase**: System falls back to in-memory storage (data lost on restart).

---

## Webhooks Setup

### WhatsApp (Twilio Sandbox)
1. Go to Twilio Console → Messaging → WhatsApp Sandbox
2. Set webhook URL: `https://your-domain/webhook/whatsapp`
3. Method: HTTP POST
4. Send "join [sandbox-keyword]" to the Twilio number on WhatsApp
5. Text the number — Aadhya will respond!

### Voice (Vapi)
1. Create a Vapi assistant at [vapi.ai](https://vapi.ai)
2. Set the server URL to: `https://your-domain/webhook/vapi`
3. Set transcriber: Deepgram · `nova-2` · `en-IN`
4. Set voice: ElevenLabs with your preferred voice ID
5. Assign a phone number to the assistant

---

## Admin Panel — /krsna

Access at: `http://localhost:8000/krsna`  
(or `http://localhost:5173/krsna` in dev mode)

**Login**: Use `ADMIN_PASSWORD` from your `.env`

| Section | Path | Description |
|---|---|---|
| Dashboard | `/krsna/dashboard` | Stats + charts |
| Sessions | `/krsna/sessions` | All active conversations |
| Session Detail | `/krsna/sessions/:id` | Chat + AI thinking trace |
| Enquiries | `/krsna/enquiries` | Structured field data |
| Summaries | `/krsna/summaries` | Generated project summaries |
| Logs | `/krsna/logs` | Structured event logs |
| System | `/krsna/system` | API health + live feed |

---

## Supabase Schema

Run this SQL in your Supabase SQL editor to create the required tables:

```sql
-- Copy from: backend/storage/supabase_store.py (SCHEMA_SQL constant)
```

---

## Deployment (Railway / Render)

### Railway
```bash
railway login
railway init
railway up
```

Set all `.env` variables in Railway dashboard.

**Build command**: `pip install -r requirements.txt && cd admin-ui && npm install && npm run build`  
**Start command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

### Render
- Runtime: Python 3.11
- Build: `pip install -r requirements.txt`
- Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Add all env vars in Render dashboard

---

## Testing Locally (Simulated Webhooks)

```bash
# Test WhatsApp webhook
curl -X POST http://localhost:8000/webhook/whatsapp \
  -d "From=whatsapp%3A%2B919876543210&Body=Hi+I+need+interior+design+help"

# Test Vapi webhook
curl -X POST http://localhost:8000/webhook/vapi \
  -H "Content-Type: application/json" \
  -d '{"message":{"type":"transcript","role":"user","transcript":"I have a 3BHK villa in Bengaluru"},"call":{"id":"test_001","customer":{"number":"+919876543210"}}}'

# Admin API
curl http://localhost:8000/admin/dashboard \
  -H "X-Admin-Key: your_admin_api_key"

# Admin login
curl -X POST http://localhost:8000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"password":"your_admin_password"}'
```

---

## Project Structure

```
aadhya/
├── backend/
│   ├── main.py                      # FastAPI app entry
│   ├── config.py                    # Pydantic settings
│   ├── agents/
│   │   ├── chat/whatsapp_handler.py # Twilio webhook
│   │   └── voice/vapi_handler.py    # Vapi webhook
│   ├── intelligence/
│   │   ├── persona.py               # Aadhya system prompts
│   │   ├── gemini_engine.py         # Gemini API wrapper
│   │   ├── conversation_controller.py # Orchestration
│   │   ├── enquiry_engine.py        # Priority field engine
│   │   └── extractor.py             # Structured extraction
│   ├── schemas/                     # Pydantic models
│   ├── summarizer/                  # Summary generator
│   ├── storage/                     # Redis + Supabase
│   ├── admin/                       # Admin API endpoints
│   └── utils/                       # Logger + retry
├── admin-ui/                        # React + Tailwind SPA
└── examples/                        # Sample conversations
```

---

*Built with ❤️ for TatvaOps · Powered by Google Gemini*
