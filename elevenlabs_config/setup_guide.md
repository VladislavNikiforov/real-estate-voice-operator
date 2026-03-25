# ElevenLabs Agent Setup Guide

## Step 1 — Start your server + ngrok

```bash
# Terminal 1
python main.py

# Terminal 2
ngrok http 8000
# Copy the https URL — you'll need it in Step 4
```

## Step 2 — Create ElevenLabs Agent

1. Go to elevenlabs.io → **Conversational AI** → **Agents** → **Create Agent**
2. Choose **Blank template**

## Step 3 — Configure the Agent

**System Prompt tab:**
- Paste the contents of `elevenlabs_config/agent_prompt.md`

**Voice tab:**
- Pick any voice you like (Rachel works well for English, use a native speaker voice for LV/RU)

**LLM tab:**
- Model: `claude-3-5-sonnet` or `gpt-4o` (both work)
- Temperature: `0.3` (keep it focused)

## Step 4 — Add Tools

In the **Tools** tab, add each tool from `elevenlabs_config/agent_tools.json`:

For each tool:
1. Click **Add Tool** → **Webhook**
2. Set the tool name (e.g. `send_invoice`)
3. Set URL to: `https://YOUR_NGROK_URL/api/elevenlabs/tool-call`
4. Method: **POST**
5. Add the parameters as listed in `agent_tools.json`
6. Check **Required** boxes for required fields

## Step 5 — Configure Post-Call Webhook (for transcripts)

In **Agent Settings** → **Post-call webhook**:
- URL: `https://YOUR_NGROK_URL/api/elevenlabs/post-call`
- Method: POST

This fires after every call ends and sends the full transcript to your server.

## Step 6 — Connect a Phone Number

**Option A: Use ElevenLabs phone number (easiest)**
1. In agent settings → **Phone** tab
2. Click **Get phone number** (uses ElevenLabs + Twilio under the hood)
3. You'll get a number you can call directly

**Option B: Bring your own Twilio number**
1. In Twilio, create a phone number
2. In ElevenLabs → **Phone Numbers** → **Add** → Twilio
3. Enter your Twilio Account SID + Auth Token + phone number

## Step 7 — Test

```bash
# Check server is running
curl http://localhost:8000/health

# Test tool call directly (without calling)
curl -X POST http://localhost:8000/api/elevenlabs/tool-call \
  -H "Content-Type: application/json" \
  -d '{
    "type": "tool_call",
    "tool_name": "send_invoice",
    "tool_call_id": "test_001",
    "parameters": {
      "client_name": "Test Client",
      "client_email": "test@example.com",
      "property_id": "apt-1",
      "amount": 1200,
      "language": "en"
    }
  }'
```

Call the phone number and say: *"I want to send an invoice to John Smith at john@example.com for apartment 3, amount 1200 euros, in English."*

## Endpoints Summary

| Endpoint | Purpose |
|---|---|
| `POST /api/elevenlabs/tool-call` | ElevenLabs calls this when agent triggers a tool |
| `POST /api/elevenlabs/post-call` | ElevenLabs sends full transcript after call ends |
| `POST /api/vapi/tool-call` | Old Vapi endpoint (still works) |
| `POST /api/test` | Direct test without any voice platform |
| `GET /health` | Health check |
