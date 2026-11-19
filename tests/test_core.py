from docuflow.core import parse_document, validate, risk_flags, classify, sha256, extract_text
from docuflow.db import connect, insert, all_documents, update

def test_invoice_fields():
    f=parse_document('Vendor: Acme Supplies\nInvoice No: INV-1001\nDate: 2026-11-19\nSubtotal: $100.00\nTax: $10.00\nTotal: $110.00')
    assert f['doc_type']=='invoice' and f['total']==110 and f['vendor']=='Acme Supplies'
    assert f['invoice_number']=='INV-1001' and validate(f)==[]

def test_mismatch():
    f=parse_document('Invoice No: INV-1002\nVendor: Acme\nSubtotal: 100\nTax: 10\nTotal: 120')
    assert any('does not match' in x for x in validate(f))

def test_duplicate_flag():
    f={'invoice_number':'INV-1','vendor':'Acme','total':100}
    assert any('duplicate' in x.lower() for x in risk_flags(f,[{'invoice_number':'INV-1','vendor':'acme'}]))

def test_classify():
    assert classify('Agreement between the parties with signature')=='contract'
    assert classify('some random text')=='other'

def test_text_and_hash():
    assert extract_text('test.txt',b'hello')=='hello'
    assert sha256(b'a')==sha256(b'a')

def test_db_roundtrip(tmp_path):
    c=connect(tmp_path/'db.sqlite')
    fields=parse_document('Invoice No: INV-2000\nVendor: Alpha\nTotal: 90')
    insert(c,'invoice.txt','unique',fields,'text',[],[])
    rows=all_documents(c)
    assert len(rows)==1 and rows[0]['vendor']=='Alpha'
    update(c,rows[0]['id'],{'vendor':'Beta','invoice_number':'INV-2000','date':'','currency':'USD','subtotal':0,'tax':0,'total':90},'Approved')
    assert all_documents(c)[0]['status']=='Approved'
    c.close()
