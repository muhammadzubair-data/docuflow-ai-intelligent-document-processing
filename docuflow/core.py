import hashlib
import io
import re
from datetime import datetime
from pathlib import Path

import pymupdf as fitz  # `import fitz` is deprecated in PyMuPDF >= 1.24

MONEY = re.compile(r'(?<!\w)(?:USD|EUR|GBP|PKR|Rs\.?|\$|€|£)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)(?!\w)', re.I)
FIELD_PATTERNS = {
    'invoice_number': [r'(?:invoice|inv)\s*(?:no\.?|number|#|:)\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_-]{2,})', r'\bINV[- ]?([A-Z0-9-]{3,})\b'],
    'date': [r'(?:invoice\s+date|date|issued\s+on)\s*[:#-]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'],
    'total': [r'(?<![A-Za-z])(?:grand\s+total|amount\s+due|total\s+due|total)\s*[:\s]*((?:USD|EUR|GBP|PKR|Rs\.?|\$|€|£)?\s*[0-9][0-9,]*(?:\.\d{1,2})?)'],
    'tax': [r'(?:sales\s+tax|vat|gst|tax)\s*[:\s]*((?:USD|EUR|GBP|PKR|Rs\.?|\$|€|£)?\s*[0-9][0-9,]*(?:\.\d{1,2})?)'],
    'subtotal': [r'(?:sub\s*total)\s*[:\s]*((?:USD|EUR|GBP|PKR|Rs\.?|\$|€|£)?\s*[0-9][0-9,]*(?:\.\d{1,2})?)'],
}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == '.pdf':
        with fitz.open(stream=data, filetype='pdf') as doc:
            if doc.page_count > 100:
                raise ValueError('PDF exceeds 100-page processing limit')
            return '\n'.join(page.get_text(sort=True) for page in doc)
    if ext in ('.txt', '.csv'):
        return data.decode('utf-8-sig', errors='replace')
    if ext in ('.png', '.jpg', '.jpeg'):
        try:
            import pytesseract
            from PIL import Image
            return pytesseract.image_to_string(Image.open(io.BytesIO(data)))
        except (ImportError, OSError) as exc:
            raise ValueError('Image OCR requires pytesseract and a local Tesseract installation') from exc
    raise ValueError('Supported types: PDF, TXT, CSV, PNG, JPG')

def _first(patterns, text):
    for p in patterns:
        match = re.search(p, text, re.I | re.M)
        if match:
            return match.group(1).strip()
    return None

def _money(value):
    if not value:
        return None
    m = MONEY.search(value)
    return round(float(m.group(1).replace(',', '')), 2) if m else None

def classify(text: str) -> str:
    lower = text.lower()
    scores = {'invoice': sum(w in lower for w in ('invoice', 'amount due', 'subtotal', 'bill to')),
              'receipt': sum(w in lower for w in ('receipt', 'payment received', 'paid', 'change due')),
              'contract': sum(w in lower for w in ('agreement', 'parties', 'terms and conditions', 'signature'))}
    kind = max(scores, key=scores.get)
    return kind if scores[kind] else 'other'

def parse_document(text: str) -> dict:
    result = {'doc_type': classify(text)}
    for field, patterns in FIELD_PATTERNS.items():
        value = _first(patterns, text)
        result[field] = _money(value) if field in ('total', 'tax', 'subtotal') else value
    vendor = _first([r'(?:vendor|supplier|merchant|from)\s*:\s*([^\n\r]+)'], text)
    result['vendor'] = vendor or (next((line.strip() for line in text.splitlines() if line.strip()), '')[:120])
    result['currency'] = 'PKR' if re.search(r'\bPKR\b|\bRs\.', text, re.I) else ('EUR' if '€' in text else ('GBP' if '£' in text else 'USD'))
    return result

def validate(fields: dict) -> list[str]:
    issues = []
    if fields['doc_type'] in ('invoice', 'receipt'):
        for key in ('vendor', 'total'):
            if fields.get(key) in (None, ''):
                issues.append(f'Missing {key}')
    if fields.get('total') is not None and fields['total'] < 0:
        issues.append('Negative total')
    subtotal, tax, total = (fields.get(k) for k in ('subtotal', 'tax', 'total'))
    if all(v is not None for v in (subtotal, tax, total)) and abs(subtotal + tax - total) > .05:
        issues.append('Subtotal + tax does not match total (discounts/fees may apply)')
    date = fields.get('date')
    if date:
        try:
            parsed = None
            for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
                try:
                    parsed = datetime.strptime(date, fmt)
                    break
                except ValueError:
                    pass
            if parsed is None:
                issues.append('Unrecognized date format')
        except (TypeError, ValueError):
            issues.append('Invalid date')
    return issues

def risk_flags(fields: dict, existing: list[dict]) -> list[str]:
    flags = []
    if fields.get('total') is not None and fields['total'] >= 10000:
        flags.append('High-value transaction: manual review recommended (demo threshold)')
    if fields.get('invoice_number') and any(r.get('invoice_number') == fields['invoice_number'] and r.get('vendor', '').lower() == (fields.get('vendor') or '').lower() for r in existing):
        flags.append('Possible duplicate invoice number and vendor')
    return flags
