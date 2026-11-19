"""Streamlit UI for DocuFlow AI (local-first demonstration)."""
import io
import json
import os
import sqlite3
import streamlit as st
import pandas as pd
import plotly.express as px
from docuflow.core import extract_text, parse_document, validate, risk_flags, sha256
from docuflow.db import connect, all_documents, insert, update

st.set_page_config(page_title='DocuFlow AI | ZubairLabs', page_icon='📄', layout='wide')
st.markdown('''<style>
.block-container{padding-top:1.8rem;max-width:1400px}
h1,h2,h3{letter-spacing:-.025em}
[data-testid="stMetric"]{border:1px solid rgba(120,130,160,.22);border-radius:14px;padding:16px}
</style>''', unsafe_allow_html=True)
conn = connect(os.getenv('DOCUFLOW_DB', 'data/docuflow.db'))
st.sidebar.title('📄 DocuFlow AI')
st.sidebar.caption('ZubairLabs · Local-first document intelligence')
page = st.sidebar.radio('Workspace', ['Overview', 'Process documents', 'Review queue', 'Data explorer', 'About'])
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
    st.write('Upload text-based PDF, TXT, CSV, or images (image OCR requires optional local Tesseract). Maximum 10 MB per file.')
    uploads=st.file_uploader('Choose documents',type=['pdf','txt','csv','png','jpg','jpeg'],accept_multiple_files=True)
    if uploads and st.button('Extract and save',type='primary'):
        for upload in uploads:
            try:
                raw=upload.getvalue()
                if len(raw)>10*1024*1024: raise ValueError('File exceeds 10 MB limit')
                digest=sha256(raw)
                if any(r['sha256']==digest for r in records):
                    st.warning(f'{upload.name}: identical file already exists'); continue
                text=extract_text(upload.name,raw)
                if not text.strip(): raise ValueError('No selectable text found. For scanned PDFs, OCR is not yet supported.')
                fields=parse_document(text)
                issues=validate(fields); flags=risk_flags(fields,records)
                insert(conn,upload.name,digest,fields,text,issues,flags)
                st.success(f'{upload.name}: saved as {fields["doc_type"]} — {len(issues)} validation issues, {len(flags)} risk flags')
                records=all_documents(conn)
            except (ValueError,sqlite3.Error,RuntimeError) as exc:
                st.error(f'{upload.name}: {exc}')
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
        st.download_button('Download CSV',filtered.to_csv(index=False).encode(),file_name='docuflow_export.csv',mime='text/csv')
        buf=io.BytesIO()
        with pd.ExcelWriter(buf,engine='openpyxl') as writer: filtered.to_excel(writer,index=False,sheet_name='Documents')
        st.download_button('Download Excel',buf.getvalue(),file_name='docuflow_export.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.download_button('Download JSON',filtered.to_json(orient='records',indent=2),file_name='docuflow_export.json',mime='application/json')

else:
    st.title('About DocuFlow AI')
    st.markdown('''**DocuFlow AI** is a local-first document intelligence demonstration by **ZubairLabs**.

**Pipeline:** File upload → PDF/text extraction → heuristic document classification → field extraction → business-rule validation → duplicate/risk flags → human review → analytics and export.

**Important limitations:** The current engine is rule-based, not a trained fraud classifier. Image OCR requires optional local Tesseract; scanned PDF OCR is not included. No authentication, encryption-at-rest, role-based access control, or cloud isolation is implemented. Do not deploy publicly with sensitive documents. This prototype is intended for local evaluation and portfolio demonstration.

[ZubairLabs](https://zubairlabs.com) · [GitHub](https://github.com/muhammadzubair-data)''')
