"""pdf_generator/templates.py — Locale-aware formatting for invoice PDFs."""

from datetime import datetime


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


def format_date(language: str = "en", dt: datetime | None = None) -> str:
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
