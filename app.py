# app.py — CC Smash Statement Analyzer (Gradio)
import gradio as gr
import pandas as pd
import os
import re
import tempfile

from parser import combine_files, extract_raw_text
from analyzer import (
    get_data_summary,
    get_top_13,
    get_recurring_charges,
    get_possible_subscriptions,
    get_yoy_changes,
    build_llm_summary,
)
from llm import get_ai_insights

CUSTOM_CSS = """
.stat-row { display: flex; gap: 12px; flex-wrap: wrap; margin: 0 0 1.25rem; }
.stat-card {
    background: #f9fafb; border: 1px solid #e5e7eb;
    border-radius: 10px; padding: 0.75rem 1rem;
    flex: 1; min-width: 130px; text-align: center;
}
.stat-label { font-size: 0.75rem; color: #9ca3af; margin-bottom: 2px; }
.stat-value { font-size: 1.3rem; font-weight: 600; color: #111827; }
.quality-banner {
    border-radius: 8px; padding: 0.75rem 1rem;
    font-size: 0.9rem; margin-bottom: 1rem;
}
.section-note {
    font-size: 0.8rem; color: #9ca3af;
    font-style: italic; margin: 0 0 0.5rem;
}
.privacy-badge {
    background: #f0fdf4; border: 1px solid #bbf7d0;
    border-radius: 8px; padding: 0.5rem 0.85rem;
    font-size: 0.8rem; color: #166534; margin-top: 0.5rem;
}
"""


def _wrap_file(f):
    """Adapt a Gradio uploaded file to the .name / .read() interface combine_files expects."""
    if isinstance(f, str):
        path, orig = f, os.path.basename(f)
    elif hasattr(f, "path"):
        path = f.path
        orig = getattr(f, "orig_name", None) or os.path.basename(f.path)
    elif hasattr(f, "name"):
        path = f.name
        orig = getattr(f, "orig_name", None) or os.path.basename(f.name)
    else:
        path, orig = str(f), os.path.basename(str(f))

    class _W:
        name = orig

        def read(self):
            with open(path, "rb") as fh:
                return fh.read()

        def seek(self, *a):
            pass

    return _W()


def _make_tempfile(text: str) -> str:
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8")
    tf.write(text)
    tf.close()
    return tf.name


def _no_results():
    none_df = gr.update(value=None, visible=False)
    return (
        gr.update(visible=False),              # results_col
        None, None, None,                      # state: df, summary, llm_text
        gr.update(value="", visible=False),    # warnings_md
        "", "",                                # quality_html, stats_html
        none_df, "",                           # top13_table, top13_footer_md
        none_df, "",                           # recurring_table, recurring_footer_md
        none_df, "",                           # subs_table, subs_footer_md
        "",                                    # yoy_status_md
        none_df, none_df,                      # yoy_inc_table, yoy_dec_table
        gr.update(value=None, visible=False),  # download_file
    )


