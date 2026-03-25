# 🖥️ OpenClaw + Desktop Commander Module

**Owner:** `@openclaw-person`

## Your Job

Build the bridge between our webhook server and Desktop Commander on the VM.

## What You Receive

HTTP POST to your endpoint on the VM:

```json
{
  "action": "send_email_gmail",
  "email": {
    "to": "janis@example.com",
    "subject": "Invoice INV-2026-1001 — Property apt-3",
    "body": "Dear Jānis...\n\nInvoice document: https://drive.google.com/file/d/xxx/view",
    "drive_link": "https://drive.google.com/file/d/xxx/view?usp=sharing",
    "language": "lv"
  },
  "prompt": "Open Gmail in the browser and compose a new email.\n\nRECIPIENT: janis@example.com\nSUBJECT: Invoice INV-2026-1001..."
}
```

## What You Do

1. Receive the request on your VM endpoint
2. Launch/connect to Desktop Commander
3. Pass the `prompt` field to Desktop Commander
4. Desktop Commander opens Gmail in browser → clicks Compose → fills To/Subject/Body → sends
5. Return success/failure JSON

## Your Endpoint Contract

- Listen on: `http://VM_IP:8888`
- `POST /execute` → receives JSON above
- `GET /health` → returns `{"status": "ok"}`

### Response format:
```json
{"success": true, "message": "Email sent successfully", "execution_time": 15.3}
```
or on failure:
```json
{"success": false, "message": "Failed: compose button not found", "execution_time": 8.1}
```

## Run:
```bash
pip install fastapi uvicorn
uvicorn openclaw.receiver:app --host 0.0.0.0 --port 8888
```

## Priority timeline:
- **Hour 3**: Endpoint receives + logs prompts ✓
- **Hour 5**: Desktop Commander opens Gmail + composes
- **Hour 7**: Full send working end-to-end
