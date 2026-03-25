#!/usr/bin/env python3
"""Test the entire pipeline with mocks — no server needed, no API keys.

Prints every step so you can verify the whole flow works.

Usage:
    python scripts/test_full_pipeline.py
"""

import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENCLAW_URL",       "http://localhost:8888")
os.environ.setdefault("COMPANY_NAME",       "Demo Real Estate SIA")
os.environ.setdefault("COMPANY_ADDRESS",    "Brīvības iela 100, Rīga")
os.environ.setdefault("COMPANY_BANK",       "Swedbank")
os.environ.setdefault("COMPANY_IBAN",       "LV00HABA0000000000000")
os.environ.setdefault("COMPANY_PHONE",      "+371 20000000")

_G = "\033[92m"; _C = "\033[96m"; _Y = "\033[93m"; _R = "\033[91m"; _B = "\033[1m"; _N = "\033[0m"

def step(n: int, label: str) -> None:
    print(f"\n{_B}{_C}Step {n}: {label}{_N}")
    print("─" * 55)


async def main():
    print(f"\n{_B}Real Estate Voice Operator — Full Pipeline Test{_N}")
    print("=" * 55)
    print("Using mocks for Drive + OpenClaw\n")

    params = {
        "client_name":  "Jānis Bērziņš",
        "client_email": "janis@example.lv",
        "property_id":  "apt-3",
        "amount":       85000,
        "language":     "lv",
    }
    print(f"Input params: {params}\n")

    # ── Step 1: Generate PDF ──────────────────────────────────
    step(1, "Generate Invoice PDF")
    from pdf_generator.invoice import generate_invoice_pdf
    from pdf_generator.templates import format_date
    from llm.models import InvoiceData

    invoice_number = "INV-2026-9999"
    data = InvoiceData(
        invoice_number=invoice_number,
        client_name=params["client_name"],
        client_email=params["client_email"],
        property_id=params["property_id"],
        amount=params["amount"],
        language=params["language"],
        date=format_date(params["language"]),
        company_name="Demo Real Estate SIA",
        company_address="Brīvības iela 100, Rīga",
        company_bank="Swedbank",
        company_iban="LV00HABA0000000000000",
        company_phone="+371 20000000",
    )
    pdf_bytes = generate_invoice_pdf(data)
    print(f"{_G}✓ PDF generated: {len(pdf_bytes):,} bytes{_N}")
    assert pdf_bytes[:4] == b"%PDF"

    # ── Step 2: Upload to Drive (mock) ───────────────────────
    step(2, "Upload to Google Drive (mock fallback)")
    from mock.mock_gdrive import fake_upload
    drive_link = fake_upload(pdf_bytes, f"invoice_{invoice_number}.pdf")
    print(f"{_G}✓ Drive link: {drive_link}{_N}")

    # ── Step 3: Draft email ───────────────────────────────────
    step(3, "Draft email (Latvian template)")
    from email_drafter.drafter import draft_email
    email_params = {**params, "invoice_number": invoice_number}
    email = draft_email("invoice", email_params, drive_link)
    print(f"{_G}✓ Email drafted:{_N}")
    print(f"   To:      {email.to}")
    print(f"   Subject: {email.subject}")
    print(f"   Body preview: {email.body[:120].replace(chr(10), ' ')!r}")

    # ── Step 4: Generate OpenClaw prompt ─────────────────────
    step(4, "Generate OpenClaw / Desktop Commander prompt")
    from openclaw_prompt.generator import build_openclaw_instruction
    instruction = build_openclaw_instruction(email)
    print(f"{_G}✓ Instruction built:{_N}")
    print(f"   Action: {instruction.action}")
    print(f"   Prompt preview:\n")
    for line in instruction.prompt.strip().split("\n")[:10]:
        print(f"     {line}")
    print("     ...")

    # ── Step 5: POST to mock OpenClaw ─────────────────────────
    step(5, "Send to mock OpenClaw (simulated, no real server)")
    print(f"{_Y}ℹ️  Skipping HTTP call in pipeline test (use test_call.py for live test){_N}")
    print(f"   Would POST to: {os.environ['OPENCLAW_URL']}/execute")
    print(f"   Payload: action={instruction.action}, to={instruction.email.to}")

    # ── Summary ───────────────────────────────────────────────
    print(f"\n{'=' * 55}")
    print(f"{_B}{_G}✅ Full pipeline test passed!{_N}")
    print(f"   Invoice:    {invoice_number}")
    print(f"   Drive link: {drive_link[:60]}...")
    print(f"   Email to:   {email.to}")
    print(f"   Check:      generated_files/invoice_{invoice_number}.pdf\n")


if __name__ == "__main__":
    asyncio.run(main())