def run_analysis(files, debug_parse):
    if not files:
        return _no_results()

    wrapped = [_wrap_file(f) for f in files]
    df, warnings = combine_files(wrapped)

    warn_lines = [f"> ⚠️ {w}" for w in warnings]
    debug_parts = []
    if debug_parse and warnings:
        failed = {m for w in warnings for m in re.findall(r"\*\*(.*?)\*\*", w)}
        for fw in wrapped:
            if fw.name in failed:
                try:
                    raw = extract_raw_text(fw.read(), fw.name)
                    if raw:
                        debug_parts.append(f"**Raw text: {fw.name}**\n```\n{raw[:3000]}\n```")
                except Exception:
                    pass

    warn_text = "\n\n".join(warn_lines)
    if debug_parts:
        warn_text += "\n\n" + "\n\n".join(debug_parts)

    if df.empty:
        err = "> ❌ Could not extract any transactions. Check file formats and try again."
        if warn_text:
            err += "\n\n" + warn_text
        none_df = gr.update(value=None, visible=False)
        return (
            gr.update(visible=False), None, None, None,
            gr.update(value=err, visible=True),
            "", "",
            none_df, "", none_df, "", none_df, "",
            "", none_df, none_df,
            gr.update(value=None, visible=False),
        )

    summary = get_data_summary(df)
    top13 = get_top_13(df)
    recurring = get_recurring_charges(df)
    subscriptions = get_possible_subscriptions(df)
    yoy = get_yoy_changes(df)
    llm_text = build_llm_summary(df, summary, top13, recurring, subscriptions, yoy)

    months = summary["months_covered"]
    has_yoy = summary["has_yoy"]
    years = summary["years_covered"]

    # Colored quality banner
    if months < 6:
        bg, border = "#fef3c7", "#f59e0b"
        msg = (
            f"📊 <strong>{months} month(s)</strong> of data detected. "
            "Upload at least 6 months for recurring charge detection and 12+ for full annual cost analysis."
        )
    elif months < 12:
        bg, border = "#fff7ed", "#f97316"
        msg = (
            f"📊 <strong>{months} months</strong> of data ({', '.join(str(y) for y in years)}). "
            "Upload 12+ months to see true annual costs. Upload 2+ years to unlock Year-over-Year."
        )
    elif not has_yoy:
        bg, border = "#eff6ff", "#3b82f6"
        msg = (
            f"📊 <strong>{months} months</strong> of data. "
            "Great for annual analysis! Upload statements from another year to unlock Year-over-Year."
        )
    else:
        bg, border = "#f0fdf4", "#22c55e"
        msg = (
            f"✅ <strong>{months} months across {len(years)} years</strong> — "
            "full analysis unlocked including Year-over-Year!"
        )

    quality_html = (
        f'<div class="quality-banner" style="background:{bg};border-left:4px solid {border};">'
        f"{msg}</div>"
    )

    avg_month = summary["total_spent"] / max(months, 1)
    stats_html = (
        '<div class="stat-row" style="display:flex;gap:12px;flex-wrap:wrap;margin:0 0 1.25rem;">'
        f'<div class="stat-card" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:0.75rem 1rem;flex:1;min-width:130px;text-align:center;">'
        f'<div class="stat-label" style="font-size:0.75rem;color:#9ca3af;margin-bottom:2px;">Total Spent</div>'
        f'<div class="stat-value" style="font-size:1.3rem;font-weight:600;color:#111827;">${summary["total_spent"]:,.0f}</div></div>'
        f'<div class="stat-card" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:0.75rem 1rem;flex:1;min-width:130px;text-align:center;">'
        f'<div class="stat-label" style="font-size:0.75rem;color:#9ca3af;margin-bottom:2px;">Transactions</div>'
        f'<div class="stat-value" style="font-size:1.3rem;font-weight:600;color:#111827;">{summary["total_transactions"]:,}</div></div>'
        f'<div class="stat-card" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:0.75rem 1rem;flex:1;min-width:130px;text-align:center;">'
        f'<div class="stat-label" style="font-size:0.75rem;color:#9ca3af;margin-bottom:2px;">Date Range</div>'
        f'<div class="stat-value" style="font-size:0.85rem;font-weight:600;color:#111827;">{summary["date_range_start"]}<br>→ {summary["date_range_end"]}</div></div>'
        f'<div class="stat-card" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:0.75rem 1rem;flex:1;min-width:130px;text-align:center;">'
        f'<div class="stat-label" style="font-size:0.75rem;color:#9ca3af;margin-bottom:2px;">Months</div>'
        f'<div class="stat-value" style="font-size:1.3rem;font-weight:600;color:#111827;">{months}</div></div>'
        f'<div class="stat-card" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:0.75rem 1rem;flex:1;min-width:130px;text-align:center;">'
        f'<div class="stat-label" style="font-size:0.75rem;color:#9ca3af;margin-bottom:2px;">Avg/Month</div>'
        f'<div class="stat-value" style="font-size:1.3rem;font-weight:600;color:#111827;">${avg_month:,.0f}</div></div>'
        '</div>'
    )

    # ── Top 13 ────────────────────────────────────────────────────────────────
    if not top13.empty:
        disp = top13.copy()
        disp["merchant"] = disp.apply(
            lambda r: f"🔁 {r['merchant']}" if r["is_recurring"] else r["merchant"], axis=1
        )
        top13_df = disp[["date_fmt", "merchant", "amount_fmt", "source_file"]].rename(
            columns={"date_fmt": "Date", "merchant": "Merchant",
                     "amount_fmt": "Amount", "source_file": "Statement File"}
        )
        total_top13 = top13["amount"].sum()
        pct = (total_top13 / summary["total_spent"] * 100) if summary["total_spent"] > 0 else 0
        top13_footer = (
            f"**Top 13 total: ${total_top13:,.2f}** — "
            f"that's **{pct:.1f}%** of all spending in this period."
        )
        top13_out = gr.update(value=top13_df, visible=True)
    else:
        top13_footer = "No transactions found."
        top13_out = gr.update(value=None, visible=False)

    # ── Recurring ─────────────────────────────────────────────────────────────
    if months < 3:
        rec_footer = "> ⚠️ Upload at least 3 months of statements to detect recurring charges."
        rec_out = gr.update(value=None, visible=False)
    elif recurring is None or recurring.empty:
        rec_footer = "No recurring charges detected in the uploaded statements."
        rec_out = gr.update(value=None, visible=False)
    else:
        rec_df = recurring[[
            "merchant", "frequency", "avg_charge_fmt", "annual_cost_fmt",
            "occurrences", "first_seen_fmt", "last_seen_fmt"
        ]].rename(columns={
            "merchant": "Merchant", "frequency": "Frequency",
            "avg_charge_fmt": "Avg Charge", "annual_cost_fmt": "Est. Annual Cost",
            "occurrences": "Times Seen", "first_seen_fmt": "First Seen", "last_seen_fmt": "Last Seen",
        })
        total_rec = recurring["annual_cost"].sum()
        rec_footer = f"**Estimated total annual cost of recurring charges: ${total_rec:,.2f}**"
        rec_out = gr.update(value=rec_df, visible=True)

    # ── Subscriptions ─────────────────────────────────────────────────────────
    if months < 2:
        subs_footer = "> ⚠️ Upload at least 2 months of statements to detect subscriptions."
        subs_out = gr.update(value=None, visible=False)
    elif subscriptions is None or subscriptions.empty:
        subs_footer = "No small recurring subscriptions detected."
        subs_out = gr.update(value=None, visible=False)
    else:
        subs_df = subscriptions[[
            "merchant", "frequency", "avg_charge_fmt", "annual_cost_fmt",
            "occurrences", "first_seen_fmt"
        ]].rename(columns={
            "merchant": "Merchant", "frequency": "Frequency",
            "avg_charge_fmt": "Per Period", "annual_cost_fmt": "Per Year",
            "occurrences": "Times Seen", "first_seen_fmt": "Paying Since",
        })
        total_subs = subscriptions["annual_cost"].sum()
        subs_footer = (
            f"**Total possible subscription spend: ${total_subs:,.2f}/year** — "
            f"that's **${total_subs/12:,.2f}/month** in charges you might not be thinking about."
        )
        subs_out = gr.update(value=subs_df, visible=True)

    # ── Year-over-Year ────────────────────────────────────────────────────────
    yoy_cols_map = {
        "merchant": "Merchant", "year_a": "Year A", "year_b": "Year B",
        "amount_a_fmt": "Spent (A)", "amount_b_fmt": "Spent (B)",
        "delta_fmt": "Change ($)", "pct_fmt": "Change (%)",
    }
    yoy_cols = list(yoy_cols_map.keys())

    if not has_yoy:
        yoy_status = (
            f"📅 Year-over-Year analysis requires at least 2 years of statements.\n\n"
            f"Currently loaded: **{', '.join(str(y) for y in years)}**.\n\n"
            "Upload statements from an additional year to unlock this tab."
        )
        yoy_inc_out = gr.update(value=None, visible=False)
        yoy_dec_out = gr.update(value=None, visible=False)
    elif yoy is None or yoy.empty:
        yoy_status = "No significant year-over-year changes found in the data."
        yoy_inc_out = gr.update(value=None, visible=False)
        yoy_dec_out = gr.update(value=None, visible=False)
    else:
        yoy_status = ""
        increases = yoy[yoy["delta"] > 0]
        decreases = yoy[yoy["delta"] < 0]
        yoy_inc_out = (
            gr.update(value=increases[yoy_cols].rename(columns=yoy_cols_map), visible=True)
            if not increases.empty else gr.update(value=None, visible=False)
        )
        yoy_dec_out = (
            gr.update(value=decreases[yoy_cols].rename(columns=yoy_cols_map), visible=True)
            if not decreases.empty else gr.update(value=None, visible=False)
        )

    download_path = _make_tempfile(llm_text)

    return (
        gr.update(visible=True),                              # results_col
        df, summary, llm_text,                                # state
        gr.update(value=warn_text, visible=bool(warn_text)),  # warnings_md
        quality_html,                                         # quality_html
        stats_html,                                           # stats_html
        top13_out,       top13_footer,                        # top13
        rec_out,         rec_footer,                          # recurring
        subs_out,        subs_footer,                         # subscriptions
        yoy_status,      yoy_inc_out,       yoy_dec_out,      # yoy
        gr.update(value=download_path, visible=True),         # download_file
    )


