# ElevenLabs Agent Setup Guide

## 1. Create Agent

1. Go to [elevenlabs.io](https://elevenlabs.io) → Agents (Conversational AI)
2. Click "Create Agent"
3. Name: **Operator Email Assistant**
4. First message: **"Hi, this is your Operator assistant. How can I help you today?"**
5. Copy the system prompt from `agent_prompt.md` into the Agent Prompt field
6. Voice: pick a professional voice (e.g. "Adam", "Rachel", or "Charlie")
7. Language: set to **auto-detect**

## 2. Configure Tools

Add 3 tools in the Agent dashboard. Each tool is a **Webhook (Server Tool)**.

### Tool 1: lookup_contact

- **Name:** lookup_contact
- **Description:** Find a contact's email address by their name
- **Method:** POST
- **URL:** `https://YOUR_SERVER/api/tools/lookup-contact`
- **Body parameters:**
  - `name` (string, required): "The name of the person to look up"

### Tool 2: search_emails

- **Name:** search_emails
- **Description:** Search recent emails from or about a person
- **Method:** POST
- **URL:** `https://YOUR_SERVER/api/tools/search-emails`
- **Body parameters:**
  - `query` (string, required): "Search query — person name, email, or topic"

### Tool 3: create_task

- **Name:** create_task
- **Description:** Create and execute an email task (send invoice, reminder, follow-up, or document request). Call this ONLY after confirming all details with the user.
- **Method:** POST
- **URL:** `https://YOUR_SERVER/api/tools/create-task`
- **Body parameters:**
  - `action` (string, required): "The action to perform. One of: send_invoice, send_reminder, follow_up, request_documents"
  - `client_name` (string, required): "Full name of the recipient"
  - `client_email` (string, required): "Email address of the recipient"
  - `property_id` (string, required): "Property or room identifier, e.g. room-5, apt-3"
  - `amount` (number, optional): "Total amount for invoice in EUR"
  - `language` (string, required): "Language code: en, lv, or ru"
  - `notes` (string, optional): "Additional notes or details for the email"

## 3. Phone Number

- **Option A:** ElevenLabs dashboard → Phone → Buy a number (~$2/mo)
- **Option B:** Connect your Twilio number via Integrations → Twilio
- **Option C (fallback):** Use the web widget — embed in an HTML page

## 4. Expose Your Backend

Your backend must be reachable from the internet for ElevenLabs to call the webhooks.

For development/demo:
```bash
# Install ngrok: https://ngrok.com
ngrok http 8000
```

Then use the ngrok URL (e.g. `https://abc123.ngrok.io`) as YOUR_SERVER in the tool URLs above.

## 5. Test

1. Start your backend: `python main.py`
2. Start ngrok: `ngrok http 8000`
3. Update tool URLs in ElevenLabs dashboard with ngrok URL
4. Click "Test" in ElevenLabs dashboard
5. Say: "I need to send an invoice to John Smith for office room 5, 3 days at 80 dollars per day"
6. The agent should:
   - Call lookup_contact → find john.smith@gmail.com
   - Call search_emails → find his recent booking email
   - Confirm details with you
   - Call create_task → generate invoice + send email
