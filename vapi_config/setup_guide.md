# Vapi Setup (15 min)

## Step-by-step

1. Go to [dashboard.vapi.ai](https://dashboard.vapi.ai) → sign up (free $10 credits)
2. **Create Assistant** → Blank → name "RE Operator"
3. **System Prompt**: paste the full contents of `assistant_prompt.md`
4. **Model**: Claude Sonnet 4.5 or GPT-4o
5. **Transcriber**: Deepgram Nova 2 (best for LV/RU)
6. **Voice**: ElevenLabs → pick a professional male/female voice
7. **Tools**: Add all 4 tools from `tools.json`
   - In dashboard: Tools tab → Add tool → paste each tool JSON
8. **Server URL**: `https://YOUR-NGROK-URL.ngrok.io/api/vapi/tool-call`
   - Start ngrok: `ngrok http 8000`
   - Copy the `https://` URL
9. **Phone Numbers** → Create → assign to this assistant
10. Call and test!

## Webhook URL format

```
POST https://YOUR-NGROK-URL.ngrok.io/api/vapi/tool-call
```

Vapi sends tool calls here. Our server processes them and returns the spoken result.

## Testing without a phone call

Use `scripts/test_call.py` to simulate a Vapi tool call locally:
```bash
python scripts/test_call.py
```

## Troubleshooting

- **Vapi not calling the tool**: Check server URL is correct, ngrok is running, /health returns 200
- **Tool call not reaching server**: Check ngrok logs (`ngrok http 8000` shows requests)
- **Invoice not generating**: Check `generated_files/` folder — PDF should appear there
- **OpenClaw not responding**: Normal in dev — server falls back and logs the prompt to console