def run_ai(llm_text, provider, api_key, depth):
    if not llm_text:
        return "> ❌ Please run analysis first.", gr.update(visible=False)
    if not api_key:
        return "> ⚠️ Enter your API key in the AI Provider section above to use AI Insights.", gr.update(visible=False)
    result = get_ai_insights(data_summary=llm_text, provider=provider, api_key=api_key, depth=depth)
    return result, gr.update(value=_make_tempfile(result), visible=True)


# ── UI ────────────────────────────────────────────────────────────────────────

_SECTION_NOTE = '<div style="font-size:0.8rem;color:#9ca3af;font-style:italic;margin:0 0 0.5rem;">{}</div>'

with gr.Blocks(title="CC Smash — Statement Analyzer", theme=gr.themes.Soft(), css=CUSTOM_CSS) as demo:

    st_df = gr.State(None)
    st_summary = gr.State(None)
    st_llm = gr.State(None)

    gr.Markdown("""
# 💳 CC Smash — Statement Analyzer
Upload your credit card statements and uncover what your spending is really telling you.

**All statement data is processed in-memory — never stored or logged.**
""")

    with gr.Row():
        with gr.Column(scale=1):
            file_upload = gr.File(
                file_count="multiple",
                label="Upload Statements (PDF, CSV, XLS, XLSX, DOCX)",
                file_types=[".pdf", ".csv", ".xls", ".xlsx", ".docx"],
                height=120,
            )
        with gr.Column(scale=1):
            gr.HTML("""
<div style="padding:0.5rem 0;">
<strong>Better results with more data</strong><br><br>
🟡 1 statement — basic insights only<br>
🟠 6 months — recurring detection<br>
🟢 12 months — full annual cost view<br>
🔵 24+ months — Year-over-Year unlocked
</div>
""")

    with gr.Accordion("⚙️ Settings", open=False):
        debug_check = gr.Checkbox(label="Show raw parsed text for failed uploads (debug)")

    with gr.Accordion("🤖 AI Provider", open=True):
        gr.HTML(_SECTION_NOTE.format(
            "Required only for the AI Insights tab — choose your provider and paste your API key."
        ))
        with gr.Row():
            provider_dd = gr.Dropdown(
                choices=["OpenAI (GPT-4o)", "Google Gemini", "Anthropic Claude"],
                value="Anthropic Claude",
                label="AI Provider",
            )
            api_key_tb = gr.Textbox(
                type="password",
                label="API Key",
                placeholder="Paste your key here...",
                info="Used only this session. Never stored or shared.",
            )

    analyze_btn = gr.Button("🔍 Analyze Statements", variant="primary", size="lg")

    warnings_md = gr.Markdown(visible=False)

    with gr.Column(visible=False) as results_col:
        quality_html = gr.HTML()
        stats_html = gr.HTML()

        with gr.Tabs():

            with gr.Tab("💰 Top 13"):
                gr.Markdown("#### 💰 Top 13 Most Expensive Single Purchases")
                gr.HTML(_SECTION_NOTE.format(
                    "Ranked by transaction amount. Charges marked 🔁 also appear as recurring charges."
                ))
                top13_table = gr.DataFrame(wrap=True, visible=False)
                top13_footer_md = gr.Markdown()

            with gr.Tab("🔁 Recurring Charges"):
                gr.Markdown("#### 🔁 Recurring Charges — True Annual Cost")
                gr.HTML(_SECTION_NOTE.format(
                    "These charges appear on a regular schedule. The annual cost column shows what you're "
                    "actually paying per year — a number most people have never seen laid out clearly."
                ))
                recurring_table = gr.DataFrame(wrap=True, visible=False)
                recurring_footer_md = gr.Markdown()

            with gr.Tab("📋 Possible Subscriptions"):
                gr.Markdown("#### 📋 Possible Forgotten Subscriptions")
                gr.HTML(_SECTION_NOTE.format(
                    "Small, consistent charges that are easy to forget about. "
                    "Sorted by forgettability — the ones most likely to be autopilot spending. "
                    "Could you cancel any of these?"
                ))
                subs_table = gr.DataFrame(wrap=True, visible=False)
                subs_footer_md = gr.Markdown()

            with gr.Tab("📈 Year-over-Year"):
                gr.Markdown("#### 📈 Year-over-Year Spending Changes")
                yoy_status_md = gr.Markdown()
                gr.Markdown("##### ↑ Charges That Increased")
                gr.HTML(_SECTION_NOTE.format("These cost you more this year than last year."))
                yoy_inc_table = gr.DataFrame(wrap=True, visible=False)
                gr.Markdown("##### ↓ Charges That Decreased")
                gr.HTML(_SECTION_NOTE.format(
                    "You spent less here — cancellations, negotiated rates, or reduced usage."
                ))
                yoy_dec_table = gr.DataFrame(wrap=True, visible=False)

            with gr.Tab("🔍 AI Insights"):
                gr.Markdown("#### 🔍 AI Insights")
                gr.HTML(_SECTION_NOTE.format(
                    "The AI analyzes your aggregated spending data — not your raw transactions. "
                    "Merchant names and totals are shared with the provider you select; "
                    "no account numbers, card numbers, or personal details are ever sent."
                ))
                gr.Markdown("*Provider and API key are configured in the **AI Provider** section above.*")
                depth_radio = gr.Radio(
                    choices=["Summary bullets", "Deep narrative analysis"],
                    value="Summary bullets",
                    label="Analysis depth",
                    info="Deep analysis uses more tokens (~3-5x the cost of summary).",
                )
                ai_btn = gr.Button("✨ Run AI Analysis", variant="secondary")
                ai_output_md = gr.Markdown()
                ai_download_file = gr.File(label="Download AI Analysis", visible=False)

        download_file = gr.File(label="⬇️ Download Full Analysis Data", visible=False)

    # ── Event wiring ──────────────────────────────────────────────────────────

    analyze_outputs = [
        results_col, st_df, st_summary, st_llm,
        warnings_md, quality_html, stats_html,
        top13_table, top13_footer_md,
        recurring_table, recurring_footer_md,
        subs_table, subs_footer_md,
        yoy_status_md, yoy_inc_table, yoy_dec_table,
        download_file,
    ]

    analyze_btn.click(
        fn=run_analysis,
        inputs=[file_upload, debug_check],
        outputs=analyze_outputs,
    )

    ai_btn.click(
        fn=run_ai,
        inputs=[st_llm, provider_dd, api_key_tb, depth_radio],
        outputs=[ai_output_md, ai_download_file],
    )


if __name__ == "__main__":
    demo.launch()
