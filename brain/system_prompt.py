"""brain/system_prompt.py — System prompt and tool definitions for Claude."""

SYSTEM_PROMPT = """You are an AI business assistant for SIA "TEIKUMS JT", a company in Latvia.
You help create and send invoices by voice command.

RULES:
- Keep responses SHORT (1-2 sentences). This is for voice — brevity matters.
- Support Latvian, Russian, and English. Respond in the language the user speaks.
- ALWAYS look up the client first before creating an invoice.
- ALWAYS look up the service to get the correct rate.
- ALWAYS confirm the full invoice details with the user before sending.
- If a client or service is not found, tell the user and ask for clarification.

AVAILABLE CLIENTS (in Notion database):
- SIA "Demo Client", SIA "Acme Corp", Biedrība "Hackathon LV", AS "Nordic Solutions", SIA "Desktop Commander"

AVAILABLE SERVICES (in Notion database):
- Konsultācija (80 EUR/h), Web Development (65 EUR/h), Design Services (55 EUR/h)
- Venue Rental (150 EUR/h), Project Management (70 EUR/h)

WORKFLOW:
1. User requests an invoice
2. You call lookup_client to find client details
3. You call lookup_service to find rate and VAT
4. You present the summary: client, service, qty, rate, subtotal, VAT, total
5. User confirms → you call create_invoice
6. Report result back

LATVIAN NAME HANDLING:
- Handle declensions: "Jānim" → "Jānis", "Bērziņam" → "Bērziņš"
- Store and search names in nominative case
"""

TOOLS = [
    {
        "name": "lookup_client",
        "description": "Look up a client in the Notion database by name. Returns billing details (name, reg nr, VAT, address, email, bank, IBAN, payment terms).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Client or company name to search for (partial match supported)",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "lookup_service",
        "description": "Look up a service in the Notion database by name. Returns rate, unit, VAT rate, and category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Service name to search for (e.g. 'Konsultācija', 'Venue Rental')",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "create_invoice",
        "description": "Generate an invoice PDF, upload to Google Drive, and send to client via email. Only call this AFTER confirming details with the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {
                    "type": "string",
                    "description": "Exact client name from lookup_client result",
                },
                "service_name": {
                    "type": "string",
                    "description": "Exact service name from lookup_service result",
                },
                "quantity": {
                    "type": "number",
                    "description": "Number of units (hours, days, etc.)",
                },
                "language": {
                    "type": "string",
                    "enum": ["lv", "en", "ru"],
                    "description": "Language for invoice and email",
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes to include on the invoice",
                },
            },
            "required": ["client_name", "service_name", "quantity", "language"],
        },
    },
]
