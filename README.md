# 💳 Statement Analyzer

A Streamlit app that ingests credit card statements (PDF, CSV, XLS/XLSX, DOCX)
and surfaces spending intelligence you'd never catch manually.

## Features

| Tab | What it does |
|---|---|
| 💰 Top 13 | Largest single purchases ranked by amount |
| 🔁 Recurring Charges | Monthly/weekly/quarterly charges with true annual cost |
| 📋 Possible Subscriptions | Small forgotten recurring charges |
| 📈 Year-over-Year | Spend changes across years (requires 2+ years) |
| 🔍 AI Insights | LLM-powered narrative analysis (BYOK) |

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run locally
```bash
streamlit run app.py
```

### 3. Open in browser
```
http://localhost:8501
```

## Deploy to Streamlit Cloud (free)

1. Push this folder to a GitHub repo
2. Go to https://share.streamlit.io
3. Connect your repo, set `app.py` as the main file
4. Deploy — you get a shareable URL instantly

## Privacy

- Files are processed **entirely in memory** — never written to disk or any server
- Your API key lives only in your browser session and is discarded when you close the tab
- The AI Insights tab sends only **aggregated data** (merchant names + totals) to the LLM provider — no account numbers, card numbers, or personal details

## Supported Banks

Any bank that exports in PDF, CSV, or XLS format is supported. Tested against common
export formats from Chase, Bank of America, Citi, Capital One, American Express,
Wells Fargo, and Discover.

If your bank's export isn't parsing correctly, the CSV export format is the most
reliable — most banks offer this under "Download transactions" in their portal.

## File Structure

```
statement_analyzer/
├── app.py              Main Streamlit application
├── parser.py           File ingestion & normalization (PDF/CSV/XLS/DOCX)
├── analyzer.py         Rules engine (Top 13, Recurring, Subscriptions, YoY)
├── llm.py              Multi-provider AI calls (OpenAI / Gemini / Anthropic)
├── merchant_map.py     Merchant alias normalization dictionary
├── requirements.txt
└── README.md
```

## Data Quality Tiers

| Data | Features Unlocked |
|---|---|
| 1 statement | Top 13 only |
| 2–5 months | + Possible subscriptions |
| 6–11 months | + Recurring charges |
| 12 months | + True annual cost view |
| 24+ months | + Year-over-Year analysis |
