import json
import sqlite3
from pathlib import Path

SCHEMA = '''CREATE TABLE IF NOT EXISTS documents (
 id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE,
 doc_type TEXT, vendor TEXT, invoice_number TEXT, date TEXT, currency TEXT,
 subtotal REAL, tax REAL, total REAL, status TEXT NOT NULL DEFAULT 'Needs review',
 issues TEXT NOT NULL DEFAULT '[]', flags TEXT NOT NULL DEFAULT '[]',
 extracted_text TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)'''

def connect(path='data/docuflow.db'):
    """Open (and initialise) a database. Pass ':memory:' for a private, temporary database."""
    if str(path) != ':memory:':
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.commit()
    return conn

def all_documents(conn):
    return [dict(r) for r in conn.execute('SELECT * FROM documents ORDER BY id DESC')]

def insert(conn, filename, digest, fields, text, issues, flags):
    values = [filename, digest, *[fields.get(k) for k in ('doc_type','vendor','invoice_number','date','currency','subtotal','tax','total')], json.dumps(issues), json.dumps(flags), text]
    conn.execute('''INSERT INTO documents (filename,sha256,doc_type,vendor,invoice_number,date,currency,subtotal,tax,total,issues,flags,extracted_text)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', values)
    conn.commit()

def clear(conn):
    """Delete every stored document (used by the demo 'clear my session' button)."""
    conn.execute('DELETE FROM documents')
    conn.commit()

def update(conn, doc_id, fields, status):
    allowed = ('vendor', 'invoice_number', 'date', 'currency', 'subtotal', 'tax', 'total')
    if status not in ('Needs review', 'Approved', 'Rejected'):
        raise ValueError('Invalid status')
    conn.execute('''UPDATE documents SET vendor=?, invoice_number=?, date=?, currency=?, subtotal=?, tax=?, total=?, status=? WHERE id=?''',
                 [*[fields.get(k) for k in allowed], status, doc_id])
    conn.commit()
