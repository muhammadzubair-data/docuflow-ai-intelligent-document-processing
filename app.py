"""Streamlit UI for DocuFlow AI (local-first demonstration)."""
import io
import json
import os
import sqlite3
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
from docuflow.core import extract_text, parse_document, validate, risk_flags, sha256
from docuflow.db import connect, all_documents, insert, update, clear

SAMPLE_DIR = Path(__file__).parent / 'sample_data'
# Storage mode:
#   session (default) - private in-memory database per browser session; nothing is written to disk
#                       and visitors never see each other's records. Used for the public demo.
#   local             - persistent SQLite file (DOCUFLOW_DB, default data/docuflow.db) for a trusted
#                       single-user machine: DOCUFLOW_STORAGE=local streamlit run app.py
STORAGE = os.getenv('DOCUFLOW_STORAGE', 'session').strip().lower()
LOCAL_MODE = STORAGE == 'local'

st.set_page_config(page_title='DocuFlow AI | ZubairLabs', page_icon='📄', layout='wide')
st.markdown('''<style>
.block-container{padding-top:1.8rem;max-width:1400px}
h1,h2,h3{letter-spacing:-.025em}
[data-testid="stMetric"]{border:1px solid rgba(120,130,160,.22);border-radius:14px;padding:16px}
</style>''', unsafe_allow_html=True)
@st.cache_resource
def local_connection(path):
    return connect(path)

if LOCAL_MODE:
    conn = local_connection(os.getenv('DOCUFLOW_DB', 'data/docuflow.db'))
else:
    if 'docuflow_conn' not in st.session_state:
        st.session_state.docuflow_conn = connect(':memory:')
    conn = st.session_state.docuflow_conn

def safe_export(frame):
    # Neutralise spreadsheet formulas in text cells (values come from uploaded documents).
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(lambda v: "'" + v if isinstance(v, str) and v[:1] in ('=', '+', '-', '@', '\t', '\r') else v)
    return out

def process_file(name, raw, existing):
    """Extract, validate, flag and store one document. Returns (fields, issues, flags) or None if duplicate file."""
    if len(raw) > 10*1024*1024: raise ValueError('File exceeds 10 MB limit')
    digest = sha256(raw)
    if any(r['sha256'] == digest for r in existing):
        return None
    text = extract_text(name, raw)
    if not text.strip(): raise ValueError('No selectable text found. For scanned PDFs, OCR is not yet supported.')
    fields = parse_document(text)
    issues = validate(fields); flags = risk_flags(fields, existing)
    insert(conn, name, digest, fields, text, issues, flags)
    return fields, issues, flags

st.sidebar.title('📄 DocuFlow AI')
st.sidebar.caption('ZubairLabs · Local-first document intelligence')
page = st.sidebar.radio('Workspace', ['Overview', 'Process documents', 'Review queue', 'Data explorer', 'About'])
if LOCAL_MODE:
    st.sidebar.success('Local mode: records are saved to a SQLite file on this machine.')
else:
    st.sidebar.warning('**Public demo · private session.** Your records live only in this browser session, are not visible to other visitors, '
                       'and are erased when you reload or close the page. Use synthetic sample documents only.')
    if st.sidebar.button('Clear my session data'):
        clear(conn); st.rerun()
st.sidebar.info('Rule-based extraction and anomaly flags are decision support, not verified fraud detection. Process only documents you are authorized to use.')
records = all_documents(conn)
df = pd.DataFrame([{k:v for k,v in r.items() if k not in ('extracted_text', 'sha256')} for r in records])

if page == 'Overview':
    st.title('Document Intelligence Overview')
    st.caption('Extract · Validate · Review · Analyze')
    a,b,c,d = st.columns(4)
    a.metric('Documents',len(records)); b.metric('Needs review',sum(r['status']=='Needs review' for r in records))
    c.metric('Approved',sum(r['status']=='Approved' for r in records))
    d.metric('Flagged',sum(bool(json.loads(r['flags'])) for r in records))
    if df.empty:
        st.info('Upload sample documents in **Process documents** to populate the dashboard.')
    else:
        left,right = st.columns(2)
        with left: st.plotly_chart(px.histogram(df,x='doc_type',color='status',title='Document types and review status'),width='stretch')
        with right:
            amounts=df.dropna(subset=['total'])
            if not amounts.empty: st.plotly_chart(px.bar(amounts.groupby(['vendor','currency'],as_index=False)['total'].sum(),x='vendor',y='total',color='currency',title='Amounts by vendor (currencies not combined)'),width='stretch')
        st.subheader('Recent documents')
        st.dataframe(df.drop(columns=['issues','flags'],errors='ignore').head(10),hide_index=True,width='stretch')

