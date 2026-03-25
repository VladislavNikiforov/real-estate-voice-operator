"""pdf_generator/templates.py — Locale-aware formatting for invoice PDFs."""

from __future__ import annotations
from datetime import datetime
from typing import Optional


def format_amount(amount: float, currency: str = "EUR", language: str = "en") -> str:
    """Format monetary amount per locale.

    LV/RU: 85 000,00 €
    EN:    €85,000.00
    """
    if language in ("lv", "ru"):
        formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", "\u00a0")
        return f"{formatted}\u00a0{currency}"
    else:
        symbol = "€" if currency == "EUR" else currency
        return f"{symbol}{amount:,.2f}"


def format_date(language: str = "en", dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.utcnow()
    if language in ("lv", "ru"):
        return dt.strftime("%d.%m.%Y")
    return dt.strftime("%B %d, %Y")


def invoice_label(language: str) -> str:
    return {"lv": "RĒĶINS", "ru": "СЧЁТ", "en": "INVOICE"}.get(language, "INVOICE")


def date_label(language: str) -> str:
    return {"lv": "Datums:", "ru": "Дата:", "en": "Date:"}.get(language, "Date:")


def invoice_no_label(language: str) -> str:
    return {"lv": "Nr.", "ru": "№", "en": "No."}.get(language, "No.")


def bill_to_label(language: str) -> str:
    return {"lv": "Saņēmējs:", "ru": "Получатель:", "en": "Bill To:"}.get(language, "Bill To:")


def description_label(language: str) -> str:
    return {"lv": "Apraksts", "ru": "Описание", "en": "Description"}.get(language, "Description")


def amount_label(language: str) -> str:
    return {"lv": "Summa", "ru": "Сумма", "en": "Amount"}.get(language, "Amount")


def total_label(language: str) -> str:
    return {"lv": "KOPĀ:", "ru": "ИТОГО:", "en": "TOTAL:"}.get(language, "TOTAL:")


def property_label(language: str) -> str:
    return {"lv": "Īpašums", "ru": "Объект", "en": "Property"}.get(language, "Property")


def payment_details_label(language: str) -> str:
    return {
        "lv": "Maksājuma rekvizīti:",
        "ru": "Реквизиты для оплаты:",
        "en": "Payment Details:",
    }.get(language, "Payment Details:")


def transaction_description(language: str, property_id: str) -> str:
    return {
        "lv": f"Nekustamā īpašuma darījums — {property_id}",
        "ru": f"Сделка с недвижимостью — {property_id}",
        "en": f"Real estate transaction — {property_id}",
    }.get(language, f"Real estate transaction — {property_id}")


def seller_label(language: str) -> str:
    return {"lv": "Pakalpojuma sniedzējs:", "ru": "Поставщик:", "en": "From:"}.get(language, "From:")


def buyer_label(language: str) -> str:
    return {"lv": "Pakalpojuma saņēmējs:", "ru": "Покупатель:", "en": "Bill To:"}.get(language, "Bill To:")


def reg_nr_label(language: str) -> str:
    return {"lv": "Reģ. nr.", "ru": "Рег. №", "en": "Reg. No."}.get(language, "Reg. No.")


def vat_nr_label(language: str) -> str:
    return {"lv": "PVN nr.", "ru": "НДС №", "en": "VAT No."}.get(language, "VAT No.")


def qty_label(language: str) -> str:
    return {"lv": "Daudzums", "ru": "Кол-во", "en": "Qty"}.get(language, "Qty")


def unit_price_label(language: str) -> str:
    return {"lv": "Cena", "ru": "Цена", "en": "Unit Price"}.get(language, "Unit Price")


def subtotal_label(language: str) -> str:
    return {"lv": "Summa bez PVN:", "ru": "Сумма без НДС:", "en": "Subtotal:"}.get(language, "Subtotal:")


def vat_label(language: str) -> str:
    return {"lv": "PVN", "ru": "НДС", "en": "VAT"}.get(language, "VAT")


def payment_terms_label(language: str) -> str:
    return {
        "lv": "Apmaksas termiņš:",
        "ru": "Срок оплаты:",
        "en": "Payment Terms:",
    }.get(language, "Payment Terms:")
