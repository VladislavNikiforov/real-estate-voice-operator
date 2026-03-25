# Real Estate Voice Operator

A voice-driven real estate operations assistant powered by [Vapi](https://vapi.ai) phone calls and automated via [Desktop Commander](https://github.com/wonderwhy-er/DesktopCommanderMCP).

**Hackathon build — 10 hours, ships working.**

---

## Architecture

```
Agent speaks command (phone call via Vapi)
        │
        ▼
Vapi STT + LLM  ──tool-call──▶  Our FastAPI Webhook
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              Generate PDF       Upload to Drive      Draft email
              (reportlab)       (Google Drive API)  (txt templates)
                    │                   │                   │
                    └───────────────────┴───────────────────┘
                                        │
                                        ▼
                              Build OpenClaw prompt
                                        │
                              POST to OpenClaw VM
                                        │
                                        ▼
                          Desktop Commander opens Gmail
                          → composes → sends email
                                        │
                                        ▼
                         Vapi speaks confirmation to caller
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

Required for full functionality:
- `OPENCLAW_URL` — URL of the OpenClaw VM server
- Google Drive: place `service_account.json` in project root (or set `GDRIVE_SERVICE_ACCOUNT_PATH`)

All other vars have defaults for local development.

### 3. Start the server

```bash
# Start mock OpenClaw + main server
bash scripts/start_dev.sh

# Or just the main server
python main.py
```

Server runs on `http://localhost:8000`.

### 4. Expose to Vapi (development)

```bash
ngrok http 8000
# Copy the https URL → set as Vapi server URL
```

---

## Testing

### Offline pipeline test (no server needed, no API keys)

```bash
python scripts/test_full_pipeline.py
```

This tests: PDF generation → mock Drive upload → email drafting → OpenClaw prompt building.

### Unit tests

```bash
pytest tests/ -v
```

### Live server test (server must be running)

```bash
# Terminal 1
python main.py

# Terminal 2
python scripts/test_call.py
```

---

## Project Structure

```
real-estate-voice-operator/
├── server/
│   ├── app.py              # FastAPI app, endpoints
│   ├── vapi_handler.py     # Vapi tool-call dispatcher
│   └── config.py           # Env vars, config
├── llm/
│   ├── models.py           # Pydantic models (InvoiceData, EmailDraft, etc.)
│   ├── orchestrator.py     # Main pipeline brain
│   └── prompts.py          # Success message templates
├── pdf_generator/
│   ├── invoice.py          # reportlab PDF generation
│   └── templates.py        # Locale-aware formatters
├── email_drafter/
│   ├── drafter.py          # Template loader + renderer
│   └── templates/          # 12 txt templates (4 actions × 3 languages)
├── openclaw_prompt/
│   ├── generator.py        # Build OpenClawInstruction
│   └── templates.py        # Gmail prompt templates
├── gdrive/
│   └── uploader.py         # Drive upload + local fallback
├── openclaw/               # TODO: OpenClaw person implements this
│   ├── receiver.py         # FastAPI receiver skeleton
│   ├── desktop_commander.py
│   └── gmail_flow.py
├── mock/
│   ├── mock_openclaw.py    # Fake OpenClaw server (port 8888)
│   └── mock_gdrive.py      # Fake Drive upload
├── vapi_config/
│   ├── assistant_prompt.md # Paste into Vapi dashboard
│   ├── tools.json          # Tool definitions for Vapi
│   └── setup_guide.md      # Step-by-step Vapi setup
├── tests/                  # pytest test suite
├── scripts/
│   ├── start_dev.sh        # Dev startup
│   ├── test_call.py        # Live server tests
│   └── test_full_pipeline.py  # Offline pipeline test
└── main.py                 # Entry point
```

---

## Supported Operations

| Voice command | Action | Languages |
|---|---|---|
| "Send invoice to [name] for [property]" | `send_invoice` | LV / RU / EN |
| "Send payment reminder to [name]" | `send_reminder` | LV / RU / EN |
| "Follow up with [name] about [property]" | `follow_up` | LV / RU / EN |
| "Request documents from [name]" | `request_documents` | LV / RU / EN |

---

## Vapi Setup

See [`vapi_config/setup_guide.md`](vapi_config/setup_guide.md) for the full 10-step guide.

Quick version:
1. Create Vapi assistant
2. Paste [`vapi_config/assistant_prompt.md`](vapi_config/assistant_prompt.md) as system prompt
3. Add tools from [`vapi_config/tools.json`](vapi_config/tools.json)
4. Set server URL to `https://YOUR_NGROK_URL/api/vapi/tool-call`
5. Call the number and speak your command

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/vapi/tool-call` | Main Vapi webhook |
| `POST` | `/api/test` | Direct test (no Vapi wrapper needed) |
| `GET` | `/health` | Health check |

### Direct test example

```bash
curl -X POST http://localhost:8000/api/test \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "send_invoice",
    "client_name": "Jānis Bērziņš",
    "client_email": "janis@example.lv",
    "property_id": "apt-3",
    "amount": 85000,
    "language": "lv"
  }'
```

---

## OpenClaw Integration

The `openclaw/` directory is the integration point for the Desktop Commander automation. It receives a structured prompt and executes Gmail actions.

See [`openclaw/README.md`](openclaw/README.md) for the TODO list and integration options.

---

## Team

- **Voice Person** — Vapi setup, FastAPI webhook, pipeline orchestration (this repo)
- **OpenClaw Person** — Desktop Commander VM, Gmail automation (`openclaw/` directory)
