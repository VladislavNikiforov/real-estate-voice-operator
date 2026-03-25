# Real Estate Voice Operator

Voice-driven invoice assistant for real estate — powered by ElevenLabs Conversational AI, Claude API, Notion, and Twilio.

**Hackathon build — ships working.**

---

## Architecture

```
Incoming call (Twilio)
        │
        ▼
ElevenLabs Conversational AI (voice ↔ transcript)
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
                               Gen PDF  e-mail   subject/text
                                            │
                                            ▼
                                  Send email (SMTP/Gmail)
                                            │
                                            ▼
                              Response text (ElevenLabs)
```

Twilio receives the phone call and bridges it to ElevenLabs via WebSocket. ElevenLabs handles voice-to-text and text-to-voice. After the call ends, the transcript is sent to Claude brain, which orchestrates tools: looking up clients/services in Notion, generating PDF invoices, and sending emails.

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
npm install   # for sendmail_skill
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

Required:
- `ANTHROPIC_API_KEY` — Claude API key
- `NOTION_TOKEN` — Notion integration token
- `NOTION_CLIENTS_DB` — Notion clients database ID
- `NOTION_SERVICES_DB` — Notion services database ID

Optional:
- `ELEVENLABS_AGENT_ID` — ElevenLabs agent for Twilio bridge
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` — Telegram notifications
- Chrome with remote debugging on port 9222 (for sendmail_skill)

### 3. Start the server

```bash
python main.py
```

Server runs on `http://localhost:8000`.

### 4. Open the dashboard

```
http://localhost:8000/dashboard
```

### 5. Expose for ElevenLabs (development)

```bash
ngrok http 8000
# Set https://YOUR_URL.ngrok-free.app/api/elevenlabs/post-call
# as the post-call webhook in ElevenLabs
```

---

## Notion Database Schema

### Clients (`NOTION_CLIENTS_DB`)

| Property | Type | Description |
|---|---|---|
| Nosaukums | Title | Client / company name |
| Reģ. nr. | Text | Registration number |
| PVN nr. | Text | VAT number |
| Adrese | Text | Address |
| E-pasts | Email | Email address |
| Telefons | Phone | Phone number |
| Banka | Text | Bank name |
| IBAN | Text | Bank account |
| Apmaksas termiņš | Text | Payment terms |
| Kontaktpersona | Text | Contact person |

### Services (`NOTION_SERVICES_DB`)

| Property | Type | Description |
|---|---|---|
| Pakalpojums | Title | Service name |
| Apraksts | Text | Description |
| Mērvienība | Text | Unit (h, m², pcs) |
| Likme (EUR) | Number | Rate in EUR |
| PVN likme (%) | Number | VAT rate |
| Kategorija | Select | Category |

---

## Project Structure

```
real-estate-voice-operator/
├── server/
│   ├── app.py                # FastAPI app, all endpoints
│   ├── elevenlabs_handler.py # Post-call transcript handler
│   └── config.py             # Env vars, config
├── brain/
│   ├── claude_brain.py       # Claude API multi-turn conversation
│   ├── system_prompt.py      # System prompt + tool definitions
│   └── tools.py              # Tool dispatcher (Notion + pipeline)
├── llm/
│   ├── models.py             # Pydantic models (InvoiceData, LineItem, etc.)
│   ├── orchestrator.py       # Invoice pipeline (PDF → email → send)
│   └── prompts.py            # Success/error message templates
├── notion/
│   └── client.py             # Notion API (lookup/create clients & services)
├── pdf_generator/
│   ├── invoice.py            # reportlab PDF generation
│   └── templates.py          # Locale-aware formatters
├── email_drafter/
│   ├── drafter.py            # Template loader + renderer
│   └── templates/            # txt templates (actions × languages)
├── dashboard/
│   ├── events.py             # SSE event bus + stats tracking
│   └── index.html            # Live dashboard frontend
├── scripts/
│   └── sendmail_skill/
│       └── send-gmail.js     # Puppeteer Gmail sender via Chrome
├── generated_files/          # Saved invoice PDFs
└── main.py                   # Entry point
```

---

## Supported Operations

| Voice command | Tool | Languages |
|---|---|---|
| "Send invoice to [name] for [service]" | `create_invoice` | LV / RU / EN |
| "Look up client [name]" | `lookup_client` | LV / RU / EN |
| "Look up service [name]" | `lookup_service` | LV / RU / EN |
| "Add new client [name]" | `create_client` | LV / RU / EN |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/elevenlabs/post-call` | ElevenLabs post-call webhook |
| `POST` | `/api/elevenlabs/twilio-voice` | Twilio → ElevenLabs bridge |
| `POST` | `/api/chat` | Direct Claude brain conversation |
| `POST` | `/api/chat/reset` | Reset conversation session |
| `POST` | `/api/test/transcript` | Test transcript → pipeline flow |
| `GET`  | `/dashboard` | Live pipeline dashboard |
| `GET`  | `/api/events` | SSE stream for dashboard |
| `GET`  | `/api/dashboard/state` | Dashboard stats |
| `GET`  | `/health` | Health check |

---

## Live Dashboard

The dashboard at `/dashboard` shows real-time pipeline execution during voice calls:

- Left panel: call transcript (user ↔ operator)
- Right panel: pipeline steps with timing (PDF → email → send)
- Notion toast notifications when new clients are added
- Bottom stats bar: invoices today, total amount, active calls

---

## Team

Built at BADideas hackathon by a team of 4:
Sergei Goncharenko
Vladislav Nikiforov
Kaspars Kondratjuks
Raghav Joshi



