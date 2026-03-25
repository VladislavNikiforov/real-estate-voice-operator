# Real Estate Voice Operator

A voice-driven business operations assistant. Call a phone number, ask to send an invoice — it looks up the client and service from Notion, generates a PDF, sends the email via Gmail, uploads to Drive, and notifies you on Telegram.

**Hackathon build** | Demo company: SIA "TEIKUMS JT"

---

## Architecture

Two parallel approaches — ElevenLabs-managed and Claude-as-brain:

### Approach 1: ElevenLabs-managed (master)

```
Phone call (ElevenLabs Conversational AI)
        │
        ▼
ElevenLabs STT + LLM  ──webhook──▶  FastAPI Server
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
           Notion lookup        Generate PDF          Search Gmail
        (client & service)     (reportlab +           (Gmail API)
                               DejaVu fonts)
                    │                   │
                    ▼                   ▼
              Draft email        Upload to Drive
           (templates EN/LV/RU)  (Google Drive API)
                    │                   │
                    └───────────────────┘
                              │
                              ▼
                     Send via Gmail API
                    (OAuth2, with PDF attachment)
                              │
                              ▼
                    Telegram notification
                              │
                              ▼
                  ElevenLabs speaks confirmation
```

### Approach 2: Claude as brain (claude-brain branch)

```
Voice/Text input
        │
        ▼
  POST /api/chat  ──▶  Claude API (tool_use)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       lookup_client   lookup_service   create_invoice
       (Notion API)    (Notion API)         │
                                    ┌───────┼───────┐
                                    ▼       ▼       ▼
                               Gen PDF  Upload   Send email
                                        Drive    (SMTP/Gmail)
                                            │
                                            ▼
                                    Telegram notify
                                            │
                                            ▼
                                   Response text for TTS
```

Claude handles multi-turn conversation natively — looks up data, asks for confirmation, then executes. Single `/api/chat` endpoint replaces three separate tool endpoints.

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Gmail API

```bash
# 1. Create project at https://console.cloud.google.com
# 2. Enable Gmail API
# 3. Create OAuth2 credentials (Desktop app)
# 4. Download JSON → save as credentials/gmail_credentials.json

python scripts/gmail_setup.py
# Browser opens → sign in → done
```

### 3. Configure environment

```bash
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, NOTION_TOKEN, TELEGRAM_BOT_TOKEN, etc.
```

### 4. Start the server

```bash
python main.py
```

Server runs on `http://localhost:8000`.

### 5. Expose for ElevenLabs (development)

```bash
ngrok http 8000
# Copy the https URL → configure in ElevenLabs dashboard
```

---

## Notion — Company OS

Client and service data is stored in Notion. The agent queries these databases when creating invoices.

### Clients DB

| Property | Type | Example |
|---|---|---|
| Nosaukums | title | SIA "Desktop Commander" |
| Reģ. nr. | text | 40203666483 |
| PVN nr. | text | LV40203666483 |
| Adrese | text | Elizabetes iela 8-6, Rīga, LV-1010 |
| E-pasts | email | jurgis@desktopcommander.lv |
| Banka / IBAN | text | Swedbank / LV80HABA... |
| Apmaksas termiņš | select | 7 / 14 / 30 dienas |

### Services DB

| Property | Type | Example |
|---|---|---|
| Pakalpojums | title | Venue Rental |
| Likme (EUR) | number | 150 |
| Mērvienība | select | stunda / diena / projekts |
| PVN likme (%) | number | 0.21 |
| Kategorija | select | Telpa |

Pre-loaded: 5 clients, 5 services. See `OPERATOR_PLAN.md` for full schema and API examples.

---

## Claude Brain (`/api/chat`)

The `claude-brain` branch adds Claude API as the conversation engine with native tool_use.

### How it works

1. Send text to `/api/chat` with a session ID
2. Claude decides which tools to call (lookup_client, lookup_service, create_invoice)
3. Tools execute directly in Python — no HTTP round-trips
4. Claude confirms details with user before executing
5. Multi-turn conversation state maintained per session

### Example conversation

```bash
# Turn 1: Request
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s1", "text": "Invoice Desktop Commander for 8 hours venue rental"}'

# Response: Claude looks up client + service, presents summary, asks to confirm
# {
#   "text": "Klientam: SIA Desktop Commander. Venue Rental 8h × 150 EUR = 1200 EUR + PVN 252 EUR = 1452 EUR. Apstiprināt?",
#   "actions_taken": [{"tool": "lookup_client", ...}, {"tool": "lookup_service", ...}]
# }

# Turn 2: Confirm
curl -X POST http://localhost:8000/api/chat \
  -d '{"session_id": "s1", "text": "yes, send it"}'

# Response: Invoice created, PDF generated, email sent
# {
#   "text": "Rēķins INV-2026-1001 par 1 452,00 EUR izveidots un nosūtīts.",
#   "actions_taken": [{"tool": "create_invoice", ...}]
# }
```

### Reset session

