"""Shared pytest fixtures."""

import os
import pytest

# Set env vars before any import touches config
os.environ.setdefault("COMPANY_NAME",    "Test SIA")
os.environ.setdefault("COMPANY_ADDRESS", "Test St 1, Riga")
os.environ.setdefault("COMPANY_BANK",    "Swedbank")
os.environ.setdefault("COMPANY_IBAN",    "LV00HABA0000000000000")
os.environ.setdefault("COMPANY_PHONE",   "+371 20000000")


@pytest.fixture
def invoice_params_lv():
    return {
        "client_name":  "Jānis Bērziņš",
        "client_email": "janis@example.lv",
        "property_id":  "apt-3",
        "amount":       85000.0,
        "language":     "lv",
    }


@pytest.fixture
def invoice_params_ru():
    return {
        "client_name":  "Ivan Petrov",
        "client_email": "ivan@example.ru",
        "property_id":  "apt-5",
        "amount":       100000.0,
        "language":     "ru",
    }


@pytest.fixture
def invoice_params_en():
    return {
        "client_name":  "John Smith",
        "client_email": "john@example.com",
        "property_id":  "apt-3",
        "amount":       85000.0,
        "language":     "en",
    }


@pytest.fixture
def reminder_params():
    return {
        "client_name":  "Māris Kalniņš",
        "client_email": "maris@example.lv",
        "language":     "lv",
        "property_id":  "apt-2",
        "amount":       50000.0,
    }


@pytest.fixture
def follow_up_params():
    return {
        "client_name":  "Anna Liepiņa",
        "client_email": "anna@example.lv",
        "language":     "lv",
        "property_id":  "house-1",
        "notes":        "She was very interested in the garden.",
    }


@pytest.fixture
def request_documents_params():
    return {
        "client_name":      "John Smith",
        "client_email":     "john@example.com",
        "documents_needed": "Passport copy, proof of income, bank statement",
        "language":         "en",
    }
