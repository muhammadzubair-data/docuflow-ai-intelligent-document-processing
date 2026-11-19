"""Public-demo safety: per-session isolation, sample documents and app start-up."""
import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from docuflow.core import extract_text, parse_document, risk_flags, validate
from docuflow.db import all_documents, clear, connect, insert

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / 'sample_data'


def test_memory_databases_are_isolated():
    a, b = connect(':memory:'), connect(':memory:')
    insert(a, 'a.txt', 'hash-a', parse_document('Invoice No: INV-1\nVendor: A\nTotal: 5'), 'text', [], [])
    assert len(all_documents(a)) == 1
    assert all_documents(b) == []          # a second session sees nothing from the first


def test_memory_database_writes_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    c = connect(':memory:')
    insert(c, 'a.txt', 'h', parse_document('Total: 1'), 't', [], [])
    assert list(tmp_path.iterdir()) == []


def test_clear_removes_all_records():
    c = connect(':memory:')
    insert(c, 'a.txt', 'h1', parse_document('Total: 1'), 't', [], [])
    insert(c, 'b.txt', 'h2', parse_document('Total: 2'), 't', [], [])
    clear(c)
    assert all_documents(c) == []


def test_sample_pdf_extraction():
    data = (SAMPLES / 'invoice_003.pdf').read_bytes()
    f = parse_document(extract_text('invoice_003.pdf', data))
    assert (f['doc_type'], f['invoice_number'], f['total'], f['vendor']) == ('invoice', 'INV-2026-003', 3740.0, 'Contoso Office Furniture')
    assert validate(f) == []


@pytest.mark.skipif(shutil.which('tesseract') is None, reason='Tesseract OCR not installed')
def test_sample_image_ocr():
    data = (SAMPLES / 'invoice_004.png').read_bytes()
    f = parse_document(extract_text('invoice_004.png', data))
    assert (f['invoice_number'], f['total']) == ('INV-2026-004', 946.0)


def test_suspicious_sample_is_flagged():
    first = parse_document((SAMPLES / 'invoice_001.txt').read_text())
    sus = parse_document((SAMPLES / 'invoice_suspicious.txt').read_text())
    flags = risk_flags(sus, [first])
    assert any('duplicate' in x.lower() for x in flags) and any('high-value' in x.lower() for x in flags)
    assert any('does not match' in x for x in validate(sus))


def test_app_starts_in_private_session_mode(monkeypatch):
    monkeypatch.delenv('DOCUFLOW_STORAGE', raising=False)
    at = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=60).run()
    assert not at.exception
    assert any('private session' in w.value for w in at.sidebar.warning)