```bash
curl -X POST http://localhost:8000/api/chat/reset \
  -d '{"session_id": "s1"}'
```

---

## ElevenLabs Setup

1. Create a Conversational AI agent at [elevenlabs.io](https://elevenlabs.io)
2. Paste `elevenlabs_config/agent_prompt.md` as the system prompt
3. Add 3 server tools, each pointing to your server:

| Tool | URL |
|---|---|
| `lookup_contact` | `https://YOUR_URL/api/tools/lookup-contact` |
| `search_emails` | `https://YOUR_URL/api/tools/search-emails` |
| `create_task` | `https://YOUR_URL/api/tools/create-task` |

4. Assign a phone number (ElevenLabs or Twilio)

See `elevenlabs_config/setup_guide.md` for detailed parameter schemas.

---

## Project Structure

```
real-estate-voice-operator/
├── server/
│   ├── app.py                 # FastAPI: ElevenLabs tools + /api/chat (Claude)
│   ├── elevenlabs_handler.py  # ElevenLabs tool dispatcher
│   └── config.py              # All env vars and config
├── brain/
│   ├── claude_brain.py        # Claude API conversation handler + tool loop
│   ├── system_prompt.py       # System prompt + tool definitions
│   └── tools.py               # Tool execution (Notion, PDF, email)
├── gmail/
│   └── sender.py              # Gmail API: send + search (OAuth2)
├── email_sender/
│   └── sender.py              # SMTP direct email (alternative to Gmail)
├── notion/
│   └── client.py              # Notion API: client & service lookup
├── llm/
│   ├── models.py              # Pydantic models (InvoiceData, LineItem, etc.)
│   ├── orchestrator.py        # Main pipeline: PDF → Drive → Email → Telegram
│   └── prompts.py             # Success message templates
├── pdf_generator/
│   ├── invoice.py             # reportlab PDF (seller/buyer, line items, VAT)
│   ├── templates.py           # Locale-aware formatters (LV/RU/EN)
│   ├── DejaVuSans.ttf         # Bundled font for Latvian/Cyrillic
│   └── DejaVuSans-Bold.ttf
├── email_drafter/
│   ├── drafter.py             # Template loader + renderer
│   └── templates/             # 12 txt templates (4 actions × 3 languages)
├── gdrive/
│   └── uploader.py            # Drive upload + local fallback
├── telegram/
│   └── bot.py                 # Telegram notifications
├── data/
│   └── contacts.json          # Local contact fallback
├── elevenlabs_config/
│   ├── agent_prompt.md        # System prompt for ElevenLabs agent
│   └── setup_guide.md         # ElevenLabs setup guide
├── samples/
│   └── invoice_sample_*.pdf   # Sample generated invoices
├── scripts/
│   ├── gmail_setup.py         # One-time Gmail OAuth2 setup
│   └── test_full_pipeline.py  # Offline pipeline test
├── credentials/               # .gitignored — OAuth tokens
├── tests/                     # pytest test suite
├── main.py                    # Entry point
├── OPERATOR_PLAN.md           # Full project plan + Notion schema
└── requirements.txt
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | Claude brain: send text, get response + tool results |
| `POST` | `/api/chat/reset` | Reset a Claude chat session |
| `POST` | `/api/tools/lookup-contact` | ElevenLabs tool: find contact by name |
| `POST` | `/api/tools/search-emails` | ElevenLabs tool: search Gmail inbox |
| `POST` | `/api/tools/create-task` | ElevenLabs tool: invoice/reminder/follow-up |
| `POST` | `/api/test` | Direct test (no ElevenLabs/Claude needed) |
| `GET` | `/health` | Health check |

---

## Supported Operations

| Voice command | Action | Languages |
|---|---|---|
| "Send invoice to [name] for [service]" | `send_invoice` | LV / RU / EN |
| "Send payment reminder to [name]" | `send_reminder` | LV / RU / EN |
| "Follow up with [name] about [property]" | `follow_up` | LV / RU / EN |
| "Request documents from [name]" | `request_documents` | LV / RU / EN |

---

## Testing

```bash
# Unit tests
pytest tests/ -v

# Offline pipeline test
python scripts/test_full_pipeline.py
```

---

## Environment Variables

See `.env.example` for all variables. Key ones:

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | For `/api/chat` | Claude API key (brain) |
| `GMAIL_CREDENTIALS_PATH` | For email | Path to OAuth2 credentials JSON |
| `NOTION_TOKEN` | For DB lookup | Notion integration token |
| `NOTION_CLIENTS_DB` | For DB lookup | Notion Clients database ID |
| `NOTION_SERVICES_DB` | For DB lookup | Notion Services database ID |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot for notifications |
| `TELEGRAM_CHAT_ID` | No | Telegram chat to notify |
| `GDRIVE_CREDENTIALS_PATH` | No | Google Drive service account |
| `GDRIVE_FOLDER_ID` | No | Drive folder for invoice PDFs |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | For SMTP email | Direct SMTP (alternative to Gmail) |
