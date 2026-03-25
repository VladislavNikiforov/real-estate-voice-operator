"""pdf_generator/invoice.py — Generate invoice PDFs using reportlab."""

import io
import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from llm.models import InvoiceData
from pdf_generator.templates import (
    format_amount, invoice_label, date_label, invoice_no_label,
    description_label, amount_label, total_label, payment_details_label,
    transaction_description, seller_label, buyer_label,
    reg_nr_label, vat_nr_label, qty_label, unit_price_label,
    subtotal_label, vat_label, payment_terms_label,
)

# ── Font registration ─────────────────────────────────────────

_FONT_REGISTERED = False
_UNICODE_FONT = "Helvetica"

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
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(p)))
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
    """Generate a PDF invoice and return raw bytes."""
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

    font   = _UNICODE_FONT
    font_b = _UNICODE_FONT
    lang   = data.language

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
            f'<font color="#e63946"><b>{invoice_label(lang)}</b></font>',
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
            f"{invoice_no_label(lang)} <b>{data.invoice_number}</b><br/>"
            f"{date_label(lang)} {data.date}",
            style(9, align="RIGHT"),
        ),
    ]]
    sub_table = Table(sub_header, colWidths=["50%", "50%"])
    sub_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(sub_table)
    story.append(HRFlowable(width="100%", thickness=2, color=_DARK, spaceAfter=8))

    # ── Seller / Buyer blocks ─────────────────────────────────
    seller_lines = [f"<b>{data.company_name}</b>"]
    if data.company_reg_nr:
        seller_lines.append(f"{reg_nr_label(lang)} {data.company_reg_nr}")
    if data.company_vat_nr:
        seller_lines.append(f"{vat_nr_label(lang)} {data.company_vat_nr}")
    seller_lines.append(data.company_address)

    buyer_lines = [f"<b>{data.client_name}</b>"]
    if data.client_reg_nr:
        buyer_lines.append(f"{reg_nr_label(lang)} {data.client_reg_nr}")
    if data.client_vat_nr:
        buyer_lines.append(f"{vat_nr_label(lang)} {data.client_vat_nr}")
    if data.client_address:
        buyer_lines.append(data.client_address)
    buyer_lines.append(data.client_email)

    party_data = [[
        [Paragraph(seller_label(lang), style(8, color=_RED)),
         Paragraph("<br/>".join(seller_lines), style(9))],
        [Paragraph(buyer_label(lang), style(8, color=_RED)),
         Paragraph("<br/>".join(buyer_lines), style(9))],
    ]]
    # Flatten to single row with two cells
    party_table = Table(
        [[
            Table([[p] for p in party_data[0][0]], colWidths=["100%"]),
            Table([[p] for p in party_data[0][1]], colWidths=["100%"]),
        ]],
        colWidths=["50%", "50%"],
    )
    party_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(party_table)
    story.append(Spacer(1, 8 * mm))

    # ── Line items table ──────────────────────────────────────
    has_line_items = bool(data.line_items)

    if has_line_items:
        # Full line items with qty, unit price, amount
        header_row = [
            Paragraph(f"<b>{description_label(lang)}</b>", style(9, bold=True)),
            Paragraph(f"<b>{qty_label(lang)}</b>", style(9, bold=True, align="RIGHT")),
            Paragraph(f"<b>{unit_price_label(lang)}</b>", style(9, bold=True, align="RIGHT")),
            Paragraph(f"<b>{amount_label(lang)}</b>", style(9, bold=True, align="RIGHT")),
        ]
        rows = [header_row]
        for item in data.line_items:
            unit_str = f" {item.unit}" if item.unit else ""
            rows.append([
                Paragraph(item.description, style(10)),
                Paragraph(f"{item.quantity:g}{unit_str}", style(10, align="RIGHT")),
                Paragraph(format_amount(item.unit_price, data.currency, lang), style(10, align="RIGHT")),
                Paragraph(format_amount(item.amount, data.currency, lang), style(10, align="RIGHT")),
            ])

        item_table = Table(rows, colWidths=["45%", "15%", "20%", "20%"])
    else:
        # Legacy: single line item
        formatted_amt = format_amount(data.amount, data.currency, lang)
        rows = [
            [
                Paragraph(f"<b>{description_label(lang)}</b>", style(9, bold=True)),
                Paragraph(f"<b>{amount_label(lang)}</b>", style(9, bold=True, align="RIGHT")),
            ],
            [
                Paragraph(transaction_description(lang, data.property_id), style(10)),
                Paragraph(formatted_amt, style(10, align="RIGHT")),
            ],
        ]
        item_table = Table(rows, colWidths=["75%", "25%"])

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

    # ── Totals ────────────────────────────────────────────────
    total_rows = []

    if has_line_items and data.vat_rate > 0:
        total_rows.append([
            Paragraph(""),
            Paragraph(
                f'{subtotal_label(lang)}&nbsp;&nbsp;{format_amount(data.subtotal, data.currency, lang)}',
                style(10, align="RIGHT"),
            ),
        ])
        vat_pct = int(data.vat_rate * 100)
        total_rows.append([
            Paragraph(""),
            Paragraph(
                f'{vat_label(lang)} {vat_pct}%:&nbsp;&nbsp;{format_amount(data.vat_amount, data.currency, lang)}',
                style(10, align="RIGHT"),
            ),
        ])

    display_total = data.total if data.total else data.amount
    total_rows.append([
        Paragraph(""),
        Paragraph(
            f'<b>{total_label(lang)}&nbsp;&nbsp;{format_amount(display_total, data.currency, lang)}</b>',
            style(13, bold=True, align="RIGHT"),
        ),
    ])

    total_table = Table(total_rows, colWidths=["50%", "50%"])
    total_table.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE",     (1, -1), (1, -1), 1.5, _DARK),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 8 * mm))

    # ── Payment details ───────────────────────────────────────
    story.append(Paragraph(payment_details_label(lang), style(8, color=_RED)))
    pd_data = [
        ["IBAN:", data.company_iban],
        [("Banka:" if lang == "lv" else "Банк:" if lang == "ru" else "Bank:"),
         data.company_bank],
        [("Mērķis:" if lang == "lv" else "Назначение:" if lang == "ru" else "Ref:"),
         data.invoice_number],
    ]
    if data.payment_terms:
        pd_data.append([payment_terms_label(lang), data.payment_terms])

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
    footer_parts = [data.company_name, data.company_address]
    if data.company_reg_nr:
        footer_parts.append(f"{reg_nr_label(lang)} {data.company_reg_nr}")
    story.append(Paragraph(
        " | ".join(footer_parts),
        style(7, color=_GRAY, align="CENTER"),
    ))

    doc.build(story)
    return buf.getvalue()
