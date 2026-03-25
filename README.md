# Real Estate Voice Operator

A voice-driven real estate operations assistant. Call a phone number, ask to send an invoice — it generates a PDF, sends the email via Gmail, and notifies you on Telegram.

**Hackathon build — 12 hours.**

---

## Architecture

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
# Fill in: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, NOTION_TOKEN (if using Notion)
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
│   ├── app.py              # FastAPI app, ElevenLabs webhook endpoints
│   ├── elevenlabs_handler.py  # Tool call dispatcher
│   └── config.py           # Env vars, config
├── gmail/
│   └── sender.py           # Gmail API: send + search (OAuth2)
├── notion/
│   └── client.py           # Notion API: client & service lookup
├── llm/
│   ├── models.py           # Pydantic models (InvoiceData, LineItem, etc.)
│   ├── orchestrator.py     # Main pipeline brain
│   └── prompts.py          # Success message templates
├── pdf_generator/
│   ├── invoice.py          # reportlab PDF generation (DejaVu fonts)
│   └── templates.py        # Locale-aware formatters
├── email_drafter/
│   ├── drafter.py          # Template loader + renderer
│   └── templates/          # 12 txt templates (4 actions × 3 languages)
├── gdrive/
│   └── uploader.py         # Drive upload + local fallback
├── telegram/
│   └── bot.py              # Telegram notifications
├── data/
│   └── contacts.json       # Local contact database
├── mock/
│   └── mock_gdrive.py      # Fake Drive upload for dev
├── elevenlabs_config/
│   ├── agent_prompt.md     # System prompt for ElevenLabs agent
│   └── setup_guide.md      # Step-by-step ElevenLabs setup
├── scripts/
│   ├── gmail_setup.py      # One-time Gmail OAuth2 setup
│   ├── test_call.py        # Live server tests
│   └── test_full_pipeline.py  # Offline pipeline test
├── credentials/            # .gitignored — OAuth tokens go here
├── tests/                  # pytest test suite
└── main.py                 # Entry point
```

---

## Supported Operations

| Voice command | Action | Languages |
|---|---|---|
| "Send invoice to [name] for [service]" | `send_invoice` | LV / RU / EN |
| "Send payment reminder to [name]" | `send_reminder` | LV / RU / EN |
| "Follow up with [name] about [property]" | `follow_up` | LV / RU / EN |
| "Request documents from [name]" | `request_documents` | LV / RU / EN |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/tools/lookup-contact` | ElevenLabs tool: find contact by name |
| `POST` | `/api/tools/search-emails` | ElevenLabs tool: search Gmail inbox |
| `POST` | `/api/tools/create-task` | ElevenLabs tool: invoice/reminder/follow-up |
| `POST` | `/api/test` | Direct test (no ElevenLabs needed) |
| `GET` | `/health` | Health check |

### Direct test example

```bash
curl -X POST http://localhost:8000/api/test \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "send_invoice",
    "params": {
      "client_name": "Jānis Bērziņš",
      "client_email": "janis@example.lv",
      "service_name": "consultation",
      "quantity": 2,
      "language": "lv"
    }
  }'
```

---

## Testing

```bash
# Unit tests
pytest tests/ -v

# Offline pipeline test (no API keys needed)
python scripts/test_full_pipeline.py
```

---

## Environment Variables

See `.env.example` for all variables. Key ones:

| Variable | Required | Description |
|---|---|---|
| `GMAIL_CREDENTIALS_PATH` | Yes | Path to OAuth2 credentials JSON |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot for notifications |
| `TELEGRAM_CHAT_ID` | No | Telegram chat to notify |
| `NOTION_TOKEN` | No | Notion integration token for client/service DB |
| `GDRIVE_CREDENTIALS_PATH` | No | Google Drive service account |
| `GDRIVE_FOLDER_ID` | No | Drive folder for invoice PDFs |