elif page == 'Process documents':
    st.title('Process documents')
    samples = sorted(p for p in SAMPLE_DIR.glob('*') if p.suffix.lower() in ('.txt', '.pdf', '.png', '.jpg', '.jpeg', '.csv'))
    st.subheader('Try the synthetic samples')
    st.caption('Fictional invoices in TXT, PDF and PNG (OCR) formats: four clean invoices plus one with a repeated invoice number, a high total and a total mismatch.')
    if st.button(f'Load {len(samples)} synthetic sample documents', type='primary'):
        for sample in samples:
            try:
                result = process_file(sample.name, sample.read_bytes(), records)
                if result is None:
                    st.warning(f'{sample.name}: identical file already exists'); continue
                fields, issues, flags = result
                st.success(f'{sample.name}: saved as {fields["doc_type"]} — {len(issues)} validation issues, {len(flags)} risk flags')
                records = all_documents(conn)
            except (ValueError, sqlite3.Error, RuntimeError) as exc:
                st.error(f'{sample.name}: {exc}')
    st.divider()
    st.subheader('Upload your own files')
    st.write('Upload text-based PDF, TXT, CSV, or images (image OCR requires Tesseract). Maximum 10 MB per file.')
    confirmed = True
    if not LOCAL_MODE:
        confirmed = st.checkbox('I confirm these files contain no confidential, personal or customer data (public demo).')
    uploads = st.file_uploader('Choose documents', type=['pdf','txt','csv','png','jpg','jpeg'], accept_multiple_files=True, disabled=not confirmed)
    if uploads and confirmed and st.button('Extract and save', type='primary'):
        for upload in uploads:
            try:
                result = process_file(upload.name, upload.getvalue(), records)
                if result is None:
                    st.warning(f'{upload.name}: identical file already exists'); continue
                fields, issues, flags = result
                st.success(f'{upload.name}: saved as {fields["doc_type"]} — {len(issues)} validation issues, {len(flags)} risk flags')
                records = all_documents(conn)
            except (ValueError, sqlite3.Error, RuntimeError) as exc:
                st.error(f'{upload.name}: {exc}')
    if records:
        st.info('Open Review queue to verify and approve extracted fields.')

elif page == 'Review queue':
    st.title('Human review queue')
    if not records: st.info('No documents yet.')
    else:
        chosen=st.selectbox('Select document',records,format_func=lambda r:f'#{r["id"]} · {r["filename"]} · {r["status"]}')
        col1,col2=st.columns([1,1])
        with col1:
            st.subheader('Extracted content')
            st.text_area('Text preview',chosen['extracted_text'][:20000],height=350,disabled=True)
        with col2:
            st.subheader('Verify extracted fields')
            for issue in json.loads(chosen['issues']): st.warning(issue)
            for flag in json.loads(chosen['flags']): st.error(flag)
            with st.form('review'):
                vendor=st.text_input('Vendor',chosen['vendor'] or '')
                invoice_number=st.text_input('Invoice number',chosen['invoice_number'] or '')
                date=st.text_input('Document date',chosen['date'] or '')
                currency=st.selectbox('Currency',['USD','PKR','EUR','GBP'],index=['USD','PKR','EUR','GBP'].index(chosen['currency']) if chosen['currency'] in ['USD','PKR','EUR','GBP'] else 0)
                subtotal=st.number_input('Subtotal',value=float(chosen['subtotal'] or 0),min_value=0.0)
                tax=st.number_input('Tax',value=float(chosen['tax'] or 0),min_value=0.0)
                total=st.number_input('Total',value=float(chosen['total'] or 0),min_value=0.0)
                status=st.selectbox('Decision',['Needs review','Approved','Rejected'],index=['Needs review','Approved','Rejected'].index(chosen['status']))
                if st.form_submit_button('Save review',type='primary'):
                    fields=dict(vendor=vendor,invoice_number=invoice_number,date=date,currency=currency,subtotal=subtotal,tax=tax,total=total)
                    if status=='Approved' and validate({**chosen,**fields}): st.error('Resolve validation issues before approving.')
                    else:
                        update(conn,chosen['id'],fields,status)
                        st.success('Review saved'); st.rerun()

elif page == 'Data explorer':
    st.title('Document data explorer')
    if df.empty: st.info('No documents to export.')
    else:
        status_filter=st.multiselect('Status',sorted(df['status'].unique()),default=sorted(df['status'].unique()))
        filtered=df[df['status'].isin(status_filter)].copy()
        st.dataframe(filtered.drop(columns=['issues','flags'],errors='ignore'),hide_index=True,width='stretch')
        safe=safe_export(filtered)
        st.download_button('Download CSV',safe.to_csv(index=False).encode(),file_name='docuflow_export.csv',mime='text/csv')
        buf=io.BytesIO()
        with pd.ExcelWriter(buf,engine='openpyxl') as writer: safe.to_excel(writer,index=False,sheet_name='Documents')
        st.download_button('Download Excel',buf.getvalue(),file_name='docuflow_export.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.download_button('Download JSON',filtered.to_json(orient='records',indent=2),file_name='docuflow_export.json',mime='application/json')

else:
    st.title('About DocuFlow AI')
    st.markdown('''**DocuFlow AI** is a local-first document intelligence demonstration by **ZubairLabs**.

**Pipeline:** File upload → PDF/text extraction → heuristic document classification → field extraction → business-rule validation → duplicate/risk flags → human review → analytics and export.

**Storage:** the public demo keeps each visitor's records in a private in-memory database tied to their browser session; nothing is written to disk and records disappear on reload. Local mode (`DOCUFLOW_STORAGE=local`) stores records in a SQLite file for a single trusted user.

**Important limitations:** The current engine is rule-based, not a trained fraud classifier. Image OCR requires Tesseract; scanned PDF OCR is not included. No authentication, encryption-at-rest or role-based access control is implemented, and Streamlit Community Cloud storage is temporary, so this is not durable or production-grade storage. Do not upload sensitive documents to the public demo. This prototype is intended for evaluation and portfolio demonstration.

[ZubairLabs](https://zubairlabs.com) · [GitHub](https://github.com/muhammadzubair-data)''')
