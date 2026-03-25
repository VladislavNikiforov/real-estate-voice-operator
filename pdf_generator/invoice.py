"""pdf_generator/invoice.py — Generate invoice PDFs using reportlab."""

import io
import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from llm.models import InvoiceData
from pdf_generator.templates import (
    format_amount, format_date,
    invoice_label, date_label, invoice_no_label, bill_to_label,
    description_label, amount_label, total_label, payment_details_label,
    transaction_description,
)

# ── Font registration ─────────────────────────────────────────
# DejaVu Sans covers Latvian extended Latin + Cyrillic.
# Falls back to Helvetica (ASCII-only) if font file not found.

_FONT_REGISTERED = False
_UNICODE_FONT = "Helvetica"  # overwritten below if DejaVu found

def _register_fonts() -> None:
    global _FONT_REGISTERED, _UNICODE_FONT
    if _FONT_REGISTERED:
        return

    search_paths = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
        Path("/Library/Fonts/DejaVuSans.ttf"),
        Path(os.path.expanduser("~")) / "Library/Fonts/DejaVuSans.ttf",
        Path(__file__).parent / "DejaVuSans.ttf",
    ]

    for p in search_paths:
        if p.exists():
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", str(p)))
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(p)))  # same file, bold via weight
                _UNICODE_FONT = "DejaVuSans"
                break
            except Exception:
                pass

    _FONT_REGISTERED = True


# ── Colours ───────────────────────────────────────────────────
_DARK  = colors.HexColor("#1a1a2e")
_RED   = colors.HexColor("#e63946")
_LIGHT = colors.HexColor("#f8f9fa")
_GRAY  = colors.HexColor("#6c757d")


def generate_invoice_pdf(data: InvoiceData) -> bytes:
    """Generate a PDF invoice and return raw bytes.

    Supports Latvian and Russian characters if DejaVu Sans is installed.
    Falls back to Helvetica (ASCII) gracefully.
    """
    _register_fonts()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    font     = _UNICODE_FONT
    font_b   = _UNICODE_FONT  # Bold variant (same file for DejaVu fallback)

    def style(size=10, bold=False, color=_DARK, align="LEFT"):
        return ParagraphStyle(
            "s",
            fontName=font_b if bold else font,
            fontSize=size,
            textColor=color,
            alignment={"LEFT": 0, "CENTER": 1, "RIGHT": 2}.get(align, 0),
            leading=size * 1.4,
        )

    story = []

    # ── Header ────────────────────────────────────────────────
    header_data = [[
        Paragraph(data.company_name, style(14, bold=True)),
        Paragraph(
            f'<font color="#e63946"><b>{invoice_label(data.language)}</b></font>',
            style(22, align="RIGHT"),
        ),
    ]]
    header_table = Table(header_data, colWidths=["50%", "50%"])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)

    sub_header = [[
        Paragraph(
            f"{data.company_address}<br/>{data.company_phone}",
            style(8, color=_GRAY),
        ),
        Paragraph(
            f"{invoice_no_label(data.language)} <b>{data.invoice_number}</b><br/>"
            f"{date_label(data.language)} {data.date}",
            style(9, align="RIGHT"),
        ),
    ]]
    sub_table = Table(sub_header, colWidths=["50%", "50%"])
    sub_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(sub_table)
    story.append(HRFlowable(width="100%", thickness=2, color=_DARK, spaceAfter=8))

    # ── Bill To ───────────────────────────────────────────────
    story.append(Paragraph(bill_to_label(data.language), style(8, color=_RED)))
    story.append(Paragraph(f"<b>{data.client_name}</b>", style(12, bold=True)))
    story.append(Paragraph(data.client_email, style(9, color=_GRAY)))
    story.append(Spacer(1, 8 * mm))

    # ── Line items table ──────────────────────────────────────
    formatted_amt = format_amount(data.amount, data.currency, data.language)
    items = [
        [
            Paragraph(f"<b>{description_label(data.language)}</b>", style(9, bold=True)),
            Paragraph(f"<b>{amount_label(data.language)}</b>", style(9, bold=True, align="RIGHT")),
        ],
        [
            Paragraph(transaction_description(data.language, data.property_id), style(10)),
            Paragraph(formatted_amt, style(10, align="RIGHT")),
        ],
    ]
    item_table = Table(items, colWidths=["75%", "25%"])
    item_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  _DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 4 * mm))

    # ── Total ─────────────────────────────────────────────────
    total_data = [[
        Paragraph(""),
        Paragraph(
            f'<b>{total_label(data.language)}&nbsp;&nbsp;{formatted_amt}</b>',
            style(13, bold=True, align="RIGHT"),
        ),
    ]]
    total_table = Table(total_data, colWidths=["50%", "50%"])
    total_table.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE",     (1, 0), (1, 0), 1.5, _DARK),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 8 * mm))

    # ── Payment details ───────────────────────────────────────
    story.append(Paragraph(payment_details_label(data.language), style(8, color=_RED)))
    pd_data = [
        ["IBAN:",        data.company_iban],
        [("Banka:" if data.language == "lv" else "Банк:" if data.language == "ru" else "Bank:"),
         data.company_bank],
        [("Mērķis:" if data.language == "lv" else "Назначение:" if data.language == "ru" else "Ref:"),
         data.invoice_number],
    ]
    pd_rows = [[Paragraph(k, style(9, color=_GRAY)), Paragraph(f"<b>{v}</b>", style(9, bold=True))]
               for k, v in pd_data]
    pd_table = Table(pd_rows, colWidths=["25%", "75%"])
    pd_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(pd_table)

    # ── Notes ─────────────────────────────────────────────────
    if data.notes:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(data.notes, style(9, color=_GRAY)))

    # ── Footer ────────────────────────────────────────────────
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_GRAY))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"{data.company_name} | {data.company_address}",
        style(7, color=_GRAY, align="CENTER"),
    ))

    doc.build(story)
    return buf.getvalue()
