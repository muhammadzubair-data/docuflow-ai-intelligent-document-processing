<div align="center">

![DocuFlow AI project cover](assets/hero.svg)

# DocuFlow AI

### Intelligent Document Processing · Validation · Human Review · Analytics

**A local-first document intelligence portfolio prototype by [ZubairLabs](https://zubairlabs.com)**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/) [![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/) [![SQLite](https://img.shields.io/badge/SQLite-Local%20Storage-003B57?logo=sqlite&logoColor=white)](https://sqlite.org/) [![CI](https://github.com/muhammadzubair-data/docuflow-ai-intelligent-document-processing/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/muhammadzubair-data/docuflow-ai-intelligent-document-processing/actions/workflows/ci.yml) [![MIT](https://img.shields.io/badge/License-MIT-8B5CF6)](LICENSE)

**[Features](#-what-it-does) · [Quick start](#-quick-start) · [Architecture](#-processing-architecture) · [Limitations](#%EF%B8%8F-honest-limitations) · [Roadmap](#%EF%B8%8F-roadmap)**

</div>

> [!IMPORTANT]
> **Prototype, not an enterprise-ready AI service.** Document classification, extraction and risk flags use transparent rules, **not** a trained ML fraud detector. Sample invoices are synthetic. Use only nonsensitive or appropriately authorized files on a trusted local machine.

## 🎯 The problem

Manual document handling is slow and error-prone: teams retype invoice details, compare totals, check duplicate identifiers, route exceptions for approval and assemble reports. DocuFlow AI demonstrates an **inspectable end-to-end workflow** to reduce repetitive steps while keeping a human in control.

## 🧩 What it does

| Stage | Current implementation | Why it matters |
|:--|:--|:--|
| 📥 Ingest | Text PDFs, TXT, CSV; optional image OCR | Accept common local formats |
| 🔎 Extract | PyMuPDF text extraction and invoice regex patterns | Convert text into fields |
| 🏷️ Classify | Keyword rules: invoice, receipt, contract, other | Organize records |
| 🧮 Validate | Required values, dates, subtotal/tax/total checks | Surface inconsistencies |
| 🚩 Flag | Duplicate vendor + invoice number, high-value threshold | Prioritize manual review |
| 👤 Review | Edit fields, approve or reject | Keep human oversight |
| 📊 Explore | Status charts, vendor totals, record explorer | See workflow activity |
| 📤 Export | CSV, XLSX and JSON | Reuse structured results |
| 💾 Store | SQLite on the local machine | Persist reviewed records |

## 🎨 Processing architecture

![Illustrated DocuFlow AI workflow](assets/workflow.svg)

```mermaid
flowchart LR
    A[Upload file] --> B[Extract text]
    B --> C[Classify document]
    C --> D[Parse fields]
    D --> E[Validate + flag]
    E --> F[(Local SQLite)]
    F --> G[Human review]
    G --> H[Analytics + export]
```

## 🚀 Quick start

**Requirements:** Python 3.11 or later; local environment with access to package installation.

```bash
# 1. Clone the repository
 git clone https://github.com/muhammadzubair-data/docuflow-ai-intelligent-document-processing.git
 cd docuflow-ai-intelligent-document-processing

# 2. Create a virtual environment
 python -m venv .venv

# 3. Activate it
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate

# 4. Install and launch
 pip install -r requirements.txt
 streamlit run app.py
```

Open the URL shown by Streamlit, normally **http://localhost:8501**.

### Five-minute walkthrough

1. Open **Process documents** and upload a sample file from `sample_data/`.
2. Inspect extraction and validation messages.
3. Open **Review queue** to inspect source text, correct fields and save a decision.
4. Visit **Overview** to explore counts, review status and vendor totals.
5. Use **Data explorer** to export CSV, Excel or JSON.

### Optional image OCR

Install the Tesseract executable separately and add it to your system PATH, then install the Python bridge:

```bash
pip install pytesseract
```

PNG/JPG OCR is optional. **Scanned PDF OCR is not supported** in this version; PDFs must contain selectable text. OCR output requires review.

## 🛠️ Technology stack

| Layer | Technology |
|:--|:--|
| UI | Streamlit |
| Data analysis and charts | Pandas, Plotly |
| PDF text extraction | PyMuPDF |
| Parsing, validation, flags | Python, regular expressions, deterministic rules |
| Persistence | SQLite |
| Exports | Pandas, openpyxl |
| Optional image OCR | Tesseract, pytesseract |
| Quality checks | pytest, GitHub Actions |

## 🗂️ Repository structure

```text
docuflow-ai/
├── assets/
│   ├── hero.svg                  # Project cover
│   └── workflow.svg              # Illustrated processing pipeline
├── docuflow/
│   ├── __init__.py
│   ├── core.py                   # Extraction, parsing, validation and flags
│   └── db.py                     # SQLite persistence
├── sample_data/                 # Synthetic demonstration invoices
├── tests/
│   └── test_core.py
├── .github/workflows/ci.yml
├── app.py                        # Streamlit application
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

## 🧪 Tests and reproducibility

```bash
python -m pytest -q
python -m compileall -q app.py docuflow
```

The GitHub Actions workflow runs automated checks on repository changes. The included sample documents are **synthetic**, not an independent real-world benchmark. No field-level extraction precision/recall or fraud-detection accuracy is claimed.

## 🔐 Local data and safety

- Extracted text and fields are saved to a **local SQLite database** at `data/docuflow.db` by default.
- The app has **no login, role permissions, encryption at rest, malware scanning or tenant isolation**.
- Remove the local database file to delete stored demonstration records. Make backups first if needed.
- Do **not** deploy this prototype publicly with confidential documents or sensitive user data.
- The high-value flag uses a demonstration threshold of **10,000 in extracted units**; it is **not** calibrated fraud detection and does not convert currencies.

## ⚠️ Honest limitations

| Area | Current boundary |
|:--|:--|
| Document layouts | Regex extraction can miss unusual layouts |
| Classification | Explainable keywords, not trained NLP |
| Fraud | Risk heuristics only; no validated fraud model |
| Scanned PDFs | OCR not implemented |
| Security | Local prototype, not production hardened |
| Performance | Not benchmarked at enterprise scale |
| Data | Synthetic demonstration invoices |

## 🛣️ Roadmap

- [ ] Add scanned-PDF OCR and layout-aware extraction
- [ ] Build labeled extraction benchmark with precision and recall
- [ ] Train and validate an anomaly model against real labels
- [ ] Add authentication, access controls and audit logs
- [ ] Add secure file handling and encrypted storage
- [ ] Support asynchronous processing and a REST API
- [ ] Add containerization and private deployment guides

## 💼 Portfolio case study

**Challenge:** Invoice-heavy workflows require manual entry, checking and review.

**Approach:** Create a local-first workflow for text extraction, structured parsing, validation, risk flags, human correction and export.

**Demonstration scenario:** Import synthetic invoices, examine a total mismatch, inspect a repeated invoice identifier, correct extracted values and export reviewed records.

**Value:** Shows how data engineering, rule-based intelligence, visualization and workflow design can combine into a practical prototype. It does not claim quantified time savings without measurement.

## 👨‍💻 Author

**ZubairLabs** · [Website](https://zubairlabs.com) · [GitHub](https://github.com/muhammadzubair-data)

## 📄 License

[MIT License](LICENSE) · © 2026 ZubairLabs
