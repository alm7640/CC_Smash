---
title: CC Smash
emoji: 💳
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "5.0.0"
app_file: app.py
pinned: false
---

# 💳 CC Smash — Statement Analyzer

A Gradio app that ingests credit card statements (PDF, CSV, XLS/XLSX, DOCX)
and surfaces spending intelligence you'd never catch manually.

## Features

| Tab | What it does |
|---|---|
| 💰 Top 13 | Largest single purchases ranked by amount |
| 🔁 Recurring Charges | Monthly/weekly/quarterly charges with true annual cost |
| 📋 Possible Subscriptions | Small forgotten recurring charges |
| 📈 Year-over-Year | Spend changes across years (requires 2+ years) |
| 🔍 AI Insights | LLM-powered narrative analysis (BYOK) |

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

## Deploy

Pushes to `main` are automatically synced to the HuggingFace Space via GitHub Actions.
Requires a `HF_TOKEN` secret in the GitHub repo settings with write access to `alm7640/CC_Smash`.

## Privacy

- Files are processed **entirely in memory** — never written to disk or any server
- Your API key lives only in your browser session and is discarded when you close the tab
- The AI Insights tab sends only **aggregated data** (merchant names + totals) to the LLM provider — no account numbers, card numbers, or personal details are ever sent

## Supported Banks

Any bank that exports PDF, CSV, or XLS is supported. Tested against Chase, Bank of America,
Citi, Capital One, American Express, Wells Fargo, and Discover.

## Data Quality Tiers

| Data | Features Unlocked |
|---|---|
| 1 statement | Top 13 only |
| 2–5 months | + Possible subscriptions |
| 6–11 months | + Recurring charges |
| 12 months | + True annual cost view |
| 24+ months | + Year-over-Year analysis |
