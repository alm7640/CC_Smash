# analyzer.py
# Rules engine: Top 13, Recurring, Subscriptions, YoY, Data quality checks

import pandas as pd
import numpy as np
from datetime import datetime
from typing import TypedDict


# ─────────────────────────────────────────────────────────────────────────────
# Type hints
# ─────────────────────────────────────────────────────────────────────────────

class DataSummary(TypedDict):
    total_transactions: int
    total_spent: float
    date_range_start: str
    date_range_end: str
    months_covered: int
    years_covered: list[int]
    has_yoy: bool          # 2+ distinct years
    has_full_year: bool    # 12+ months


# ─────────────────────────────────────────────────────────────────────────────
# Data summary
# ─────────────────────────────────────────────────────────────────────────────

def get_data_summary(df: pd.DataFrame) -> DataSummary:
    years = sorted(df["date"].dt.year.unique().tolist())
    months_covered = df["date"].dt.to_period("M").nunique()
    return DataSummary(
        total_transactions=len(df),
        total_spent=round(df["amount"].sum(), 2),
        date_range_start=df["date"].min().strftime("%b %d, %Y"),
        date_range_end=df["date"].max().strftime("%b %d, %Y"),
        months_covered=months_covered,
        years_covered=years,
        has_yoy=len(years) >= 2,
        has_full_year=months_covered >= 12,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Top 13 most expensive single purchases
# ─────────────────────────────────────────────────────────────────────────────

def get_top_13(df: pd.DataFrame) -> pd.DataFrame:
    """
    Top 13 single transactions by amount.
    Excludes recurring charges (those are shown separately).
    """
    # Get recurring merchants so we can flag them
    recurring = _detect_recurring_merchants(df)
    recurring_names = set(recurring["merchant"].tolist()) if not recurring.empty else set()

    result = (
        df.copy()
        .sort_values("amount", ascending=False)
        .head(13)
        .reset_index(drop=True)
    )
    result.index += 1
    result["is_recurring"] = result["merchant"].isin(recurring_names)
    result["date_fmt"] = result["date"].dt.strftime("%b %d, %Y")
    result["amount_fmt"] = result["amount"].apply(lambda x: f"${x:,.2f}")
    return result[["date_fmt", "merchant", "amount_fmt", "amount", "is_recurring", "source_file"]]


# ─────────────────────────────────────────────────────────────────────────────
# Recurring charge detection (internal helper)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_recurring_merchants(df: pd.DataFrame, min_occurrences: int = 3) -> pd.DataFrame:
    """
    Core recurring detection. A merchant is recurring if it appears
    at least min_occurrences times AND the median gap between charges
    is 25–35 days (monthly) or 6–8 days (weekly) or 88–95 days (quarterly).
    """
    if df.empty:
        return pd.DataFrame()

    results = []
    grouped = df.groupby("merchant")

    for merchant, group in grouped:
        group = group.sort_values("date")
        if len(group) < min_occurrences:
            continue

        dates = group["date"].tolist()
        gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        if not gaps:
            continue

        median_gap = np.median(gaps)
        avg_amount = group["amount"].mean()
        amounts = group["amount"].tolist()

        # Classify frequency
        if 25 <= median_gap <= 35:
            frequency = "Monthly"
            periods_per_year = 12
        elif 6 <= median_gap <= 8:
            frequency = "Weekly"
            periods_per_year = 52
        elif 88 <= median_gap <= 95:
            frequency = "Quarterly"
            periods_per_year = 4
        elif 355 <= median_gap <= 375:
            frequency = "Annual"
            periods_per_year = 1
        elif 13 <= median_gap <= 17:
            frequency = "Bi-Weekly"
            periods_per_year = 26
        else:
            continue  # Irregular — skip

        annual_cost = avg_amount * periods_per_year
        amount_variance = np.std(amounts)
        amount_consistent = amount_variance < (avg_amount * 0.1)  # <10% variation

        results.append({
            "merchant": merchant,
            "frequency": frequency,
            "avg_charge": round(avg_amount, 2),
            "annual_cost": round(annual_cost, 2),
            "occurrences": len(group),
            "amount_consistent": amount_consistent,
            "first_seen": group["date"].min(),
            "last_seen": group["date"].max(),
            "amounts": amounts,
        })

    if not results:
        return pd.DataFrame()

    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values("annual_cost", ascending=False).reset_index(drop=True)
    result_df.index += 1
    return result_df


# ─────────────────────────────────────────────────────────────────────────────
# Recurring charges (public — for Recurring tab)
# ─────────────────────────────────────────────────────────────────────────────

def get_recurring_charges(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns recurring charges with annualized cost.
    Excludes likely subscriptions (handled separately).
    """
    rec = _detect_recurring_merchants(df, min_occurrences=3)
    if rec.empty:
        return pd.DataFrame()

    # Exclude those that look like subscriptions (small + consistent)
    mask = ~((rec["avg_charge"] <= 30) & (rec["amount_consistent"]))
    rec = rec[mask].copy()

    rec["avg_charge_fmt"] = rec["avg_charge"].apply(lambda x: f"${x:,.2f}")
    rec["annual_cost_fmt"] = rec["annual_cost"].apply(lambda x: f"${x:,.2f}")
    rec["first_seen_fmt"] = rec["first_seen"].dt.strftime("%b %Y")
    rec["last_seen_fmt"] = rec["last_seen"].dt.strftime("%b %Y")
    return rec


# ─────────────────────────────────────────────────────────────────────────────
# Possible subscriptions
# ─────────────────────────────────────────────────────────────────────────────

def get_possible_subscriptions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Small (≤$30), highly consistent recurring charges.
    These are the 'set it and forget it' subscriptions people often forget.
    """
    rec = _detect_recurring_merchants(df, min_occurrences=2)
    if rec.empty:
        return pd.DataFrame()

    # Keep only small + consistent charges
    mask = (rec["avg_charge"] <= 30) & (rec["amount_consistent"])
    subs = rec[mask].copy()

    if subs.empty:
        return pd.DataFrame()

    # Forgettability score: lower charge + more occurrences = more forgettable
    subs["forgettability"] = (subs["occurrences"] / subs["avg_charge"]).round(2)
    subs = subs.sort_values("forgettability", ascending=False).reset_index(drop=True)
    subs.index += 1

    subs["avg_charge_fmt"] = subs["avg_charge"].apply(lambda x: f"${x:,.2f}")
    subs["annual_cost_fmt"] = subs["annual_cost"].apply(lambda x: f"${x:,.2f}")
    subs["first_seen_fmt"] = subs["first_seen"].dt.strftime("%b %Y")
    return subs


# ─────────────────────────────────────────────────────────────────────────────
# Year-over-Year changes
# ─────────────────────────────────────────────────────────────────────────────

def get_yoy_changes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare total annual spend per merchant across years.
    Returns merchants with notable increases or decreases.
    Requires at least 2 years of data.
    """
    years = sorted(df["date"].dt.year.unique())
    if len(years) < 2:
        return pd.DataFrame()

    # Annual totals per merchant
    df2 = df.copy()
    df2["year"] = df2["date"].dt.year
    pivot = df2.groupby(["merchant", "year"])["amount"].sum().unstack(fill_value=0)

    results = []
    year_pairs = list(zip(years[:-1], years[1:]))

    for (yr_a, yr_b) in year_pairs:
        if yr_a not in pivot.columns or yr_b not in pivot.columns:
            continue
        for merchant in pivot.index:
            amt_a = pivot.loc[merchant, yr_a]
            amt_b = pivot.loc[merchant, yr_b]

            # Skip if either year is zero (new/dropped merchant)
            if amt_a <= 0 or amt_b <= 0:
                continue
            # Skip very small amounts
            if amt_a < 10 and amt_b < 10:
                continue

            delta = amt_b - amt_a
            pct_change = (delta / amt_a) * 100

            # Only flag meaningful changes (≥5% or ≥$25)
            if abs(pct_change) >= 5 or abs(delta) >= 25:
                results.append({
                    "merchant": merchant,
                    "year_a": yr_a,
                    "year_b": yr_b,
                    "amount_a": round(amt_a, 2),
                    "amount_b": round(amt_b, 2),
                    "delta": round(delta, 2),
                    "pct_change": round(pct_change, 1),
                    "direction": "↑ Increase" if delta > 0 else "↓ Decrease",
                })

    if not results:
        return pd.DataFrame()

    result_df = pd.DataFrame(results)
    # Sort: biggest increases first, then decreases
    result_df = result_df.sort_values("delta", ascending=False).reset_index(drop=True)
    result_df.index += 1

    result_df["amount_a_fmt"] = result_df["amount_a"].apply(lambda x: f"${x:,.2f}")
    result_df["amount_b_fmt"] = result_df["amount_b"].apply(lambda x: f"${x:,.2f}")
    result_df["delta_fmt"] = result_df["delta"].apply(
        lambda x: f"+${x:,.2f}" if x > 0 else f"-${abs(x):,.2f}"
    )
    result_df["pct_fmt"] = result_df["pct_change"].apply(
        lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%"
    )
    return result_df


# ─────────────────────────────────────────────────────────────────────────────
# Build LLM summary payload
# ─────────────────────────────────────────────────────────────────────────────

def build_llm_summary(
    df: pd.DataFrame,
    summary: DataSummary,
    top13: pd.DataFrame,
    recurring: pd.DataFrame,
    subscriptions: pd.DataFrame,
    yoy: pd.DataFrame,
) -> str:
    """
    Build a concise text summary to send to the LLM.
    We send aggregated data, NOT raw transactions, for privacy.
    """
    lines = []
    lines.append("=== CREDIT CARD STATEMENT ANALYSIS DATA ===")
    lines.append(f"Date range: {summary['date_range_start']} to {summary['date_range_end']}")
    lines.append(f"Total transactions: {summary['total_transactions']}")
    lines.append(f"Total spent: ${summary['total_spent']:,.2f}")
    lines.append(f"Months covered: {summary['months_covered']}")
    lines.append(f"Years: {', '.join(str(y) for y in summary['years_covered'])}")
    lines.append("")

    lines.append("--- TOP 13 LARGEST SINGLE PURCHASES ---")
    if not top13.empty:
        for _, row in top13.iterrows():
            lines.append(f"  {row['date_fmt']}  {row['merchant']}  {row['amount_fmt']}")
    lines.append("")

    lines.append("--- RECURRING CHARGES (ANNUALIZED) ---")
    if not recurring.empty:
        for _, row in recurring.iterrows():
            lines.append(
                f"  {row['merchant']}  {row['frequency']}  "
                f"avg {row['avg_charge_fmt']}/period  "
                f"annual est. {row['annual_cost_fmt']}"
            )
    lines.append("")

    lines.append("--- POSSIBLE FORGOTTEN SUBSCRIPTIONS ---")
    if not subscriptions.empty:
        for _, row in subscriptions.iterrows():
            lines.append(
                f"  {row['merchant']}  {row['frequency']}  "
                f"{row['avg_charge_fmt']}/period  "
                f"since {row['first_seen_fmt']}"
            )
    lines.append("")

    if not yoy.empty:
        lines.append("--- YEAR-OVER-YEAR CHANGES ---")
        for _, row in yoy.iterrows():
            lines.append(
                f"  {row['merchant']}  {row['year_a']}→{row['year_b']}  "
                f"{row['amount_a_fmt']}→{row['amount_b_fmt']}  "
                f"({row['pct_fmt']}, {row['delta_fmt']})"
            )
        lines.append("")

    # Monthly totals for context
    monthly = df.groupby(df["date"].dt.to_period("M"))["amount"].sum()
    lines.append("--- MONTHLY SPEND TOTALS ---")
    for period, total in monthly.items():
        lines.append(f"  {period}: ${total:,.2f}")
    lines.append("")

    # Category-level summary (merchant frequency)
    lines.append("--- TOP MERCHANTS BY TOTAL SPEND ---")
    top_merchants = (
        df.groupby("merchant")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
    )
    for merchant, total in top_merchants.items():
        lines.append(f"  {merchant}: ${total:,.2f}")

    return "\n".join(lines)
